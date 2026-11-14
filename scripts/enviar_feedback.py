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
        else:
            abrir_formulario_sugerencia(modo, " ".join(sys.argv[2:]))
    else:
        abrir_formulario_sugerencia()
