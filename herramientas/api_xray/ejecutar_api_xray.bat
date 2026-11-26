@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE="
if defined NOVA_PYTHON if exist "%NOVA_PYTHON%" set "PY_EXE=%NOVA_PYTHON%"
if not defined PY_EXE if exist "<NOVA_HOME>\nova_env\Scripts\python.exe" set "PY_EXE=<NOVA_HOME>\nova_env\Scripts\python.exe"
if not defined PY_EXE set "PY_EXE=python"

"%PY_EXE%" "%~dp0api_xray.py" %*
if errorlevel 1 (
    echo.
    echo [Error] API X-Ray termino con codigo %errorlevel%.
    pause
)
endlocal
