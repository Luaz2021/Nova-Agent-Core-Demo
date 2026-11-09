import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""Órdenes que acepta el vigilante (se recarga solo: si se añade una orden aquí, no hace falta reiniciar el vigilante)."""
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"


def traducir(linea):
    """Solo estas órdenes; cualquier otra cosa se rechaza."""
    p = linea.strip().split()
    if not p:
        return None
    if p[0] == "analizar" and len(p) in (2, 3) and re.match(r"^https?://[^\s\"'&|<>^]+$", p[1]) and p[2:] in ([], ["--sin-dinamico"]):
        return [sys.executable, "-u", "analizar.py"] + p[1:]
    if p[0] in ("clonar", "cadena") and len(p) == 2 and re.match(r"^https?://[^\s\"'&|<>^]+$", p[1]):
        return [sys.executable, "-u", "clonar.py", p[1]]        # el flujo entero, sin Qwen: analizar -> crear -> verificar
    if p[0] == "construir_legado" and all(re.match(r"^--umbral=\d{2}$", x) for x in p[1:]):
        return [sys.executable, "-u", "construir.py", "--legacy"] + p[1:]   # cadena B retirada (Qwen desde cero)
    if p[0] == "vestir" and len(p) == 1:
        return [sys.executable, "-u", "construir.py", "--vestir"]
    # crear / verificar: sin nombre = último análisis · con nombre = workspace/<nombre> (p. ej. apple_com_iphone_16_pro)
    web = [x for x in p[1:] if not x.startswith("--")]
    if web and not (len(web) == 1 and re.match(r"^[a-z0-9_]{1,60}$", web[0])):
        return None
    carpeta = [str(WORKSPACE / web[0])] if web else []
    if p[0] == "crear" and len(p) == 1 + len(web):
        return [sys.executable, "-u", "crear.py"] + carpeta
    flags = [x for x in p[1:] if x.startswith("--")]
    if p[0] == "verificar" and all(re.match(r"^--(umbral|lista|solo|intentos)=\d{1,3}$", x) for x in flags):
        return [sys.executable, "-u", "verificar.py"] + carpeta + flags
    if p[0] == "lote" and len(p) <= 2 and (len(p) == 1 or re.match(r"^[a-z0-9_]{1,30}$", p[1])):
        return [sys.executable, "-u", "lote.py"] + p[1:]          # "lote" = lote.txt · "lote reintentar" = reintentar.txt
    if p[0] == "probar_guia" and len(p) == 2 and re.match(r"^[a-z0-9_]{1,30}$", p[1]):
        return [sys.executable, "-u", "probar_guia.py", p[1]]
    if p[0] == "crear_cero" and len(p) == 2 and re.match(r"^[a-z0-9_]{1,30}$", p[1]):
        return [sys.executable, "-u", "crear_cero.py", p[1]]
    return None
