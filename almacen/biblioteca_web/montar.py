"""
MONTAR · biblioteca web de Nova: datos reales + receta + direccion de arte -> index.html (sin IA, 0 tokens)

    python montar.py --datos datos.json --categoria hosteleria [--receta cafeteria] [--direccion direction.json]
                     [--out index.html] [--semilla N]

- La MAQUETACION viene de los bloques (bloques.py): calidad fija, accesibles y responsive.
- Los DATOS vienen de datos.json (los da Alexander o el cliente). Lo que falta sale como [PENDIENTE]; las secciones
  opcionales sin datos (resenas, eventos, faq) no se pintan. Nada se inventa.
- La DIRECCION (draw.mjs) se convierte en variables: paleta por roles, tipografias, escala, motivo grafico.
- Devuelve avisos: contraste insuficiente de la paleta, datos pendientes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import bloques as B  # noqa: E402


# ---------------------------------------------------------------------------------------------- color
def _rgb(hexa: str) -> tuple[float, float, float]:
    h = hexa.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def contraste(a: str, b: str) -> float:
    def lum(c):
        r, g, bl = (x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in _rgb(c))
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# ---------------------------------------------------------------------------------------------- direccion -> variables
def variables(direccion: dict) -> tuple[str, list[str], dict, list[str]]:
    """(css :root, enlaces de fuentes, estilo {motivo, prefiere_partido}, avisos)."""
    avisos = []
    pal = direccion.get("palette") or {}
    ty = direccion.get("type") or {}
    v = {}
    for clave, var in (("bg", "--bg"), ("surface", "--surface"), ("ink", "--ink"), ("muted", "--muted"),
                       ("accent", "--accent"), ("accentInk", "--accent-ink")):
        if re.fullmatch(r"#[0-9a-fA-F]{3,8}", str(pal.get(clave, ""))):
            v[var] = pal[clave]
    campo = (pal.get("fields") or [{}])[0]
    if campo.get("bg"):
        v["--field"] = campo["bg"]
        v["--field-ink"] = campo.get("ink") or v.get("--ink", "#222")
    # contraste minimo (color-palette-builder / WCAG AA): si la paleta sorteada no llega, se corrige y se avisa
    bg, ink = v.get("--bg", "#f4f1ec"), v.get("--ink", "#22201d")
    if contraste(bg, ink) < 7:
        avisos.append(f"contraste tinta/fondo {contraste(bg, ink):.1f}:1 (objetivo 7:1)")
    if "--accent" in v and contraste(v["--accent"], v.get("--accent-ink", "#fff")) < 4.5:
        mejor = "#ffffff" if contraste(v["--accent"], "#ffffff") >= contraste(v["--accent"], "#111111") else "#111111"
        avisos.append(f"texto del boton corregido a {mejor} (contraste {contraste(v['--accent'], v.get('--accent-ink', '#fff')):.1f}:1)")
        v["--accent-ink"] = mejor
    if "--muted" in v and contraste(v["--muted"], bg) < 4.5:
        avisos.append(f"texto apagado oscurecido: contraste {contraste(v['--muted'], bg):.1f}:1 era bajo")
        v["--muted"] = f"color-mix(in srgb, {v['--muted']} 55%, {ink})"
    disp, texto = ty.get("display") or {}, ty.get("text") or {}
    if disp.get("family"):
        v["--font-display"] = f"'{disp['family']}', Georgia, serif" if "serif" in str(ty.get("class", "")) else f"'{disp['family']}', system-ui, sans-serif"
    if texto.get("family"):
        v["--font-text"] = f"'{texto['family']}', system-ui, sans-serif"
    ajustes = str(disp.get("settings", ""))
    m = re.search(r"tracking\s+(-?[\d.]+em)", ajustes)
    if m:
        v["--display-tracking"] = m.group(1)
    m = re.search(r"leading\s+([\d.]+)", ajustes)
    if m:
        v["--display-leading"] = m.group(1)
    if disp.get("weights"):
        v["--display-weight"] = str(disp["weights"][0])
    for paso, valor in (ty.get("scale") or {}).items():
        if paso in ("step-small", "step-body", "step-lead", "step-head"):
            v[f"--{paso}"] = valor
    css = ":root {\n" + "\n".join(f"  {k}: {val};" for k, val in v.items()) + "\n}"
    nombre = str((direccion.get("direction") or {}).get("id", "")) + str((direccion.get("direction") or {}).get("name", ""))
    motivo = ("rayas" if re.search(r"stripe|band|awning", nombre, re.I) else "arcos" if re.search(r"arch|stage|room", nombre, re.I)
              else "grano" if re.search(r"object|motif|one", nombre, re.I) else "anillos")
    prefiere_partido = "split" in str((direccion.get("hero") or {}).get("archetype", "")) or "split" in nombre
    return css, list(ty.get("links") or []), {"motivo": motivo, "prefiere_partido": prefiere_partido}, avisos


# ---------------------------------------------------------------------------------------------- receta y variantes
def cargar_recetas() -> dict:
    import carga  # 09/11: categorias/<cat>/_categoria.json
    return carga.recetas()


def recetas_de(cat: dict) -> dict:
    return {k: v for k, v in cat.items() if isinstance(v, dict) and "bloques" in v}


def _norm(t: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


def detectar_categoria(texto: str) -> tuple[str, str]:
    """(categoria, receta) a partir del tipo de negocio o del pedido ("gimnasio en Madrid" -> deporte/gimnasio)."""
    t = _norm(texto)
    mejor = ("", "", (10**6, 0))  # gana la palabra que aparece ANTES en la frase; a igualdad, la mas larga
    for cat, info in cargar_recetas().items():
        if cat.startswith("_"):
            continue
        for nombre, r in recetas_de(info).items():
            for palabra in (x.strip() for x in _norm(r["descripcion"]).split(",")):
                m = re.search(r"\b" + re.escape(palabra), t) if palabra else None
                if m and (m.start(), -len(palabra)) < mejor[2]:
                    mejor = (cat, nombre, (m.start(), -len(palabra)))
    return mejor[0], mejor[1]


def elegir_receta(categoria: str, receta: str, datos: dict) -> dict:
    """Receta (bloques, schema) + rotulos y sector de la categoria."""
    todas = cargar_recetas()
    if categoria not in todas:
        categoria, receta = detectar_categoria(f"{(datos.get('negocio') or {}).get('tipo', '')} {categoria}")
        if not categoria:
            raise SystemExit(f"Categoria desconocida. Hay: {', '.join(k for k in todas if not k.startswith('_'))}")
    info = todas[categoria]
    recetas = recetas_de(info)
    nombre = receta if receta in recetas else ""
    if not nombre:
        tipo = _norm((datos.get("negocio") or {}).get("tipo", ""))
        nombre = next((n for n, r in recetas.items()
                       if n in tipo or any(p.strip() and p.strip() in tipo for p in _norm(r["descripcion"]).split(","))),
                      next(iter(recetas)))
    return {**recetas[nombre], "receta": nombre, "rotulos": info.get("rotulos") or {}, "sector": info.get("sector", "other"),
            "categoria": categoria}


def elegir_variante(nombre: str, datos: dict, estilo: dict, semilla: int) -> str:
    info = B.BLOQUES[nombre]["variantes"]
    hay_fotos = bool(datos.get("fotos"))
    validas = [k for k, v in info.items() if (hay_fotos or not v.get("fotos")) and (datos.get("video") or not v.get("video"))]
    if nombre == "hero":
        if datos.get("video") and "video" in validas:
            return "video"
        if hay_fotos and "foto" in validas:
            return "foto"
        return "partido" if estilo.get("prefiere_partido") else "tipografico"
    return validas[semilla % len(validas)]


# ---------------------------------------------------------------------------------------------- JSON-LD (solo datos reales)
def json_ld(datos: dict) -> str:
    n = datos.get("negocio") or {}
    if not n.get("nombre"):
        return ""
    tipo = datos.get("_schema") or "LocalBusiness"
    ld = {"@context": "https://schema.org", "@type": tipo, "name": n["nombre"]}
    if n.get("direccion"):
        ld["address"] = {"@type": "PostalAddress", "streetAddress": n["direccion"],
                         **({"addressLocality": n["ciudad"]} if n.get("ciudad") else {})}
    if n.get("telefono"):
        ld["telephone"] = n["telefono"]
    dias_en = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    horas = [{"@type": "OpeningHoursSpecification", "dayOfWeek": [dias_en[d] for d in f.get("dias_semana") or []],
              "opens": f["abre"], "closes": f["cierra"]} for f in datos.get("horario") or [] if f.get("abre")]
    if horas:
        ld["openingHoursSpecification"] = horas
    return '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>"


def pendientes(datos: dict) -> list[str]:
    n = datos.get("negocio") or {}
    falta = [k for k in ("nombre", "direccion", "ciudad") if not n.get(k)]
    if not datos.get("horario"):
        falta.append("horario")
    if not (datos.get("reservas") or {}).get("valor") and not n.get("telefono"):
        falta.append("forma de reservar o telefono")
    if not (datos.get("legal") or {}).get("titular"):
        falta.append("titular y NIF (aviso legal)")
    return falta



# ---------------------------------------------------------------------------------------------- esqueletos + memoria
MEMORIA = AQUI / "memoria_disenos.json"
DATOS_RADAR = AQUI.parent.parent / "herramientas" / "datos" / "referencias_web"


def cargar_esqueletos() -> dict:
    import carga  # 09/11: general/estilos/<estilo>.json
    return {k: v for k, v in carga.esqueletos().items() if not k.startswith("_")}


def leer_memoria() -> list[dict]:
    try:
        return json.loads(MEMORIA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def apuntar_memoria(fila: dict) -> None:
    mem = (leer_memoria() + [fila])[-30:]
    try:
        MEMORIA.write_text(json.dumps(mem, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def preferencia_radar(sector: str) -> str:
    """Palabras que favorecen un esqueleto segun lo que hacen las webs reales del sector (radar_web.py)."""
    try:
        r = json.loads((DATOS_RADAR / sector / "resumen.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    pal = []
    if (r.get("fotos_porcentaje") or 0) >= 35:
        pal += ["photo", "image", "full"]
    heroes = " ".join(h for h, _ in r.get("hero") or [])
    if "tipografico" in heroes:
        pal += ["type", "editorial"]
    if "sangre" in heroes:
        pal += ["photo", "cinematic"]
    secs = " ".join(sname for sname, _ in r.get("secciones_mas_usadas") or [])
    if "tarjetas" in secs:
        pal += ["card", "grid"]
    if "precios" in secs:
        pal += ["precios", "price"]
    if (r.get("aire_seccion_px") or 0) >= 140:
        pal += ["air", "space", "minimal"]
    return " ".join(pal)


SIN_FOTOS = ("editorial", "minimal")  # esqueletos de portada tipografica: no ensenan ninguna foto

# 09/11: los estilos por categoria (esqueletos.json con "rasgos") no llevan CSS escrito a mano: se genera de sus rasgos
ESCALAS = {  # (titular de portada, titulo de seccion)
    "pequena": ("clamp(1.6rem, 1rem + 2vw, 2.6rem)", "clamp(1.2rem, 1rem + .8vw, 1.6rem)"),
    "media": ("clamp(2.2rem, 1.2rem + 3.5vw, 4rem)", "clamp(1.5rem, 1.1rem + 1.6vw, 2.4rem)"),
    "grande": ("clamp(2.8rem, 1.4rem + 5vw, 5.6rem)", "clamp(1.8rem, 1.2rem + 2.4vw, 3.2rem)"),
    "enorme": ("clamp(3.4rem, 1.2rem + 8vw, 8.5rem)", "clamp(2.2rem, 1.2rem + 3.6vw, 4.2rem)"),
}


def css_rasgos(nombre: str, r: dict) -> str:
    p = f".pag--{nombre}"
    disp, head = ESCALAS.get(r.get("escala", "media"), ESCALAS["media"])
    mayus = "uppercase" if r.get("mayus") else "none"
    trk = r.get("tracking", "-0.01em")
    css = [f"{p} {{ --radius: {int(r.get('radius', 4))}px; }}",
           f"{p} .t-display {{ font-size: {disp}; text-transform: {mayus}; letter-spacing: {trk}; line-height: {'1.0' if r.get('escala') == 'enorme' else '1.08'}; }}",
           f"{p} .t-head {{ font-size: {head}; text-transform: {mayus}; letter-spacing: {trk}; line-height: 1.12; }}"]
    if r.get("mayus"):
        css.append(f"{p} .boton, {p} .cab__nav a {{ text-transform: uppercase; letter-spacing: .08em; font-size: .82rem; }}")
    if r.get("boton") == "pastilla":
        css.append(f"{p} .boton {{ border-radius: 999px; padding-inline: 1.8em; }}")
    return "\n".join(css)


def elegir_esqueleto(pedido: str, direccion: dict, preferencia: str, semilla: int, categoria: str = "",
                     excluir: tuple = (), tipo: str = "") -> tuple[str, str]:
    """(nombre, motivo). 09/11: no repite el esqueleto de las 3 ultimas webs de la MISMA categoria (antes: de las 3
    ultimas de cualquiera) ni el de la web inmediatamente anterior; puntua por la direccion sorteada y el radar."""
    esq = cargar_esqueletos()
    if pedido in esq:
        return pedido, "pedido"
    mem = leer_memoria()
    recientes = [m.get("esqueleto") for m in mem if m.get("categoria") == categoria][-3:] + [m.get("esqueleto") for m in mem[-1:]]
    # 09/11: esqueletos de un tipo concreto ("tipos": galeria/tostador solo para cafeteria, panaderia, tienda, bar)
    posibles = [k for k in esq if k not in excluir and (not esq[k].get("tipos") or tipo in esq[k]["tipos"])]
    posibles = posibles or [k for k in esq if not esq[k].get("tipos")]
    # los hechos para el tipo solo evitan la web ANTERIOR de la categoria (alternan entre ellos y rotan sus 3 paletas)
    anterior = [m.get("esqueleto") for m in mem if m.get("categoria") == categoria][-1:]
    libres = [k for k in posibles
              if (k not in anterior if (tipo and tipo in (esq[k].get("tipos") or [])) else k not in recientes)] or posibles
    # si hay estilos hechos para este tipo de negocio (referencias de Luaz), solo se elige entre ellos
    propios = [k for k in libres if tipo and tipo in (esq[k].get("tipos") or [])]
    libres = propios or libres
    d = direccion.get("direction") or {}
    texto_dir = " ".join(str(x) for x in (d.get("id"), d.get("name"), d.get("idea"), d.get("composition"),
                                          (direccion.get("hero") or {}).get("archetype"), (direccion.get("hero") or {}).get("name"))).lower()
    pref = preferencia.lower()

    def puntos(k):
        pistas = esq[k].get("pistas") or []
        hecho_para = 3 if tipo and tipo in (esq[k].get("tipos") or []) else 0  # los estilos de su tipo van primero
        return sum(p in texto_dir for p in pistas) + 2 * sum(p in pref for p in pistas) + hecho_para
    orden = sorted(libres, key=lambda k: (-puntos(k), hashlib.md5(f"{semilla}-{k}".encode()).hexdigest()))
    return orden[0], f"puntos {puntos(orden[0])}; evitados por memoria: {', '.join(x for x in recientes if x) or 'ninguno'}"


def fotos_catalogo(categoria: str, semilla: int, n: int = 7) -> list[dict]:
    """Sin fotos del cliente: fotos de CDN gratis y comprobadas (medios.py), en el formato de los bloques."""
    try:
        import medios
        return [{"src": f["url"], "src_movil": f["url_movil"], "alt": f["alt"], "credito": f["credito"]}
                for f in medios.elegir(categoria, n, "", semilla)]
    except Exception:
        return []


# ---------------------------------------------------------------------------------------------- montar
def montar(datos: dict, categoria: str, receta: str = "", direccion: dict | None = None, semilla: int | None = None,
           esqueleto: str = "", preferencia: str = "", fotos_auto: bool = True, memoria: bool = True) -> tuple[str, list[str], dict]:
    direccion = dict(direccion or {})
    if semilla is None:
        semilla = int(hashlib.sha1(json.dumps(datos.get("negocio", {}), sort_keys=True).encode()).hexdigest(), 16) % 97
    rec = elegir_receta(categoria, receta, datos)
    # 09/11 IDENTIDAD (identidad.py): la paleta y las fotos salen de DE QUE VA el negocio, no de un sorteo por sector
    import identidad as ID
    pf = ID.perfil(rec["categoria"], rec.get("receta", ""), datos)
    paleta, motivo_pal = ID.elegir_paleta(pf, datos, leer_memoria(), semilla)
    if paleta:
        direccion["palette"] = paleta
    css_vars, fuentes, estilo, avisos = variables(direccion)
    avisos.append(f"identidad: tipo {pf['tipo'] or '?'} · paleta {(direccion.get('palette') or {}).get('id', '?')} ({motivo_pal})")
    datos = {**datos, "_estilo": estilo}
    datos = {**datos, "_rotulos": rec["rotulos"], "_schema": rec.get("schema", "LocalBusiness")}
    # fotos: las del cliente o, si no hay, 1o biblioteca que CASE con el negocio, 2o internet (licencias libres)
    creditos = ""
    cuenta_fotos = {}
    if not datos.get("fotos") and fotos_auto:
        try:
            cat_fotos, cuenta_fotos = ID.fotos(pf, 7, semilla)
        except Exception as e:  # nunca romper el montaje por las fotos
            cat_fotos, cuenta_fotos = [], {"error": str(e)[:80]}
        if not cat_fotos and not pf.get("fotos"):  # categoria sin identidad: el catalogo de siempre
            cat_fotos = fotos_catalogo(rec["categoria"], semilla)
        if cat_fotos:
            datos = {**datos, "fotos": cat_fotos}
            creditos = "Fotos: " + " · ".join(dict.fromkeys(f["credito"] for f in cat_fotos[:5]))
        avisos.append(f"fotos: {cuenta_fotos or 'catalogo general'}")
    # esqueleto: estructura de la pagina (orden, variantes, efecto) sin repetir las 3 ultimas de la categoria
    # negocios donde la foto vende (hosteleria, alojamiento...): nada de portadas solo de texto si hay fotos
    excluir = SIN_FOTOS if (pf.get("fotografica") and datos.get("fotos")) else ()
    nombre_esq, motivo_esq = elegir_esqueleto(esqueleto, direccion, preferencia or preferencia_radar(rec.get("sector", "")), semilla,
                                              rec["categoria"], excluir, pf.get("tipo", ""))
    esq = cargar_esqueletos()[nombre_esq]
    # estilos con identidad propia (galeria, tostador): traen sus paletas y su tipografia. Si el cliente pidio colores
    # o una paleta, mandan los suyos (elegir_paleta los respeta).
    if esq.get("paletas") or esq.get("tipografia"):
        if esq.get("paletas"):
            pal_e, motivo_pal = ID.elegir_paleta({**pf, "paletas": esq["paletas"]}, datos, leer_memoria(), semilla)
            if pal_e:
                direccion["palette"] = pal_e
        if esq.get("tipografia"):
            direccion["type"] = esq["tipografia"]
        css_vars, fuentes, estilo, avisos_e = variables(direccion)
        datos = {**datos, "_estilo": estilo}
        avisos += [a for a in avisos_e if a not in avisos]
        avisos.append(f"estilo {nombre_esq}: paleta {(direccion.get('palette') or {}).get('id', '?')} · "
                      f"letra {((direccion.get('type') or {}).get('display') or {}).get('family', '?')}")
    receta_bloques = [b for b in rec["bloques"] if b not in (esq.get("quitar") or [])]
    orden = [b for b in esq["orden"] if b in receta_bloques]
    resto = [b for b in receta_bloques if b not in orden]
    if "pie" in orden:
        orden = orden[:orden.index("pie")] + resto + orden[orden.index("pie"):]
    else:
        orden += resto
    import efectos as EF
    fotos_ef = [{"url": f["src"], "url_movil": f.get("src_movil", f["src"]), "alt": f.get("alt", "")} for f in (datos.get("fotos") or [])]
    usa_efectos = False
    import efectos3d as EF3
    tres_d = esq.get("tres_d") or {}
    usa_3d = bool(tres_d.get("ligero"))
    partes, css_bloques, usados = [], [], {"_esqueleto": nombre_esq}
    for i, nombre in enumerate(orden):
        # 09/11: cierre antes de reservar: zoom (la foto se aleja) o mascara (la foto se abre desde un circulo)
        if nombre == "reservar" and esq.get("cierre") in ("zoom", "mascara") and len(fotos_ef) > 1:
            n_ = datos.get("negocio") or {}
            dc = {"titulo": n_.get("eslogan") or n_.get("nombre"), "texto": n_.get("descripcion") or ""}
            partes.append(EF.bloque(esq["cierre"], "cierre", dc, fotos_ef[-1:]))
            usados["cierre"] = esq["cierre"]
            usa_efectos = True
        if nombre == "destacados" and esq.get("efecto") in ("pasos", "apiladas", "horizontal") and datos.get("destacados"):
            r_ = datos.get("_rotulos") or {}
            titulo = (datos.get("_titulos") or {}).get("destacados") or r_.get("destacados") or "Lo que no te puedes perder"
            items = [{"titulo": x.get("nombre"), "texto": x.get("descripcion") or x.get("etiqueta") or ""} for x in datos["destacados"][:6]]
            clave = "pasos" if esq["efecto"] == "pasos" else "tarjetas"
            partes.append(EF.bloque(esq["efecto"], "destacados", {"titulo": titulo, clave: items}, fotos_ef[1:] or fotos_ef))
            usados[nombre] = esq["efecto"]
            usa_efectos = True
            continue
        info = B.BLOQUES[nombre]["variantes"]
        pedida = (esq.get("variantes") or {}).get(nombre)
        valida = pedida in info and (datos.get("fotos") or not info[pedida].get("fotos")) and (datos.get("video") or not info[pedida].get("video"))
        variante = pedida if valida else elegir_variante(nombre, datos, estilo, semilla + i)
        trozo, css = B.BLOQUES[nombre]["fn"](datos, variante)
        if nombre == "hero" and trozo.strip():  # 09/11: fondo vivo y decoradores del kit de efectos en la portada
            tres = esq.get("tres_d") or {}
            if tres.get("protagonista") in EF3.PROTAGONISTAS:  # 3D protagonista (sustituye al fondo vivo 2D)
                trozo = re.sub(r'(<section\b[^>]*class=")', r'\1hero--3d hero--3d-' + tres["protagonista"] + " ", trozo, count=1)
                trozo = re.sub(r"(<section\b[^>]*>)", r"\1" + EF3.canvas(tres["protagonista"]), trozo, count=1)
                usados["3d"] = tres["protagonista"]
                usa_3d = True
            elif esq.get("fondo") in ("malla", "particulas"):
                trozo = re.sub(r"(<section\b[^>]*>)", r"\1" + EF.canvas_fondo(esq["fondo"]), trozo, count=1)
                css += f"\n.pag--{nombre_esq} .hero {{ position: relative; isolation: isolate; overflow: hidden; }}"
                usados["fondo"] = esq["fondo"]
                usa_efectos = True
            deco = esq.get("decoradores") or []
            if "titular" in deco:
                trozo = re.sub(r"<h1\b(?![^>]*data-efecto)", '<h1 data-efecto="titular"', trozo, count=1)
            if "magnetico" in deco:
                trozo = re.sub(r'(<a\b[^>]*class="boton boton--principal")', r'\1 data-efecto="magnetico"', trozo, count=1)
            if deco:
                usados["decoradores"] = ",".join(deco)
                usa_efectos = True
        if trozo.strip():
            partes.append(trozo)
            usados[nombre] = variante
            if css not in css_bloques:
                css_bloques.append(css)
    if usa_efectos:
        css_bloques.append(EF.EFECTOS_CSS)
    if esq.get("rasgos"):
        css_bloques.append(css_rasgos(nombre_esq, esq["rasgos"]))
    # 09/11 bloques 3D con contenido REAL del cliente: producto .glb tras los destacados, Lottie tras la portada
    extra_3d = [(EF3.producto_3d(datos), 'id="destacados"'), (EF3.lottie(datos), 'id="inicio"')]
    for trozo3, despues_de in extra_3d:
        if trozo3:
            i = next((k for k, p in enumerate(partes) if despues_de in p), 0)
            partes.insert(i + 1, trozo3)
            usa_3d = True
    if usa_3d:
        css_bloques.append(EF3.CSS)
        if tres_d.get("ligero"):
            usados["3d_ligero"] = tres_d["ligero"]
    if creditos:
        partes.append(f'<p class="t-small" style="text-align:center;opacity:.75;padding:1rem var(--gutter) 2rem">{html.escape(creditos)}</p>')
    avisos.append(f"esqueleto: {nombre_esq} ({motivo_esq})")
    if memoria:
        n_ = datos.get("negocio") or {}
        apuntar_memoria({"fecha": __import__("time").strftime("%Y-%m-%d %H:%M"), "negocio": n_.get("nombre", ""), "categoria": rec["categoria"],
                         "esqueleto": nombre_esq, "hero": usados.get("hero", ""), "destacados": usados.get("destacados", ""),
                         "direccion": (direccion.get("direction") or {}).get("id", ""), "tipo": pf.get("tipo", ""),
                         "paleta": str((direccion.get("palette") or {}).get("id", "")).split("+")[0],
                         "fotos": cuenta_fotos})
    n = datos.get("negocio") or {}
    titulo = html.escape(" · ".join(x for x in (n.get("nombre"), n.get("tipo"), n.get("ciudad")) if x) or "Web")
    descripcion = html.escape(str(n.get("descripcion") or n.get("eslogan") or ""))
    fuentes_html = "".join(f'<link rel="stylesheet" href="{html.escape(u)}">' for u in fuentes[:1])
    sistema = (AQUI / "sistema.css").read_text(encoding="utf-8")
    cdn = json.loads((AQUI / "cdn.json").read_text(encoding="utf-8"))
    lenis = cdn["lenis"]
    scroll_suave = f"""<link rel="stylesheet" href="{html.escape(lenis['css'])}">
<script>
(() => {{ if (matchMedia('(prefers-reduced-motion: reduce)').matches || !matchMedia('(pointer: fine)').matches) return;
  const s = document.createElement('script'); s.src = {json.dumps(lenis['js'])}; s.defer = true;
  s.onload = () => {{ if (!window.Lenis) return; const l = new Lenis({{ lerp: 0.12 }});
    const f = (t) => {{ l.raf(t); requestAnimationFrame(f); }}; requestAnimationFrame(f);
    document.addEventListener('click', (ev) => {{ const a = ev.target.closest('a[href^="#"]'); if (!a || a.getAttribute('href').length < 2) return;
      const d = document.querySelector(a.getAttribute('href')); if (d) {{ ev.preventDefault(); l.scrollTo(d, {{ offset: -72 }}); }} }}); }};
  document.head.appendChild(s); }})();
</script>"""
    pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{descripcion}">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{descripcion}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fuentes_html}
<style>
{sistema}
{css_vars}
{''.join(css_bloques)}
</style>
{json_ld(datos)}
{scroll_suave}
</head>
<body class="pag--{nombre_esq}"{" data-3d-ligero" if tres_d.get("ligero") else ""}>
<script>document.documentElement.classList.add('js');</script>
<a class="solo-lector" href="#inicio">Saltar al contenido</a>
{''.join(partes)}
{EF.EFECTOS_JS if usa_efectos else ""}
{EF3.JS if usa_3d else ""}
<script>
(() => {{ const io = 'IntersectionObserver' in window ? new IntersectionObserver((es) => es.forEach(x => {{
    if (x.isIntersecting) {{ x.target.classList.add('visto'); io.unobserve(x.target); }} }}), {{ rootMargin: '0px 0px -8% 0px' }}) : null;
  document.querySelectorAll('.revelar').forEach(el => io ? io.observe(el) : el.classList.add('visto'));
}})();
</script>
</body>
</html>
"""
    avisos += [f"dato pendiente: {p}" for p in pendientes(datos)]
    return pagina, avisos, usados


def main() -> int:
    ap = argparse.ArgumentParser(description="Monta una web con la biblioteca de Nova (sin IA)")
    ap.add_argument("--datos", required=True)
    ap.add_argument("--categoria", default="hosteleria")
    ap.add_argument("--receta", default="")
    ap.add_argument("--esqueleto", default="", help="editorial | inmersivo | bento | minimal | catalogo (por defecto lo elige: memoria + direccion + radar)")
    ap.add_argument("--direccion", default="")
    ap.add_argument("--out", default="index.html")
    ap.add_argument("--semilla", type=int, default=None)
    a = ap.parse_args()
    datos = json.loads(Path(a.datos).read_text(encoding="utf-8"))
    direccion = json.loads(Path(a.direccion).read_text(encoding="utf-8")) if a.direccion else {}
    pagina, avisos, usados = montar(datos, a.categoria, a.receta, direccion, a.semilla, esqueleto=a.esqueleto)
    Path(a.out).write_text(pagina, encoding="utf-8")
    print(f"[MONTAR] {a.out} · bloques: " + ", ".join(f"{k}({v})" for k, v in usados.items()))
    for x in avisos:
        print(f"[MONTAR] aviso: {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
