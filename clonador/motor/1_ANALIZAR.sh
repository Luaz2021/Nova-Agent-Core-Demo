#!/usr/bin/env bash
# PASO 1-3 (macOS/Linux): analizar una web (script + fotos + Qwen con ojos si esta instalado).
. "$(dirname "$0")/_comun.sh"
URL="$( [ -f url.txt ] && head -n1 url.txt || true )"
echo "Web en url.txt: $URL"
read -r -p "Pega otra URL o pulsa Enter para usar esa: " NUEVA || true
[ -n "$NUEVA" ] && URL="$NUEVA"
echo "$URL" > url.txt
echo "Preparando Python (solo tarda la primera vez)..."
"$PY" -m pip install -q playwright pillow numpy >/dev/null 2>&1 || true
"$PY" -m playwright install chromium >/dev/null 2>&1 || true
asegurar_ollama
OJOS=""; ollama show qwen2.5vl:7b >/dev/null 2>&1 || { echo "Qwen con ojos no esta instalado: se analiza sin ojos."; OJOS="--sin-ojos"; }
echo "Analizando $URL (3-6 minutos)..."
"$PY" -u analizar.py "$URL" $OJOS || { echo "Esta web no se pudo analizar: mira el aviso de arriba y prueba otra."; exit 1; }
echo "Terminado (los informes estan en pruebas_Qwen/)."
