# ==============================================================================
# INSTALADOR INTERACTIVO DE NOVA AGENT v3.0 - WINDOWS (POWERSHELL)
# Zero-Tokens | Escaner de Hardware | IA local opcional (Ollama) | Reglas automaticas (hooks)
# Creado por Saul Alexander Martinez Rivas (@Luaz2021)
# ==============================================================================
$ErrorActionPreference = "SilentlyContinue"

# 0. Requisito: Python 3.10 o superior (hooks, redactor, biblioteca de webs, actualizador)
function Find-NovaPython {
    $cands = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { $p = (& py -3 -c "import sys; print(sys.executable)" 2>$null); if ($p) { $cands += $p.Trim() } }
    foreach ($n in @("python", "python3")) {
        $c = Get-Command $n -ErrorAction SilentlyContinue
        if ($c -and $c.Source -notmatch "WindowsApps") { $cands += $c.Source }
    }
    $cands += (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    $cands += (Get-ChildItem "$env:LOCALAPPDATA\Python\pythoncore-3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    foreach ($c in $cands) {
        if ($c -and (Test-Path $c)) {
            & $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $c }
        }
    }
    return $null
}
$novaPython = Find-NovaPython
if (-not $novaPython) {
    Write-Host "[AVISO] Nova necesita Python 3.10 o superior y no lo encuentro." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $askPy = Read-Host "Lo instalo ahora con winget (Python 3.12 oficial)? (s/n) [s]"
        if (-not $askPy -or $askPy.ToLower() -ne "n") {
            winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
            $novaPython = Find-NovaPython
        }
    }
    if (-not $novaPython) {
        Write-Host "[ERROR] Instala Python desde https://www.python.org/downloads/ (marca 'Add python.exe to PATH') y repite." -ForegroundColor Red
        exit 1
    }
}

Clear-Host
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   BIENVENIDO AL INSTALADOR OFICIAL DE NOVA AGENT v3.0    " -ForegroundColor Cyan
Write-Host "   Arquitecta de Software & Copiloto Tecnico Senior       " -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Cuestionario de Onboarding (Nombre y Profesion)
$nombre = Read-Host "Cual es tu nombre o como te gusta que te llamen? [Desarrollador]"
if ([string]::IsNullOrWhiteSpace($nombre)) { $nombre = "Desarrollador" }

# Aviso etico de telemetria
Write-Host ""
Write-Host "[AVISO DE PRIVACIDAD Y MEJORA CONTINUA]" -ForegroundColor Cyan
Write-Host "Si quieres ayudar a mejorar Nova, una vez al mes te propondra enviar un informe con:" -ForegroundColor Gray
Write-Host "- las lecciones que aprendio, las entradas nuevas de tu servilleta y el TIPO de errores que cometio." -ForegroundColor Gray
Write-Host "- Nada de tu equipo, tus proyectos, rutas, correos ni claves. Tu lo revisas y decides si lo envias." -ForegroundColor Gray
$optIn = Read-Host "Quieres que Nova te lo proponga? (s/n) [s]"
$telemetryEnabled = if ($optIn -and $optIn.ToLower() -eq "n") { $false } else { $true }

Write-Host ""
Write-Host "En que te enfocas o cual es tu profesion/estudios?" -ForegroundColor Yellow
Write-Host "  [1] Estudiante (DAM / DAW / Informatica / Ingenieria)" -ForegroundColor Gray
Write-Host "  [2] Desarrollador Frontend / Web (React, Next.js, UI)" -ForegroundColor Gray
Write-Host "  [3] Desarrollador Backend / Datos (Java, Spring, Python, SQL)" -ForegroundColor Gray
Write-Host "  [4] Fullstack / DevOps / Ciberseguridad" -ForegroundColor Gray
Write-Host "  [5] Emprendedor / No-Programador (Quiero crear proyectos)" -ForegroundColor Gray
$profOpcion = Read-Host "Elige una opcion [1-5] o escribe tu profesion directamente"

switch ($profOpcion) {
    "1" { $profesion = "Estudiante de Informatica / Desarrollo de Software" }
    "2" { $profesion = "Desarrollador Frontend & UI" }
    "3" { $profesion = "Desarrollador Backend & Bases de Datos" }
    "4" { $profesion = "Ingeniero Fullstack & DevSecOps" }
    "5" { $profesion = "Emprendedor / Constructor de Productos Digitales" }
    Default {
        if ([string]::IsNullOrWhiteSpace($profOpcion)) {
            $profesion = "Desarrollador de Software"
        } else {
            $profesion = $profOpcion
        }
    }
}

# 2. ESCANER DE HARDWARE INTELIGENTE (0 TOKENS) Y DECISION DE IA LOCAL
Write-Host ""
Write-Host "----------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[ESCANER DE HARDWARE NOVA] Analizando especificaciones de tu PC..." -ForegroundColor Cyan

$cpuObj = Get-CimInstance Win32_Processor | Select-Object -First 1
$cpuName = if ($cpuObj.Name) { $cpuObj.Name.Trim() } else { "CPU Estandar" }
$cpuCores = if ($cpuObj.NumberOfLogicalProcessors) { $cpuObj.NumberOfLogicalProcessors } else { 4 }

$csObj = Get-CimInstance Win32_ComputerSystem
$ramGB = if ($csObj.TotalPhysicalMemory) { [math]::Round($csObj.TotalPhysicalMemory / 1GB, 1) } else { 8.0 }

$sysDrive = $env:SystemDrive
$diskObj = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$sysDrive'"
$freeDiskGB = if ($diskObj.FreeSpace) { [math]::Round($diskObj.FreeSpace / 1GB, 1) } else { 20.0 }

$gpus = Get-CimInstance Win32_VideoController
$bestGpuName = "Grafica Integrada"
$bestVramGB = 0.0
$hasDedicatedGpu = $false

foreach ($g in $gpus) {
    $gName = $g.Name
    $vram = if ($g.AdapterRAM -gt 0) { [math]::Round($g.AdapterRAM / 1GB, 1) } else { 0.0 }
    if ($gName -match "NVIDIA|RTX|GTX|Radeon RX|Arc A") {
        $hasDedicatedGpu = $true
        $bestGpuName = $gName
        if ($vram -lt 4.0 -and $gName -match "RTX|RX 6|RX 7") { $vram = 6.0 }
        $bestVramGB = $vram
        break
    } elseif ($bestGpuName -eq "Grafica Integrada") {
        $bestGpuName = $gName
    }
}

Write-Host "  - Procesador : $cpuName ($cpuCores hilos)" -ForegroundColor Gray
Write-Host "  - Memoria RAM: $ramGB GB" -ForegroundColor Gray
Write-Host "  - Tarjeta GPU: $bestGpuName" -ForegroundColor Gray
Write-Host "  - Disco Libre: $freeDiskGB GB disponibles en $sysDrive" -ForegroundColor Gray

$quiereIA = $false
$hwTier = "BASICO_CLOUD_ONLY"

if ($ramGB -lt 11.5 -or $freeDiskGB -lt 15.0) {
    $hwTier = "BASICO_CLOUD_ONLY"
    Write-Host "  - Veredicto  : MODO NUBE (protegemos tu RAM y tu bateria; sin IA local)" -ForegroundColor Yellow
} elseif ($ramGB -ge 15.0) {
    $hwTier = "OPTIMO_GPU"
    Write-Host "  - Veredicto  : POTENCIA OPTIMA PARA IA LOCAL" -ForegroundColor Green
    $askAi = Read-Host "Activo la IA local (Ollama + qwen3.5:9b + InternVL3.5 8B, ~12 GB)? (s/n) [s]"
    if (-not $askAi -or $askAi.ToLower() -ne "n") { $quiereIA = $true }
} else {
    $hwTier = "GAMA_MEDIA"
    Write-Host "  - Veredicto  : GAMA MEDIA (IA local ligera opcional)" -ForegroundColor Cyan
    $askAi = Read-Host "Activo la IA local ligera (Ollama + qwen3.5:4b + InternVL3.5 4B, ~6,5 GB)? (s/n) [n]"
    if ($askAi -and $askAi.ToLower() -eq "s") { $quiereIA = $true }
}
Write-Host "----------------------------------------------------------" -ForegroundColor DarkCyan

Write-Host ""
Write-Host "[INFO] Configurando a Nova para $nombre ($profesion)..." -ForegroundColor Cyan

# 3. Creacion de directorios de usuario
$geminiDir = "$HOME\.gemini"
$novaLocalSkills = "$geminiDir\antigravity\skills"
$novaConfigSkills = "$geminiDir\config\skills"
$novaLocalMemory = "$geminiDir\antigravity\memory"
$novaLocalScripts = "$geminiDir\antigravity\scripts"
$novaCore = "$geminiDir\nova_core"
$novaAlmacen = "$geminiDir\antigravity\almacen"
New-Item -ItemType Directory -Path $novaCore -Force | Out-Null
New-Item -ItemType Directory -Path $novaAlmacen -Force | Out-Null
New-Item -ItemType Directory -Path $novaLocalSkills -Force | Out-Null
New-Item -ItemType Directory -Path $novaConfigSkills -Force | Out-Null
New-Item -ItemType Directory -Path $novaLocalMemory -Force | Out-Null
New-Item -ItemType Directory -Path $novaLocalScripts -Force | Out-Null

# 4. Guardar Perfil de Usuario Personalizado con Ficha de Hardware e IA Local
$perfilData = @{
    nombre = $nombre
    profesion = $profesion
    sistema_operativo = "Windows"
    fecha_instalacion = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    pedagogia_calibrada = if ($profOpcion -eq "5") { "producto_llave_en_mano" } elseif ($profOpcion -eq "1") { "mentor_didactico" } else { "socio_trinchera" }
    telemetry_opt_in = $telemetryEnabled
    hardware = @{
        cpu = $cpuName
        ram_gb = $ramGB
        gpu = $bestGpuName
        free_disk_gb = $freeDiskGB
        tier = $hwTier
    }
    ia_local = @{
        instalada = $false
        modelo = "ninguno"
        modelo_vl = "ninguno"
        regla_activacion = "solo_tareas_masivas_mayor_1500_tokens"
    }
} | ConvertTo-Json -Depth 4

# UTF-8 SIN BOM (con BOM, algunos lectores JSON fallan)
[System.IO.File]::WriteAllText("$novaLocalMemory\perfil_usuario.json", $perfilData, (New-Object System.Text.UTF8Encoding $false))

# 5. Enlace de las Skills mediante Junctions
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$repoSkills = Join-Path $repoRoot "skills"
if (Test-Path $repoSkills) {
    Write-Host "[INFO] Enlazando el catalogo de skills..." -ForegroundColor Cyan
    Get-ChildItem -Path $repoSkills -Directory | ForEach-Object {
        foreach ($targetDir in @($novaLocalSkills, $novaConfigSkills)) {
            $dest = Join-Path $targetDir $_.Name
            if (-not (Test-Path $dest)) {
                cmd /c mklink /J "$dest" "$($_.FullName)" 2>$null | Out-Null
            }
        }
    }
    Write-Host "[OK] Skills enlazadas correctamente." -ForegroundColor Green
}

# 6. Copiar scripts (con subcarpetas), nucleo (hooks, redactor) y biblioteca de webs
$repoScripts = Join-Path $repoRoot "scripts"
if (Test-Path $repoScripts) { Copy-Item -Path "$repoScripts\*" -Destination $novaLocalScripts -Recurse -Force }
$repoCore = Join-Path $repoRoot "nova_core"
if (Test-Path $repoCore) { Copy-Item -Path "$repoCore\*" -Destination $novaCore -Recurse -Force }
$repoAlmacen = Join-Path $repoRoot "almacen"
if (Test-Path $repoAlmacen) { Copy-Item -Path "$repoAlmacen\*" -Destination $novaAlmacen -Recurse -Force }
foreach ($extra in @("herramientas", "clonador")) {
    $src = Join-Path $repoRoot $extra
    if (Test-Path $src) { New-Item -ItemType Directory -Path "$geminiDirntigravity\$extra" -Force | Out-Null; Copy-Item -Path "$src\*" -Destination "$geminiDirntigravity\$extra" -Recurse -Force }
}
Copy-Item (Join-Path $repoRoot "manifest_master.json") "$geminiDir\antigravity\manifest_master.json" -Force
Get-ChildItem -Path $novaLocalScripts, $novaCore, $novaAlmacen -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# 7. Plantillas de Memoria
$templatesDir = Join-Path $repoRoot "memory_templates"
if (Test-Path $templatesDir) {
    if (-not (Test-Path "$novaLocalMemory\tasks.md")) {
        Copy-Item "$templatesDir\tasks.template.md" "$novaLocalMemory\tasks.md" -Force
    }
    if (-not (Test-Path "$novaLocalMemory\napkin.md")) {
        Copy-Item "$templatesDir\napkin.template.md" "$novaLocalMemory\napkin.md" -Force
    }
    Copy-Item "$templatesDir\napkin.template.md" "$novaLocalMemory\napkin_oficial.md" -Force
}

# 8. Inyeccion UNICA de GEMINI.md y AYUDA.md (Eliminando duplicado legacy en ~/.gemini/GEMINI.md)
$geminiRules = Join-Path $repoRoot "GEMINI.md"
$ayudaFile = Join-Path $repoRoot "AYUDA.md"
if (Test-Path $geminiRules) {
    Copy-Item $geminiRules "$geminiDir\config\GEMINI.md" -Force
    if (Test-Path "$geminiDir\GEMINI.md") {
        Remove-Item "$geminiDir\GEMINI.md" -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] Reglas GEMINI.md configuradas con inyeccion unica (~3.200 tokens ahorrados)." -ForegroundColor Green
}
if (Test-Path $ayudaFile) {
    Copy-Item $ayudaFile "$geminiDir\config\AYUDA.md" -Force
}

# Reglas automaticas (hooks): el sistema vigila las leyes, no el modelo
& $novaPython "$novaCore\instalar_hooks.py"

# Guardian de sesion en Inicio de Windows + Doctor + arranque inmediato
$startupDir = [Environment]::GetFolderPath("Startup")
if (Test-Path "$novaLocalScripts\start_session_guard.vbs") {
    Copy-Item "$novaLocalScripts\start_session_guard.vbs" (Join-Path $startupDir "Nova_SessionGuard.vbs") -Force
    Start-Process -FilePath "wscript.exe" -ArgumentList "`"$novaLocalScripts\start_session_guard.vbs`""
}
if (Test-Path "$novaLocalScripts\nova_doctor.ps1") {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$novaLocalScripts\nova_doctor.ps1" -SinServicios -SinAviso
}

# IA local (opcional): instala Ollama si falta y descarga los 2 modelos del perfil
if ($quiereIA) {
    & $novaPython "$novaLocalScripts\nova_instalar_ia_local.py" --perfil $hwTier
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[AVISO] La IA local no quedo lista. Repitelo cuando quieras o di 'Nova, instala la IA local'." -ForegroundColor Yellow
    }
}

# Claves opcionales (tipo 'iniciar sesion'): se guardan solo en este equipo
Write-Host ""
$askKeys = Read-Host "Quieres configurar ahora tus claves gratuitas opcionales (OpenRouter, Groq...)? (s/n) [n]"
if ($askKeys -and $askKeys.ToLower() -eq "s") { & $novaPython "$novaLocalScripts\nova_claves.py" }

# Configuracion transparente de permisos del IDE (Opt-In)
Write-Host ""
Write-Host "[CONFIGURACION DE PERMISOS DEL IDE]" -ForegroundColor Cyan
Write-Host "Nova respeta siempre la Ley 1 (pedir tu permiso en el chat antes de tocar tu codigo)." -ForegroundColor Gray
Write-Host "Sin embargo, Antigravity IDE pide confirmacion manual cada vez que Nova lee sus propias" -ForegroundColor Gray
Write-Host "skills o su memoria en ~/.gemini/antigravity/memory." -ForegroundColor Gray
$askTurbo = Read-Host "Deseas habilitar el acceso fluido a archivos de memoria/skills sin popups? (s/n) [s]"
$configJsonPath = "$geminiDir\config\config.json"
if ((-not $askTurbo -or $askTurbo.ToLower() -ne "n") -and (-not (Test-Path $configJsonPath))) {
    $defaultConfig = @{
        userSettings = @{
            nonWorkspaceFileAccessPolicy = "AGENT_SETTING_POLICY_ALLOW"
        }
    } | ConvertTo-Json -Depth 4
    Set-Content -Path $configJsonPath -Value $defaultConfig -Encoding UTF8
    Write-Host "[OK] Lectura fluida de skills/memoria habilitada (Sandbox de terminal y Ley 1 intactos)." -ForegroundColor Green
} else {
    Write-Host "[OK] Se mantienen los permisos por defecto de tu IDE." -ForegroundColor Green
}

# 9. Imprimir Bienvenida y Mapa de Atajos en Consola a 0 TOKENS + Copiar Saludo Corto
$promptCorto = "Hola Nova, soy $nombre ($profesion). Verifica mi perfil_usuario.json y confirmame en 2 o 3 lineas que todo esta listo."
$welcomeFilePath = "$geminiDir\antigravity\primer_mensaje.txt"
Set-Content -Path $welcomeFilePath -Value $promptCorto -Encoding UTF8
try { Set-Clipboard -Value $promptCorto } catch {}

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "   NOVA AGENT v3.0 - INSTALACION COMPLETADA ($nombre)" -ForegroundColor Green
Write-Host "   Arquitectura creada por Saul Alexander Martinez Rivas (@Luaz2021)" -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "ATAJOS RAPIDOS EN EL CHAT (Coste 0 tokens de redaccion):" -ForegroundColor Yellow
Write-Host "  - 'hola' / 'continuamos'        -> Retoma tu sesion exactamente donde la dejaste." -ForegroundColor White
Write-Host "  - '/ayuda' o 'ayuda'            -> Muestra la guia completa desde AYUDA.md." -ForegroundColor White
Write-Host "  - 'Nuevo proyecto: [idea]'      -> Planifica el sprint contigo antes de picar codigo." -ForegroundColor White
Write-Host "  - 'Nova analiza este proyecto'  -> Radiografia Tanque de 7 Puntos (Stack, UI, SEO, Seguridad)." -ForegroundColor White
Write-Host "  - 'te lo dejo en tus manos'     -> Modo autonomo: desarrollo 1-Shot + tests en verde." -ForegroundColor White
Write-Host ""
Write-Host "LINEA DIRECTA CON EL CREADOR (SAUL MARTINEZ):" -ForegroundColor Yellow
Write-Host "  - '/creador [mensaje]'          -> Envia una duda, idea o saludo directo al buzon de Saul." -ForegroundColor White
Write-Host "  - '/reportar-fallo'             -> Envia un bug resuelto para mejorar el Core." -ForegroundColor White
Write-Host "  - '/compartir-skill [nombre]'   -> Propone una skill tuya para incluirla con creditos." -ForegroundColor White
Write-Host "  - '/enviar-informe'             -> Lecciones y errores de Nova (tu lo revisas antes)." -ForegroundColor White
Write-Host "  - '/actualizar-nova'            -> Busca e instala mejoras oficiales sin borrar tus notas." -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "[!] Tu primer mensaje corto YA ESTA COPIADO al portapapeles (Ctrl + V):" -ForegroundColor Cyan
Write-Host "    $promptCorto" -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Green
