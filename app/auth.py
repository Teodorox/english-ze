"""Contas: cadastro com código de convite, login por e-mail e senha, uma sessão por aparelho.

As senhas ficam só como hash Argon2 (não dá pra recuperar a original). A sessão é um token
aleatório no cookie (que o JavaScript não lê); o banco guarda só o hash dele, então quem ler
o banco não consegue entrar na conta de ninguém.
"""

import hashlib
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request

from . import db

COOKIE_NAME = "ez_session"
SESSION_DAYS = 30
SESSION_SECONDS = SESSION_DAYS * 24 * 60 * 60
PASSWORD_MIN = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I, que se confundem

TIMEZONE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+){0,2}$")

# Senhas que aparecem no topo de todo vazamento (e variações óbvias do app). Recusadas no cadastro.
COMMON_PASSWORDS = {
    "12345678", "123456789", "1234567890", "87654321", "11111111", "00000000", "12341234", "11223344",
    "password", "password1", "password123", "passw0rd", "qwerty123", "qwertyui", "abc12345", "abcd1234",
    "iloveyou", "sunshine", "princess", "football", "baseball", "superman", "whatever", "trustno1",
    "senha123", "senha1234", "senha12345", "minhasenha", "mudar123", "trocar123", "admin123", "teste123",
    "brasil123", "flamengo", "corinthians", "palmeiras", "englishze", "english123", "ingles123",
}

_hasher = PasswordHasher()
# Login com e-mail que não existe também calcula um hash: assim o tempo de resposta não entrega quem tem conta.
_DUMMY_HASH = _hasher.hash("senha-de-ninguem")
# Cada hash Argon2 usa ~64 MB de memória: no máximo 4 ao mesmo tempo, pra uma enxurrada de
# logins não derrubar o servidor (os outros esperam a vez).
_hash_slots = threading.BoundedSemaphore(4)


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    timezone: str
    learner: str

    def today(self) -> date:
        return db.today(self.timezone)


# ---------- Senhas ----------

def hash_password(password: str) -> str:
    with _hash_slots:
        return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        with _hash_slots:
            return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def weak_password_reason(password: str, *, email: str = "", name: str = "") -> str:
    """Motivo pra recusar a senha, ou "" se ela serve."""
    lowered = password.lower()
    if len(password) < PASSWORD_MIN:
        return f"A senha precisa ter pelo menos {PASSWORD_MIN} caracteres"
    if lowered in COMMON_PASSWORDS or len(set(password)) <= 2:
        return "Essa senha é muito comum. Escolha uma menos óbvia"
    personal = {normalize_email(email), normalize_email(email).split("@")[0], name.strip().lower()} - {""}
    if lowered in personal:
        return "A senha não pode ser o seu nome ou e-mail"
    return ""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(EMAIL_PATTERN.match(email))


def valid_timezone(name: str) -> bool:
    if not TIMEZONE_PATTERN.match(name):  # só nomes como "America/Sao_Paulo": nada de caminhos de arquivo
        return False
    try:
        ZoneInfo(name)
    except Exception:  # nome inexistente ou malformado
        return False
    return True


def authenticate(email: str, password: str) -> int | None:
    """Id do usuário se e-mail e senha batem; None caso contrário (sem dizer qual dos dois errou)."""
    # O hash (lento de propósito) roda sem segurar conexão do banco.
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE lower(email) = %s", (normalize_email(email),)
        ).fetchone()
    if row is None:
        verify_password(_DUMMY_HASH, password)
        return None
    if not verify_password(row["password_hash"], password):
        return None
    if _hasher.check_needs_rehash(row["password_hash"]):  # parâmetros do Argon2 ficaram mais fortes
        new_hash = hash_password(password)
        with db.connect() as conn:
            conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, row["id"]))
    return row["id"]


def create_user(
    conn: psycopg.Connection, *, email: str, name: str, password: str, timezone: str, learner: str = ""
) -> int | None:
    """Cria a conta com o deck inicial. None se já existe uma conta com esse e-mail."""
    row = conn.execute(
        "INSERT INTO users (email, name, password_hash, timezone, learner) VALUES (%s, %s, %s, %s, %s)"
        " ON CONFLICT ((lower(email))) DO NOTHING RETURNING id",
        (normalize_email(email), name, hash_password(password), timezone, learner),
    ).fetchone()
    if row is None:
        return None
    db.seed_cards(conn, row["id"])
    return row["id"]


def set_password(conn: psycopg.Connection, user_id: int, password: str) -> None:
    conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(password), user_id))


# ---------- Sessões ----------

def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def create_session(conn: psycopg.Connection, user_id: int) -> str:
    conn.execute("DELETE FROM sessions WHERE user_id = %s AND expires_at <= now()", (user_id,))  # faxina
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, now() + make_interval(days => %s))",
        (_token_hash(token), user_id, SESSION_DAYS),
    )
    return token


def user_for_token(token: str) -> User | None:
    if not token:
        return None
    with db.connect() as conn:
        row = conn.execute(
            "SELECT u.id, u.email, u.name, u.timezone, u.learner FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token_hash = %s AND s.expires_at > now()",
            (_token_hash(token),),
        ).fetchone()
    return User(**row) if row else None


def end_session(token: str) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = %s", (_token_hash(token),))


def end_other_sessions(conn: psycopg.Connection, user_id: int, keep_token: str = "") -> int:
    """Desconecta os outros aparelhos (todos, se keep_token for vazio). Devolve quantos saíram."""
    return conn.execute(
        "DELETE FROM sessions WHERE user_id = %s AND token_hash != %s", (user_id, _token_hash(keep_token))
    ).rowcount


def session_token(request: Request) -> str:
    return request.cookies.get(COOKIE_NAME, "")


def current_user(request: Request) -> User:
    """Dependência do FastAPI: a rota só roda com login, e recebe quem está usando."""
    user = user_for_token(session_token(request))
    if user is None:
        raise HTTPException(401, "Faça login")
    return user


# ---------- Convites ----------

def make_invite_code() -> str:
    raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def normalize_invite(code: str) -> str:
    """Aceita o código com ou sem hífen, espaços e minúsculas."""
    raw = re.sub(r"[^A-Za-z0-9]", "", code).upper()
    return f"{raw[:4]}-{raw[4:]}" if len(raw) == 8 else raw


class LoginLimiter:
    """Bloqueia por alguns minutos depois de várias tentativas erradas seguidas (por IP e por e-mail).

    Fica no banco: vale depois de reiniciar o servidor e é o mesmo pra todos os servidores na nuvem.
    """

    def __init__(self, max_failures: int = 5, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window = window_seconds

    @staticmethod
    def _key(key: str) -> bytes:
        return hashlib.sha256(key.encode()).digest()  # não guarda IP nem e-mail legíveis

    def blocked(self, key: str, now: float | None = None) -> bool:
        now = now or time.time()
        with db.connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM auth_failures WHERE key = %s AND at > to_timestamp(%s)",
                (self._key(key), now - self.window),
            ).fetchone()["n"]
        return count >= self.max_failures

    def fail(self, key: str, now: float | None = None) -> None:
        now = now or time.time()
        with db.connect() as conn:
            conn.execute("INSERT INTO auth_failures (key, at) VALUES (%s, to_timestamp(%s))", (self._key(key), now))
            conn.execute("DELETE FROM auth_failures WHERE at < now() - interval '1 day'")  # faxina

    def reset(self, key: str) -> None:
        with db.connect() as conn:
            conn.execute("DELETE FROM auth_failures WHERE key = %s", (self._key(key),))
