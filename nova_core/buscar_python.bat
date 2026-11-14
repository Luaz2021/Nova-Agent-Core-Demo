@echo off
rem 11/11 (Claude): deja en NOVA_PY el Python de ESTE equipo (laptop 3.14, PC 3.13/3.11). Lo usan hook_tool.bat y hook_turno.bat.
rem Mismo orden que antigravity\scripts\nova_python.ps1. Nada de rutas de un equipo escritas a mano.
set "NOVA_PY="
if exist "%USERPROFILE%\.gemini\nova_env\.huella_nova" if exist "%USERPROFILE%\.gemini\nova_env\Scripts\python.exe" set "NOVA_PY=%USERPROFILE%\.gemini\nova_env\Scripts\python.exe"
if defined NOVA_PY goto :eof
if defined NOVA_PYTHON if exist "%NOVA_PYTHON%" set "NOVA_PY=%NOVA_PYTHON%"
if not defined NOVA_PY if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "NOVA_PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not defined NOVA_PY if exist "%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe" set "NOVA_PY=%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe"
if not defined NOVA_PY if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "NOVA_PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined NOVA_PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "NOVA_PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined NOVA_PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "NOVA_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined NOVA_PY if exist "C:\Python314\python.exe" set "NOVA_PY=C:\Python314\python.exe"
if not defined NOVA_PY if exist "C:\Python313\python.exe" set "NOVA_PY=C:\Python313\python.exe"
if not defined NOVA_PY if exist "C:\Python311\python.exe" set "NOVA_PY=C:\Python311\python.exe"
if not defined NOVA_PY set "NOVA_PY=python.exe"
