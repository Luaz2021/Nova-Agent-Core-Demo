"""
Nova Local Worker v2.0 (Obrero Local Portable + Contrato 2-Llamadas Consenso Claude)
====================================================================================
- Lee dinamicamente ~/.gemini/antigravity/memory/perfil_usuario.json (o Google Drive en Central)
  para detectar que modelo instalo el Escaner de Hardware (qwen2.5-coder:7b, qwen2.5-coder:3b)
  o si el equipo es Basico (ia_local.instalada = false), evitando ahogar equipos sin RAM/GPU.
- Soporta ejecucion clasica (--task / --file) y Modo Contrato 1-Shot (--brief-json + auto-test)
  para que Nova Cloud gaste maximo 2 llamadas API (Brief -> Reporte compacto con unittest).
"""

import os
import sys
import json
import re
import time
import shutil
import argparse
import urllib.request
import subprocess


def get_memory_dir():
    """Carpeta de memoria 100% local en Community Edition (Sin sincronizacion Cloud)."""
    local_mem = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "memory"))
    os.makedirs(local_mem, exist_ok=True)
    return local_mem


def load_local_ai_config():
    """Lee perfil_usuario.json para saber el modelo asignado al hardware del usuario."""
    perfil_path = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "memory", "perfil_usuario.json"))
    if not os.path.exists(perfil_path):
        perfil_path = os.path.join(get_memory_dir(), "perfil_usuario.json")

    default_cfg = {
        "instalada": True,
        "modelo": "qwen2.5-coder:7b",
        "tier": "OPTIMO_GPU",
        "regla_activacion": "solo_tareas_masivas_mayor_1500_tokens",
    }
    if os.path.exists(perfil_path):
        try:
            with open(perfil_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ia_cfg = data.get("ia_local", {})
            hw_cfg = data.get("hardware", {})
            return {
                "instalada": bool(ia_cfg.get("instalada", True)),
                "modelo": ia_cfg.get("modelo") or "qwen2.5-coder:7b",
                "tier": hw_cfg.get("tier", "OPTIMO_GPU"),
                "regla_activacion": ia_cfg.get("regla_activacion", "solo_tareas_masivas_mayor_1500_tokens"),
            }
        except Exception:
            pass
    return default_cfg


def clean_markdown_code(text):
    """Extrae el bloque de codigo puro evitando artefactos de markdown."""
    m = re.search(r"```(?:[a-zA-Z0-9_\-\+]+)?\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def ensure_ollama_service():
    """Verifica si Ollama responde en 127.0.0.1:11434; si no, lo arranca en Windows/macOS/Linux."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/", timeout=2) as r:
            if b"Ollama is running" in r.read():
                return True
    except Exception:
        pass

    ollama_cmd = shutil.which("ollama")
    if not ollama_cmd and sys.platform == "win32":
        cand = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        if os.path.exists(cand):
            ollama_cmd = cand

    if ollama_cmd:
        subprocess.Popen(
            [ollama_cmd, "serve"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
        time.sleep(2.5)
        return True
    return False


def run_local_coder(prompt, model_name=None, system_instructions=None):
    cfg = load_local_ai_config()
    if not cfg["instalada"] or cfg["modelo"] == "ninguno":
        raise RuntimeError(
            f"[BLOQUEO HARDWARE] Este equipo ({cfg['tier']}) tiene la IA Local desactivada para proteger RAM/Bateria. "
            "Usa Ejecucion 1-Shot Consolidada directamente en la nube."
        )

    chosen_model = model_name or cfg["modelo"]
    if not system_instructions:
        system_instructions = (
            "Eres un programador senior de elite. Genera codigo conciso, limpio, robusto y con early returns "
            "bajo filosofia KISS. Devuelve EXCLUSIVAMENTE codigo ejecutable sin introducciones ni despedidas."
        )

    ensure_ollama_service()
    payload = {
        "model": chosen_model,
        "messages": [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.15,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        raw_code = result["choices"][0]["message"]["content"].strip()
        return clean_markdown_code(raw_code), chosen_model


def main():
    parser = argparse.ArgumentParser(description="Nova Local Worker v2.0 - Obrero Local Portable (Consenso Claude)")
    parser.add_argument("--task", type=str, help="Prompt o tarea directa en linea de comandos")
    parser.add_argument("--file", type=str, help="Ruta al archivo con la tarea a procesar")
    parser.add_argument("--out", type=str, help="Ruta donde escribir el archivo generado")
    parser.add_argument("--model", type=str, default=None, help="Forzar modelo especifico de Ollama")
    parser.add_argument("--test-cmd", type=str, default=None, help="Comando unittest opcional para validar salida en 1 solo paso")
    parser.add_argument("--check-config", action="store_true", help="Imprime la configuracion de IA local detectada y sale")
    args = parser.parse_args()

    cfg = load_local_ai_config()
    if args.check_config:
        print(f"[CONFIG IA LOCAL] Instalada={cfg['instalada']} | Modelo={cfg['modelo']} | Tier={cfg['tier']} | Regla={cfg['regla_activacion']}")
        sys.exit(0)

    mem_dir = get_memory_dir()
    task_prompt = ""
    if args.task:
        task_prompt = args.task
    elif args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8") as f:
            task_prompt = f.read()
    else:
        default_task = os.path.join(mem_dir, "tasks_local_worker.md")
        if os.path.exists(default_task):
            with open(default_task, "r", encoding="utf-8") as f:
                task_prompt = f.read()

    if not task_prompt:
        print("[ERROR] No se indico ninguna tarea (--task, --file o tasks_local_worker.md).")
        sys.exit(1)

    try:
        code, used_model = run_local_coder(task_prompt, model_name=args.model)
    except Exception as e:
        print(str(e))
        sys.exit(2)

    out_file = args.out or os.path.join(mem_dir, "resultado_local_worker.md")
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(code)

    test_status = "N/A"
    if args.test_cmd:
        res_t = subprocess.run(args.test_cmd, shell=True, capture_output=True, text=True)
        test_status = "OK" if res_t.returncode == 0 else f"FALLO ({res_t.stderr.strip()[-200:]})"

    print(f"[OBRERO LOCAL v2.0 OK] Modelo={used_model} | Salida={out_file} ({len(code):,} chars) | Tests={test_status}")


if __name__ == "__main__":
    main()
