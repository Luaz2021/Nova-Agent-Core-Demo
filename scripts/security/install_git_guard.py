"""
Instalador Universal del Hook Fisico de Git (Pre-Commit Guard).
Configura una barrera determinista en .git/hooks/pre-commit que aborta
commits en < 200ms si detecta secretos (entropia de Shannon), archivos .env
o consultas destructivas sin clausula WHERE.
Coste: 0 tokens (Python estandar).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import stat
import sys
from pathlib import Path

GLOBAL_SCRIPTS_DIR = Path(
    r"<NOVA_HOME>\antigravity\scripts\security"
)
SCANNER_PATH = GLOBAL_SCRIPTS_DIR / "entropy_secret_scanner.py"
ORQUESTADOR_PATH = Path(r"<NOVA_HOME>\nova_core\orquestador.py")

HOOK_SHELL_CONTENT = f"""#!/bin/sh
# ==============================================================================
# NOVA PRE-COMMIT GUARDIAN (Big Tech Anti-Leak Shield)
# Bloqueo fisico en 0.2s: Entropia de Shannon, .env y SQL DELETE sin WHERE
# ==============================================================================

echo "[NOVA GUARD] Verificando staging de Git antes del commit..."

# 1. Comprobar archivos .env en staging
STAGED_ENV=$(git diff --cached --name-only | grep -E "(\\.env|\\.env\\.local|\\.pem)$" || true)
if [ -n "$STAGED_ENV" ]; then
    echo "========================================================================"
    echo " [COMMIT ABORTADO] Se intento comitear archivos de entorno sensibles:"
    echo "$STAGED_ENV"
    echo " Por favor retira estos archivos del staging con: git reset HEAD <archivo>"
    echo "========================================================================"
    exit 1
fi

# 2. Comprobar consultas SQL suicidas: DELETE FROM sin WHERE
DANGEROUS_SQL=$(git diff --cached -S"DELETE FROM" | grep -iE "DELETE[[:space:]]+FROM[[:space:]]+[a-zA-Z0-9_]+[[:space:]]*;" || true)
if [ -n "$DANGEROUS_SQL" ]; then
    echo "========================================================================"
    echo " [COMMIT ABORTADO] Detectada consulta destructiva 'DELETE FROM' sin WHERE:"
    echo "$DANGEROUS_SQL"
    echo "========================================================================"
    exit 1
fi

# 3. Escaner de Secretos por Entropia de Shannon (Python)
PYTHON_EXE=$(which python 2>/dev/null || which python3 2>/dev/null || echo "python")
"$PYTHON_EXE" "{str(SCANNER_PATH).replace("\\", "/")}" --staged
SCAN_STATUS=$?

if [ $SCAN_STATUS -ne 0 ]; then
    echo "========================================================================"
    echo " [COMMIT BLOQUEADO] El escaner de secretos de Nova rechazo el commit."
    echo "========================================================================"
    exit 1
fi

# 4. Aduana de Linters y Anti-Fosiles (orquestador.py revisar-staged con autofix + git add)
"$PYTHON_EXE" "{str(ORQUESTADOR_PATH).replace("\\", "/")}" revisar-staged
LINT_STATUS=$?

if [ $LINT_STATUS -ne 0 ]; then
    echo "========================================================================"
    echo " [COMMIT BLOQUEADO] orquestador.py detecto avisos o codigo legacy."
    echo " Corrige los avisos mostrados arriba antes de hacer commit."
    echo "========================================================================"
    exit 1
fi

# 5. Si este hook corre como global (core.hooksPath), encadenar el hook local del repo si existe
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
if [ -n "$GIT_DIR" ] && [ -f "$GIT_DIR/hooks/pre-commit" ]; then
    SELF_REAL=$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")
    LOCAL_REAL=$(cd "$(dirname "$GIT_DIR/hooks/pre-commit")" 2>/dev/null && pwd)/pre-commit
    if [ "$SELF_REAL" != "$LOCAL_REAL" ]; then
        echo "[NOVA GUARD] Ejecutando hook local del repositorio ($GIT_DIR/hooks/pre-commit)..."
        sh "$GIT_DIR/hooks/pre-commit" "$@"
        LOCAL_STATUS=$?
        if [ $LOCAL_STATUS -ne 0 ]; then
            exit $LOCAL_STATUS
        fi
    fi
fi

echo "[NOVA GUARD] Aprobado: Staging limpio y seguro."
exit 0
"""


def find_git_root(start_path: Path) -> Path | None:
    curr = start_path.resolve()
    while curr != curr.parent:
        if (curr / ".git").is_dir():
            return curr
        curr = curr.parent
    return None


def install_hook(repo_path: Path) -> bool:
    git_dir = repo_path / ".git"
    if not git_dir.is_dir():
        print(f"[ERROR] '{repo_path}' no es la raiz de un repositorio Git.")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_file = hooks_dir / "pre-commit"
    with open(hook_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(HOOK_SHELL_CONTENT)

    # Dar permisos de ejecucion (POSIX)
    with contextlib.suppress(OSError):
        st = os.stat(hook_file)
        os.chmod(hook_file, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"[OK] Hook fisico pre-commit instalado en: {hook_file}")
    print("     Protecciones activadas:")
    print("     - Escaner matematico de entropia de Shannon (H >= 4.2)")
    print("     - Bloqueo de archivos .env y claves privadas .pem")
    print("     - Bloqueo de DELETE FROM sin clausula WHERE")
    return True


def uninstall_hook(repo_path: Path) -> bool:
    hook_file = repo_path / ".git" / "hooks" / "pre-commit"
    if hook_file.exists():
        hook_file.unlink()
        print(f"[OK] Hook desinstalado de: {hook_file}")
        return True
    print(f"[INFO] No habia hook en: {hook_file}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instala el hook pre-commit guardian de Nova en cualquier repositorio Git."
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Ruta al repositorio Git (por defecto el directorio actual)",
    )
    parser.add_argument("--uninstall", action="store_true", help="Desinstalar el hook")
    args = parser.parse_args()

    repo_root = find_git_root(Path(args.repo))
    if not repo_root:
        print(
            "[ERROR] No se encontro ninguna carpeta .git en este directorio ni en sus padres."
        )
        return 1

    if args.uninstall:
        return 0 if uninstall_hook(repo_root) else 1
    return 0 if install_hook(repo_root) else 1


if __name__ == "__main__":
    sys.exit(main())
