import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
import pytest
from psycopg.rows import dict_row

import importar_sqlite
from app import db

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


def test_migrations_run_once_and_seed_once(database):
    db.init_db()
    db.init_db()
    with psycopg.connect(database, row_factory=dict_row) as conn:
        assert db.migrate(conn) == []
        versions = [r["version"] for r in conn.execute("SELECT version FROM schema_migrations")]
        seeded = conn.execute("SELECT COUNT(*) AS n FROM cards").fetchone()["n"]
    assert versions == [1]
    assert seeded == len(json.loads(db.SEED_FILE.read_text(encoding="utf-8")))


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
    db.init_db()  # o app já subiu uma vez (só o deck inicial): a importação pode substituir
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
