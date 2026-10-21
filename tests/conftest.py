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
    """Cria contas já logadas, cada uma no seu 'navegador': new_user("ana@x.com")."""
    from app.main import app

    clients = []

    def make(email: str = "ana@example.com", name: str = "Ana", password: str = PASSWORD) -> TestClient:
        client = TestClient(app)
        clients.append(client)
        res = client.post(
            "/api/signup", json={"name": name, "email": email, "password": password, "invite": make_invite()}
        )
        assert res.status_code == 201, res.text
        res = client.post("/api/login", json={"email": email, "password": password})
        assert res.status_code == 200, res.text
        return client

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def client(new_user):
    """Uma conta logada (a maioria dos testes só precisa disso)."""
    return new_user()
