"""
Nova Sync - pedir una sincronizacion (v3.2, Windows / macOS / Linux)
Lo usa Nova (una sola llamada, espera el resultado y lo imprime en UNA linea):

  <PYTHON> <NOVA_HOME>/antigravity/scripts/nova_sync_pedir.py bajar        "Nova, sincroniza"
  <PYTHON> <NOVA_HOME>/antigravity/scripts/nova_sync_pedir.py subir        "Nova, sube los cambios"
  <PYTHON> <NOVA_HOME>/antigravity/scripts/nova_sync_pedir.py espejo       "Nova, deja este equipo igual que Drive"
  <PYTHON> <NOVA_HOME>/antigravity/scripts/nova_sync_pedir.py estado
  <PYTHON> <NOVA_HOME>/antigravity/scripts/nova_sync_pedir.py configurar [--si] [--carpeta RUTA] [--nombre N]

En Windows Antigravity no deja a Nova escribir en la unidad de Google Drive: deja el pedido en
memory/pedir_sync.json y el guardian de sesion (fuera de Antigravity) ejecuta nova_sync.py.
Si nadie recoge el pedido en 8 s (macOS/Linux, o guardian parado), lo ejecuta directamente.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

MEM = Path.home() / ".gemini" / "antigravity" / "memory"
PEDIDO = MEM / "pedir_sync.json"
RESULTADO = MEM / "sync_resultado.txt"
SYNC = Path(__file__).with_name("nova_sync.py")
MODOS = {"bajar", "subir", "espejo", "estado", "configurar"}
PERMITIDOS = {"--si", "--simular", "--carpeta", "--nombre"}  # nunca --forzar desde el chat: ese lo decide el usuario en una terminal


def main() -> int:
    if sys.stdout:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    args = sys.argv[1:]
    modo = (args[0].lower() if args else "estado").replace("sincroniza", "bajar").replace("sube", "subir")
    if modo not in MODOS:
        print(f"Modo no valido: usa {', '.join(sorted(MODOS))}")
        return 2
    extra = []
    i = 1
    while i < len(args):
        if args[i] in ("--carpeta", "--nombre") and i + 1 < len(args):
            extra += [args[i], args[i + 1]]
            i += 2
            continue
        if args[i] in PERMITIDOS:
            extra.append(args[i])
        i += 1
    MEM.mkdir(parents=True, exist_ok=True)
    RESULTADO.unlink(missing_ok=True)
    PEDIDO.write_text(json.dumps({"modo": modo, "args": extra, "pedido": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
    fin_recogida = time.time() + 8
    while time.time() < fin_recogida and PEDIDO.exists():
        time.sleep(0.5)
    if PEDIDO.exists():  # nadie lo recogio: se ejecuta aqui
        PEDIDO.unlink(missing_ok=True)
        r = subprocess.run([sys.executable, str(SYNC), modo, *extra], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        salida = (r.stdout + r.stderr).strip()
        print(salida.splitlines()[-1] if salida else "SYNC: sin respuesta")
        if r.returncode == 3 or "Permission" in salida or "denegado" in salida.lower():
            print("Si Antigravity no deja escribir en Drive, ejecutalo en una terminal: "
                  f"python \"{SYNC}\" {modo} {' '.join(extra)}".rstrip())
        return r.returncode
    fin = time.time() + 900  # el guardian lo esta ejecutando
    while time.time() < fin:
        if RESULTADO.exists():
            texto = RESULTADO.read_text(encoding="utf-8", errors="replace").strip()
            if texto.endswith("[FIN]"):
                lineas = [l for l in texto.splitlines() if l.strip() and l.strip() != "[FIN]"]
                print("\n".join(lineas[-6:]) if modo in ("configurar", "estado") else (lineas[-1] if lineas else "SYNC: sin respuesta"))
                return 0
        time.sleep(1)
    print("SYNC: el guardian lo esta ejecutando pero tarda mas de 15 min. Mira memory/sync_status.json en un rato.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
