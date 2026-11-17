"""
Nova Doctor multiplataforma v3.2 (Windows / macOS / Linux)
==========================================================
Creado por Saul Alexander Martinez Rivas (@Luaz2021)

Revisa la instalacion de Nova en ESTE equipo y, con --reparar, arregla sola lo que sepa arreglar.
Lo lanzan: el actualizador (/actualizar-nova) al terminar cada parche, y Nova cuando algo no va
("Nova, revisate" -> python ~/.gemini/antigravity/scripts/nova_doctor.py --reparar).
En Windows, ademas, llama al Doctor completo de PowerShell (nova_doctor.ps1: Python propio con uv, hooks.json,
Ollama, voz...). En macOS/Linux hace aqui lo equivalente.

Revisa:
  1. Carpetas de Nova en ~/.gemini (si falta una -> el actualizador la trae con --force).
  2. Carpeta rota de v3.0/v3.1 en Windows (nombre con un caracter invisible): rescata herramientas/clonador.
  3. Skills ENLAZADAS (junctions/symlinks de instalaciones viejas) -> copias reales; enlaces rotos -> fuera.
  4. Python propio de Nova (nova_env) y sus librerias (macOS/Linux: las instala con pip).
  5. Reglas automaticas (hooks) registradas en ~/.gemini/config/hooks.json.
  6. Reglas GEMINI.md en su sitio.
  7. Navegador para la extension (Brave/Chrome/Edge/Opera/Vivaldi; Firefox no es compatible) y Ollama (informativo).
Resultado: ~/.gemini/antigravity/memory/doctor_estado.json (lo lee Nova) y una linea de resumen.
Nunca borra datos del usuario: lo que aparta va a ~/.gemini/antigravity/backups/doctor_<fecha>/.

Uso:
  python nova_doctor.py            (solo revisar)
  python nova_doctor.py --reparar  (revisar y reparar)
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

GEMINI = Path.home() / ".gemini"
AG = GEMINI / "antigravity"
MEM = AG / "memory"
ESTADO = MEM / "doctor_estado.json"
BACKUP = AG / "backups" / f"doctor_{datetime.datetime.now():%Y%m%d_%H%M%S}"
WIN = os.name == "nt"
MAC = sys.platform == "darwin"

CARPETAS = ["nova_core", "config", "config/skills", "antigravity/scripts", "antigravity/memory",
            "antigravity/almacen", "antigravity/herramientas", "antigravity/clonador", "antigravity/skills"]
# Modulos que Nova usa en TODOS los sistemas (la voz con bandeja y la aduana son de Windows: ver LEEME)
MODULOS = ["numpy", "PIL", "docx", "openpyxl", "pptx", "fitz", "aiohttp", "psutil", "playwright", "watchdog"]

res: list[dict] = []


def nota(area: str, estado: str, texto: str) -> None:
    res.append({"area": area, "estado": estado, "texto": texto})
    print(f"  [{estado}] {area}: {texto}")


def es_enlace(p: Path) -> bool:
    """Symlink o junction de Windows (sin depender de Python 3.12)."""
    try:
        if p.is_symlink():
            return True
        if WIN:
            st = os.lstat(p)
            return bool(getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return False
    return False


def quitar_enlace(p: Path) -> None:
    """Quita SOLO el enlace (nunca el contenido al que apunta)."""
    try:
        os.unlink(p)
    except (IsADirectoryError, PermissionError, OSError):
        os.rmdir(p)  # junction de Windows


def nova_python() -> Path | None:
    p = GEMINI / "nova_env" / ("Scripts/python.exe" if WIN else "bin/python")
    return p if p.exists() else None


# ------------------------------------------------------------------ 1. carpetas
def revisar_carpetas(reparar: bool) -> None:
    faltan = [c for c in CARPETAS if not (GEMINI / c).is_dir()]
    if not faltan:
        nota("carpetas", "OK", "estan todas las carpetas de Nova")
        return
    if reparar:
        for c in faltan:
            (GEMINI / c).mkdir(parents=True, exist_ok=True)
        nota("carpetas", "ARREGLADO", f"creadas {', '.join(faltan)}; su contenido lo trae: python actualizar_nova.py --force")
    else:
        nota("carpetas", "FALLA", f"faltan {', '.join(faltan)} (repara: python nova_doctor.py --reparar)")


# ------------------------------------------------------------------ 2. carpeta rota de v3.0/v3.1 (Windows)
def revisar_carpeta_invisible(reparar: bool) -> None:
    if not WIN:
        return
    sospechosas = []
    for base in (GEMINI, GEMINI.parent):
        try:
            sospechosas += [d for d in base.iterdir() if d.is_dir() and any(ord(ch) < 32 for ch in d.name)]
        except OSError:
            pass
    if not sospechosas:
        return
    if not reparar:
        nota("carpeta_rota", "FALLA", f"{len(sospechosas)} carpeta(s) con nombre roto de la v3.1 (repara con --reparar)")
        return
    for d in sospechosas:
        for sub in ("herramientas", "clonador"):
            if (d / sub).is_dir():
                shutil.copytree(d / sub, AG / sub, dirs_exist_ok=True)
        destino = BACKUP / "carpeta_rota"
        destino.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(destino / d.name.encode("ascii", "replace").decode().replace("?", "_")))
    nota("carpeta_rota", "ARREGLADO", "herramientas/clonador rescatados de la carpeta rota de la v3.1 (copia en backups)")


# ------------------------------------------------------------------ 3. skills enlazadas
def revisar_enlaces(reparar: bool) -> None:
    enlaces, rotos = [], []
    for raiz in (GEMINI / "config" / "skills", AG / "skills"):
        if not raiz.is_dir() or es_enlace(raiz):
            continue
        for p in raiz.iterdir():
            if es_enlace(p):
                (enlaces if p.exists() else rotos).append(p)
    if not enlaces and not rotos:
        nota("skills", "OK", "skills como copias reales (sin enlaces)")
        return
    if not reparar:
        nota("skills", "FALLA" if rotos else "AVISO",
             f"{len(rotos)} skill(s) con enlace ROTO y {len(enlaces)} enlazadas a la carpeta de descarga "
             "(repara: python nova_doctor.py --reparar)")
        return
    for p in enlaces:  # enlace vivo -> se copia su contenido y queda carpeta real
        tmp = p.with_name(p.name + ".nova_copia")
        shutil.copytree(p, tmp, dirs_exist_ok=True)
        quitar_enlace(p)
        tmp.rename(p)
    for p in rotos:  # enlace roto -> fuera; el actualizador vuelve a traer la skill
        quitar_enlace(p)
    nota("skills", "ARREGLADO", f"{len(enlaces)} skills pasadas a copia real y {len(rotos)} enlaces rotos quitados "
         + ("(las que faltan las trae: python actualizar_nova.py --force)" if rotos else ""))


# ------------------------------------------------------------------ 4. Python de Nova
def revisar_python(reparar: bool) -> None:
    py = nova_python()
    if WIN:
        return  # en Windows lo monta nova_doctor.ps1 (uv + Python fijado), llamado al final
    if not py and reparar:
        subprocess.run([sys.executable, "-m", "venv", str(GEMINI / "nova_env")], check=False)
        py = nova_python()
    if not py:
        nota("python", "FALLA", "no hay ~/.gemini/nova_env (en Debian/Ubuntu: sudo apt install python3-venv; luego --reparar)")
        return
    code = ("import sys\nm=[]\nfor x in sys.argv[1:]:\n    try: __import__(x)\n    except Exception: m.append(x)\n"
            "print(','.join(m))")
    out = subprocess.run([str(py), "-c", code, *MODULOS], capture_output=True, text=True).stdout.strip()
    faltan = [m for m in out.split(",") if m]
    if not faltan:
        nota("python", "OK", f"Python de Nova con sus {len(MODULOS)} librerias")
        return
    if not reparar:
        nota("python", "FALLA", f"faltan librerias: {', '.join(faltan)} (repara con --reparar)")
        return
    req = GEMINI / "nova_core" / "requisitos_nova.txt"
    r = subprocess.run([str(py), "-m", "pip", "install", "-r", str(req)], capture_output=True, text=True)
    if r.returncode != 0:  # versiones fijadas para Windows: se instalan sin version
        libs = [l.split("=")[0].split("<")[0].split(">")[0].strip() for l in req.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.strip().startswith("#")]
        for lib in libs:
            subprocess.run([str(py), "-m", "pip", "install", lib], capture_output=True)
    out = subprocess.run([str(py), "-c", code, *MODULOS], capture_output=True, text=True).stdout.strip()
    faltan = [m for m in out.split(",") if m]
    nota("python", "ARREGLADO" if not faltan else "AVISO",
         "librerias instaladas" if not faltan else f"no se pudieron instalar: {', '.join(faltan)}")


# ------------------------------------------------------------------ 5. hooks
def hooks_ok() -> bool:
    """Las 3 entradas de Nova estan en hooks.json y sus scripts EXISTEN (un nombre corto viejo NOVA_H~1.PY no vale)."""
    try:
        d = json.loads((GEMINI / "config" / "hooks.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    claves = ("nova-guardia-herramientas", "nova-recordatorio-codigo", "nova-correccion-codigo-chat")
    if not all(k in d for k in claves):
        return False
    texto = json.dumps(d).lower()
    return "nova_hook.py" in texto and "nova_hook_turno.py" in texto


def revisar_hooks(reparar: bool) -> None:
    if hooks_ok():
        nota("hooks", "OK", "reglas automaticas registradas")
        return
    inst = GEMINI / "nova_core" / "instalar_hooks.py"
    if reparar and inst.exists():
        subprocess.run([str(nova_python() or sys.executable), str(inst)], check=False)
    ok = hooks_ok()
    nota("hooks", "ARREGLADO" if ok and reparar else ("OK" if ok else "FALLA"),
         "reglas automaticas registradas de nuevo (cierra y abre Antigravity)" if ok
         else "las reglas automaticas no estan registradas (repara: python nova_doctor.py --reparar)")


# ------------------------------------------------------------------ 6. GEMINI.md
def revisar_reglas() -> None:
    g = GEMINI / "config" / "GEMINI.md"
    if g.exists():
        nota("reglas", "OK", "GEMINI.md en su sitio")
    else:
        nota("reglas", "FALLA", "falta ~/.gemini/config/GEMINI.md (lo trae: python actualizar_nova.py --force)")


# ------------------------------------------------------------------ 7. navegador y Ollama (informativo)
def navegadores() -> list[str]:
    encontrados = []
    if WIN:
        pf = [os.environ.get(v, "") for v in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        rutas = {"Brave": r"BraveSoftware\Brave-Browser\Application\brave.exe",
                 "Chrome": r"Google\Chrome\Application\chrome.exe",
                 "Edge": r"Microsoft\Edge\Application\msedge.exe",
                 "Opera": r"Programs\Opera\opera.exe", "Vivaldi": r"Vivaldi\Application\vivaldi.exe",
                 "Firefox": r"Mozilla Firefox\firefox.exe"}
        for n, r in rutas.items():
            if any(b and Path(b, r).exists() for b in pf):
                encontrados.append(n)
    elif MAC:
        for n, app in {"Brave": "Brave Browser", "Chrome": "Google Chrome", "Edge": "Microsoft Edge",
                       "Opera": "Opera", "Vivaldi": "Vivaldi", "Firefox": "Firefox"}.items():
            if Path(f"/Applications/{app}.app").exists():
                encontrados.append(n)
    else:
        for n, exes in {"Brave": ["brave-browser", "brave"], "Chrome": ["google-chrome", "google-chrome-stable"],
                        "Chromium": ["chromium", "chromium-browser"], "Edge": ["microsoft-edge"],
                        "Vivaldi": ["vivaldi"], "Opera": ["opera"], "Firefox": ["firefox"]}.items():
            if any(shutil.which(e) for e in exes):
                encontrados.append(n)
    return encontrados


def revisar_navegador() -> None:
    nav = navegadores()
    chromium = [n for n in nav if n != "Firefox"]
    if chromium:
        nota("navegador", "OK", f"extension de Nova compatible con: {', '.join(chromium)} "
             "(cargala desde ~/.gemini/antigravity/scripts/brave_extension en <navegador>://extensions, modo desarrollador)")
    elif nav:
        nota("navegador", "AVISO", "solo hay Firefox: la extension de Nova necesita un navegador Chromium "
             "(Brave, Chrome, Edge...). Mientras, Nova usa su navegador automatico (Playwright)")
    else:
        nota("navegador", "AVISO", "no encuentro navegador Chromium: Nova usara su navegador automatico (Playwright)")


def revisar_sync() -> None:
    cfg_p = GEMINI / "config" / "nova_sync.json"
    if not cfg_p.exists():
        nota("sync", "OK", "Nova Sync sin configurar (opcional: 'Nova, configura el sync')")
        return
    try:
        cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
        ult = json.loads((MEM / "sync_status.json").read_text(encoding="utf-8")) if (MEM / "sync_status.json").exists() else {}
    except (OSError, ValueError):
        nota("sync", "AVISO", "la configuracion de Nova Sync no se puede leer (repite 'Nova, configura el sync')")
        return
    if not Path(cfg.get("carpeta", "")).is_dir():
        nota("sync", "AVISO", f"no veo la carpeta de Drive ({cfg.get('carpeta')}): abre Google Drive para escritorio")
    elif ult.get("Estado") not in (None, "OK", "CONFLICTOS"):
        nota("sync", "AVISO", f"ultima pasada {ult.get('Modo')}: {ult.get('Estado')} ('Nova, como va el sync')")
    else:
        nota("sync", "OK", f"Nova Sync activo ({ult.get('Timestamp', 'sin pasadas aun')})")


def revisar_ollama() -> None:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            n = len(json.loads(r.read().decode()).get("models", []))
        nota("ollama", "OK", f"IA local encendida ({n} modelos)")
    except Exception:
        nota("ollama", "AVISO", "IA local (Ollama) apagada o no instalada: Nova funciona en modo nube")


# ------------------------------------------------------------------ Windows: Doctor completo
def doctor_windows() -> None:
    ps = AG / "scripts" / "nova_doctor.ps1"
    if WIN and ps.exists() and not os.environ.get("NOVA_DOCTOR_SIN_PS"):  # (NOVA_DOCTOR_SIN_PS: solo pruebas)
        print("[DOCTOR] Doctor completo de Windows (Python propio, hooks, Ollama, voz)...")
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps),
                        "-SinServicios", "-SinAviso"], check=False)


def main() -> int:
    reparar = "--reparar" in sys.argv
    print(f"[NOVA DOCTOR] Revisando Nova en este equipo ({sys.platform}){' y reparando' if reparar else ''}...")
    revisar_carpeta_invisible(reparar)
    revisar_carpetas(reparar)
    revisar_enlaces(reparar)
    if "--estructura" in sys.argv:  # lo usa el actualizador ANTES de bajar el parche (rapido, sin pip ni Doctor)
        return 0
    revisar_python(reparar)
    revisar_hooks(reparar)
    revisar_reglas()
    revisar_navegador()
    revisar_sync()
    revisar_ollama()
    fallos = [r for r in res if r["estado"] == "FALLA"]
    resumen = ("Nova Doctor: todo OK" if not fallos else
               f"Nova Doctor: {len(fallos)} fallo(s) - " + " | ".join(f"{r['area']}: {r['texto']}" for r in fallos))
    if not WIN:  # en Windows el estado lo escribe nova_doctor.ps1 (mas completo)
        MEM.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps({
            "fecha": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}", "ok": not fallos, "resumen": resumen,
            "fallos": [f"{r['area']}: {r['texto']}" for r in fallos],
            "arreglos": [f"{r['area']}: {r['texto']}" for r in res if r["estado"] == "ARREGLADO"],
            "avisos": [f"{r['area']}: {r['texto']}" for r in res if r["estado"] == "AVISO"], "avisado": [],
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(resumen)
    doctor_windows()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
