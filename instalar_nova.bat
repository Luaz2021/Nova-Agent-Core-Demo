@echo off
setlocal enabledelayedexpansion
title Instalador Oficial de Nova Agent Core

echo ==========================================================
echo    INSTALADOR OFICIAL EN 1 CLIC - NOVA AGENT
echo    Copiloto Tecnico Senior ^& Arquitectura de Software
echo ==========================================================
echo.

REM 1. Comprobar si Antigravity ya esta instalado en el sistema
set "ANTIGRAVITY_FOUND=0"
if exist "%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe" set "ANTIGRAVITY_FOUND=1"
if exist "%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe" set "ANTIGRAVITY_FOUND=1"

where agy >nul 2>&1
if !errorlevel! equ 0 set "ANTIGRAVITY_FOUND=1"

if "!ANTIGRAVITY_FOUND!"=="1" (
    echo [OK] Google Antigravity detectado en el equipo.
    goto :CONFIGURAR_NOVA
)

echo [AVISO] No se detecto Google Antigravity instalado en tu equipo.
echo Antigravity es el entorno nativo de Google necesario para que Nova opere.
echo.
set /p INSTALAR_AGY="Deseas descargar e instalar Google Antigravity oficial ahora? (s/n) [s]: "
if /i "!INSTALAR_AGY!"=="n" (
    echo [!] Se continuara con la instalacion de skills y reglas, pero necesitaras
    echo     instalar Antigravity manualmente desde: https://antigravity.google/
    goto :CONFIGURAR_NOVA
)

echo.
echo [INFO] Descargando e instalando Google Antigravity oficial...
where winget >nul 2>&1
if !errorlevel! equ 0 (
    echo [INFO] Instalando mediante Windows Package Manager (winget)...
    winget install Google.Antigravity --accept-source-agreements --accept-package-agreements
    if !errorlevel! equ 0 (
        echo [OK] Google Antigravity instalado correctamente con winget.
        goto :CONFIGURAR_NOVA
    )
)

echo [INFO] Descargando instalador directo oficial de Google Antigravity...
set "TEMP_INSTALLER=%TEMP%\AntigravitySetup.exe"
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://storage.googleapis.com/antigravity-public/antigravity-hub/2.26.0-6546645232517120/windows-x64/Antigravity-x64.exe' -OutFile '$env:TEMP_INSTALLER'"
if exist "%TEMP_INSTALLER%" (
    echo [INFO] Ejecutando instalador de Google Antigravity...
    start /wait "" "%TEMP_INSTALLER%"
    echo [OK] Instalador finalizado.
) else (
    echo [ERROR] No se pudo descargar automaticamente.
    echo Por favor descargalo desde: https://antigravity.google/
)

:CONFIGURAR_NOVA
echo.
echo [INFO] Iniciando configuracion interactiva de Nova Agent...
powershell -ExecutionPolicy Bypass -File "%~dp0adapters\windows\install.ps1"

echo.
echo Presiona cualquier tecla para salir...
pause >nul
