import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "english.db"
SEED_FILE = ROOT / "data" / "seed_cards.json"
SEED_SOURCE = "deck inicial"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    front         TEXT NOT NULL UNIQUE,
    back          TEXT NOT NULL,
    note          TEXT NOT NULL DEFAULT '',
    category      TEXT NOT NULL DEFAULT 'geral',
    source        TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    ease          REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    reps          INTEGER NOT NULL DEFAULT 0,
    lapses        INTEGER NOT NULL DEFAULT 0,
    due           TEXT,
    introduced_on TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id     INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    grade       INTEGER NOT NULL,
    reviewed_on TEXT NOT NULL,
    reviewed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journal (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_due ON cards(due);
CREATE INDEX IF NOT EXISTS idx_reviews_day ON reviews(reviewed_on);
"""


def db_path() -> Path:
    return Path(os.environ.get("ENGLISH_DB", DEFAULT_DB))


@contextmanager
def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_db() -> None:
    db_path().parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        empty = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 0
        if empty and SEED_FILE.exists():
            _seed(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Adiciona colunas novas em bancos criados por versões anteriores."""
    journal_columns = {r["name"] for r in conn.execute("PRAGMA table_info(journal)")}
    if "correction" not in journal_columns:
        conn.execute("ALTER TABLE journal ADD COLUMN correction TEXT")


def _seed(conn: sqlite3.Connection) -> None:
    """Carrega o deck inicial intercalando categorias, pra os cards novos virem variados."""
    cards = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    by_category: dict[str, list[dict]] = {}
    for card in cards:
        by_category.setdefault(card["category"], []).append(card)

    created = now_iso()
    for group in zip_longest(*by_category.values()):
        for card in filter(None, group):
            conn.execute(
                "INSERT OR IGNORE INTO cards (front, back, note, category, source, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (card["front"], card["back"], card.get("note", ""), card["category"], SEED_SOURCE, created),
            )
