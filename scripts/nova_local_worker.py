"""
Nova Local Worker v2.0 (Obrero Local Portable + Contrato 2-Llamadas Consenso Claude)
====================================================================================
- Lee dinamicamente ~/.gemini/antigravity/memory/perfil_usuario.json (o Google Drive en Central)
  para detectar que modelo instalo el Escaner de Hardware (qwen2.5-coder:7b, qwen2.5-coder:3b)
  o si el equipo es Basico (ia_local.instalada = false), evitando ahogar equipos sin RAM/GPU.
- Soporta ejecucion clasica (--task / --file) y Modo Contrato 1-Shot (--brief-json + auto-test)
  para que Nova Cloud gaste maximo 2 llamadas API (Brief -> Reporte compacto con unittest).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".gemini" / "nova_core"))
from ollama_comun import ensure_ollama_service, generar_qwen


def get_memory_dir():
    """Sync v4: memoria siempre en ~/.gemini/antigravity/memory; Drive es solo respaldo."""
    local_mem = os.path.expanduser(
        os.path.join("~", ".gemini", "antigravity", "memory")
    )
    os.makedirs(local_mem, exist_ok=True)
    return local_mem


def modelo_nova(clave, defecto):
    """Nombre del modelo Qwen desde scripts/nova_modelos.json (unico sitio para cambiar de version)."""
    try:
        with open(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "nova_modelos.json"
            ),
            encoding="utf-8",
        ) as f:
            return json.load(f)[clave]
    except Exception:
        return defecto


CODER_NOVA = modelo_nova("coder", "qwen3.5:9b")


def load_local_ai_config():
    """Lee perfil_usuario.json para saber el modelo asignado al hardware del usuario."""
    perfil_path = os.path.expanduser(
        os.path.join("~", ".gemini", "antigravity", "memory", "perfil_usuario.json")
    )
    if not os.path.exists(perfil_path):
        perfil_path = os.path.join(get_memory_dir(), "perfil_usuario.json")

    default_cfg = {
        "instalada": True,
        "modelo": CODER_NOVA,
        "tier": "OPTIMO_GPU",
        "regla_activacion": "solo_tareas_masivas_mayor_1500_tokens",
    }
    if os.path.exists(perfil_path):
        try:
            with open(perfil_path, encoding="utf-8") as f:
                data = json.load(f)
            ia_cfg = data.get("ia_local", {})
            hw_cfg = data.get("hardware", {})
            return {
                "instalada": bool(ia_cfg.get("instalada", True)),
                "modelo": ia_cfg.get("modelo") or CODER_NOVA,
                "tier": hw_cfg.get("tier", "OPTIMO_GPU"),
                "regla_activacion": ia_cfg.get(
                    "regla_activacion", "solo_tareas_masivas_mayor_1500_tokens"
                ),
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

    if not ensure_ollama_service():
        raise RuntimeError("[CAPA 0] Ollama no responde ni arranca: freno (sin fallback a la nube).")
    # generar_qwen (nova_core/ollama_comun.py): /api/chat sin modo "pensar", contexto y keep_alive explicitos.
    # Por /v1/chat/completions qwen3.5 pensaba sin limite y se agotaban los 300 s (07/11).
    raw_code, cortado = generar_qwen(prompt, chosen_model, sistema=system_instructions, temperatura=0.15)
    if cortado:
        raise RuntimeError(
            "[CAPA 0] Qwen agoto los tokens y el codigo salio CORTADO: divide la tarea en trozos mas pequenos."
        )
    return clean_markdown_code(raw_code.strip()), chosen_model


def main():
    parser = argparse.ArgumentParser(
        description="Nova Local Worker v2.0 - Obrero Local Portable (Consenso Claude)"
    )
    parser.add_argument(
        "--task", type=str, help="Prompt o tarea directa en linea de comandos"
    )
    parser.add_argument(
        "--file", type=str, help="Ruta al archivo con la tarea a procesar"
    )
    parser.add_argument(
        "--out", type=str, help="Ruta donde escribir el archivo generado"
    )
    parser.add_argument(
        "--model", type=str, default=None, help="Forzar modelo especifico de Ollama"
    )
    parser.add_argument(
        "--test-cmd",
        type=str,
        default=None,
        help="Comando unittest opcional para validar salida en 1 solo paso",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Imprime la configuracion de IA local detectada y sale",
    )
    args = parser.parse_args()

    cfg = load_local_ai_config()
    if args.check_config:
        print(
            f"[CONFIG IA LOCAL] Instalada={cfg['instalada']} | Modelo={cfg['modelo']} | Tier={cfg['tier']} | Regla={cfg['regla_activacion']}"
        )
        sys.exit(0)

    mem_dir = get_memory_dir()
    task_prompt = ""
    if args.task:
        task_prompt = args.task
    elif args.file and os.path.exists(args.file):
        with open(args.file, encoding="utf-8") as f:
            task_prompt = f.read()
    else:
        default_task = os.path.join(mem_dir, "registros", "tasks_local_worker.md")
        if os.path.exists(default_task):
            with open(default_task, encoding="utf-8") as f:
                task_prompt = f.read()

    if not task_prompt:
        print(
            "[ERROR] No se indico ninguna tarea (--task, --file o tasks_local_worker.md)."
        )
        sys.exit(1)

    try:
        code, used_model = run_local_coder(task_prompt, model_name=args.model)
    except Exception as e:
        # el agente de nube lee esta salida: el fallo se dice claro y se frena (no picar ese codigo en la nube)
        print(f"[FRENO CAPA 0] {e}")
        print("NO escribas este codigo desde la nube: vuelca el fallo a nova_pendiente.txt y avisa a Alexander.")
        sys.exit(2)

    out_file = args.out or os.path.join(mem_dir, "registros", "resultado_local_worker.md")
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(code)

    test_status = "N/A"
    if args.test_cmd:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        res_t = subprocess.run(
            args.test_cmd, shell=True, capture_output=True, text=True, creationflags=flags
        )
        test_status = (
            "OK" if res_t.returncode == 0 else f"FALLO ({res_t.stderr.strip()[-200:]})"
        )

    print(
        f"[OBRERO LOCAL v2.0 OK] Modelo={used_model} | Salida={out_file} ({len(code):,} chars) | Tests={test_status}"
    )


if __name__ == "__main__":
    main()
