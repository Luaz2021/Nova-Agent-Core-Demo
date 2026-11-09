"""
Nova Awake Sentinel v2.0 - Guardian Anti-Suspension Inteligente (Windows / macOS / Linux)
=========================================================================================
- Mantiene el equipo despierto mientras haya una tarea larga de Nova (flag ~/.gemini/antigravity/.task_running):
    Windows: API nativa SetThreadExecutionState (cero clics/teclas falsas).
    macOS:   'caffeinate -is' mientras dure la tarea.
    Linux:   'systemd-inhibit --what=idle:sleep' (si existe).
- Vigila la bateria:
    Windows: GetSystemPowerStatus.  macOS: 'pmset -g batt'.  Linux: /sys/class/power_supply.
- Si bateria <= 10% (o Modo Ahorro en Windows): Parada en Punto Seguro (deja que el equipo se suspenda).
- Al terminar las tareas: cuenta atras de 5 minutos (300 s) y vuelve al comportamiento normal del sistema.

Uso:  python nova_awake_sentinel.py            (centinela en bucle)
      python nova_awake_sentinel.py flag-on     (marca tarea activa)
      python nova_awake_sentinel.py flag-off    (marca tarea terminada)
      python nova_awake_sentinel.py estado      (muestra la bateria que ve)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path.home() / ".gemini" / "antigravity"
FLAG_FILE = BASE / ".task_running"
STATE_FILE = BASE / "sentinel_state.json"
LOG_FILE = BASE / "sentinel.log"
IDLE_GRACE_PERIOD = 300  # 5 minutos

SIN_BATERIA = {"on_ac_power": True, "has_battery": False, "battery_percent": 100, "battery_saver_on": False}


# ------------------------------------------------------------------ bateria (por sistema)
def _bateria_windows() -> dict:
    import ctypes
    from ctypes import Structure, byref, c_ubyte, c_ulong

    class SYSTEM_POWER_STATUS(Structure):
        _fields_ = [
            ("ACLineStatus", c_ubyte),        # 0: bateria, 1: corriente, 255: desconocido
            ("BatteryFlag", c_ubyte),         # 128: sin bateria (PC), 255: desconocido
            ("BatteryLifePercent", c_ubyte),  # 0-100, 255: desconocido
            ("SystemStatusFlag", c_ubyte),    # 1: ahorro de bateria activado
            ("BatteryLifeTime", c_ulong),
            ("BatteryFullLifeTime", c_ulong),
        ]

    status = SYSTEM_POWER_STATUS()
    if ctypes.windll.kernel32.GetSystemPowerStatus(byref(status)):
        return {
            "on_ac_power": status.ACLineStatus == 1,
            "has_battery": status.BatteryFlag not in (128, 255),
            "battery_percent": int(status.BatteryLifePercent),
            "battery_saver_on": status.SystemStatusFlag == 1,
        }
    return dict(SIN_BATERIA)


def _bateria_macos() -> dict:
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return dict(SIN_BATERIA)
    m = re.search(r"(\d+)%", out)
    if not m:  # Mac de sobremesa
        return dict(SIN_BATERIA)
    return {"on_ac_power": "AC Power" in out, "has_battery": True, "battery_percent": int(m.group(1)),
            "battery_saver_on": False}


def _bateria_linux() -> dict:
    raiz = Path("/sys/class/power_supply")
    if not raiz.is_dir():
        return dict(SIN_BATERIA)
    porcentaje, en_corriente = None, False
    for d in raiz.iterdir():
        try:
            tipo = (d / "type").read_text().strip()
            if tipo == "Battery" and (d / "capacity").exists():
                porcentaje = int((d / "capacity").read_text().strip())
                if (d / "status").exists() and (d / "status").read_text().strip() in ("Charging", "Full"):
                    en_corriente = True
            elif tipo == "Mains" and (d / "online").exists():
                en_corriente = en_corriente or (d / "online").read_text().strip() == "1"
        except (OSError, ValueError):
            continue
    if porcentaje is None:
        return dict(SIN_BATERIA)
    return {"on_ac_power": en_corriente, "has_battery": True, "battery_percent": porcentaje, "battery_saver_on": False}


def get_power_status() -> dict:
    try:
        if sys.platform == "win32":
            return _bateria_windows()
        if sys.platform == "darwin":
            return _bateria_macos()
        return _bateria_linux()
    except Exception:
        return dict(SIN_BATERIA)


# ------------------------------------------------------------------ mantener despierto (por sistema)
_INHIBIDOR: subprocess.Popen | None = None  # caffeinate / systemd-inhibit en macOS y Linux


def set_keep_awake(enable: bool, keep_display: bool = True) -> bool:
    global _INHIBIDOR
    if sys.platform == "win32":
        import ctypes
        ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED, ES_CONTINUOUS = 0x00000001, 0x00000002, 0x80000000
        flags = ES_CONTINUOUS
        if enable:
            flags |= ES_SYSTEM_REQUIRED | (ES_DISPLAY_REQUIRED if keep_display else 0)
        return ctypes.windll.kernel32.SetThreadExecutionState(flags) != 0

    if not enable:
        if _INHIBIDOR and _INHIBIDOR.poll() is None:
            _INHIBIDOR.terminate()
        _INHIBIDOR = None
        return True
    if _INHIBIDOR and _INHIBIDOR.poll() is None:
        return True
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        cmd = ["caffeinate", "-is"] + (["-d"] if keep_display else [])
    elif shutil.which("systemd-inhibit"):
        cmd = ["systemd-inhibit", "--what=idle:sleep", "--who=Nova", "--why=Tarea de Nova en curso", "sleep", "infinity"]
    else:
        log_sentinel("No hay caffeinate ni systemd-inhibit: no puedo impedir la suspension en este equipo.")
        return False
    try:
        _INHIBIDOR = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError as exc:
        log_sentinel(f"No se pudo lanzar {cmd[0]}: {exc}")
        return False


# ------------------------------------------------------------------ registro y estado
def log_sentinel(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [SENTINEL] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def write_state(data: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def main() -> None:
    log_sentinel(f"Iniciando Nova Awake Sentinel v2.0 ({sys.platform})...")
    currently_awake = False
    task_finished_time: float | None = None

    while True:
        try:
            power = get_power_status()
            task_active = FLAG_FILE.is_file()

            # 1. Seguridad de bateria (<= 10% o Modo Ahorro)
            if power["has_battery"] and not power["on_ac_power"]:
                battery_pct = power["battery_percent"]
                if (battery_pct <= 10 or power["battery_saver_on"]) and currently_awake:
                    log_sentinel(f"ALERTA BATERIA CRITICA ({battery_pct}% / Ahorro={power['battery_saver_on']}).")
                    log_sentinel("Activando Parada en Punto Seguro y liberando bloqueo de suspension.")
                    set_keep_awake(False)
                    currently_awake = False
                    write_state({"status": "paused_critical_battery", "battery_percent": battery_pct, "power": power})
                    time.sleep(10)
                    continue

            # 2. Tarea activa
            if task_active:
                task_finished_time = None
                if not currently_awake:
                    log_sentinel("Tarea activa detectada. Bloqueando suspension del sistema.")
                    set_keep_awake(True, keep_display=True)
                    currently_awake = True
                    write_state({"status": "active_keep_awake", "power": power})
            elif currently_awake:
                if task_finished_time is None:
                    task_finished_time = time.time()
                    log_sentinel(f"Tarea finalizada. Iniciando cuenta atras de gracia ({IDLE_GRACE_PERIOD}s)...")
                remaining = IDLE_GRACE_PERIOD - (time.time() - task_finished_time)
                if remaining <= 0:
                    log_sentinel("Periodo de gracia finalizado sin nuevas tareas. Restaurando suspension normal.")
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
    elif len(sys.argv) > 1 and sys.argv[1] == "estado":
        print(json.dumps(get_power_status(), indent=2))
        sys.exit(0)

    main()
