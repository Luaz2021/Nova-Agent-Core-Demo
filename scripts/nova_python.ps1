# ==============================================================================
# nova_python.ps1 - Busca el Python de ESTE equipo (11/11/2026, Claude)
# ------------------------------------------------------------------------------
# Cada equipo tiene su Python: laptop = instalador nuevo (pythoncore-3.14-64),
# PC de sobremesa = Python 3.13 / 3.11. Antes las rutas de la laptop iban escritas
# a mano y en el PC fallaban sync, voz, guardian y scripts.
#
# Uso desde otro .ps1:
#   . (Join-Path $env:USERPROFILE ".gemini\antigravity\scripts\nova_python.ps1")
#   $py  = Get-NovaPython          # python.exe
#   $pyw = Get-NovaPython -W       # pythonw.exe (sin ventana)
#   Set-NovaPythonEnv              # guarda NOVA_PYTHON y NOVA_PYTHONW (variables de usuario)
#
# Orden: NOVA_PYTHON ya guardada -> 3.14 -> 3.13 -> 3.12 (instalador nuevo y clasico) -> C:\Python3xx -> PATH.
# ==============================================================================

function Get-NovaPythonCandidates {
    $la = $env:LOCALAPPDATA
    $out = @()
    foreach ($v in @("3.14", "3.13", "3.12")) { $out += (Join-Path $la "Python\pythoncore-$v-64\python.exe") }
    foreach ($v in @("314", "313", "312")) { $out += (Join-Path $la "Programs\Python\Python$v\python.exe") }
    foreach ($v in @("314", "313", "312", "311")) { $out += "C:\Python$v\python.exe" }
    $out += (Join-Path $la "Programs\Python\Python311\python.exe")
    return $out
}

function Get-NovaPython([switch]$W) {
    $guardada = $env:NOVA_PYTHON
    if (-not $guardada) { $guardada = [Environment]::GetEnvironmentVariable("NOVA_PYTHON", "User") }
    $cands = @()
    # 11/11: 1o el Python PROPIO de Nova (lo monta nova_doctor.ps1 con uv); no depende del Python de Windows
    $propio = Join-Path $env:USERPROFILE ".gemini\nova_env\Scripts\python.exe"
    if (Test-Path -LiteralPath (Join-Path $env:USERPROFILE ".gemini\nova_env\.huella_nova")) { $cands += $propio }
    if ($guardada) { $cands += $guardada }
    $cands += Get-NovaPythonCandidates
    foreach ($c in $cands) {
        if (-not $c -or -not (Test-Path -LiteralPath $c -PathType Leaf)) { continue }
        if ($W) {
            $cw = Join-Path (Split-Path $c -Parent) "pythonw.exe"
            if (Test-Path -LiteralPath $cw -PathType Leaf) { return $cw }
            continue
        }
        return $c
    }
    # Ultimo recurso: lo que haya en el PATH (evitando el atajo de WindowsApps, que falla en segundo plano)
    $exe = if ($W) { "pythonw.exe" } else { "python.exe" }
    $cmd = Get-Command $exe -All -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" } | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    return $exe
}

function Set-NovaPythonEnv {
    $py = Get-NovaPython
    $pyw = Get-NovaPython -W
    if (-not (Test-Path -LiteralPath $py -PathType Leaf)) { return $null }
    foreach ($par in @(@("NOVA_PYTHON", $py), @("NOVA_PYTHONW", $pyw))) {
        if ([Environment]::GetEnvironmentVariable($par[0], "User") -ne $par[1]) {
            [Environment]::SetEnvironmentVariable($par[0], $par[1], "User")
        }
        Set-Item -Path "Env:$($par[0])" -Value $par[1]
    }
    return $py
}
