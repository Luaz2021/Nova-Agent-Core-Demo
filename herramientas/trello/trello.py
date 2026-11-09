"""
TRELLO · herramienta generica de Nova (sustituye a los scripts sueltos add_card_fase*, populate_trello_bolivar...).

La clave y el token se leen EN LOCAL del vault (trello_api_key / trello_token en vault\\secrets.json) o de las variables
TRELLO_API_KEY / TRELLO_TOKEN. Nunca se imprimen ni salen en los errores: Nova solo ve los resultados.

    python trello.py tableros
    python trello.py listas "<tablero>"                         (tablero = id o parte del nombre)
    python trello.py tarjetas "<tablero>" [--lista "<lista>"]
    python trello.py buscar "<texto>"
    python trello.py crear-tablero "<nombre>" [--listas "Por hacer,Haciendo,Hecho"]
    python trello.py crear-lista "<tablero>" "<nombre>"
    python trello.py crear-tarjeta "<tablero>" --lista "<lista>" --titulo "<titulo>" [--desc "..."] [--vence 2026-11-30]
    python trello.py mover "<id tarjeta>" "<tablero>" --a "<lista>"
    python trello.py comentar "<id tarjeta>" "<texto>"
    python trello.py archivar "<id tarjeta>"                    (se puede desarchivar en Trello)
Anade --json para salida en JSON.
"""

from __future__ import annotations

import sys as _sys
_sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.trello.com/1"


def credenciales() -> tuple[str, str]:
    clave, token = os.environ.get("TRELLO_API_KEY", ""), os.environ.get("TRELLO_TOKEN", "")
    if clave and token:
        return clave, token
    for linea in (Path.home() / ".gemini" / "config" / "secrets.env").read_text(encoding="utf-8").splitlines() \
            if (Path.home() / ".gemini" / "config" / "secrets.env").exists() else []:
        k, _, v = linea.partition("=")
        if k.strip() in ("TRELLO_API_KEY", "TRELLO_TOKEN") and v.strip():
            os.environ.setdefault(k.strip(), v.strip())
    clave, token = os.environ.get("TRELLO_API_KEY", ""), os.environ.get("TRELLO_TOKEN", "")
    if clave and token:
        return clave, token
    candidatos = [Path.home() / ".gemini" / "antigravity" / "vault" / "secrets.json"]
    for ruta in candidatos:
        try:
            if ruta.exists():
                s = json.loads(ruta.read_text(encoding="utf-8"))
                if s.get("trello_api_key") and s.get("trello_token"):
                    return s["trello_api_key"], s["trello_token"]
        except (OSError, ValueError):
            continue
    sys.exit("[TRELLO] No encuentro trello_api_key / trello_token en el vault ni en TRELLO_API_KEY / TRELLO_TOKEN.")


def llamar(metodo: str, ruta: str, **params):
    clave, token = credenciales()
    q = urllib.parse.urlencode({**{k: v for k, v in params.items() if v not in (None, "")}, "key": clave, "token": token})
    url = f"{API}{ruta}?{q}" if metodo == "GET" else f"{API}{ruta}"
    datos = None if metodo == "GET" else q.encode()
    req = urllib.request.Request(url, data=datos, method=metodo, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            cuerpo = r.read().decode("utf-8")
            return json.loads(cuerpo) if cuerpo else {}
    except urllib.error.HTTPError as e:  # nunca mostrar la URL (lleva la clave)
        sys.exit(f"[TRELLO] Error {e.code} en {metodo} {ruta}: {e.read().decode('utf-8', 'ignore')[:200]}")
    except urllib.error.URLError as e:
        sys.exit(f"[TRELLO] Sin conexion con Trello: {e.reason}")


def tablero(ref: str) -> dict:
    if re.fullmatch(r"[0-9a-f]{24}|[A-Za-z0-9]{8}", ref):
        return llamar("GET", f"/boards/{ref}", fields="name,url")
    todos = llamar("GET", "/members/me/boards", fields="name,url,closed", filter="open")
    hallados = [b for b in todos if ref.lower() in b["name"].lower()]
    if not hallados:
        sys.exit(f"[TRELLO] No hay ningun tablero abierto que contenga '{ref}'. Usa: python trello.py tableros")
    if len(hallados) > 1:
        exacto = [b for b in hallados if b["name"].lower() == ref.lower()]
        if len(exacto) != 1:
            sys.exit("[TRELLO] Varios tableros encajan: " + " | ".join(f"{b['name']} ({b['id']})" for b in hallados))
        return exacto[0]
    return hallados[0]


def lista(tab: dict, nombre: str) -> dict:
    listas = llamar("GET", f"/boards/{tab['id']}/lists", fields="name", filter="open")
    hallada = [x for x in listas if x["name"].lower() == nombre.lower()] or [x for x in listas if nombre.lower() in x["name"].lower()]
    if not hallada:
        sys.exit(f"[TRELLO] '{tab['name']}' no tiene la lista '{nombre}'. Listas: {', '.join(x['name'] for x in listas)}")
    return hallada[0]


def salida(datos, como_json: bool, fmt):
    if como_json:
        print(json.dumps(datos, ensure_ascii=False, indent=1))
    else:
        for x in (datos if isinstance(datos, list) else [datos]):
            print(fmt(x))


def main() -> int:
    ap = argparse.ArgumentParser(description="Trello para Nova (claves del vault, nunca impresas)")
    ap.add_argument("orden", choices=["tableros", "listas", "tarjetas", "buscar", "crear-tablero", "crear-lista",
                                      "crear-tarjeta", "mover", "comentar", "archivar"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--lista", default="")
    ap.add_argument("--listas", default="")
    ap.add_argument("--titulo", default="")
    ap.add_argument("--desc", default="")
    ap.add_argument("--vence", default="")
    ap.add_argument("--a", dest="destino", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    J, o, x = a.json, a.orden, a.args

    def falta(n):
        if len(x) < n:
            sys.exit(f"[TRELLO] '{o}' necesita {n} argumento(s). Mira: python trello.py --help")

    if o == "tableros":
        salida(llamar("GET", "/members/me/boards", fields="name,url", filter="open"), J, lambda b: f"{b['name']}  ·  {b['id']}  ·  {b['url']}")
    elif o == "listas":
        falta(1); t = tablero(x[0])
        salida(llamar("GET", f"/boards/{t['id']}/lists", fields="name", filter="open"), J, lambda l: f"{l['name']}  ·  {l['id']}")
    elif o == "tarjetas":
        falta(1); t = tablero(x[0])
        ruta = f"/lists/{lista(t, a.lista)['id']}/cards" if a.lista else f"/boards/{t['id']}/cards"
        salida(llamar("GET", ruta, fields="name,idList,due,url,shortLink"), J, lambda c: f"{c['name']}  ·  {c['id']}  ·  vence {c.get('due') or '-'}")
    elif o == "buscar":
        falta(1)
        r = llamar("GET", "/search", query=x[0], modelTypes="cards,boards", cards_limit=20)
        salida([{"tipo": "tablero", **b} for b in r.get("boards", [])] + [{"tipo": "tarjeta", **c} for c in r.get("cards", [])], J,
               lambda c: f"[{c['tipo']}] {c['name']}  ·  {c['id']}")
    elif o == "crear-tablero":
        falta(1)
        b = llamar("POST", "/boards", name=x[0], defaultLists="false" if a.listas else "true")
        for nombre in [s.strip() for s in reversed(a.listas.split(",")) if s.strip()]:
            llamar("POST", "/lists", name=nombre, idBoard=b["id"], pos="top")
        salida(b, J, lambda b: f"Tablero creado: {b['name']}  ·  {b['id']}  ·  {b.get('url', '')}")
    elif o == "crear-lista":
        falta(2); t = tablero(x[0])
        salida(llamar("POST", "/lists", name=x[1], idBoard=t["id"], pos="bottom"), J, lambda l: f"Lista creada: {l['name']}  ·  {l['id']}")
    elif o == "crear-tarjeta":
        falta(1)
        if not (a.lista and a.titulo):
            sys.exit("[TRELLO] crear-tarjeta necesita --lista y --titulo")
        t = tablero(x[0])
        c = llamar("POST", "/cards", idList=lista(t, a.lista)["id"], name=a.titulo, desc=a.desc, due=a.vence or None, pos="bottom")
        salida(c, J, lambda c: f"Tarjeta creada: {c['name']}  ·  {c['id']}  ·  {c.get('url', '')}")
    elif o == "mover":
        falta(2)
        if not a.destino:
            sys.exit("[TRELLO] mover necesita --a <lista>")
        t = tablero(x[1])
        c = llamar("PUT", f"/cards/{x[0]}", idList=lista(t, a.destino)["id"], pos="top")
        salida(c, J, lambda c: f"Movida: {c['name']} -> {a.destino}")
    elif o == "comentar":
        falta(2)
        salida(llamar("POST", f"/cards/{x[0]}/actions/comments", text=x[1]), J, lambda r: "Comentario anadido")
    elif o == "archivar":
        falta(1)
        salida(llamar("PUT", f"/cards/{x[0]}", closed="true"), J, lambda c: f"Archivada: {c.get('name', x[0])} (se puede desarchivar en Trello)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
