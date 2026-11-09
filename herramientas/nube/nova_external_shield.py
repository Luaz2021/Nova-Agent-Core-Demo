"""
Nova External Shield (Blindaje de Capa 1: OpenRouter / Mistral / Fallback)
========================================================================
Regla Sagrada:
- Cero fugas de GitHub, secretos (.env, vault), Trello o codigo interno.
- Si el contexto es privado, sensible o de produccion -> BLOQUEO EXTERNO.
- Si es generico (mock, front basico, boilerplate, dataset) -> OPENROUTER / MISTRAL.
- Si el proveedor externo falla (429, 5xx, timeout) -> AUTO-FAILOVER A NOVA LOCAL.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.error

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# Palabras prohibidas que activan el bloqueo estricto hacia terceros
FORBIDDEN_KEYWORDS = [
    r"\.env",
    r"vault[\\/]",
    r"github",
    r"git\s+",
    r"ghp_[a-zA-Z0-9]+",
    r"trello",
    r"api[_-]?key",
    r"bearer\s+[a-zA-Z0-9_\-\.]+",
    r"password",
    r"connection[_-]?string",
    r"database[_-]?url",
    r"sk-[a-zA-Z0-9]{20,}",
    r"samnailsstudio",
    r"airbnb",
    r"edificio",
    r"bolivar",
]


def es_contenido_sensible(texto: str) -> tuple[bool, str]:
    """Verifica si el texto contiene rutas, credenciales o proyectos protegidos."""
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, texto, re.IGNORECASE):
            return True, f"Patron sensible detectado: {pattern}"
    return False, ""


def invocar_openrouter(prompt: str, system_prompt: str = "", model: str = "cohere/north-mini-code:free", timeout: int = 15):
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None, "OPENROUTER_API_KEY no encontrada"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://nova-agent.local",
        "X-Title": "Nova Core Shield",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    try:
        req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, f"Error OpenRouter: {str(e)}"


def invocar_mistral(prompt: str, system_prompt: str = "", model: str = "codestral-latest", timeout: int = 15):
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        return None, "MISTRAL_API_KEY no encontrada"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    try:
        req = urllib.request.Request(MISTRAL_URL, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, f"Error Mistral: {str(e)}"


def ejecutar_con_blindaje(prompt: str, system_prompt: str = "", es_privado: bool = False, prefer_provider: str = "openrouter"):
    """
    Punto de entrada maestro:
    1. Audita privacidad.
    2. Si es seguro, prueba OpenRouter / Mistral.
    3. Si falla o es privado, auto-failover a Nova interna.
    """
    # 1. Filtro estricto
    if es_privado:
        return {
            "status": "BLOCKED_LOCAL",
            "provider": "NOVA_INTERNA",
            "reason": "Marcado explicitamente como privado",
            "content": None,
        }

    sensible, motivo = es_contenido_sensible(prompt + " " + system_prompt)
    if sensible:
        return {
            "status": "BLOCKED_LOCAL",
            "provider": "NOVA_INTERNA",
            "reason": f"Cortafuegos activo: {motivo}",
            "content": None,
        }

    # 2. Despacho a Capa 1 externa
    content, err = None, None
    if prefer_provider == "mistral":
        content, err = invocar_mistral(prompt, system_prompt)
        provider_used = "MISTRAL_CODESTRAL"
    else:
        content, err = invocar_openrouter(prompt, system_prompt)
        provider_used = "OPENROUTER"

    # Si el preferido falla, intenta el alternativo externo
    if not content and prefer_provider != "mistral":
        content, err = invocar_mistral(prompt, system_prompt)
        if content:
            provider_used = "MISTRAL_FALLBACK"

    if content:
        return {
            "status": "SUCCESS",
            "provider": provider_used,
            "reason": "Generado con exito en Capa 1 externa (0 tokens propios)",
            "content": content,
        }

    # 3. Fallback de rescate
    return {
        "status": "FAILOVER_LOCAL",
        "provider": "NOVA_INTERNA",
        "reason": f"Proveedores externos no disponibles ({err}). Rescate local activado.",
        "content": None,
    }


if __name__ == "__main__":
    test_privado = "Genera codigo con mi clave ghp_1234567890abcdef y revisa el .env"
    res1 = ejecutar_con_blindaje(test_privado)
    print("Test 1 (Privado/Sensible):", res1["status"], "->", res1["reason"])

    test_publico = "Escribe una funcion helper en TypeScript para formatear fechas en formato DD/MM/YYYY"
    res2 = ejecutar_con_blindaje(test_publico)
    print("Test 2 (Publico/Generico):", res2["status"], "-> Proveedor:", res2["provider"])
