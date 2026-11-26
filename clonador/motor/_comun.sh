#!/usr/bin/env bash
# Comun a los lanzadores del clonador en macOS/Linux (v3.3). Equivale a la cabecera de los .bat de Windows.
set -e
cd "$(dirname "$0")"
PY="${NOVA_PYTHON:-$HOME/.gemini/nova_env/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3 || command -v python)"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1
asegurar_ollama() {
  curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && return 0
  command -v ollama >/dev/null 2>&1 || { echo "Ollama no esta instalado: se sigue sin IA local."; return 0; }
  echo "Abriendo Ollama..."; (ollama serve >/dev/null 2>&1 &); sleep 6
}
abrir() {  # abre la revision en el navegador
  if command -v open >/dev/null 2>&1; then open "$1"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1; fi
}
