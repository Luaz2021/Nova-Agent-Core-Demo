#!/usr/bin/env bash
# PASO 3 (macOS/Linux): cada seccion contra la original (si no llega al 90 %, Qwen la repara hasta 3 veces).
. "$(dirname "$0")/_comun.sh"
asegurar_ollama
read -r -p "Verificar solo las primeras N secciones? (numero, o Enter = todas): " N || true
"$PY" -u verificar.py ${N:+--solo=$N}
ULT="pruebas_Qwen/ultimo_analisis.txt"
[ -f "$ULT" ] && abrir "$(head -n1 "$ULT")/construccion/revision.html"
