"""Administração das contas (rode no terminal deste computador).

    python contas.py convite --para "Professora Ana"   # cria um código de convite (uso único)
    python contas.py convites                          # lista os convites e quem usou
    python contas.py listar                            # lista as contas
    python contas.py redefinir-senha EMAIL             # nova senha pra quem esqueceu (desconecta os aparelhos)
    python contas.py assumir-dados EMAIL               # entrega os dados sem dono (da versão antiga) a essa conta
    python contas.py descricao EMAIL "texto"           # como a IA deve tratar essa pessoa na correção

As senhas são digitadas sem aparecer na tela e nunca passam por argumentos de linha de comando.
"""

import argparse
import getpass

import psycopg
from psycopg.rows import dict_row

from app import auth, db
from app.config import load_env_file


def connect() -> psycopg.Connection:
    load_env_file()
    db.init_db()  # aplica migrações pendentes
    return psycopg.connect(db.database_url(), row_factory=dict_row)


def find_user(conn: psycopg.Connection, email: str) -> dict:
    user = conn.execute(
        "SELECT id, email, name FROM users WHERE lower(email) = %s", (auth.normalize_email(email),)
    ).fetchone()
    if user is None:
        raise SystemExit(f"Nenhuma conta com o e-mail {email}.")
    return user


def create_invite(conn: psycopg.Connection, note: str) -> str:
    while True:
        code = auth.make_invite_code()
        if conn.execute(
            "INSERT INTO invites (code, note) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING code", (code, note)
        ).fetchone():
            return code


def adopt_orphans(conn: psycopg.Connection, user_id: int) -> dict[str, int]:
    """Entrega à conta os cards e o diário sem dono. A conta precisa estar intocada (só o deck inicial)."""
    orphans = conn.execute(
        "SELECT (SELECT COUNT(*) FROM cards WHERE user_id IS NULL) AS cards,"
        " (SELECT COUNT(*) FROM journal WHERE user_id IS NULL) AS journal"
    ).fetchone()
    if not orphans["cards"] and not orphans["journal"]:
        raise SystemExit("Não há dados sem dono pra entregar.")
    used = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM cards c JOIN reviews r ON r.card_id = c.id WHERE c.user_id = %s)"
        " OR EXISTS (SELECT 1 FROM journal WHERE user_id = %s)"
        " OR EXISTS (SELECT 1 FROM cards WHERE user_id = %s AND source != %s) AS v",
        (user_id, user_id, user_id, db.SEED_SOURCE),
    ).fetchone()["v"]
    if used:
        raise SystemExit("Essa conta já tem estudo próprio; os dados antigos só entram numa conta ainda intocada.")
    # O deck inicial que a conta ganhou no cadastro sai: os dados antigos já trazem o deck, com o progresso.
    conn.execute("DELETE FROM cards WHERE user_id = %s", (user_id,))
    conn.execute("UPDATE cards SET user_id = %s WHERE user_id IS NULL", (user_id,))
    conn.execute("UPDATE journal SET user_id = %s WHERE user_id IS NULL", (user_id,))
    return {"cards": orphans["cards"], "journal": orphans["journal"]}


def ask_new_password() -> str:
    first = getpass.getpass(f"Nova senha (mínimo {auth.PASSWORD_MIN} caracteres): ")
    if len(first) < auth.PASSWORD_MIN:
        raise SystemExit("Senha curta demais.")
    if getpass.getpass("Repita a senha: ") != first:
        raise SystemExit("As senhas não conferem.")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(description="Administração das contas do English Ze.")
    sub = parser.add_subparsers(dest="command", required=True)
    invite = sub.add_parser("convite", help="cria um código de convite")
    invite.add_argument("--para", default="", help="pra quem é (só pra você lembrar)")
    sub.add_parser("convites", help="lista os convites")
    sub.add_parser("listar", help="lista as contas")
    for name in ("redefinir-senha", "assumir-dados"):
        sub.add_parser(name).add_argument("email")
    learner = sub.add_parser("descricao", help="como a IA deve tratar a pessoa")
    learner.add_argument("email")
    learner.add_argument("texto")
    args = parser.parse_args()

    with connect() as conn:
        if args.command == "convite":
            code = create_invite(conn, args.para)
            print(f"Convite criado: {code}\nVale pra um cadastro só. Na tela de entrada, toque em 'Criar conta'.")

        elif args.command == "convites":
            rows = conn.execute(
                "SELECT i.code, i.note, i.created_at, u.email, i.used_at FROM invites i"
                " LEFT JOIN users u ON u.id = i.used_by ORDER BY i.created_at"
            ).fetchall()
            for r in rows:
                status = f"usado por {r['email']} em {r['used_at']:%d/%m %H:%M}" if r["used_at"] else "livre"
                print(f"{r['code']}  {r['note'] or '-':24} {status}")
            print(f"{len(rows)} convite(s).")

        elif args.command == "listar":
            rows = conn.execute(
                "SELECT u.email, u.name, u.created_at,"
                " (SELECT COUNT(*) FROM cards c WHERE c.user_id = u.id) AS cards,"
                " (SELECT MAX(r.reviewed_on) FROM reviews r JOIN cards c ON c.id = r.card_id WHERE c.user_id = u.id) AS last"
                " FROM users u ORDER BY u.id"
            ).fetchall()
            for r in rows:
                last = f"estudou em {r['last']:%d/%m}" if r["last"] else "ainda não estudou"
                print(f"{r['email']:32} {r['name']:20} {r['cards']:>4} cards  {last}")
            print(f"{len(rows)} conta(s).")

        elif args.command == "redefinir-senha":
            user = find_user(conn, args.email)
            auth.set_password(conn, user["id"], ask_new_password())
            ended = auth.end_other_sessions(conn, user["id"])
            print(f"Senha de {user['email']} trocada. {ended} aparelho(s) desconectado(s).")

        elif args.command == "assumir-dados":
            user = find_user(conn, args.email)
            moved = adopt_orphans(conn, user["id"])
            print(f"{moved['cards']} cards e {moved['journal']} entradas do diário agora são de {user['email']}.")

        elif args.command == "descricao":
            user = find_user(conn, args.email)
            conn.execute("UPDATE users SET learner = %s WHERE id = %s", (args.texto.strip(), user["id"]))
            print(f"Descrição de {user['email']} atualizada.")


if __name__ == "__main__":
    main()
