"""Carriles por tema (20/11/2026, Claude; el usuario: "debe ser en automatico y saber cuando y donde, asi como lo pensamos
de las web").

Flash no decide que skill leer: el CODIGO decide. Lo usan:
- nova_hook_turno.py (pre): detecta el tema en el mensaje del usuario, activa el carril y manda leer su KIT (una
  ficha corta en herramientas\\carriles\\). El kit queda en la conversacion (cache): no se relee en cada mensaje.
- nova_hook.py (PreToolUse): si el carril es obligatorio y Nova va a escribir un archivo de ese tema SIN haber leido
  el kit, la frena UNA vez ("lee primero el kit"). La segunda vez la deja (nunca un bucle).
Reglas (palabras, atajos, extensiones) en herramientas\\carriles\\carriles.json.
"""

import json
import re
import time
from pathlib import Path

DIR = Path.home() / ".gemini" / "antigravity" / "herramientas" / "carriles"
REGLAS = DIR / "carriles.json"
ESTADO = Path(__file__).resolve().parent / ".nova_carriles.json"
MAX_CONVS = 300


def reglas() -> dict:
    try:
        return json.loads(REGLAS.read_text(encoding="utf-8")).get("carriles", {})
    except (OSError, ValueError):
        return {}


def detectar(texto: str) -> list[str]:
    """Carriles que encajan con el texto (atajo al principio = solo ese carril)."""
    t = (texto or "").strip().lower()
    if not t:
        return []
    rs = reglas()
    for nombre, r in rs.items():
        if any(t.startswith(a) for a in r.get("atajos", [])):
            return [nombre]
    encontrados = []
    for nombre, r in rs.items():
        if any(re.search(p, t) for p in r.get("palabras", [])):
            encontrados.append(nombre)
    return encontrados


def kit(nombre: str) -> Path:
    """25/11: el kit puede ser una ficha de carriles\\ o directamente un INDICE de skills ("<NOVA_HOME>/config/...")."""
    k = reglas().get(nombre, {}).get("kit", f"carril_{nombre}.md").replace("\\", "/")  # v3.3: vale en los 3 sistemas
    if k.startswith("<NOVA_HOME>"):
        return Path.home() / ".gemini" / k[len("<NOVA_HOME>"):].lstrip("/")
    return DIR / k


def marca_kit(nombre: str) -> str:
    """Texto que identifica la lectura del kit en el transcript (para un SKILL.md, su carpeta: 'index-java')."""
    p = kit(nombre)
    return p.parent.name if p.name.lower() == "skill.md" else p.name


def por_ruta(ruta_archivo: str) -> list[str]:
    """25/11 (router): carriles cuyo patron 'rutas' encaja con el archivo que se va a escribir (aunque el usuario no
    haya nombrado el tema: una practica de Android se reconoce por res\\layout\\*.xml o .kt)."""
    r = (ruta_archivo or "").replace("/", "\\")
    return [n for n, d in reglas().items() if d.get("rutas") and any(re.search(p, r) for p in d["rutas"])
            and not any(re.search(p, r) for p in d.get("rutas_no", []))]


def leer_estado() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_estado(e: dict) -> None:
    try:
        ESTADO.write_text(json.dumps(dict(list(e.items())[-MAX_CONVS:]), ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def activar(conv: str, texto: str) -> tuple[list[str], list[str]]:
    """(carriles NUEVOS en este mensaje, todos los ACTIVOS de la conversacion)."""
    e = leer_estado()
    c = e.setdefault(conv, {"activos": [], "frenados": [], "hora": 0})
    nuevos = [n for n in detectar(texto) if n not in c["activos"]]
    c["activos"] += nuevos
    c["hora"] = time.time()
    guardar_estado(e)
    return nuevos, list(c["activos"])


def kit_leido(transcript: str, nombre: str) -> bool:
    """True si en la conversacion hay una lectura (read_file/view_file) del kit del carril."""
    archivo = marca_kit(nombre)
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if archivo in linea and ('"read_file"' in linea or '"view_file"' in linea):
                    return True
    except OSError:
        pass
    return False


def pendiente_de_leer(conv: str, transcript: str, ruta_archivo: str) -> str | None:
    """Carril obligatorio activo cuyo kit NO se ha leido y que cubre la extension del archivo que se va a escribir.
    Devuelve su nombre la PRIMERA vez (y lo marca como frenado); despues None (nunca un bucle)."""
    e = leer_estado()
    if not ruta_archivo:
        return None
    nuevos_ruta = por_ruta(ruta_archivo)  # 25/11: el archivo activa su carril aunque el mensaje no lo nombrara
    c = e.get(conv)
    if nuevos_ruta:
        c = e.setdefault(conv, {"activos": [], "frenados": [], "hora": time.time()})
        c["activos"] += [n for n in nuevos_ruta if n not in c["activos"]]
        guardar_estado(e)
    if not c:
        return None
    ext = Path(ruta_archivo.strip().strip('"')).suffix.lower()
    rs = reglas()
    for nombre in c.get("activos", []):
        r = rs.get(nombre, {})
        if not r.get("obligatorio") or ext not in r.get("extensiones", []) or nombre in c.get("frenados", []):
            continue
        if transcript and kit_leido(transcript, nombre):
            continue
        c.setdefault("frenados", []).append(nombre)
        guardar_estado(e)
        return nombre
    return None


def mensaje_turno(conv: str, texto: str, transcript: str) -> str:
    """Aviso para el modelo al empezar un mensaje del usuario (vacio si no hay carril)."""
    nuevos, activos = activar(conv, texto)
    if not activos:
        return ""
    por_leer = [n for n in activos if not (transcript and kit_leido(transcript, n))]
    if not por_leer:
        return f"CARRILES ACTIVOS: {', '.join(activos)} (kits ya leidos: aplicalos y cumple su 'Definicion de hecho')."
    rutas = " ".join(f'"{kit(n)}"' for n in por_leer)
    # 25/11 (router): las REGLAS DE ORO del carril van en el propio aviso (llegan aunque el modelo no lea nada)
    oro = [f"- {x}" for n in por_leer for x in reglas().get(n, {}).get("oro", [])]
    return (f"CARRIL {', '.join(por_leer).upper()} (lo detecta un hook por el tema). ANTES de escribir codigo o documentos "
            f"lee con read_file, en UNA llamada en paralelo, su kit corto: {rutas}. Es lo esencial de tus skills de ese "
            "tema: aplicalo y cumple su 'Definicion de hecho' antes de dar nada por terminado. "
            "(Si el tema no encaja con lo que pide el usuario, ignora este aviso.)"
            + ("\nREGLAS DE ORO:\n" + "\n".join(oro[:10]) if oro else ""))
