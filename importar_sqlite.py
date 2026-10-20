"""Copia os dados do banco antigo (SQLite) pro PostgreSQL. O arquivo SQLite só é lido, nunca alterado.

    python importar_sqlite.py                       # data/english.db -> banco do DATABASE_URL
    python importar_sqlite.py --profile professora  # data/profiles/professora/english.db -> english_ze_professora
    python importar_sqlite.py --substituir          # apaga o que já estiver no PostgreSQL antes de copiar

Mantém os números (ids) dos cards, o progresso da repetição espaçada, as revisões (e a sequência de
dias), o diário e as correções. No fim, confere se as contagens dos dois bancos batem.
"""

import argparse
import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app import db
from app.config import load_env_file

ROOT = Path(__file__).resolve().parent
TABLES = ("cards", "reviews", "journal")


def as_datetime(value: str | None) -> datetime | None:
    """Os horários do SQLite eram locais e sem fuso: ganham o fuso do app."""
    if not value:
        return None
    moment = datetime.fromisoformat(value)
    return moment if moment.tzinfo else moment.replace(tzinfo=db.timezone())


def as_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def read_sqlite(path: Path) -> dict[str, list[dict]]:
    source = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        return {t: [dict(r) for r in source.execute(f"SELECT * FROM {t} ORDER BY id")] for t in TABLES}
    finally:
        source.close()


def summary_sqlite(rows: dict[str, list[dict]]) -> dict[str, object]:
    cards, reviews = rows["cards"], rows["reviews"]
    return {
        "cards": len(cards),
        "cards estudados": sum(c["introduced_on"] is not None for c in cards),
        "soma das repetições": sum(c["reps"] for c in cards),
        "soma dos erros (lapses)": sum(c["lapses"] for c in cards),
        "revisões": len(reviews),
        "dias com revisão": len({r["reviewed_on"] for r in reviews}),
        "entradas do diário": len(rows["journal"]),
        "entradas corrigidas": sum(bool(j.get("correction")) for j in rows["journal"]),
    }


def summary_postgres(conn: psycopg.Connection) -> dict[str, object]:
    one = lambda query: conn.execute(query).fetchone()["v"]  # noqa: E731
    return {
        "cards": one("SELECT COUNT(*) AS v FROM cards"),
        "cards estudados": one("SELECT COUNT(*) AS v FROM cards WHERE introduced_on IS NOT NULL"),
        "soma das repetições": one("SELECT COALESCE(SUM(reps), 0) AS v FROM cards"),
        "soma dos erros (lapses)": one("SELECT COALESCE(SUM(lapses), 0) AS v FROM cards"),
        "revisões": one("SELECT COUNT(*) AS v FROM reviews"),
        "dias com revisão": one("SELECT COUNT(DISTINCT reviewed_on) AS v FROM reviews"),
        "entradas do diário": one("SELECT COUNT(*) AS v FROM journal"),
        "entradas corrigidas": one("SELECT COUNT(*) AS v FROM journal WHERE correction IS NOT NULL"),
    }


def only_fresh_seed(conn: psycopg.Connection) -> bool:
    """True se o PostgreSQL só tem o deck inicial intocado (o app já subiu uma vez, mas ninguém estudou)."""
    return conn.execute(
        "SELECT NOT EXISTS (SELECT 1 FROM reviews) AND NOT EXISTS (SELECT 1 FROM journal)"
        " AND NOT EXISTS (SELECT 1 FROM cards WHERE source != %s OR introduced_on IS NOT NULL) AS v",
        (db.SEED_SOURCE,),
    ).fetchone()["v"]


def copy(conn: psycopg.Connection, rows: dict[str, list[dict]]) -> int:
    conn.execute("TRUNCATE cards, reviews, journal RESTART IDENTITY CASCADE")
    card_ids = {c["id"] for c in rows["cards"]}
    orphans = [r for r in rows["reviews"] if r["card_id"] not in card_ids]
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO cards (id, front, back, note, category, source, created_at, ease, interval_days,"
            " reps, lapses, due, introduced_on) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (c["id"], c["front"], c["back"], c["note"], c["category"], c["source"], as_datetime(c["created_at"]),
                 c["ease"], c["interval_days"], c["reps"], c["lapses"], as_date(c["due"]), as_date(c["introduced_on"]))
                for c in rows["cards"]
            ],
        )
        cur.executemany(
            "INSERT INTO reviews (id, card_id, grade, reviewed_on, reviewed_at) VALUES (%s, %s, %s, %s, %s)",
            [
                (r["id"], r["card_id"], r["grade"], as_date(r["reviewed_on"]), as_datetime(r["reviewed_at"]))
                for r in rows["reviews"]
                if r["card_id"] in card_ids
            ],
        )
        cur.executemany(
            "INSERT INTO journal (id, text, correction, created_at) VALUES (%s, %s, %s, %s)",
            [
                (j["id"], j["text"], Jsonb(json.loads(j["correction"])) if j.get("correction") else None,
                 as_datetime(j["created_at"]))
                for j in rows["journal"]
            ],
        )
    # Os próximos cards criados continuam a numeração de onde o SQLite parou.
    for table in TABLES:
        conn.execute(
            sql.SQL(
                "SELECT setval(pg_get_serial_sequence({t}, 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {i}"
            ).format(t=sql.Literal(table), i=sql.Identifier(table))
        )
    return len(orphans)


def main() -> None:
    parser = argparse.ArgumentParser(description="Copia os dados do SQLite antigo pro PostgreSQL.")
    parser.add_argument("--profile", help="perfil (data/profiles/NOME/english.db -> banco english_ze_NOME)")
    parser.add_argument("--sqlite", type=Path, help="outro arquivo SQLite de origem")
    parser.add_argument("--substituir", action="store_true", help="apaga os dados que já estiverem no PostgreSQL")
    args = parser.parse_args()

    source = ROOT / "data" / "english.db"
    if args.profile:
        profile_dir = ROOT / "data" / "profiles" / args.profile
        source = profile_dir / "english.db"
        load_env_file(profile_dir / ".env")
        profile_has_database = "DATABASE_URL" in os.environ
    load_env_file()
    url = db.database_url()
    if args.profile and not profile_has_database:
        url = db.with_database(url, db.profile_database(args.profile))
    source = args.sqlite or source
    if not source.exists():
        raise SystemExit(f"Não achei o arquivo SQLite: {source}")
    target = conninfo_to_dict(url).get("dbname")

    rows = read_sqlite(source)
    db._create_database_if_missing(url)
    with psycopg.connect(url, row_factory=dict_row) as conn:
        db.migrate(conn)
        if not args.substituir and not only_fresh_seed(conn):
            raise SystemExit(
                f"O banco {target} já tem dados de estudo. Pra apagar e copiar de novo, use --substituir."
            )
        orphans = copy(conn, rows)
        conn.commit()
        after = summary_postgres(conn)

    before = summary_sqlite(rows)
    if orphans:
        before["revisões"] -= orphans
    print(f"De: {source}\nPara: banco {target}\n")
    print(f"{'':26}{'SQLite':>8}{'PostgreSQL':>12}")
    ok = True
    for key, value in before.items():
        match = value == after[key]
        ok &= match
        print(f"{key:26}{value:>8}{after[key]:>12}  {'ok' if match else 'DIFERENTE'}")
    if orphans:
        print(f"\n{orphans} revisões de cards que não existem mais foram ignoradas.")
    print("\nTudo copiado e conferido." if ok else "\nATENÇÃO: alguma contagem não bateu.")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
