import os

import pytest

# Definidas antes de importar o app: o .env não sobrescreve variáveis existentes,
# então os testes nunca usam (nem gastam) a chave real e começam sem login.
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
os.environ["ENGLISH_ZE_PASSWORD"] = ""


@pytest.fixture(autouse=True)
def web_dist(tmp_path, monkeypatch):
    """Um 'app React compilado' mínimo, pra os testes não dependerem do npm run build."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    monkeypatch.setenv("ENGLISH_ZE_WEB_DIST", str(dist))
    return dist
