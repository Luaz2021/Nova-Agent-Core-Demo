# ==============================================================================
# INSTALADOR INTERACTIVO UNIVERSAL DE NOVA AGENT - WINDOWS (POWERSHELL)
# Zero-Tokens | Onboarding Personalizado | Auto-Inyeccion de Bienvenida
# Creado por Saul Martinez (Torrevieja, Espana)
# ==============================================================================
$ErrorActionPreference = "Stop"

Clear-Host
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   BIENVENIDO AL INSTALADOR OFICIAL DE NOVA AGENT         " -ForegroundColor Cyan
Write-Host "   Arquitecta de Software & Copiloto Tecnico Senior       " -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Cuestionario de Onboarding (Nombre y Profesion)
$nombre = Read-Host "Cual es tu nombre o como te gusta que te llamen?"
if ([string]::IsNullOrWhiteSpace($nombre)) { $nombre = "Desarrollador" }

# Aviso etico de telemetria
Write-Host ""
Write-Host "[AVISO DE PRIVACIDAD Y MEJORA CONTINUA]" -ForegroundColor Cyan
Write-Host "Nova Agent esta basado en Google Gemini. Para mejorar y evolucionar el sistema:" -ForegroundColor Gray
Write-Host "- Una vez al mes genera un resumen anonimo de manifiesto (skills y errores esquivados)." -ForegroundColor Gray
Write-Host "- Cero rutas privadas, cero codigo confidencial, cero contrasenas." -ForegroundColor Gray
Write-Host "- Puedes activar o desactivar este envio ahora o en cualquier momento." -ForegroundColor Gray
$optIn = Read-Host "Deseas habilitar la telemetria etica anonima? (s/n) [s]"
$telemetryEnabled = if ($optIn.ToLower() -eq "n") { $false } else { $true }

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

Write-Host ""
Write-Host "[INFO] Configurando a Nova para $nombre ($profesion)..." -ForegroundColor Cyan

# 2. Creacion de directorios de usuario
$geminiDir = "$HOME\.gemini"
$novaLocalSkills = "$geminiDir\antigravity\skills"
$novaConfigSkills = "$geminiDir\config\skills"
$novaLocalMemory = "$geminiDir\antigravity\memory"
New-Item -ItemType Directory -Path $novaLocalSkills -Force | Out-Null
New-Item -ItemType Directory -Path $novaConfigSkills -Force | Out-Null
New-Item -ItemType Directory -Path $novaLocalMemory -Force | Out-Null

# 3. Guardar Perfil de Usuario Personalizado
$perfilData = @{
    nombre = $nombre
    profesion = $profesion
    sistema_operativo = "Windows"
    fecha_instalacion = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    pedagogia_calibrada = if ($profOpcion -eq "5") { "producto_llave_en_mano" } elseif ($profOpcion -eq "1") { "mentor_didactico" } else { "socio_trinchera" }
    telemetry_opt_in = $telemetryEnabled
} | ConvertTo-Json -Depth 3

Set-Content -Path "$novaLocalMemory\perfil_usuario.json" -Value $perfilData -Encoding UTF8

# 4. Enlace de Skills mediante Junctions
$repoSkills = Join-Path $PSScriptRoot "..\..\skills"
if (Test-Path $repoSkills) {
    Write-Host "[INFO] Enlazando las 115 skills de Nova a tu sistema..." -ForegroundColor Cyan
    Get-ChildItem -Path $repoSkills -Directory | ForEach-Object {
        foreach ($targetDir in @($novaLocalSkills, $novaConfigSkills)) {
            $dest = Join-Path $targetDir $_.Name
            if (-not (Test-Path $dest)) {
                cmd /c mklink /J "$dest" "$($_.FullName)" | Out-Null
            }
        }
    }
    Write-Host "[OK] Skills enlazadas correctamente." -ForegroundColor Green
}

# 5. Plantillas de Memoria
$templatesDir = Join-Path $PSScriptRoot "..\..\memory_templates"
if (Test-Path $templatesDir) {
    if (-not (Test-Path "$novaLocalMemory\tasks.md")) {
        Copy-Item "$templatesDir\tasks.template.md" "$novaLocalMemory\tasks.md" -Force
    }
    if (-not (Test-Path "$novaLocalMemory\napkin.md")) {
        Copy-Item "$templatesDir\napkin.template.md" "$novaLocalMemory\napkin.md" -Force
    }
    Write-Host "[OK] Memorias y tablero Kanban inicializados." -ForegroundColor Green
}

# 6. Copia de Reglas Maestras y Permisos Turbo
$geminiRules = Join-Path $PSScriptRoot "..\..\GEMINI.md"
if (Test-Path $geminiRules) {
    Copy-Item $geminiRules "$geminiDir\antigravity\GEMINI.md" -Force
    Copy-Item $geminiRules "$geminiDir\config\GEMINI.md" -Force
    Copy-Item $geminiRules "$geminiDir\GEMINI.md" -Force
    Write-Host "[OK] Reglas operativas GEMINI.md configuradas." -ForegroundColor Green
}

$configJsonPath = "$geminiDir\config\config.json"
if (-not (Test-Path $configJsonPath)) {
    $defaultConfig = @{
        userSettings = @{
            autoExecutionPolicy = "CASCADE_COMMANDS_AUTO_EXECUTION_EAGER"
            browserJsExecutionPolicy = "BROWSER_JS_EXECUTION_POLICY_TURBO"
            enableTerminalSandbox = $false
            nonWorkspaceFileAccessPolicy = "AGENT_SETTING_POLICY_ALLOW"
            permissionPreset = "AGENT_PERMISSION_PRESET_TURBO"
        }
    } | ConvertTo-Json -Depth 4
    Set-Content -Path $configJsonPath -Value $defaultConfig -Encoding UTF8
    Write-Host "[OK] Permisos Turbo y acceso de archivos preconfigurados." -ForegroundColor Green
}

# 7. Generacion del Prompt de Primer Arranque (Auto-Presentacion)
$promptBienvenida = @"
Hola Nova, soy $nombre ($profesion). Acabo de instalarte en mi equipo.
Presentate oficialmente: cuentame quien eres, tus origenes con Saul Martinez en Torrevieja Espana, tus ventajas frente a otros agentes de IA, tus atajos de trabajo y que extensiones me puedes configurar o recomendar para arrancar.
Ademas, explicame como puedo decirte en cualquier momento: 'Nova, envia mensaje al creador: [mi mensaje]' para hacerle llegar sugerencias o dudas directamente a Saul en su repositorio de GitHub.
"@

$welcomeFilePath = "$geminiDir\antigravity\primer_mensaje.txt"
Set-Content -Path $welcomeFilePath -Value $promptBienvenida -Encoding UTF8
try { Set-Clipboard -Value $promptBienvenida } catch {}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   INSTALACION COMPLETADA CON EXITO PARA $nombre          " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[!] El primer mensaje YA ESTA COPIADO en tu portapapeles (Ctrl + V)." -ForegroundColor Cyan
Write-Host "Abre Antigravity y simplemente presiona Ctrl + V para pegar:" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------" -ForegroundColor Gray
Write-Host $promptBienvenida -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor Gray
Write-Host "(Tambien lo guardamos en: $welcomeFilePath)" -ForegroundColor Gray
