#!/usr/bin/env sh
# ==============================================================================
# NOVA - PACK DE VOZ (macOS con chip Apple y Linux con GPU NVIDIA).
# Voces oficiales: Ayla (Nova) y Marina (guardian y videos). Motor local Qwen3-TTS 1.7B.
#   - Mac con chip Apple (M1, M2, M3, M4...): mlx-audio sobre MLX (memoria unificada), modelo en 8 bits (~2 GB).
#     EXPERIMENTAL hasta probarlo en Macs reales.
#   - Linux con NVIDIA: faster-qwen3-tts con CUDA (~9 GB).
#   - Mac Intel o equipos sin NVIDIA: no compatible (solo CPU, muy lento): Nova usa la voz del sistema.
# LAS VOCES AYLA Y MARINA NO SON MIT: solo se pueden usar dentro de Nova (LICENCIA_VOCES.md). Hay que aceptarla.
# ==============================================================================
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
BASE="$HOME/nova_voz_clon"
echo "== Pack de voz de Nova =="

LIBRE="$(df -Pk "$HOME" | awk 'NR==2 {print int($4 / 1048576)}')"
MOTOR=""
if [ "$(uname -s)" = "Darwin" ]; then
    if [ "$(uname -m)" != "arm64" ]; then
        echo "[NO] Este Mac es Intel: el motor de voz necesita un chip Apple (M1 o posterior) o una GPU NVIDIA."
        echo "     Nova seguira con la voz del sistema (say)."
        exit 2
    fi
    RAM="$(( $(sysctl -n hw.memsize) / 1073741824 ))"
    echo "  Mac con chip Apple ($(sysctl -n machdep.cpu.brand_string 2>/dev/null)) | RAM: ${RAM} GB | Disco libre: ${LIBRE} GB"
    [ "$RAM" -lt 8 ] && { echo "[NO] Hacen falta 8 GB de memoria o mas."; exit 2; }
    [ "$LIBRE" -lt 6 ] && { echo "[NO] Hacen falta 6 GB libres."; exit 2; }
    [ "$RAM" -lt 16 ] && echo "  Aviso: con ${RAM} GB funcionara, pero mejor con 16 GB si a la vez usas la IA local."
    MOTOR="mlx"
else
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo "[NO] No hay GPU NVIDIA (o falta su driver). Nova seguira con la voz del sistema."
        exit 2
    fi
    VRAM="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -d ' ')"
    echo "  GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1) (${VRAM} MB) | Disco libre: ${LIBRE} GB"
    [ "$VRAM" -lt 6000 ] && { echo "[NO] Hacen falta 6 GB de VRAM o mas."; exit 2; }
    [ "$LIBRE" -lt 12 ] && { echo "[NO] Hacen falta 12 GB libres."; exit 2; }
    MOTOR="cuda"
fi

echo ""
echo "LICENCIA DE LAS VOCES AYLA Y MARINA (resumen; completa en LICENCIA_VOCES.md de esta carpeta):"
echo "  - Son voces de dos personas reales, espanolas, que las autorizan SOLO y EXCLUSIVAMENTE para usarlas dentro de Nova."
echo "  - NO son MIT. Prohibido: extraerlas o distribuirlas, clonarlas con otras herramientas, entrenar modelos con ellas,"
echo "    suplantar a sus titulares, contenido sexual, de odio, politico, publicitario o enganoso, y el uso comercial sin permiso escrito."
echo "  - Permitido: que Nova te hable (Ayla), avisos del guardian (Marina) y narrar tus videos de Nova sin fines comerciales (Marina)."
echo "  - Se rige por la ley espanola: el mal uso puede acarrear acciones civiles y penales (LO 1/1982, RGPD/LOPDGDD, Codigo Penal)."
printf "Escribe ACEPTO para aceptar la licencia e instalar (cualquier otra cosa cancela): "
read -r R < /dev/tty || R=""
[ "$R" = "ACEPTO" ] || { echo "Cancelado. Nova seguira con la voz del sistema."; exit 1; }
mkdir -p "$BASE/voces" "$BASE/salidas"
printf '{"acepto": true, "fecha": "%s", "equipo": "%s", "licencia": "LICENCIA_VOCES.md"}\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$(hostname)" > "$BASE/licencia_voces_aceptada.json"

PY="$BASE/env_fq/bin/python"
if command -v uv >/dev/null 2>&1; then
    [ -x "$PY" ] || uv venv "$BASE/env_fq" --python 3.12
    PIP="uv pip install --python $PY"
else
    [ -x "$PY" ] || python3 -m venv "$BASE/env_fq"
    PIP="$PY -m pip install"
fi
if [ "$MOTOR" = "mlx" ]; then
    echo "mlx-audio y librerias (MLX, chip Apple)..."
    $PIP mlx-audio soundfile sounddevice numpy huggingface_hub
    echo "Modelo Qwen3-TTS 1.7B Base en 8 bits para MLX (~2 GB)..."
    "$PY" -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit', local_dir='$BASE/modelo_mlx')"
else
    echo "PyTorch con CUDA 12.8 (~3 GB)..."
    $PIP torch torchaudio --index-url https://download.pytorch.org/whl/cu128
    echo "faster-qwen3-tts y librerias..."
    $PIP "faster-qwen3-tts==0.5.4" "transformers==5.15.1" soundfile sounddevice numpy huggingface_hub
    echo "Modelo Qwen3-TTS 1.7B Base (~4,2 GB)..."
    "$PY" -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-Base', local_dir='$BASE/modelo')"
fi
"$PY" "$AQUI/clonador.py" estado
echo "Prueba: \"$PY\" \"$AQUI/clonador.py\" hablar --voz nova --texto \"Hola, soy Nova\""
echo "[OK] Pack de voz listo. Nova hablara con Ayla y el guardian con Marina."
