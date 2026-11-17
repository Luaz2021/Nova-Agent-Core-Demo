"""
Nova - Clave de Gemini para NOVA VOZ LIVE (Windows). 17/11/2026, Claude.
==========================================================================
Pide SOLO la clave de Gemini (gratis en https://aistudio.google.com/apikey), sin pasar por las demas claves,
y la guarda como GEMINI_API_KEY en:
  - el cofre de Nova: ~/.gemini/antigravity/vault/google_cloud.env (el mismo que usa la aduana de claves)
  - las variables de Windows del usuario (ahi la busca Nova Voz Live al abrir Antigravity)
La clave no se ve al escribirla y nunca se imprime ni se apunta en ningun log.

    python nova_clave_gemini.py            (pide la clave y la guarda)
    python nova_clave_gemini.py --estado   (dice si esta puesta, sin mostrarla)
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

NOMBRE = "GEMINI_API_KEY"
VOZ = Path.home() / ".gemini" / "antigravity" / "herramientas" / "voz"


def _cofre():
    sys.path.insert(0, str(VOZ))
    import guardian_claves  # noqa: PLC0415 (mismo cofre y misma forma de guardar que la aduana)
    return guardian_claves


def estado() -> int:
    g = _cofre()
    en_cofre = any(l.partition("=")[0].strip() == NOMBRE and l.partition("=")[2].strip() for l in g._leer())
    import winreg
    en_windows = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            en_windows = bool(winreg.QueryValueEx(k, NOMBRE)[0])
    except OSError:
        pass
    print(f"  {NOMBRE} en el cofre: {'si' if en_cofre else 'no'} | en Windows: {'si' if en_windows else 'no'}")
    return 0 if (en_cofre and en_windows) else 1


def guardar(clave: str) -> None:
    g = _cofre()
    lineas = g._leer()
    for i, linea in enumerate(lineas):
        if linea.partition("=")[0].strip() == NOMBRE:
            lineas[i] = f"{NOMBRE}={clave}"
            break
    else:
        lineas.append(f"{NOMBRE}={clave}")
    g._escribir(lineas)
    g._variable_windows(NOMBRE, clave)


def main() -> int:
    if os.name != "nt":
        print("[VOZ LIVE] Nova Voz Live es solo para Windows. En Mac/Linux usa: python nova_claves.py")
        return 1
    if "--estado" in sys.argv:
        return estado()
    if not sys.stdin or not sys.stdin.isatty():
        print("[VOZ LIVE] Necesito una terminal. Ejecutalo a mano en PowerShell.")
        return 1
    print("\n[NOVA VOZ LIVE] Clave gratuita de Gemini: https://aistudio.google.com/apikey -> 'Create API key'.")
    print("Pegala aqui (no se vera al escribir; Enter = cancelar).")
    try:
        clave = getpass.getpass("  GEMINI_API_KEY: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    if not clave:
        print("[VOZ LIVE] Cancelado: no se ha cambiado nada.")
        return 1
    if not clave.startswith("AIza") or len(clave) < 30:
        seguir = input("  Eso no parece una clave de Gemini (suelen empezar por 'AIza'). Guardarla igual? (s/n) [n]: ")
        if seguir.strip().lower() != "s":
            print("[VOZ LIVE] Cancelado: no se ha cambiado nada.")
            return 1
    guardar(clave)
    print(f"[OK] Guardada como {NOMBRE} en el cofre y en Windows (termina en ...{clave[-3:]}).")
    print("     Cierra Antigravity del todo y vuelve a abrirlo: saldra el monito. Di 'Nova' y habla.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
