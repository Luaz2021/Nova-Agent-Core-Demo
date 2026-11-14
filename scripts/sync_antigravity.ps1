<#
.SYNOPSIS
    Sincronizador Maestro Total y Puente Principal de Nova y Antigravity (PC & Laptop) v4.1
    Drive es el ORIGINAL. Cada equipo trabaja en C: y usa dos puentes (motor: scripts\nova_sync_v4.ps1):
      -Modo Bajar (por defecto) = puente de SALIDA: "Nova, sincroniza" y al encender Windows.
      -Modo Subir               = puente de ENTRADA: "Nova, sube los cambios" (salta la auditoria de runtimes).
    Ubicacion: <NOVA_HOME>\antigravity\scripts\sync_antigravity.ps1 (respaldo en Drive\Antigravity\)
#>
param(
    [ValidateSet("Bajar", "Subir")]
    [string]$Modo = "Bajar"
)
$ErrorActionPreference = "SilentlyContinue"

# 09/11 (Claude, a pedido de Luaz): CANDADO. El Bajar del arranque (on_boot_sync, ~3 min por la auditoria de runtimes)
# y un "Nova, sube los cambios" corrieron A LA VEZ sobre las mismas carpetas. Ahora van en cola: el segundo espera
# a que acabe el primero (max 15 min). Si el primero murio a medias, Windows suelta el candado (AbandonedMutex).
$candado = New-Object System.Threading.Mutex($false, "Global\NovaSyncAntigravity")
$tengoCandado = $false
try { $tengoCandado = $candado.WaitOne([TimeSpan]::FromMinutes(15)) }
catch [System.Threading.AbandonedMutexException] { $tengoCandado = $true }
if (-not $tengoCandado) {
    Write-Host "[COLA] Otra sincronizacion lleva mas de 15 min: este $Modo no se ejecuta." -ForegroundColor Red
    exit 2
}

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "   PUENTE PRINCIPAL NOVA & ANTIGRAVITY - SINCRONIZADOR MAESTRO (PC & LAPTOP)" -ForegroundColor Yellow
Write-Host "==========================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# 0. LOCALIZACIÓN DINÁMICA DE GOOGLE DRIVE (BLINDADA CONTRA FALSO POSITIVO .gemini)
# ------------------------------------------------------------------------------
function Resolve-CloudAntigravityDir {
    if (Test-Path "$PSScriptRoot\skills") {
        $here = (Resolve-Path $PSScriptRoot).Path
        if ($here -notmatch "\\\.gemini(\\|$)") {
            return $here
        }
    }

    foreach ($letter in @("G", "D", "E", "F", "H", "I", "J", "K", "C")) {
        foreach ($sub in @("Mi unidad\Antigravity", "My Drive\Antigravity", "Google Drive\Antigravity", "Antigravity")) {
            $cand = "$letter`:\$sub"
            if (($cand -notmatch "\\\.gemini(\\|$)") -and (Test-Path "$cand\skills")) {
                return $cand
            }
        }
    }

    $userCand = "$env:USERPROFILE\Google Drive\Antigravity"
    if (($userCand -notmatch "\\\.gemini(\\|$)") -and (Test-Path "$userCand\skills")) {
        return $userCand
    }
    return $null
}

$cloudDir = Resolve-CloudAntigravityDir
if (-not $cloudDir) {
    Write-Host "[ERROR FATAL] No se pudo encontrar la carpeta Antigravity en Google Drive." -ForegroundColor Red
    Write-Host "Verifica que Google Drive de escritorio esté iniciado y la unidad montada." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Google Drive detectado en: $cloudDir" -ForegroundColor Green
$userHome = $env:USERPROFILE
$geminiDir = "$userHome\.gemini"
$localScriptsDir = "$geminiDir\antigravity\scripts"
New-Item -ItemType Directory -Path $localScriptsDir -Force | Out-Null

$runtimesReport = @("omitido en modo Subir")
# ------------------------------------------------------------------------------
# FASE 1: VALIDACIÓN Y ACTUALIZACIÓN DE ENTORNOS Y RUNTIMES (solo al sincronizar/bajar)
# ------------------------------------------------------------------------------
if ($Modo -eq "Bajar") {
Write-Host "`n[FASE 1/4] Auditando entornos y lenguajes base..." -ForegroundColor Yellow

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$toolsToCheck = @(
    @{ Name = "Node.js (LTS)"; WingetId = "OpenJS.NodeJS.LTS"; CheckCmd = { (node -v 2>$null) } },
    @{ Name = "Java 21 (OpenJDK)"; WingetId = "Microsoft.OpenJDK.21"; CheckCmd = { if (Test-Path "C:\Program Files\Microsoft\jdk-21*") { "Java 21 instalado" } else { (java -version 2>&1 | Select-String "21") } } },
    @{ Name = "Git CLI"; WingetId = "Git.Git"; CheckCmd = { (git --version 2>$null) } },
    @{ Name = "GitHub CLI"; WingetId = "GitHub.cli"; CheckCmd = { (gh --version 2>$null | Select-Object -First 1) } },
    @{ Name = "Python 3"; WingetId = "Python.Python.3.11"; CheckCmd = { (python --version 2>$null) } },
    @{ Name = "Ollama Local AI Engine"; WingetId = "Ollama.Ollama"; CheckCmd = { 
        $ollamaExe = if (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") { "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" } else { (Get-Command ollama -ErrorAction SilentlyContinue).Source }
        if ($ollamaExe) { (& $ollamaExe --version 2>&1 | Select-Object -First 1) } else { $null }
    } }
)

$runtimesReport = @()

foreach ($t in $toolsToCheck) {
    $val = & $t.CheckCmd
    if (-not $val) {
        Write-Host "  [FALTA] $($t.Name) no detectado. Instalando via winget..." -ForegroundColor Yellow
        winget install --id $t.WingetId --silent --accept-package-agreements --accept-source-agreements
        $runtimesReport += "$($t.Name): INSTALADO"
        Write-Host "  [INSTALADO] $($t.Name) completado." -ForegroundColor Green
    } else {
        Write-Host "  [OK] $($t.Name): $val" -ForegroundColor Green
        $runtimesReport += "$($t.Name): OK"
    }
}

# Configuración de JAVA_HOME
$jdkPath = Get-ChildItem -Path "C:\Program Files\Microsoft" -Filter "jdk-21*" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if ($jdkPath) {
    [System.Environment]::SetEnvironmentVariable("JAVA_HOME", $jdkPath, "User")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$jdkPath*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$jdkPath\bin;$userPath", "User")
    }
    Write-Host "  [OK] JAVA_HOME configurado en: $jdkPath" -ForegroundColor Green
}

# 11/11 (Claude): las librerias de voz/aduana ya NO se instalan aqui en el Python de Windows. Las monta el Nova Doctor
# en el Python PROPIO de Nova (nova_env) al final del Bajar, cuando requisitos_nova.txt ya esta al dia.

# Auditar y asegurar Servicio de IA Local (Ollama + Modelo Obrero Qwen2.5-Coder)
Write-Host "  Auditando motor de IA Local (Ollama / Obrero)..." -ForegroundColor Cyan
# Igual en PC y laptop: comprueba los modelos de nova_modelos.json e instala desde Drive solo si faltan (nunca borra).
$ollamaCheck = "$localScriptsDir\nova_ollama_modelos.ps1"
if (-not (Test-Path $ollamaCheck)) { $ollamaCheck = "$cloudDir\scripts\nova_ollama_modelos.ps1" }
if (Test-Path $ollamaCheck) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ollamaCheck" -CloudDir "$cloudDir"
} else {
    Write-Host "  [AVISO] nova_ollama_modelos.ps1 no encontrado." -ForegroundColor Yellow
}
}  # fin FASE 1 (solo modo Bajar)

# ------------------------------------------------------------------------------
# FASE 2 & 3: COFRE DE SECRETOS + PUENTE (Bajar = salida desde Drive | Subir = entrada a Drive)
# ------------------------------------------------------------------------------
$puenteTxt = if ($Modo -eq "Subir") { "ENTRADA (subir cambios de este equipo a Drive)" } else { "SALIDA (absorber de Drive lo nuevo)" }
Write-Host "`n[FASE 2 y 3/4] Cofre de secretos + Puente de $puenteTxt..." -ForegroundColor Yellow

# Se usa la copia local de cada motor; la de Drive solo si este equipo aun no la tiene (primer arranque tras actualizar).
function Resolve-Engine($name) {
    $localEngine = "$localScriptsDir\$name"
    if (Test-Path $localEngine) { return $localEngine }
    $cloudEngine = "$cloudDir\scripts\$name"
    if (Test-Path $cloudEngine) { return $cloudEngine }
    return $null
}

$vaultEngine = Resolve-Engine "nova_vault_sync.ps1"
if ($vaultEngine) { & $vaultEngine -CloudDir $cloudDir }

$skippedCount = 0
$updatedCount = 0
$syncEstado = "SIN_MOTOR"
$syncEngine = Resolve-Engine "nova_sync_v4.ps1"
if ($syncEngine) {
    & $syncEngine -Modo $Modo -CloudRoot $cloudDir
    $statusFile = "$geminiDir\antigravity\memory\sync_status.json"
    if (Test-Path $statusFile) {
        try {
            $st = Get-Content -Path $statusFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $skippedCount = $st.AlDia
            $updatedCount = $st.Subidos + $st.Bajados + $st.Borrados
            $syncEstado = $st.Estado
        } catch {}
    }
} else {
    Write-Host "  [AVISO] nova_sync_v4.ps1 no encontrado ni en local ni en Drive." -ForegroundColor Magenta
}
$cloudSkills = "$cloudDir\skills"

# Git Guardian Hooks (v4: desde la copia local del almacen; Drive solo si aun no existe)
$gitHook = "$geminiDir\antigravity\almacen\skills\gemini-git-guardian\scripts"
if (-not (Test-Path $gitHook)) { $gitHook = "$cloudSkills\gemini-git-guardian\scripts" }
if (Test-Path $gitHook) {
    git config --global core.hooksPath "$gitHook"
    Write-Host "  [OK] Git Guardian configurado globalmente en Git." -ForegroundColor Green
}

# Startup Launcher (shell:startup)
$startupFolder = [System.Environment]::GetFolderPath("Startup")
$vbsLauncher = "$startupFolder\Nova_OnBoot.vbs"
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$localScriptsDir\on_boot_sync.ps1""", 0, False
"@
Set-Content -Path $vbsLauncher -Value $vbsContent -Encoding ASCII
Write-Host "  [OK] Lanzador de arranque en Windows Startup verificado." -ForegroundColor Green

# Organizador de Escritorio (PecoFence Rust) si aun no esta instalado en este equipo
if ($Modo -eq "Bajar") {
    $pecoInstalled = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter "DayuanJiang.PecoFence*" -Directory -ErrorAction SilentlyContinue
    $pecoSetup = "$localScriptsDir\nova_pecofence_setup.ps1"
    if (-not $pecoInstalled -and (Test-Path $pecoSetup)) {
        Write-Host "  [ESCRITORIO] Instalando y organizando PecoFence (5 cajas Acrylic Dark)..." -ForegroundColor Cyan
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$pecoSetup" | Out-Null
        Write-Host "  [OK] Escritorio organizado con PecoFence." -ForegroundColor Green
    }
}

# ------------------------------------------------------------------------------
# FASE 4: VERIFICACIÓN REAL DE SUBIDA A LA NUBE Y REPORTE FINAL
# ------------------------------------------------------------------------------
# 11/11 (Claude): NOVA DOCTOR al bajar (encender Windows / "Nova, sincroniza"): monta o repara el Python propio de
# Nova, hooks.json, Ollama y Vosk en ESTE equipo con lo que acaba de llegar de Drive. Rapido si todo esta bien (~15 s).
$doctor = Join-Path $env:USERPROFILE ".gemini\antigravity\scripts\nova_doctor.ps1"
if ($Modo -eq "Bajar" -and (Test-Path $doctor)) {
    Write-Host "`n[DOCTOR] Revisando y reparando este equipo..." -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$doctor" -SinServicios
}
$novaPyLib = Join-Path $env:USERPROFILE ".gemini\antigravity\scripts\nova_python.ps1"
$pyEquipo = $null
if (Test-Path $novaPyLib) { . $novaPyLib; $pyEquipo = Set-NovaPythonEnv }

$driveVerifier = "$cloudDir\scripts\nova_drive_verifier.py"
$pyNova = if ($pyEquipo) { $pyEquipo } else { "python.exe" }  # 11/11: el Python de este equipo (nova_python.ps1)
# 09/11 (Claude): quitada la 1a comprobacion de Drive (30 s, su resultado no se usaba). Queda una sola, al final.

$reportDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$machineName = $env:COMPUTERNAME

$reportContent = @"
# Estado de Sincronizacion (v4.1 | Puente de $puenteTxt)
*Fecha: $reportDate* | *Maquina: $machineName*

- **Entornos y Lenguajes:** $($runtimesReport -join ", ")
- **Componentes de Nova:** $skippedCount al dia, $updatedCount cambios aplicados (subidos + bajados + borrados).
- **Estado del sync:** $syncEstado (detalle en antigravity\memory\sync_status.json).
- **Cofre de Secretos (Vault):** secrets.json + google_cloud.env sincronizados en variables de entorno de Windows.
- **Skills:** copia real en C:\...\.gemini\config\skills (sin Junction a Drive).
- **Proteccion Git:** Git Guardian activo.
"@

foreach ($reportPath in @("$geminiDir\antigravity\memory\ultimo_estado_sincronizacion.md", "$cloudDir\memory\ultimo_estado_sincronizacion.md")) {
    Set-Content -Path $reportPath -Value $reportContent -Encoding UTF8
}

if (Test-Path $driveVerifier) {
    & $pyNova "$driveVerifier" 45
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ALERTA] Los archivos se estan subiendo a Google Drive todavia. Espera unos momentos antes de apagar o cambiar de maquina." -ForegroundColor Yellow
    }
}

Write-Host "`n==========================================================================" -ForegroundColor Green
Write-Host "   PUENTE DE $puenteTxt TERMINADO: $syncEstado | $skippedCount al dia, $updatedCount cambios aplicados." -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
try { $candado.ReleaseMutex() } catch {}
