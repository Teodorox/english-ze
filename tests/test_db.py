import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
import pytest
from psycopg.rows import dict_row

import contas
import importar_sqlite
from app import auth, db

# Estrutura do banco SQLite antigo (antes do PostgreSQL), pra testar a importação.
OLD_SQLITE_SCHEMA = """
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT, front TEXT NOT NULL UNIQUE, back TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT 'geral', source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, ease REAL NOT NULL DEFAULT 2.5, interval_days INTEGER NOT NULL DEFAULT 0,
    reps INTEGER NOT NULL DEFAULT 0, lapses INTEGER NOT NULL DEFAULT 0, due TEXT, introduced_on TEXT
);
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT, card_id INTEGER NOT NULL, grade INTEGER NOT NULL,
    reviewed_on TEXT NOT NULL, reviewed_at TEXT NOT NULL
);
CREATE TABLE journal (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, created_at TEXT NOT NULL, correction TEXT);
"""


def test_migrations_run_once_in_order(database):
    db.init_db()
    db.init_db()
    with psycopg.connect(database, row_factory=dict_row) as conn:
        assert db.migrate(conn) == []
        versions = [r["version"] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
        assert conn.execute("SELECT COUNT(*) AS n FROM cards").fetchone()["n"] == 0  # deck só nas contas
    assert versions == sorted(int(p.name[:3]) for p in db.MIGRATIONS_DIR.glob("*.sql"))


def test_new_account_starts_without_cards(database):
    db.init_db()
    with psycopg.connect(database, row_factory=dict_row) as conn:
        user_id = auth.create_user(conn, email="a@b.co", name="A", password="12345678", timezone="UTC")
        assert conn.execute("SELECT COUNT(*) AS n FROM cards WHERE user_id = %s", (user_id,)).fetchone()["n"] == 0


def test_today_follows_the_app_timezone(monkeypatch):
    # Kiritimati (UTC+14) e Honolulu (UTC-10) estão sempre em dias diferentes.
    monkeypatch.setenv("ENGLISH_ZE_TIMEZONE", "Pacific/Kiritimati")
    ahead = db.today()
    monkeypatch.setenv("ENGLISH_ZE_TIMEZONE", "Pacific/Honolulu")
    assert db.today() < ahead
    assert db.today() == datetime.now(ZoneInfo("Pacific/Honolulu")).date()


def test_missing_database_url_explains_what_to_do(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(db.DatabaseError, match="DATABASE_URL"):
        db.init_db()


@pytest.fixture
def old_sqlite(tmp_path):
    path = tmp_path / "english.db"
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SQLITE_SCHEMA)
    conn.executemany(
        "INSERT INTO cards (id, front, back, source, created_at, ease, interval_days, reps, lapses, due, introduced_on)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (3, "No cap", "Sem mentira", "deck inicial", "2026-10-01T20:15:00", 2.36, 6, 3, 1, "2026-10-25", "2026-10-01"),
            (9, "That's tuff", "Isso é muito bom", "live", "2026-10-02T21:00:00", 2.5, 0, 0, 0, None, None),
        ],
    )
    conn.executemany(
        "INSERT INTO reviews (card_id, grade, reviewed_on, reviewed_at) VALUES (?, ?, ?, ?)",
        [(3, 2, "2026-10-01", "2026-10-01T20:16:00"), (3, 0, "2026-10-02", "2026-10-02T08:00:00"),
         (99, 2, "2026-10-02", "2026-10-02T08:01:00")],  # card 99 foi apagado: revisão órfã
    )
    conn.execute(
        "INSERT INTO journal (text, created_at, correction) VALUES (?, ?, ?)",
        ("I go yesterday", "2026-10-02T22:00:00", '{"corrected": "I went yesterday", "mistakes": []}'),
    )
    conn.commit()
    conn.close()
    return path


def test_import_from_sqlite_keeps_everything(database, old_sqlite, monkeypatch, capsys):
    db.init_db()  # o app já subiu uma vez (banco vazio, sem contas): a importação pode rodar
    monkeypatch.setattr("sys.argv", ["importar_sqlite.py", "--sqlite", str(old_sqlite)])
    importar_sqlite.main()
    assert "Tudo copiado e conferido." in capsys.readouterr().out

    with psycopg.connect(database, row_factory=dict_row) as conn:
        card = conn.execute("SELECT * FROM cards WHERE id = 3").fetchone()
        assert (card["front"], card["ease"], card["reps"], card["due"].isoformat()) == ("No cap", 2.36, 3, "2026-10-25")
        assert card["created_at"] == datetime(2026, 10, 1, 20, 15, tzinfo=ZoneInfo("America/Sao_Paulo"))
        assert conn.execute("SELECT COUNT(*) AS n FROM reviews").fetchone()["n"] == 2
        assert conn.execute("SELECT correction FROM journal").fetchone()["correction"]["corrected"] == "I went yesterday"
        # Card novo continua a numeração depois do maior id importado
        new_id = conn.execute("INSERT INTO cards (front, back) VALUES ('W', 'Vitória') RETURNING id").fetchone()["id"]
        assert new_id == 10


def test_import_refuses_to_overwrite_study_data(database, old_sqlite, monkeypatch):
    monkeypatch.setattr("sys.argv", ["importar_sqlite.py", "--sqlite", str(old_sqlite)])
    importar_sqlite.main()
    with pytest.raises(SystemExit, match="--substituir"):
        importar_sqlite.main()
    monkeypatch.setattr("sys.argv", ["importar_sqlite.py", "--sqlite", str(old_sqlite), "--substituir"])
    importar_sqlite.main()


def test_import_never_runs_once_accounts_exist(database, old_sqlite, monkeypatch):
    db.init_db()
    with psycopg.connect(database, row_factory=dict_row) as conn:
        auth.create_user(conn, email="a@b.co", name="A", password="12345678", timezone="UTC")
    monkeypatch.setattr("sys.argv", ["importar_sqlite.py", "--sqlite", str(old_sqlite), "--substituir"])
    with pytest.raises(SystemExit, match="já tem contas"):
        importar_sqlite.main()


def test_adopt_old_data_into_a_fresh_account(database, old_sqlite, monkeypatch):
    monkeypatch.setattr("sys.argv", ["importar_sqlite.py", "--sqlite", str(old_sqlite)])
    importar_sqlite.main()
    with psycopg.connect(database, row_factory=dict_row) as conn:
        user_id = auth.create_user(conn, email="eu@b.co", name="Eu", password="12345678", timezone="UTC")
        other = auth.create_user(conn, email="outra@b.co", name="Outra", password="12345678", timezone="UTC")
        assert contas.adopt_orphans(conn, user_id) == {"cards": 2, "journal": 1}
        fronts = {r["front"] for r in conn.execute("SELECT front FROM cards WHERE user_id = %s", (user_id,))}
        assert fronts == {"No cap", "That's tuff"}  # os dados antigos entraram na conta
        assert conn.execute("SELECT COUNT(*) AS n FROM cards WHERE user_id IS NULL").fetchone()["n"] == 0
        # Nada foi pra outra conta, e ela não pode assumir de novo
        assert conn.execute("SELECT COUNT(*) AS n FROM cards WHERE user_id = %s", (other,)).fetchone()["n"] == 0
        with pytest.raises(SystemExit, match="sem dono"):
            contas.adopt_orphans(conn, other)


def test_adopt_refuses_an_account_that_already_studied(database, old_sqlite, monkeypatch):
    monkeypatch.setattr("sys.argv", ["importar_sqlite.py", "--sqlite", str(old_sqlite)])
    importar_sqlite.main()
    with psycopg.connect(database, row_factory=dict_row) as conn:
        user_id = auth.create_user(conn, email="eu@b.co", name="Eu", password="12345678", timezone="UTC")
        conn.execute("INSERT INTO journal (user_id, text) VALUES (%s, 'meu')", (user_id,))
        with pytest.raises(SystemExit, match="estudo próprio"):
            contas.adopt_orphans(conn, user_id)
