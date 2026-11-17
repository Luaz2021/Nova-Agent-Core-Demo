# ==============================================================================
# NOVA - PACK DE VOZ (Windows). Voces oficiales: Ayla (Nova) y Marina (guardian y videos).
# Motor local Qwen3-TTS 1.7B (Apache 2.0) acelerado con faster-qwen3-tts (MIT). ~9 GB en %USERPROFILE%\nova_voz_clon.
# Necesita GPU NVIDIA con 6 GB de VRAM o mas. Sin el pack, Nova usa la voz de Windows.
# LAS VOCES AYLA Y MARINA NO SON MIT: solo se pueden usar dentro de Nova (LICENCIA_VOCES.md). Hay que aceptarla.
# Receta probada: Python 3.12, torch cu128, faster-qwen3-tts 0.5.4, transformers 5.15.1 (la 5.23 rompe el modelo).
# ==============================================================================
$ErrorActionPreference = "Stop"
$aqui = $PSScriptRoot
$base = Join-Path $env:USERPROFILE "nova_voz_clon"

Write-Host "== Pack de voz de Nova ==" -ForegroundColor Cyan

# 1. Equipo: GPU NVIDIA, VRAM y disco
$smi = (Get-Command nvidia-smi -ErrorAction SilentlyContinue).Source
if (-not $smi) {
    Write-Host "[NO] No hay GPU NVIDIA (o falta su driver). El pack de voz necesita una. Nova seguira con la voz de Windows." -ForegroundColor Yellow
    exit 2
}
$linea = (& $smi --query-gpu=name,memory.total --format=csv,noheader,nounits | Select-Object -First 1)
$gpu = $linea.Split(",")[0].Trim(); $vram = [int]$linea.Split(",")[1].Trim()
$libre = [math]::Round((Get-PSDrive ($env:USERPROFILE.Substring(0, 1))).Free / 1GB, 1)
Write-Host "  GPU: $gpu ($vram MB) | Disco libre: $libre GB"
if ($vram -lt 6000) { Write-Host "[NO] Hacen falta 6 GB de VRAM o mas (tienes $vram MB). Nova seguira con la voz de Windows." -ForegroundColor Yellow; exit 2 }
if ($libre -lt 12) { Write-Host "[NO] Hacen falta 12 GB libres (tienes $libre GB)." -ForegroundColor Yellow; exit 2 }

# 2. Licencia de las voces (obligatoria)
$lic = @((Join-Path $aqui "LICENCIA_VOCES.md"), (Join-Path $aqui "..\..\LICENCIA_VOCES.md")) | Where-Object { Test-Path $_ } | Select-Object -First 1
Write-Host ""
Write-Host "LICENCIA DE LAS VOCES AYLA Y MARINA (resumen; completa en LICENCIA_VOCES.md de esta carpeta):" -ForegroundColor Yellow
Write-Host "  - Son voces de dos personas reales, espanolas, que las autorizan SOLO y EXCLUSIVAMENTE para usarlas dentro de Nova."
Write-Host "  - NO son MIT. Prohibido: extraerlas o distribuirlas, clonarlas con otras herramientas, entrenar modelos con ellas,"
Write-Host "    suplantar a sus titulares, contenido sexual, de odio, politico, publicitario o enganoso, y el uso comercial sin permiso escrito."
Write-Host "  - Permitido: que Nova te hable (Ayla), avisos del guardian (Marina) y narrar tus videos de Nova sin fines comerciales (Marina)."
Write-Host "  - Se rige por la ley espanola: el mal uso puede acarrear acciones civiles y penales (LO 1/1982, RGPD/LOPDGDD, Codigo Penal)."
if ($lic) { Write-Host "  Texto completo: $((Resolve-Path $lic).Path)" }
$r = Read-Host "Escribe ACEPTO para aceptar la licencia e instalar (cualquier otra cosa cancela)"
if ($r -cne "ACEPTO") { Write-Host "Cancelado. Nova seguira con la voz de Windows." -ForegroundColor Yellow; exit 1 }
New-Item -ItemType Directory -Force $base, "$base\voces", "$base\salidas" | Out-Null
@{ acepto = $true; fecha = (Get-Date -Format "yyyy-MM-dd HH:mm:ss"); equipo = $env:COMPUTERNAME; licencia = "LICENCIA_VOCES.md" } |
    ConvertTo-Json | Set-Content -Path (Join-Path $base "licencia_voces_aceptada.json") -Encoding UTF8

# 3. Entorno de voz (uv; si falta, lo monta el Nova Doctor)
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
if (-not (Test-Path $uv)) { Write-Host "Falta uv: di 'Nova, revisate' (el Doctor lo instala) y repite." -ForegroundColor Red; exit 1 }
$env:UV_HTTP_TIMEOUT = "600"
$py = Join-Path $base "env_fq\Scripts\python.exe"
if (-not (Test-Path $py)) { & $uv venv (Join-Path $base "env_fq") --python 3.12 }
Write-Host "PyTorch con CUDA 12.8 (~3 GB)..." -ForegroundColor Cyan
& $uv pip install --python $py torch torchaudio --index-url https://download.pytorch.org/whl/cu128
Write-Host "faster-qwen3-tts y librerias..." -ForegroundColor Cyan
& $uv pip install --python $py "faster-qwen3-tts==0.5.4" "transformers==5.15.1" soundfile sounddevice numpy huggingface_hub
Write-Host "Modelo Qwen3-TTS 1.7B Base (~4,2 GB)..." -ForegroundColor Cyan
$env:HF_HUB_DISABLE_SYMLINKS = "1"   # Windows sin permiso de enlaces simbolicos: carpeta normal
$destino = Join-Path $base "modelo"
& $py -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-Base', local_dir=r'$destino')"
& $py (Join-Path $aqui "clonador.py") estado
Write-Host "[OK] Pack de voz listo. Nova hablara con Ayla y el guardian con Marina (cierra y abre Antigravity)." -ForegroundColor Green
