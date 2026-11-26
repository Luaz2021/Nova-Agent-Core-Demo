#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$DIR/api_xray.py" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$DIR/api_xray.py" "$@"
else
  echo "[Error] No se encontro Python 3 en el sistema." >&2
  read -r -p "Pulsa Enter para cerrar..."
  exit 1
fi
