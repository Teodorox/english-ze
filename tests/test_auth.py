import time

import pytest
from fastapi.testclient import TestClient

from app import auth

PASSWORD = "senha-forte-123"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGLISH_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ENGLISH_ZE_PASSWORD", PASSWORD)
    from app import main

    main.login_limiter.reset("testclient")
    with TestClient(main.app) as c:
        yield c


def test_blocks_without_login(client):
    assert client.get("/api/stats").status_code == 401
    res = client.get("/", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == "/login.html"
    assert client.get("/login.html").status_code == 200
    assert client.get("/style.css").status_code == 200


def test_login_and_logout(client):
    assert client.post("/api/login", json={"password": "errada"}).status_code == 401
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    assert client.get("/api/stats").status_code == 200
    assert client.get("/").status_code == 200

    client.post("/api/logout")
    assert client.get("/api/stats").status_code == 401


def test_rate_limit_after_failures(client):
    for _ in range(5):
        client.post("/api/login", json={"password": "errada"})
    # até a senha certa é recusada enquanto estiver bloqueado
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 429


def test_token_rules(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGLISH_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ENGLISH_ZE_PASSWORD", PASSWORD)
    token = auth.make_token()
    assert auth.valid_token(token)
    assert not auth.valid_token(token + "x")
    assert not auth.valid_token("garbage")
    assert not auth.valid_token(token, now=time.time() + auth.SESSION_SECONDS + 1)

    # trocar a senha derruba as sessões antigas
    monkeypatch.setenv("ENGLISH_ZE_PASSWORD", "nova-senha")
    assert not auth.valid_token(token)


def test_limiter_window():
    limiter = auth.LoginLimiter(max_failures=2, window_seconds=60)
    limiter.fail("ip", now=0)
    limiter.fail("ip", now=1)
    assert limiter.blocked("ip", now=2)
    assert not limiter.blocked("ip", now=100)
