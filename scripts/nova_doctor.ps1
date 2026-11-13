<#
==============================================================================
 NOVA DOCTOR v1 (11/11/2026, Claude, a pedido de Luaz: "blindar" a Nova en los dos equipos)
------------------------------------------------------------------------------
 Revisa y REPARA solo lo que Nova necesita en ESTE equipo, y deja UNA linea de resumen:
   1. Python PROPIO de Nova (.gemini\nova_env, con uv y Python 3.14 gestionado por uv) con las librerias de
      nova_core\requisitos_nova.txt. Da igual el Python que Luaz instale o actualice en Windows.
      Si la lista cambia (huella distinta) o falta una libreria -> reinstala solo.
   2. Variables NOVA_PYTHON / NOVA_PYTHONW -> ese Python (GEMINI.md <PYTHON>, hooks, voz, guardian).
   3. config\hooks.json generado con las rutas de ESTE equipo (rutas cortas, sin espacios) y probado.
   4. Ollama encendido y con los modelos de scripts\nova_modelos.json.
   5. Modelo de Vosk ("Nova" en local) y navegador de Playwright.
   6. Con Antigravity abierto: voz + puente de adjuntos + guardian vivos, y la ADUANA inyectada en el chat.
 Resultado: memory\doctor_estado.json (lo lee el hook de turno y se lo cuenta a Nova si algo falla),
            memory\registros\doctor.log y, si algo falla, un aviso de Windows.

 Lo lanzan: session_guard.ps1 al abrir Antigravity (-AlAbrir), sync_antigravity.ps1 al bajar (-SinServicios)
 y Nova cuando algo no va: powershell -ExecutionPolicy Bypass -File "<NOVA_HOME>\antigravity\scripts\nova_doctor.ps1"
 Nova NUNCA repara a mano: ejecuta esto y cuenta el resultado.
==============================================================================
#>
param(
    [switch]$AlAbrir,        # recien abierto Antigravity: espera a que arranquen voz/puente/aduana
    [switch]$SinServicios,   # solo entorno, hooks, Ollama y Vosk (lo usa el sync, a veces sin Antigravity)
    [switch]$SinAviso        # sin globo de Windows
)
$ErrorActionPreference = "Continue"
$G       = Join-Path $env:USERPROFILE ".gemini"
$AG      = Join-Path $G "antigravity"
$EnvDir  = Join-Path $G "nova_env"
$EnvPy   = Join-Path $EnvDir "Scripts\python.exe"
$Req     = Join-Path $G "nova_core\requisitos_nova.txt"
$Huella  = Join-Path $EnvDir ".huella_nova"
$PyVer   = "3.14"
$UvVer   = "0.13.6"
$Hooks   = Join-Path $G "config\hooks.json"
$LogF    = Join-Path $AG "memory\registros\doctor.log"
$EstadoF = Join-Path $AG "memory\doctor_estado.json"
$BadAG = "$G ntigravity"
if (Test-Path -LiteralPath $BadAG) {
    foreach ($s in @("herramientas", "clonador")) {
        if (Test-Path -LiteralPath "$BadAG\$s") { robocopy "$BadAG\$s" "$AG\$s" /E /XC /XN /XO /NFL /NDL /NJH /NJS | Out-Null }
    }
    Remove-Item -LiteralPath $BadAG -Recurse -Force -ErrorAction SilentlyContinue
}
$guardStartup = Join-Path ([Environment]::GetFolderPath("Startup")) "Nova_SessionGuard.vbs"
$guardSrc = Join-Path $AG "scripts\start_session_guard.vbs"
if ((Test-Path -LiteralPath $guardSrc) -and -not (Test-Path -LiteralPath $guardStartup)) {
    Copy-Item -LiteralPath $guardSrc -Destination $guardStartup -Force
}
$Modulos = @("sounddevice", "numpy", "speech_recognition", "websocket", "edge_tts", "vosk", "PIL", "pystray",
             "pymupdf", "docx", "openpyxl", "pptx", "playwright", "aiohttp", "psutil", "imageio_ffmpeg", "watchdog")

New-Item -ItemType Directory -Force (Split-Path $LogF) | Out-Null
$mutex = New-Object System.Threading.Mutex($false, "Global\NovaDoctor")
try { $tengo = $mutex.WaitOne(900000) } catch [System.Threading.AbandonedMutexException] { $tengo = $true }
if (-not $tengo) { Write-Host "[DOCTOR] Otro Doctor lleva 15 min trabajando. Salgo."; exit 2 }

$res = New-Object System.Collections.ArrayList
function Log([string]$t) {
    $linea = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $env:COMPUTERNAME, $t
    try { Add-Content -LiteralPath $LogF -Value $linea -Encoding UTF8 } catch {}
}
function Nota([string]$area, [string]$estado, [string]$texto) {
    [void]$res.Add([pscustomobject]@{ area = $area; estado = $estado; texto = $texto })
    Log "$estado $area - $texto"
    $color = switch ($estado) { "OK" { "Green" } "ARREGLADO" { "Cyan" } "AVISO" { "Yellow" } default { "Red" } }
    Write-Host ("  [{0}] {1}: {2}" -f $estado, $area, $texto) -ForegroundColor $color
}
function Prueba-Modulos([string]$py) {
    # Devuelve la lista de modulos que NO se pueden importar con ese Python (vacia = todo bien)
    if (-not (Test-Path -LiteralPath $py)) { return $Modulos }
    # se IMPORTA de verdad (una DLL rota tambien cuenta como fallo)
    $code = "import sys`nm=[]`nfor x in sys.argv[1:]:`n    try: __import__(x)`n    except Exception: m.append(x)`nprint(','.join(m))"
    $out = & $py -c $code @Modulos 2>$null
    if ($LASTEXITCODE -ne 0) { return $Modulos }
    $txt = ("" + ($out | Select-Object -Last 1)).Trim()
    if (-not $txt) { return @() }
    return $txt.Split(",")
}
Write-Host "[NOVA DOCTOR] Revisando este equipo ($env:COMPUTERNAME)..." -ForegroundColor Cyan
Log "---- inicio (AlAbrir=$AlAbrir SinServicios=$SinServicios) ----"

# ------------------------------------------------------------------------------
# 1. uv (el que instala y fija el Python de Nova)
# ------------------------------------------------------------------------------
function Find-Uv {
    $c = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in @("$env:USERPROFILE\.local\bin\uv.exe", "$env:USERPROFILE\.cargo\bin\uv.exe", "$env:LOCALAPPDATA\Programs\uv\uv.exe")) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}
$uv = Find-Uv
if (-not $uv) {
    Log "uv no esta: se instala la version $UvVer (instalador oficial de astral.sh)"
    $inst = & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/$UvVer/install.ps1 | iex" 2>&1 | Out-String
    $uv = Find-Uv
    if ($uv) { Nota "uv" "ARREGLADO" "instalado uv $UvVer" } else { Nota "uv" "FALLA" "no se pudo instalar uv (sin internet?). Detalle en doctor.log"; Log $inst }
}

# ------------------------------------------------------------------------------
# 2. Python propio de Nova (nova_env)
# ------------------------------------------------------------------------------
$huellaQuiere = ""
if (Test-Path -LiteralPath $Req) { $huellaQuiere = (Get-FileHash -LiteralPath $Req -Algorithm SHA256).Hash + "|" + $PyVer }
$huellaTiene = if (Test-Path -LiteralPath $Huella) { (Get-Content -LiteralPath $Huella -Raw).Trim() } else { "" }
$faltan = Prueba-Modulos $EnvPy
$envSano = (Test-Path -LiteralPath $EnvPy) -and ($faltan.Count -eq 0) -and ($huellaTiene -eq $huellaQuiere)

if ($envSano) {
    $ver = (& $EnvPy -c "import platform; print(platform.python_version())" 2>$null)
    Nota "python" "OK" "Python de Nova $ver con sus $($Modulos.Count) librerias"
} elseif (-not $uv) {
    Nota "python" "FALLA" "falta uv para montar el Python de Nova"
} elseif (-not (Test-Path -LiteralPath $Req)) {
    Nota "python" "FALLA" "no esta nova_core\requisitos_nova.txt (di 'Nova, sincroniza')"
} else {
    $detalle = ""
    # Python que no arranca (p. ej. le borraron la base): se aparta y se crea de nuevo
    if (Test-Path -LiteralPath $EnvPy) {
        & $EnvPy -c "import sys" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $roto = "$EnvDir.roto-$(Get-Date -Format 'yyyyMMdd-HHmm')"
            try { Rename-Item -LiteralPath $EnvDir -NewName (Split-Path $roto -Leaf) -ErrorAction Stop; Log "nova_env roto apartado en $roto" }
            catch { Log "nova_env roto y bloqueado: $($_.Exception.Message)" }
        }
    }
    if (-not (Test-Path -LiteralPath $EnvPy)) {
        $detalle += (& $uv python install $PyVer 2>&1 | Out-String)
        $detalle += (& $uv venv $EnvDir --python $PyVer --managed-python --seed 2>&1 | Out-String)
    }
    $detalle += (& $uv pip install --python $EnvPy -r $Req 2>&1 | Out-String)
    $faltan = Prueba-Modulos $EnvPy
    if ((Test-Path -LiteralPath $EnvPy) -and $faltan.Count -eq 0) {
        Set-Content -LiteralPath $Huella -Value $huellaQuiere -Encoding ASCII
        $ver = (& $EnvPy -c "import platform; print(platform.python_version())" 2>$null)
        Nota "python" "ARREGLADO" "Python de Nova $ver montado/actualizado con sus librerias"
    } else {
        Nota "python" "FALLA" "no se pudieron instalar: $($faltan -join ', ') (detalle en doctor.log)"
        Log $detalle
    }
}

# Navegador de Playwright (radar_web, capturas). Comparte carpeta entre Pythons: solo se baja si falta.
if ((Test-Path -LiteralPath $EnvPy) -and $Modulos -contains "playwright" -and -not (Get-ChildItem "$env:LOCALAPPDATA\ms-playwright" -Directory -Filter "chromium-*" -ErrorAction SilentlyContinue)) {
    $o = & $EnvPy -m playwright install chromium 2>&1 | Out-String
    if (Get-ChildItem "$env:LOCALAPPDATA\ms-playwright" -Directory -Filter "chromium-*" -ErrorAction SilentlyContinue) { Nota "playwright" "ARREGLADO" "navegador chromium instalado" }
    else { Nota "playwright" "AVISO" "no se pudo bajar chromium (el radar web no ira)"; Log $o }
}

# ------------------------------------------------------------------------------
# 3. Variables NOVA_PYTHON / NOVA_PYTHONW
# ------------------------------------------------------------------------------
. (Join-Path $AG "scripts\nova_python.ps1")
$py = Set-NovaPythonEnv
if ($py -and $py -like "$EnvDir*") { Nota "variables" "OK" "NOVA_PYTHON = Python de Nova" }
elseif ($py) { Nota "variables" "AVISO" "NOVA_PYTHON = $py (el Python de Nova no esta listo; se usa el del sistema)" }
else { Nota "variables" "FALLA" "no hay ningun Python en este equipo" }

# ------------------------------------------------------------------------------
# 4. hooks.json con las rutas de ESTE equipo
# ------------------------------------------------------------------------------
$fso = New-Object -ComObject Scripting.FileSystemObject
function Corta-Carpeta([string]$p) { try { return $fso.GetFolder($p).ShortPath } catch { return $p } }
# OJO (09/11): el nombre corto de un ARCHIVO cambia al editarlo (NOVA_H~3.PY) -> solo carpetas cortas + nombre largo
$pyHook = if (Test-Path -LiteralPath $EnvPy) { $EnvPy } else { Get-NovaPython }
$pyHookCorto = (Corta-Carpeta (Split-Path $pyHook -Parent)) + "\" + (Split-Path $pyHook -Leaf)
$coreCorto = Corta-Carpeta (Join-Path $G "nova_core")
function Q([string]$s) { if ($s -match ' ') { return '"' + $s + '"' } else { return $s } }
$cmdTool = "$(Q $pyHookCorto) $(Q "$coreCorto\nova_hook.py")"
$cmdPre  = "$(Q $pyHookCorto) $(Q "$coreCorto\nova_hook_turno.py") pre"
$cmdStop = "$(Q $pyHookCorto) $(Q "$coreCorto\nova_hook_turno.py") stop"
$plantilla = [ordered]@{
    "nova-guardia-herramientas"   = [ordered]@{ enabled = $true; PreToolUse = @([ordered]@{ matcher = "*"; hooks = @([ordered]@{ type = "command"; command = $cmdTool; timeout = 10 }) }) }
    "nova-recordatorio-codigo"    = [ordered]@{ enabled = $true; PreInvocation = @([ordered]@{ type = "command"; command = $cmdPre; timeout = 60 }) }
    "nova-correccion-codigo-chat" = [ordered]@{ enabled = $true; Stop = @([ordered]@{ type = "command"; command = $cmdStop; timeout = 10 }) }
}
$actualTxt = if (Test-Path -LiteralPath $Hooks) { Get-Content -LiteralPath $Hooks -Raw -Encoding UTF8 } else { "" }
$otros = 0
if ($actualTxt) {
    try {
        $actual = $actualTxt | ConvertFrom-Json
        foreach ($p in $actual.PSObject.Properties) { if (-not $plantilla.Contains($p.Name)) { $plantilla[$p.Name] = $p.Value; $otros++ } }
    } catch { Log "hooks.json no se podia leer (JSON roto): se rehace" }
}
$nuevoTxt = $plantilla | ConvertTo-Json -Depth 12
$cambiado = $false
try { $mismo = (($actualTxt | ConvertFrom-Json) | ConvertTo-Json -Depth 12) -eq $nuevoTxt } catch { $mismo = $false }
if (-not $mismo) {
    if ($actualTxt) { Copy-Item -LiteralPath $Hooks -Destination "$Hooks.antes-doctor" -Force }
    New-Item -ItemType Directory -Force (Split-Path $Hooks) | Out-Null
    [IO.File]::WriteAllText($Hooks, $nuevoTxt, (New-Object System.Text.UTF8Encoding($false)))  # sin BOM
    $cambiado = $true
}
# Prueba de fuego: el hook de herramientas tiene que contestar un JSON con "decision"
$prueba = '{"toolCall":{"name":"view_file","args":{"AbsolutePath":"C:\\x.txt"}},"conversationId":"doctor"}' | cmd.exe /c $cmdTool 2>&1 | Out-String
$pruebaPre = '{"conversationId":"doctor","lastUserInput":""}' | cmd.exe /c $cmdPre 2>&1 | Out-String
if ($prueba -match '"decision"' -and $pruebaPre.Trim().StartsWith("{")) {
    if ($cambiado) { Nota "hooks" "ARREGLADO" "hooks.json rehecho con las rutas de este equipo y probado (copia: hooks.json.antes-doctor)" }
    else { Nota "hooks" "OK" "hooks.json correcto y los vigilantes contestan" }
} else {
    Nota "hooks" "FALLA" "los vigilantes no contestan bien (detalle en doctor.log)"
    Log "prueba hook: $prueba | pre: $pruebaPre"
}

# Arranque de Windows: el vigilante de lint con el Python de ESTE equipo y SIN ventana (antes la ruta de la laptop a mano)
$startup = [Environment]::GetFolderPath("Startup")
$vigiaVbs = Join-Path $startup "Nova_VigiaLint.vbs"
$vigiaQuiere = "Set WshShell = CreateObject(""WScript.Shell"")`r`n' 11/11 (Claude, Nova Doctor): lanza el vigilante con el Python de este equipo, sin ventana`r`nWshShell.Run ""wscript.exe """"" + (Join-Path $AG "scripts\start_vigia_lint.vbs") + """"""", 0, False`r`n"
if ((Test-Path -LiteralPath $vigiaVbs) -and ((Get-Content -LiteralPath $vigiaVbs -Raw) -ne $vigiaQuiere)) {
    [IO.File]::WriteAllText($vigiaVbs, $vigiaQuiere, [System.Text.Encoding]::ASCII)
    Nota "arranque" "ARREGLADO" "Nova_VigiaLint.vbs (Inicio de Windows) ya no lleva rutas de otro equipo"
}

# ------------------------------------------------------------------------------
# 5. Ollama + modelos, y Vosk
# ------------------------------------------------------------------------------
function Get-OllamaTags { try { return Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 } catch { return $null } }
$tags = Get-OllamaTags
$ollamaArrancado = $false
if (-not $tags) {
    $ol = (Get-Command ollama.exe -ErrorAction SilentlyContinue).Source
    if (-not $ol) { $ol = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" }
    if (Test-Path -LiteralPath $ol) {
        Start-Process -FilePath $ol -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 20 -and -not $tags; $i++) { Start-Sleep -Seconds 1; $tags = Get-OllamaTags }
        $ollamaArrancado = [bool]$tags
    }
}
if (-not $tags) {
    Nota "ollama" "FALLA" "Ollama no esta instalado o no arranca: las webs, la vision y los resumenes locales no iran"
} else {
    $tiene = @($tags.models | ForEach-Object { $_.name })
    $quiere = @()
    try { $m = Get-Content (Join-Path $AG "scripts\nova_modelos.json") -Raw -Encoding UTF8 | ConvertFrom-Json; $quiere = @($m.coder, $m.vl) | Where-Object { $_ } } catch {}
    $sinModelo = @($quiere | Where-Object { $q = $_; -not ($tiene | Where-Object { $_ -eq $q -or $_ -eq "$q`:latest" }) })
    if ($sinModelo.Count -gt 0) { Nota "ollama" "FALLA" "faltan modelos: $($sinModelo -join ', ') (instalar con: ollama pull <modelo>)" }
    elseif ($ollamaArrancado) { Nota "ollama" "ARREGLADO" "Ollama estaba apagado: encendido, con $($quiere -join ' y ')" }
    else { Nota "ollama" "OK" "encendido con $($quiere -join ' y ')" }
}
$voskDir = Join-Path $AG "herramientas\voz\modelos"
if (Get-ChildItem $voskDir -Directory -Filter "vosk-model*" -ErrorAction SilentlyContinue) { Nota "vosk" "OK" "modelo de 'Nova' en local presente" }
else {
    try {
        New-Item -ItemType Directory -Force $voskDir | Out-Null
        $z = Join-Path $env:TEMP "vosk-model-small-es-0.42.zip"
        Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip" -OutFile $z -UseBasicParsing
        Expand-Archive -LiteralPath $z -DestinationPath $voskDir -Force
        Remove-Item -LiteralPath $z -Force -ErrorAction SilentlyContinue
        Nota "vosk" "ARREGLADO" "modelo Vosk descargado e instalado en local"
    } catch { Nota "vosk" "FALLA" "no se pudo descargar vosk-model-small-es-0.42" }
}

# ------------------------------------------------------------------------------
# 6. Servicios con Antigravity abierto: voz, puente, guardian y ADUANA
# ------------------------------------------------------------------------------
if (-not $SinServicios -and (Get-Process -Name "Antigravity" -ErrorAction SilentlyContinue)) {
    $vozApagada = Test-Path (Join-Path $AG "voice_cache\voz_apagada.flag")
    $espera = if ($AlAbrir) { 60 } else { 20 }   # session_guard los (re)lanza cada 15 s
    $cdp = $null; $faltaSrv = @()
    for ($t = 0; $t -le $espera; $t += 5) {
        $procs = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^pythonw?(\.exe)?$' } | ForEach-Object { "" + $_.CommandLine })
        $faltaSrv = @()
        if (-not ($procs -like "*nova_puente_capturas.py*--daemon*")) { $faltaSrv += "puente de adjuntos" }
        if (-not ($procs -like "*nova_buffer_guardian.py*--daemon*")) { $faltaSrv += "guardian de memoria" }
        if (-not $vozApagada -and -not ($procs -like "*nova_voz.py*")) { $faltaSrv += "voz" }
        $cdp = $null
        if ($faltaSrv.Count -eq 0 -and (Test-Path -LiteralPath $EnvPy)) {
            try { $cdp = (& $EnvPy (Join-Path $G "nova_core\nova_doctor_cdp.py") 2>$null | Select-Object -Last 1) | ConvertFrom-Json } catch { $cdp = $null }
        }
        if ($faltaSrv.Count -eq 0 -and ($vozApagada -or ($cdp -and $cdp.aduana))) { break }
        Start-Sleep -Seconds 5
    }
    if ($faltaSrv.Count -gt 0) {
        Nota "servicios" "FALLA" "no arrancan: $($faltaSrv -join ', ') (mira memory\registros\nova_voice.log)"
    } else {
        Nota "servicios" "OK" "voz, puente de adjuntos y guardian en marcha"
        if ($vozApagada) { Nota "aduana" "AVISO" "la voz esta apagada desde la bandeja: sin aduana, los adjuntos van a la nube" }
        elseif ($cdp -and $cdp.aduana) { Nota "aduana" "OK" ("aduana inyectada en el chat (adjuntos en local)" + $(if ($cdp.mascota) { "" } else { "; mascota no visible" })) }
        else { Nota "aduana" "FALLA" "la voz corre pero la aduana NO esta en el chat: los adjuntos irian a la nube" }
    }
}

# ------------------------------------------------------------------------------
# 7. Resumen
# ------------------------------------------------------------------------------
$fallos = @($res | Where-Object { $_.estado -eq "FALLA" })
$arreglos = @($res | Where-Object { $_.estado -eq "ARREGLADO" })
$avisos = @($res | Where-Object { $_.estado -eq "AVISO" })
$resumen = if ($fallos.Count -eq 0) {
    "Nova Doctor: todo OK" + $(if ($arreglos.Count) { " ($($arreglos.Count) arreglado: " + (($arreglos | ForEach-Object { $_.area }) -join ", ") + ")" } else { "" })
} else {
    "Nova Doctor: $($fallos.Count) fallo(s) - " + (($fallos | ForEach-Object { "$($_.area): $($_.texto)" }) -join " | ")
}
$estadoObj = [ordered]@{
    fecha = (Get-Date -Format "yyyy-MM-dd HH:mm:ss"); maquina = $env:COMPUTERNAME; ok = ($fallos.Count -eq 0)
    resumen = $resumen; fallos = @($fallos | ForEach-Object { "$($_.area): $($_.texto)" })
    arreglos = @($arreglos | ForEach-Object { "$($_.area): $($_.texto)" }); avisos = @($avisos | ForEach-Object { "$($_.area): $($_.texto)" })
    avisado = @()
}
# Estado por equipo: memory\doctor_estado.json es el de ESTE equipo (no viaja: lo excluye el sync)
[IO.File]::WriteAllText($EstadoF, ($estadoObj | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($false)))
Log $resumen
Write-Host ""
Write-Host $resumen -ForegroundColor $(if ($fallos.Count) { "Red" } else { "Green" })

if ($fallos.Count -gt 0 -and -not $SinAviso) {
    try {
        Add-Type -AssemblyName System.Windows.Forms, System.Drawing
        $n = New-Object System.Windows.Forms.NotifyIcon
        $n.Icon = [System.Drawing.SystemIcons]::Warning
        $n.Visible = $true
        $txt = ($fallos | ForEach-Object { "$($_.area): $($_.texto)" }) -join "`n"
        if ($txt.Length -gt 250) { $txt = $txt.Substring(0, 247) + "..." }
        $n.ShowBalloonTip(15000, "Nova Doctor: algo falla", $txt, [System.Windows.Forms.ToolTipIcon]::Warning)
        Start-Sleep -Seconds 16
        $n.Dispose()
    } catch {}
}
$mutex.ReleaseMutex()
exit $(if ($fallos.Count) { 1 } else { 0 })
