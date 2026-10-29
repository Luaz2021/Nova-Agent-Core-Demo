#!/usr/bin/env bash
# ==============================================================================
# NOVA BUFFER GUARDIAN (macOS / Linux POSIX Runner)
# Creado por Saul Alexander Martinez Rivas (@Luaz2021)
# ==============================================================================
# Ejecuta silenciosamente en segundo plano el monitor de tokens y sesion sin terminal visible.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="python3"

if ! command -v "$PYTHON_EXEC" &> /dev/null; then
    PYTHON_EXEC="python"
fi

if ! command -v "$PYTHON_EXEC" &> /dev/null; then
    echo "[ERROR] Python 3 no esta instalado o no se encuentra en el PATH." >&2
    exit 1
fi

nohup "$PYTHON_EXEC" "$SCRIPT_DIR/nova_buffer_guardian.py" > /dev/null 2>&1 &
echo "[OK] Nova Buffer Guardian iniciado en segundo plano (PID: $!)."
