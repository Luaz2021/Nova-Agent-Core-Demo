"""
Script de Feedback Directo y Conexion Segura con GitHub para Nova
=================================================================
Permite a cualquier usuario enviar mensajes directos (/creador), fixes (/reportar-fallo)
o skills (/compartir-skill) a Saul Martinez sanitizando rutas privadas, IPs y secretos.
"""

from __future__ import annotations
import re
import sys
import urllib.parse
import webbrowser

REPO_URL = "https://github.com/Luaz2021/Nova-Agent-Core-Demo"


def sanitize_text(text: str) -> str:
    """Borra rutas de usuario, IPs locales y tokens antes de abrir o enviar."""
    text = re.sub(r"[A-Za-z]:\\[Uu]sers\\[^\\\s]+", "<USER_HOME>", text)
    text = re.sub(r"/Users/[^/\s]+", "<USER_HOME>", text)
    text = re.sub(r"/home/[^/\s]+", "<USER_HOME>", text)
    text = re.sub(r"\b192\.168\.\d+\.\d+\b", "<LOCAL_IP>", text)
    text = re.sub(r"\b10\.\d+\.\d+\.\d+\b", "<LOCAL_IP>", text)
    text = re.sub(r"(AIza[0-9A-Za-z\-_]{35}|sk-[0-9A-Za-z]{20,}|ghp_[0-9A-Za-z]{30,})", "<REDACTED_KEY>", text)
    return text


def abrir_mensaje_directo(mensaje: str = ""):
    msg_san = sanitize_text(mensaje)
    query = urllib.parse.urlencode({
        "template": "01_sugerencia.yml",
        "labels": "buzon-creador",
        "title": f"[Mensaje a Saul]: {msg_san[:50]}",
        "idea_titulo": msg_san[:60],
        "descripcion": msg_san,
    })
    url = f"{REPO_URL}/issues/new?{query}"
    print("[OK] Abriendo canal directo con Saul Martinez en tu navegador (datos privados sanitizados)...")
    webbrowser.open(url)


def abrir_formulario_sugerencia(titulo: str = "", descripcion: str = "", es_skill: bool = False):
    titulo_san = sanitize_text(titulo)
    desc_san = sanitize_text(descripcion)
    prefijo = "[Skill Comunitaria]" if es_skill else "[Sugerencia]"
    label = "skill-comunitaria" if es_skill else "sugerencia"
    query = urllib.parse.urlencode({
        "template": "01_sugerencia.yml",
        "labels": label,
        "title": f"{prefijo}: {titulo_san[:50]}",
        "idea_titulo": titulo_san,
        "descripcion": desc_san,
    })
    url = f"{REPO_URL}/issues/new?{query}"
    print(f"[OK] Abriendo envio de {prefijo} en tu navegador...")
    webbrowser.open(url)


def abrir_formulario_fix(contexto: str = "", causa: str = "", solucion: str = ""):
    ctx_san = sanitize_text(contexto)
    causa_san = sanitize_text(causa)
    sol_san = sanitize_text(solucion)
    query = urllib.parse.urlencode({
        "template": "02_error_solucionado.yml",
        "labels": "napkin-crowd",
        "title": f"[Fix Napkin]: {ctx_san[:50]}",
        "contexto": ctx_san,
        "causa_raiz": causa_san,
        "solucion": sol_san,
    })
    url = f"{REPO_URL}/issues/new?{query}"
    print("[OK] Abriendo reporte de fallo resuelto (Napkin Crowd) en tu navegador...")
    webbrowser.open(url)


# ------------------------------------------------------------------ /enviar-informe (v3.2)
def _mem():
    from pathlib import Path
    return Path.home() / ".gemini" / "antigravity" / "memory"


def _limpio(texto: str) -> str:
    texto = sanitize_text(texto)
    texto = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "<EMAIL>", texto)
    texto = re.sub(r"(?i)\b(token|clave|password|secret|api[_-]?key)\s*[:=]\s*\S+", r"\1=<REDACTED>", texto)
    return texto


def _lineas(p, maximo=40):
    try:
        return [l.rstrip() for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()][-maximo:]
    except OSError:
        return []


def preparar_informe(enviar: bool = False) -> int:
    """Prepara el informe (SOLO lecciones, servilleta nueva y TIPO de errores), lo deja para revisar y,
    solo con --enviar (el usuario ya lo reviso), abre el formulario de GitHub en el navegador."""
    import collections
    import json
    import time
    mem = _mem()
    lecciones = _lineas(mem / "inbox_lecciones.md")
    oficial = set(_lineas(mem / "napkin_oficial.md", 100000))
    napkin = [l for l in _lineas(mem / "napkin.md", 400) if l not in oficial][-40:]
    tipos = collections.Counter()
    for l in _lineas(mem / "registros" / "telemetria_hooks.jsonl", 5000):
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if d.get("decision") in ("deny", "force_ask", "ask"):
            tipos[f"{d.get('decision')} - {str(d.get('regla') or d.get('motivo') or d.get('herramienta') or 'otra')[:40]}"] += 1
    fallos = [f"{n} x {t}" for t, n in tipos.most_common(15)]
    version = ""
    try:
        version = json.loads((mem.parent / "manifest_master.json").read_text(encoding="utf-8-sig")).get("Version", "")
    except (OSError, ValueError):
        pass
    partes = {
        "lecciones": _limpio("\n".join(lecciones) or "(sin lecciones nuevas)"),
        "napkin": _limpio("\n".join(napkin) or "(sin entradas nuevas)"),
        "fallos": _limpio("\n".join(fallos) or "(sin errores registrados)"),
    }
    vista = mem / "informe_para_enviar.md"
    if not enviar:
        vista.parent.mkdir(parents=True, exist_ok=True)
        vista.write_text(
            f"# Informe de Nova v{version} ({time.strftime('%Y-%m-%d')})\n\nREVISALO: borra lo que no quieras enviar y luego "
            "di 'Nova, envia el informe'.\n\n## Lecciones\n" + partes["lecciones"] + "\n\n## Servilleta (entradas nuevas)\n"
            + partes["napkin"] + "\n\n## Errores de Nova (por tipo)\n" + partes["fallos"] + "\n", encoding="utf-8")
        print(f"[INFORME] Preparado para que lo revises: {vista} (solo lecciones, servilleta y tipos de error; "
              "sin rutas, correos ni claves). Cuando quieras: 'Nova, envia el informe'.")
        return 0
    if not vista.exists():
        print("[INFORME] Primero hay que prepararlo y revisarlo: /enviar-informe")
        return 2
    texto = vista.read_text(encoding="utf-8")  # se envia lo que el usuario dejo tras revisarlo

    def seccion(nombre):
        m = re.search(rf"## {nombre}[^\n]*\n(.*?)(?=\n## |\Z)", texto, re.S)
        return _limpio(m.group(1).strip())[:1800] if m else ""
    query = urllib.parse.urlencode({
        "template": "03_informe_uso.yml", "labels": "informe-uso", "title": f"[Informe]: Nova v{version}",
        "version": version, "lecciones": seccion("Lecciones"), "napkin": seccion("Servilleta"),
        "fallos": seccion("Errores"),
    })
    webbrowser.open(f"{REPO_URL}/issues/new?{query}")
    (mem / "informe_ultimo_envio.txt").write_text(time.strftime("%Y-%m-%d"), encoding="utf-8")
    print("[OK] Abierto el formulario del informe en tu navegador: revisalo y pulsa 'Submit new issue' para enviarlo.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower().lstrip("/") in {"informe", "enviar-informe"}:
        sys.exit(preparar_informe("--enviar" in sys.argv))
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
        else:
            abrir_formulario_sugerencia(modo, " ".join(sys.argv[2:]))
    else:
        abrir_formulario_sugerencia()
