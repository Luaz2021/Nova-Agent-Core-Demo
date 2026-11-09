import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
auto_planos.py - Planos y sistema de diseño de CUALQUIER web, calculados de las medidas (0 tokens, sin IA)
==========================================================================================================
Lee referencia/spec.json y datos.json de la web analizada y genera:
  claude/diseno.json   colores con nombre (tinta, fondo, acento, enlace...), fuentes, escala tipográfica, botón base
  claude/sec_N.md      plano corto de cada sección (~150-250 tokens): contenedor, anchura, paddings, grid/carrusel
                       con su gap real, tipografía y botones en clases de Tailwind
  claude/planos.json   lo mismo en datos (para otros scripts)

Nada está escrito a mano para una web concreta: todo sale de lo medido.
Los archivos escritos a mano en claude/ (sin la marca AUTO) NO se tocan: así Claude puede afinar una sección
y el script no se la pisa al volver a generar.

Uso:  python auto_planos.py [carpeta]        (sin carpeta: el último análisis)
"""
import json
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"
MARCA = "<!-- AUTO auto_planos"
PESOS = {100: "font-thin", 200: "font-extralight", 300: "font-light", 400: "font-normal", 500: "font-medium",
         600: "font-semibold", 700: "font-bold", 800: "font-extrabold", 900: "font-black"}


# ---------------------------------------------------------------- colores
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _luz(h):
    r, g, b = (c / 255 for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _sat(h):
    c = _rgb(h)
    return (max(c) - min(c)) / max(c) if max(c) else 0


def _opaco(h):
    return isinstance(h, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", h) is not None


def _ranking(pares, respaldo):
    """[(hex, veces)] opacos, de más a menos usado (datos.json) o, si no hay, la lista del spec."""
    lista = [(h.upper(), n) for h, n in (pares or []) if _opaco(h)]
    return lista or [(h.upper(), len(respaldo) - i) for i, h in enumerate(respaldo or []) if _opaco(h)]


def sistema_de_diseno(spec, datos):
    dis = datos.get("diseno", {})
    textos = _ranking(dis.get("colores_texto"), spec.get("colores_texto"))
    fondos = _ranking(dis.get("colores_fondo"), spec.get("colores_fondo"))
    bordes = _ranking(dis.get("colores_borde"), [])
    botones = [b for s in spec["secciones"] for b in s.get("botones", [])]
    colores = {}

    def poner(nombre, hexa):
        if hexa and nombre not in colores:
            colores[nombre] = hexa

    neutros = [(h, n) for h, n in textos if _sat(h) < 0.25]
    vivos = [(h, n) for h, n in textos if _sat(h) >= 0.35]
    fondo = fondos[0][0] if fondos else (spec.get("fondo_body") or "#FFFFFF").upper()
    poner("fondo", fondo)
    poner("superficie", next((h for h, _ in fondos[1:] if abs(_luz(h) - _luz(fondo)) > 0.015), None))
    # tinta: el texto neutro más usado que contrasta con el fondo; gris: el siguiente neutro, más claro
    tinta = next((h for h, _ in neutros if abs(_luz(h) - _luz(fondo)) > 0.45), neutros[0][0] if neutros else None)
    poner("tinta", tinta)
    if tinta:
        poner("gris", next((h for h, _ in neutros if h != tinta and abs(_luz(h) - _luz(tinta)) > 0.12
                            and abs(_luz(h) - _luz(fondo)) > 0.2), None))
    btn = Counter(b["fondo"].upper() for b in botones if _opaco(b.get("fondo")) and _sat(b["fondo"]) >= 0.35)
    acento = btn.most_common(1)[0][0] if btn else None
    enlace = vivos[0][0] if vivos else None
    poner("acento", acento or enlace or next((h for h, _ in fondos if _sat(h) >= 0.35), None))
    poner("enlace", enlace)
    poner("destacado", next((h for h, _ in vivos if h not in (enlace, acento)), None))
    poner("borde", bordes[0][0] if bordes else None)

    # fuentes: la del texto más grande (títulos) y la más repetida (texto), ya cambiadas a Google Fonts
    fg = spec.get("fuentes_google", {})
    todos = [t for s in spec["secciones"] for t in s.get("textos", [])]
    grande = max(todos, key=lambda t: t.get("px", 0), default=None)
    comun = Counter(t.get("fuente") for t in todos if t.get("fuente")).most_common(1)
    fuentes = {"titulo": fg.get(grande["fuente"], "Inter") if grande and grande.get("fuente") else "Inter",
               "texto": fg.get(comun[0][0], "Inter") if comun else "Inter"}

    # escala tipográfica: tamaños más usados, con su tamaño en móvil y su peso habitual
    escala = []
    for px, veces in Counter(t["px"] for t in todos if t.get("px")).most_common(8):
        mismos = [t for t in todos if t.get("px") == px]
        movil = Counter(t["px_movil"] for t in mismos if t.get("px_movil")).most_common(1)
        peso = Counter(t.get("peso") for t in mismos if t.get("peso")).most_common(1)
        escala.append({"px": px, "movil": movil[0][0] if movil else px, "peso": peso[0][0] if peso else 400, "veces": veces})
    escala.sort(key=lambda e: -e["px"])

    base_btn = Counter((b.get("fondo"), b.get("color"), b.get("radio"), b.get("pad"), b.get("px"), b.get("h")) for b in botones).most_common(1)
    boton = None
    if base_btn:
        f, c, r, pad, px, h = base_btn[0][0]
        boton = {"fondo": f, "color": c, "radio": r, "pad": pad, "px": px, "alto": h}

    notas = []
    if boton:
        notas.append(f"botón base {('píldora (rounded-full)' if _radio(boton['radio'], boton['alto']) == 'rounded-full' else _radio(boton['radio'], boton['alto']))}"
                     f" {boton['fondo']}/{boton['color']} {boton['px']}px")
    notas.append(f"fondo dominante {fondo}")
    if grande:
        notas.append(f"titulares {fuentes['titulo']} {grande.get('peso', 600)} hasta {grande['px']}px")
    return {"_auto": True, "_web": spec.get("url", ""), "colores": colores, "fuentes": fuentes,
            "escala": escala, "boton": boton, "notas": " · ".join(notas)}


# ---------------------------------------------------------------- clases de Tailwind
def _radio(r, alto=None):
    r = int(r or 0)
    if r <= 0:
        return "rounded-none"
    if alto and r >= alto / 2:
        return "rounded-full"
    return f"rounded-[{r}px]"


def _peso(p):
    try:
        return PESOS[min(PESOS, key=lambda k: abs(k - int(p)))]
    except (TypeError, ValueError):
        return "font-normal"


def _tam(px, px_movil=None):
    return f"text-[{px_movil}px] md:text-[{px}px]" if px_movil and px_movil != px else f"text-[{px}px]"


def _color(hexa, colores, prefijo):
    hexa = (hexa or "").upper()
    nombre = next((k for k, v in colores.items() if v == hexa), None)
    return f"{prefijo}-{nombre}" if nombre else f"{prefijo}-[{hexa}]"


def _pad(pad):
    """'11px 21px' -> 'py-[11px] px-[21px]' (acepta 1, 2 o 4 valores)."""
    v = re.findall(r"[\d.]+", pad or "")
    if not v:
        return ""
    v = [str(round(float(x))) for x in v]
    if len(v) == 1:
        return f"p-[{v[0]}px]"
    arr, der = v[0], v[1]
    aba, izq = (v[2], v[3]) if len(v) >= 4 else (arr, der)
    py = f"py-[{arr}px]" if arr == aba else f"pt-[{arr}px] pb-[{aba}px]"
    px = f"px-[{der}px]" if der == izq else f"pl-[{izq}px] pr-[{der}px]"
    return f"{py} {px}"


def _cols(n):
    n = max(1, int(n or 1))
    return f"grid-cols-{n}" if n <= 12 else f"grid-cols-[repeat({n},minmax(0,1fr))]"


def _mediana(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


# ---------------------------------------------------------------- plano de una sección
def plano_seccion(s, diseno, componentes):
    col = diseno["colores"]
    ancho, alto = s.get("ancho") or 1920, s.get("alto_escritorio") or s.get("alto") or 0
    textos, imgs = s.get("textos", []), [i for i in s.get("imagenes", []) if i.get("w", 0) >= 8]
    fotos = [i for i in imgs if i.get("tipo") != "svg"]
    cajas = [(t["x"], t["y"], t.get("w", 0), t.get("lh") or round(t.get("px", 16) * 1.2)) for t in textos if "x" in t] + \
            [(i["x"], i["y"], i["w"], i["h"]) for i in imgs if "x" in i]
    p = {"n": s["n"], "tag": s.get("tag", "section"), "alto": alto, "alto_movil": s.get("alto_movil"), "ancho": ancho}

    # anchura del contenido y paddings, de la caja que envuelve todo lo que hay dentro
    if cajas:
        izq = max(0, min(c[0] for c in cajas))
        der = min(ancho, max(c[0] + c[2] for c in cajas))
        arriba = max(0, min(c[1] for c in cajas))
        abajo = max(0, alto - max(c[1] + c[3] for c in cajas)) if alto else 0
        desborda = max(c[0] + c[2] for c in cajas) > ancho + 4
        centrado = desborda or abs(izq - (ancho - der)) <= max(24, ancho * 0.03)
        contenido = ancho - 2 * izq if desborda else der - izq
        p.update(izq=izq, contenido=contenido, pt=arriba, pb=abajo)
        p["caja"] = ("w-full" if contenido >= ancho - 8 else
                     f"max-w-[{contenido}px] mx-auto" if centrado else f"pl-[{izq}px] max-w-[{contenido}px]")
    # filas de fotos: la más larga da el ancho de tarjeta y el gap real
    filas = {}
    for i in sorted(fotos, key=lambda i: (i["y"], i["x"])):
        clave = next((k for k in filas if abs(k - i["y"]) <= 12), i["y"])
        filas.setdefault(clave, []).append(i)
    fila = max(filas.values(), key=len, default=[])
    if len(fila) >= 2:
        fila.sort(key=lambda i: i["x"])
        huecos = [b["x"] - (a["x"] + a["w"]) for a, b in zip(fila, fila[1:]) if b["x"] - (a["x"] + a["w"]) >= 0]
        p["gap"] = _mediana(huecos)
        p["tarjeta"] = Counter((i["w"], i["h"]) for i in fila).most_common(1)[0][0]
        p["por_fila"] = len(fila)

    cpa = s.get("columnas_por_ancho") or {}
    cm, ct, ce = cpa.get("movil", 1), cpa.get("tablet", cpa.get("movil", 1)), cpa.get("escritorio", s.get("columnas", 1))
    tipo = (s.get("comportamiento") or {}).get("tipo", "carrusel_horizontal" if s.get("carrusel") else "estatica")
    gap = f" gap-[{p['gap']}px]" if p.get("gap") is not None else ""
    if tipo == "carrusel_horizontal" or s.get("carrusel"):
        item = f"w-[{p['tarjeta'][0]}px] " if p.get("tarjeta") else ""
        p["layout"] = (f"fila deslizable: flex overflow-x-auto snap-x snap-mandatory{gap} [scrollbar-width:none]; "
                       f"cada elemento {item}flex-shrink-0 snap-start (NO lo apiles en vertical)")
    elif max(cm, ct, ce) > 1:
        cls = [_cols(cm)] + ([f"md:{_cols(ct)}"] if ct != cm else []) + ([f"lg:{_cols(ce)}"] if ce != ct else [])
        p["layout"] = f"grid {' '.join(cls)}{gap} (móvil {cm} · tablet {ct} · escritorio {ce} columnas)"
    else:
        p["layout"] = "una columna (flex flex-col)"
    extra = {"acordeon": "desplegables: <details>/<summary> o botón con aria-expanded",
             "video_loop": "vídeo en bucle (autoplay muted loop playsinline object-cover)",
             "canvas_3d": "canvas/3D: va como imagen o vídeo de fondo",
             "iframe_embebido": "contenido incrustado (iframe)"}.get(tipo)
    if extra:
        p["comportamiento"] = extra
    if s.get("superpuesto") or s.get("imagen_fondo"):
        p["capas"] = "texto encima de imagen/vídeo: relative; el medio absolute inset-0 object-cover; el texto relative z-10"

    # tipografía: los estilos distintos de la sección, de mayor a menor
    estilos = {}
    for t in textos:
        k = (t.get("px"), t.get("peso"), (t.get("color") or "").upper())
        estilos.setdefault(k, {"t": t, "veces": 0})["veces"] += 1
    p["tipos"] = []
    for (px, peso, color), e in sorted(estilos.items(), key=lambda x: -(x[0][0] or 0))[:4]:
        t = e["t"]
        cls = [_tam(px, t.get("px_movil")), _peso(peso), _color(color, col, "text")]
        if t.get("may"):
            cls.append("uppercase")
        if abs(t.get("espaciado") or 0) >= 0.1:
            cls.append(f"tracking-[{t['espaciado']}px]")
        if t.get("lh") and px:
            cls.append(f"leading-[{t['lh']}px]")
        p["tipos"].append({"ejemplo": t["t"][:40], "veces": e["veces"], "clases": " ".join(cls)})

    # botones: estilos distintos
    p["botones"] = []
    vistos = Counter((b.get("fondo"), b.get("color"), b.get("radio"), b.get("pad"), b.get("px")) for b in s.get("botones", []))
    for (f, c, r, pad, px), veces in vistos.most_common(2):
        b = next(x for x in s["botones"] if (x.get("fondo"), x.get("color"), x.get("radio"), x.get("pad"), x.get("px")) == (f, c, r, pad, px))
        cls = [_color(f, col, "bg") if _opaco(f) else "bg-transparent", _color(c, col, "text"), _radio(r, b.get("h")), _pad(pad), _tam(px), _peso(b.get("peso"))]
        p["botones"].append({"ejemplo": b.get("t", "")[:30], "veces": veces, "clases": " ".join(x for x in cls if x)})

    if fotos:
        tam = Counter((i["w"], i["h"]) for i in fotos).most_common(1)[0][0]
        p["imagenes"] = f"{len(fotos)} foto(s), la más repetida {tam[0]}x{tam[1]}" + \
                        (f", {sum(1 for i in fotos if i.get('redonda'))} redonda(s)" if any(i.get("redonda") for i in fotos) else "")
    iconos = len(imgs) - len(fotos)
    if iconos:
        p["iconos"] = iconos
    # repetidos: datos.json los cuenta en toda la página; aquí solo los que encajan con lo que hay en ESTA sección
    def encaja(c):
        if not fotos:
            return len(c.get("secciones", [])) == 1
        return any(abs(i["w"] - c["ancho"]) <= c["ancho"] * 0.1 and abs(i["h"] - c["alto"]) <= c["alto"] * 0.1 for i in fotos) \
            or ("imagen" not in c["nombre"] and len(c.get("secciones", [])) == 1)
    p["componentes"] = [f"{c['nombre']} ×{c['veces']} ({c['ancho']}x{c['alto']})"
                        for c in componentes if s["n"] in c.get("secciones", []) and encaja(c)][:3]
    p["fondo"] = _color(s.get("fondo"), col, "bg") if _opaco(s.get("fondo")) else ""
    p["alinea"] = "text-center" if s.get("alineacion") == "centrado" else "text-left"
    return p


def plano_md(p):
    """El plano en texto corto para Qwen (lo que va en claude/sec_N.md)."""
    L = [f"{MARCA} · sección {p['n']} · calculado de las medidas -->",
         f"PLANO MEDIDO DE LA SECCIÓN {p['n']} (<{p['tag']}> {p['ancho']}x{p['alto']}px en PC"
         + (f", alto {p['alto_movil']}px en móvil" if p.get("alto_movil") else "") + "):"]
    cont = " ".join(x for x in (p.get("fondo"), p["alinea"]) if x)
    if p["alto"] and p["alto"] <= 80:
        cont += f" h-[{p['alto']}px]"
    L.append(f"- Contenedor: {cont}" + (f" pt-[{p['pt']}px] pb-[{p['pb']}px]" if p.get("pt") is not None and p["alto"] > 80 else "")
             + " (no fijes la altura con h-[...]: que la dé el contenido)" * (p["alto"] > 80))
    if p.get("caja"):
        L.append(f"- Contenido: {p['caja']}")
    L.append(f"- Disposición: {p['layout']}")
    for k in ("comportamiento", "capas"):
        if p.get(k):
            L.append(f"- {k.capitalize()}: {p[k]}")
    for t in p["tipos"]:
        veces = f" (×{t['veces']})" if t["veces"] > 1 else ""
        L.append(f"- Texto \"{t['ejemplo']}\"{veces}: {t['clases']}")
    for b in p["botones"]:
        L.append(f"- Botón \"{b['ejemplo']}\" ×{b['veces']}: {b['clases']}")
    if p.get("imagenes"):
        L.append(f"- Imágenes: {p['imagenes']}" + (f" · {p['iconos']} icono(s) SVG" if p.get("iconos") else ""))
    if p.get("componentes"):
        L.append(f"- Repetidos (escríbelos una vez y repítelos igual): {'; '.join(p['componentes'])}")
    return "\n".join(L)


# ---------------------------------------------------------------- archivos
def _es_auto(ruta):
    """Se puede (re)escribir: no existe, lo generó este script, o es del antiguo auto_planos escrito para Apple."""
    if not ruta.exists():
        return True
    t = ruta.read_text(encoding="utf-8", errors="replace")
    if ruta.suffix == ".json":
        try:
            j = json.loads(t)
            return bool(j.get("_auto")) or str(j.get("notas", "")).startswith("Filosofía Apple minimalista")
        except Exception:
            return False
    return t.startswith(MARCA) or t.startswith("<!-- INSTRUCCIONES ARQUITECTO")


def generar_planos(carpeta=None):
    carpeta = Path(carpeta) if carpeta else Path((WORKSPACE / "ultimo_analisis.txt").read_text(encoding="utf-8").strip())
    datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8")) if (carpeta / "datos.json").exists() else {}
    ref = Path(datos.get("carpeta_referencia") or carpeta / "referencia")
    spec_path = ref / "spec.json"
    if not spec_path.exists():
        print(f"[ERROR] No se encontró {spec_path}")
        return False
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    dclaude = carpeta / "claude"
    dclaude.mkdir(parents=True, exist_ok=True)

    ruta = dclaude / "diseno.json"
    diseno = sistema_de_diseno(spec, datos)
    if _es_auto(ruta):
        ruta.write_text(json.dumps(diseno, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(f"  diseno.json escrito a mano: se respeta")
        diseno = {**diseno, **json.loads(ruta.read_text(encoding="utf-8"))}

    planos, escritas, respetadas = [], 0, []
    for s in spec["secciones"]:
        p = plano_seccion(s, diseno, datos.get("componentes", []))
        planos.append(p)
        ruta = dclaude / f"sec_{s['n']}.md"
        if _es_auto(ruta):
            ruta.write_text(plano_md(p), encoding="utf-8")
            escritas += 1
        else:
            respetadas.append(s["n"])
    (dclaude / "planos.json").write_text(json.dumps({"_auto": True, "diseno": diseno, "secciones": planos},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] planos de {spec.get('url', carpeta.name)}: diseno.json + {escritas} sec_N.md en {dclaude}"
          + (f" (escritos a mano, respetados: {respetadas})" if respetadas else ""))
    return True


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    generar_planos(args[0] if args else None)
