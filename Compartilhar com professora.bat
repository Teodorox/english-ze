@echo off
chcp 65001 > nul
set PYTHONUTF8=1
title English Ze - acesso da professora
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python nao encontrado. Siga a secao "Como rodar" do README.
  pause
  exit /b 1
)

echo ============================================================
echo   English Ze - acesso da professora
echo   Deixe esta janela ABERTA enquanto ela estiver usando.
echo   Para encerrar, feche a janela.
echo ============================================================
echo.

".venv\Scripts\python.exe" run.py --profile professora --tunnel --port 8100

echo.
echo O servidor parou. Se apareceu algum erro acima, mande para o Claude.
pause
