"""
IDENTIDAD · fotos y colores segun DE QUE VA el negocio

Antes: fotos al azar de colecciones genericas (un cafe con frutos del bosque, Chicago y una maquina de escribir) y una
paleta sorteada entre 56 por "sector" (verde oliva de una web de safari para un cafe).

Ahora, en automatico (criterio de Nova; el usuario no tiene que saber de diseno):
  1. TIPO de negocio: categoria + receta de montar.py, afinado con las palabras de identidad.json ("detectar") sobre
     tipo/nombre/descripcion del negocio (p. ej. hosteleria -> cafeteria | panaderia).
  2. FOTOS, dos salidas: (a) las de la biblioteca cuya descripcion CASA con el negocio; (b) si no llegan, INTERNET
     (Openverse/Wikimedia, licencias libres, con credito) con las busquedas del tipo. Nunca fotos que no casen: mejor
     menos fotos que una ciudad en un cafe.
  3. PALETA por algoritmo: solo las permitidas para ese tipo, sin repetir las 3 ultimas de la MISMA categoria
     (memoria_disenos.json); "oscuro/elegante/noche" o "claro/luminoso/fresco" en la ficha inclinan la eleccion.
  4. Si el USUARIO da caracteristicas, mandan las suyas: datos["estilo"] = {"paleta": "<id>"} o
     {"colores": ["#hex", ...]} (o negocio.colores). Sus colores se respetan y el resto lo completa la paleta base.

    python identidad.py --datos datos.json --categoria hosteleria [--receta cafeteria] [--sin-red]   (prueba)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
IDENTIDAD = AQUI / "identidad.json"
LIBRERIA = AQUI.parent / "skills" / "gemini-ui-artisan" / "library"
RE_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
# Openverse/Wikimedia mezclan fotos actuales con material de ARCHIVO: fuera grabados, cuadros, museos y fotos viejas
RE_ARCHIVO = re.compile(r"(?i)\b(wellcome|engraving|etching|lithograph|woodcut|painting|drawing|illustration|poster|"
                        r"museum|archive|archival|historic|vintage photo|stamp|postcard|map|diagram|logo|"
                        r"caricature|cartoon|satir\w*|grotesque|portrait of)\b|"
                        r"\bc\.?\s?1[89]\d\d\b|\b1[89]\d\d\b|\b19[0-9]\d\b|\bV00\d+")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _h(*partes) -> str:
    return hashlib.md5("-".join(str(p) for p in partes).encode()).hexdigest()


def cargar() -> dict:
    """09/11: los datos viven en categorias/<cat>/<tipo>.json y general/paletas.json (carga.py)."""
    import carga
    return carga.identidad()


def texto_negocio(datos: dict) -> str:
    n = datos.get("negocio") or {}
    est = datos.get("estilo") or {}
    return _norm(" ".join(str(x) for x in (n.get("tipo"), n.get("nombre"), n.get("descripcion"), n.get("notas"),
                                          n.get("eslogan"), est.get("tono"), est.get("notas")) if x))


# ---------------------------------------------------------------------------------------------- 1. tipo de negocio
def perfil(categoria: str, receta: str, datos: dict) -> dict:
    ident = cargar()
    cat_todo = ident.get(categoria) or {}
    cat = {k: v for k, v in cat_todo.items() if not k.startswith("_")}
    t = texto_negocio(datos)
    tipo = next((k for k, v in cat.items() if v.get("detectar") and re.search(v["detectar"], t)), "")
    if not tipo:
        tipo = receta if receta in cat else next(iter(cat), "")
    p = dict(cat.get(tipo) or {})
    buscar = list(p.get("buscar") or [])
    for rx, qs in (p.get("buscar_si") or {}).items():  # afinar la busqueda: clinica DENTAL, salon de UNAS...
        if re.search(rx, t):
            buscar = list(qs) + [q for q in buscar if q not in qs]
    return {"categoria": categoria, "tipo": tipo, "fotos": p.get("fotos", ""), "no_fotos": p.get("no_fotos", ""),
            "buscar": buscar, "paletas": p.get("paletas") or [], "texto": t, "tono": texto_tono(datos),
            "fotografica": bool(cat_todo.get("_fotografica"))}


def texto_tono(datos: dict) -> str:
    """Solo lo que DESCRIBE el estilo (no el nombre: 'Origen Negro' no es pedir una web oscura)."""
    n = datos.get("negocio") or {}
    est = datos.get("estilo") or {}
    return _norm(" ".join(str(x) for x in (n.get("notas"), est.get("tono"), est.get("notas"), est.get("estilo")) if x))


# ---------------------------------------------------------------------------------------------- 3-4. paleta
def paletas_todas() -> dict[str, dict]:
    todas = {}
    try:
        d = json.loads((LIBRERIA / "palettes.json").read_text(encoding="utf-8"))
        for p in (d.get("palettes", d) if isinstance(d, dict) else d):
            todas[p["id"]] = p
    except (OSError, ValueError, KeyError):
        pass
    for p in cargar().get("paletas_extra") or []:
        todas[p["id"]] = p
    return todas


def _oscura(p: dict) -> bool:
    h = str(p.get("bg", "#ffffff")).lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) < 110


def colores_usuario(datos: dict) -> list[str]:
    n, est = datos.get("negocio") or {}, datos.get("estilo") or {}
    crudo = est.get("colores") or n.get("colores") or []
    if isinstance(crudo, str):
        crudo = RE_HEX.findall(crudo)
    return [c for c in crudo if isinstance(c, str) and RE_HEX.fullmatch(c.strip())]


def elegir_paleta(pf: dict, datos: dict, memoria: list[dict], semilla: int) -> tuple[dict | None, str]:
    """(paleta, motivo). None = no hay identidad para esta categoria: se queda la sorteada por draw.mjs."""
    todas = paletas_todas()
    est = datos.get("estilo") or {}
    if est.get("paleta") in todas:  # el usuario la nombra
        return dict(todas[est["paleta"]]), "pedida por el usuario"
    permitidas = [todas[i] for i in pf.get("paletas", []) if i in todas]
    if not permitidas:
        return None, "sin identidad para esta categoria"
    t = pf.get("tono", "")
    quiere_oscura = bool(re.search(r"oscur|noche|nocturn|elegante|lujo|premium|negro", t))
    quiere_clara = bool(re.search(r"clar|luminos|fresc|limpi|blanc|natural|calid", t))
    recientes = [m.get("paleta") for m in memoria if m.get("categoria") == pf.get("categoria")][-3:]
    libres = [p for p in permitidas if p["id"] not in recientes] or permitidas

    def puntos(p):
        o = _oscura(p)
        return (2 if (quiere_oscura and o) or (quiere_clara and not o) else 0) - (1 if p["id"] in recientes else 0)
    elegida = dict(sorted(libres, key=lambda p: (-puntos(p), _h(semilla, p["id"])))[0])
    motivo = f"tipo {pf.get('tipo')}; evitadas por memoria de {pf.get('categoria')}: {', '.join(x for x in recientes if x) or 'ninguna'}"
    cols = colores_usuario(datos)
    if cols:  # colores del cliente: el 1o es el acento (botones, enlaces); si da 2+, el 2o es el texto
        elegida["accent"] = cols[0]
        elegida["fields"] = [{"bg": cols[0], "ink": elegida.get("accentInk", "#ffffff")}]
        if len(cols) > 1:
            elegida["ink"] = cols[1]
        elegida["id"] = elegida["id"] + "+cliente"
        motivo = "colores del cliente sobre " + motivo
    return elegida, motivo


# ---------------------------------------------------------------------------------------------- 2. fotos
OPENVERSE = "https://api.openverse.org/v1/images/"
UA = "NovaWebs/1.0 (webs de Nova, uso local; open source)"


def buscar_fotos_red(consulta: str, n: int = 12) -> list[dict]:
    """Internet, 1a opcion: Openverse SOLO FOTOGRAFIAS (category=photograph: fuera dibujos, grabados y escaneos),
    licencias que permiten uso comercial y modificar (CC0, PD, BY, BY-SA), horizontales y grandes. Sin claves.
    Con cache en medios_cache/ov_<consulta>.json. Devuelve el formato de medios.buscar_tema."""
    import urllib.parse
    import urllib.request
    cache = AQUI / "medios_cache"
    cache.mkdir(exist_ok=True)
    ruta = cache / ("ov_" + re.sub(r"[^a-z0-9]+", "_", consulta.lower()).strip("_")[:60] + ".json")
    if ruta.exists():
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))[:n]
        except ValueError:
            pass
    # 09/11: la API da 504 a ratos si se le piden muchos filtros: se pide solo "fotografia" y el resto se filtra aqui
    q = urllib.parse.urlencode({"q": consulta, "category": "photograph", "page_size": 20})  # sin cuenta: max 20 (40 = 401)
    res = None
    for intento in range(3):
        try:
            req = urllib.request.Request(f"{OPENVERSE}?{q}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.loads(r.read()).get("results") or []
            break
        except Exception:
            import time
            time.sleep(1.5 * (intento + 1))
    if res is None:
        return []  # sin respuesta: no se guarda en cache (la proxima vez se reintenta)
    LIBRES = {"cc0", "pdm", "by", "by-sa"}  # uso comercial y se puede recortar/modificar (fuera NC y ND)
    items = [{"image": x.get("url"), "smaller": x.get("thumbnail") or x.get("url"), "title": x.get("title") or consulta,
              "creator": x.get("creator") or "", "license": (x.get("license") or "").upper(), "via": x.get("source") or "Openverse",
              "imageWidth": x.get("width") or 0, "imageHeight": x.get("height") or 0, "page": x.get("foreign_landing_url"),
              "fuente": "openverse"}
             for x in res if x.get("url") and str(x.get("license", "")).lower() in LIBRES
             and int(x.get("width") or 0) >= 1200 and int(x.get("width") or 0) > int(x.get("height") or 0)]
    try:
        ruta.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    return items[:n]


def fotos(pf: dict, n: int = 7, semilla: int = 0, red: bool = True) -> tuple[list[dict], dict]:
    """(fotos en formato de bloques {src, src_movil, alt, credito}, cuenta {biblioteca, internet})."""
    import medios
    # las palabras cuentan desde el INICIO de palabra: "dish" no casa con "reddish" ni "hair" con "chair"
    rx = rf"\b(?:{pf['fotos']})" if pf.get("fotos") else ""
    no = rf"\b(?:{pf['no_fotos']})" if pf.get("no_fotos") else ""
    out, cuenta = [], {"biblioteca": 0, "internet": 0}
    if rx:
        casan = [p for p in medios._picsum()
                 if re.search(rx, p.get("alt", ""), re.I) and not (no and re.search(no, p.get("alt", ""), re.I))
                 and int(p.get("quality") or 0) >= 3]
        for p in sorted(casan, key=lambda p: _h(semilla, p["id"]))[:n]:
            out.append({"src": medios.url_picsum(p, 1600), "src_movil": medios.url_picsum(p, 800), "alt": p.get("alt", ""),
                        "credito": medios.credito(p)})
            cuenta["biblioteca"] += 1
    if red and len(out) < n:
        busquedas = pf.get("buscar") or []
        vistas = {f["src"] for f in out}
        for q in busquedas[:3]:
            if len(out) >= n:
                break
            # 1o Openverse solo fotografias; si no responde o no hay, el buscador de siempre (Openverse + Wikimedia)
            for it in (buscar_fotos_red(q, n * 2) or medios.buscar_tema(q, n * 2)):
                if len(out) >= n:
                    break
                texto = json.dumps(it, ensure_ascii=False).lower()
                ancho = int(it.get("imageWidth") or it.get("width") or 0)
                if (it.get("image") in vistas or "rawpixel" in texto or ancho < 1200
                        or RE_ARCHIVO.search(str(it.get("title", "")))
                        or (no and re.search(no, str(it.get("title", "")), re.I))):
                    continue
                vistas.add(it["image"])
                out.append({"src": it["image"], "src_movil": it.get("smaller") or it["image"],
                            "alt": str(it.get("title") or q)[:140], "credito": medios.credito(it)})
                cuenta["internet"] += 1
    return out, cuenta


def main() -> int:
    ap = argparse.ArgumentParser(description="Prueba de identidad visual (tipo, paleta, fotos)")
    ap.add_argument("--datos", required=True)
    ap.add_argument("--categoria", default="hosteleria")
    ap.add_argument("--receta", default="")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--sin-red", action="store_true")
    a = ap.parse_args()
    datos = json.loads(Path(a.datos).read_text(encoding="utf-8"))
    pf = perfil(a.categoria, a.receta, datos)
    pal, motivo = elegir_paleta(pf, datos, [], a.semilla)
    fs, cuenta = fotos(pf, 7, a.semilla, red=not a.sin_red)
    print(f"tipo: {pf['tipo']} | paleta: {pal and pal['id']} ({motivo})")
    print(f"fotos: {cuenta}")
    for f in fs:
        print(f"  - {f['alt'][:80]}  [{f['credito'][:50]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
