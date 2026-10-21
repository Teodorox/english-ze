@echo off
chcp 65001 > nul
set PYTHONUTF8=1
title English Zé
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python nao encontrado. Siga a secao "Como rodar" do README.
  pause
  exit /b 1
)

echo ============================================================
echo   English Zé - o navegador vai abrir sozinho.
echo   Deixe esta janela aberta enquanto estiver estudando.
echo ============================================================
echo.

".venv\Scripts\python.exe" run.py

echo.
echo O servidor parou. Se apareceu algum erro acima, mande para o Claude.
pause
