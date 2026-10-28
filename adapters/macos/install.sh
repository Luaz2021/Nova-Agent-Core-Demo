#!/usr/bin/env sh
# ==============================================================================
# INSTALADOR INTERACTIVO UNIVERSAL DE NOVA AGENT v2.0 - MACOS (ZSH / SH)
# Zero-Tokens | Escaner de Hardware Inteligente | Inyeccion Unica Optimizada
# Creado por Saul Alexander Martinez Rivas (@Luaz2021 - Torrevieja, Espana)
# ==============================================================================
set -e

if [ "$(id -u)" -eq 0 ]; then
    echo "[ERROR] No ejecutes este instalador con sudo. Corre como usuario normal."
    exit 1
fi

clear 2>/dev/null || true
echo "=========================================================="
echo "   BIENVENIDO AL INSTALADOR OFICIAL DE NOVA AGENT v2.0    "
echo "   Arquitecta de Software & Copiloto Tecnico Senior       "
echo "=========================================================="
echo ""

printf "Cual es tu nombre o como te gusta que te llamen? [Desarrollador]: "
read -r nombre
if [ -z "$nombre" ]; then nombre="Desarrollador"; fi

echo ""
echo "[AVISO DE PRIVACIDAD Y MEJORA CONTINUA]"
echo "Nova Agent esta basado en Google Gemini. Para mejorar y evolucionar el sistema:"
echo "- Una vez al mes genera un resumen anonimo de manifiesto (skills y errores esquivados)."
echo "- Cero rutas privadas, cero codigo confidencial, cero contrasenas."
printf "Deseas habilitar la telemetria etica anonima? (s/n) [s]: "
read -r optIn
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
read -r profOpcion

case "$profOpcion" in
    1) profesion="Estudiante de Informatica / Desarrollo de Software" ;;
    2) profesion="Desarrollador Frontend & UI" ;;
    3) profesion="Desarrollador Backend & Bases de Datos" ;;
    4) profesion="Ingeniero Fullstack & DevSecOps" ;;
    5) profesion="Emprendedor / Constructor de Productos Digitales" ;;
    *) profesion="Desarrollador de Software" ;;
esac

# 2. ESCANER DE HARDWARE INTELIGENTE (0 TOKENS)
echo ""
echo "----------------------------------------------------------"
echo "[ESCANER DE HARDWARE NOVA] Analizando especificaciones de tu equipo..."

if [ "$(uname -s)" = "Darwin" ]; then
    cpuName="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon / Mac')"
    ramBytes="$(sysctl -n hw.memsize 2>/dev/null || echo 8589934592)"
    ramGB="$((ramBytes / 1073741824))"
    gpuName="$(system_profiler SPDisplaysDataType 2>/dev/null | awk -F': ' '/Chipset Model/ {print $2; exit}' || echo 'GPU Integrada Mac')"
else
    cpuName="$(awk -F': ' '/model name/ {print $2; exit}' /proc/cpuinfo 2>/dev/null || echo 'CPU Linux')"
    ramKb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 8388608)"
    ramGB="$((ramKb / 1048576))"
    gpuName="$(lspci 2>/dev/null | grep -iE 'vga|3d|display' | head -n 1 | cut -d: -f3 | sed 's/^ //' || echo 'GPU Estandar')"
fi
freeDiskGB="$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print int($4 / 1048576)}' || echo 25)"

echo "  - Procesador : $cpuName"
echo "  - Memoria RAM: ${ramGB} GB"
echo "  - Tarjeta GPU: $gpuName"
echo "  - Disco Libre: ${freeDiskGB} GB disponibles"

localAiInstalled="false"
localAiModel="ninguno"
hwTier="BASICO_CLOUD_ONLY"

if [ "$ramGB" -lt 12 ] || [ "$freeDiskGB" -lt 15 ]; then
    hwTier="BASICO_CLOUD_ONLY"
    echo "  - Veredicto  : MODO NUBE EXCLUSIVO (Proteccion de RAM y Bateria)"
    echo "----------------------------------------------------------"
    echo "[OPTIMIZACION AUTOMATICA] Tu equipo tiene ${ramGB} GB de RAM / ${freeDiskGB} GB libres."
    echo "Para proteger la fluidez y bateria de tu equipo, Nova NO instalara IA local"
    echo "y operara con el Modo 1-Shot Cloud Optimizado (~38% menos consumo de tokens)."
elif [ "$ramGB" -ge 16 ]; then
    hwTier="OPTIMO_GPU"
    echo "  - Veredicto  : POTENCIA OPTIMA PARA IA LOCAL"
    echo "----------------------------------------------------------"
    printf "Tu equipo tiene potencia para el Obrero Local (Qwen 2.5 Coder 7B). Deseas activarlo? (s/n) [s]: "
    read -r askAi
    if [ "$askAi" != "n" ] && [ "$askAi" != "N" ]; then
        localAiModel="qwen2.5-coder:7b"
        localAiInstalled="true"
    fi
else
    hwTier="GAMA_MEDIA"
    echo "  - Veredicto  : GAMA MEDIA (Opcional Obrero Ligero 3B)"
    echo "----------------------------------------------------------"
    printf "Deseas instalar el Obrero Local Ligero (Qwen 2.5 Coder 3B - 1.9 GB)? (s/n) [n]: "
    read -r askAi
    if [ "$askAi" = "s" ] || [ "$askAi" = "S" ]; then
        localAiModel="qwen2.5-coder:3b"
        localAiInstalled="true"
    fi
fi

if [ "$localAiInstalled" = "true" ] && command -v ollama >/dev/null 2>&1; then
    echo "[INFO] Descargando modelo $localAiModel en Ollama..."
    ollama pull "$localAiModel" || true
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GEMINI_DIR="$HOME/.gemini/antigravity"
CONFIG_DIR="$HOME/.gemini/config"

mkdir -p "$GEMINI_DIR/skills" "$GEMINI_DIR/memory" "$GEMINI_DIR/scripts" "$CONFIG_DIR/skills"

cat <<EOF > "$GEMINI_DIR/memory/perfil_usuario.json"
{
  "nombre": "$nombre",
  "profesion": "$profesion",
  "sistema_operativo": "macOS",
  "telemetry_opt_in": $telemetryEnabled,
  "pedagogia_calibrada": "auto_detect",
  "hardware": {
    "cpu": "$cpuName",
    "ram_gb": $ramGB,
    "gpu": "$gpuName",
    "free_disk_gb": $freeDiskGB,
    "tier": "$hwTier"
  },
  "ia_local": {
    "instalada": $localAiInstalled,
    "modelo": "$localAiModel",
    "regla_activacion": "solo_tareas_masivas_mayor_1500_tokens"
  }
}
EOF

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

for script_file in "$REPO_ROOT/scripts"/*; do
    if [ -f "$script_file" ]; then
        cp "$script_file" "$GEMINI_DIR/scripts/"
    fi
done

TEMPLATES_DIR="$REPO_ROOT/memory_templates"
if [ ! -f "$GEMINI_DIR/memory/tasks.md" ]; then cp "$TEMPLATES_DIR/tasks.template.md" "$GEMINI_DIR/memory/tasks.md"; fi
if [ ! -f "$GEMINI_DIR/memory/napkin.md" ]; then cp "$TEMPLATES_DIR/napkin.template.md" "$GEMINI_DIR/memory/napkin.md"; fi
if [ -f "$TEMPLATES_DIR/protocolo_costos_nova_claude.md" ]; then cp "$TEMPLATES_DIR/protocolo_costos_nova_claude.md" "$GEMINI_DIR/memory/protocolo_costos_nova_claude.md"; fi

# Inyeccion UNICA de GEMINI.md en ~/.gemini/config/GEMINI.md
cp "$REPO_ROOT/GEMINI.md" "$CONFIG_DIR/GEMINI.md"
rm -f "$HOME/.gemini/GEMINI.md"
if [ -f "$REPO_ROOT/AYUDA.md" ]; then cp "$REPO_ROOT/AYUDA.md" "$CONFIG_DIR/AYUDA.md"; fi

echo ""
echo "[CONFIGURACION DE PERMISOS DEL IDE]"
echo "Nova respeta siempre la Ley 1 (pedir tu permiso en el chat antes de tocar tu codigo)."
printf "Deseas habilitar lectura fluida de ~/.gemini/antigravity/memory y skills sin popups? (s/n) [s]: "
read -r askTurbo
if [ "$askTurbo" != "n" ] && [ "$askTurbo" != "N" ] && [ ! -f "$CONFIG_DIR/config.json" ]; then
cat <<EOF > "$CONFIG_DIR/config.json"
{
  "userSettings": {
    "nonWorkspaceFileAccessPolicy": "AGENT_SETTING_POLICY_ALLOW"
  }
}
EOF
echo "[OK] Lectura fluida de skills/memoria habilitada (Sandbox de terminal y Ley 1 intactos)."
fi

PROMPT_FILE="$GEMINI_DIR/primer_mensaje.txt"
cat <<EOF > "$PROMPT_FILE"
Hola Nova, soy $nombre ($profesion). Verifica mi perfil_usuario.json y confirmame en 2 o 3 lineas que todo esta listo.
EOF

if command -v pbcopy >/dev/null 2>&1; then pbcopy < "$PROMPT_FILE" 2>/dev/null || true; fi

echo ""
echo "=========================================================================="
echo "   NOVA COPILOT ENGINE v2.0 - INSTALACION COMPLETADA ($nombre)"
echo "   Arquitectura creada por Saul Alexander Martinez Rivas (@Luaz2021)"
echo "=========================================================================="
echo "ATAJOS RAPIDOS EN EL CHAT (Coste 0 tokens de redaccion):"
echo "  - 'hola' / 'continuamos'        -> Retoma tu sesion exactamente donde la dejaste."
echo "  - '/ayuda' o 'ayuda'            -> Muestra la guia completa desde AYUDA.md."
echo "  - 'Nuevo proyecto: [idea]'      -> Planifica el sprint contigo antes de picar codigo."
echo "  - 'Nova analiza este proyecto'  -> Radiografia Tanque de 7 Puntos (Stack, UI, SEO, Seguridad)."
echo "  - 'te lo dejo en tus manos'     -> Modo autonomo: desarrollo 1-Shot + tests en verde."
echo ""
echo "LINEA DIRECTA CON EL CREADOR (SAUL MARTINEZ):"
echo "  - '/creador [mensaje]'          -> Envia una duda, idea o saludo directo al buzon de Saul."
echo "  - '/reportar-fallo'             -> Envia un bug resuelto para mejorar el Core."
echo "  - '/compartir-skill [nombre]'   -> Propone una skill tuya para incluirla con creditos."
echo "  - '/actualizar-nova'            -> Busca e instala mejoras oficiales sin borrar tus notas."
echo "=========================================================================="
echo "Pega este primer mensaje corto al abrir Antigravity:"
cat "$PROMPT_FILE"
echo "=========================================================================="
