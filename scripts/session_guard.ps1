<#
.SYNOPSIS
    Guardian silencioso y auto-reparable de sesion de Antigravity (Nova Session Guard v2.2).
    - Detecta cuando Antigravity esta abierto y mantiene vivo Buffer Guardian, Puente Capturas y Nova Voz.
    - v2.2 (09/11, Claude, a pedido de Luaz): Nova Voz (herramientas\voz\nova_voz.py) + mascota arrancan con
      Antigravity y se apagan al cerrarlo. "Salir" en la bandeja de la voz la deja apagada hasta la proxima apertura.
    - En cuanto Antigravity se cierra, apaga los servicios y ejecuta el guardado automatico en Google Drive.
#>
$ErrorActionPreference = "SilentlyContinue"
$scriptDir = $PSScriptRoot

# 09/11 (Claude, a pedido de Luaz): SINCRONIZACION AUTOMATICA. Nova trabaja en el sandbox de Antigravity, que no deja
# tocar G:\ (Drive). Para "Nova, sube los cambios" / "sincroniza" Nova solo escribe memory\pedir_sync.json
# ({"modo":"Subir"} o {"modo":"Bajar"}) y ESTE guardian (fuera del sandbox) ejecuta sync_antigravity.ps1.
# Solo acepta esos dos modos y solo ese script: Nova no gana ningun otro permiso. Resultado: memory\sync_status.json.
$pedidoSync = (Split-Path $scriptDir -Parent) + "\memory\pedir_sync.json"
function Invoke-PedidoSync {
    if (-not (Test-Path $pedidoSync)) { return }
    $modo = "Subir"
    try {
        $j = Get-Content $pedidoSync -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($j.modo -in @("Subir", "Bajar")) { $modo = $j.modo }
    } catch {}
    Remove-Item $pedidoSync -Force -ErrorAction SilentlyContinue
    $syncScript = Join-Path $scriptDir "sync_antigravity.ps1"
    if (Test-Path $syncScript) {
        & powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "$syncScript" -Modo $modo *> $null
    }
}

while ($true) {
    # 1. Esperar a que Antigravity se inicie si no lo esta
    while (-not (Get-Process -Name "Antigravity" -ErrorAction SilentlyContinue)) {
        Start-Sleep -Seconds 2
    }

    # 2. Rutas y ejecutables
    $vozScript  = (Split-Path $scriptDir -Parent) + "\herramientas\voz\nova_voz.py"
    $vozApagada = (Split-Path $scriptDir -Parent) + "\voice_cache\voz_apagada.flag"
    # 11/11 (Claude): NOVA DOCTOR al abrir Antigravity (en segundo plano: no frena el arranque). Revisa Python de Nova,
    # hooks, Ollama, Vosk y, cuando arrancan, voz + puente + aduana. Si algo falla: aviso de Windows y el hook se lo
    # cuenta a Nova en el primer mensaje (memory\doctor_estado.json).
    $doctorPs = "$scriptDir\nova_doctor.ps1"
    if (Test-Path $doctorPs) {
        Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$doctorPs`" -AlAbrir" -WindowStyle Hidden
    }
    # 11/11 (Claude): el pythonw de ESTE equipo (1o el Python propio de Nova), no la ruta de la laptop a mano
    . "$scriptDir\nova_python.ps1"
    $vozPyw = Get-NovaPython -W
    if (-not (Test-Path $vozPyw)) { $vozPyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source }
    $bufferScript = "$scriptDir\nova_buffer_guardian.py"
    $puenteScript = "$scriptDir\nova_puente_capturas.py"
    $pywCmd = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if (-not $pywCmd) { $pywCmd = "C:\Python311\pythonw.exe" }
    if (-not (Test-Path $pywCmd)) { $pywCmd = "pythonw.exe" }

    # 3. Mientras este abierto Antigravity, vigilar Buffer Guardian y Puente Capturas
    while (Get-Process -Name "Antigravity" -ErrorAction SilentlyContinue) {
        # 09/11: el puente de adjuntos va PRIMERO (si Luaz sube algo nada mas abrir, que ya este escuchando) y con el
        # Python directo (el pythonw de WindowsApps es un lanzador intermedio y tarda mas en arrancar).
        if (Test-Path $puenteScript) {
            $runningPte = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_puente_capturas.py*--daemon*" }
            if (-not $runningPte) {
                $ptePyw = if ($vozPyw) { $vozPyw } else { $pywCmd }
                Start-Process -FilePath $ptePyw -ArgumentList "`"$puenteScript`" --daemon" -WindowStyle Hidden
            }
        }
        if (Test-Path $bufferScript) {
            # solo procesos de Python con el script en modo daemon (antes contaba cualquier proceso que nombrara el
            # script, p. ej. una consola que lo mencionaba, y entonces no lo relanzaba: 08/11 el puente estuvo parado)
            $runningBuf = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_buffer_guardian.py*--daemon*" }
            if (-not $runningBuf) {
                # 09/11: con el atajo pythonw de WindowsApps NO arrancaba desde el guardian (hoy 4 de 8 conversaciones
                # sin copia en memory\chat_logs). Python directo, como el puente de adjuntos.
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
        for ($i = 0; $i -lt 5; $i++) {  # 15 s entre revisiones de servicios, mirando cada 3 s si Nova pidio sincronizar
            Invoke-PedidoSync
            Start-Sleep -Seconds 3
        }
    }
    
    # 4. Antigravity se CERRO -> Detener servicios inmediatamente
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*nova_buffer_guardian.py*" -or $_.CommandLine -like "*nova_puente_capturas.py*" -or
        ($_.Name -match '^pythonw?(\.exe)?$' -and $_.CommandLine -like "*nova_voz.py*")
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $vozApagada -Force -ErrorAction SilentlyContinue  # la proxima vez que se abra Antigravity, la voz vuelve
    # 09/11: los MCP de pago fijo (Playwright, Postgres) vuelven a APAGADO; el hook de turno los enciende si Luaz los pide
    $mcpScript = "$scriptDir\nova_mcp.py"
    if ($vozPyw -and (Test-Path $mcpScript)) {
        Start-Process -FilePath $vozPyw -ArgumentList "`"$mcpScript`" apagar" -WindowStyle Hidden -Wait
    }
    
    # 5. Ejecutar guardado de rescate automatico
    $autoSave = "$scriptDir\auto_save_session.ps1"
    if (Test-Path $autoSave) {
        & powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "$autoSave"
    }
    
    Start-Sleep -Seconds 5
}
