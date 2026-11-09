import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
MEDIOS: esqueleto para verificar + vestido final con medios de libre uso.

  esqueleto(html, imagenes)  -> cada <img>/<video>/<iframe> queda como un MARCO del tamaño y color de la original,
                                sin descargar nada (el verificador compara estructura, no fotos)
  vestir(html, libres)       -> cada marco recibe su medio libre (Picsum, vídeo libre, OpenStreetMap, DiceBear...)

Los marcos son responsive: proporción (aspect-[w/h]) + object-cover, así que cualquier foto o link encaja solo.
"""
import json
import math
import re
from pathlib import Path

GIF_VACIO = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

LIBRES_POR_DEFECTO = {
    "_nota": "Medios de libre uso para vestir el clon. Puedes cambiar o añadir enlaces. {seed} {w} {h} se rellenan solos.",
    "foto": "https://picsum.photos/seed/{seed}/{w}/{h}",
    "logo": "https://placehold.co/{w}x{h}/EEEEEE/999999?text=LOGO",
    "avatar": "https://api.dicebear.com/9.x/notionists/svg?seed={seed}",
    "icono": "https://placehold.co/{w}x{h}/EEEEEE/999999?text=%E2%97%8F",
    "videos": [
        "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4",
        "https://test-videos.co.uk/vids/sintel/mp4/h264/720/Sintel_720_10s_1MB.mp4",
        "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        "https://archive.org/download/ElephantsDream/ed_1024_512kb.mp4"
    ],
    "youtube": "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ",
    "mapa": "https://www.openstreetmap.org/export/embed.html?bbox=-3.7100%2C40.4100%2C-3.6900%2C40.4250&layer=mapnik",
    "creditos": "Fotos: Lorem Picsum (Unsplash) · Vídeos: Blender Foundation (CC BY) y MDN (CC0) · Mapa: © OpenStreetMap · Avatares: DiceBear"
}


def cargar_libres(base):
    ruta = Path(base) / "medios_libres.json"
    if not ruta.exists():
        ruta.write_text(json.dumps(LIBRES_POR_DEFECTO, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return {**LIBRES_POR_DEFECTO, **json.loads(ruta.read_text(encoding="utf-8"))}
    except Exception:
        return LIBRES_POR_DEFECTO


def proporcion(w, h):
    w, h = max(int(w or 1), 1), max(int(h or 1), 1)
    g = math.gcd(w, h)
    a, b = w // g, h // g
    if a > 40 or b > 40:                       # proporciones raras: redondear a algo legible
        a, b = round(w / h * 20), 20
        g = math.gcd(a, b)
        a, b = a // g, b // g
    return f"{a}/{b}"


def tipo_imagen(im):
    if im.get("tipo") == "video":
        return "video"
    if im.get("redonda"):
        return "avatar"
    if im["w"] <= 160 and im["h"] <= 90:
        return "logo" if im["w"] > im["h"] * 1.6 else "icono"
    return "foto"


def _attr(tag, nombre):
    m = re.search(rf'\b{nombre}\s*=\s*"([^"]*)"', tag) or re.search(rf"\b{nombre}\s*=\s*'([^']*)'", tag)
    return m.group(1) if m else None


def _set(tag, nombre, valor):
    """Pone (o cambia) un atributo en la etiqueta de apertura."""
    patron = rf'\b{nombre}\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)'
    if re.search(patron, tag):
        return re.sub(patron, lambda m: f'{nombre}="{valor}"', tag, count=1)
    if re.search(rf"\s{nombre}(?=[\s/>])", tag):            # atributo suelto (autoplay, muted...)
        return tag
    fin = "/>" if tag.rstrip().endswith("/>") else ">"
    return tag.rstrip()[: -len(fin)].rstrip() + f' {nombre}="{valor}"' + (" />" if fin == "/>" else ">")


def _quitar(tag, nombre):
    return re.sub(rf'\s\b{nombre}\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', "", tag)


def esqueleto(html, imagenes):
    """Convierte imágenes, vídeos e iframes de una sección en marcos vacíos del color y tamaño de la original.
    `imagenes` = lista de la ficha (en orden): w, h, color, tipo, redonda."""
    cola = list(imagenes or [])

    def img(m):
        tag = m.group(0)
        im = cola.pop(0) if cola else {"w": 800, "h": 600, "color": "DDDDDD"}
        tipo = _attr(tag, "data-medio") or tipo_imagen(im)
        clases = _attr(tag, "class") or ""
        if not re.search(r"\bobject-(cover|contain|fill|none|scale-down)\b", clases):
            clases += " object-contain" if tipo in ("logo", "icono") else " object-cover"
        if not re.search(r"(^|\s)(h-|aspect-|size-)", clases):
            clases += f" aspect-[{proporcion(im['w'], im['h'])}]"
        if not re.search(r"(^|\s)(w-|size-|max-w-)", clases):
            clases += " w-full"
        tag = _set(tag, "class", clases.strip())
        tag = _set(tag, "data-medio", tipo)
        tag = _set(tag, "data-w", str(im["w"]))
        tag = _set(tag, "data-h", str(im["h"]))
        tag = _quitar(tag, "srcset")
        tag = _set(tag, "src", GIF_VACIO)
        estilo = (_attr(tag, "style") or "").rstrip("; ")
        tag = _set(tag, "style", (estilo + "; " if estilo else "") + f"background-color:#{im.get('color', 'DDDDDD')}")
        return tag

    html = re.sub(r"<img\b[^>]*>", img, html, flags=re.I)

    def video(m):
        tag = m.group(1)
        tag = _quitar(_quitar(tag, "src"), "poster")
        for k, v in (("data-medio", "video"), ("autoplay", "autoplay"), ("muted", "muted"), ("loop", "loop"), ("playsinline", "playsinline")):
            if k == "data-medio" or not re.search(rf"\b{k}\b", tag):
                tag = _set(tag, k, v)
        estilo = (_attr(tag, "style") or "").rstrip("; ")
        if "background" not in estilo:
            tag = _set(tag, "style", (estilo + "; " if estilo else "") + "background-color:#333333")
        return tag + "</video>"
    html = re.sub(r"(<video\b[^>]*>).*?</video>", video, html, flags=re.I | re.S)

    def iframe(m):
        tag = m.group(1)
        src = (_attr(tag, "src") or "").lower()
        tipo = "mapa" if re.search(r"map", src) else "youtube"
        tag = _set(_quitar(tag, "src"), "data-medio", tipo)
        estilo = (_attr(tag, "style") or "").rstrip("; ")
        tag = _set(tag, "style", (estilo + "; " if estilo else "") + "background-color:#CCCCCC")
        return tag + "</iframe>"
    html = re.sub(r"(<iframe\b[^>]*>).*?</iframe>", iframe, html, flags=re.I | re.S)
    return html


def vestir(html, libres, semilla="clon"):
    """Cambia cada marco vacío por su medio de libre uso, del mismo tamaño."""
    cont = {"n": 0}

    def sig():
        cont["n"] += 1
        return f"{semilla}{cont['n']}"

    def img(m):
        tag = m.group(0)
        tipo = _attr(tag, "data-medio") or "foto"
        w, h = int(_attr(tag, "data-w") or 800), int(_attr(tag, "data-h") or 600)
        escala = 2 if max(w, h) <= 900 else 1                         # el doble de nítida en pantallas retina
        url = libres.get(tipo, libres["foto"]).format(seed=sig(), w=min(w * escala, 2000), h=min(h * escala, 2000))
        tag = _set(tag, "src", url)
        return tag if "loading=" in tag else _set(tag, "loading", "lazy")

    html = re.sub(r'<img\b[^>]*data-medio="[^"]*"[^>]*>', img, html, flags=re.I)
    vids = libres.get("videos") or []

    def video(m):
        if not vids:
            return m.group(0)
        sig()
        return _set(m.group(0), "src", vids[cont["n"] % len(vids)])
    html = re.sub(r'<video\b[^>]*data-medio="video"[^>]*>', video, html, flags=re.I)

    def iframe(m):
        tag = m.group(0)
        tipo = _attr(tag, "data-medio")
        tag = _set(tag, "src", libres.get(tipo, libres["youtube"]))
        if tipo == "youtube" and "allow=" not in tag:
            tag = _set(tag, "allow", "autoplay; encrypted-media; picture-in-picture")
        return tag
    html = re.sub(r'<iframe\b[^>]*data-medio="(mapa|youtube)"[^>]*>', iframe, html, flags=re.I)
    if libres.get("creditos") and "</body>" in html:
        html = html.replace("</body>", f"<!-- Medios de libre uso: {libres['creditos']} -->\n</body>", 1)
    return html
