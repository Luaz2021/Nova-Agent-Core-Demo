"""
Nova - Asistente de claves (opcional, interactivo). Windows / macOS / Linux.
============================================================================
Pide UNA a UNA las claves gratuitas que usan algunas skills (OpenRouter, Groq, Mistral, YouTube...).
Cada una se puede saltar con Enter. Lo que escribes no se ve en pantalla.

- Se guardan SOLO en tu equipo: ~/.gemini/config/secrets.env (en macOS/Linux con permisos 600).
- Nunca se suben a ningun sitio, no van en los informes y los hooks de Nova impiden que el modelo las lea.
- Puedes repetirlo cuando quieras: "Nova, configura mis claves" o  python nova_claves.py

    python nova_claves.py            (asistente)
    python nova_claves.py --estado   (que claves hay puestas, sin mostrarlas)
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

SECRETS = Path.home() / ".gemini" / "config" / "secrets.env"
CLAVES = [
    ("OPENROUTER_API_KEY", "Router multi-modelo gratis (DeepSeek, Llama, Qwen)", "https://openrouter.ai/keys"),
    ("GROQ_API_KEY", "Transcripcion de audio rapida (Whisper)", "https://console.groq.com/keys"),
    ("MISTRAL_API_KEY", "Revisiones de codigo (Codestral, capa gratis)", "https://console.mistral.ai/api-keys/"),
    ("YOUTUBE_API_KEY", "Busquedas en YouTube sin gastar tokens", "https://console.cloud.google.com/apis/library/youtube.googleapis.com"),
]


def leer() -> dict:
    datos = {}
    try:
        for linea in SECRETS.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                datos[k.strip()] = v.strip()
    except OSError:
        pass
    return datos


def guardar(datos: dict) -> None:
    SECRETS.parent.mkdir(parents=True, exist_ok=True)
    lineas = ["# Claves de Nova (solo en este equipo; nunca se suben). Edita o borra lineas cuando quieras."]
    lineas += [f"{k}={v}" for k, v in datos.items()]
    SECRETS.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(SECRETS, 0o600)


def main() -> int:
    datos = leer()
    if "--estado" in sys.argv:
        for k, desc, _ in CLAVES:
            print(f"  {'[x]' if datos.get(k) else '[ ]'} {k:20} {desc}")
        return 0
    if not sys.stdin or not sys.stdin.isatty():
        print("[CLAVES] Necesito una terminal interactiva. Ejecutalo a mano: python nova_claves.py")
        return 1
    print("\n[CLAVES OPCIONALES] Todas son gratis y sin tarjeta. Enter = saltar (Nova funciona igual sin ellas).")
    print(f"Se guardan solo en tu equipo: {SECRETS}\n")
    cambios = 0
    for k, desc, url in CLAVES:
        puesta = " (ya configurada; Enter = dejarla)" if datos.get(k) else ""
        print(f"- {desc}\n  Consiguela en: {url}")
        try:
            valor = getpass.getpass(f"  {k}{puesta}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if valor:
            datos[k] = valor
            cambios += 1
    if cambios:
        guardar(datos)
        print(f"\n[OK] {cambios} clave(s) guardadas en {SECRETS}")
    else:
        print("\n[OK] Sin cambios.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
