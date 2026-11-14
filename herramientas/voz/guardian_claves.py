"""GUARDIAN DE CLAVES (12/11/2026, Claude): las claves de API que Luaz pega en el chat de Antigravity NO llegan a la nube.

La aduana (aduana.js) detecta la clave al pegarla, la quita del mensaje y se la pasa a nova_voz.py, que llama a
guardar(). Aqui se guarda en el cofre de Drive (vault\\google_cloud.env, linea NOMBRE=valor) y en las variables de
Windows del usuario, para que el codigo la use con os.environ.get("NOMBRE"). En el chat solo queda
"[clave guardada en el cofre: NOMBRE]". El valor no se imprime ni se apunta en ningun log.

Uso por terminal (Nova puede usarlo: nunca muestra valores):
    python guardian_claves.py lista                       -> nombres guardados y como terminan (...a1B)
    python guardian_claves.py renombrar CLAVE_1530 TRELLO_API_KEY
    python guardian_claves.py borrar CLAVE_1112_141500        (solo si Alexander lo pide)
"""

from __future__ import annotations

import ctypes
import os
import re
import sys
import winreg
from pathlib import Path

VAULT = Path(os.environ.get("NOVA_VAULT_DIR", r"G:\Mi unidad\Antigravity\vault"))
ARCHIVO = "google_cloud.env"
RE_NOMBRE = re.compile(r"^[A-Z][A-Z0-9_]{2,60}$")

# Prefijo de la clave -> nombre de la variable (el primero que case)
PREFIJOS = [
    (r"^sk-gamma-", "GAMMA_API_KEY"),
    (r"^sk-ant-", "ANTHROPIC_API_KEY"),
    (r"^sk-or-", "OPENROUTER_API_KEY"),
    (r"^sk-(?:proj-)?[A-Za-z0-9_-]{20,}$", "OPENAI_API_KEY"),
    (r"^sk_[a-f0-9]{32,}$", "ELEVENLABS_API_KEY"),
    (r"^AIza", "GOOGLE_API_KEY"),
    (r"^(?:ghp|gho|ghs|ghu)_|^github_pat_", "GITHUB_TOKEN"),
    (r"^re_", "RESEND_API_KEY"),
    (r"^gsk_", "GROQ_API_KEY"),
    (r"^hf_", "HUGGINGFACE_TOKEN"),
    (r"^sb_secret_", "SUPABASE_SECRET_KEY"),
    (r"^sb_publishable_", "SUPABASE_PUBLISHABLE_KEY"),
    (r"^(?:sk|rk)_live_", "STRIPE_SECRET_KEY"),
    (r"^pk_live_", "STRIPE_PUBLISHABLE_KEY"),
    (r"^xox[abprs]-", "SLACK_TOKEN"),
    (r"^AKIA", "AWS_ACCESS_KEY_ID"),
]
# Si el prefijo no lo dice, lo que Luaz escribio justo antes de pegar ("la api de trello: ...")
SERVICIOS = ["gamma", "trello", "openai", "anthropic", "claude", "gemini", "google", "youtube", "groq", "mistral",
             "openrouter", "supabase", "resend", "elevenlabs", "github", "stripe", "huggingface", "deepseek",
             "notion", "airtable", "twilio", "cloudflare", "vercel", "netlify", "highlevel", "brevo", "mailchimp"]


def nombre_para(clave: str, contexto: str = "") -> str:
    for patron, nombre in PREFIJOS:
        if re.search(patron, clave):
            return nombre
    bajo = contexto.lower()
    encontrados = [(bajo.rfind(s), s) for s in SERVICIOS if s in bajo]
    if encontrados:
        servicio = max(encontrados)[1]
        sufijo = "TOKEN" if "token" in bajo[-40:] else "API_KEY"  # "y el token de trello:" / "trello token:"
        return f"{servicio.upper()}_{sufijo}"
    return "CLAVE_" + __import__("time").strftime("%m%d_%H%M%S")


def _leer() -> list[str]:
    ruta = VAULT / ARCHIVO
    return ruta.read_text(encoding="utf-8-sig").splitlines() if ruta.exists() else []


def _escribir(lineas: list[str]) -> None:
    VAULT.mkdir(parents=True, exist_ok=True)
    (VAULT / ARCHIVO).write_text("\n".join(lineas).rstrip() + "\n", encoding="utf-8")


def _variable_windows(nombre: str, valor: str | None) -> None:
    """Variable de usuario (como hace nova_vault_sync.ps1) + aviso a Windows para que la vean los programas nuevos."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
        if valor is None:
            try:
                winreg.DeleteValue(k, nombre)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(k, nombre, 0, winreg.REG_SZ, valor)
    if valor is None:
        os.environ.pop(nombre, None)
    else:
        os.environ[nombre] = valor
    try:  # WM_SETTINGCHANGE (sin esperar a nadie)
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 1000, None)
    except Exception:
        pass


def guardar(clave: str, nombre: str) -> tuple[str, bool]:
    """Guarda NOMBRE=clave en el cofre. Devuelve (nombre final, ya_estaba). Si el nombre existe con otro valor,
    se sustituye (la clave nueva manda: es la que Luaz acaba de pegar)."""
    clave = clave.strip()
    if not RE_NOMBRE.match(nombre):
        nombre = nombre_para(clave)
    lineas = _leer()
    for i, linea in enumerate(lineas):
        k, _, v = linea.partition("=")
        if k.strip() == nombre:
            if v.strip() == clave:
                _variable_windows(nombre, clave)
                return nombre, True
            lineas[i] = f"{nombre}={clave}"
            break
    else:
        if any(linea.partition("=")[2].strip() == clave for linea in lineas):  # misma clave con otro nombre
            return next(linea.partition("=")[0].strip() for linea in lineas if linea.partition("=")[2].strip() == clave), True
        lineas.append(f"{nombre}={clave}")
    _escribir(lineas)
    _variable_windows(nombre, clave)
    return nombre, False


def lista() -> list[str]:
    salida = []
    for linea in _leer():
        k, _, v = linea.partition("=")
        if k.strip() and not k.strip().startswith("#") and v.strip():
            salida.append(f"{k.strip():<34} ...{v.strip()[-3:]}")
    return salida


def renombrar(viejo: str, nuevo: str) -> str:
    if not RE_NOMBRE.match(nuevo):
        return f"[error] '{nuevo}' no vale como nombre: MAYUSCULAS_Y_GUIONES_BAJOS (ej. TRELLO_API_KEY)"
    lineas = _leer()
    for i, linea in enumerate(lineas):
        k, _, v = linea.partition("=")
        if k.strip() == viejo:
            if any(x.partition("=")[0].strip() == nuevo for x in lineas):
                return f"[error] Ya existe {nuevo} en el cofre"
            lineas[i] = f"{nuevo}={v.strip()}"
            _escribir(lineas)
            _variable_windows(viejo, None)
            _variable_windows(nuevo, v.strip())
            return f"[ok] {viejo} -> {nuevo}"
    return f"[error] No hay {viejo} en el cofre (mira: guardian_claves.py lista)"


def borrar(nombre: str) -> str:
    lineas = _leer()
    nuevas = [x for x in lineas if x.partition("=")[0].strip() != nombre]
    if len(nuevas) == len(lineas):
        return f"[error] No hay {nombre} en el cofre (mira: guardian_claves.py lista)"
    _escribir(nuevas)
    _variable_windows(nombre, None)
    return f"[ok] {nombre} borrada del cofre y de Windows"


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else "lista"
    if orden == "lista":
        print("\n".join(lista()) or "(cofre vacio)")
    elif orden == "renombrar" and len(sys.argv) == 4:
        print(renombrar(sys.argv[2], sys.argv[3]))
    elif orden == "borrar" and len(sys.argv) == 3:
        print(borrar(sys.argv[2]))
    else:
        print(__doc__)
