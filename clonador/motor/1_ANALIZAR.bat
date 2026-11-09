@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1
echo ============================================================
echo  PASO 1-3 - ANALIZAR UNA WEB (script + fotos + Qwen con ojos)
echo ============================================================
set URL=
if exist url.txt for /f "usebackq delims=" %%U in ("url.txt") do if not defined URL set URL=%%U
echo Web en url.txt: %URL%
set /p NUEVA="Pega otra URL o pulsa Enter para usar esa: "
if not "%NUEVA%"=="" set URL=%NUEVA%
echo %URL%> url.txt
echo.
echo Preparando Python (solo tarda la primera vez)...
python -m pip install -q playwright pillow numpy >nul 2>&1
python -m playwright install chromium >nul 2>&1
set OJOS=
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1 || (echo Abriendo Ollama... & start "" /min ollama serve & timeout /t 6 >nul)
ollama show qwen2.5vl:7b >nul 2>&1 || (echo Qwen con ojos no esta instalado: se analiza sin ojos. & set OJOS=--sin-ojos)
echo.
echo Analizando %URL% (3-6 minutos)...
python -u analizar.py "%URL%" %OJOS%
if errorlevel 2 (
  echo.
  echo  Esta web no se pudo analizar: mira el aviso de arriba y prueba otra.
  pause
  exit /b
)
echo.
echo ============================================================
echo  Terminado. Dile a Claude: "ya analice" 
echo  (los informes estan en pruebas_Qwen\)
echo ============================================================
pause
