"""
Registra los hooks de Nova en ~/.gemini/config/hooks.json (Windows / macOS / Linux).

- Usa el MISMO Python que ejecuta este script (el instalador y el actualizador lo lanzan con el bueno).
- Solo anade o reemplaza las entradas "nova-*": los hooks que el usuario tenga de otras cosas se respetan.
- Guarda copia del hooks.json anterior (hooks.json.bak) antes de cambiarlo.
- En Windows usa la ruta corta (8.3) si hay espacios ("C:\\Users\\Ana Maria\\..."), igual que en la Nova original.

    python instalar_hooks.py            (registrar / actualizar)
    python instalar_hooks.py --quitar   (quitar solo los hooks de Nova)
    python instalar_hooks.py --mostrar  (ver lo que escribiria, sin tocar nada)
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
HOOKS = Path.home() / ".gemini" / "config" / "hooks.json"


def ruta_para_comando(p: str) -> str:
    if os.name == "nt":
        if " " in p:
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(1024)
                if ctypes.windll.kernel32.GetShortPathNameW(p, buf, 1024) and " " not in buf.value:
                    return buf.value
            except Exception:
                pass
            return f'"{p}"'
        return p
    return shlex.quote(p)


def entradas_nova() -> dict:
    py = ruta_para_comando(sys.executable)
    hook = ruta_para_comando(str(AQUI / "nova_hook.py"))
    turno = ruta_para_comando(str(AQUI / "nova_hook_turno.py"))
    return {
        "nova-guardia-herramientas": {
            "enabled": True,
            "PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": f"{py} {hook}", "timeout": 10}]}],
        },
        "nova-recordatorio-codigo": {
            "enabled": True,
            "PreInvocation": [{"type": "command", "command": f"{py} {turno} pre", "timeout": 60}],
        },
        "nova-correccion-codigo-chat": {
            "enabled": True,
            "Stop": [{"type": "command", "command": f"{py} {turno} stop", "timeout": 10}],
        },
    }


def leer() -> dict:
    try:
        d = json.loads(HOOKS.read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        print(f"[HOOKS] No pude leer {HOOKS} ({e}). No lo toco: revisalo a mano.")
        raise SystemExit(1)


def escribir(datos: dict) -> None:
    HOOKS.parent.mkdir(parents=True, exist_ok=True)
    if HOOKS.exists():
        shutil.copy2(HOOKS, HOOKS.with_name("hooks.json.bak"))
    HOOKS.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    if "--mostrar" in sys.argv:
        print(json.dumps(entradas_nova(), indent=2, ensure_ascii=False))
        return 0
    datos = leer()
    for k in [k for k in datos if k.startswith("nova-")]:
        del datos[k]
    if "--quitar" in sys.argv:
        escribir(datos)
        print("[HOOKS] Hooks de Nova quitados (los demas se mantienen).")
        return 0
    datos.update(entradas_nova())
    escribir(datos)
    print(f"[HOOKS] Reglas automaticas de Nova registradas en {HOOKS} (se activan al reabrir Antigravity).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
