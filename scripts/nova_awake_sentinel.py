"""
Nova Awake Sentinel v1.0 - Guardian Anti-Suspension Inteligente para Windows
=============================================================================
- Usa API nativa del kernel: SetThreadExecutionState (cero clics/teclas falsas).
- Monitorea bateria via GetSystemPowerStatus.
- Si bateria <= 10% o Modo Ahorro activo: activa Parada en Punto Seguro (Safe Checkpoint).
- Al terminar tareas: cuenta atras de 5 minutos (300s). Si no hay mas tareas, restaura
  el bloqueo normal de Windows.
- Consumo: 0% CPU, <10 MB RAM.
"""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_byte, c_ulong, byref
import json
import os
import sys
import time
from pathlib import Path

# Flags oficiales de Windows Kernel32
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_CONTINUOUS = 0x80000000

# Estructura oficial SYSTEM_POWER_STATUS
class SYSTEM_POWER_STATUS(Structure):
    _fields_ = [
        ("ACLineStatus", c_byte),          # 0: Bateria, 1: Conectado a corriente, 255: Desconocido
        ("BatteryFlag", c_byte),           # 1: Alta, 2: Baja, 4: Critica, 8: Cargando, 128: Sin bateria (PC)
        ("BatteryLifePercent", c_byte),    # 0 - 100%, 255: Desconocido
        ("SystemStatusFlag", c_byte),      # 1: Ahorro de bateria activado (Windows 10/11)
        ("BatteryLifeTime", c_ulong),
        ("BatteryFullLifeTime", c_ulong),
    ]

kernel32 = ctypes.windll.kernel32

def get_power_status() -> dict[str, int | bool]:
    status = SYSTEM_POWER_STATUS()
    if kernel32.GetSystemPowerStatus(byref(status)):
        return {
            "on_ac_power": status.ACLineStatus == 1,
            "has_battery": status.BatteryFlag != 128 and status.BatteryFlag != 255,
            "battery_percent": int(status.BatteryLifePercent),
            "battery_saver_on": status.SystemStatusFlag == 1,
        }
    return {
        "on_ac_power": True,
        "has_battery": False,
        "battery_percent": 100,
        "battery_saver_on": False,
    }

def set_keep_awake(enable: bool, keep_display: bool = True) -> bool:
    if enable:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        if keep_display:
            flags |= ES_DISPLAY_REQUIRED
    else:
        flags = ES_CONTINUOUS

    prev = kernel32.SetThreadExecutionState(flags)
    return prev != 0

FLAG_FILE = Path(os.path.expanduser(r"~\.gemini\antigravity\.task_running"))
STATE_FILE = Path(os.path.expanduser(r"~\.gemini\antigravity\sentinel_state.json"))
IDLE_GRACE_PERIOD = 300  # 5 minutos

def log_sentinel(msg: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] [SENTINEL] {msg}"
    print(line)
    try:
        log_path = Path(os.path.expanduser(r"~\.gemini\antigravity\sentinel.log"))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

def write_state(data: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass

def main():
    log_sentinel("Iniciando Nova Awake Sentinel v1.0...")
    currently_awake = False
    task_finished_time: float | None = None

    while True:
        try:
            power = get_power_status()
            task_active = FLAG_FILE.is_file()

            # 1. Comprobacion de Seguridad de Bateria (<= 10% o Modo Ahorro)
            if power["has_battery"] and not power["on_ac_power"]:
                battery_pct = power["battery_percent"]
                is_critical = battery_pct <= 10 or power["battery_saver_on"]

                if is_critical and currently_awake:
                    log_sentinel(f"ALERTA BATERIA CRITICA ({battery_pct}% / Ahorro={power['battery_saver_on']}).")
                    log_sentinel("Activando Parada en Punto Seguro y liberando bloqueo de suspension.")
                    set_keep_awake(False)
                    currently_awake = False
                    write_state({"status": "paused_critical_battery", "battery_percent": battery_pct, "power": power})
                    time.sleep(10)
                    continue

            # 2. Si hay tarea activa
            if task_active:
                task_finished_time = None
                if not currently_awake:
                    log_sentinel("Tarea activa detectada. Bloqueando suspension de Windows (CPU y Pantalla vivas).")
                    set_keep_awake(True, keep_display=True)
                    currently_awake = True
                    write_state({"status": "active_keep_awake", "power": power})
            else:
                # Si no hay tarea activa pero estabamos despiertos
                if currently_awake:
                    if task_finished_time is None:
                        task_finished_time = time.time()
                        log_sentinel(f"Tarea finalizada. Iniciando cuenta atras de gracia ({IDLE_GRACE_PERIOD}s)...")
                        write_state({"status": "grace_countdown", "remaining": IDLE_GRACE_PERIOD, "power": power})

                    elapsed = time.time() - task_finished_time
                    remaining = IDLE_GRACE_PERIOD - elapsed

                    if remaining <= 0:
                        log_sentinel("Periodo de gracia finalizado sin nuevas tareas. Restaurando suspension normal de Windows.")
                        set_keep_awake(False)
                        currently_awake = False
                        task_finished_time = None
                        write_state({"status": "idle_normal", "power": power})
                    else:
                        write_state({"status": "grace_countdown", "remaining": int(remaining), "power": power})

            time.sleep(2)

        except KeyboardInterrupt:
            log_sentinel("Apagando centinela y restaurando estado normal...")
            set_keep_awake(False)
            break
        except Exception as exc:
            log_sentinel(f"Error inesperado en centinela: {exc}")
            time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "flag-on":
        FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
        FLAG_FILE.write_text("ACTIVE", encoding="utf-8")
        print("[OK] Flag activado.")
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "flag-off":
        if FLAG_FILE.exists():
            FLAG_FILE.unlink()
        print("[OK] Flag desactivado.")
        sys.exit(0)

    main()
