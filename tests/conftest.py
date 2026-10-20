import os

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from app.config import load_env_file

# Definidas antes de importar o app: o .env não sobrescreve variáveis existentes,
# então os testes nunca usam (nem gastam) a chave real e começam sem login.
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
os.environ["ENGLISH_ZE_PASSWORD"] = ""
load_env_file()


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.exit("Defina TEST_DATABASE_URL no .env (um banco só pra testes, ex.: english_ze_test).", 2)
    # Trava de segurança: cada teste apaga o banco inteiro, então nunca pode ser o banco de verdade.
    if not conninfo_to_dict(url).get("dbname", "").endswith("_test"):
        pytest.exit("TEST_DATABASE_URL precisa apontar pra um banco com nome terminado em _test.", 2)
    return url


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """Cada teste começa com o banco de teste vazio (o app cria as tabelas e o deck inicial ao subir)."""
    url = _test_database_url()
    with psycopg.connect(url, autocommit=True) as conn:
        tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
        for table in tables:
            conn.execute(sql.SQL("DROP TABLE {} CASCADE").format(sql.Identifier(table)))
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("ENGLISH_ZE_DATA_DIR", str(tmp_path / "data"))
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
