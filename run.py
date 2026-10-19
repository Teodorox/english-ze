"""Inicia o servidor e abre o navegador.

    python run.py              # só neste computador, porta 8001 (ou a próxima livre)
    python run.py --port 9000  # escolhe a porta
    python run.py --lan        # libera pro celular no mesmo Wi-Fi, com HTTPS (microfone funciona)
"""

import argparse
import ipaddress
import os
import socket
import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import uvicorn

from app.config import load_env_file

LOCALHOST = "127.0.0.1"
DEFAULT_PORT = 8001
CERT_DIR = Path(__file__).resolve().parent / "data" / "certs"
CERT_VERSION = 2  # mude ao alterar o formato do certificado, pra gerar um novo
CERT_DAYS = 365   # o iOS recusa certificados com mais de 825 dias


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--lan", action="store_true", help="libera pro celular no mesmo Wi-Fi (HTTPS)")
    args = parser.parse_args()

    load_env_file()
    if args.lan and not os.environ.get("ENGLISH_ZE_PASSWORD"):
        raise SystemExit(
            "Pra liberar na rede, defina uma senha: adicione ENGLISH_ZE_PASSWORD=... no arquivo .env"
        )

    port = find_free_port(args.port)
    if port != args.port:
        print(f"Porta {args.port} ocupada, usando {port}.")

    options: dict = {"host": LOCALHOST, "port": port}
    url = f"http://{LOCALHOST}:{port}"

    if args.lan:
        ip = lan_ip()
        cert_file, key_file = self_signed_cert(ip)
        options.update(host="0.0.0.0", ssl_certfile=str(cert_file), ssl_keyfile=str(key_file))
        url = f"https://{LOCALHOST}:{port}"
        print(f"No celular (mesmo Wi-Fi), abra: https://{ip}:{port}")
        print("O navegador vai avisar que a conexão não é privada: toque em 'Avançado' > 'Continuar'.")

    print(f"English Ze rodando em {url}")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.main:app", **options)
