import json
import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from app.config import load_env_file

# Definidas antes de importar o app: o .env não sobrescreve variáveis existentes,
# então os testes nunca usam (nem gastam) a chave real.
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
load_env_file()

PASSWORD = "senha-forte-123"
ONBOARDING = {"goals": ["streamers", "conversar"], "level": "iniciante", "daily_minutes": 10}

# Trilhas pequenas e fixas: os testes não mudam quando as frases de data/tracks mudam.
TEST_TRACKS = {
    "base": {"category": "conversa", "situations": [
        {"level": "basico", "title": "Base básico", "cards": [
            {"front": "Base B1", "back": "Base b1"}, {"front": "Base B2", "back": "Base b2"}]},
        {"level": "iniciante", "title": "Base iniciante", "cards": [
            {"front": "Base I1", "back": "Base i1", "note": "nota"}, {"front": "Base I2", "back": "Base i2"},
            {"front": "Base I3", "back": "Base i3"}]},
    ]},
    "streamers": {"category": "streamer", "situations": [
        {"level": "iniciante", "title": "Chat", "cards": [
            {"front": "No cap, that was crazy.", "back": "Sem mentira, aquilo foi insano."},
            {"front": "Stream I2", "back": "Stream i2"}, {"front": "Stream I3", "back": "Stream i3"}]},
        {"level": "basico", "title": "Gírias", "cards": [
            {"front": "Stream B1", "back": "Stream b1"}, {"front": "Stream B2", "back": "Stream b2"}]},
    ]},
    "conversar": {"category": "conversa", "situations": [
        {"level": "iniciante", "title": "Oi", "cards": [
            {"front": "Talk I1", "back": "Talk i1"}, {"front": "Talk I2", "back": "Talk i2"},
            {"front": "Talk I3", "back": "Talk i3"}]},
    ]},
    "viagem": {"category": "viagem", "situations": [
        {"level": "iniciante", "title": "No aeroporto", "cards": [
            {"front": "Trip I1", "back": "Trip i1"}, {"front": "Trip I2", "back": "Trip i2"}]},
        {"level": "basico", "title": "No hotel", "category": "hotel", "cards": [
            {"front": "Trip B1", "back": "Trip b1"}, {"front": "Trip B2", "back": "Trip b2"}]},
    ]},
}


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.exit("Defina TEST_DATABASE_URL no .env (um banco só pra testes, ex.: english_ze_test).", 2)
    # Trava de segurança: cada teste apaga o banco inteiro, então nunca pode ser o banco de verdade.
    if not conninfo_to_dict(url).get("dbname", "").endswith("_test"):
        pytest.exit("TEST_DATABASE_URL precisa apontar pra um banco com nome terminado em _test.", 2)
    return url


@pytest.fixture(autouse=True)
def database(monkeypatch):
    """Cada teste começa com o banco de teste vazio (o app cria as tabelas ao subir)."""
    url = _test_database_url()
    with psycopg.connect(url, autocommit=True) as conn:
        tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
        for table in tables:
            conn.execute(sql.SQL("DROP TABLE {} CASCADE").format(sql.Identifier(table)))
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture(autouse=True)
def web_dist(tmp_path, monkeypatch):
    """Um 'app React compilado' mínimo, pra os testes não dependerem do npm run build."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    monkeypatch.setenv("ENGLISH_ZE_WEB_DIST", str(dist))
    return dist


@pytest.fixture(autouse=True)
def test_tracks(tmp_path, monkeypatch):
    folder = tmp_path / "tracks"
    folder.mkdir()
    for name, track in TEST_TRACKS.items():
        (folder / f"{name}.json").write_text(json.dumps(track), encoding="utf-8")
    monkeypatch.setenv("ENGLISH_ZE_TRACKS_DIR", str(folder))
    return folder


@pytest.fixture
def make_invite(database):
    """Cria um convite direto no banco (como o 'python contas.py convite')."""

    def make() -> str:
        from app import auth

        code = auth.make_invite_code()
        with psycopg.connect(database) as conn:
            conn.execute("INSERT INTO invites (code) VALUES (%s)", (code,))
        return code

    return make


@pytest.fixture
def anon():
    """Navegador sem login (o app já subiu e criou as tabelas)."""
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def new_user(anon, make_invite):
    """Contas logadas e com o primeiro acesso feito, cada uma no seu 'navegador': new_user("ana@x.com")."""
    from app.main import app

    clients = []

    def make(
        email: str = "ana@example.com", name: str = "Ana", password: str = PASSWORD, onboard: bool = True
    ) -> TestClient:
        client = TestClient(app)
        clients.append(client)
        res = client.post(
            "/api/signup", json={"name": name, "email": email, "password": password, "invite": make_invite()}
        )
        assert res.status_code == 201, res.text
        res = client.post("/api/login", json={"email": email, "password": password})
        assert res.status_code == 200, res.text
        if onboard:  # como no app: a pessoa responde o primeiro acesso e ganha as frases das trilhas
            assert client.post("/api/me/onboarding", json=ONBOARDING).status_code == 200
        return client

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def client(new_user):
    """Uma conta logada (a maioria dos testes só precisa disso)."""
    return new_user()
