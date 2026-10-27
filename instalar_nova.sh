#!/usr/bin/env sh
# ==============================================================================
# INSTALADOR OFICIAL EN 1 LINEA - NOVA AGENT (MACOS / LINUX)
# Detecta Antigravity, ofrece descarga oficial e instala Nova
# ==============================================================================
set -e

echo "=========================================================="
echo "   INSTALADOR OFICIAL - NOVA AGENT (UNIX)                 "
echo "   Copiloto Tecnico Senior & Arquitectura de Software     "
echo "=========================================================="
echo ""

ANTIGRAVITY_FOUND=0
if command -v agy >/dev/null 2>&1 || [ -d "$HOME/.gemini/antigravity" ] || [ -d "/Applications/Antigravity.app" ]; then
    ANTIGRAVITY_FOUND=1
fi

if [ "$ANTIGRAVITY_FOUND" -eq 1 ]; then
    echo "[OK] Google Antigravity detectado en el sistema."
else
    echo "[AVISO] No se detecto Google Antigravity en tu equipo."
    echo "Antigravity es el entorno necesario para que Nova opere."
    printf "Deseas abrir la pagina oficial para descargarlo ahora? (s/n) [s]: "
    read -r resp
    if [ "$resp" != "n" ] && [ "$resp" != "N" ]; then
        if command -v open >/dev/null 2>&1; then
            open "https://antigravity.google/"
        elif command -v xdg-open >/dev/null 2>&1; then
            xdg-open "https://antigravity.google/"
        else
            echo "Abre https://antigravity.google/ en tu navegador."
        fi
    fi
fi

# Si se ejecuta directamente vía curl | bash, no existe la carpeta local.
# Clonamos o descargamos el repositorio temporalmente para ejecutar la instalación.
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"
if [ ! -d "$SCRIPT_DIR/adapters" ]; then
    TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'nova_install')"
    echo "[INFO] Descargando archivos de Nova en entorno temporal..."
    git clone --depth 1 https://github.com/Luaz2021/Nova-Agent-Core-Demo.git "$TMP_DIR" >/dev/null 2>&1 || {
        echo "[ERROR] Se requiere git instalado para clonar el repositorio."
        exit 1
    }
    cd "$TMP_DIR"
    SCRIPT_DIR="$TMP_DIR"
fi

OS_NAME="$(uname -s)"
case "$OS_NAME" in
    Darwin*)
        sh "$SCRIPT_DIR/adapters/macos/install.sh"
        ;;
    Linux*)
        sh "$SCRIPT_DIR/adapters/linux/install.sh"
        ;;
    *)
        echo "[ERROR] Sistema operativo no reconocido: $OS_NAME"
        exit 1
        ;;
esac
