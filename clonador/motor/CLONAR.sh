#!/usr/bin/env bash
# CLONAR (macOS/Linux): analizar -> crear -> verificar, todo seguido (sin Qwen, en local).
. "$(dirname "$0")/_comun.sh"
echo "============================================================"
echo " CLONAR: analizar -> crear -> verificar, todo seguido"
echo "============================================================"
read -r -p "URL de la web (Enter = la de url.txt): " URL || true
"$PY" -u clonar.py ${URL:+"$URL"}
ULT="../workspace/ultimo_analisis.txt"
[ -f "$ULT" ] && abrir "$(head -n1 "$ULT")/construccion/revision.html"
