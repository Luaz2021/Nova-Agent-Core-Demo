"""Nova Doctor - comprobacion de la aduana de adjuntos y la mascota DENTRO de Antigravity (11/11/2026, Claude).

Lo usa antigravity/scripts/nova_doctor.ps1. Habla con Antigravity por CDP (el mismo canal que usa nova_voz.py) y mira
si la ventana del chat tiene window.novaAduana (la aduana) y la mascota inyectadas.
Imprime UNA linea JSON: {"antigravity": bool, "aduana": bool, "mascota": bool, "ventanas": n, "error": "..."}
Solo lee: no cambia nada en Antigravity.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

EXPR = ("JSON.stringify({aduana: typeof window.novaAduana === 'function', "
        "mascota: !!document.querySelector('[id*=nova],[class*=nova-mascota]')})")


def main() -> None:
    out = {"antigravity": False, "aduana": False, "mascota": False, "ventanas": 0, "error": ""}
    puerto_f = Path(os.environ.get("APPDATA", "")) / "Antigravity" / "DevToolsActivePort"
    try:
        puerto = puerto_f.read_text(encoding="utf-8").split()[0]
        paginas = json.load(urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json", timeout=3))
    except Exception as e:  # Antigravity cerrado o sin puerto de depuracion
        out["error"] = f"sin CDP: {e.__class__.__name__}"
        print(json.dumps(out))
        return
    out["antigravity"] = True
    try:
        import websocket
    except ImportError:
        out["error"] = "falta websocket-client"
        print(json.dumps(out))
        return
    for p in paginas:
        url = str(p.get("url", ""))
        if p.get("type") != "page" or "webSocketDebuggerUrl" not in p or url.startswith("data:"):
            continue
        out["ventanas"] += 1
        try:
            ws = websocket.create_connection(p["webSocketDebuggerUrl"], timeout=5, suppress_origin=True)
            ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": EXPR, "returnByValue": True}}))
            r = json.loads(ws.recv())
            ws.close()
            v = json.loads(r.get("result", {}).get("result", {}).get("value") or "{}")
            out["aduana"] = out["aduana"] or bool(v.get("aduana"))
            out["mascota"] = out["mascota"] or bool(v.get("mascota"))
        except Exception as e:
            out["error"] = f"{e.__class__.__name__}: {e}"[:200]
    print(json.dumps(out))


if __name__ == "__main__":
    sys.exit(main())
