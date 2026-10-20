import json
import os
from contextlib import contextmanager
from datetime import date, datetime
from itertools import zip_longest
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / "data" / "seed_cards.json"
SEED_SOURCE = "deck inicial"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
MIGRATION_LOCK = 4_242_001  # trava do PostgreSQL: dois servidores subindo juntos não migram ao mesmo tempo

_pool: ConnectionPool | None = None


class DatabaseError(RuntimeError):
    """Banco não configurado ou fora do ar (mensagem pronta pra mostrar no terminal)."""


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise DatabaseError("Defina DATABASE_URL no .env (veja o .env.example e o README).")
    return url


def with_database(url: str, name: str) -> str:
    """O mesmo servidor e usuário, outro banco (ex.: o de um perfil)."""
    return make_conninfo(url, dbname=name)


def profile_database(profile: str) -> str:
    return f"english_ze_{profile.replace('-', '_')}"


def data_dir() -> Path:
    """Arquivos locais do app (chave das sessões, certificados). Cada perfil tem a sua pasta."""
    return Path(os.environ.get("ENGLISH_ZE_DATA_DIR", ROOT / "data"))


def timezone() -> ZoneInfo:
    return ZoneInfo(os.environ.get("ENGLISH_ZE_TIMEZONE", DEFAULT_TIMEZONE))


def today() -> date:
    """O 'hoje' das revisões no fuso do usuário, não no do servidor (na nuvem ele roda em UTC)."""
    return datetime.now(timezone()).date()


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            database_url(),
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            check=ConnectionPool.check_connection,  # descarta conexões mortas (ex.: o PostgreSQL reiniciou)
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def connect():
    """Uma conexão do pool numa transação: confirma no fim, desfaz tudo se der erro."""
    with _get_pool().connection() as conn:
        yield conn


def init_db() -> None:
    url = database_url()
    try:
        _create_database_if_missing(url)
        with psycopg.connect(url, row_factory=dict_row) as conn:
            migrate(conn)
            if conn.execute("SELECT NOT EXISTS (SELECT 1 FROM cards) AS empty").fetchone()["empty"] and SEED_FILE.exists():
                _seed(conn)
    except psycopg.OperationalError as e:
        name = conninfo_to_dict(url).get("dbname", "?")
        raise DatabaseError(
            f"Não consegui conectar ao PostgreSQL (banco {name}). Confira se o serviço está rodando"
            f" e o DATABASE_URL no .env.\nDetalhe: {e}"
        ) from None


def _create_database_if_missing(url: str) -> None:
    """Cria o banco (ex.: o de um perfil novo) se o usuário tiver permissão; senão, segue e o erro aparece ao conectar."""
    name = conninfo_to_dict(url).get("dbname")
    if not name:
        return
    try:
        with psycopg.connect(with_database(url, "postgres"), autocommit=True) as conn:
            if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone() is None:
                conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.Error:
        pass


def migrate(conn: psycopg.Connection) -> list[int]:
    """Aplica, em ordem, os arquivos de app/migrations que este banco ainda não tem."""
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK,))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = int(path.name.split("_", 1)[0])
        if version in done:
            continue
        conn.execute(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        applied.append(version)
    conn.commit()
    return applied


def _seed(conn: psycopg.Connection) -> None:
    """Carrega o deck inicial intercalando categorias, pra os cards novos virem variados."""
    cards = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    by_category: dict[str, list[dict]] = {}
    for card in cards:
        by_category.setdefault(card["category"], []).append(card)

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO cards (front, back, note, category, source) VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (front) DO NOTHING",
            [
                (card["front"], card["back"], card.get("note", ""), card["category"], SEED_SOURCE)
                for group in zip_longest(*by_category.values())
                for card in filter(None, group)
            ],
        )
    conn.commit()
