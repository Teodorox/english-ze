import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGLISH_DB", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_screens_return_the_app(client):
    for path in ("/", "/estudar", "/vault", "/stats", "/qualquer/coisa"):
        res = client.get(path)
        assert res.status_code == 200, path
        assert "id=root" in res.text
        assert res.headers["cache-control"] == "no-cache"


def test_files_are_served_with_cache(client):
    asset = client.get("/assets/index-abc123.js")
    assert asset.status_code == 200
    assert "immutable" in asset.headers["cache-control"]
    assert client.get("/favicon.svg").status_code == 200


def test_missing_files_are_404_not_the_app(client):
    assert client.get("/assets/nao-existe.js").status_code == 404
    assert client.get("/nao-existe.png").status_code == 404
    assert client.get("/api/rota-inexistente").status_code == 404


def test_cannot_escape_the_app_folder(client, tmp_path):
    (tmp_path / "segredo.txt").write_text("não pode vazar", encoding="utf-8")
    for path in ("/../segredo.txt", "/%2e%2e/segredo.txt", "/assets/..%2f..%2fsegredo.txt"):
        res = client.get(path)
        assert "não pode vazar" not in res.text, path


def test_api_still_works(client):
    assert client.get("/api/stats").status_code == 200


def test_app_not_built_shows_instructions(client, monkeypatch, tmp_path):
    monkeypatch.setenv("ENGLISH_ZE_WEB_DIST", str(tmp_path / "vazio"))
    res = client.get("/")
    assert res.status_code == 503
    assert "npm run build" in res.text
