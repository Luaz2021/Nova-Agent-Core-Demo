@echo off
chcp 65001 >nul
title Nova Voz Live
set PYTHONIOENCODING=utf-8
"%USERPROFILE%\.gemini\nova_env\Scripts\python.exe" "%~dp0nova_voz_live.py" %*
pause
