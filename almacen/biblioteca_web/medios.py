"""
MEDIOS · fotos de CDN gratis y COMPROBADAS para las webs de Nova (nadie escribe URLs a mano: ni Nova ni Qwen).

Dos niveles:
  1. Picsum (Unsplash): 420 fotos de photos.json (draw.mjs) por colecciones (niebla, costa, interiores, gente, manos,
     texturas...). ID estable, tamano y formato por URL: https://picsum.photos/id/<id>/<w>/<h>.webp. Licencia Unsplash.
  2. Openverse / Wikimedia (assets.mjs, sin claves): temas concretos ("gym", "dental clinic"...). Licencias CC0, PD,
     CC BY, CC BY-SA, cada una con su credito. Se guardan en cache (medios_cache/) y se comprueba que cargan.

    python medios.py --categoria deporte [--buscar "gym training"] [--n 6] [--json]
    python medios.py --comprobar                     # revisa que las 420 de Picsum siguen vivas

Desde codigo: elegir(categoria, n, buscar="", semilla=0) -> lista de fotos {url(w,h), alt, credito, fuente, ...}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARTISAN = AQUI.parent / "skills" / "gemini-ui-artisan"
PHOTOS = ARTISAN / "library" / "photos.json"
ASSETS = ARTISAN / "scripts" / "assets.mjs"
CACHE = AQUI / "medios_cache"
UA = "NovaMedios/1.0 (webs de Nova, uso local)"

# categoria de la biblioteca -> (colecciones de Picsum que le van, busqueda en ingles para Openverse)
TEMAS = {
    "hosteleria": (["interior-and-table", "object-still", "hands-and-making", "city-day"], "cafe interior coffee"),
    "deporte": (["people", "city-day", "texture", "mountain"], "gym training weights"),
    "salud": (["fog-and-quiet", "interior-and-table", "plants-and-flowers", "water"], "medical clinic interior"),
    "belleza": (["plants-and-flowers", "interior-and-table", "texture", "fog-and-quiet"], "hair salon interior"),
    "alojamiento": (["coast", "mountain", "interior-and-table", "forest", "field-and-farm"], "hotel room interior"),
    "comercio": (["object-still", "city-day", "interior-and-table", "texture"], "shop interior"),
    "profesionales": (["architecture", "city-day", "object-still", "texture"], "office desk work"),
    "educacion": (["hands-and-making", "object-still", "city-day", "plants-and-flowers"], "classroom students"),
    "oficios": (["hands-and-making", "architecture", "texture", "object-still"], "carpenter tools workshop"),
    "eventos": (["people", "city-night", "plants-and-flowers", "interior-and-table"], "wedding celebration"),
    "ocio": (["city-night", "people", "sky-and-space", "architecture"], "concert stage lights"),
    "inmobiliaria": (["architecture", "interior-and-table", "city-day", "coast"], "modern house interior"),
    "motor": (["transport", "city-night", "desert-and-road", "texture"], "car mechanic garage"),
    "digital": (["texture", "sky-and-space", "city-night", "object-still"], "laptop workspace"),
    "asociaciones": (["people", "hands-and-making", "field-and-farm", "city-day"], "community volunteers"),
}


def _picsum() -> list[dict]:
    d = json.loads(PHOTOS.read_text(encoding="utf-8"))
    out = []
    for coleccion, s in d["sets"].items():
        for p in s["photos"]:
            out.append({**p, "coleccion": coleccion, "sectores": s.get("sectors", []), "fuente": "picsum"})
    return out


def url_picsum(foto: dict, w: int = 1600, h: int | None = None) -> str:
    h = h or round(w / float(foto.get("ratio") or 1.5))
    return f"https://picsum.photos/id/{foto['id']}/{w}/{h}.webp"


def credito(foto: dict) -> str:
    if foto["fuente"] == "picsum":
        return f"{foto.get('by', '')} / Unsplash"
    lic = (foto.get("license") or "").upper().replace("BY-SA", "BY-SA").replace("CC0", "CC0")
    return f"{foto.get('creator') or 'Autor desconocido'} / {foto.get('via') or 'Openverse'} ({'CC ' + lic if lic not in ('CC0', 'PD') else lic})"


def _vivo(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200 and r.headers.get("Content-Type", "").startswith("image")
    except Exception:
        return False


def buscar_tema(consulta: str, n: int = 6) -> list[dict]:
    """Openverse/Wikimedia via assets.mjs (sin claves), con cache. Solo licencias seguras para uso comercial."""
    CACHE.mkdir(exist_ok=True)
    clave = re.sub(r"[^a-z0-9]+", "_", consulta.lower()).strip("_")[:60]
    ruta = CACHE / f"{clave}.json"
    if ruta.exists():
        items = json.loads(ruta.read_text(encoding="utf-8"))
    else:
        try:
            r = subprocess.run(["node", str(ASSETS), consulta, "--source", "openverse,commons", "--license", "safe",
                                "--orientation", "landscape", "--min-width", "1200", "--limit", str(max(n, 8)), "--json"],
                               capture_output=True, text=True, encoding="utf-8", timeout=180)
            datos = json.loads(r.stdout or "{}")
        except (subprocess.SubprocessError, ValueError, OSError):
            return []
        items = [{**it, "fuente": "openverse"} for s in datos.get("sources", []) for it in s.get("items", []) if it.get("image")]
        ruta.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return items[:n]


def elegir(categoria: str, n: int = 6, buscar: str = "", semilla: int = 0, tono: str = "") -> list[dict]:
    """Fotos para una web: primero las del tema concreto (si se pide), luego Picsum de las colecciones de la categoria.
    Devuelve dicts uniformes: {url, url_movil, alt, credito, fuente, ratio, tono}."""
    colecciones, consulta_def = TEMAS.get(categoria, (["texture", "city-day", "object-still"], ""))
    out = []
    # Openverse/Wikimedia SOLO si se pide un tema a proposito (sus fotos son documentales: archivo, b/n, marcas de agua).
    # Por defecto, fotos curadas de Unsplash (Picsum). Nunca de rawpixel (marca de agua).
    temas = [it for it in (buscar_tema(buscar, n * 2) if buscar else [])
             if "rawpixel" not in json.dumps(it).lower() and int(it.get("imageWidth") or it.get("width") or 0) >= 1200]
    for it in temas:
        if len(out) >= max(1, n // 3):
            break
        w, h = it.get("imageWidth") or it.get("width") or 1600, it.get("imageHeight") or it.get("height") or 1000
        out.append({"url": it["image"], "url_movil": it.get("smaller") or it["image"], "alt": it.get("title", ""),
                    "credito": credito(it), "fuente": "openverse", "ratio": round(w / max(h, 1), 2), "tono": "", "pagina": it.get("page")})
    candidatas = [p for p in _picsum() if p["coleccion"] in colecciones and int(p.get("quality") or 0) >= 4 and (not tono or p.get("tone") == tono)]
    candidatas.sort(key=lambda p: (colecciones.index(p["coleccion"]),
                                   hashlib.md5(f"{semilla}-{p['id']}".encode()).hexdigest()))
    vistas = set()
    for p in candidatas:  # repartir entre colecciones
        if len(out) >= n:
            break
        if p["coleccion"] in vistas and len(vistas) < len(colecciones):
            continue
        vistas.add(p["coleccion"])
        out.append({"url": url_picsum(p, 1600), "url_movil": url_picsum(p, 800), "alt": p.get("alt", ""), "credito": credito(p),
                    "fuente": "picsum", "ratio": float(p.get("ratio") or 1.5), "tono": p.get("tone", ""), "pagina": p.get("page")})
    restantes = [p for p in candidatas if url_picsum(p, 1600) not in {o["url"] for o in out}]
    for p in restantes[: max(0, n - len(out))]:
        out.append({"url": url_picsum(p, 1600), "url_movil": url_picsum(p, 800), "alt": p.get("alt", ""), "credito": credito(p),
                    "fuente": "picsum", "ratio": float(p.get("ratio") or 1.5), "tono": p.get("tone", ""), "pagina": p.get("page")})
    return out[:n]


def linea_creditos(fotos: list[dict]) -> str:
    vistos = list(dict.fromkeys(f["credito"] for f in fotos if f.get("credito")))
    return ("Fotos: " + " · ".join(vistos)) if vistos else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Fotos de CDN gratis y comprobadas para webs de Nova")
    ap.add_argument("--categoria", default="")
    ap.add_argument("--buscar", default="", help="Tema concreto en ingles para Openverse/Wikimedia (gym, dental clinic...)")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--comprobar", action="store_true", help="Revisa que las fotos de Picsum siguen cargando")
    a = ap.parse_args()
    if a.comprobar:
        import concurrent.futures as cf
        fotos = _picsum()
        with cf.ThreadPoolExecutor(12) as ex:
            vivas = list(ex.map(lambda p: _vivo(url_picsum(p, 400, 300)), fotos))
        muertas = [str(p["id"]) for p, v in zip(fotos, vivas) if not v]
        print(f"[MEDIOS] {len(fotos) - len(muertas)}/{len(fotos)} fotos de Picsum cargan" + (f"; caidas: {', '.join(muertas[:20])}" if muertas else ""))
        return 0 if not muertas else 1
    fotos = elegir(a.categoria, a.n, a.buscar)
    vivas = [f for f in fotos if _vivo(f["url"])]
    if a.json:
        print(json.dumps(vivas, ensure_ascii=False, indent=1))
    else:
        for f in vivas:
            print(f"- {f['url']}\n    alt: {f['alt'][:80]} · {f['credito']}")
        print(linea_creditos(vivas))
    return 0 if vivas else 1


if __name__ == "__main__":
    sys.exit(main())
