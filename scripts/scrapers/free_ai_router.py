r"""
Free AI Router Client (OpenRouter Free Tier + Mistral / Codestral)
Ubicacion: scripts/scrapers/free_ai_router.py
Principio API/CLI First: Resuelve consultas generales, revisiones de codigo y razonamiento logico
a COSTE CERO de creditos de Antigravity usando OpenRouter (:free) y Mistral.
"""

import os
import sys
import json
import subprocess


def load_secrets():
    secrets = {}
    candidates = [
        os.path.expanduser("~/.gemini/config/secrets.env"),
        os.path.expanduser("~/.gemini/antigravity/vault/secrets.env"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            secrets[k.strip()] = v.strip()
                if secrets:
                    return secrets
            except Exception:
                pass
    return secrets


SECRETS = load_secrets()
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY") or SECRETS.get("OPENROUTER_API_KEY")
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY") or SECRETS.get("MISTRAL_API_KEY")


def call_openrouter(prompt, model="nvidia/nemotron-3.5-lightning:free", system_prompt="Eres un asistente conciso y tecnico. Responde en español directo al grano."):
    if not OPENROUTER_KEY:
        return {"error": "Falta OPENROUTER_API_KEY. Configura ~/.gemini/config/secrets.env o define la variable de entorno."}

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    })

    try:
        res = subprocess.run(
            [
                "curl.exe", "-s", "-X", "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                "-H", f"Authorization: Bearer {OPENROUTER_KEY}",
                "-H", "Content-Type: application/json",
                "-H", "HTTP-Referer: https://github.com/Luaz2021/Nova-Agent-Core-Demo",
                "-H", "X-Title: Nova-Copilot-Engine",
                "-d", payload
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=35
        )
        data = json.loads(res.stdout)
        if "choices" in data and data["choices"]:
            msg = data["choices"][0]["message"]["content"]
            return {"status": "ok", "provider": "OpenRouter", "model": model, "response": msg}
        return {"status": "error", "raw": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def call_mistral(prompt, model="codestral-latest", system_prompt="Eres un experto senior en desarrollo de software y arquitectura limpia. Se conciso y directo."):
    if not MISTRAL_KEY:
        return {"error": "Falta MISTRAL_API_KEY. Configura ~/.gemini/config/secrets.env o define la variable de entorno."}

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    })

    try:
        res = subprocess.run(
            [
                "curl.exe", "-s", "-X", "POST",
                "https://api.mistral.ai/v1/chat/completions",
                "-H", f"Authorization: Bearer {MISTRAL_KEY}",
                "-H", "Content-Type: application/json",
                "-d", payload
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30
        )
        data = json.loads(res.stdout)
        if "choices" in data and data["choices"]:
            msg = data["choices"][0]["message"]["content"]
            return {"status": "ok", "provider": "MistralAI", "model": model, "response": msg}
        return {"status": "error", "raw": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Uso:")
        print('  python free_ai_router.py ask "<pregunta>" [modelo_openrouter]')
        print('  python free_ai_router.py code "<consulta_codigo>" (usa Codestral de Mistral)')
        sys.exit(1)

    cmd = sys.argv[1].lower()
    text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "code":
        out = call_mistral(text, model="codestral-latest")
        if out.get("status") != "ok":
            out = call_openrouter(text, model="cohere/north-mini-code:free")
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif cmd == "mistral":
        out = call_mistral(text, model="mistral-small-latest")
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        out = call_openrouter(text)
        print(json.dumps(out, ensure_ascii=False, indent=2))
