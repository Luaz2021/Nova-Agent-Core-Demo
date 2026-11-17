@echo off
setlocal enabledelayedexpansion
title Instalador Oficial de Nova Agent Core

echo ==========================================================
echo    INSTALADOR OFICIAL EN 1 CLIC - NOVA AGENT
echo    Copiloto Tecnico Senior ^& Arquitectura de Software
echo ==========================================================
echo.

REM 1. Antigravity: Nova NO lo instala (v3.2). Solo mira si esta y, si no, da el enlace oficial.
REM    (Antes intentaba winget y un .exe con version fija: fallaba en muchos equipos y caducaba con cada version.)
set "ANTIGRAVITY_FOUND=0"
if exist "%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe" set "ANTIGRAVITY_FOUND=1"
if exist "%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe" set "ANTIGRAVITY_FOUND=1"
if exist "%USERPROFILE%\.gemini\antigravity" set "ANTIGRAVITY_FOUND=1"
where agy >nul 2>&1
if !errorlevel! equ 0 set "ANTIGRAVITY_FOUND=1"

if "!ANTIGRAVITY_FOUND!"=="1" (
    echo [OK] Google Antigravity detectado en el equipo.
) else (
    echo [AVISO] No encuentro Google Antigravity en este equipo. Nova funciona DENTRO de Antigravity.
    echo         1. Descargalo e instalalo desde la pagina oficial:  https://antigravity.google/
    echo         2. Abrelo una vez, inicia sesion y cierralo.
    echo         3. Vuelve a ejecutar este instalador.
    echo.
    set /p SEGUIR="Instalo Nova igualmente ahora (quedara lista para cuando tengas Antigravity)? (s/n) [s]: "
    if /i "!SEGUIR!"=="n" (
        echo Hasta luego. Cuando tengas Antigravity, vuelve a ejecutar este instalador.
        pause
        exit /b 0
    )
)

:DESCARGAR_CORE
set "INSTALL_SCRIPT=%~dp0adapters\windows\install.ps1"
if exist "!INSTALL_SCRIPT!" goto :CONFIGURAR_NOVA

set "NOVA_ROOT=%USERPROFILE%\.nova-agent"
set "NOVA_NUEVO=%USERPROFILE%\.nova-agent-nuevo"
echo.
echo [INFO] Descargando nucleo de Nova Agent en !NOVA_ROOT!...
if exist "!NOVA_NUEVO!" rmdir /s /q "!NOVA_NUEVO!"
where git >nul 2>&1
if !errorlevel! equ 0 (
    git clone --depth 1 https://github.com/Luaz2021/Nova-Agent-Core-Demo.git "!NOVA_NUEVO!" >nul 2>&1
) else (
    echo [INFO] No hay git: descargo el ZIP oficial de GitHub...
    powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $zip = Join-Path $env:TEMP 'nova_core.zip'; $tmp = Join-Path $env:TEMP 'nova_core_zip'; if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }; Invoke-WebRequest -Uri 'https://github.com/Luaz2021/Nova-Agent-Core-Demo/archive/refs/heads/main.zip' -OutFile $zip; Expand-Archive -Path $zip -DestinationPath $tmp -Force; Move-Item (Join-Path $tmp 'Nova-Agent-Core-Demo-main') $env:NOVA_NUEVO"
)
if not exist "!NOVA_NUEVO!\adapters\windows\install.ps1" (
    echo [ERROR] No se pudo descargar Nova ^(revisa tu conexion a internet o que GitHub este accesible^).
    echo         Tu instalacion anterior, si la habia, sigue intacta.
    pause
    exit /b 1
)
REM Solo ahora, con la descarga completa, se reemplaza la version anterior (las notas viven en .gemini, no aqui)
if exist "!NOVA_ROOT!" rmdir /s /q "!NOVA_ROOT!"
move "!NOVA_NUEVO!" "!NOVA_ROOT!" >nul
set "INSTALL_SCRIPT=!NOVA_ROOT!\adapters\windows\install.ps1"

:CONFIGURAR_NOVA
echo.
echo [INFO] Iniciando configuracion interactiva de Nova Agent...
powershell -NoProfile -ExecutionPolicy Bypass -File "!INSTALL_SCRIPT!"

echo.
echo Presiona cualquier tecla para salir...
pause >nul
