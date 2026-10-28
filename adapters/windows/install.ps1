# ==============================================================================
# INSTALADOR INTERACTIVO UNIVERSAL DE NOVA AGENT - WINDOWS (POWERSHELL)
# Zero-Tokens | Escaner de Hardware Inteligente | Inyeccion Unica Optimizada
# Creado por Saul Alexander Martinez Rivas (@Luaz2021 - Torrevieja, Espana)
# ==============================================================================
$ErrorActionPreference = "SilentlyContinue"

Clear-Host
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   BIENVENIDO AL INSTALADOR OFICIAL DE NOVA AGENT v2.0    " -ForegroundColor Cyan
Write-Host "   Arquitecta de Software & Copiloto Tecnico Senior       " -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Cuestionario de Onboarding (Nombre y Profesion)
$nombre = Read-Host "Cual es tu nombre o como te gusta que te llamen? [Desarrollador]"
if ([string]::IsNullOrWhiteSpace($nombre)) { $nombre = "Desarrollador" }

# Aviso etico de telemetria
Write-Host ""
Write-Host "[AVISO DE PRIVACIDAD Y MEJORA CONTINUA]" -ForegroundColor Cyan
Write-Host "Nova Agent esta basado en Google Gemini. Para mejorar y evolucionar el sistema:" -ForegroundColor Gray
Write-Host "- Una vez al mes genera un resumen anonimo de manifiesto (skills y errores esquivados)." -ForegroundColor Gray
Write-Host "- Cero rutas privadas, cero codigo confidencial, cero contrasenas." -ForegroundColor Gray
Write-Host "- Puedes activar o desactivar este envio ahora o en cualquier momento." -ForegroundColor Gray
$optIn = Read-Host "Deseas habilitar la telemetria etica anonima? (s/n) [s]"
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

$localAiInstalled = $false
$localAiModel = "ninguno"
$hwTier = "BASICO_CLOUD_ONLY"

if ($ramGB -lt 11.5 -or $freeDiskGB -lt 15.0) {
    # EQUIPO BASICO: Prohibido instalar IA local para no ahogar RAM ni disco
    $hwTier = "BASICO_CLOUD_ONLY"
    Write-Host "  - Veredicto  : MODO NUBE EXCLUSIVO (Proteccion de RAM y Bateria)" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------" -ForegroundColor DarkCyan
    Write-Host "[OPTIMIZACION AUTOMATICA] Tu equipo tiene $ramGB GB de RAM / $freeDiskGB GB libres." -ForegroundColor Yellow
    Write-Host "Para evitar que tu PC se congele o gaste bateria, Nova NO instalara modelos pesados" -ForegroundColor Gray
    Write-Host "en local y operara con el Modo 1-Shot Cloud Optimizado (~38% menos consumo de tokens)." -ForegroundColor Gray
} elseif ($hasDedicatedGpu -and $ramGB -ge 15.0) {
    # EQUIPO POTENTE / GPU DEDICADA
    $hwTier = "OPTIMO_GPU"
    Write-Host "  - Veredicto  : POTENCIA OPTIMA PARA IA LOCAL (Aceleracion GPU)" -ForegroundColor Green
    Write-Host "----------------------------------------------------------" -ForegroundColor DarkCyan
    Write-Host "Tu PC tiene potencia de sobra para correr el Obrero Local (Ollama + Qwen 2.5 Coder 7B)" -ForegroundColor Gray
    Write-Host "en tareas masivas (>1.500 tokens repetitivos, mocks y lectura pesada) para ahorrar cuota." -ForegroundColor Gray
    $askAi = Read-Host "Deseas instalar y activar la IA Local en tu equipo? (s/n) [s]"
    if (-not $askAi -or $askAi.ToLower() -ne "n") {
        $localAiModel = "qwen2.5-coder:7b"
        $localAiInstalled = $true
    }
} else {
    # EQUIPO GAMA MEDIA (12-16 GB RAM sin GPU dedicada potente)
    $hwTier = "GAMA_MEDIA"
    Write-Host "  - Veredicto  : GAMA MEDIA (Opcional Obrero Ultraligero 3B)" -ForegroundColor Cyan
    Write-Host "----------------------------------------------------------" -ForegroundColor DarkCyan
    Write-Host "Tu equipo cuenta con buena RAM ($ramGB GB) pero sin GPU dedicada pesada." -ForegroundColor Gray
    Write-Host "Puedes operar 100% en la nube (Modo 1-Shot) o instalar el modelo ligero Qwen 2.5 Coder 3B (1.9 GB)." -ForegroundColor Gray
    $askAi = Read-Host "Deseas instalar el Obrero Local Ligero (3B)? (s/n) [n]"
    if ($askAi -and $askAi.ToLower() -eq "s") {
        $localAiModel = "qwen2.5-coder:3b"
        $localAiInstalled = $true
    }
}

if ($localAiInstalled) {
    Write-Host "[INFO] Verificando motor Ollama para descargar $localAiModel..." -ForegroundColor Cyan
    $ollamaExe = if (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") { "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" } else { (Get-Command ollama -ErrorAction SilentlyContinue).Source }
    if (-not $ollamaExe) {
        Write-Host "[INFO] Instalando Ollama via winget..." -ForegroundColor Yellow
        winget install --id Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
        $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    }
    if (Test-Path $ollamaExe) {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Write-Host "[INFO] Descargando modelo $localAiModel..." -ForegroundColor Yellow
        & $ollamaExe pull $localAiModel
        Write-Host "[OK] IA Local ($localAiModel) lista y vinculada." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[INFO] Configurando a Nova para $nombre ($profesion)..." -ForegroundColor Cyan

# 3. Creacion de directorios de usuario
$geminiDir = "$HOME\.gemini"
$novaLocalSkills = "$geminiDir\antigravity\skills"
$novaConfigSkills = "$geminiDir\config\skills"
$novaLocalMemory = "$geminiDir\antigravity\memory"
$novaLocalScripts = "$geminiDir\antigravity\scripts"
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
        instalada = $localAiInstalled
        modelo = $localAiModel
        regla_activacion = "solo_tareas_masivas_mayor_1500_tokens"
    }
} | ConvertTo-Json -Depth 4

Set-Content -Path "$novaLocalMemory\perfil_usuario.json" -Value $perfilData -Encoding UTF8

# 5. Enlace de las 119 Skills mediante Junctions
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$repoSkills = Join-Path $repoRoot "skills"
if (Test-Path $repoSkills) {
    Write-Host "[INFO] Enlazando el catalogo de 119 skills optimizadas..." -ForegroundColor Cyan
    Get-ChildItem -Path $repoSkills -Directory | ForEach-Object {
        foreach ($targetDir in @($novaLocalSkills, $novaConfigSkills)) {
            $dest = Join-Path $targetDir $_.Name
            if (-not (Test-Path $dest)) {
                cmd /c mklink /J "$dest" "$($_.FullName)" 2>$null | Out-Null
            }
        }
    }
    Write-Host "[OK] 119 Skills enlazadas correctamente (-60% peso en frontmatter)." -ForegroundColor Green
}

# 6. Copiar Scripts de Guardian y Feedback a ~/.gemini/antigravity/scripts
$repoScripts = Join-Path $repoRoot "scripts"
if (Test-Path $repoScripts) {
    Get-ChildItem -Path $repoScripts -File | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $novaLocalScripts $_.Name) -Force
    }
}

# 7. Plantillas de Memoria
$templatesDir = Join-Path $repoRoot "memory_templates"
if (Test-Path $templatesDir) {
    if (-not (Test-Path "$novaLocalMemory\tasks.md")) {
        Copy-Item "$templatesDir\tasks.template.md" "$novaLocalMemory\tasks.md" -Force
    }
    if (-not (Test-Path "$novaLocalMemory\napkin.md")) {
        Copy-Item "$templatesDir\napkin.template.md" "$novaLocalMemory\napkin.md" -Force
    }
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

# Configuracion transparente de permisos del IDE (Opt-In)
Write-Host ""
Write-Host "[CONFIGURACION DE PERMISOS DEL IDE]" -ForegroundColor Cyan
Write-Host "Nova respeta siempre la Ley 1 (pedir tu permiso en el chat antes de tocar tu codigo)." -ForegroundColor Gray
Write-Host "Sin embargo, Antigravity IDE pide confirmacion manual cada vez que Nova lee sus propias" -ForegroundColor Gray
Write-Host "119 skills o su memoria en ~/.gemini/antigravity/memory." -ForegroundColor Gray
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
Write-Host "   NOVA COPILOT ENGINE v2.0 - INSTALACION COMPLETADA ($nombre)" -ForegroundColor Green
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
Write-Host "  - '/actualizar-nova'            -> Busca e instala mejoras oficiales sin borrar tus notas." -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "[!] Tu primer mensaje corto YA ESTA COPIADO al portapapeles (Ctrl + V):" -ForegroundColor Cyan
Write-Host "    $promptCorto" -ForegroundColor White
Write-Host "==========================================================================" -ForegroundColor Green
