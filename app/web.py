"""Serve o app React já compilado (web/dist).

Arquivos que existem são entregues direto; qualquer outro endereço (/vault, /stats...)
devolve o index.html e o React decide qual tela mostrar.
"""

import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .config import ROOT

NOT_BUILT_PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>English Zé</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 560px; margin: 60px auto; padding: 0 20px; line-height: 1.5">
<h1>O app ainda não foi gerado</h1>
<p>Abra pelo <strong>English Ze.bat</strong> (ele gera sozinho) ou rode:</p>
<pre style="background: #f2f2f7; padding: 12px; border-radius: 10px">cd web
npm install
npm run build</pre>
</body></html>"""


NOT_BUILT_CSP = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"


def dist_dir() -> Path:
    return Path(os.environ.get("ENGLISH_ZE_WEB_DIST", ROOT / "web" / "dist")).resolve()


def serve(path: str):
    dist = dist_dir()
    index = dist / "index.html"
    if not index.is_file():
        # Página simples com estilo embutido: ganha uma política própria, ainda mais fechada (sem scripts).
        return HTMLResponse(NOT_BUILT_PAGE, status_code=503, headers={"Content-Security-Policy": NOT_BUILT_CSP})

    if path:
        candidate = (dist / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist):
            # Arquivos de assets/ têm o hash no nome: podem ficar em cache pra sempre.
            in_assets = candidate.parent == dist / "assets"
            cache = "public, max-age=31536000, immutable" if in_assets else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})
        if path.startswith(("api/", "assets/")) or "." in Path(path).name:
            raise HTTPException(404, "Não encontrado")

    # Endereço de tela: o React cuida. Sem cache, pra pegar versões novas do app na hora.
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
