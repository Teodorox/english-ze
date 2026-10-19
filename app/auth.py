"""Login simples por senha (o app tem um único usuário: você).

A senha fica em ENGLISH_ZE_PASSWORD no .env. Depois do login, o navegador guarda
um cookie assinado com HMAC que vale por SESSION_DAYS. Trocar a senha invalida
todas as sessões abertas, porque a senha faz parte da chave da assinatura.
"""

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from . import db

COOKIE_NAME = "ez_session"
SESSION_DAYS = 30
SESSION_SECONDS = SESSION_DAYS * 24 * 60 * 60


def password() -> str:
    return os.environ.get("ENGLISH_ZE_PASSWORD", "")


def enabled() -> bool:
    return bool(password())


def _secret_file() -> Path:
    return db.db_path().parent / "secret.key"


def _secret() -> bytes:
    path = _secret_file()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip().encode()


def _sign(message: str) -> str:
    key = _secret() + password().encode()
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()


def check_password(attempt: str) -> bool:
    return enabled() and hmac.compare_digest(attempt.encode(), password().encode())


def make_token(now: float | None = None) -> str:
    expires = str(int((now or time.time()) + SESSION_SECONDS))
    return f"{expires}.{_sign(expires)}"


def valid_token(token: str, now: float | None = None) -> bool:
    expires, _, signature = token.partition(".")
    if not expires.isdigit() or not signature:
        return False
    return int(expires) > (now or time.time()) and hmac.compare_digest(signature, _sign(expires))


class LoginLimiter:
    """Bloqueia um IP por alguns minutos depois de várias senhas erradas seguidas."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window]
        self._failures[key] = recent
        return recent

    def blocked(self, key: str, now: float | None = None) -> bool:
        return len(self._recent(key, now or time.time())) >= self.max_failures

    def fail(self, key: str, now: float | None = None) -> None:
        now = now or time.time()
        self._recent(key, now).append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
