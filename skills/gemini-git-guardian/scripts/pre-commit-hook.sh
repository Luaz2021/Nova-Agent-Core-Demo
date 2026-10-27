#!/bin/sh
# Git Pre-Commit / Pre-Push Guardian Sentinel
# Bloquea automáticamente commits o pushes con secretos expuestos o SQL destructivo.

echo "🛡️ [Git Guardian] Analizando cambios antes de permitir la operacion..."

# 1. Comprobar API Keys y Secretos de Alto Riesgo
SECRETS_PATTERN="sk_live_[0-9a-zA-Z]{24}|AKIA[0-9A-Z]{16}|ghp_[0-9a-zA-Z]{36}|BEGIN RSA PRIVATE KEY|postgres://.*:.*@|mongodb\+srv://.*:.*@"

MATCHED_SECRETS=$(git diff --cached | grep -E "$SECRETS_PATTERN")

if [ -n "$MATCHED_SECRETS" ]; then
    echo "🚨 [BLOQUEO DE SEGURIDAD] ¡Se ha detectado una API Key o Secreto en el commit!"
    echo "Detalle del riesgo:"
    echo "$MATCHED_SECRETS" | head -n 5
    echo ""
    echo "❌ Operacion cancelada. Mueve la credencial a tu archivo .env y asegurate de que este en .gitignore."
    exit 1
fi

# 2. Comprobar archivos .env rastreados por error
TRACKED_ENV=$(git diff --cached --name-only | grep -E "(^|/)\.env(\..+)?$")
if [ -n "$TRACKED_ENV" ]; then
    echo "🚨 [BLOQUEO DE SEGURIDAD] ¡Estas intentando commitear un archivo .env!"
    echo "Archivo: $TRACKED_ENV"
    echo "❌ Operacion cancelada. Quitalo del staging con 'git reset $TRACKED_ENV' y anadelo a .gitignore."
    exit 1
fi

# 3. Comprobar Sentencias SQL Destructivas Sueltas (El clasico DELETE o DROP sin WHERE inmediato)
BAD_DELETE=$(git diff --cached | grep -iE "^\+[[:space:]]*DELETE[[:space:]]+FROM[[:space:]]+[a-zA-Z0-9_]+[[:space:]]*;")
BAD_DROP=$(git diff --cached | grep -iE "^\+[[:space:]]*DROP[[:space:]]+TABLE[[:space:]]+[a-zA-Z0-9_]+[[:space:]]*;")

if [ -n "$BAD_DELETE" ] || [ -n "$BAD_DROP" ]; then
    echo "🚨 [PELIGRO DE DESTRUCCION DE BD] Se detecto una consulta destructiva sin clausula WHERE valida:"
    echo "$BAD_DELETE"
    echo "$BAD_DROP"
    echo "❌ Operacion cancelada. Revisa que no haya un ';' separando el DELETE del WHERE."
    exit 1
fi

echo "✅ [Git Guardian] Verificacion completada: Codigo seguro. Procediendo..."
exit 0
