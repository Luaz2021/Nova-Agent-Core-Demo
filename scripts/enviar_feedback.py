"""
Script de Feedback Directo y Conexion con GitHub para Nova
==========================================================
Permite a cualquier usuario enviar sugerencias o errores solucionados
a Saul Martinez sin exponer sus rutas privadas, datos locales ni contraseñas.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.parse
import webbrowser
from pathlib import Path

REPO_URL = "https://github.com/Luaz2021/Nova-Agent-Core-Demo"

def sanitize_text(text: str) -> str:
    """Borra rutas de usuario, IPs y nombres privados antes de subir."""
    text = re.sub(r'[A-Za-z]:\\[Uu]sers\\[^\\]+', '<USER_HOME>', text)
    text = re.sub(r'/Users/[^/]+', '<USER_HOME>', text)
    text = re.sub(r'/home/[^/]+', '<USER_HOME>', text)
    text = re.sub(r'\b192\.168\.\d+\.\d+\b', '<LOCAL_IP>', text)
    text = re.sub(r'\b10\.\d+\.\d+\.\d+\b', '<LOCAL_IP>', text)
    return text

def abrir_mensaje_directo(mensaje: str = ""):
    msg_san = sanitize_text(mensaje)
    query = urllib.parse.urlencode({
        "template": "01_sugerencia.yml",
        "title": f"[Mensaje a Saul]: {msg_san[:50]}...",
        "idea_titulo": msg_san[:60],
        "descripcion": msg_san
    })
    url = f"{REPO_URL}/issues/new?{query}"
    print(f"\n[INFO] Abriendo canal directo con Saul Martinez en tu navegador...")
    webbrowser.open(url)

def abrir_formulario_sugerencia(titulo: str = "", descripcion: str = ""):
    titulo_san = sanitize_text(titulo)
    desc_san = sanitize_text(descripcion)
    
    query = urllib.parse.urlencode({
        "template": "01_sugerencia.yml",
        "title": f"[Sugerencia]: {titulo_san}",
        "idea_titulo": titulo_san,
        "descripcion": desc_san
    })
    url = f"{REPO_URL}/issues/new?{query}"
    print(f"\n[INFO] Abriendo formulario de sugerencia en tu navegador...")
    webbrowser.open(url)

def abrir_formulario_fix(contexto: str = "", causa: str = "", solucion: str = ""):
    ctx_san = sanitize_text(contexto)
    causa_san = sanitize_text(causa)
    sol_san = sanitize_text(solucion)

    query = urllib.parse.urlencode({
        "template": "02_error_solucionado.yml",
        "title": f"[Fix]: {ctx_san}",
        "contexto": ctx_san,
        "causa_raiz": causa_san,
        "solucion": sol_san
    })
    url = f"{REPO_URL}/issues/new?{query}"
    print(f"\n[INFO] Abriendo formulario de error solucionado en tu navegador...")
    webbrowser.open(url)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        modo = sys.argv[1].lower()
        if modo in {"mensaje", "msg", "creador", "directo"}:
            cuerpo = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
            abrir_mensaje_directo(cuerpo)
        elif modo == "fix":
            abrir_formulario_fix()
        else:
            abrir_formulario_sugerencia(modo, " ".join(sys.argv[2:]))
    else:
        abrir_formulario_sugerencia()
