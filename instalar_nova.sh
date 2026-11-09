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
    read -r resp < /dev/tty || resp="s"
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

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"
if [ ! -d "$SCRIPT_DIR/adapters" ]; then
    INSTALL_ROOT="$HOME/.nova-agent"
    NUEVO="$HOME/.nova-agent-nuevo"
    if ! command -v git >/dev/null 2>&1; then
        echo "[ERROR] Falta git, que se usa para descargar Nova."
        case "$(uname -s)" in
            Darwin*) echo "        Instalalo con:  xcode-select --install   (o  brew install git)" ;;
            *) echo "        Instalalo con:  sudo apt install git   (Debian/Ubuntu)  o  sudo dnf install git  (Fedora)" ;;
        esac
        exit 1
    fi
    echo "[INFO] Descargando nucleo de Nova en $INSTALL_ROOT..."
    rm -rf "$NUEVO"
    if ! git clone --depth 1 https://github.com/Luaz2021/Nova-Agent-Core-Demo.git "$NUEVO" >/dev/null 2>&1; then
        rm -rf "$NUEVO"
        echo "[ERROR] No se pudo descargar Nova (revisa tu conexion a internet o que github.com este accesible)."
        echo "        Tu instalacion anterior, si la habia, sigue intacta."
        exit 1
    fi
    # Solo con la descarga completa se reemplaza la version anterior (las notas viven en ~/.gemini, no aqui)
    rm -rf "$INSTALL_ROOT"
    mv "$NUEVO" "$INSTALL_ROOT"
    SCRIPT_DIR="$INSTALL_ROOT"
fi

OS_NAME="$(uname -s)"
case "$OS_NAME" in
    Darwin*)
        sh "$SCRIPT_DIR/adapters/macos/install.sh" < /dev/tty
        ;;
    Linux*)
        sh "$SCRIPT_DIR/adapters/linux/install.sh" < /dev/tty
        ;;
    *)
        echo "[ERROR] Sistema operativo no reconocido: $OS_NAME"
        exit 1
        ;;
esac
