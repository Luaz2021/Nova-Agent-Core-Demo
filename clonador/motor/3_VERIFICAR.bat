@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
echo ============================================================
echo  PASO 3 - VERIFICAR: cada seccion contra la original
echo  (si no llega al 90%%, Qwen la repara hasta 3 veces)
echo ============================================================
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1 || (echo Abriendo Ollama... & start "" /min ollama serve & timeout /t 6 >nul)
set SOLO=
set /p N="Verificar solo las primeras N secciones? (numero, o Enter = todas): "
if not "%N%"=="" set SOLO=--solo=%N%
python -u verificar.py %SOLO%
echo.
echo ============================================================
echo  Terminado. Se abre la revision. Dile a Claude: "ya verifique"
echo  y arregla con codigo lo que quede en rojo.
echo ============================================================
for /f "usebackq delims=" %%C in ("pruebas_Qwen\ultimo_analisis.txt") do start "" "%%C\construccion\revision.html"
pause
