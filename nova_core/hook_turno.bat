@echo off
rem 11/11 (Claude): vale para la laptop y el PC (antes llevaba las rutas del PC a mano).
call "%~dp0buscar_python.bat"
"%NOVA_PY%" "%~dp0nova_hook_turno.py" %*
