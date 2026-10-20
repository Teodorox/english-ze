"""Inicia o servidor e abre o navegador.

    python run.py              # só neste computador, porta 8001 (ou a próxima livre)
    python run.py --port 9000  # escolhe a porta
    python run.py --lan        # libera pro celular no mesmo Wi-Fi, com HTTPS (microfone funciona)
    python run.py --tunnel     # publica na internet com um link https (Cloudflare Tunnel)
    python run.py --profile professora --tunnel --port 8100
                               # cópia separada (banco english_ze_professora) publicada
"""

import argparse
import atexit
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import uvicorn

from app import db
from app.config import load_env_file

LOCALHOST = "127.0.0.1"
DEFAULT_PORT = 8001
ROOT = Path(__file__).resolve().parent
CERT_DIR = ROOT / "data" / "certs"
PROFILES_DIR = ROOT / "data" / "profiles"
WEB_DIR = ROOT / "web"
CERT_VERSION = 2  # mude ao alterar o formato do certificado, pra gerar um novo
CERT_DAYS = 365   # o iOS recusa certificados com mais de 825 dias


def frontend_is_stale() -> bool:
    """True se o app React nunca foi gerado ou se o código mudou depois da última geração."""
    built = WEB_DIR / "dist" / "index.html"
    if not built.exists():
        return True
    built_at = built.stat().st_mtime
    sources = [WEB_DIR / "index.html", WEB_DIR / "package.json", *(WEB_DIR / "src").rglob("*"), *(WEB_DIR / "public").rglob("*")]
    return any(p.is_file() and p.stat().st_mtime > built_at for p in sources)


def ensure_frontend_built() -> None:
    """Gera o app React (npm run build) quando precisa. Requer o Node.js instalado."""
    if not frontend_is_stale():
        return
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("O app precisa ser gerado, mas o Node.js não foi encontrado. Instale em https://nodejs.org")
    print("Gerando o app (só na primeira vez ou quando o código muda)...")
    if not (WEB_DIR / "node_modules").exists():
        subprocess.run([npm, "ci"], cwd=WEB_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=WEB_DIR, check=True)


def is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((LOCALHOST, port)) != 0


def find_free_port(start: int, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        if is_free(port):
            return port
    raise SystemExit(f"Nenhuma porta livre entre {start} e {start + attempts - 1}.")


def lan_ip() -> str:
    """IP deste computador na rede local. O UDP 'connect' não envia nenhum pacote."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return LOCALHOST


def self_signed_cert(ip: str) -> tuple[Path, Path]:
    """Gera (uma vez por IP) um certificado autoassinado, que o navegador aceita após um aviso.

    O HTTPS é o que libera o microfone no celular. O certificado segue as regras do
    iOS/Safari (validade <= 825 dias e Extended Key Usage = serverAuth); sem isso o
    Safari nem mostra o aviso, simplesmente não carrega a página.
    """
    stem = f"{ip}-v{CERT_VERSION}"
    cert_file, key_file = CERT_DIR / f"{stem}.crt", CERT_DIR / f"{stem}.key"
    if cert_file.exists() and key_file.exists():
        return cert_file, key_file

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "English Ze (local)")])
    now = datetime.now(timezone.utc)
    alt_names = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address(LOCALHOST)),
        x509.IPAddress(ipaddress.ip_address(ip)),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(hours=1))
        .not_valid_after(now + timedelta(days=CERT_DAYS))
        .add_extension(alt_names, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_encipherment=False, content_commitment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256())
    )

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_file, key_file


def cloudflared_path() -> str:
    found = shutil.which("cloudflared")
    if found:
        return found
    # o winget instala aqui, mas o PATH só atualiza em terminais novos
    for candidate in (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "cloudflared" / "cloudflared.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "cloudflared" / "cloudflared.exe",
    ):
        if candidate.exists():
            return str(candidate)
    raise SystemExit("cloudflared não encontrado. Instale com: winget install Cloudflare.cloudflared")


def start_tunnel(port: int) -> subprocess.Popen:
    """Abre um Cloudflare quick tunnel (link https público, sem conta) e mostra o endereço."""
    proc = subprocess.Popen(
        [cloudflared_path(), "tunnel", "--no-autoupdate", "--url", f"http://{LOCALHOST}:{port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    def watch() -> None:
        announced = False
        for line in proc.stderr:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match and not announced:
                announced = True
                link = match.group(0)
                copied = copy_to_clipboard(link)
                print(f"\n>>> Link público: {link}")
                print(">>> (copiado, é só colar na mensagem)\n" if copied else "")

    threading.Thread(target=watch, daemon=True).start()
    atexit.register(proc.terminate)
    return proc


def copy_to_clipboard(text: str) -> bool:
    if os.name != "nt":
        return False
    try:
        subprocess.run(["clip"], input=text, text=True, check=True, timeout=5)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--lan", action="store_true", help="libera pro celular no mesmo Wi-Fi (HTTPS)")
    parser.add_argument("--tunnel", action="store_true", help="publica na internet com um link https (Cloudflare)")
    parser.add_argument("--profile", help="roda uma cópia separada, com dados em data/profiles/NOME/")
    args = parser.parse_args()

    if args.lan and args.tunnel:
        raise SystemExit("Use --lan ou --tunnel, não os dois.")

    if args.profile:
        if not re.fullmatch(r"[a-z0-9_-]+", args.profile):
            raise SystemExit("Nome de perfil: só letras minúsculas, números, - e _.")
        profile_dir = PROFILES_DIR / args.profile
        if not (profile_dir / ".env").exists():
            raise SystemExit(
                f"Crie {profile_dir / '.env'} com pelo menos ENGLISH_ZE_PASSWORD=... (veja o README)."
            )
        os.environ["ENGLISH_ZE_DATA_DIR"] = str(profile_dir)
        load_env_file(profile_dir / ".env")  # vem antes: os valores do perfil têm prioridade
        profile_has_database = "DATABASE_URL" in os.environ
        print(f"Perfil: {args.profile}")

    load_env_file()
    if args.profile and not profile_has_database and os.environ.get("DATABASE_URL"):
        # Mesmo servidor, banco próprio do perfil (criado sozinho na primeira vez)
        os.environ["DATABASE_URL"] = db.with_database(
            os.environ["DATABASE_URL"], db.profile_database(args.profile)
        )
    try:
        db.init_db()
    except db.DatabaseError as e:
        raise SystemExit(str(e)) from None
    if (args.lan or args.tunnel) and not os.environ.get("ENGLISH_ZE_PASSWORD"):
        raise SystemExit(
            "Pra liberar fora deste computador, defina uma senha: ENGLISH_ZE_PASSWORD=... no .env"
        )

    ensure_frontend_built()

    port = find_free_port(args.port)
    if port != args.port:
        print(f"Porta {args.port} ocupada, usando {port}.")

    options: dict = {"host": LOCALHOST, "port": port}
    url = f"http://{LOCALHOST}:{port}"

    if args.tunnel:
        # O Cloudflare cuida do HTTPS; os headers de proxy informam o IP real de quem
        # acessa (pro limite de tentativas de login) e que a conexão original é https.
        options.update(proxy_headers=True, forwarded_allow_ips=LOCALHOST)
        start_tunnel(port)
        print("Abrindo o túnel... o link público aparece abaixo em alguns segundos.")

    if args.lan:
        ip = lan_ip()
        cert_file, key_file = self_signed_cert(ip)
        options.update(host="0.0.0.0", ssl_certfile=str(cert_file), ssl_keyfile=str(key_file))
        url = f"https://{LOCALHOST}:{port}"
        print(f"No celular (mesmo Wi-Fi), abra: https://{ip}:{port}")
        print("O navegador vai avisar que a conexão não é privada: toque em 'Avançado' > 'Continuar'.")

    print(f"English Ze rodando em {url}")
    if not args.tunnel:  # no túnel, o app é pra outra pessoa: não abre o navegador aqui
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.main:app", **options)
