@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
echo ============================================================
echo  CLONAR: analizar -^> crear -^> verificar, todo seguido
echo  (sin Qwen, en local; lo que quede bajo el 90%% lo arregla Claude)
echo ============================================================
set URL=
set /p URL="URL de la web (Enter = la de url.txt): "
python -u clonar.py %URL%
echo.
for /f "usebackq delims=" %%C in ("..\workspace\ultimo_analisis.txt") do start "" "%%C\construccion\revision.html"
pause
