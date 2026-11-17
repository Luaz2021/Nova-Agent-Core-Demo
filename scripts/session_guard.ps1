<#
.SYNOPSIS
    Guardian silencioso de sesion de Antigravity (Nova Session Guard v3.2, Windows).
    - Con Antigravity abierto mantiene vivos el Buffer Guardian, el Puente de adjuntos y Nova Voz (si esta).
    - Al abrir Antigravity: Nova Doctor en segundo plano y, si Nova Sync esta configurado, "sincroniza" (baja).
    - Mientras esta abierto: atiende los pedidos de sync de Nova (memory\pedir_sync.json), porque Antigravity no
      deja a Nova escribir en la unidad de Google Drive. Solo ejecuta nova_sync.py con modos permitidos.
    - Al cerrar Antigravity: apaga los servicios y, si Nova Sync esta configurado, "sube los cambios".
    - v3.2: "abierto" = Antigravity CON VENTANA. Sus procesos auxiliares huerfanos (sidecars) seguian vivos tras
      cerrar y el guardian creia que seguia abierto: nunca apagaba servicios ni guardaba.
#>
$ErrorActionPreference = "SilentlyContinue"
$scriptDir = $PSScriptRoot
$agDir = Split-Path $scriptDir -Parent
$memDir = Join-Path $agDir "memory"
$syncPy = Join-Path $scriptDir "nova_sync.py"
$syncCfg = Join-Path (Split-Path $agDir -Parent) "config\nova_sync.json"
$pedidoSync = Join-Path $memDir "pedir_sync.json"
$resultadoSync = Join-Path $memDir "sync_resultado.txt"

function Test-AntigravityAbierto {
    @(Get-Process -Name "Antigravity" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero }).Count -gt 0
}

. "$scriptDir\nova_python.ps1"
function Get-PyConsola { $p = Get-NovaPython; if ($p -and (Test-Path $p)) { return $p }; return "python.exe" }

function Invoke-NovaSync([string]$modo, [string[]]$extra = @()) {
    if (-not (Test-Path $syncPy)) { return }
    $py = Get-PyConsola
    $out = & $py "$syncPy" $modo @extra 2>&1 | Out-String
    Set-Content -Path $resultadoSync -Value ($out.TrimEnd() + "`r`n[FIN]") -Encoding UTF8
}

function Invoke-PedidoSync {
    if (-not (Test-Path $pedidoSync)) { return }
    $modo = $null; $extra = @()
    try {
        $j = Get-Content $pedidoSync -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($j.modo -in @("bajar", "subir", "espejo", "estado", "configurar")) { $modo = $j.modo }
        $a = @($j.args); $i = 0
        while ($i -lt $a.Count) {   # lista blanca de opciones (nunca --forzar desde el chat)
            if ($a[$i] -in @("--carpeta", "--nombre") -and ($i + 1) -lt $a.Count) { $extra += @($a[$i], [string]$a[$i + 1]); $i += 2; continue }
            if ($a[$i] -in @("--si", "--simular")) { $extra += $a[$i] }
            $i++
        }
    } catch {}
    Remove-Item $pedidoSync -Force -ErrorAction SilentlyContinue
    if ($modo) { Invoke-NovaSync $modo $extra }
}

while ($true) {
    # 1. Esperar a que Antigravity se abra
    while (-not (Test-AntigravityAbierto)) {
        Start-Sleep -Seconds 2
    }

    # 2. Al abrir: Doctor (segundo plano) y "sincroniza" si Nova Sync esta configurado
    $doctorPs = "$scriptDir\nova_doctor.ps1"
    $doctorPy = "$scriptDir\nova_doctor.py"
    if (Test-Path $doctorPy) {   # v3.2: Doctor multiplataforma REPARANDO al abrir (llama tambien al de Windows)
        Start-Process -FilePath (Get-PyConsola) -ArgumentList "`"$doctorPy`" --reparar" -WindowStyle Hidden
    } elseif (Test-Path $doctorPs) {
        Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$doctorPs`" -AlAbrir" -WindowStyle Hidden
    }
    if (Test-Path $syncCfg) { Invoke-NovaSync "bajar" }

    $vozScript  = "$agDir\herramientas\voz\nova_voz.py"
    $vozApagada = "$agDir\voice_cache\voz_apagada.flag"
    $vozPyw = Get-NovaPython -W
    if (-not (Test-Path $vozPyw)) { $vozPyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source }
    $bufferScript = "$scriptDir\nova_buffer_guardian.py"
    $puenteScript = "$scriptDir\nova_puente_capturas.py"
    $pywCmd = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if (-not $pywCmd) { $pywCmd = "pythonw.exe" }

    # 3. Mientras este abierto: servicios vivos (cada 15 s) y pedidos de sync (cada 3 s)
    $sinVentana = 0
    while ($sinVentana -lt 3) {   # 3 revisiones seguidas sin ventana (~9 s) = cerrado
        if (Test-AntigravityAbierto) { $sinVentana = 0 } else { $sinVentana++; Start-Sleep -Seconds 3; continue }
        if (Test-Path $puenteScript) {
            $runningPte = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_puente_capturas.py*--daemon*" }
            if (-not $runningPte) {
                $ptePyw = if ($vozPyw) { $vozPyw } else { $pywCmd }
                Start-Process -FilePath $ptePyw -ArgumentList "`"$puenteScript`" --daemon" -WindowStyle Hidden
            }
        }
        if (Test-Path $bufferScript) {
            $runningBuf = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_buffer_guardian.py*--daemon*" }
            if (-not $runningBuf) {
                $bufPyw = if ($vozPyw) { $vozPyw } else { $pywCmd }
                Start-Process -FilePath $bufPyw -ArgumentList "`"$bufferScript`" --daemon" -WindowStyle Hidden
            }
        }
        if ($vozPyw -and (Test-Path $vozScript) -and -not (Test-Path $vozApagada)) {
            $runningVoz = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_voz.py*" }
            if (-not $runningVoz) {
                Start-Process -FilePath $vozPyw -ArgumentList "`"$vozScript`"" -WindowStyle Hidden
            }
        }
        for ($i = 0; $i -lt 5; $i++) { Invoke-PedidoSync; Start-Sleep -Seconds 3 }
    }

    # 4. Antigravity se CERRO -> apagar servicios
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*nova_buffer_guardian.py*" -or $_.CommandLine -like "*nova_puente_capturas.py*" -or
        ($_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_voz.py*")
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $vozApagada -Force -ErrorAction SilentlyContinue
    $mcpScript = "$scriptDir\nova_mcp.py"
    if ($vozPyw -and (Test-Path $mcpScript)) {
        Start-Process -FilePath $vozPyw -ArgumentList "`"$mcpScript`" apagar" -WindowStyle Hidden -Wait
    }

    # 5. "Sube los cambios" al cerrar (solo si Nova Sync esta configurado)
    if (Test-Path $syncCfg) { Invoke-NovaSync "subir" }

    Start-Sleep -Seconds 5
}
