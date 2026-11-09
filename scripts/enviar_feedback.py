"""
Script de Feedback Directo y Conexion Segura con GitHub para Nova
=================================================================
Permite a cualquier usuario enviar al creador (Saul Martinez), sanitizando rutas privadas, IPs y secretos:
  /creador [mensaje]          -> mensaje directo                     (etiqueta buzon-creador)
  /reportar-fallo             -> fallo resuelto o esquivado          (etiquetas fix-esquivado, napkin)
  /compartir-skill [nombre]   -> skill propia para incluirla         (etiqueta skill-comunitaria)
  /enviar-informe             -> lecciones aprendidas y fallos de Nova en este equipo (etiqueta informe-uso)

Nada se envia solo: se abre el formulario de GitHub ya relleno en el navegador y el usuario decide si lo publica.

    python enviar_feedback.py creador "mensaje"
    python enviar_feedback.py fallo "contexto" "causa" "solucion"
    python enviar_feedback.py skill <nombre> "descripcion"
    python enviar_feedback.py informe [--dias 30] [--ver]     (--ver: solo muestra el texto, no abre nada)
"""

from __future__ import annotations

import collections
import json
import re
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

REPO_URL = "https://github.com/Luaz2021/Nova-Agent-Core-Demo"
ANTIGRAVITY = Path.home() / ".gemini" / "antigravity"
MEMORIA = ANTIGRAVITY / "memory"
INBOX = MEMORIA / "inbox_lecciones.md"
TELEMETRIA = MEMORIA / "registros" / "telemetria_hooks.jsonl"
ESTADO_INFORME = MEMORIA / "registros" / "ultimo_informe.json"
MAX_URL = 7500  # GitHub corta las URL muy largas


def sanitize_text(text: str) -> str:
    """Borra rutas de usuario, IPs locales, correos y claves antes de abrir o enviar."""
    text = re.sub(r"[A-Za-z]:\\[Uu]sers\\[^\\\s\"']+", "<USER_HOME>", text)
    text = re.sub(r"/Users/[^/\s\"']+", "<USER_HOME>", text)
    text = re.sub(r"/home/[^/\s\"']+", "<USER_HOME>", text)
    text = re.sub(r"\b192\.168\.\d+\.\d+\b", "<LOCAL_IP>", text)
    text = re.sub(r"\b10\.\d+\.\d+\.\d+\b", "<LOCAL_IP>", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "<EMAIL>", text)
    text = re.sub(r"(AIza[0-9A-Za-z\-_]{35}|sk-[0-9A-Za-z_-]{20,}|gh[pousr]_[0-9A-Za-z]{30,}|hf_[0-9A-Za-z]{30,}"
                  r"|xox[bpas]-[0-9A-Za-z-]+|AKIA[0-9A-Z]{16})", "<REDACTED_KEY>", text)
    text = re.sub(r"(?i)((api[_-]?key|token|secret|password|contrase[nñ]a)\s*[:=]\s*)\S+", r"\1<REDACTED>", text)
    return text


def _abrir(query: dict, aviso: str) -> None:
    url = f"{REPO_URL}/issues/new?{urllib.parse.urlencode(query)}"
    while len(url) > MAX_URL:  # recorta el campo mas largo hasta que quepa
        campo = max((k for k in query if k not in ("template", "labels", "title")), key=lambda k: len(query[k]))
        query[campo] = query[campo][: int(len(query[campo]) * 0.8)] + "\n[... recortado]"
        url = f"{REPO_URL}/issues/new?{urllib.parse.urlencode(query)}"
    print(aviso)
    if not webbrowser.open(url):
        print(f"No pude abrir el navegador. Abre este enlace:\n{url}")


def abrir_mensaje_directo(mensaje: str = ""):
    msg_san = sanitize_text(mensaje)
    _abrir({"template": "01_sugerencia.yml", "labels": "buzon-creador", "title": f"[Mensaje a Saul]: {msg_san[:50]}",
            "idea_titulo": msg_san[:60], "descripcion": msg_san},
           "[OK] Abriendo canal directo con Saul Martinez en tu navegador (datos privados sanitizados)...")


def abrir_formulario_sugerencia(titulo: str = "", descripcion: str = "", es_skill: bool = False):
    titulo_san, desc_san = sanitize_text(titulo), sanitize_text(descripcion)
    prefijo = "[Skill Comunitaria]" if es_skill else "[Sugerencia]"
    _abrir({"template": "01_sugerencia.yml", "labels": "skill-comunitaria" if es_skill else "sugerencia",
            "title": f"{prefijo}: {titulo_san[:50]}", "idea_titulo": titulo_san, "descripcion": desc_san},
           f"[OK] Abriendo envio de {prefijo} en tu navegador...")


def abrir_formulario_fix(contexto: str = "", causa: str = "", solucion: str = ""):
    ctx_san = sanitize_text(contexto)
    _abrir({"template": "02_error_solucionado.yml", "labels": "fix-esquivado,napkin", "title": f"[Fix]: {ctx_san[:50]}",
            "contexto": ctx_san, "causa_raiz": sanitize_text(causa), "solucion": sanitize_text(solucion)},
           "[OK] Abriendo reporte de fallo resuelto (Napkin Community) en tu navegador...")


# ---------------------------------------------------------------- informe de uso (lecciones + fallos)
def _leer_json(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


# El informe SOLO lleva: lecciones de autoaprendizaje, entradas nuevas de la servilleta (napkin) y QUE TIPO de
# errores cometio Nova (por categoria, nunca el comando, la ruta ni el nombre del archivo). Nada del equipo,
# del sistema, del perfil ni de los proyectos. Y todo pasa por sanitize_text (claves, rutas, correos, IPs).
NAPKIN = MEMORIA / "napkin.md"
NAPKIN_OFICIAL = MEMORIA / "napkin_oficial.md"
CATEGORIAS_FALLO = [
    ("freno de gasto (tokens)", r"FRENO DE GASTO"),
    ("web grande escrita desde la nube", r"lineas de web"),
    ("codigo grande escrito desde la nube", r"va a escribir \d+ lineas de codigo"),
    ("edicion en rama principal (Ley 5)", r"LEY 5"),
    ("intento de leer o mostrar claves", r"AVISO CLAVES"),
    ("comando destructivo", r"Comando destructivo"),
    ("escritura en carpeta protegida", r"carpeta protegida"),
    ("demasiadas herramientas seguidas", r"herramientas seguidas"),
    ("python a secas en Windows", r"'python'/'py' a secas"),
    ("ruta con espacios sin comillas", r"SIN comillas"),
    ("documento guardado en sitio equivocado", r"documentos \(PDF"),
    ("lectura de archivo pesado o de dependencias", r"no se mete entero|no se lee"),
    ("archivo nuevo en carpeta no permitida", r"No se crean archivos nuevos"),
    (".env tocado", r"\.env"),
]


def _categoria(motivo: str) -> str:
    return next((nombre for nombre, patron in CATEGORIAS_FALLO if re.search(patron, motivo, re.I)), "otra regla")


def _entradas_napkin_nuevas() -> list[str]:
    """Entradas de la servilleta que NO vienen de la plantilla oficial (lo que aprendio este usuario)."""
    try:
        texto = NAPKIN.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    try:
        oficial = NAPKIN_OFICIAL.read_text(encoding="utf-8", errors="replace")
    except OSError:
        oficial = ""
    entradas, actual = [], []
    for linea in texto.splitlines():
        if re.match(r"^\s*(\d+\.|-)\s+\*\*", linea) or re.match(r"^#{1,3} ", linea):
            if actual:
                entradas.append("\n".join(actual))
            actual = [] if linea.startswith("#") else [linea.rstrip()]
        elif actual and linea.strip():
            actual.append(linea.rstrip())
    if actual:
        entradas.append("\n".join(actual))
    return [e for e in entradas if e.splitlines()[0].strip() not in oficial]


def informe_texto(dias: int = 30) -> dict:
    corte = time.strftime("%Y-%m-%d", time.localtime(time.time() - dias * 86400))
    lecciones = []
    try:
        for linea in INBOX.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^- \[(\d{4}-\d{2}-\d{2})\]", linea.strip())
            if m and m.group(1) >= corte:
                lecciones.append(linea.strip())
    except OSError:
        pass
    categorias, errores_hook = collections.Counter(), 0
    try:
        with TELEMETRIA.open(encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                if str(o.get("t", ""))[:10] < corte:
                    continue
                d = o.get("decision_calculada") or o.get("decision")
                if d and d not in ("allow", "auto_approve") and o.get("motivo"):
                    categorias[_categoria(str(o["motivo"]))] += 1
                elif o.get("decision") == "pedir_leccion":
                    categorias["el usuario corrigio a Nova"] += 1
                elif o.get("lineas_codigo_chat"):
                    categorias["codigo pegado en el chat"] += 1
                if o.get("error_hook"):
                    errores_hook += 1
    except OSError:
        pass
    fallos = [f"- {n}x {c}" for c, n in categorias.most_common()] or ["(ninguno en este periodo)"]
    if errores_hook:
        fallos.append(f"- {errores_hook}x error interno de los hooks")
    return {
        "version": f"Nova v{_leer_json(ANTIGRAVITY / 'manifest_master.json').get('Version', '?')} (ultimos {dias} dias)",
        "lecciones": sanitize_text("\n".join(lecciones[-40:]) or "(sin lecciones en este periodo)"),
        "napkin": sanitize_text("\n\n".join(_entradas_napkin_nuevas()[-15:]) or "(sin entradas nuevas)"),
        "fallos": "\n".join(fallos),
    }


def abrir_informe(dias: int = 30, solo_ver: bool = False):
    datos = informe_texto(dias)
    if solo_ver:
        print(json.dumps(datos, indent=2, ensure_ascii=False))
        return
    _abrir({"template": "03_informe_uso.yml", "labels": "informe-uso", "title": f"[Informe]: {datos['version'][:60]}",
            **datos}, "[OK] Abriendo tu informe de uso en el navegador. Revisalo y pulsa 'Submit' solo si quieres enviarlo.")
    try:
        ESTADO_INFORME.parent.mkdir(parents=True, exist_ok=True)
        ESTADO_INFORME.write_text(json.dumps({"ultimo": time.strftime("%Y-%m-%d")}), encoding="utf-8")
    except OSError:
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        modo = sys.argv[1].lower().lstrip("/")
        if modo in {"mensaje", "msg", "creador", "directo"}:
            abrir_mensaje_directo(" ".join(sys.argv[2:]))
        elif modo in {"fix", "reportar-fallo", "fallo"}:
            ctx = sys.argv[2] if len(sys.argv) > 2 else ""
            causa = sys.argv[3] if len(sys.argv) > 3 else ""
            sol = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
            abrir_formulario_fix(ctx, causa, sol)
        elif modo in {"skill", "compartir-skill"}:
            nombre = sys.argv[2] if len(sys.argv) > 2 else "Nueva Skill"
            desc = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            abrir_formulario_sugerencia(nombre, desc, es_skill=True)
        elif modo in {"informe", "enviar-informe", "lecciones"}:
            dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 30
            abrir_informe(dias, solo_ver="--ver" in sys.argv)
        else:
            abrir_formulario_sugerencia(modo, " ".join(sys.argv[2:]))
    else:
        abrir_formulario_sugerencia()
