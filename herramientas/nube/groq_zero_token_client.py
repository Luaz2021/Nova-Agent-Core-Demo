r"""
Groq Zero-Token Offloader Client (Whisper Audio + Llama 3.3 70B Summarizer)
Ubicacion: <NOVA_HOME>\antigravity\herramientas\nube\groq_zero_token_client.py
Principio API/CLI First: Procesa textos gigantes o transcribe audios gratis en la nube de Groq
para no consumir creditos de contexto en Antigravity ni bateria local.
"""

import os
import sys
import json
import subprocess


def get_groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    for letter in "GDEFGHIJKLMNOPQRSTUVWXYZC":
        for sub in [r"Mi unidad\Antigravity\vault\google_cloud.env", r"My Drive\Antigravity\vault\google_cloud.env"]:
            vault_path = os.path.join(f"{letter}:\\", sub)
            if os.path.exists(vault_path):
                try:
                    with open(vault_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("GROQ_API_KEY="):
                                return line.strip().split("=", 1)[1].strip()
                except Exception:
                    pass
    return None


def summarize_or_ask(prompt_text, system_prompt="Eres un asistente tecnico conciso. Responde en español directo al grano."):
    key = get_groq_key()
    if not key:
        print(json.dumps({"error": "No se encontro GROQ_API_KEY en vault/google_cloud.env"}))
        return

    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    })

    try:
        res = subprocess.run(
            [
                "curl.exe", "-s", "-X", "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                "-H", f"Authorization: Bearer {key}",
                "-H", "Content-Type: application/json",
                "-d", payload
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=25
        )
        data = json.loads(res.stdout)
        if "choices" in data and data["choices"]:
            answer = data["choices"][0]["message"]["content"]
            print(json.dumps({"status": "ok", "model": data.get("model"), "response": answer}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"status": "error", "raw": data}, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Uso: python groq_zero_token_client.py "<texto o pregunta>"')
        sys.exit(1)
    summarize_or_ask(" ".join(sys.argv[1:]))
