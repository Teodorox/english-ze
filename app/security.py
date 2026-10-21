"""Proteções que valem pra toda requisição: cabeçalhos de segurança, origem e tamanho do corpo.

- Cabeçalhos: o navegador só roda scripts e estilos do próprio app (barra XSS), não deixa outro
  site embutir o app numa moldura (clickjacking) e não guarda dados da API em cache.
- Origem: ações que mudam dados (POST/PATCH/DELETE) só valem vindas do próprio app. Um site
  malicioso aberto noutra aba não consegue agir em nome de quem está logado (CSRF).
- Tamanho: corpo de requisição tem limite, pra ninguém travar o servidor mandando gigabytes.
"""

import json
import logging
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("english_ze.security")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
DEFAULT_BODY_LIMIT = 64 * 1024  # textos do app são bem menores; o diário tem no máximo 5000 caracteres

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob: data:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "microphone=(self), camera=(), geolocation=(), payment=(), usb=()",
}


def _hostname(netloc: str) -> str:
    return urlsplit(f"//{netloc}").hostname or ""


def same_origin(request: Request) -> bool:
    """True se a requisição veio de uma página do próprio app.

    Navegadores sempre mandam Origin em POST/PATCH/DELETE e um site não consegue falsificá-lo.
    Sem Origin não é um navegador (ex.: curl), e aí não há cookie de vítima pra abusar.
    """
    origin = request.headers.get("origin")
    if origin is None:
        return True
    if origin == "null":  # páginas em sandbox, arquivos locais, redirecionamentos estranhos
        return False
    origin_netloc = urlsplit(origin).netloc.lower()
    hosts = {h.lower() for h in (request.headers.get("host"), request.headers.get("x-forwarded-host")) if h}
    if origin_netloc in hosts:
        return True
    # Desenvolvimento: o Vite (localhost:5173) repassa pra API (127.0.0.1:8001), ambos neste computador.
    return _hostname(origin_netloc) in LOCAL_HOSTS and all(_hostname(h) in LOCAL_HOSTS for h in hosts)


async def protect(request: Request, call_next):
    """Middleware HTTP: confere a origem das ações e acrescenta os cabeçalhos de segurança."""
    path = request.url.path
    if request.method in UNSAFE_METHODS and path.startswith("/api/") and not same_origin(request):
        log.warning("Ação bloqueada: origem %s diferente do app (%s %s)", request.headers.get("origin"), request.method, path)
        return JSONResponse({"detail": "Origem não permitida"}, status_code=403)

    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.url.scheme == "https":
        # Daqui pra frente o navegador só abre o app por HTTPS (vale 1 ano).
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"  # dados pessoais não ficam em cache nenhum
    return response




class BodyLimitMiddleware:
    """Recusa corpos maiores que o limite, contando os bytes de verdade (não só o Content-Length).

    Lê o corpo inteiro antes de passar adiante (os limites são pequenos, então cabe na memória):
    quem manda em pedaços, sem dizer o tamanho, também é cortado assim que passa do limite.
    """

    def __init__(self, app, default: int = DEFAULT_BODY_LIMIT, per_path: dict[str, int] | None = None):
        self.app = app
        self.default = default
        self.per_path = per_path or {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in UNSAFE_METHODS:
            return await self.app(scope, receive, send)
        limit = self.per_path.get(scope["path"], self.default)

        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > limit):
            return await self._reject(send)

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body += message.get("body", b"")
            if len(body) > limit:
                return await self._reject(send)
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()  # depois do corpo, só espera o cliente desconectar

        await self.app(scope, replay, send)

    @staticmethod
    async def _reject(send):
        body = json.dumps({"detail": "Conteúdo grande demais"}).encode()
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})
