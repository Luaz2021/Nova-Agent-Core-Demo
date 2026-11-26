#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PY_EXE=""
if [[ -n "${NOVA_PYTHON:-}" && -x "${NOVA_PYTHON}" ]]; then
  PY_EXE="$NOVA_PYTHON"
elif [[ -x "$HOME/.gemini/nova_env/bin/python" ]]; then
  PY_EXE="$HOME/.gemini/nova_env/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_EXE="python3"
elif command -v python >/dev/null 2>&1; then
  PY_EXE="python"
else
  echo "[Error] No se encontro Python 3 en el sistema." >&2
  exit 1
fi

exec "$PY_EXE" "$DIR/api_xray.py" "$@"
