import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
Modulo autopsia_collector: recolecta pares DPO para alimentar el dataset de reentrenamiento.
"""
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AUTOPSIAS_FILE = BASE_DIR / "autopsias_dataset" / "autopsias_pendientes.jsonl"


def registrar_autopsia(seccion, url, prompt_instruccion, codigo_rechazado_qwen, codigo_elegido_nova, motivo_fallo):
    item = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "seccion": seccion,
        "motivo_fallo": motivo_fallo,
        "prompt": prompt_instruccion.strip(),
        "rejected": codigo_rechazado_qwen.strip(),
        "chosen": codigo_elegido_nova.strip()
    }
    AUTOPSIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTOPSIAS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[AUTOPSIA REGISTRADA] Seccion: {seccion} | Motivo: {motivo_fallo}")


if __name__ == "__main__":
    print(f"Colector de autopsias activo en: {AUTOPSIAS_FILE}")
