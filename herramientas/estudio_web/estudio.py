r"""
NOVA · ESTUDIO WEB (15/11/2026, Claude, a pedido del usuario). Sustituye a gema_esqueleto y a la "Gema" en markdown.

Idea: Nova es la DIRECTORA DE ARTE y decide el diseno con lo que sabe. La biblioteca es su caja de herramientas
(efectos, CDN, buscador de fotos), no un molde. Qwen pica el HTML con las clases que ella definio. El CODIGO revisa
lo medible; Nova y el usuario juzgan el gusto mirando 2 hojas de capturas.

  1. ficha    <carpeta> "<pedido>"        -> estudio/ficha.json para rellenar + que NO repetir de webs anteriores
  2. fotos    <carpeta> --buscar "..."    -> baja candidatas y hace UNA hoja numerada para elegir mirandolas
  3. validar  <carpeta>                   -> contraste, neones, tipografias, repeticion, fotos. Crea estilos/00_tokens.css
                                             y el resumen para ENSENARSELO AL USUARIO antes de construir.
  4. (Nova)   estudio/estilos/NN_*.css (cada uno <= 150 lineas) + estudio/secciones.json (+ secciones/<id>.html suyas)
  5. picar    <carpeta> [--solo a,b]      -> Qwen escribe el HTML de las secciones "autor": "qwen"
  6. montar   <carpeta>                   -> index.html + estilos.css (+ app.js si hay estudio/extra.js)
  7. revisar  <carpeta>                   -> baja por la web en PC y movil, mide, mira las fotos con InternVL
                                             -> estudio/revision.md + capturas/hoja_pc.jpg + hoja_movil.jpg
  herramientas                            -> lo que hay en la biblioteca para coger SOLO si hace falta

Uso: <PYTHON> "<NOVA_HOME>/antigravity/herramientas/estudio_web/estudio.py" <orden> ...
Salida 0 = OK, 1 = hay fallos (leer lo que imprime), 2 = mal llamado.
"""

from __future__ import annotations

import argparse
import base64
import colorsys
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

NOVA = Path.home() / ".gemini"
AG = NOVA / "antigravity"
BIBLIOTECA = AG / "almacen" / "biblioteca_web"
MEMORIA = Path(os.environ.get("NOVA_ESTUDIO_MEMORIA") or AG / "herramientas" / "datos" / "estudio_web" / "memoria.json")
MODELOS = AG / "scripts" / "nova_modelos.json"
sys.path.insert(0, str(NOVA / "nova_core"))
sys.path.insert(0, str(BIBLIOTECA))
sys.path.insert(0, str(AG / "scripts"))

# NOVA_ESTUDIO_TELEMETRIA / NOVA_ESTUDIO_MEMORIA: solo para pruebas (no tocar la telemetria ni la memoria reales)
TELEMETRIA = Path(os.environ.get("NOVA_ESTUDIO_TELEMETRIA") or AG / "memory" / "registros" / "telemetria_hooks.jsonl")
SKILLS = AG / "almacen" / "skills"
# Skills por fase. "obligatorias": el estudio comprueba en la telemetria del hook que Nova las LEYO (ultimas 12 h).
SKILLS_DIRECCION = ["frontend-design-direction", "typography-system", "color-palette-builder"]
SKILLS_PIEZA = {"video-scroll": ["scroll-video-ffmpeg-webcodecs"], "webgl": ["webgl-shaders-postprocessing"],
                "3d": ["threejs-web-experience"], "canvas": ["gemini-motion-artifacts"]}
SKILLS_HERRAMIENTA = {"gsap": ["gsap-scrolltrigger", "cinematic-gsap-lenis-motion-system"], "lenis": ["cinematic-gsap-lenis-motion-system"]}
SKILLS_CONSTRUIR = ["site-motion-excellence-director", "motion-design"]
SKILLS_CIERRE = ["design-critique", "frontend-a11y", "web-seo-mastery", "gemini-webperf"]
SKILLS_OPCIONALES = {
    "build-awwwards-quality-sites": "heroes distintivos y coreografia nivel Awwwards",
    "swiss-kinetic-typography-grid": "reticula editorial asimetrica y tipografia viva",
    "flagship-saas-experimental-patterns": "patrones Linear/Raycast/Vercel (Cmd+K, bordes, bento)",
    "moodboard-builder": "moodboard de 8-16 imagenes antes de decidir",
    "gemini-brand-tokens": "design systems de 156 marcas (Apple, Stripe, Linear...) como referencia",
    "brand-to-design-md": "saca el DESIGN.md de una web de referencia (URL)",
    "gemini-ui-artisan": "radar de 247 webs Awwwards (draw.mjs) e inspect.mjs",
    "design-doctrine": "dogmas: tokens por intencion, cirugia visual",
    "web-motion-auditor": "auditar animaciones y reduced-motion",
    "web-legal-compliance": "aviso legal / cookies si la web es real",
}
MAX_LINEAS_NOVA = 150  # el hook bloquea mas de 150 lineas de web por archivo escritas desde la nube
TIPOS_PIEZA = {"foto", "tipografia", "ilustracion", "video-scroll", "canvas", "webgl", "3d"}
PIEZA_VIVA = {"video-scroll", "canvas", "webgl", "3d"}
# display sin caracter: sirven para texto, no para titulares de una web "top"
DISPLAY_GENERICA = {"inter", "roboto", "poppins", "montserrat", "open sans", "lato", "arial", "helvetica",
                    "space grotesk", "dm sans", "nunito", "raleway", "source sans 3", "work sans"}
QUE_COMPRA = {  # 15/11, criterio del usuario: la web ensena LO QUE EL CLIENTE COMPRA
    "producto": "el producto de cerca y el oficio (panaderia, cafe, moda de autor): limpio, poco y apetecible",
    "espacio": "el sitio y su equipamiento (gym, coworking, estudio): salas, maquinas, luz, que te veas ahi",
    "experiencia": "como te vas a sentir (hotel, restaurante, evento): ambiente, vistas, momentos",
    "confianza": "quien te atiende y su trayectoria (clinica, abogado, academia): caras reales, calma, nada que distraiga",
    "catalogo": "elegir y comprar (e-commerce): aqui SI muchos productos, filtros y precios a la vista",
}
ESCALAS = {"barrio", "cadena", "premium"}
CASOS = AG / "herramientas" / "datos" / "estudio_web" / "casos.json"

VACIA = {
    "pedido": "",
    "criterio": {"que_compra": "", "por_que": "", "primer_pantallazo": "", "escala": "", "que_sobra": ""},
    "nivel": 4,
    "datos_reales": {"nombre": "", "direccion": "", "telefono": "", "email": "", "horario": "", "precios": [], "otros": []},
    "concepto": "",
    "referencias": [{"quien": "", "que_tomo": ""}, {"quien": "", "que_tomo": ""}],
    "paleta": {"bg": "", "surface": "", "ink": "", "muted": "", "accent": "", "accent_ink": ""},
    "tipografia": {"display": "", "texto": "", "detalle": ""},
    "pieza_principal": {"tipo": "", "como": ""},
    "secciones": [{"id": "", "patron": "", "proposito": ""}],
    "fotos": [{"archivo": "assets/", "uso": "", "que_se_ve": ""}],
    "herramientas": [],
}

GUIA_DIRECTORA = """
COMO TRABAJA LA DIRECTORA (Nova). Rellena estudio/ficha.json pensando como una disenadora, no como una plantilla:
 0. CRITERIO (lo primero, manda sobre todo lo demas). Una web bonita que no transmite no sirve: entra por los ojos.
    - que_compra: producto | espacio | experiencia | confianza | catalogo (ver tabla abajo). por_que: en 1 frase.
    - primer_pantallazo: que ve el cliente en los primeros 3 s para entender el negocio y querer quedarse
      (panaderia: el pan grande y de cerca; gym: la sala y las maquinas). El revisor mide que la foto principal mande.
    - escala: barrio | cadena | premium. Una cadena necesita un COLOR DE FIRMA propio y fotos con la misma luz.
    - que_sobra: lo que NO vas a poner (limpio, que se entienda; lo cargado solo en catalogo/e-commerce).
    - El efecto (WebGL, scroll...) va al servicio de lo que se compra: nunca lo tapa.
 1. datos_reales: SOLO lo que dio el usuario (nombre, direccion, precios...). Lo que falte = "[PENDIENTE]". En la web
    no puede aparecer ningun precio, telefono ni email que no este aqui (el revisor lo bloquea).
 2. concepto: la idea que hila toda la web en 1-2 frases (que se tiene que SENTIR y por que). Nada de "moderno y elegante".
 3. referencias: minimo 2 webs/marcas reales de nivel (miralas con el navegador) y que tomas de cada una
    (ritmo, como ensenan el producto, tipografia...). No copias: tomas decisiones.
 4. paleta: 6 colores en #hex. bg/surface/ink/muted/accent/accent_ink. Prohibidos neones (lima, cian, magenta
    electricos) y el morado-cian de IA. ink sobre bg >= 7:1, muted >= 4.5:1, accent_ink sobre accent >= 4.5:1.
 5. tipografia: display CON caracter (serif editorial, grotesca con personalidad, mono...) + texto legible
    (+ detalle opcional). Google Fonts, nombre exacto. Inter/Poppins/Montserrat/Space Grotesk NO como display.
 6. pieza_principal: UNA pieza que haga quedarse y que ENSENE lo que se compra. producto -> foto o video-scroll del
    producto (o 3d del producto); espacio/experiencia (nivel 4) -> video-scroll, canvas, webgl o 3d del sitio.
    "como": que hace y con que (frames FFmpeg, shader, Three.js...).
 Textos de la web SIEMPRE con tildes, ñ y ¿¡: "mañana", "Bollería", "¿Qué te apetece?", "-ción". El revisor lo bloquea.
 7. secciones: id + patron (split asimetrico, galeria horizontal, ficha tecnica, mosaico, carrusel en luz baja...)
    + proposito. Varia los patrones: si todo son tarjetas en rejilla, es plantilla.
 8. fotos: elegidas MIRANDOLAS (estudio.py fotos ... te da una hoja numerada). Coherentes entre si y con la paleta;
    sin fondos blancos, sin carteles ni marcas ajenas, ninguna repetida. "que_se_ve" = lo que se ve de verdad.
 9. herramientas: lo que coges de la biblioteca SOLO si lo necesitas ("lenis", "gsap", "efecto:mascara"...). Ver
    estudio.py herramientas. Vacio tambien vale.
Despues: estudio.py validar <carpeta> -> ensena el resumen al usuario y espera su "vale" antes de construir.
"""

GUIA_CONSTRUIR = """
CONSTRUIR (despues del "vale" del usuario):
 a) estudio/estilos/00_tokens.css YA esta hecho (variables y fuentes de la ficha): no lo toques.
 b) Escribe tu el sistema en estudio/estilos/10_base.css, 20_componentes.css, 30_secciones.css... (cada archivo <= 150
    lineas; el hook bloquea mas). Usa SOLO var(--...) de 00_tokens.css. Encima de cada clase que Qwen deba usar pon
    un comentario  /* qwen: .clase = para que sirve */  -> Qwen recibe esa guia.
 c) estudio/secciones.json:
    {"secciones": [
      {"id": "portada", "autor": "nova"},                         <- la escribes tu en estudio/secciones/portada.html
      {"id": "carta", "autor": "qwen",                            <- la pica Qwen
       "estructura": "section.carta > div.contenedor > h2.titulo-seccion + ul.lista-carta > li.plato (h3 + p + span.precio)",
       "textos": {"titulo": "...", "platos": [{"nombre": "Flat white", "texto": "Leche entera...", "precio": "3,20 EUR", "alt": "..."}]},
       (cada texto CON NOMBRE: titulo, texto, boton, alt... Nunca listas sueltas ["a", "b", "c"]: Qwen no sabe cual va donde)
       "fotos": ["assets/barra.jpg"]},
      {"id": "galeria", "autor": "efecto", "efecto": "horizontal", "datos": {...}, "fotos": [...]}  <- kit de la biblioteca
    ]}
    Lo tuyo (portada, pieza principal, navegacion, pie...) va en estudio/secciones/<id>.html (<= 150 lineas cada uno)
    y, si hace falta JS, en estudio/extra.js (<= 150 lineas). Qwen hace el volumen: listas, cartas, fichas, formularios.
 d) estudio.py picar <carpeta>  ->  estudio.py montar <carpeta>  ->  estudio.py revisar <carpeta>
 e) Arregla SOLO lo que diga revision.md (edit_file pequeno), vuelve a montar y revisar. Maximo 3 rondas; despues,
    ensena al usuario las hojas de capturas y lo que queda.
"""


# ---------------------------------------------------------------- utilidades


def leer_json(ruta: Path, defecto=None):
    try:
        return json.loads(ruta.read_text(encoding="utf-8-sig"))  # -sig: acepta el BOM de PowerShell
    except (OSError, ValueError):
        return defecto


def escribir_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def dir_estudio(carpeta: Path) -> Path:
    return carpeta / "estudio"


def hex_rgb(valor: str) -> tuple[int, int, int] | None:
    v = str(valor or "").strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
        return None
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def css_rgb(valor: str) -> tuple[int, int, int, float] | None:
    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?", valor or "")
    if not m:
        return None
    return round(float(m[1])), round(float(m[2])), round(float(m[3])), float(m[4]) if m[4] is not None else 1.0


def luminancia(rgb) -> float:
    c = [x / 255 for x in rgb[:3]]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste(a, b) -> float:
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def es_neon(rgb) -> bool:
    """Lima, cian, magenta o violeta electricos (el look "se nota IA"): muy saturado y luminoso."""
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb[:3]))
    tono = h * 360
    if s < 0.85 or not 0.42 <= l <= 0.75:
        return False
    return 55 <= tono <= 200 or 250 <= tono <= 330 or luminancia(rgb) >= 0.55


def distancia(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a[:3], b[:3], strict=False)) ** 0.5


def lineas(ruta: Path) -> int:
    try:
        return ruta.read_text(encoding="utf-8").count("\n") + 1
    except OSError:
        return 0


def aplanar(x) -> list[str]:
    if isinstance(x, dict):
        return [t for v in x.values() for t in aplanar(v)]
    if isinstance(x, list | tuple):
        return [t for v in x for t in aplanar(v)]
    return [str(x)] if x not in (None, "") else []


def normal(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(t)).strip().lower()


def modelos() -> tuple[str, str]:
    m = leer_json(MODELOS, {}) or {}
    return m.get("coder", "qwen3.5:9b"), m.get("vl", "blaifa/InternVL3_5:8b")


def hoja(imagenes: list[Path], destino: Path, ancho: int, columnas: int, etiquetas: list[str] | None = None) -> Path | None:
    """Une varias capturas en UNA imagen (Nova mira 1 archivo, no 20)."""
    from PIL import Image, ImageDraw

    piezas = []
    for p in imagenes:
        try:
            im = Image.open(p).convert("RGB")
        except OSError:
            continue
        im.thumbnail((ancho, ancho * 3))
        piezas.append(im)
    if not piezas:
        return None
    alto_fila = max(i.height for i in piezas) + 28
    filas = (len(piezas) + columnas - 1) // columnas
    lienzo = Image.new("RGB", (columnas * (ancho + 12) + 12, filas * alto_fila + 12), (40, 40, 40))
    d = ImageDraw.Draw(lienzo)
    for n, im in enumerate(piezas):
        x, y = 12 + (n % columnas) * (ancho + 12), 12 + (n // columnas) * alto_fila
        lienzo.paste(im, (x, y + 22))
        d.text((x, y + 4), (etiquetas or [str(i + 1) for i in range(len(piezas))])[n], fill=(255, 220, 120))
    destino.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(destino, quality=82)
    return destino


def analizar_foto(ruta: Path) -> dict:
    """Tamano, fondo blanco (bordes casi blancos) y huella para detectar repetidas. Sin IA."""
    from PIL import Image

    info = {"ok": False}
    try:
        im = Image.open(ruta)
        info.update(ok=True, ancho=im.width, alto=im.height)
        pq = im.convert("L").resize((120, 120))
        px = pq.load()
        borde = [px[x, y] for x in range(120) for y in range(120) if x < 7 or y < 7 or x > 112 or y > 112]
        info["fondo_blanco"] = sum(1 for v in borde if v > 232) / len(borde) > 0.55
        info["huella"] = hashlib.md5(pq.resize((16, 16)).tobytes()).hexdigest()
    except OSError as e:
        info["error"] = str(e)[:80]
    return info


def url_fuentes(tipo: dict) -> tuple[str, list[str]]:
    """Comprueba en Google Fonts que cada familia existe y devuelve la URL que funciona."""
    familias = [f for f in (tipo.get("display"), tipo.get("texto"), tipo.get("detalle")) if f]
    partes, fallos = [], []
    for fam in dict.fromkeys(familias):
        base = urllib.parse.quote_plus(fam)
        hecha = ""
        for pesos in (":ital,wght@0,400;0,500;0,600;0,700;1,400", ":wght@400;500;600;700", ":wght@400;700", ""):
            u = f"https://fonts.googleapis.com/css2?family={base}{pesos}&display=swap"
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    if r.status == 200:
                        hecha = f"family={base}{pesos}"
                        break
            except Exception:
                continue
        if hecha:
            partes.append(hecha)
        else:
            fallos.append(fam)
    url = "https://fonts.googleapis.com/css2?" + "&".join(partes) + "&display=swap" if partes else ""
    return url, fallos


def memoria() -> list[dict]:
    return leer_json(MEMORIA, []) or []


def casos_para(pedido: str, maximo: int = 6) -> list[dict]:
    """Correcciones reales del usuario: primero las del mismo tipo de negocio, luego las generales."""
    import unicodedata

    casos = leer_json(CASOS, []) or []
    p = "".join(c for c in unicodedata.normalize("NFD", normal(pedido)) if unicodedata.category(c) != "Mn")  # sin tildes
    propios = [c for c in casos if any(k in p for k in c.get("claves", []))]
    generales = [c for c in casos if not c.get("claves")]
    return (propios + generales)[:maximo]


def skills_leidas(horas: float = 12) -> set[str]:
    """Skills que Nova ha abierto de verdad (read_file / view_file / comando con su SKILL.md), segun el hook."""
    if not TELEMETRIA.exists():
        return set()
    limite = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - horas * 3600))
    leidas = set()
    with TELEMETRIA.open("rb") as f:
        f.seek(max(0, TELEMETRIA.stat().st_size - 6_000_000))
        for linea in f.read().decode("utf-8", "replace").splitlines():
            if "SKILL.md" not in linea and "skills" not in linea:
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            if str(d.get("t", "")) < limite:
                continue
            texto = f"{d.get('ruta', '')} {d.get('comando', '')}".replace("/", "\\")
            leidas.update(m.lower() for m in re.findall(r"\\skills\\([\w.-]+)\\SKILL\.md", texto, re.I))
    return leidas


def skills_obligatorias(ficha: dict) -> list[str]:
    tp = str((ficha.get("pieza_principal") or {}).get("tipo", "")).lower()
    req = list(SKILLS_DIRECCION) + SKILLS_PIEZA.get(tp, [])
    for h in ficha.get("herramientas", []):
        req += SKILLS_HERRAMIENTA.get(str(h).lower(), [])
    return [s for s in dict.fromkeys(req) if (SKILLS / s / "SKILL.md").exists()]


def faltan_skills(nombres: list[str]) -> list[str]:
    leidas = skills_leidas()
    return [s for s in nombres if s.lower() not in leidas and (SKILLS / s / "SKILL.md").exists()]


def ruta_skill(nombre: str) -> str:
    return f"<NOVA_HOME>/antigravity/almacen/skills/{nombre}/SKILL.md"


# ---------------------------------------------------------------- 1. ficha


def orden_ficha(a) -> int:
    carpeta = Path(a.carpeta).resolve()
    ruta = dir_estudio(carpeta) / "ficha.json"
    if ruta.exists() and not a.forzar:
        print(f"[ESTUDIO] Ya existe {ruta}. Rellenala o usa --forzar para empezar de cero.")
    else:
        ficha = json.loads(json.dumps(VACIA))
        ficha["pedido"] = a.pedido
        escribir_json(ruta, ficha)
        print(f"[ESTUDIO] Ficha creada: {ruta}")
    print(GUIA_DIRECTORA)
    print("QUE COMPRA EL CLIENTE -> QUE ENSENA LA WEB:")
    for k, v in QUE_COMPRA.items():
        print(f"  - {k}: {v}")
    casos = casos_para(a.pedido or (leer_json(ruta, {}) or {}).get("pedido", ""))
    if casos:
        print("CORRECCIONES DEL USUARIO EN WEBS PARECIDAS (no repitas estos errores):")
        for c in casos:
            print(f"  - {c['web']}: {c['fallo']} -> {c['leccion']}")
    print("LEE ANTES DE RELLENAR (en 1 lote paralelo; validar comprueba que las abriste):")
    for s in SKILLS_DIRECCION:
        print(f"  - {ruta_skill(s)}")
    print("  + segun la pieza principal: " + " · ".join(f"{k} -> {', '.join(v)}" for k, v in SKILLS_PIEZA.items()))
    print("  + si usas gsap/lenis: " + ", ".join(dict.fromkeys(x for v in SKILLS_HERRAMIENTA.values() for x in v)))
    print("OPCIONALES (solo si aportan a ESTA web):")
    for s, para in SKILLS_OPCIONALES.items():
        print(f"  - {s}: {para}")
    ultimas = memoria()[-5:]
    if ultimas:
        print("NO REPITAS (ultimas webs del estudio):")
        for m in ultimas:
            print(f"  - {m.get('fecha', '')} {m.get('proyecto', '')}: display {m.get('display')}, acento {m.get('accent')}, "
                  f"fondo {m.get('bg')}, pieza {m.get('pieza')}, patrones {', '.join(m.get('patrones', [])[:4])}")
    return 0


# ---------------------------------------------------------------- 2. fotos


def bajar(url: str, ruta: Path) -> bool:
    """Wikimedia limita la velocidad (429): se espera y se reintenta. User-Agent generico, sin datos del usuario."""
    for intento in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NovaEstudioWeb/1.0 (uso local; python-urllib)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                ruta.write_bytes(r.read())
            time.sleep(0.6)
            return True
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or intento == 3:
                print(f"[FOTOS] HTTP {e.code}")
                return False
            time.sleep(2 + intento * 3)
        except Exception:
            return False
    return False


def orden_fotos(a) -> int:
    import medios

    carpeta = Path(a.carpeta).resolve()
    destino = carpeta / "assets" / "candidatas"
    destino.mkdir(parents=True, exist_ok=True)
    if a.buscar:  # SOLO fotos del tema (Openverse/Wikimedia): las genericas de Picsum son las que estropeaban las webs
        fotos = []
        for consulta in [c.strip() for c in a.buscar.split("|") if c.strip()]:
            for f in medios.buscar_tema(consulta, a.n):
                if f.get("image") and all(f["image"] != x["url"] for x in fotos):
                    fotos.append({"url": f["image"], "credito": f"{f.get('creator', '')} / {f.get('via', '')} ({f.get('license', '')})"})
        fotos = fotos[: a.n]
    else:
        fotos = medios.elegir(a.categoria or "", a.n, "", a.semilla)
    bajadas, etiquetas, creditos = [], [], []
    for n, f in enumerate(fotos, 1):
        url = f.get("url") or f.get("src")
        if not url:
            continue
        ext = ".jpg" if not re.search(r"\.(png|webp)(\?|$)", url, re.I) else "." + re.search(r"\.(png|webp)", url, re.I)[1].lower()
        ruta = destino / f"c{n:02d}{ext}"
        if not bajar(url, ruta):
            print(f"[FOTOS] c{n:02d} no se pudo bajar ({url[-60:]})")
            continue
        info = analizar_foto(ruta)
        if not info.get("ok"):
            ruta.unlink(missing_ok=True)
            continue
        marca = []
        if info.get("fondo_blanco"):
            marca.append("FONDO BLANCO")
        if info.get("ancho", 0) < 1200:
            marca.append(f"pequena {info.get('ancho')}px")
        bajadas.append(ruta)
        etiquetas.append(f"c{n:02d} {info.get('ancho')}x{info.get('alto')} {' '.join(marca)}")
        creditos.append({"archivo": f"assets/candidatas/{ruta.name}", "credito": f.get("credito", ""), "url": url})
    escribir_json(destino / "creditos.json", creditos)
    h = hoja(bajadas, dir_estudio(carpeta) / "fotos_candidatas.jpg", 300, 4, etiquetas)
    print(f"[FOTOS] {len(bajadas)} candidatas en {destino}")
    if h:
        print(f"[FOTOS] MIRA esta hoja (1 imagen) y elige: {h}")
        print("        Copia las elegidas a assets/ con un nombre claro y ponlas en ficha.fotos con lo que se ve de verdad.")
    return 0 if bajadas else 1


# ---------------------------------------------------------------- 3. validar


def validar_ficha(carpeta: Path, ficha: dict) -> tuple[list[str], list[str], dict]:
    fallos, avisos, extra = [], [], {}
    crit = ficha.get("criterio") or {}
    compra = str(crit.get("que_compra", "")).strip().lower()
    escala = str(crit.get("escala", "")).strip().lower()
    if compra not in QUE_COMPRA:
        fallos.append(f"criterio.que_compra: elige uno de {', '.join(QUE_COMPRA)} (que compra de verdad el cliente)")
    if len(str(crit.get("por_que", "")).strip()) < 20:
        fallos.append("criterio.por_que: explica en una frase por que el cliente elige ESTE negocio y no otro")
    if len(str(crit.get("primer_pantallazo", "")).strip()) < 25:
        fallos.append("criterio.primer_pantallazo: que ve el cliente en los primeros 3 segundos (lo que compra, grande)")
    if escala not in ESCALAS:
        fallos.append(f"criterio.escala: {', '.join(sorted(ESCALAS))}")
    for campo in ("concepto", "paleta", "tipografia", "pieza_principal", "secciones", "referencias"):
        if not ficha.get(campo):
            fallos.append(f"falta '{campo}'")
    if len(str(ficha.get("concepto", "")).strip()) < 30:
        fallos.append("concepto demasiado corto: explica la idea que hila la web (1-2 frases)")
    refs = [r for r in ficha.get("referencias", []) if str(r.get("quien", "")).strip() and str(r.get("que_tomo", "")).strip()]
    if len(refs) < 2:
        fallos.append("hacen falta al menos 2 referencias reales con lo que tomas de cada una")

    pal = ficha.get("paleta", {})
    rgb = {k: hex_rgb(pal.get(k)) for k in ("bg", "surface", "ink", "muted", "accent", "accent_ink")}
    malos = [k for k, v in rgb.items() if v is None]
    if malos:
        fallos.append(f"paleta: colores que no son #hex: {', '.join(malos)}")
    else:
        for a, b, minimo in (("ink", "bg", 7), ("ink", "surface", 4.5), ("muted", "bg", 4.5), ("accent_ink", "accent", 4.5)):
            c = contraste(rgb[a], rgb[b])
            if c < minimo:
                fallos.append(f"contraste {a} sobre {b} = {c:.1f}:1 (minimo {minimo}:1)")
        if contraste(rgb["accent"], rgb["bg"]) < 3:
            avisos.append(f"el acento casi no se ve sobre el fondo ({contraste(rgb['accent'], rgb['bg']):.1f}:1)")
        for k in ("accent", "surface", "bg", "ink"):
            if es_neon(rgb[k]):
                fallos.append(f"paleta: {k} {pal[k]} es un neon (lima/cian/magenta electrico): el look 'se nota IA'")
        if distancia(rgb["bg"], rgb["surface"]) < 6:
            avisos.append("bg y surface son casi iguales: las superficies no se van a distinguir")
        # 15/11 (panaderia): beige/crema + terracota = la paleta "artesano" de siempre, sin firma
        h_bg, l_bg, s_bg = colorsys.rgb_to_hls(*(x / 255 for x in rgb["bg"]))
        h_ac, l_ac, s_ac = colorsys.rgb_to_hls(*(x / 255 for x in rgb["accent"]))
        crema = l_bg > 0.85 and 20 <= h_bg * 360 <= 55 and distancia(rgb["bg"], rgb["surface"]) < 45
        terracota = 5 <= h_ac * 360 <= 30 and 0.3 <= l_ac <= 0.55  # rojo anaranjado de barro; granate/burdeos no lo es
        if crema and terracota:
            (fallos if escala in ("cadena", "premium") else avisos).append(
                "paleta 'artesano' generica (crema + terracota, superficies casi iguales): no tiene color de firma. "
                + ("Una cadena necesita un color propio que se reconozca en una bolsa o un letrero" if escala != "barrio"
                   else "Vale para barrio, pero piensa si se reconoceria"))
        if escala in ("cadena", "premium") and s_ac < 0.3:
            fallos.append(f"escala {escala}: el acento {pal['accent']} esta apagado; el color de firma tiene que reconocerse")

    tipo = ficha.get("tipografia", {})
    disp = str(tipo.get("display", "")).strip()
    if not disp or not str(tipo.get("texto", "")).strip():
        fallos.append("tipografia: faltan display y/o texto")
    elif disp.lower() in DISPLAY_GENERICA:
        fallos.append(f"tipografia: '{disp}' no tiene caracter para titulares (sirve para texto)")
    if disp:
        url, no_existen = url_fuentes(tipo)
        if no_existen:
            fallos.append(f"tipografia: no existe en Google Fonts (nombre exacto): {', '.join(no_existen)}")
        extra["fuentes_url"] = url

    pieza = ficha.get("pieza_principal", {})
    tp = str(pieza.get("tipo", "")).strip().lower()
    if tp not in TIPOS_PIEZA:
        fallos.append(f"pieza_principal.tipo debe ser uno de: {', '.join(sorted(TIPOS_PIEZA))}")
    elif compra in ("espacio", "experiencia") and int(ficha.get("nivel", 4) or 4) >= 4 and tp not in PIEZA_VIVA:
        fallos.append(f"nivel 4 con '{compra}' pide una pieza viva del sitio ({', '.join(sorted(PIEZA_VIVA))}); '{tp}' es de nivel 2-3")
    elif compra == "producto" and tp in ("webgl", "canvas", "tipografia", "ilustracion"):
        fallos.append(f"se compra el PRODUCTO: la pieza principal tiene que ensenarlo (foto, video-scroll o 3d del producto), "
                      f"no un efecto '{tp}' que lo tape. El efecto puede ir de fondo, nunca en lugar del producto")
    if len(str(pieza.get("como", ""))) < 20:
        fallos.append("pieza_principal.como: explica que hace y con que")

    secs = [s for s in ficha.get("secciones", []) if str(s.get("id", "")).strip()]
    if len(secs) < 3:
        fallos.append("hacen falta al menos 3 secciones con id, patron y proposito")
    patrones = [normal(str(s.get("patron", ""))) for s in secs]
    if any(not p for p in patrones):
        fallos.append("cada seccion necesita su 'patron' (como se compone)")
    repetidos = {p for p in patrones if p and patrones.count(p) >= 3}
    if repetidos:
        avisos.append(f"3+ secciones con el mismo patron ({', '.join(repetidos)}): huele a plantilla")
    if sum(1 for p in patrones if re.search(r"tarjeta|card|grid|rejilla", p)) >= max(3, len(patrones) // 2 + 1):
        avisos.append("casi todo son tarjetas/rejillas: varia la composicion")

    huellas = {}
    for f in ficha.get("fotos", []):
        arch = str(f.get("archivo", "")).strip()
        if not arch or arch.endswith("/"):
            continue
        ruta = (carpeta / arch).resolve()
        if not ruta.exists():
            fallos.append(f"foto {arch}: no existe en la carpeta")
            continue
        info = analizar_foto(ruta)
        if not info.get("ok"):
            fallos.append(f"foto {arch}: no se puede abrir")
            continue
        if info["huella"] in huellas:
            fallos.append(f"foto {arch} repetida (igual que {huellas[info['huella']]})")
        huellas[info["huella"]] = arch
        oscuro = rgb.get("bg") and luminancia(rgb["bg"]) < 0.2
        if info.get("fondo_blanco") and oscuro:
            fallos.append(f"foto {arch}: fondo blanco de catalogo sobre una web oscura")
        minimo = 1600 if str(f.get("uso", "")).lower() in ("portada", "hero", "fondo") else 900
        if info.get("ancho", 0) < minimo:
            avisos.append(f"foto {arch}: {info.get('ancho')}px de ancho; para '{f.get('uso')}' conviene >= {minimo}px")
        if len(str(f.get("que_se_ve", ""))) < 10:
            avisos.append(f"foto {arch}: describe 'que_se_ve' (el revisor lo compara con lo que ve InternVL)")
    if not huellas and tp in ("foto", "video-scroll"):
        fallos.append("la pieza principal usa foto/video pero ficha.fotos esta vacia")

    ult = memoria()[-4:]
    if not malos:
        for m in ult:
            if m.get("proyecto") == carpeta.name:
                continue
            if disp and str(m.get("display", "")).lower() == disp.lower():
                fallos.append(f"repite la tipografia display de {m.get('proyecto')} ({disp})")
            acc = hex_rgb(m.get("accent"))
            if acc and distancia(acc, rgb["accent"]) < 45:
                fallos.append(f"acento casi igual al de {m.get('proyecto')} ({m.get('accent')})")
            comunes = set(patrones) & set(m.get("patrones", []))
            if patrones and len(comunes) >= max(2, len(patrones) * 0.6):
                avisos.append(f"composicion muy parecida a {m.get('proyecto')}: {', '.join(sorted(comunes))}")
        if len(ult) >= 2 and all(m.get("pieza") == tp for m in ult[-2:]):
            avisos.append(f"las 2 ultimas webs tambien tenian pieza '{tp}'")
    return fallos, avisos, extra


def tokens_css(ficha: dict, url_fuentes_ok: str) -> str:
    p, t = ficha["paleta"], ficha["tipografia"]
    fam = lambda n, gen: f"'{n}', {gen}" if n else gen  # noqa: E731
    return f"""/* 00_tokens.css - GENERADO por estudio.py validar desde ficha.json - no editar a mano */
/* fuentes: {url_fuentes_ok} */
:root {{
  --bg: {p['bg']}; --surface: {p['surface']}; --ink: {p['ink']}; --muted: {p['muted']};
  --accent: {p['accent']}; --accent-ink: {p['accent_ink']};
  --font-display: {fam(t.get('display'), 'serif')};
  --font-text: {fam(t.get('texto'), 'system-ui, sans-serif')};
  --font-detalle: {fam(t.get('detalle') or t.get('texto'), 'ui-monospace, monospace')};
  --max: 1240px; --gutter: clamp(20px, 5vw, 64px);
  color-scheme: {'dark' if luminancia(hex_rgb(p['bg'])) < 0.2 else 'light'};
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{ margin: 0; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--font-text); -webkit-font-smoothing: antialiased; }}
img, video, canvas, svg {{ display: block; max-width: 100%; }}
"""


def orden_validar(a) -> int:
    carpeta = Path(a.carpeta).resolve()
    est = dir_estudio(carpeta)
    ficha = leer_json(est / "ficha.json")
    if not ficha:
        print(f"[ESTUDIO] No hay ficha en {est}. Primero: estudio.py ficha <carpeta> \"<pedido>\"")
        return 2
    fallos, avisos, extra = validar_ficha(carpeta, ficha)
    sin_leer = faltan_skills(skills_obligatorias(ficha))
    if sin_leer:
        fallos.append("no has leido las skills de esta fase (lee en 1 lote y vuelve a validar): "
                      + " · ".join(ruta_skill(s) for s in sin_leer))
    extra["skills_leidas"] = sorted(set(skills_obligatorias(ficha)) - set(sin_leer))
    for x in avisos:
        print(f"[AVISO] {x}")
    if fallos:
        for x in fallos:
            print(f"[FALLO] {x}")
        print(f"[ESTUDIO] Ficha NO valida ({len(fallos)} fallos). Corrige ficha.json y vuelve a validar.")
        return 1
    (est / "estilos").mkdir(parents=True, exist_ok=True)
    (est / "estilos" / "00_tokens.css").write_text(tokens_css(ficha, extra.get("fuentes_url", "")), encoding="utf-8")
    escribir_json(est / "ficha_validada.json", {"fecha": time.strftime("%Y-%m-%d %H:%M"), **extra,
                                                "huella": hashlib.md5(json.dumps(ficha, sort_keys=True).encode()).hexdigest()})
    p, t, pz = ficha["paleta"], ficha["tipografia"], ficha["pieza_principal"]
    print("[ESTUDIO] FICHA VALIDA. Ensenale ESTO al usuario y espera su 'vale' antes de construir:")
    c = ficha["criterio"]
    print(f"  Que compra el cliente: {c['que_compra']} ({c['por_que']}) · escala {c['escala']}")
    print(f"  Primer pantallazo: {c['primer_pantallazo']}")
    if c.get("que_sobra"):
        print(f"  Lo que sobra: {c['que_sobra']}")
    print(f"  Concepto: {ficha['concepto']}")
    print("  Referencias: " + " | ".join(f"{r['quien']} ({r['que_tomo']})" for r in ficha["referencias"] if r.get("quien")))
    print(f"  Paleta: fondo {p['bg']} · superficie {p['surface']} · texto {p['ink']} · acento {p['accent']}")
    print(f"  Tipografia: {t['display']} (titulares) + {t['texto']} (texto)" + (f" + {t['detalle']}" if t.get("detalle") else ""))
    print(f"  Pieza principal: {pz['tipo']} -> {pz['como']}")
    print("  Secciones: " + " · ".join(f"{s['id']} ({s.get('patron', '')})" for s in ficha["secciones"]))
    print(f"  Fotos: {len([f for f in ficha.get('fotos', []) if str(f.get('archivo', '')).strip('/').count('/')])}")
    print(GUIA_CONSTRUIR)
    print("PARA CONSTRUIR, lee: " + " · ".join(ruta_skill(s) for s in SKILLS_CONSTRUIR if (SKILLS / s / "SKILL.md").exists()))
    return 0


# ---------------------------------------------------------------- 5. picar (Qwen)

SISTEMA_QWEN = """Eres maquetador HTML senior. La directora de arte ya escribio TODO el CSS. Tu escribes SOLO el HTML de UNA seccion.
Devuelve SOLO esto, sin ``` ni explicaciones:
<section id="ID" class="..."> ... </section>
Reglas (las comprueba un programa; si fallas, repites):
- Usa SOLO clases de la lista CLASES. Ninguna otra.
- Prohibido: atributo style, <style>, <script>, <html>, <head>, <body>, iconos de librerias, URLs inventadas.
- TEXTOS: copialos EXACTOS. No inventes cifras, precios, telefonos, emails ni nombres. Nada de lorem ni [corchetes].
- Imagenes: solo las de FOTOS, con su src exacto y loading="lazy". alt = el que venga en TEXTOS para esa foto; si no hay, el de FOTOS.
- Cada texto va en el sitio que dice su nombre (titulo -> h2/h3, texto -> p, boton -> button, alt -> alt de la foto).
- Enlaces internos href="#id". Un <h2> como titulo de la seccion (h1 solo si es la portada). Listas con ul/li.
  Formularios con <label> en cada campo.
- Sigue la ESTRUCTURA al pie de la letra (es el orden y anidado de los elementos)."""

VACIOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Inspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.clases, self.tags, self.textos, self.pila, self.errores = set(), [], [], [], []
        self.srcs, self.estilos, self.hrefs, self.ids = [], 0, [], []
        self.atributos: list[str] = []  # alt, aria-label, title, value, data-*: textos que no se ven pero cuentan
        self.alts: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.tags.append(tag)
        self.atributos += [str(v) for k, v in d.items() if v and (k in ("alt", "title", "aria-label", "value", "placeholder", "content") or k.startswith("data-"))]
        if tag == "img" and d.get("alt"):
            self.alts.append(d["alt"])
        self.clases.update((d.get("class") or "").split())
        if "style" in d:
            self.estilos += 1
        if d.get("id"):
            self.ids.append(d["id"])
        if tag in ("img", "source", "video") and d.get("src"):
            self.srcs.append(d["src"])
        if tag == "a" and d.get("href"):
            self.hrefs.append(d["href"])
        if tag not in VACIOS:
            self.pila.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VACIOS and self.pila and self.pila[-1] == tag:
            self.pila.pop()

    def handle_endtag(self, tag):
        if tag in VACIOS:
            return
        if tag in self.pila:
            while self.pila and self.pila[-1] != tag:
                self.errores.append(f"<{self.pila.pop()}> sin cerrar")
            self.pila.pop()
        else:
            self.errores.append(f"</{tag}> sobra")

    def handle_data(self, data):
        if data.strip():
            self.textos.append(data.strip())


def clases_permitidas(est: Path) -> tuple[set[str], str]:
    clases, guia = set(), []
    for css in sorted((est / "estilos").glob("*.css")):
        t = css.read_text(encoding="utf-8")
        guia += [g.strip() for g in re.findall(r"/\*\s*qwen:\s*(.*?)\*/", t, re.S)]
        t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
        t = re.sub(r"url\([^)]*\)|\"[^\"]*\"|'[^']*'", "", t)
        for selector in re.findall(r"([^{}]+)\{", t):
            clases.update(re.findall(r"\.(-?[a-zA-Z_][\w-]*)", selector))
    return clases, "\n".join(f"- {g}" for g in guia)


def comprobar_qwen(frag: str, sec: dict, clases_ok: set[str], fotos: list[str], base_datos: str) -> str:
    if not re.match(rf'\s*<section\b[^>]*\bid=["\']{re.escape(sec["id"])}["\']', frag):
        return f'debe empezar por <section id="{sec["id"]}">'
    if not frag.rstrip().endswith("</section>"):
        return "debe terminar en </section>"
    ins = Inspector()
    try:
        ins.feed(frag)
        ins.close()
    except Exception as e:
        return f"HTML roto: {e}"
    if ins.errores or ins.pila:
        return "etiquetas mal cerradas: " + ", ".join((ins.errores + [f"<{t}> sin cerrar" for t in ins.pila])[:4])
    prohibidas = {t for t in ins.tags if t in ("style", "script", "html", "head", "body", "link", "iframe")}
    if prohibidas:
        return f"etiquetas prohibidas: {', '.join(sorted(prohibidas))}"
    if ins.estilos:
        return "hay atributos style=: quitalos (el CSS ya esta hecho; usa clases de la lista)"
    raras = sorted(ins.clases - clases_ok)
    if raras:
        return f"clases que NO existen en el CSS: {', '.join(raras[:8])}. Usa solo las de CLASES"
    malas = [s for s in ins.srcs if s not in fotos]
    if malas:
        return f"imagenes que no estan en FOTOS: {', '.join(malas[:3])}"
    externos = [h for h in ins.hrefs if re.match(r"https?://", h) and h not in base_datos]
    if externos:
        return f"enlaces inventados: {', '.join(externos[:3])}"
    texto = " ".join(ins.textos)
    if re.search(r"lorem|ipsum|\[[^\]]{2,40}\](?<!PENDIENTE\])", texto, re.I) and "[PENDIENTE]" not in texto:
        return "texto de relleno: usa solo los TEXTOS"
    base = re.sub(r"\s", "", base_datos)
    inventadas = [n for n in re.findall(r"\d[\d.,:]*", texto) if re.sub(r"\s", "", n).rstrip(".,:") not in base]
    if inventadas:
        return f"cifras que no estan en TEXTOS (inventadas): {', '.join(inventadas[:5])}"
    # 15/11: los textos pueden ir en lo visible O en un atributo (alt, data-...). Antes solo se miraba lo visible y se
    # rechazaban secciones correctas (panaderia: descubrir y bolleria estaban bien).
    norm = normal(texto + " " + " ".join(ins.atributos))
    alts = [set(re.findall(r"\w+", normal(a))) for a in ins.alts]

    def es_otro_alt(t: str) -> bool:  # la misma foto descrita con otras palabras (alt de la ficha vs alt de TEXTOS)
        p = set(re.findall(r"\w+", normal(t)))
        return bool(p) and any(len(p & a) / len(p) >= 0.6 for a in alts)

    faltan = [t for t in aplanar(sec.get("textos")) if len(t.split()) >= 3 and normal(t) not in norm and not es_otro_alt(t)]
    if faltan:
        return "faltan textos: " + " | ".join(f"'{t[:50]}'" for t in faltan[:3])
    return ""


def orden_picar(a) -> int:
    from ollama_comun import ensure_ollama_service, generar_qwen

    carpeta = Path(a.carpeta).resolve()
    est = dir_estudio(carpeta)
    spec = leer_json(est / "secciones.json")
    ficha = leer_json(est / "ficha.json", {}) or {}
    if not spec or not spec.get("secciones"):
        print(f"[PICAR] Falta {est / 'secciones.json'} (ver estudio.py ficha para el formato).")
        return 2
    if not (est / "ficha_validada.json").exists():
        print("[PICAR] La ficha no esta validada: estudio.py validar <carpeta> (y el 'vale' del usuario).")
        return 2
    clases_ok, guia = clases_permitidas(est)
    if len(clases_ok) < 5:
        print("[PICAR] Casi no hay clases en estudio/estilos/*.css: escribe primero el sistema (10_base.css, 20_...).")
        return 2
    qwen = [s for s in spec["secciones"] if s.get("autor", "qwen") == "qwen"]
    solo = {x.strip() for x in a.solo.split(",") if x.strip()}
    if solo:
        qwen = [s for s in qwen if s["id"] in solo]
    if not qwen:
        print("[PICAR] No hay secciones de Qwen que picar.")
        return 0
    if not ensure_ollama_service():
        print("[PICAR] FRENO: Ollama no responde. Avisa al usuario (no lo hagas desde la nube).")
        return 1
    coder, _ = modelos()
    (est / "secciones").mkdir(exist_ok=True)
    datos = json.dumps(ficha.get("datos_reales", {}), ensure_ascii=False)
    pendientes = []
    for sec in qwen:
        sueltas = [k for k, v in (sec.get("textos") or {}).items()
                   if isinstance(v, list) and any(isinstance(x, list) and len(x) >= 3 for x in v)]
        if sueltas:
            print(f"[PICAR] AVISO #{sec['id']}: textos en listas sin nombre ({', '.join(sueltas)}). Qwen se lia: "
                  'usa objetos {"titulo": ..., "texto": ..., "boton": ..., "alt": ...}.', flush=True)
        fotos = [str(f) for f in sec.get("fotos", [])]
        descr = {str(f.get("archivo")): f.get("que_se_ve", "") for f in ficha.get("fotos", [])}
        base_datos = json.dumps(sec, ensure_ascii=False) + datos
        error, frag = "", ""
        for intento in range(1, 4):
            prompt = (f"ID: {sec['id']}{' (portada: usa h1)' if sec is spec['secciones'][0] else ''}\n"
                      f"ESTRUCTURA: {sec.get('estructura', '')}\n"
                      f"TEXTOS:\n{json.dumps(sec.get('textos', {}), ensure_ascii=False, indent=1)}\n"
                      f"FOTOS: {json.dumps([{'src': f, 'alt': descr.get(f, '')} for f in fotos], ensure_ascii=False)}\n"
                      f"CLASES: {' '.join('.' + c for c in sorted(clases_ok))}\n"
                      + (f"GUIA DE CLASES:\n{guia}\n" if guia else ""))
            if error:
                prompt += f"\nTu intento anterior fallo por: {error}. Corrige SOLO eso."
            t0 = time.time()
            texto, cortado = generar_qwen(prompt, coder, sistema=SISTEMA_QWEN, num_predict=3000, num_ctx=8192, temperatura=0.2)
            frag = re.sub(r"^```[a-z]*\s*|\s*```$", "", texto.strip(), flags=re.I | re.M).strip()
            error = "la respuesta se corto: hazla mas compacta" if cortado else comprobar_qwen(frag, sec, clases_ok, fotos, base_datos)
            print(f"[PICAR] #{sec['id']} intento {intento}: {round(time.time() - t0)} s · {'OK' if not error else error}", flush=True)
            if not error:
                break
        if error:
            pendientes.append(f"- #{sec['id']}: {error}. Mejora 'estructura'/'textos' en secciones.json y relanza "
                              f"--solo {sec['id']}, o escribela tu en estudio/secciones/{sec['id']}.html y pon \"autor\": \"nova\".")
            (est / "secciones" / f"{sec['id']}.qwen_fallido.html").write_text(frag, encoding="utf-8")
        else:
            (est / "secciones" / f"{sec['id']}.html").write_text(frag + "\n", encoding="utf-8")
    if pendientes:
        (est / "pendientes.md").write_text("# Secciones que Qwen no pudo\n" + "\n".join(pendientes) + "\n", encoding="utf-8")
        print(f"[PICAR] FRENO en {len(pendientes)} seccion(es): estudio/pendientes.md")
        return 1
    print("[PICAR] Todas las secciones de Qwen OK. Ahora: estudio.py montar <carpeta>")
    return 0


# ---------------------------------------------------------------- 6. montar


def fotos_kit(rutas: list[str], ficha: dict) -> list[dict]:
    descr = {str(f.get("archivo")): f.get("que_se_ve", "") for f in ficha.get("fotos", [])}
    return [{"url": r, "url_movil": r, "src": r, "src_movil": r, "alt": descr.get(r, ""), "credito": ""} for r in rutas]


def orden_montar(a) -> int:
    import efectos

    carpeta = Path(a.carpeta).resolve()
    est = dir_estudio(carpeta)
    spec = leer_json(est / "secciones.json") or {}
    ficha = leer_json(est / "ficha.json", {}) or {}
    validada = leer_json(est / "ficha_validada.json", {}) or {}
    cuerpo, faltan, largos, usa_kit = [], [], [], False
    for sec in spec.get("secciones", []):
        sid, autor = sec["id"], sec.get("autor", "qwen")
        if autor == "efecto":
            if sec.get("efecto") not in efectos.BLOQUES:
                faltan.append(f"#{sid}: efecto '{sec.get('efecto')}' no existe ({', '.join(efectos.BLOQUES)})")
                continue
            cuerpo.append(efectos.bloque(sec["efecto"], sid, sec.get("datos") or {}, fotos_kit(sec.get("fotos", []), ficha)))
            usa_kit = True
            continue
        ruta = est / "secciones" / f"{sid}.html"
        if not ruta.exists():
            faltan.append(f"#{sid}: falta estudio/secciones/{sid}.html ({'picala con estudio.py picar' if autor == 'qwen' else 'escribela tu'})")
            continue
        if autor == "nova" and lineas(ruta) > MAX_LINEAS_NOVA:
            largos.append(f"{ruta.name} ({lineas(ruta)} lineas)")
        cuerpo.append(ruta.read_text(encoding="utf-8").strip())
    if faltan:
        for f in faltan:
            print(f"[MONTAR] {f}")
        return 1
    estilos = sorted((est / "estilos").glob("*.css"))
    for css in estilos:
        if css.name != "00_tokens.css" and lineas(css) > MAX_LINEAS_NOVA:
            largos.append(f"{css.name} ({lineas(css)} lineas)")
    sin_leer = faltan_skills(SKILLS_CONSTRUIR)
    if sin_leer:
        print("[MONTAR] AVISO: construiste sin leer las skills de movimiento: " + " · ".join(ruta_skill(s) for s in sin_leer))
    if largos:
        print(f"[MONTAR] AVISO: archivos de mas de {MAX_LINEAS_NOVA} lineas (el hook no deja escribirlos de una vez): {', '.join(largos)}")
    todo_css = "\n\n".join(f"/* ===== {c.name} ===== */\n" + c.read_text(encoding="utf-8") for c in estilos)
    html_cuerpo = "\n\n".join(cuerpo)
    if usa_kit or "data-efecto=" in html_cuerpo:
        todo_css += "\n\n/* ===== kit de efectos (biblioteca) ===== */\n" + efectos.EFECTOS_CSS
    (carpeta / "estilos.css").write_text(todo_css, encoding="utf-8")
    cdn = leer_json(BIBLIOTECA / "cdn.json", {}) or {}
    cabeza, pie = [], []
    for h in ficha.get("herramientas", []):
        info = cdn.get(str(h).lower())
        if isinstance(info, dict):
            if info.get("css"):
                cabeza.append(f'<link rel="stylesheet" href="{html.escape(info["css"])}">')
            for k in ("js", "scrolltrigger"):
                if info.get(k):
                    pie.append(f'<script src="{html.escape(info[k])}"></script>')
    if (est / "extra.js").exists():
        (carpeta / "app.js").write_text((est / "extra.js").read_text(encoding="utf-8"), encoding="utf-8")
        pie.append('<script src="app.js" defer></script>')
    if usa_kit or "data-efecto=" in html_cuerpo:
        pie.append(efectos.EFECTOS_JS)
    titulo = html.escape(ficha.get("datos_reales", {}).get("nombre") or ficha.get("pedido", "Web")[:70])
    fuentes = validada.get("fuentes_url", "")
    pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{html.escape(str(ficha.get('concepto', ''))[:155])}">
{'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' if fuentes else ''}
{f'<link rel="stylesheet" href="{html.escape(fuentes)}">' if fuentes else ''}
{chr(10).join(cabeza)}
<link rel="stylesheet" href="estilos.css">
</head>
<body>
<script>document.documentElement.classList.add('js');</script>
{html_cuerpo}
{chr(10).join(pie)}
</body>
</html>
"""
    (carpeta / "index.html").write_text(pagina, encoding="utf-8")
    q = sum(lineas(est / "secciones" / f"{s['id']}.html") for s in spec.get("secciones", []) if s.get("autor", "qwen") == "qwen")
    n = sum(lineas(est / "secciones" / f"{s['id']}.html") for s in spec.get("secciones", []) if s.get("autor") == "nova")
    n += sum(lineas(c) for c in estilos if c.name != "00_tokens.css") + lineas(est / "extra.js")
    total = max(q + n, 1)
    print(f"[MONTAR] index.html + estilos.css en {carpeta}. Lineas: Qwen {q} ({q * 100 // total} %) · Nova {n} ({n * 100 // total} %)")
    print("[MONTAR] Ahora: estudio.py revisar <carpeta>")
    return 0


# ---------------------------------------------------------------- 7. revisar

JS_MEDIR = r"""() => {
  const vw = innerWidth, vh = innerHeight, sy = scrollY;
  const nombre = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList[0] ? '.' + e.classList[0] : '');
  const opac = (e) => { let o = 1; for (let p = e; p && p !== document.documentElement; p = p.parentElement) o *= parseFloat(getComputedStyle(p).opacity); return o; };
  const todos = [...document.body.querySelectorAll('*')];
  const contenido = todos.filter(e => {
    if (!e.matches('h1,h2,h3,h4,p,li,a,button,img,video,canvas,svg,figure,blockquote,label,input,select,textarea,picture,iframe')) return false;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 4 && r.height > 4 && cs.visibility !== 'hidden' && cs.display !== 'none';
  });
  const invisibles = contenido.filter(e => (e.innerText || '').trim().length > 2 && opac(e) < 0.1).slice(0, 6).map(nombre);
  // tramos cubiertos de la pagina (los sticky cubren todo su padre: secciones de scroll largo)
  const tramos = [];
  for (const e of contenido) { const r = e.getBoundingClientRect(); tramos.push([r.top + sy, r.bottom + sy, nombre(e)]); }
  for (const e of todos) {
    const cs = getComputedStyle(e);
    if (cs.position === 'sticky' && e.parentElement) { const r = e.parentElement.getBoundingClientRect(); tramos.push([r.top + sy, r.bottom + sy, nombre(e)]); }
    if (cs.backgroundImage && cs.backgroundImage !== 'none' && !cs.backgroundImage.startsWith('linear') && !cs.backgroundImage.startsWith('radial')) {
      const r = e.getBoundingClientRect(); if (r.height > 40) tramos.push([r.top + sy, r.bottom + sy, nombre(e)]);
    }
  }
  tramos.sort((a, b) => a[0] - b[0]);
  const alto = document.documentElement.scrollHeight, huecos = [];
  let fin = 0, antes = 'inicio';
  for (const [a, b, n] of tramos) { if (a - fin > 0.6 * vh) huecos.push([Math.round(a - fin), antes, n]); if (b > fin) { fin = b; antes = n; } }
  if (alto - fin > 0.6 * vh) huecos.push([Math.round(alto - fin), antes, 'final de la pagina']);
  // colores pintados
  const colores = {};
  for (const e of todos) {
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(e);
    const tieneTexto = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    for (const c of [tieneTexto ? cs.color : null, cs.backgroundColor, cs.borderTopWidth !== '0px' ? cs.borderTopColor : null]) {
      if (!c || c === 'rgba(0, 0, 0, 0)' || c === 'transparent') continue;
      (colores[c] = colores[c] || []).length < 2 && colores[c].push(nombre(e));
    }
  }
  const fotos = [...document.images].filter(i => i.complete && i.naturalWidth).map(i => {
    const r = i.getBoundingClientRect(); return { src: i.getAttribute('src'), nat: i.naturalWidth, vis: Math.round(r.width * devicePixelRatio) };
  });
  const videos = [...document.querySelectorAll('video')].map(v => ({ src: v.currentSrc, nat: v.videoWidth, vis: Math.round(v.getBoundingClientRect().width * devicePixelRatio) }));
  const fuentes = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, ''));
  const izq = [...document.querySelectorAll('body > section, body > main > section, body > header, body > footer')].map(s => {
    const t = [...s.querySelectorAll('h1,h2,h3,p')].filter(x => x.getBoundingClientRect().width > 0)[0];
    return t ? [nombre(s), Math.round(t.getBoundingClientRect().left)] : null; }).filter(Boolean);
  return { invisibles, huecos: huecos.slice(0, 6), colores, fotos, videos, fuentes, izq, ancho: document.documentElement.scrollWidth, vw, texto: document.body.innerText };
}"""


JS_PORTADA = r"""() => {
  // primer pantallazo: cuanto ocupa la foto/video mas grande (o un fondo con imagen) dentro de la ventana
  const vw = innerWidth, vh = innerHeight; let mejor = 0, quien = '';
  const visible = (r) => Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
  for (const e of document.querySelectorAll('img, video, picture, [style*="background-image"], header, section, div')) {
    const cs = getComputedStyle(e);
    const esMedia = e.matches('img, video, picture') || (cs.backgroundImage && cs.backgroundImage.includes('url('));
    if (!esMedia) continue;
    const a = visible(e.getBoundingClientRect()) / (vw * vh);
    if (a > mejor) { mejor = a; quien = (e.getAttribute('src') || e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : '')); }
  }
  return { area: Math.round(mejor * 100), quien };
}"""

SIN_TILDE = {
    "manana": "mañana", "bolleria": "bollería", "panaderia": "panadería", "pasteleria": "pastelería",
    "cafeteria": "cafetería", "galeria": "galería", "cumpleanos": "cumpleaños", "anos": "años", "ano": "año",
    "espanol": "español", "espana": "España", "tambien": "también", "aqui": "aquí", "alli": "allí", "dias": "días",
    "dia": "día", "envio": "envío", "telefono": "teléfono", "menu": "menú", "pagina": "página", "cafe": "café",
    "azucar": "azúcar", "recien": "recién", "rustico": "rústico", "clasico": "clásico", "clasicas": "clásicas",
    "clasicos": "clásicos", "unico": "único", "unica": "única", "numero": "número", "rapido": "rápido",
    "facil": "fácil", "ademas": "además", "despues": "después", "segun": "según", "catalogo": "catálogo",
    "pequeno": "pequeño", "pequena": "pequeña", "diseno": "diseño", "senor": "señor", "nino": "niño",
    "acompanar": "acompañar", "acompanado": "acompañado", "sabado": "sábado", "miercoles": "miércoles",
    "reunion": "reunión", "maquinas": "máquinas", "maquina": "máquina", "musica": "música", "camara": "cámara",
}


def faltas_ortografia(texto: str) -> list[str]:
    """Tildes, eñes y signos de apertura que faltan en el texto VISIBLE de la web."""
    malas = []
    for w in re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]+", texto):
        lw = w.lower()
        if lw in SIN_TILDE:
            malas.append(f"{w} -> {SIN_TILDE[lw]}")
        elif len(lw) > 5 and lw.endswith("cion"):
            malas.append(f"{w} -> {w[:-4]}ción")
    for linea in texto.splitlines():
        if linea.count("?") > linea.count("¿"):
            malas.append(f"falta '¿' en: {linea.strip()[:40]}")
        if linea.count("!") > linea.count("¡"):
            malas.append(f"falta '¡' en: {linea.strip()[:40]}")
    return list(dict.fromkeys(malas))


JS_TEXTOS = r"""() => {
  const out = [];
  for (const e of document.body.querySelectorAll('*')) {
    if (out.length >= 160) break;
    if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1)) continue;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (r.width < 8 || r.height < 8 || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.5) continue;
    out.push({ x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, color: cs.color,
               size: parseFloat(cs.fontSize), peso: parseInt(cs.fontWeight) || 400,
               nombre: e.tagName.toLowerCase() + (e.classList[0] ? '.' + e.classList[0] : ''),
               texto: e.textContent.trim().slice(0, 28) });
  }
  return out;
}"""


def contraste_pixeles(captura: Path, textos: list[dict]) -> list[str]:
    """Para cada texto: separa los pixeles que NO son del color del texto (el fondo real) y mide el contraste."""
    from PIL import Image

    im = Image.open(captura).convert("RGB")
    malos = []
    for t in textos:
        rgb = css_rgb(t["color"])
        if not rgb:
            continue
        caja = (max(0, int(t["x"])), max(0, int(t["y"])), min(im.width, int(t["x"] + t["w"])), min(im.height, int(t["y"] + t["h"])))
        if caja[2] - caja[0] < 4 or caja[3] - caja[1] < 4:
            continue
        trozo = im.crop(caja)
        trozo.thumbnail((160, 60))
        px = list(trozo.get_flattened_data() if hasattr(trozo, "get_flattened_data") else trozo.getdata())
        fondo = [p for p in px if distancia(p, rgb) > 60]
        if len(fondo) < len(px) * 0.25:
            continue
        mediana = tuple(sorted(c[i] for c in fondo)[len(fondo) // 2] for i in range(3))
        ratio = contraste(rgb, mediana)
        grande = t["size"] >= 24 or (t["size"] >= 18.6 and t["peso"] >= 700)
        if ratio < (3 if grande else 4.5) - 0.2:
            malos.append(f"{t['nombre']} \"{t['texto']}\" {ratio:.1f}:1")
    return malos[:8]


def preguntar_vl(ruta: Path, modelo: str) -> str:
    datos = {"model": modelo, "stream": False, "keep_alive": "5m",
             "messages": [{"role": "user", "images": [base64.b64encode(ruta.read_bytes()).decode()],
                           "content": "Describe en una frase corta en espanol que se ve en la foto. Despues, en otra linea: "
                                      "TEXTO: SI o NO (hay letras, carteles, logotipos o marcas de agua visibles)."}],
             "options": {"temperature": 0.1, "num_predict": 120}}
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=json.dumps(datos).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["message"]["content"].strip()


def recorrer(navegador, url: str, ancho: int, alto: int, destino: Path, prefijo: str) -> tuple[list[Path], dict, list[str]]:
    pagina = navegador.new_page(viewport={"width": ancho, "height": alto})
    errores: list[str] = []
    pagina.on("pageerror", lambda e: errores.append(str(e)[:140]))
    pagina.on("requestfailed", lambda r: errores.append(f"no carga {r.url[-80:]}") if r.resource_type in ("image", "media", "font", "script", "stylesheet") else None)
    pagina.goto(url, wait_until="load", timeout=30000)
    pagina.wait_for_timeout(1200)
    portada = pagina.evaluate(JS_PORTADA)
    capturas, y, n = [], 0, 0
    total = pagina.evaluate("document.documentElement.scrollHeight")
    while y < total and n < 30:
        pagina.evaluate(f"window.scrollTo(0, {y})")
        pagina.wait_for_timeout(750)
        ruta = destino / f"{prefijo}_{n:02d}.png"
        pagina.screenshot(path=str(ruta))
        capturas.append(ruta)
        y += alto
        n += 1
        total = pagina.evaluate("document.documentElement.scrollHeight")
    medida = pagina.evaluate(JS_MEDIR)
    medida["portada"] = portada
    try:  # contraste REAL: color del texto contra los pixeles que tiene detras (foto, degradado o color)
        pagina.evaluate("window.scrollTo(0, 0)")
        pagina.wait_for_timeout(500)
        completa = destino / f"{prefijo}_completa.png"
        pagina.screenshot(path=str(completa), full_page=True)
        medida["ilegibles"] = contraste_pixeles(completa, pagina.evaluate(JS_TEXTOS))
        completa.unlink(missing_ok=True)
    except Exception as e:
        medida["ilegibles"] = []
        errores.append(f"no se pudo medir el contraste ({type(e).__name__})")
    try:  # el verificador de siempre (contraste real, textos cortados, cajas vacias, relleno), ya con todo a la vista
        import nova_pipeline_local as NPL

        ids = pagina.evaluate("[...document.querySelectorAll('body > [id], main > [id]')].map(e => '#' + e.id)")
        medida["dom"] = NPL.problemas_dom(pagina.evaluate(NPL.JS_CHEQUEO_DOM, ids), prefijo)
    except Exception as e:
        medida["dom"] = []
        errores.append(f"verificador DOM no disponible ({type(e).__name__})")
    pagina.close()
    return capturas, medida, errores


def orden_revisar(a) -> int:
    from playwright.sync_api import sync_playwright

    carpeta = Path(a.carpeta).resolve()
    est = dir_estudio(carpeta)
    ficha = leer_json(est / "ficha.json", {}) or {}
    index = carpeta / "index.html"
    if not index.exists():
        print("[REVISAR] No hay index.html: estudio.py montar <carpeta>")
        return 2
    cap = est / "capturas"
    cap.mkdir(parents=True, exist_ok=True)
    for viejo in cap.glob("*.png"):
        viejo.unlink()
    fallos, avisos = [], []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pc, m_pc, e_pc = recorrer(nav, index.as_uri(), 1280, 800, cap, "pc")
        mv, m_mv, e_mv = recorrer(nav, index.as_uri(), 390, 844, cap, "movil")
        nav.close()
    for vista, m, errs in (("PC 1280", m_pc, e_pc), ("Movil 390", m_mv, e_mv)):
        if m["ancho"] > m["vw"] + 1:
            fallos.append(f"{vista}: la pagina se sale por la derecha ({m['ancho']}px de {m['vw']}px)")
        if m["invisibles"]:
            fallos.append(f"{vista}: contenido que nunca aparece (opacidad 0 tras bajar): {', '.join(m['invisibles'])}")
        for alto, antes, despues in m["huecos"]:
            (fallos if alto > 1.0 * (800 if vista.startswith("PC") else 844) else avisos).append(
                f"{vista}: hueco vacio de {alto}px entre {antes} y {despues}")
        for f in m["fotos"] + m["videos"]:
            if f["nat"] and f["vis"] > f["nat"] * 1.35:
                avisos.append(f"{vista}: {f['src']} se ve pixelada ({f['nat']}px estirada a {f['vis']}px)")
        for e in dict.fromkeys(errs):
            fallos.append(f"{vista}: {e}")
        if m.get("ilegibles"):
            fallos.append(f"{vista}: texto con poco contraste sobre lo que tiene detras (medido en pixeles): {', '.join(m['ilegibles'])}")
        for d in m.get("dom", []):
            # desbordes: ya los mide JS_MEDIR · contraste: el viejo mira el color de fondo, no la foto (falsos fallos)
            if "se salen por la derecha" not in d and "poco contraste" not in d:
                fallos.append(d)
    # colores fuera de lo acordado
    pal = [hex_rgb(v) for v in (ficha.get("paleta") or {}).values() if hex_rgb(v)]
    neones, fuera = [], []
    for c, quien in m_pc["colores"].items():
        rgb = css_rgb(c)
        if not rgb or rgb[3] < 0.35:
            continue
        if es_neon(rgb):
            neones.append(f"{c} en {quien[0]}")
        h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb[:3]))
        if s > 0.3 and pal and min(distancia(rgb, p) for p in pal) > 40:
            fuera.append(f"{c} ({quien[0]})")
    if neones:
        fallos.append("colores neon pintados en la pagina: " + ", ".join(neones[:4]))
    if len(fuera) > 2:
        avisos.append("colores que no son de la paleta de la ficha: " + ", ".join(fuera[:5]))
    tipo = ficha.get("tipografia") or {}
    for fam in (tipo.get("display"), tipo.get("texto")):
        if fam and fam not in m_pc["fuentes"]:
            fallos.append(f"la fuente '{fam}' no llega a cargar (revisa el nombre o --font-display)")
    lados = [x for _, x in m_pc["izq"]]
    if len(lados) >= 3 and max(lados) - min(lados) > 40:
        avisos.append("los textos de las secciones no arrancan en la misma linea a la izquierda: "
                      + ", ".join(f"{n} {x}px" for n, x in m_pc["izq"][:6]) + " (si no es a proposito, unifica el contenedor)")
    # 15/11 criterio del usuario: el primer pantallazo ensena lo que se compra; limpio; sin repetir; bien escrito
    crit = ficha.get("criterio") or {}
    compra = str(crit.get("que_compra", "")).lower()
    port = m_pc.get("portada") or {}
    if compra in ("producto", "espacio", "experiencia") and port.get("area", 0) < 35:
        fallos.append(f"primer pantallazo: lo que compra el cliente ({compra}) no manda: la foto/video mas grande ocupa "
                      f"el {port.get('area', 0)} % de la pantalla ({port.get('quien', 'nada')}). Tiene que verse grande y de cerca")
    faltas = faltas_ortografia(m_pc["texto"])
    if faltas:
        fallos.append(f"ortografia ({len(faltas)}): " + " · ".join(faltas[:8]))
    veces: dict[str, int] = {}
    for f in m_pc["fotos"]:
        if f.get("src"):
            veces[f["src"]] = veces.get(f["src"], 0) + 1
    for src, n in veces.items():
        if n >= 3:
            fallos.append(f"la misma foto sale {n} veces ({src}): cansa y parece que no hay producto")
        elif n == 2:
            avisos.append(f"la foto {src} sale 2 veces")
    codigo = index.read_text(encoding="utf-8", errors="ignore") + ((carpeta / "app.js").read_text(encoding="utf-8", errors="ignore")
                                                                 if (carpeta / "app.js").exists() else "")
    tienda = len(re.findall(r"<(?:button|a)\b[^>]*>\s*\+?\s*(?:Sumar|Añadir|Anadir|Agregar|Comprar|Encargar)", codigo, re.I))
    if compra and compra != "catalogo" and tienda > 6:
        avisos.append(f"{tienda} botones de 'sumar/añadir': parece una tienda online. Si se compra '{compra}', ensena y "
                      "deja UN camino claro para pedir (limpio, que se entienda)")
    for lib, uso in (("gsap", r"gsap\.|ScrollTrigger"), ("lenis", r"new\s+Lenis")):
        if lib in [str(h).lower() for h in ficha.get("herramientas", [])] and not re.search(uso, codigo):
            avisos.append(f"la ficha pide '{lib}' y se carga, pero el codigo no lo usa: quitalo o usalo")
    # datos que no dio el usuario
    try:
        from nova_pipeline_local import RE_EMAIL, RE_PRECIO, RE_TELEFONO
    except Exception:
        sys.path.insert(0, str(AG / "scripts"))
        from nova_pipeline_local import RE_EMAIL, RE_PRECIO, RE_TELEFONO
    base = re.sub(r"\s", "", json.dumps(ficha.get("datos_reales", {}), ensure_ascii=False).lower() + str(ficha.get("pedido", "")).lower())
    inventados = sorted({f"{n} {mm.group(0).strip()}" for n, pat in (("precio", RE_PRECIO), ("telefono", RE_TELEFONO), ("email", RE_EMAIL))
                         for mm in pat.finditer(m_pc["texto"])
                         if re.sub(r"\s", "", mm.group(0).lower()).rstrip(".,;:") not in base})  # "...@gmail.com." fin de frase
    if inventados:
        fallos.append("datos que NO estan en ficha.datos_reales (inventados): " + ", ".join(inventados[:6]))
    # fotos: sin IA (fondo blanco) + InternVL describe lo que ve
    vistas_vl = []
    usadas = sorted({f["src"] for f in m_pc["fotos"] if f["src"] and not re.match(r"https?:|data:", f["src"])})
    descr = {str(f.get("archivo")): f.get("que_se_ve", "") for f in ficha.get("fotos", [])}
    oscuro = (hex_rgb((ficha.get("paleta") or {}).get("bg")) or (0, 0, 0))
    _, vl = modelos()
    vl_ok = not a.sin_vl
    for src in usadas:
        ruta = (carpeta / src).resolve()
        if not ruta.exists():
            continue
        info = analizar_foto(ruta)
        if info.get("fondo_blanco") and luminancia(oscuro) < 0.2:
            fallos.append(f"foto {src}: fondo blanco de catalogo sobre web oscura")
        if vl_ok:
            try:
                r = preguntar_vl(ruta, vl)
                vistas_vl.append(f"- `{src}`: InternVL ve: {r.replace(chr(10), ' / ')}  ·  ficha dice: {descr.get(src, '(sin descripcion)')}")
                if re.search(r"TEXTO:\s*S[IÍ]", r, re.I):
                    avisos.append(f"foto {src}: InternVL ve texto/carteles/logos (mirala: puede ser una marca ajena)")
            except Exception as e:
                vl_ok = False
                avisos.append(f"InternVL no disponible ({type(e).__name__}): fotos sin describir")
    sin_leer = faltan_skills(SKILLS_CIERRE)
    if sin_leer:
        fallos.append("antes de entregar, lee y aplica las skills de cierre (critica, accesibilidad, SEO, rendimiento): "
                      + " · ".join(ruta_skill(s) for s in sin_leer))
    h_pc = hoja(pc, cap / "hoja_pc.jpg", 640, 2, [f"PC {i + 1}" for i in range(len(pc))])
    h_mv = hoja(mv, cap / "hoja_movil.jpg", 260, 5, [f"movil {i + 1}" for i in range(len(mv))])
    estado = "OK" if not fallos else f"CON FALLOS ({len(fallos)})"
    informe = [f"# Revision · {carpeta.name} · {time.strftime('%d/%m/%Y %H:%M')} · {estado}", "",
               "## Fallos (bloquean la entrega)", *(f"- {x}" for x in fallos or ["Ninguno."]), "",
               "## Avisos", *(f"- {x}" for x in avisos or ["Ninguno."]), "",
               "## Fotos (lo que ve InternVL vs lo que dice la ficha)", *(vistas_vl or ["- (sin revisar)"]), "",
               "## Ahora TU, como directora (mira solo estas 2 imagenes)",
               f"- {h_pc}", f"- {h_mv}",
               "- Mira como un CLIENTE que entra por primera vez (la web entra por los ojos, como la comida):",
               f"- ¿En 3 segundos se ve lo que compra ({compra or '?'}) y entran ganas de quedarse? ¿O solo es bonita?",
               "- ¿Esta limpia y se entiende, o hay cajas, botones y efectos que sobran?",
               f"- ¿Parece ESTA marca ({crit.get('escala', '?')}) o una plantilla? ¿El color de firma se reconoceria en una bolsa?",
               "- ¿Las fotos tienen la misma luz y estilo entre si? ¿Alguna se ve casera, vieja o fuera de tono?",
               "- Arregla con cambios pequenos, monta y revisa otra vez (max 3 rondas). Luego ensenaselo al usuario."]
    (est / "revision.md").write_text("\n".join(informe) + "\n", encoding="utf-8")
    for x in fallos:
        print(f"[FALLO] {x}")
    for x in avisos:
        print(f"[AVISO] {x}")
    print(f"[REVISAR] {estado}. Informe: {est / 'revision.md'}")
    print(f"[REVISAR] Mira: {h_pc}  y  {h_mv}")
    if not fallos:
        apuntar_memoria(carpeta, ficha)
    return 0 if not fallos else 1


def apuntar_memoria(carpeta: Path, ficha: dict) -> None:
    mem = [m for m in memoria() if m.get("proyecto") != carpeta.name]
    p, t = ficha.get("paleta") or {}, ficha.get("tipografia") or {}
    mem.append({"fecha": time.strftime("%Y-%m-%d %H:%M"), "proyecto": carpeta.name, "bg": p.get("bg"), "accent": p.get("accent"),
                "display": t.get("display"), "texto": t.get("texto"), "pieza": (ficha.get("pieza_principal") or {}).get("tipo"),
                "patrones": [normal(str(s.get("patron", ""))) for s in ficha.get("secciones", [])]})
    escribir_json(MEMORIA, mem[-30:])


# ---------------------------------------------------------------- herramientas


def orden_herramientas(_a) -> int:
    import efectos

    cdn = leer_json(BIBLIOTECA / "cdn.json", {}) or {}
    print("CAJA DE HERRAMIENTAS (coger SOLO lo que haga falta; ponlo en ficha.herramientas):")
    print("  Librerias CDN (versiones fijas): " + ", ".join(k for k in cdn if not k.startswith("_") and isinstance(cdn[k], dict)))
    print("  Bloques de scroll ya hechos ({\"autor\": \"efecto\", \"efecto\": X, \"datos\": {...}, \"fotos\": [...]}):")
    for nombre in efectos.BLOQUES:
        info = efectos.CATALOGO.get(nombre, {})
        print(f"    - {nombre} ({info.get('intensidad', '')}): datos {json.dumps(info.get('datos', {}), ensure_ascii=False)}")
    print("    Fotos del bloque: rutas de la carpeta en \"fotos\" (assets/...). Un solo efecto espectacular por pagina.")
    print('  Decoradores (atributo en cualquier HTML): data-efecto="titular" | "relleno" | "contador" | "magnetico"')
    print('  Fotos: estudio.py fotos <carpeta> --buscar "dark espresso bar interior" [--n 12]  -> hoja para elegir')
    print("  Video a frames para scroll: skill almacen/skills/scroll-video-ffmpeg-webcodecs (FFmpeg en local)")
    print("  WebGL/shaders: skill almacen/skills/webgl-shaders-postprocessing · 3D: threejs-web-experience")
    print("  Paletas/estilos de la biblioteca (general/paletas.json, general/estilos/): como INSPIRACION, no como molde")
    return 0


# ---------------------------------------------------------------- CLI


def main() -> int:
    ap = argparse.ArgumentParser(description="Estudio web de Nova (directora de arte + Qwen + revisor)")
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("ficha")
    p.add_argument("carpeta")
    p.add_argument("pedido", nargs="?", default="")
    p.add_argument("--forzar", action="store_true")
    p = sub.add_parser("fotos")
    p.add_argument("carpeta")
    p.add_argument("--buscar", default="", help='tema en ingles; varias busquedas con |: "sourdough loaf|bakery oven"')
    p.add_argument("--categoria", default="")
    p.add_argument("--n", type=int, default=12)
    p.add_argument("--semilla", type=int, default=0)
    sub.add_parser("validar").add_argument("carpeta")
    p = sub.add_parser("picar")
    p.add_argument("carpeta")
    p.add_argument("--solo", default="")
    sub.add_parser("montar").add_argument("carpeta")
    p = sub.add_parser("revisar")
    p.add_argument("carpeta")
    p.add_argument("--sin-vl", action="store_true", help="sin InternVL (mas rapido)")
    sub.add_parser("herramientas")
    a = ap.parse_args()
    return {"ficha": orden_ficha, "fotos": orden_fotos, "validar": orden_validar, "picar": orden_picar,
            "montar": orden_montar, "revisar": orden_revisar, "herramientas": orden_herramientas}[a.orden](a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
