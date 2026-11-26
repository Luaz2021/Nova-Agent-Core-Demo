#!/usr/bin/env bash
# PASO 2 (macOS/Linux): crear la base del clon (sin IA, 2-4 minutos).
. "$(dirname "$0")/_comun.sh"
"$PY" -u crear.py
echo "Terminado. Siguiente: 3_VERIFICAR.sh"
