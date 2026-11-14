<#
.SYNOPSIS
    Sincronizador y Gestor de Modelos Ollama para Nova (PC & Laptop) v2026.
    1. Purga primero los modelos locales obsoletos (v4, v1 y versiones previas).
    2. Instala los modelos oficiales vigentes (qwen3.5:9b y blaifa/InternVL3_5:8b) vía ollama pull.
    3. Configuración centralizada en: nova_modelos.json.
#>
param([string]$CloudDir)

$ErrorActionPreference = "SilentlyContinue"

$cfgPath = Join-Path $PSScriptRoot "nova_modelos.json"
$cfg = if (Test-Path $cfgPath) { Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
$coder = if ($cfg.coder) { $cfg.coder } else { "qwen3.5:9b" }
$vl = if ($cfg.vl) { $cfg.vl } else { "blaifa/InternVL3_5:8b" }
$obsoletos = if ($cfg.modelos_obsoletos) { @($cfg.modelos_obsoletos) } else { @("qwen2.5-coder-nova2026:v4", "qwen2.5-vl-nova2026:v1") }

$ollama = if (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") { 
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" 
} else { 
    try { (Get-Command ollama -ErrorAction Stop).Source } catch { $null } 
}

if (-not $ollama) {
    Write-Host "  [AVISO] Ollama no esta instalado o no esta en el PATH." -ForegroundColor Yellow
    exit 1
}

# 1. Asegurar que el servicio de Ollama este respondiendo
$up = try { (Invoke-RestMethod -Uri "http://127.0.0.1:11434/" -TimeoutSec 3) -eq "Ollama is running" } catch { $false }
if (-not $up) {
    Write-Host "  Iniciando Ollama en segundo plano (puerto 11434)..." -ForegroundColor Yellow
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

# 2. FASE DE LIMPIEZA: Eliminar modelos obsoletos primero
$lista = (& $ollama list 2>$null) -join "`n"
foreach ($obs in $obsoletos) {
    if ($lista -match [regex]::Escape($obs)) {
        Write-Host "  [LIMPIEZA] Eliminando modelo local obsoleto: $obs ..." -ForegroundColor Yellow
        & $ollama rm $obs
    }
}

# Buscar patrones residuales de modelos custom antiguos
$lineas = (& $ollama list 2>$null)
foreach ($linea in $lineas) {
    $partes = $linea -split "\s+"
    if ($partes.Count -gt 0) {
        $tag = $partes[0].Trim()
        if (($tag -like "qwen2.5-coder-nova2026*") -or ($tag -like "qwen2.5-vl-nova2026*")) {
            Write-Host "  [LIMPIEZA] Purgando version custom previa: $tag ..." -ForegroundColor Yellow
            & $ollama rm $tag
        }
    }
}

# 3. FASE DE INSTALACION: Descargar modelos oficiales faltantes
$listaActual = (& $ollama list 2>$null) -join "`n"
$modelosRequeridos = @($coder, $vl)

foreach ($mod in $modelosRequeridos) {
    if ($listaActual -notmatch [regex]::Escape($mod)) {
        Write-Host "  [DESPLIEGUE] Descargando modelo oficial $mod desde el registro de Ollama..." -ForegroundColor Cyan
        & $ollama pull $mod
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR] Fallo al descargar $mod vía ollama pull." -ForegroundColor Red
        } else {
            Write-Host "  [OK] Modelo $mod instalado correctamente." -ForegroundColor Green
        }
    }
}

# 4. Verificación final de estado
$listaFinal = (& $ollama list 2>$null) -join "`n"
$faltan = @($coder, $vl | Where-Object { $listaFinal -notmatch [regex]::Escape($_) })

if ($faltan.Count -eq 0) {
    Write-Host "  [OK] Modelos Nova activos en Ollama: $coder + $vl" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  [AVISO] Faltan por desplegar: $($faltan -join ', ')" -ForegroundColor Yellow
    exit 1
}
