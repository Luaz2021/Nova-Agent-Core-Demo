@echo off
chcp 65001 >nul
cd /d "%~dp0"
if defined NOVA_PYTHON (set "PY=%NOVA_PYTHON%") else (set "PY=python")
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
echo ============================================================
echo  PASO 2 - CREAR la base del clon (sin IA, 2-4 minutos)
echo ============================================================
"%PY%" -u crear.py
echo.
echo  Terminado. Siguiente: 3_VERIFICAR.bat
pause
