import argparse
import glob
import json
import os

BRAIN_DIR = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "brain"))
SAFE_BUFFER_LIMIT = 100000


def get_latest_transcript(conv_id=None):
    if conv_id:
        cand = os.path.join(
            BRAIN_DIR, conv_id, ".system_generated", "logs", "transcript.jsonl"
        )
        if os.path.exists(cand):
            return cand
    pattern = os.path.join(
        BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl"
    )
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def get_turn_telemetry(conv_id=None):
    t_path = get_latest_transcript(conv_id)
    if not t_path or not os.path.exists(t_path):
        return None

    steps = []
    with open(t_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    steps.append(json.loads(line))
                except Exception:
                    continue

    last_user_idx = 0
    for i in range(len(steps) - 1, -1, -1):
        if steps[i].get("type") == "USER_INPUT":
            last_user_idx = i
            break

    last_in = 0
    last_cache = 0
    out_total = 0
    calls = 0

    for s in steps[last_user_idx:]:
        if s.get("type") == "PLANNER_RESPONSE":
            calls += 1
            last_in = int(s.get("input_tokens", 0) or 0)
            last_cache = int(s.get("cache_read_tokens", 0) or 0)
            out_total += int(s.get("output_tokens", 0) or 0)

    total_tokens = last_in + last_cache
    free_buffer = max(0, SAFE_BUFFER_LIMIT - total_tokens)
    pct = round((total_tokens / SAFE_BUFFER_LIMIT) * 100, 1)

    return {
        "envio": last_in,
        "cache": last_cache,
        "salida": out_total,
        "llamadas": calls,
        "buffer_libre": free_buffer,
        "buffer_pct": pct,
        "total_tokens": total_tokens,
        "linea": f"Envio: {last_in:,} | Cache: {last_cache:,} | Salida: {out_total:,} - {calls} llamada{'s' if calls != 1 else ''} | Buffer: {free_buffer:,} libres ({pct}%) | Total tokens: {total_tokens:,}",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--conv-id", default=None)
    args = parser.parse_args()

    data = get_turn_telemetry(args.conv_id)
    if data:
        print(data["linea"])
