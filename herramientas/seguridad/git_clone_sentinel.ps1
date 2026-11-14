<#
.SYNOPSIS
    Git Clone Sentinel Wrapper
    Intercepta 'git clone' para escanear automaticamente proyectos de terceros en <400ms a 0 tokens.
    Ubicacion: <NOVA_HOME>\antigravity\herramientas\seguridad\git_clone_sentinel.ps1
#>

function git-clone-guard {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$GitArgs
    )

    # 1. Ejecutar el comando git original
    & (Get-Command -CommandType Application -Name git).Source @GitArgs
    $gitExit = $LASTEXITCODE

    if ($gitExit -ne 0) {
        return $gitExit
    }

    # 2. Si fue un comando 'clone', auditar el resultado inmediatamente
    if ($GitArgs -and $GitArgs[0] -eq "clone") {
        $targetDir = $null
        # El destino puede ser el ultimo argumento o deducirse de la URL
        if ($GitArgs.Count -ge 3 -and -not ($GitArgs[2].StartsWith("-"))) {
            $targetDir = $GitArgs[2]
        } elseif ($GitArgs.Count -ge 2) {
            $url = $GitArgs[1]
            $repoName = [System.IO.Path]::GetFileNameWithoutExtension($url.TrimEnd('/'))
            if ($repoName) {
                $targetDir = Join-Path (Get-Location) $repoName
            }
        }

        if ($targetDir -and (Test-Path $targetDir)) {
            $scanner = (Join-Path $PSScriptRoot "nova_repo_scanner.py")
            if (-not (Test-Path $scanner)) {
                $scanner = (Join-Path $PSScriptRoot "nova_repo_scanner.py")
            }
            if (Test-Path $scanner) {
                # 09/11: en el sandbox de Antigravity el atajo python.exe no funciona -> ruta completa
                # 11/11: el Python de ESTE equipo (laptop 3.14, PC 3.13/3.11)
                . (Join-Path $env:USERPROFILE ".gemini\antigravity\scripts\nova_python.ps1")
                $pyNova = Get-NovaPython
                & $pyNova "$scanner" "$targetDir"
            }
        }
    }
}

# Alias opcional
Set-Alias -Name git-safe -Value git-clone-guard
