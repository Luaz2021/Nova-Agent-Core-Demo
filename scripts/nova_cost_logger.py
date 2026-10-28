r"""
Nova Cost Logger v2.1 (Consenso Final Nova Argon + Claude)
Ubicacion: G:\Mi unidad\Antigravity\scripts\nova_cost_logger.py
Registra automaticamente cada tarea sumando cache_read_tokens de todas las llamadas API.
Incluye modo --auto-last-task para leer directamente desde transcript.jsonl sin error humano.
Formula:
  Costo_Base = sum(Input_Nuevo)*1.0 + sum(Cache_Leida)*0.1 + sum(Output)*6.0
  Costo_Final = Costo_Base * Factor_Modelo (Flash=1.0, Argon/Pro=4.0)
"""

import os
import glob
import json
import datetime
import argparse

def _resolve_log_path():
    local_mem = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "memory"))
    os.makedirs(local_mem, exist_ok=True)
    return os.path.join(local_mem, "token_cost_log.jsonl")

LOG_PATH = _resolve_log_path()
BRAIN_DIR = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "brain"))

MODEL_MULTIPLIERS = {
    "flash": 1.0,
    "pro": 4.0,
    "argon": 4.0,
}


def compute_weighted_cost(sum_input_nuevo, sum_cache_leida, sum_output, modelo="flash"):
    """Calcula el costo base (Flash=1.0x) y el costo ponderado real segun el tier de modelo."""
    tier = modelo.lower().strip()
    factor_modelo = MODEL_MULTIPLIERS.get(tier, 1.0)
    costo_base = (sum_input_nuevo * 1.0) + (sum_cache_leida * 0.1) + (sum_output * 6.0)
    costo_ponderado = costo_base * factor_modelo
    return round(costo_base, 2), round(costo_ponderado, 2), factor_modelo


def extract_task_metrics_from_transcript(transcript_path, since_last_user_input=True):
    """
    Extrae las metricas reales de las llamadas PLANNER_RESPONSE en transcript.jsonl.
    Si since_last_user_input=True, toma todas las llamadas API desde el ultimo USER_INPUT.
    """
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"No existe el transcript: {transcript_path}")

    steps = []
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                steps.append(json.loads(line))
            except Exception:
                continue

    start_idx = 0
    if since_last_user_input:
        for i in range(len(steps) - 1, -1, -1):
            if steps[i].get("type") == "USER_INPUT":
                start_idx = i
                break

    planner_calls = []
    for s in steps[start_idx:]:
        if s.get("type") == "PLANNER_RESPONSE":
            inp = int(s.get("input_tokens", 0) or 0)
            cache = int(s.get("cache_read_tokens", 0) or 0)
            out = int(s.get("output_tokens", 0) or 0)
            if inp + cache + out > 0:
                planner_calls.append({
                    "step_index": s.get("step_index"),
                    "input_tokens": inp,
                    "cache_read_tokens": cache,
                    "output_tokens": out,
                    "total_prompt": inp + cache,
                })

    return {
        "llamadas_api": len(planner_calls),
        "sum_input_nuevo": sum(c["input_tokens"] for c in planner_calls),
        "sum_cache_leida": sum(c["cache_read_tokens"] for c in planner_calls),
        "sum_output": sum(c["output_tokens"] for c in planner_calls),
        "calls": planner_calls,
    }


def get_latest_transcript_path(conv_id=None):
    if conv_id:
        candidate = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(candidate):
            return candidate
    pattern = os.path.join(BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def log_task_cost(
    tipo_tarea,
    modo,
    llamadas_api,
    sum_input_nuevo,
    sum_cache_leida,
    sum_output,
    modelo="flash",
    rondas=1,
    resultado="OK",
    intervencion_humana=False,
    notas="",
    log_path=LOG_PATH,
):
    tier = modelo.lower().strip()
    costo_base, costo_ponderado, factor_modelo = compute_weighted_cost(
        sum_input_nuevo, sum_cache_leida, sum_output, tier
    )

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tipo_tarea": tipo_tarea,
        "modo": modo,
        "modelo": tier,
        "factor_modelo": factor_modelo,
        "llamadas_api": llamadas_api,
        "sum_input_nuevo": sum_input_nuevo,
        "sum_cache_leida": sum_cache_leida,
        "sum_output": sum_output,
        "costo_base_relativo": costo_base,
        "costo_ponderado_real": costo_ponderado,
        "rondas": rondas,
        "resultado": resultado,
        "intervencion_humana": intervencion_humana,
        "notas": notas,
    }

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Registrador oficial v2.1 de costo ponderado de tareas")
    parser.add_argument("--tarea", required=True, help="Tipo de tarea")
    parser.add_argument("--modo", required=True, help="Modo de ejecucion")
    parser.add_argument("--modelo", default="flash", choices=["flash", "pro", "argon"], help="Nivel de modelo")
    parser.add_argument("--auto-transcript", action="store_true", help="Extrae metricas automaticamente del transcript activo")
    parser.add_argument("--all-session", action="store_true", help="Con --auto-transcript, suma toda la sesion en vez del ultimo turno")
    parser.add_argument("--conv-id", default=None, help="ID de conversacion opcional para --auto-transcript")
    parser.add_argument("--llamadas", type=int, default=1, help="Numero total de llamadas API en la tarea")
    parser.add_argument("--in_nuevo", type=int, default=0, help="Suma de input_tokens de todas las llamadas")
    parser.add_argument("--cache", type=int, default=0, help="Suma de cache_read_tokens de todas las llamadas")
    parser.add_argument("--out", type=int, default=0, help="Suma de output_tokens de todas las llamadas")
    parser.add_argument("--rondas", type=int, default=1, help="Rondas de correccion")
    parser.add_argument("--resultado", default="OK", help="OK o FALLO")
    parser.add_argument("--humano", action="store_true", help="Si requirio intervencion humana")
    parser.add_argument("--notas", default="", help="Notas adicionales")
    args = parser.parse_args()

    if args.auto_transcript:
        t_path = get_latest_transcript_path(args.conv_id)
        metrics = extract_task_metrics_from_transcript(t_path, since_last_user_input=not args.all_session)
        llamadas = metrics["llamadas_api"]
        in_nuevo = metrics["sum_input_nuevo"]
        cache = metrics["sum_cache_leida"]
        out = metrics["sum_output"]
    else:
        llamadas = args.llamadas
        in_nuevo = args.in_nuevo
        cache = args.cache
        out = args.out

    res = log_task_cost(
        tipo_tarea=args.tarea,
        modo=args.modo,
        llamadas_api=llamadas,
        sum_input_nuevo=in_nuevo,
        sum_cache_leida=cache,
        sum_output=out,
        modelo=args.modelo,
        rondas=args.rondas,
        resultado=args.resultado,
        intervencion_humana=args.humano,
        notas=args.notas,
    )
    print(
        f"[LOGGER v2.1 OK] '{args.tarea}' ({args.modelo}) | "
        f"Llamadas={res['llamadas_api']} | In={res['sum_input_nuevo']:,} | "
        f"Cache={res['sum_cache_leida']:,} | Out={res['sum_output']:,} | "
        f"Base(Flash)={res['costo_base_relativo']:,.1f} | Real={res['costo_ponderado_real']:,.1f}"
    )
