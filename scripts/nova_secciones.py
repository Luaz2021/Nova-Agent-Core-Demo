"""
NOVA SECCIONES - Qwen pica una web SECCION A SECCION (como el clonador de Claude), con 8k de contexto (cabe entero en
la GPU de 8 GB) y 3 intentos por seccion con comprobacion. Nova solo escribe el encargo masticado (secciones.json).

    python nova_secciones.py --carpeta <ruta> [--spec secciones.json] [--direccion nova_direccion/direction.json]

secciones.json (lo escribe Nova, MASTICADO: cuanto mas preciso, mejor pica Qwen):
{
  "titulo": "Nombre del sitio · tipo · ciudad",
  "descripcion": "meta description",
  "secciones": [
    {"id": "inicio", "encargo": "Hero: h1 'Entrena sin miramientos', subtitulo '...', boton principal 'Reservar' a #contacto.
                                 Layout: texto a la izquierda, a la derecha un SVG de circulos concentricos con var(--accent)."},
    {"id": "servicios", "encargo": "..."}
  ]
}

Base comun (para que todas las secciones casen): sistema.css de la biblioteca + variables de la direccion sorteada
(paleta, tipografias, escala). Qwen solo usa esas variables y clases (.contenedor, .seccion, .t-display, .t-head,
.t-lead, .boton--principal...). Al final se monta index.html y se pasa el verificador (DOM + InternVL).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

NOVA = Path.home() / ".gemini"
BIBLIOTECA = NOVA / "antigravity" / "almacen" / "biblioteca_web"
sys.path.insert(0, str(NOVA / "nova_core"))
sys.path.insert(0, str(BIBLIOTECA))

CTX = 8192          # cabe entero en la GPU (24k se salia 1,4 GB a la CPU y lo hacia 2-3 veces mas lento)
PREDICT = 3500      # una seccion: HTML + su <style>
INTENTOS = 3

SISTEMA = """Eres maquetador web senior. Escribes UNA sola seccion de una pagina, en HTML + CSS, en espanol de Espana.
Devuelves SOLO este formato, sin explicaciones ni ```:
<section id="ID" class="seccion" aria-labelledby="ID-t"> ... </section>
<style> ... reglas que empiezan SIEMPRE por #ID ... </style>

Reglas:
- NUNCA declares ni cambies variables (nada de --bg: ..., --accent: ...): solo las LEES con var(). Para fondos usa las clases
  .seccion--superficie, .seccion--campo o .seccion--invertida en la <section>.
- Dentro de la <section> va SIEMPRE un <div class="contenedor"> con todo el contenido.
- Usa SOLO estas variables: var(--bg) var(--surface) var(--ink) var(--muted) var(--accent) var(--accent-ink) var(--field)
  var(--field-ink) var(--font-display) var(--font-text) var(--step-small) var(--step-body) var(--step-lead) var(--step-head)
  var(--step-display) var(--radius) var(--gutter) var(--section) var(--max). Nada de colores o fuentes sueltos.
- Clases ya hechas que puedes usar: .contenedor (ancho maximo y margenes), .t-display .t-head .t-lead .t-small .t-eyebrow,
  .boton .boton--principal .boton--secundario, .rejilla-2, .seccion--superficie .seccion--campo .seccion--invertida.
- Un titulo de seccion con id="ID-t" (h1 solo si es la portada; si no, h2).
- Movil primero: debe verse bien a 375px y a 1280px. Usa grid/flex con wrap, minmax, clamp(). Nada de anchos fijos en px
  mayores de 360, nada de height fijo con overflow hidden, nada de position absolute para el texto.
- Fotos: SOLO si el encargo dice FOTO_n. Entonces <img src="{{FOTO_n}}" alt="{{ALT_n}}" loading="lazy"> con object-fit: cover
  y aspect-ratio. Nunca escribas una URL. Sin FOTO_n en el encargo: cero <img> (usa tipografia, color o SVG).
- Movimiento (ya hecho, solo pon el atributo): data-efecto="titular" en el titulo de la seccion, data-efecto="contador" en
  una cifra real, data-efecto="magnetico" en el boton principal, data-efecto="relleno" en un parrafo destacado.
- Textos: solo los del encargo. No inventes precios, cifras, premios, telefonos ni direcciones: si faltan, [PENDIENTE].
- Toda caja con color de fondo lleva contenido.
- CONTRASTE (lo mira un verificador): en .seccion--invertida el texto NO lleva color propio (color: inherit). Dentro de una caja
  con fondo var(--accent) el texto es var(--accent-ink) y sus botones llevan fondo var(--accent-ink) y texto var(--accent).
  Nunca pongas un texto del mismo color que el fondo de su caja."""


def leer_spec(ruta: Path) -> dict:
    spec = json.loads(ruta.read_text(encoding="utf-8"))
    if not spec.get("secciones"):
        raise SystemExit(f"{ruta} no tiene 'secciones'.")
    for s in spec["secciones"]:
        s["id"] = re.sub(r"[^a-z0-9-]", "-", str(s.get("id", "")).lower()).strip("-")
        if not s["id"] or (not str(s.get("encargo", "")).strip() and not s.get("efecto")):
            raise SystemExit("Cada seccion necesita 'id' y 'encargo'.")
    return spec


def limpiar(texto: str) -> str:
    texto = re.sub(r"^```[a-z]*\s*|\s*```$", "", texto.strip(), flags=re.I | re.M)
    return texto.strip()


def comprobar(fragmento: str, sid: str) -> str:
    """'' si vale; si no, el motivo (se le devuelve a Qwen en el siguiente intento)."""
    if not re.search(rf'<section[^>]*\bid="{re.escape(sid)}"', fragmento):
        return f'falta <section id="{sid}">'
    if fragmento.count("<section") != fragmento.count("</section>"):
        return "las etiquetas <section> no cierran"
    if not re.search(r"class=[\"'][^\"']*\bcontenedor\b", fragmento):
        return 'todo el contenido va dentro de <div class="contenedor"> (si no, los titulos quedan pegados al borde)'
    if re.search(r"max-width:\s*(\d+)(px|ch)", fragmento) and any(int(n) < (14 if u == "ch" else 220) for n, u in re.findall(r"max-width:\s*(\d+)(px|ch)", fragmento)):
        return "hay un max-width demasiado estrecho: el texto queda en una columna de 2-3 palabras"
    srcs = re.findall(r"<img[^>]*\bsrc=[\"']([^\"']*)", fragmento, re.I)
    if any(not re.fullmatch(r"\{\{FOTO_\d+\}\}", x) for x in srcs) or ("<img" in fragmento.lower() and not srcs):
        return "las <img> solo pueden usar src=\"{{FOTO_n}}\" (las fotos las pone el sistema); si el encargo no da FOTO_n, quitalas"
    if re.search(r"--(bg|surface|ink|muted|accent|accent-ink|field|field-ink|font-display|font-text)\s*:", fragmento):
        return "no redefinas las variables de la paleta (--bg, --ink...): usa .seccion--invertida, --campo o --superficie"
    if re.search(r"<(html|head|body)\b", fragmento, re.I):
        return "devuelve solo la seccion, sin <html>, <head> ni <body>"
    estilos = "".join(re.findall(r"<style[^>]*>(.*?)</style>", fragmento, re.S | re.I))
    sueltas = [r.strip()[:40] for r in re.findall(r"(?:^|})\s*([^{}@]+)\{", estilos)
               if r.strip() and not r.strip().startswith(("#" + sid, "from", "to")) and not re.match(r"^\d+%", r.strip())]
    if sueltas:
        return f"reglas CSS que no empiezan por #{sid}: {', '.join(sueltas[:3])}"
    if re.search(r"#[0-9a-f]{3,8}\b(?![^{]*\{)", estilos, re.I) and "var(--" not in estilos:
        return "usa las variables var(--...) en lugar de colores sueltos"
    return ""


def picar(seccion: dict, spec: dict, modelo: str) -> tuple[str, list[str]]:
    from ollama_comun import generar_qwen

    sid, notas, error = seccion["id"], [], ""
    for intento in range(1, INTENTOS + 1):
        prompt = (f"Sitio: {spec.get('titulo', '')}\nSeccion: id=\"{sid}\" ({'portada, usa h1' if seccion is spec['secciones'][0] else 'usa h2'})\n"
                  f"Encargo:\n{seccion['encargo']}\n")
        if error:
            prompt += f"\nTu intento anterior fallo por: {error}. Corrigelo."
        t0 = time.time()
        texto, cortado = generar_qwen(prompt, modelo, sistema=SISTEMA, num_predict=PREDICT, num_ctx=CTX, temperatura=0.3)
        fragmento = limpiar(texto)
        error = "la respuesta se corto (demasiado larga): hazla mas compacta" if cortado else comprobar(fragmento, sid)
        notas.append(f"#{sid} intento {intento}: {round(time.time() - t0)} s · {'OK' if not error else error}")
        print(f"[SECCIONES] {notas[-1]}", flush=True)
        if not error:
            return fragmento, notas
    return "", notas


# ---------------------------------------------------------------- ACABADOS (lo "extra" que hace que se vea cuidada)
# Siempre igual y probado, NO lo escribe Qwen: titulares equilibrados, aparicion escalonada al hacer scroll, botones
# que responden, foco visible, un halo de luz que respira en la portada y scroll suave (Lenis de cdn.json).
# Todo se apaga con prefers-reduced-motion y la pagina funciona igual sin JavaScript.
ACABADOS_CSS = """
/* --- acabados Nova --- */
html { scroll-behavior: smooth; }
section[id] { scroll-margin-top: 72px; }
h1, h2, h3 { text-wrap: balance; }
p { text-wrap: pretty; }
::selection { background: var(--accent); color: var(--accent-ink); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 4px; }
a { text-underline-offset: .18em; }
.boton, a.boton, button { transition: transform .25s cubic-bezier(.2,.7,.2,1), box-shadow .25s, background-color .25s, color .25s; }
.boton:hover, a.boton:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -12px color-mix(in srgb, var(--ink) 55%, transparent); }
.boton:active { transform: translateY(0); }
body > section:first-of-type { position: relative; isolation: isolate; overflow: clip; }
body > section:first-of-type::before { content: ""; position: absolute; z-index: -1; inset: -20% -10% auto auto; width: min(70vw, 760px);
  aspect-ratio: 1; border-radius: 50%; pointer-events: none; filter: blur(60px); opacity: .22;
  background: radial-gradient(circle at 40% 40%, var(--accent), transparent 65%); animation: nova-halo 14s ease-in-out infinite alternate; }
@keyframes nova-halo { to { transform: translate(-8%, 10%) scale(1.15); } }
.js .nova-aparece { opacity: 0; transform: translateY(22px); transition: opacity .8s cubic-bezier(.2,.7,.2,1), transform .8s cubic-bezier(.2,.7,.2,1); transition-delay: var(--retraso, 0s); }
.js .nova-aparece.visto { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  body > section:first-of-type::before { animation: none; }
  .js .nova-aparece { opacity: 1; transform: none; transition: none; }
  .boton:hover, a.boton:hover { transform: none; }
}
"""

ACABADOS_JS = """<script>
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver((es) => es.forEach(x => { if (x.isIntersecting) { x.target.classList.add('visto'); io.unobserve(x.target); } }),
                                      { rootMargin: '0px 0px -10% 0px' });
  document.querySelectorAll('body > section:not(:first-of-type)').forEach(sec => {
    const base = sec.querySelector('.contenedor') || sec;
    [...base.children].slice(0, 8).forEach((el, i) => { el.classList.add('nova-aparece'); el.style.setProperty('--retraso', (i * 0.08) + 's'); io.observe(el); });
  });
})();
</script>"""


def scroll_suave() -> str:
    try:
        lenis = json.loads((BIBLIOTECA / "cdn.json").read_text(encoding="utf-8"))["lenis"]
    except (OSError, ValueError, KeyError):
        return ""
    return (f'<link rel="stylesheet" href="{html.escape(lenis["css"])}">\n<script>\n'
            "(() => { if (matchMedia('(prefers-reduced-motion: reduce)').matches || !matchMedia('(pointer: fine)').matches) return;\n"
            f"  const s = document.createElement('script'); s.src = {json.dumps(lenis['js'])}; s.defer = true;\n"
            "  s.onload = () => { if (!window.Lenis) return; document.documentElement.style.scrollBehavior = 'auto';\n"
            "    const l = new Lenis({ lerp: 0.12 }); const f = (t) => { l.raf(t); requestAnimationFrame(f); }; requestAnimationFrame(f);\n"
            "    document.addEventListener('click', (ev) => { const a = ev.target.closest('a[href^=\"#\"]'); if (!a || a.getAttribute('href').length < 2) return;\n"
            "      const d = document.querySelector(a.getAttribute('href')); if (d) { ev.preventDefault(); l.scrollTo(d, { offset: -72 }); } }); };\n"
            "  document.head.appendChild(s); })();\n</script>")


def poner_fotos(fragmento: str, fotos: list[dict]) -> str:
    """{{FOTO_n}} / {{ALT_n}} -> URL real comprobada y su texto alternativo (n empieza en 1)."""
    def foto(m):
        i = int(m.group(2)) - 1
        f = fotos[i % len(fotos)] if fotos else None
        if not f:
            return "" if m.group(1) == "ALT" else "data:,"
        return html.escape(f["alt"] if m.group(1) == "ALT" else f["url"], quote=True)
    return re.sub(r"\{\{(FOTO|ALT)_(\d+)\}\}", foto, fragmento)


def identidad_de(spec: dict) -> tuple[dict | None, dict]:
    """09/11 (Claude): la misma identidad que la biblioteca (identidad.py): de que va el negocio -> fotos y paleta.
    El tipo sale de spec["tipo"], fotos.tipo, el titulo ("Nombre · tipo · ciudad") o la descripcion."""
    import identidad as ID
    import montar
    pedido = spec.get("fotos") or {}
    texto = " ".join(str(x) for x in (spec.get("tipo"), pedido.get("tipo"), spec.get("titulo"), spec.get("descripcion")) if x)
    datos = {"negocio": {"tipo": texto, "notas": spec.get("notas", "")}, "estilo": spec.get("estilo") or {}}
    cat, rec = montar.detectar_categoria(texto)
    if pedido.get("categoria") in ID.cargar():
        cat = pedido["categoria"]
    return (ID.perfil(cat, rec, datos) if cat else None), datos


def fotos_de(spec: dict) -> list[dict]:
    pedido = spec.get("fotos") or {}
    if not pedido:
        return []
    import medios
    semilla, n = int(pedido.get("semilla", 0)), int(pedido.get("n", 6))
    try:  # 1o biblioteca que case con el negocio, 2o internet (identidad.py)
        import identidad as ID
        pf, _ = identidad_de(spec)
        if pf and pf.get("fotos"):
            if pedido.get("buscar"):
                pf["buscar"] = [pedido["buscar"]] + pf["buscar"]
            fs, _ = ID.fotos(pf, n, semilla)
            elegidas = [{"url": f["src"], "url_movil": f["src_movil"], "alt": f["alt"], "credito": f["credito"]} for f in fs]
            vivas = [f for f in elegidas if medios._vivo(f["url"])]
            if vivas:
                return vivas
    except Exception as e:
        print(f"[SECCIONES] identidad de fotos no disponible ({type(e).__name__}): catalogo general")
    elegidas = medios.elegir(pedido.get("categoria", ""), n, pedido.get("buscar", ""), semilla)
    return [f for f in elegidas if medios._vivo(f["url"])]


def montar_pagina(spec: dict, fragmentos: list[str], direccion: dict, fotos: list[dict] | None = None) -> str:
    import efectos
    import medios
    import montar

    fotos = fotos or []
    fragmentos = [poner_fotos(f, fotos) for f in fragmentos]
    if spec.get("fondo_vivo") and fragmentos:  # canvas vivo detras de la portada
        fragmentos[0] = re.sub(r"(<section\b[^>]*>)", r"\1" + efectos.canvas_fondo(spec["fondo_vivo"]), fragmentos[0], count=1)
    usados = [f for f in fotos if any(f["url"] in x for x in fragmentos)]
    creditos = medios.linea_creditos(usados)

    css_vars, fuentes, _, _ = montar.variables(direccion)
    sistema = (BIBLIOTECA / "sistema.css").read_text(encoding="utf-8")
    secciones_html, estilos = [], []
    for f in fragmentos:
        estilos += re.findall(r"<style[^>]*>(.*?)</style>", f, re.S | re.I)
        secciones_html.append(re.sub(r"<style[^>]*>.*?</style>", "", f, flags=re.S | re.I).strip())
    fuentes_html = "".join(f'<link rel="stylesheet" href="{html.escape(u)}">' for u in fuentes[:1])
    titulo = html.escape(spec.get("titulo") or "Web")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{html.escape(spec.get('descripcion', ''))}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fuentes_html}
<style>
{sistema}
{css_vars}
{chr(10).join(estilos)}
{ACABADOS_CSS}
{efectos.EFECTOS_CSS}
.nova-creditos {{ font-size: var(--step-small); opacity: .75; padding: 1rem var(--gutter) 2rem; text-align: center; }}
</style>
{scroll_suave()}
</head>
<body>
<script>document.documentElement.classList.add('js');</script>
{chr(10).join(secciones_html)}
{f'<p class="nova-creditos">{html.escape(creditos)}</p>' if creditos else ''}
{ACABADOS_JS}
{efectos.EFECTOS_JS}
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Qwen pica la web seccion a seccion (8k, GPU) y se verifica")
    ap.add_argument("--carpeta", required=True)
    ap.add_argument("--spec", default="secciones.json")
    ap.add_argument("--direccion", default="nova_direccion/direction.json")
    ap.add_argument("--archivo", default="index.html")
    ap.add_argument("--solo-montar", action="store_true", help="No llama a Qwen: vuelve a montar index.html con nova_secciones/*.html (tras arreglos de Nova)")
    ap.add_argument("--solo", default="", help="Repicar solo estas secciones (ids separados por comas); el resto se conserva")
    args = ap.parse_args()
    from ollama_comun import ensure_ollama_service

    carpeta = Path(args.carpeta).resolve()
    spec = leer_spec(carpeta / args.spec)
    ruta_dir = carpeta / args.direccion
    direccion = json.loads(ruta_dir.read_text(encoding="utf-8")) if ruta_dir.exists() else {}
    # 09/11: paleta por identidad del negocio (no la sorteada por sector), sin repetir dentro de la categoria
    pf_id = None
    try:
        import identidad as ID
        import montar as MON
        pf_id, datos_id = identidad_de(spec)
        if pf_id:
            pal, motivo = ID.elegir_paleta(pf_id, datos_id, MON.leer_memoria(), int((spec.get("fotos") or {}).get("semilla", 0)))
            if pal:
                direccion["palette"] = pal
                print(f"[SECCIONES] identidad: tipo {pf_id['tipo']} · paleta {pal['id']} ({motivo})")
    except Exception as e:
        print(f"[SECCIONES] identidad no disponible ({type(e).__name__}): paleta de la direccion")
    if not args.solo_montar and not ensure_ollama_service():
        print("[SECCIONES] FRENO: Ollama no responde. Avisa a Alexander (no lo hagas desde la nube).")
        return 1
    try:
        modelo = json.loads((NOVA / "antigravity" / "scripts" / "nova_modelos.json").read_text(encoding="utf-8"))["coder"]
    except (OSError, ValueError, KeyError):
        modelo = "qwen3.5:9b"
    piezas = carpeta / "nova_secciones"
    piezas.mkdir(exist_ok=True)
    solo = {x.strip() for x in args.solo.split(",") if x.strip()}
    fragmentos, fallidas, t0 = [], [], time.time()
    fotos = fotos_de(spec)
    if spec.get("fotos"):
        print(f"[SECCIONES] {len(fotos)} fotos comprobadas de CDN gratis (Picsum/Unsplash, Openverse/Wikimedia)")
    import efectos
    for s in spec["secciones"]:
        guardada = piezas / f"{s['id']}.html"
        if s.get("efecto") in efectos.BLOQUES:  # bloque de scroll del kit: calidad fija, sin Qwen
            desde = int(s.get("foto_desde", 1)) - 1
            frag = efectos.bloque(s["efecto"], s["id"], s.get("datos") or {}, fotos[desde:] + fotos[:desde])
            if frag:
                fragmentos.append(frag)
                print(f"[SECCIONES] #{s['id']}: bloque de efecto '{s['efecto']}' (kit)")
            continue
        if (args.solo_montar or (solo and s["id"] not in solo)) and guardada.exists():
            fragmentos.append(guardada.read_text(encoding="utf-8"))
            continue
        frag, _ = picar(s, spec, modelo)
        if frag:
            guardada.write_text(frag, encoding="utf-8")
            fragmentos.append(frag)
        else:
            fallidas.append(s["id"])
    print(f"[SECCIONES] {len(fragmentos)}/{len(spec['secciones'])} secciones en {round(time.time() - t0)} s")
    if fallidas:
        print(f"[SECCIONES] FRENO: Qwen no pudo con {', '.join('#' + f for f in fallidas)} en {INTENTOS} intentos. "
              "Nova: mejora el encargo de esas secciones o escribelas tu (<= 150 lineas cada una) en nova_secciones/<id>.html "
              "y relanza con --solo <ids>.")
        return 1
    (carpeta / args.archivo).write_text(montar_pagina(spec, fragmentos, direccion, fotos), encoding="utf-8")
    if pf_id:  # que la memoria anti-repeticion tambien vea las webs hechas por secciones
        try:
            import montar as MON
            MON.apuntar_memoria({"fecha": time.strftime("%Y-%m-%d %H:%M"), "negocio": str(spec.get("titulo", ""))[:60],
                                 "categoria": pf_id["categoria"], "tipo": pf_id["tipo"], "esqueleto": "secciones",
                                 "paleta": str((direccion.get("palette") or {}).get("id", "")).split("+")[0]})
        except Exception:
            pass
    print(f"[SECCIONES] Montada {carpeta / args.archivo}. Ahora el verificador.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
