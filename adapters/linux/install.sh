#!/usr/bin/env sh
# ==============================================================================
# INSTALADOR INTERACTIVO UNIVERSAL DE NOVA AGENT - LINUX (BASH / SH)
# Creado por Saul Martinez (Torrevieja, Espana)
# ==============================================================================
set -e

if [ "$(id -u)" -eq 0 ]; then
    echo "[ERROR] No ejecutes este instalador con sudo. Corre como usuario normal."
    exit 1
fi

clear 2>/dev/null || true
echo "=========================================================="
echo "   BIENVENIDO AL INSTALADOR OFICIAL DE NOVA AGENT (LINUX) "
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
echo "- Puedes activar o desactivar este envio ahora o en cualquier momento."
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

echo ""
echo "[INFO] Configurando a Nova para $nombre ($profesion)..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GEMINI_DIR="$HOME/.gemini/antigravity"

mkdir -p "$GEMINI_DIR/skills"
mkdir -p "$GEMINI_DIR/memory"

cat <<EOF > "$GEMINI_DIR/memory/perfil_usuario.json"
{
  "nombre": "$nombre",
  "profesion": "$profesion",
  "sistema_operativo": "Linux",
  "telemetry_opt_in": $telemetryEnabled,
  "pedagogia_calibrada": "auto_detect"
}
EOF

for skill_path in "$REPO_ROOT/skills"/*; do
    if [ -d "$skill_path" ]; then
        skill_name="$(basename "$skill_path")"
        dest_link="$GEMINI_DIR/skills/$skill_name"
        if [ ! -e "$dest_link" ]; then
            ln -s "$skill_path" "$dest_link" 2>/dev/null || cp -R "$skill_path" "$dest_link"
        fi
    fi
done

TEMPLATES_DIR="$REPO_ROOT/memory_templates"
if [ ! -f "$GEMINI_DIR/memory/tasks.md" ]; then cp "$TEMPLATES_DIR/tasks.template.md" "$GEMINI_DIR/memory/tasks.md"; fi
if [ ! -f "$GEMINI_DIR/memory/napkin.md" ]; then cp "$TEMPLATES_DIR/napkin.template.md" "$GEMINI_DIR/memory/napkin.md"; fi
cp "$REPO_ROOT/GEMINI.md" "$GEMINI_DIR/GEMINI.md"

PROMPT_FILE="$GEMINI_DIR/primer_mensaje.txt"
cat <<EOF > "$PROMPT_FILE"
Hola Nova, soy $nombre ($profesion). Acabo de instalarte en mi equipo.
Presentate oficialmente: cuentame quien eres, tus origenes con Saul Martinez en Torrevieja Espana, tus ventajas frente a otros agentes de IA, tus atajos de trabajo y que extensiones me puedes configurar o recomendar para arrancar.
Ademas, explicame como puedo decirte en cualquier momento: 'Nova, envia mensaje al creador: [mi mensaje]' para hacerle llegar sugerencias o dudas directamente a Saul en su repositorio de GitHub.
EOF

# 6. Verificacion de Motor de Audio (mpv / aplay en Linux)
if command -v mpv >/dev/null 2>&1; then
    echo "[OK] Motor de audio ligero (mpv) detectado."
elif command -v aplay >/dev/null 2>&1; then
    echo "[OK] Motor de audio nativo ALSA (aplay) detectado."
fi

echo ""
echo "=========================================================="
echo "   INSTALACION COMPLETADA CON EXITO PARA $nombre          "
echo "=========================================================="
echo "Pega este primer mensaje al abrir Antigravity o VS Code:"
echo "----------------------------------------------------------"
cat "$PROMPT_FILE"
echo "----------------------------------------------------------"
