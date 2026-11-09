@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
title VIGILANTE - Claude puede lanzar los scripts
echo ============================================================
echo  VIGILANTE: Claude lanza los scripts mientras no estas.
echo  Deja esta ventana abierta. Para pararlo, cierrala.
echo ============================================================
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1 || (echo Abriendo Ollama... & start "" /min ollama serve & timeout /t 6 >nul)
python -u vigilante.py
pause
