#!/usr/bin/env sh
# ==============================================================================
# INSTALADOR INTERACTIVO DE NOVA AGENT v3.0 - LINUX Y MACOS (SH)
# Zero-Tokens | Escaner de Hardware | IA local opcional (Ollama) | Reglas automaticas (hooks)
# Creado por Saul Alexander Martinez Rivas (@Luaz2021)
# (adapters/linux/install.sh y adapters/macos/install.sh son el mismo script)
# ==============================================================================
set -e

if [ "$(id -u)" -eq 0 ]; then
    echo "[ERROR] No ejecutes este instalador con sudo. Corre como usuario normal."
    exit 1
fi

OS_NAME="$(uname -s)"
case "$OS_NAME" in
    Darwin*) SO="macOS" ;;
    *) SO="Linux" ;;
esac

# ---------------------------------------------------------------- 0. Requisitos: Python >= 3.10
PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$(command -v "$cand")"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[ERROR] Nova necesita Python 3.10 o superior y no lo encuentro."
    if [ "$SO" = "macOS" ]; then
        echo "        Instalalo con:  brew install python   (o desde https://www.python.org/downloads/)"
    else
        echo "        Instalalo con:  sudo apt install python3   (Debian/Ubuntu)  o  sudo dnf install python3  (Fedora)"
    fi
    exit 1
fi

clear 2>/dev/null || true
echo "=========================================================="
echo "   BIENVENIDO AL INSTALADOR OFICIAL DE NOVA AGENT v3.0    "
echo "   Arquitecta de Software & Copiloto Tecnico Senior ($SO) "
echo "=========================================================="
echo ""

printf "Cual es tu nombre o como te gusta que te llamen? [Desarrollador]: "
read -r nombre || nombre=""
if [ -z "$nombre" ]; then nombre="Desarrollador"; fi

echo ""
echo "[PRIVACIDAD Y MEJORA CONTINUA]"
echo "Si quieres ayudar a mejorar Nova, una vez al mes te propondra enviar un informe con:"
echo "- las lecciones que aprendio, las entradas nuevas de tu servilleta y el TIPO de errores que cometio."
echo "- Nada de tu equipo, tus proyectos, rutas, correos ni claves. Tu lo revisas y decides si lo envias."
printf "Quieres que Nova te lo proponga? (s/n) [s]: "
read -r optIn || optIn=""
telemetryEnabled="true"
if [ "$optIn" = "n" ] || [ "$optIn" = "N" ]; then telemetryEnabled="false"; fi

echo ""
echo "En que te enfocas o cual es tu profesion/estudios?"
echo "  [1] Estudiante (DAM / DAW / Informatica / Ingenieria)"
echo "  [2] Desarrollador Frontend / Web (React, Next.js, UI)"
echo "  [3] Desarrollador Backend / Datos (Java, Spring, Python, SQL)"
echo "  [4] Fullstack / DevOps / Ciberseguridad"
echo "  [5] Emprendedor / No-Programador (Quiero crear proyectos)"
printf "Elige una opcion [1-5]: "
read -r profOpcion || profOpcion=""

case "$profOpcion" in
    1) profesion="Estudiante de Informatica / Desarrollo de Software"; pedagogia="mentor_didactico" ;;
    2) profesion="Desarrollador Frontend & UI"; pedagogia="socio_trinchera" ;;
    3) profesion="Desarrollador Backend & Bases de Datos"; pedagogia="socio_trinchera" ;;
    4) profesion="Ingeniero Fullstack & DevSecOps"; pedagogia="socio_trinchera" ;;
    5) profesion="Emprendedor / Constructor de Productos Digitales"; pedagogia="producto_llave_en_mano" ;;
    *) profesion="Desarrollador de Software"; pedagogia="auto_detect" ;;
esac

# ---------------------------------------------------------------- 1. Escaner de hardware (0 tokens)
echo ""
echo "----------------------------------------------------------"
echo "[ESCANER DE HARDWARE NOVA] Analizando tu equipo..."

if [ "$SO" = "macOS" ]; then
    cpuName="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon / Mac')"
    ramBytes="$(sysctl -n hw.memsize 2>/dev/null || echo 8589934592)"
    ramGB="$((ramBytes / 1073741824))"
    gpuName="$(system_profiler SPDisplaysDataType 2>/dev/null | awk -F': ' '/Chipset Model/ {print $2; exit}')"
    [ -z "$gpuName" ] && gpuName="GPU Integrada Mac"
else
    cpuName="$(awk -F': ' '/model name/ {print $2; exit}' /proc/cpuinfo 2>/dev/null)"
    [ -z "$cpuName" ] && cpuName="CPU Linux"
    ramKb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null)"
    [ -z "$ramKb" ] && ramKb=8388608
    ramGB="$(( (ramKb + 524288) / 1048576 ))"
    gpuName="$(lspci 2>/dev/null | grep -iE 'vga|3d|display' | head -n 1 | cut -d: -f3 | sed 's/^ //')"
    [ -z "$gpuName" ] && gpuName="GPU Estandar"
fi
freeDiskGB="$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print int($4 / 1048576)}')"
[ -z "$freeDiskGB" ] && freeDiskGB=25

echo "  - Procesador : $cpuName"
echo "  - Memoria RAM: ${ramGB} GB"
echo "  - Tarjeta GPU: $gpuName"
echo "  - Disco Libre: ${freeDiskGB} GB"

quiereIA="false"
if [ "$ramGB" -lt 12 ] || [ "$freeDiskGB" -lt 15 ]; then
    hwTier="BASICO_CLOUD_ONLY"
    echo "  - Veredicto  : MODO NUBE (protegemos tu RAM y tu bateria; sin IA local)"
elif [ "$ramGB" -ge 16 ]; then
    hwTier="OPTIMO_GPU"
    echo "  - Veredicto  : POTENCIA OPTIMA PARA IA LOCAL"
    printf "Activo la IA local (Ollama + qwen3.5:9b + InternVL3.5 8B, ~12 GB)? (s/n) [s]: "
    read -r askAi || askAi=""
    if [ "$askAi" != "n" ] && [ "$askAi" != "N" ]; then quiereIA="true"; fi
else
    hwTier="GAMA_MEDIA"
    echo "  - Veredicto  : GAMA MEDIA (IA local ligera opcional)"
    printf "Activo la IA local ligera (Ollama + qwen3.5:4b + InternVL3.5 4B, ~6,5 GB)? (s/n) [n]: "
    read -r askAi || askAi=""
    if [ "$askAi" = "s" ] || [ "$askAi" = "S" ]; then quiereIA="true"; fi
fi
echo "----------------------------------------------------------"

# ---------------------------------------------------------------- 2. Copiar Nova a ~/.gemini
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GEMINI_HOME="$HOME/.gemini"
GEMINI_DIR="$GEMINI_HOME/antigravity"
CONFIG_DIR="$GEMINI_HOME/config"

mkdir -p "$GEMINI_DIR/skills" "$GEMINI_DIR/memory" "$GEMINI_DIR/scripts" "$GEMINI_DIR/almacen" "$CONFIG_DIR/skills" "$GEMINI_HOME/nova_core"

# Perfil: lo escribe Python para que cualquier nombre (comillas, tildes...) quede como JSON valido.
# Si ya existia (reinstalacion), se conservan los datos que el instalador no pregunta (p. ej. la IA local).
NOVA_NOMBRE="$nombre" NOVA_PROFESION="$profesion" NOVA_SO="$SO" NOVA_TELEMETRIA="$telemetryEnabled" \
NOVA_PEDAGOGIA="$pedagogia" NOVA_CPU="$cpuName" NOVA_RAM="$ramGB" NOVA_GPU="$gpuName" NOVA_DISCO="$freeDiskGB" \
NOVA_TIER="$hwTier" NOVA_PERFIL="$GEMINI_DIR/memory/perfil_usuario.json" "$PY" - <<'PYEOF'
import json, os, time
ruta = os.environ["NOVA_PERFIL"]
try:
    with open(ruta, encoding="utf-8-sig") as f:
        perfil = json.load(f)
except (OSError, ValueError):
    perfil = {}
e = os.environ
perfil.update({
    "nombre": e["NOVA_NOMBRE"], "profesion": e["NOVA_PROFESION"], "sistema_operativo": e["NOVA_SO"],
    "fecha_instalacion": time.strftime("%Y-%m-%d %H:%M:%S"), "pedagogia_calibrada": e["NOVA_PEDAGOGIA"],
    "telemetry_opt_in": e["NOVA_TELEMETRIA"] == "true",
    "hardware": {"cpu": e["NOVA_CPU"], "ram_gb": int(e["NOVA_RAM"] or 0), "gpu": e["NOVA_GPU"],
                 "free_disk_gb": int(e["NOVA_DISCO"] or 0), "tier": e["NOVA_TIER"]},
})
perfil.setdefault("ia_local", {"instalada": False, "modelo": "ninguno", "modelo_vl": "ninguno",
                               "regla_activacion": "solo_tareas_masivas_mayor_1500_tokens"})
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(perfil, f, indent=2, ensure_ascii=False)
PYEOF

# Skills: enlaces al repositorio (si no se puede enlazar, copia)
for skill_path in "$REPO_ROOT/skills"/*; do
    if [ -d "$skill_path" ]; then
        skill_name="$(basename "$skill_path")"
        for target_skills_dir in "$GEMINI_DIR/skills" "$CONFIG_DIR/skills"; do
            dest_link="$target_skills_dir/$skill_name"
            if [ ! -e "$dest_link" ]; then
                ln -s "$skill_path" "$dest_link" 2>/dev/null || cp -R "$skill_path" "$dest_link"
            fi
        done
    fi
done

# Scripts (con subcarpetas), nucleo (hooks, redactor) y biblioteca de webs
cp -R "$REPO_ROOT/scripts/." "$GEMINI_DIR/scripts/"
cp -R "$REPO_ROOT/nova_core/." "$GEMINI_HOME/nova_core/"
cp -R "$REPO_ROOT/almacen/." "$GEMINI_DIR/almacen/"
mkdir -p "$GEMINI_DIR/herramientas" "$GEMINI_DIR/clonador"
cp -R "$REPO_ROOT/herramientas/." "$GEMINI_DIR/herramientas/"
cp -R "$REPO_ROOT/clonador/." "$GEMINI_DIR/clonador/"
cp "$REPO_ROOT/manifest_master.json" "$GEMINI_DIR/manifest_master.json"
find "$GEMINI_DIR/scripts" "$GEMINI_HOME/nova_core" "$GEMINI_DIR/almacen" "$GEMINI_DIR/herramientas" "$GEMINI_DIR/clonador" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

# Plantillas de memoria (nunca se pisan las notas del usuario)
TEMPLATES_DIR="$REPO_ROOT/memory_templates"
[ -f "$GEMINI_DIR/memory/tasks.md" ] || cp "$TEMPLATES_DIR/tasks.template.md" "$GEMINI_DIR/memory/tasks.md"
[ -f "$GEMINI_DIR/memory/napkin.md" ] || cp "$TEMPLATES_DIR/napkin.template.md" "$GEMINI_DIR/memory/napkin.md"
cp "$TEMPLATES_DIR/napkin.template.md" "$GEMINI_DIR/memory/napkin_oficial.md"
if [ -f "$TEMPLATES_DIR/protocolo_costos_nova_claude.md" ]; then
    cp "$TEMPLATES_DIR/protocolo_costos_nova_claude.md" "$GEMINI_DIR/memory/protocolo_costos_nova_claude.md"
fi

# Reglas: inyeccion UNICA de GEMINI.md en ~/.gemini/config/GEMINI.md
cp "$REPO_ROOT/GEMINI.md" "$CONFIG_DIR/GEMINI.md"
rm -f "$GEMINI_HOME/GEMINI.md"
if [ -f "$REPO_ROOT/AYUDA.md" ]; then cp "$REPO_ROOT/AYUDA.md" "$CONFIG_DIR/AYUDA.md"; fi

# Reglas automaticas (hooks): el sistema vigila las leyes, no el modelo
"$PY" "$GEMINI_HOME/nova_core/instalar_hooks.py" || echo "[AVISO] No se pudieron registrar los hooks (Nova funciona igual)."

# ---------------------------------------------------------------- 3. IA local (opcional)
if [ "$quiereIA" = "true" ]; then
    "$PY" "$GEMINI_DIR/scripts/nova_instalar_ia_local.py" --perfil "$hwTier" < /dev/tty || \
        echo "[AVISO] La IA local no quedo lista. Repitelo cuando quieras: \"$PY\" \"$GEMINI_DIR/scripts/nova_instalar_ia_local.py\""
fi

# ---------------------------------------------------------------- 4. Claves opcionales (tipo "iniciar sesion")
echo ""
printf "Quieres configurar ahora tus claves gratuitas opcionales (OpenRouter, Groq...)? (s/n) [n]: "
read -r askKeys || askKeys=""
if [ "$askKeys" = "s" ] || [ "$askKeys" = "S" ]; then
    "$PY" "$GEMINI_DIR/scripts/nova_claves.py" < /dev/tty || true
fi

echo ""
echo "[CONFIGURACION DE PERMISOS DEL IDE]"
echo "Nova respeta siempre la Ley 1 (pedir tu permiso en el chat antes de tocar tu codigo)."
printf "Habilito la lectura fluida de ~/.gemini/antigravity/memory y skills sin popups? (s/n) [s]: "
read -r askTurbo || askTurbo=""
if [ "$askTurbo" != "n" ] && [ "$askTurbo" != "N" ] && [ ! -f "$CONFIG_DIR/config.json" ]; then
    printf '{\n  "userSettings": {\n    "nonWorkspaceFileAccessPolicy": "AGENT_SETTING_POLICY_ALLOW"\n  }\n}\n' > "$CONFIG_DIR/config.json"
    echo "[OK] Lectura fluida de skills/memoria habilitada (Ley 1 intacta)."
fi

PROMPT_FILE="$GEMINI_DIR/primer_mensaje.txt"
printf 'Hola Nova, soy %s (%s). Verifica mi perfil_usuario.json y confirmame en 2 o 3 lineas que todo esta listo.\n' "$nombre" "$profesion" > "$PROMPT_FILE"

# Portapapeles: macOS (pbcopy), Linux Wayland (wl-copy) o X11 (xclip / xsel)
if command -v pbcopy >/dev/null 2>&1; then pbcopy < "$PROMPT_FILE" 2>/dev/null || true
elif command -v wl-copy >/dev/null 2>&1; then wl-copy < "$PROMPT_FILE" 2>/dev/null || true
elif command -v xclip >/dev/null 2>&1; then xclip -selection clipboard < "$PROMPT_FILE" 2>/dev/null || true
elif command -v xsel >/dev/null 2>&1; then xsel --clipboard --input < "$PROMPT_FILE" 2>/dev/null || true
fi

echo ""
echo "=========================================================================="
echo "   NOVA AGENT v3.0 - INSTALACION COMPLETADA ($nombre)"
echo "   Arquitectura creada por Saul Alexander Martinez Rivas (@Luaz2021)"
echo "=========================================================================="
echo "ATAJOS RAPIDOS EN EL CHAT:"
echo "  - 'hola' / 'continuamos'        -> Retoma tu sesion donde la dejaste."
echo "  - '/ayuda' o 'ayuda'            -> Guia completa (AYUDA.md)."
echo "  - 'Nuevo proyecto: [idea]'      -> Planifica el sprint contigo antes de picar codigo."
echo "  - 'Nova, hazme una web para...' -> Web minimalista desde la biblioteca (0 tokens de nube)."
echo "  - 'Nova, instala la IA local'   -> Ollama + modelos locales cuando quieras."
echo "  - 'Nova, busca actualizaciones' -> Parches oficiales sin tocar tus notas."
echo ""
echo "LINEA DIRECTA CON EL CREADOR (SAUL MARTINEZ):"
echo "  - '/creador [mensaje]'          -> Envia una duda, idea o saludo."
echo "  - '/reportar-fallo'             -> Envia un fallo resuelto para mejorar el Core."
echo "  - '/enviar-informe'             -> Lecciones y errores de Nova (tu lo revisas antes)."
echo "=========================================================================="
echo "Pega este primer mensaje al abrir Antigravity (ya esta en tu portapapeles si se pudo):"
cat "$PROMPT_FILE"
echo "=========================================================================="
