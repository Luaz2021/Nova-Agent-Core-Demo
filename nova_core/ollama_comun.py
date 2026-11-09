"""
Modulo comun de conexion y auto-arranque de Ollama para Nova-Core (Capa 0 Local).

Centraliza `ensure_ollama_service()` para que todos los scripts locales
(nova_local_worker.py, redactor.py, resumir.py, auditar_hoja_vl.py) levanten
el demonio `ollama serve` automaticamente si esta detenido.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request

OLLAMA_BASE_URL = "http://127.0.0.1:11434/"
_ANTIGRAVITY = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity")
_DEFECTOS = {"coder": "qwen3.5:9b", "vl": "blaifa/InternVL3_5:8b"}


def modelo_nova(clave: str = "coder") -> str:
    """Modelo local de Nova para 'coder' o 'vl'. Orden: el elegido para ESTE equipo (memory/perfil_usuario.json,
    ia_local.modelo / ia_local.modelo_vl) -> catalogo scripts/nova_modelos.json -> defecto."""
    import json

    def _leer(ruta: str) -> dict:
        try:
            with open(ruta, encoding="utf-8-sig") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    ia = _leer(os.path.join(_ANTIGRAVITY, "memory", "perfil_usuario.json")).get("ia_local") or {}
    elegido = ia.get("modelo_vl" if clave == "vl" else "modelo") if isinstance(ia, dict) else ""
    if elegido and elegido != "ninguno":
        return str(elegido)
    catalogo = _leer(os.path.join(_ANTIGRAVITY, "scripts", "nova_modelos.json"))
    return str(catalogo.get(clave) or _DEFECTOS.get(clave, _DEFECTOS["coder"]))


def ruta_ollama() -> str | None:
    """Ejecutable de Ollama aunque no este en el PATH (instalaciones tipicas de Windows y macOS)."""
    cmd = shutil.which("ollama")
    if cmd:
        return cmd
    candidatos = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        "/Applications/Ollama.app/Contents/Resources/ollama",
        "/usr/local/bin/ollama",
        "/opt/homebrew/bin/ollama",
    ]
    return next((c for c in candidatos if os.path.exists(c)), None)


def ensure_ollama_service(url: str = OLLAMA_BASE_URL) -> bool:
    """Verifica si Ollama responde en 127.0.0.1:11434; si no, lo arranca en segundo plano."""
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            if b"Ollama is running" in r.read():
                return True
    except OSError:
        pass

    ollama_cmd = ruta_ollama()
    if not ollama_cmd:
        return False

    flags = 0x08000000 if sys.platform == "win32" else 0
    subprocess.Popen(
        [ollama_cmd, "serve"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    for _ in range(20):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                if b"Ollama is running" in r.read():
                    return True
        except OSError:
            continue
    return False  # no arranco: quien llama debe frenar (antes devolvia True y el fallo pasaba en silencio)


# ---------- Llamada a Qwen bien configurada (la usan nova_pipeline_local.py y nova_local_worker.py) ----------
# - /api/chat nativo: es la unica ruta donde se puede apagar el modo "pensar" de qwen3.5 ("think": False).
#   Por /v1/chat/completions piensa sin limite y se agotaba el tiempo (07/11: "timed out" -> la nube pico el codigo).
# - num_ctx explicito: sin el, Ollama usa 4096 y una web se corta a mitad del CSS (08/11: index.html sin <body>).
# - keep_alive por llamada: el OLLAMA_KEEP_ALIVE=0 del sistema descarga el modelo tras cada llamada.
# - done_reason == "length": la respuesta se corto por tope de tokens -> se devuelve marcada, nunca como buena.
CTX_QWEN = 24576
PREDICT_QWEN = 16384


def generar_qwen(
    prompt: str,
    modelo: str,
    sistema: str = "",
    num_predict: int = PREDICT_QWEN,
    num_ctx: int = CTX_QWEN,
    temperatura: float = 0.1,
    timeout: int = 900,
) -> tuple[str, bool]:
    """Devuelve (texto, cortado). cortado=True si Qwen agoto los tokens: el resultado esta incompleto."""
    import json

    mensajes = ([{"role": "system", "content": sistema}] if sistema else []) + [
        {"role": "user", "content": prompt}
    ]
    datos = {
        "model": modelo,
        "messages": mensajes,
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {"temperature": temperatura, "num_predict": num_predict, "num_ctx": num_ctx},
    }
    req = urllib.request.Request(
        OLLAMA_BASE_URL + "api/chat",
        data=json.dumps(datos).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    texto = (res.get("message") or {}).get("content", "")
    return texto, res.get("done_reason") == "length"
