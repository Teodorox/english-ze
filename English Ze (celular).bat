@echo off
chcp 65001 > nul
set PYTHONUTF8=1
title English Ze - celular (Wi-Fi)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python nao encontrado. Siga a secao "Como rodar" do README.
  pause
  exit /b 1
)

echo ============================================================
echo   English Ze - acesso pelo celular no mesmo Wi-Fi
echo   Abra no celular o endereco https://... que aparece abaixo.
echo   Deixe esta janela aberta enquanto estiver usando.
echo ============================================================
echo.

".venv\Scripts\python.exe" run.py --lan

echo.
echo O servidor parou. Se apareceu algum erro acima, mande para o Claude.
pause
