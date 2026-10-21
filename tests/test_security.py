"""Testes de ataque: SQL injection, CSRF, corpo gigante, senhas fracas, força bruta e vazamento de detalhes."""

import re
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import auth
from conftest import PASSWORD

ROOT = Path(__file__).resolve().parent.parent

INJECTIONS = [
    "'; DROP TABLE cards; --",
    "' OR '1'='1",
    "x' UNION SELECT password_hash, email, name FROM users --",
    "1; DELETE FROM users",
    "\\'; TRUNCATE sessions; --",
    "%' AND pg_sleep(5) --",
]


def tables(database) -> set[str]:
    with psycopg.connect(database) as conn:
        return {r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}


# ---------- SQL injection ----------

def test_no_sql_is_built_from_strings():
    """Toda consulta usa parâmetros (%s). Um f-string ou + dentro de execute() é como nasce um SQL injection."""
    offenders = []
    for path in [*ROOT.glob("app/*.py"), ROOT / "contas.py"]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            built = re.search(r"execute(many)?\(\s*f[\"']|execute(many)?\([^)]*[\"']\s*(\+|%(?!s))", line)
            formatted = ".format(" in line and re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\b", line)
            if built or formatted:
                if "sql.SQL(" not in line:  # sql.SQL + sql.Identifier é a forma segura de montar nomes
                    offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert offenders == []


@pytest.mark.parametrize("payload", INJECTIONS)
def test_injection_payloads_are_just_text(client, database, payload):
    before = tables(database)
    assert client.get("/api/cards", params={"q": payload}).status_code == 200
    assert client.get("/api/cards", params={"category": payload[:40]}).json() == []
    created = client.post("/api/cards", json={"front": payload, "back": payload, "category": payload[:40]})
    assert created.status_code == 201
    assert created.json()["front"] == payload  # guardado ao pé da letra, sem executar nada
    assert client.post("/api/journal", json={"text": payload}).json()["text"] == payload
    assert client.patch("/api/me", json={"name": payload[:60], "learner": payload}).status_code == 200
    assert client.patch("/api/me", json={"timezone": payload}).status_code == 422

    anon = TestClient(client.app)
    assert anon.post("/api/login", json={"email": payload, "password": payload}).status_code == 401
    assert anon.post("/api/login", json={"email": "ana@example.com", "password": payload}).status_code == 401
    res = anon.post("/api/signup", json={"name": "X", "email": "x@y.co", "password": "uma-senha-boa", "invite": payload})
    assert res.status_code in (403, 422)  # convite inválido (ou longo demais pra ser um código)

    assert tables(database) == before
    assert client.get("/api/me").status_code == 200  # a sessão e a conta continuam lá


def test_search_wildcards_are_literal(client):
    client.post("/api/cards", json={"front": "100% sure", "back": "Com certeza"})
    client.post("/api/cards", json={"front": "snake_case", "back": "nome com sublinhado"})
    assert [c["front"] for c in client.get("/api/cards", params={"q": "%"}).json()] == ["100% sure"]
    assert [c["front"] for c in client.get("/api/cards", params={"q": "_"}).json()] == ["snake_case"]


# ---------- CSRF (ação vinda de outro site) ----------

def test_actions_from_other_sites_are_blocked(client):
    card = client.get("/api/session?new_limit=1").json()["new"][0]
    evil = {"Origin": "https://site-malicioso.com"}
    assert client.post(f"/api/cards/{card['id']}/review", json={"grade": 3}, headers=evil).status_code == 403
    assert client.request("DELETE", "/api/me", json={"password": PASSWORD}, headers=evil).status_code == 403
    assert client.post("/api/me/logout-others", headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/me").status_code == 200  # nada aconteceu

    same = {"Origin": "http://testserver"}
    assert client.post(f"/api/cards/{card['id']}/review", json={"grade": 2}, headers=same).status_code == 200


def test_origin_rules():
    from starlette.requests import Request

    def request(origin, host, forwarded=None):
        headers = [(b"host", host.encode())]
        if origin is not None:
            headers.append((b"origin", origin.encode()))
        if forwarded:
            headers.append((b"x-forwarded-host", forwarded.encode()))
        return Request({"type": "http", "method": "POST", "path": "/api/x", "headers": headers})

    from app.security import same_origin

    assert same_origin(request("https://abc.trycloudflare.com", "abc.trycloudflare.com"))
    assert same_origin(request("https://abc.trycloudflare.com", "127.0.0.1:8100", "abc.trycloudflare.com"))
    assert same_origin(request("http://localhost:5173", "127.0.0.1:8001"))  # Vite em desenvolvimento
    assert same_origin(request(None, "app.com"))  # sem navegador (ex.: curl), sem cookie de vítima
    assert not same_origin(request("https://evil.com", "app.com"))
    assert not same_origin(request("https://app.com.evil.com", "app.com"))
    assert not same_origin(request("http://localhost:5173", "app.com"))  # localhost só vale em desenvolvimento
    assert not same_origin(request("null", "app.com"))


# ---------- Cabeçalhos e informações expostas ----------

def test_security_headers(client, anon):
    for res in (anon.get("/"), client.get("/api/me")):
        csp = res.headers["content-security-policy"]
        assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp and "unsafe-inline" not in csp
        assert res.headers["x-frame-options"] == "DENY"
        assert res.headers["x-content-type-options"] == "nosniff"
        assert "microphone=(self)" in res.headers["permissions-policy"]
    assert client.get("/api/me").headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in anon.get("/").headers  # só em HTTPS
    https = TestClient(anon.app, base_url="https://testserver")
    assert https.get("/").headers["strict-transport-security"].startswith("max-age=")


def test_api_map_is_not_published(anon):
    assert "swagger" not in anon.get("/docs").text.lower()
    assert "redoc" not in anon.get("/redoc").text.lower()
    assert anon.get("/openapi.json").status_code == 404


def test_no_technical_details_leak(client, monkeypatch):
    import anthropic

    from app import tutor

    def broken(**kwargs):
        raise anthropic.APIConnectionError(request=None)

    monkeypatch.setattr(tutor, "_get_client", lambda: type("C", (), {"messages": type("M", (), {"parse": staticmethod(broken)})})())
    entry = client.post("/api/journal", json={"text": "Hi"}).json()
    detail = client.post(f"/api/journal/{entry['id']}/correct").json()["detail"]
    assert "anthropic" not in detail.lower() and "api" not in detail.lower()


@pytest.mark.parametrize("card_id", [0, -1, 2**31, 10**30])
def test_absurd_ids_are_rejected_cleanly(client, card_id):
    res = client.post(f"/api/cards/{card_id}/review", json={"grade": 2})
    assert res.status_code in (404, 422)  # nunca 500


# ---------- Tamanho do corpo ----------

def test_huge_bodies_are_refused(client):
    assert client.post("/api/journal", json={"text": "a" * 200_000}).status_code == 413
    assert client.post("/api/journal", content=b"x" * 200_000, headers={"Content-Type": "application/json"}).status_code == 413
    # O áudio tem o limite dele (maior), mas também tem fim
    from app import transcribe

    big = b"x" * (transcribe.MAX_AUDIO_BYTES + 10_000)
    assert client.post("/api/transcribe", content=big).status_code == 413


def test_chunked_body_without_length_is_counted(client):
    def chunks():
        for _ in range(100):
            yield b"x" * 10_000

    res = client.post("/api/journal", content=chunks(), headers={"Content-Type": "application/json"})
    assert res.status_code == 413


# ---------- Senhas e força bruta ----------

@pytest.mark.parametrize("weak", ["12345678", "senha123", "Password", "aaaaaaaa", "abababab", "ana@example.com", "anaclara"])
def test_weak_passwords_are_refused(anon, make_invite, weak):
    res = anon.post(
        "/api/signup", json={"name": "Anaclara", "email": "ana@example.com", "password": weak, "invite": make_invite()}
    )
    assert res.status_code == 422, weak


def test_new_password_must_be_strong_too(client):
    assert client.post("/api/me/password", json={"current": PASSWORD, "new": "12345678"}).status_code == 422


def test_failed_attempts_survive_a_restart(anon):
    first = auth.LoginLimiter()
    for _ in range(5):
        first.fail("ip:1.2.3.4")
    assert auth.LoginLimiter().blocked("ip:1.2.3.4")  # outra instância (outro servidor / reinício) vê o bloqueio
    assert not auth.LoginLimiter().blocked("ip:5.6.7.8")


def test_failures_are_stored_without_personal_data(anon, database):
    auth.LoginLimiter().fail("email:ana@example.com")
    with psycopg.connect(database) as conn:
        keys = [bytes(r[0]) for r in conn.execute("SELECT key FROM auth_failures")]
    assert keys and all(b"ana" not in key for key in keys)


def test_password_guessing_on_logged_session_is_limited(client):
    for _ in range(5):
        client.request("DELETE", "/api/me", json={"password": "chute"})
    # nem a senha certa passa enquanto estiver bloqueado: quem pegou o celular destravado não consegue chutar
    assert client.request("DELETE", "/api/me", json={"password": PASSWORD}).status_code == 429
    assert client.post("/api/me/password", json={"current": PASSWORD, "new": "outra-senha-boa"}).status_code == 429


def test_timezone_cannot_be_a_file_path(client):
    for bad in ("../../etc/passwd", "/etc/localtime", "America/../../x", "C:\\Windows"):
        assert client.patch("/api/me", json={"timezone": bad}).status_code == 422, bad
