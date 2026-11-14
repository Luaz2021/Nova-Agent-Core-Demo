<#
.SYNOPSIS
    Helper de Pruebas Fantasma para Nova y Alexander.
    Permite aislar codigo, crear una rama efimera en Git o un sandbox temporal,
    ejecutar la prueba y, si falla, descartar sin dejar rastro en la rama activa.
#>
param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "status", # create, discard, diff, sandbox
    [string]$BaseBranch = "main"
)

$ErrorActionPreference = "SilentlyContinue"

$isGit = git rev-parse --is-inside-work-tree 2>$null

if ($isGit -eq "true") {
    $currentBranch = (git branch --show-current).Trim()
    
    switch ($Action) {
        "create" {
            $hash = [System.Guid]::NewGuid().ToString().Substring(0, 8)
            $phantomBranch = "phantom-fix-$hash"
            git checkout -b $phantomBranch 2>$null | Out-Null
            [PSCustomObject]@{
                Status = "Created"
                OriginalBranch = $currentBranch
                PhantomBranch = $phantomBranch
            } | ConvertTo-Json
        }
        "discard" {
            if ($currentBranch -like "phantom-fix-*") {
                git checkout $BaseBranch 2>$null | Out-Null
                if ($LASTEXITCODE -ne 0) { git checkout master 2>$null | Out-Null }
                git branch -D $currentBranch 2>$null | Out-Null
                [PSCustomObject]@{
                    Status = "Discarded"
                    Message = "Rama fantasma descartada sin rastro."
                } | ConvertTo-Json
            }
        }
        "diff" {
            git diff "$BaseBranch..HEAD" 2>$null
        }
        default {
            [PSCustomObject]@{
                IsGit = $true
                CurrentBranch = $currentBranch
            } | ConvertTo-Json
        }
    }
} else {
    $sandboxDir = "$env:USERPROFILE\.gemini\antigravity\scratch\phantom_sandbox"
    New-Item -ItemType Directory -Path $sandboxDir -Force | Out-Null
    [PSCustomObject]@{
        IsGit = $false
        Sandbox = $sandboxDir
    } | ConvertTo-Json
}
