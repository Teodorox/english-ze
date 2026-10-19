import os

# Definidas antes de importar o app: o .env não sobrescreve variáveis existentes,
# então os testes nunca usam (nem gastam) a chave real e começam sem login.
os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
os.environ["ENGLISH_ZE_PASSWORD"] = ""
