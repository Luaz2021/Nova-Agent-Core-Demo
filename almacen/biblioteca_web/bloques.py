"""
BIBLIOTECA WEB DE NOVA · bloques (núcleo común + hostelería)

Cada bloque es una función bloque(d, variante) -> (html, css) que lee los DATOS REALES del negocio (datos.json) y
solo usa las variables de sistema.css. Si falta un dato obligatorio muestra [PENDIENTE]; si falta uno opcional, el
bloque se omite o se adapta. Nunca inventa precios, direcciones ni horarios.

BLOQUES (registro al final) dice, para Nova y para montar.py: categoría, rol, variantes, datos que usa, si necesita
fotos y cuándo usarlo. Una forma de botón, un radio y unos márgenes para toda la página (sistema.css).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote_plus


# ---------------------------------------------------------------------------------------------- utilidades
def e(texto) -> str:
    return html.escape(str(texto or ""), quote=True)


def pend(valor, etiqueta: str = "PENDIENTE") -> str:
    """Valor real escapado o [PENDIENTE] marcado (nunca un dato inventado)."""
    return e(valor) if valor not in (None, "", []) else f'<span class="pendiente">[{e(etiqueta)}]</span>'


def neg(d: dict) -> dict:
    return d.get("negocio") or {}


def rot(d: dict, clave: str, defecto: str) -> str:
    """Rotulo de la categoria (recetas.json -> rotulos), escapado. Sin rotulo, el texto de hosteleria."""
    return e((d.get("_rotulos") or {}).get(clave) or defecto)


_ICONOS: dict[str, str] = {}


def icono(nombre: str) -> str:
    """Icono Lucide (ISC, lucide-static 0.460.0 de jsDelivr, copiado en iconos/) en linea: sin peticiones externas."""
    if nombre not in _ICONOS:
        ruta = Path(__file__).with_name("iconos") / f"{nombre}.svg"
        svg = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
        svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL).strip()
        svg = re.sub(r'class="[^"]*"', 'class="icono" aria-hidden="true" focusable="false"', svg, count=1)
        _ICONOS[nombre] = re.sub(r"\s+", " ", svg)
    return _ICONOS[nombre]


def enlace_mapa(n: dict) -> str:
    if n.get("maps_url"):
        return n["maps_url"]
    destino = ", ".join(x for x in (n.get("nombre"), n.get("direccion"), n.get("ciudad")) if x)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(destino)}" if destino else ""


def accion_reserva(d: dict) -> tuple[str, str] | None:
    """(texto, href) de la acción principal de reserva según los datos; None si no hay forma de reservar."""
    r = d.get("reservas") or {}
    tipo, valor = r.get("tipo"), r.get("valor")
    if not valor:
        tel = neg(d).get("telefono")
        return ("Llamar", f"tel:{tel.replace(' ', '')}") if tel else None
    if tipo == "whatsapp":
        return ((d.get("_rotulos") or {}).get("accion_whatsapp") or "Reservar por WhatsApp", f"https://wa.me/{''.join(c for c in valor if c.isdigit())}")
    if tipo == "telefono":
        return ((d.get("_rotulos") or {}).get("accion_telefono") or "Reservar por teléfono", f"tel:{valor.replace(' ', '')}")
    return ((d.get("_rotulos") or {}).get("accion") or "Reservar mesa", valor)


MOTIVOS = {
    # forma gráfica sacada del oficio, en los colores de la paleta (cuando no hay fotos reales)
    "anillos": '<svg viewBox="0 0 400 400" aria-hidden="true">' + "".join(
        f'<circle cx="200" cy="200" r="{r}" fill="none" stroke="currentColor" stroke-width="{w}" opacity="{o}"/>'
        for r, w, o in ((180, 2, .25), (140, 10, .35), (96, 2, .5), (58, 22, .8), (16, 32, 1))) + "</svg>",
    "rayas": '<svg viewBox="0 0 400 400" preserveAspectRatio="none" aria-hidden="true">' + "".join(
        f'<rect x="{x}" y="0" width="26" height="400" fill="currentColor" opacity=".85"/>' for x in range(0, 400, 52)) + "</svg>",
    "grano": '<svg viewBox="0 0 400 400" aria-hidden="true"><ellipse cx="200" cy="200" rx="120" ry="170" fill="currentColor" '
             'transform="rotate(-24 200 200)"/><path d="M150 70 C 250 160, 150 240, 250 330" fill="none" stroke="var(--field)" '
             'stroke-width="18" stroke-linecap="round" transform="rotate(-24 200 200)"/></svg>',
    "arcos": '<svg viewBox="0 0 400 400" aria-hidden="true">' + "".join(
        f'<path d="M {x} 400 L {x} {240 - i * 30} A 50 50 0 0 1 {x + 100} {240 - i * 30} L {x + 100} 400" fill="currentColor" opacity="{.35 + i * .2}"/>'
        for i, x in enumerate((20, 150, 280))) + "</svg>",
}


def motivo(d: dict) -> str:
    return MOTIVOS.get((d.get("_estilo") or {}).get("motivo"), MOTIVOS["anillos"])


def foto(d: dict, n: int):
    fotos = d.get("fotos") or []
    return fotos[n] if len(fotos) > n else None


# ---------------------------------------------------------------------------------------------- NÚCLEO COMÚN
def cabecera(d, v="barra"):
    n = neg(d)
    acc = accion_reserva(d)
    enlaces = [("#carta", rot(d, "nav_carta", "Carta")) if d.get("carta") else None, ("#horario", "Horario") if d.get("horario") else None,
               ("#visitanos", rot(d, "nav_visitanos", "Cómo llegar"))]
    nav = "".join(f'<a href="{h}">{t}</a>' for h, t in [x for x in enlaces if x])
    boton = f'<a class="boton boton--principal cab-cta" href="{e(acc[1])}">{e(acc[0])}</a>' if acc else ""
    html_ = f"""
<header class="cab cab--{v}" id="cabecera">
  <div class="contenedor cab__fila">
    <a class="cab__marca" href="#cabecera">{pend(n.get("nombre"), "NOMBRE")}</a>
    <nav class="cab__nav" aria-label="Principal">{nav}</nav>
    {boton}
  </div>
</header>"""
    css = """
.cab { position: sticky; top: 0; z-index: 20; background: color-mix(in srgb, var(--bg) 92%, transparent);
  backdrop-filter: blur(8px); border-bottom: 1px solid color-mix(in srgb, var(--ink) 10%, transparent); }
.cab__fila { display: flex; align-items: center; gap: 24px; min-height: 68px; }
.cab__marca { font-family: var(--font-display); font-size: 1.35rem; text-decoration: none; letter-spacing: var(--display-tracking); }
.cab__nav { display: none; gap: 28px; margin-left: auto; font-size: var(--step-small); }
.cab__nav a { text-decoration: none; padding-block: 12px; }
.cab__nav a:hover { text-decoration: underline; }
.cab-cta { margin-left: auto; min-height: 44px; padding: .55em 1.1em; font-size: var(--step-small); }
@media (min-width: 760px) { .cab__nav { display: flex; } .cab-cta { margin-left: 0; } }
.cab--centrada .cab__fila { justify-content: space-between; }
@media (min-width: 760px) { .cab--centrada .cab__marca { order: 2; } .cab--centrada .cab__nav { order: 1; margin-left: 0; } .cab--centrada .cab-cta { order: 3; } }
"""
    return html_, css


def visitanos(d, v="tarjeta"):
    n = neg(d)
    mapa = enlace_mapa(n)
    lineas = [f'<p class="t-lead">{pend(n.get("direccion"), "DIRECCIÓN")}</p>',
              f'<p class="t-small">{e(", ".join(x for x in (n.get("barrio"), n.get("ciudad")) if x))}</p>']
    if n.get("como_llegar"):
        lineas.append(f'<p>{e(n["como_llegar"])}</p>')
    contactos = []
    if n.get("telefono"):
        contactos.append(f'<a href="tel:{e(n["telefono"].replace(" ", ""))}">{icono("phone")}{e(n["telefono"])}</a>')
    if n.get("email"):
        contactos.append(f'<a href="mailto:{e(n["email"])}">{icono("mail")}{e(n["email"])}</a>')
    if n.get("instagram"):
        usuario = n["instagram"].lstrip("@")
        contactos.append(f'<a href="https://instagram.com/{e(usuario)}">{icono("instagram")}@{e(usuario)}</a>')
    boton = f'<a class="boton boton--secundario" href="{e(mapa)}" target="_blank" rel="noopener">{icono("map-pin")}Abrir en el mapa</a>' if mapa else ""
    html_ = f"""
<section class="seccion" id="visitanos" aria-labelledby="visitanos-t">
  <div class="contenedor rejilla-2">
    <div class="pila revelar" style="--pila:1.2rem">
      <p class="t-eyebrow">{rot(d, "visitanos_ceja", "Ven a vernos")}</p>
      <h2 class="t-head" id="visitanos-t">{rot(d, "visitanos", "Dónde estamos")}</h2>
      {''.join(lineas)}
      <div class="acciones">{boton}</div>
    </div>
    <div class="vis__contacto revelar">
      {mapa_embebido(n) or f'<div class="motivo vis__motivo">{motivo(d)}</div>'}
      <ul role="list" class="vis__lista">{''.join(f'<li>{c}</li>' for c in contactos) or '<li class="t-small">Contacto [PENDIENTE]</li>'}</ul>
    </div>
  </div>
</section>"""
    css = """
.vis__motivo { aspect-ratio: 4 / 3; padding: 12%; }
.mapa { aspect-ratio: 4 / 3; border-radius: var(--radius); overflow: hidden; background: color-mix(in srgb, var(--ink) 9%, var(--bg)); color: var(--ink);
  display: grid; place-content: center; justify-items: center; gap: .6rem; text-align: center; padding: 24px; }
.mapa iframe { width: 100%; height: 100%; border: 0; display: block; }
.mapa:has(iframe) { padding: 0; display: block; }
.mapa__nota { max-width: 30ch; color: inherit; opacity: .75; }
.vis__lista { display: grid; gap: .4rem; margin-top: 1.2rem; }
.vis__lista a { text-decoration: none; border-bottom: 1px solid currentColor; padding-block: 6px; display: inline-flex; align-items: center; gap: .5em; }
.vis__lista .icono { margin: 0; }
"""
    return html_, css


def resenas(d, v="citas"):
    lista = d.get("resenas") or []
    if not lista:
        return "", ""  # sin reseñas reales no se pinta (nunca se inventan)
    items = "".join(f'<figure class="res__item revelar"><blockquote class="t-lead">“{e(r.get("texto"))}”</blockquote>'
                    f'<figcaption class="t-small">{e(r.get("autor") or "")}</figcaption></figure>' for r in lista[:4])
    html_ = f"""
<section class="seccion seccion--superficie" id="resenas" aria-labelledby="resenas-t">
  <div class="contenedor">
    <div class="cabecera-seccion"><p class="t-eyebrow">{rot(d, "resenas_ceja", "Lo que dicen")}</p><h2 class="t-head" id="resenas-t">{rot(d, "resenas", "Reseñas")}</h2></div>
    <div class="res__rejilla">{items}</div>
  </div>
</section>"""
    css = """
.res__rejilla { display: grid; gap: clamp(32px, 4vw, 56px); }
@media (min-width: 860px) { .res__rejilla { grid-template-columns: repeat(2, 1fr); } }
.res__item { border-top: 1px solid color-mix(in srgb, var(--ink) 20%, transparent); padding-top: 1.4rem; display: grid; gap: .8rem; }
"""
    return html_, css


def faq(d, v="lista"):
    lista = d.get("faq") or []
    if not lista:
        return "", ""
    items = "".join(f'<details class="faq__item"><summary>{e(q.get("p"))}</summary><p>{e(q.get("r"))}</p></details>' for q in lista)
    html_ = f"""
<section class="seccion" id="faq" aria-labelledby="faq-t">
  <div class="contenedor rejilla-2">
    <h2 class="t-head" id="faq-t">Preguntas frecuentes</h2>
    <div class="faq__lista">{items}</div>
  </div>
</section>"""
    css = """
.faq__item { border-bottom: 1px solid color-mix(in srgb, var(--ink) 15%, transparent); padding-block: 1rem; }
.faq__item summary { cursor: pointer; font-weight: 600; min-height: 44px; display: flex; align-items: center; list-style: none; }
.faq__item summary::after { content: "+"; margin-left: auto; font-size: 1.4rem; }
.faq__item[open] summary::after { content: "–"; }
.faq__item p { padding-top: .6rem; color: var(--muted); max-width: var(--measure); }
"""
    return html_, css


def pie(d, v="firma"):
    n = neg(d)
    legal = d.get("legal") or {}
    titular = pend(legal.get("titular"), "TITULAR Y NIF")
    html_ = f"""
<footer class="pie pie--{v}" id="pie">
  <div class="contenedor pie__dentro">
    <p class="pie__firma">{pend(n.get("nombre"), "NOMBRE")}</p>
    <div class="pie__datos t-small">
      <p>{e(n.get("direccion") or "")}{(" · " + e(n["ciudad"])) if n.get("ciudad") else ""}</p>
      <p>{titular}</p>
      <p><a href="#aviso-legal">Aviso legal</a> · <a href="#privacidad">Privacidad</a> · Esta web no usa cookies de seguimiento</p>
    </div>
  </div>
</footer>"""
    css = """
.pie { padding-block: clamp(56px, 8vw, 120px) 32px; background: var(--ink); color: var(--bg); }
.pie .t-small { color: color-mix(in srgb, var(--bg) 70%, transparent); }
.pie__dentro { display: grid; gap: 32px; }
.pie__firma { font-family: var(--font-display); font-size: clamp(3rem, 2rem + 8vw, 10rem); line-height: .9;
  letter-spacing: var(--display-tracking); overflow-wrap: anywhere; }
.pie__datos { display: grid; gap: .3rem; }
.pie a { text-decoration: none; border-bottom: 1px solid currentColor; }
"""
    return html_, css


# ---------------------------------------------------------------------------------------------- MÓDULOS VIVOS
# Canvas del motivo: dibuja con los colores de la paleta (--accent / --ink), se pausa fuera de pantalla y no arranca
# con prefers-reduced-motion (queda el SVG quieto). Sin librerias.
SCRIPT_VIVO = """
<script>
(() => {
  const cv = document.querySelector('canvas.vivo'); if (!cv || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const ctx = cv.getContext('2d'); if (!ctx) return;
  const css = getComputedStyle(cv.parentElement), color = css.color, motivo = cv.dataset.motivo || 'anillos';
  let w = 0, h = 0, t = 0, vivo = true, raf = 0; const dpr = Math.min(devicePixelRatio || 1, 2);
  const medir = () => { const r = cv.getBoundingClientRect(); w = r.width; h = r.height; cv.width = w * dpr; cv.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
  const vapor = Array.from({ length: 26 }, (_, i) => ({ x: Math.random(), y: Math.random(), v: .15 + Math.random() * .35, r: 2 + Math.random() * 5 }));
  const dibujar = () => {
    ctx.clearRect(0, 0, w, h); ctx.strokeStyle = color; ctx.fillStyle = color; const cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2;
    if (motivo === 'rayas') { for (let i = 0; i < 9; i++) { const x = ((i / 9 + t * .02) % 1) * w; ctx.globalAlpha = .75; ctx.fillRect(x, 0, w / 18, h); } }
    else if (motivo === 'arcos') { [0, 1, 2].forEach(i => { const bw = w / 4.2, x = w * (.08 + i * .31), top = h * (.42 - i * .08) + Math.sin(t * .6 + i) * 8;
        ctx.globalAlpha = .35 + i * .22; ctx.beginPath(); ctx.moveTo(x, h); ctx.lineTo(x, top + bw / 2); ctx.arc(x + bw / 2, top + bw / 2, bw / 2, Math.PI, 0); ctx.lineTo(x + bw, h); ctx.fill(); }); }
    else { [.9, .7, .48, .29].forEach((k, i) => { ctx.globalAlpha = .25 + i * .2; ctx.lineWidth = 2 + i * 6; ctx.beginPath();
        ctx.arc(cx, cy, R * k * (1 + Math.sin(t * .8 + i) * .02), 0, Math.PI * 2); ctx.stroke(); }); ctx.globalAlpha = 1; ctx.beginPath(); ctx.arc(cx, cy, R * .08, 0, Math.PI * 2); ctx.fill(); }
    vapor.forEach(p => { p.y -= p.v * .004; if (p.y < -.05) { p.y = 1.05; p.x = Math.random(); }
      ctx.globalAlpha = Math.max(0, Math.min(.35, p.y * .4)); ctx.beginPath(); ctx.arc(p.x * w + Math.sin(t + p.y * 6) * 12, p.y * h, p.r, 0, Math.PI * 2); ctx.fill(); });
    ctx.globalAlpha = 1;
  };
  const bucle = () => { if (!vivo) return; t += 1 / 60; dibujar(); raf = requestAnimationFrame(bucle); };
  medir(); addEventListener('resize', medir);
  new IntersectionObserver(([x]) => { vivo = x.isIntersecting; cancelAnimationFrame(raf); if (vivo) bucle(); }).observe(cv);
  cv.classList.add('activo');
})();
</script>"""


def cinta(d, v="nombres"):
    """Cinta de texto en movimiento con los nombres reales de los destacados (o de la carta)."""
    nombres = [x.get("nombre") for x in d.get("destacados") or [] if x.get("nombre")]
    if not nombres:
        nombres = [i.get("nombre") for c in d.get("carta") or [] for i in c.get("items") or [] if i.get("nombre")][:8]
    if len(nombres) < 2:
        return "", ""
    pista = "".join(f'<span>{e(x)}</span><span aria-hidden="true">✦</span>' for x in nombres * 3)
    html_ = f"""
<div class="cinta" aria-label="{e(', '.join(nombres))}"><div class="cinta__pista" aria-hidden="true">{pista}</div><div class="cinta__pista" aria-hidden="true">{pista}</div></div>"""
    css = """
.cinta { display: flex; overflow: hidden; border-block: 1px solid color-mix(in srgb, var(--ink) 18%, transparent); padding-block: 18px;
  font-family: var(--font-display); font-size: var(--step-lead); white-space: nowrap; }
.cinta__pista { display: flex; gap: 36px; padding-right: 36px; flex-shrink: 0; animation: cinta 38s linear infinite; }
.cinta span:nth-child(4n+2), .cinta span:nth-child(4n+4) { color: var(--accent); }
@keyframes cinta { to { transform: translateX(-100%); } }
@media (prefers-reduced-motion: reduce) { .cinta__pista { animation: none; } }
"""
    return html_, css


def mapa_embebido(n: dict) -> str:
    """Mapa con carga al hacer clic: no pone cookies de terceros hasta que el usuario lo pide (RGPD) y no deforma
    (caja con proporcion fija)."""
    destino = ", ".join(x for x in (n.get("direccion"), n.get("ciudad")) if x)
    if not destino:
        return ""
    src = f"https://www.google.com/maps?q={quote_plus(destino)}&output=embed"
    caja = f"""
<div class="mapa" data-src="{e(src)}">
  <button type="button" class="boton boton--secundario mapa__cargar">Ver mapa aquí</button>
  <p class="t-small mapa__nota">Al cargarlo, Google Maps puede usar cookies.</p>
</div>"""
    return caja + SCRIPT_MAPA


SCRIPT_MAPA = """
<script>
document.querySelectorAll('.mapa').forEach(m => m.querySelector('.mapa__cargar').addEventListener('click', () => {
  const f = document.createElement('iframe'); f.src = m.dataset.src; f.title = 'Mapa de la ubicación'; f.loading = 'lazy';
  f.referrerPolicy = 'no-referrer-when-downgrade'; m.replaceChildren(f); }));
</script>"""


# ---------------------------------------------------------------------------------------------- HOSTELERÍA
def hero(d, v="tipografico"):
    n = neg(d)
    acc = accion_reserva(d)
    acciones = "".join(x for x in (
        f'<a class="boton boton--principal" href="{e(acc[1])}">{icono("phone" if acc[1].startswith("tel:") else "message-circle" if "wa.me" in acc[1] else "calendar")}{e(acc[0])}</a>' if acc else "",
        f'<a class="boton boton--secundario" href="#carta">Ver {rot(d, "nav_carta", "la carta").lower() if (d.get("_rotulos") or {}).get("nav_carta") else "la carta"}</a>' if d.get("carta") else "",
    ))
    eyebrow = e(" · ".join(x for x in (n.get("tipo"), n.get("barrio") or n.get("ciudad")) if x))
    texto = f"""
      <p class="t-eyebrow revelar">{eyebrow}</p>
      <h1 class="t-display revelar">{pend(n.get("eslogan") or n.get("nombre"), "ESLOGAN")}</h1>
      <p class="t-lead medida revelar">{pend(n.get("descripcion"), "DESCRIPCIÓN")}</p>
      <div class="acciones revelar">{acciones}</div>"""
    f = foto(d, 0)
    visual = (f'<img src="{e(f["src"])}" alt="{e(f.get("alt"))}" loading="eager">' if f and v == "foto"
              else f'<div class="hero__foto-partida"><img src="{e(f["src"])}" alt="{e(f.get("alt"))}" loading="eager"></div>' if f and v == "partido"
              else f'<div class="motivo hero__motivo">{motivo(d)}</div>')
    if v == "foto" and f:
        cuerpo = f'<div class="hero__foto">{visual}</div><div class="contenedor hero__texto pila" style="--pila:1.4rem">{texto}</div>'
    elif v == "partido":
        cuerpo = f'<div class="contenedor hero__partido"><div class="pila hero__texto" style="--pila:1.4rem">{texto}</div>{visual}</div>'
    elif v == "video" and d.get("video"):
        vid = d["video"]
        cuerpo = (f'<div class="hero__foto"><video class="hero__video" autoplay muted loop playsinline preload="metadata" '
                  f'poster="{e(vid.get("poster", ""))}" aria-hidden="true"><source src="{e(vid["src"])}" type="video/mp4"></video></div>'
                  f'<div class="contenedor hero__texto pila" style="--pila:1.4rem">{texto}</div>')
    else:
        # "one live thing" (skill gemini-ui-artisan): el motivo vive en un canvas; el SVG queda debajo como respaldo
        cuerpo = (f'<div class="contenedor hero__tipo"><div class="pila hero__texto" style="--pila:1.4rem">{texto}</div>'
                  f'<div class="hero__marca" aria-hidden="true">{motivo(d)}<canvas class="vivo" data-motivo="{e((d.get("_estilo") or {}).get("motivo", "anillos"))}"></canvas></div></div>')
    html_ = f'\n<section class="hero hero--{v}" id="inicio" aria-label="Presentación">{cuerpo}</section>' + (SCRIPT_VIVO if v not in ("foto", "video") else "")
    css = """
.hero { padding-block: clamp(56px, 9vw, 140px); overflow: clip; }
.hero__texto { max-width: 54ch; }
.hero__tipo { position: relative; }
.hero__tipo .hero__texto { position: relative; z-index: 1; max-width: 640px; }
.hero__tipo .t-display { max-width: 9ch; }
.hero__tipo .t-display { font-size: clamp(3.2rem, 1.4rem + 8vw, 9rem); }
.hero__tipo .t-lead { max-width: 38ch; }
.hero__marca { position: absolute; right: calc(-1 * var(--gutter)); top: 50%; translate: 0 -50%; width: min(52vw, 620px);
  aspect-ratio: 1; color: var(--accent); opacity: .9; pointer-events: none; }
@media (max-width: 759px) { .hero__marca { position: relative; right: auto; top: auto; translate: none; width: 70%; margin: 40px 0 0 auto; } }
.hero__foto-partida { aspect-ratio: 4 / 5; border-radius: var(--radius); overflow: hidden; }
.hero__foto-partida img { width: 100%; height: 100%; object-fit: cover; }
.hero__partido { display: grid; gap: clamp(32px, 5vw, 72px); align-items: center; }
@media (min-width: 900px) { .hero__partido { grid-template-columns: 1.1fr .9fr; } }
.hero__motivo { aspect-ratio: 4 / 5; padding: 14%; color: var(--ink);
  background: color-mix(in srgb, var(--ink) 9%, var(--bg)); }  /* mismo tono que la pagina: sin cajas blancas pegadas */
.hero__marca > svg, .hero__marca > canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
.hero__marca canvas.activo + svg, .hero__marca svg:has(+ canvas.activo) { opacity: 0; }
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .hero__marca { animation: hero-paralaje linear both; animation-timeline: view(); animation-range: exit; }
    @keyframes hero-paralaje { to { translate: 0 calc(-50% - 120px); rotate: -8deg; } }
  }
}
.hero__video { width: 100%; height: min(78svh, 820px); object-fit: cover; }
@media (max-width: 759px) { .hero__video { display: none; } .hero--video .hero__foto { background: var(--field) center / cover; min-height: 40svh; } }
.hero--video { padding-top: 0; }
.hero--video .hero__texto { margin-top: clamp(-160px, -12vw, -60px); position: relative; background: var(--bg); padding: clamp(24px, 4vw, 56px); max-width: 760px; }
.hero--foto { padding-top: 0; }
.hero__foto img { width: 100%; height: min(78svh, 820px); object-fit: cover; }
.hero--foto .hero__texto { margin-top: clamp(-160px, -12vw, -60px); position: relative; background: var(--bg);
  padding: clamp(24px, 4vw, 56px); max-width: 760px; }
"""
    return html_, css


def visual_des(d: dict, i: int) -> str:
    """Foto i+1 (la 0 es del hero) o, sin fotos, el motivo grafico de la direccion."""
    f = foto(d, i + 1)
    if f:
        return f'<div class="des__foto"><img src="{e(f["src"])}" alt="{e(f.get("alt"))}" loading="lazy" decoding="async"></div>'
    return f'<div class="motivo des__motivo" aria-hidden="true">{motivo(d)}</div>'


def destacados(d, v="tarjetas"):
    lista = (d.get("destacados") or [])[:6]
    if not lista:
        return "", ""
    def precio(x):
        return f'<p class="des__precio">{e(x["precio"])}</p>' if x.get("precio") else ""
    if v == "zigzag":
        items = "".join(f"""
      <li class="des__zz revelar">{visual_des(d, i)}
        <div class="pila" style="--pila:.6rem">
          {f'<p class="t-eyebrow">{e(x["etiqueta"])}</p>' if x.get("etiqueta") else ''}
          <h3 class="t-head">{e(x.get("nombre"))}</h3>
          <p class="t-lead">{pend(x.get("descripcion"), "DESCRIPCIÓN")}</p>{precio(x)}</div></li>""" for i, x in enumerate(lista))
        cuerpo = f'<ol role="list" class="des__zigzag">{items}</ol>'
    elif v == "lista":
        items = "".join(f"""
      <li class="des__fila revelar"><span class="des__num" aria-hidden="true">{i:02d}</span>
        <div class="pila" style="--pila:.4rem"><h3 class="des__nombre">{e(x.get("nombre"))}</h3>
        {f'<p class="t-small">{e(x["etiqueta"])}</p>' if x.get("etiqueta") else ''}
        <p class="medida">{pend(x.get("descripcion"), "DESCRIPCIÓN")}</p></div>{precio(x)}</li>""" for i, x in enumerate(lista, 1))
        cuerpo = f'<ol role="list" class="des__lista">{items}</ol>'
    else:
        items = "".join(f"""
      <li class="des__tarjeta revelar">
        {visual_des(d, i)}
        <div class="pila" style="--pila:.5rem">
          {f'<p class="t-eyebrow">{e(x["etiqueta"])}</p>' if x.get("etiqueta") else ''}
          <h3 class="des__nombre">{e(x.get("nombre"))}</h3>
          <p>{pend(x.get("descripcion"), "DESCRIPCIÓN")}</p>{precio(x)}</div></li>""" for i, x in enumerate(lista))
        cuerpo = f'<ul role="list" class="des__rejilla{" des__rejilla--bento" if v == "bento" else ""}">{items}</ul>'
    html_ = f"""
<section class="seccion" id="destacados" aria-labelledby="destacados-t">
  <div class="contenedor">
    <div class="cabecera-seccion"><p class="t-eyebrow">{rot(d, "destacados_ceja", "De la casa")}</p>
      <h2 class="t-head" id="destacados-t">{e(d.get("_titulos", {}).get("destacados") or (d.get("_rotulos") or {}).get("destacados") or "Lo que no te puedes perder")}</h2></div>
    {cuerpo}
  </div>
</section>"""
    css = """
.des__rejilla { display: grid; gap: clamp(28px, 4vw, 48px); }
@media (min-width: 720px) { .des__rejilla { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); } }
.des__tarjeta { display: grid; gap: 1.2rem; align-content: start; }
.des__motivo { aspect-ratio: 1; padding: 22%; color: var(--accent); }
.des__tarjeta:nth-child(2) .des__motivo { background: var(--surface); }
.des__nombre { font-family: var(--font-display); font-size: var(--step-lead); line-height: 1.15; }
.des__precio { font-weight: 600; font-variant-numeric: tabular-nums; }
.des__lista { display: grid; }
.des__fila { display: grid; grid-template-columns: auto 1fr; gap: 8px 28px; padding-block: 28px;
  border-top: 1px solid color-mix(in srgb, var(--ink) 18%, transparent); }
.des__fila .des__precio { grid-column: 2; }
@media (min-width: 760px) { .des__fila { grid-template-columns: 90px 1fr auto; } .des__fila .des__precio { grid-column: 3; } }
.des__num { font-family: var(--font-display); font-size: var(--step-head); line-height: 1; color: var(--accent); }
.des__foto { aspect-ratio: 4 / 3; border-radius: var(--radius); overflow: hidden; }
.des__foto img { width: 100%; height: 100%; object-fit: cover; transition: transform .8s cubic-bezier(.2,.7,.2,1); }
.des__tarjeta:hover .des__foto img, .des__zz:hover .des__foto img { transform: scale(1.04); }
@media (min-width: 900px) {
  .des__rejilla--bento { grid-template-columns: repeat(6, 1fr); grid-auto-flow: dense; }
  .des__rejilla--bento > :nth-child(6n+1) { grid-column: span 4; }
  .des__rejilla--bento > :nth-child(6n+2) { grid-column: span 2; }
  .des__rejilla--bento > :nth-child(6n+3), .des__rejilla--bento > :nth-child(6n+4), .des__rejilla--bento > :nth-child(6n+5) { grid-column: span 2; }
  .des__rejilla--bento > :nth-child(6n) { grid-column: span 6; }
  .des__rejilla--bento > :nth-child(6n+1) .des__foto, .des__rejilla--bento > :nth-child(6n+1) .des__motivo { aspect-ratio: 16 / 9; }
  .des__rejilla--bento > :last-child:nth-child(3n+1) { grid-column: 1 / -1; }
}
.des__rejilla--bento > li { background: var(--surface); padding: clamp(14px, 1.6vw, 22px); border-radius: var(--radius); }
.des__zigzag { list-style: none; margin: 0; padding: 0; display: grid; gap: clamp(48px, 8vw, 112px); }
.des__zz { display: grid; gap: clamp(20px, 3vw, 48px); align-items: center; }
@media (min-width: 860px) {
  .des__zz { grid-template-columns: 1.15fr 1fr; }
  .des__zz:nth-child(even) > :first-child { order: 2; }
}
"""
    return html_, css


def carta(d, v="menu"):
    cats = d.get("carta") or []
    if not cats:
        return "", ""
    def item(x):
        alerg = f'<p class="t-small">Alérgenos: {e(", ".join(x["alergenos"]))}</p>' if x.get("alergenos") else ""
        desc = f'<p class="t-small">{e(x["descripcion"])}</p>' if x.get("descripcion") else ""
        return (f'<li class="carta__item"><div class="carta__linea"><span class="carta__nombre">{e(x.get("nombre"))}</span>'
                f'<span class="carta__puntos" aria-hidden="true"></span><span class="carta__precio">{pend(x.get("precio"), "€")}</span></div>{desc}{alerg}</li>')
    bloques_cat = "".join(f'<div class="carta__cat revelar"><h3 class="t-eyebrow carta__titulo">{e(c.get("categoria"))}</h3>'
                          f'<ul role="list">{"".join(item(x) for x in c.get("items") or [])}</ul></div>' for c in cats)
    html_ = f"""
<section class="seccion seccion--superficie" id="carta" aria-labelledby="carta-t">
  <div class="contenedor">
    <div class="cabecera-seccion"><p class="t-eyebrow">{rot(d, "carta_ceja", "Carta")}</p><h2 class="t-head" id="carta-t">{rot(d, "carta", "Para tomar aquí o llevar")}</h2></div>
    <div class="carta__columnas">{bloques_cat}</div>
  </div>
</section>"""
    css = """
.carta__columnas { display: grid; gap: clamp(40px, 5vw, 64px); }
@media (min-width: 860px) { .carta__columnas { grid-template-columns: repeat(2, 1fr); column-gap: clamp(48px, 7vw, 120px); } }
.carta__titulo { margin-bottom: .8rem; color: var(--accent); }
.carta__item { padding-block: .7rem; border-bottom: 1px solid color-mix(in srgb, var(--ink) 10%, transparent); }
.carta__linea { display: flex; align-items: baseline; gap: .6rem; }
.carta__nombre { font-weight: 600; }
.carta__puntos { flex: 1; border-bottom: 1px dotted color-mix(in srgb, var(--ink) 35%, transparent); translate: 0 -4px; min-width: 24px; }
.carta__precio { font-variant-numeric: tabular-nums; white-space: nowrap; }
"""
    return html_, css


DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]


def horario(d, v="tabla"):
    filas = d.get("horario") or []
    if not filas:
        return "", ""
    tabla = "".join(f'<tr data-dias="{e(",".join(map(str, f.get("dias_semana") or [])))}"><th scope="row">{e(f.get("dias"))}</th>'
                    f'<td>{e(f.get("abre"))} – {e(f.get("cierra"))}</td></tr>' if f.get("abre") else
                    f'<tr><th scope="row">{e(f.get("dias"))}</th><td>Cerrado</td></tr>' for f in filas)
    datos_js = json.dumps([{"d": f.get("dias_semana") or [], "a": f.get("abre"), "c": f.get("cierra")} for f in filas if f.get("abre")])
    html_ = f"""
<section class="seccion seccion--invertida" id="horario" aria-labelledby="horario-t">
  <div class="contenedor rejilla-2">
    <div class="pila" style="--pila:1rem">
      <p class="t-eyebrow">Horario</p>
      <h2 class="t-head" id="horario-t">{rot(d, "horario", "Cuándo abrimos")}</h2>
      <p class="hor__estado t-lead" data-horario='{e(datos_js)}' aria-live="polite"></p>
    </div>
    <table class="hor__tabla"><caption class="solo-lector">Horario de apertura</caption><tbody>{tabla}</tbody></table>
  </div>
</section>
<script>
(() => {{ const p = document.querySelector('.hor__estado'); if (!p) return; const h = JSON.parse(p.dataset.horario || '[]');
  const ahora = new Date(), dia = ahora.getDay(), min = ahora.getHours() * 60 + ahora.getMinutes();
  const aMin = (t) => {{ const [a, b] = t.split(':').map(Number); return a * 60 + b; }};
  const hoy = h.find(f => f.d.includes(dia));
  document.querySelectorAll('.hor__tabla tr').forEach(tr => {{ if ((tr.dataset.dias || '').split(',').includes(String(dia))) tr.classList.add('hoy'); }});
  if (hoy && min >= aMin(hoy.a) && min < aMin(hoy.c)) p.textContent = 'Abierto ahora · hasta las ' + hoy.c;
  else if (hoy && min < aMin(hoy.a)) p.textContent = 'Hoy abrimos a las ' + hoy.a;
  else p.textContent = 'Ahora cerrado';
}})();
</script>"""
    css = """
.hor__tabla { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
.hor__tabla th, .hor__tabla td { text-align: left; padding: 1rem 0; border-bottom: 1px solid color-mix(in srgb, var(--bg) 22%, transparent); font-weight: 400; }
.hor__tabla td { text-align: right; }
.hor__tabla tr.hoy th, .hor__tabla tr.hoy td { color: inherit; font-weight: 700; }
.hor__tabla tr.hoy th::before { content: "Hoy · "; color: inherit; opacity: .7; }
.hor__estado:empty { display: none; }
.hor__estado { color: inherit; font-weight: 600; }
"""
    return html_, css


def reservar(d, v="banda"):
    acc = accion_reserva(d)
    if not acc:
        return "", ""
    n = neg(d)
    html_ = f"""
<section class="seccion seccion--campo" id="reservar" aria-labelledby="reservar-t">
  <div class="contenedor res-banda">
    <h2 class="t-head" id="reservar-t">{e(d.get("_titulos", {}).get("reservar") or (d.get("_rotulos") or {}).get("reservar") or "Te guardamos sitio")}</h2>
    <div class="pila" style="--pila:1rem">
      <p class="medida">{e(d.get("_textos", {}).get("reservar") or "")}</p>
      <div class="acciones"><a class="boton boton--principal" href="{e(acc[1])}">{icono("phone" if acc[1].startswith("tel:") else "message-circle" if "wa.me" in acc[1] else "calendar")}{e(acc[0])}</a>
      {f'<a class="boton boton--secundario" href="tel:{e(n["telefono"].replace(" ", ""))}">{e(n["telefono"])}</a>' if n.get("telefono") and not acc[1].startswith("tel:") else ''}</div>
    </div>
  </div>
</section>"""
    css = """
.res-banda { display: grid; gap: 28px; align-items: end; }
@media (min-width: 860px) { .res-banda { grid-template-columns: 1.2fr 1fr; } }
"""
    return html_, css


def eventos(d, v="lista"):
    lista = d.get("eventos") or []
    if not lista:
        return "", ""
    items = "".join(f'<li class="ev__item revelar"><p class="ev__fecha t-eyebrow">{e(x.get("fecha"))}</p>'
                    f'<h3 class="des__nombre">{e(x.get("titulo"))}</h3><p class="t-small">{e(x.get("descripcion") or "")}</p></li>' for x in lista)
    html_ = f"""
<section class="seccion" id="eventos" aria-labelledby="eventos-t">
  <div class="contenedor"><div class="cabecera-seccion"><p class="t-eyebrow">{rot(d, "eventos_ceja", "Agenda")}</p><h2 class="t-head" id="eventos-t">{rot(d, "eventos", "Próximamente")}</h2></div>
  <ul role="list" class="ev__lista">{items}</ul></div>
</section>"""
    css = """
.ev__lista { display: grid; gap: 28px; }
@media (min-width: 760px) { .ev__lista { grid-template-columns: repeat(3, 1fr); } }
.ev__item { border-top: 2px solid var(--accent); padding-top: 1rem; display: grid; gap: .5rem; }
"""
    return html_, css


# ---------------------------------------------------------------------------------------------- REGISTRO
# Para Nova y montar.py: que hay, para que sirve y que datos lee. "fotos": la variante necesita fotos reales.
BLOQUES = {
    "cabecera": {"categoria": "comun", "fn": cabecera, "variantes": {"barra": {}, "centrada": {}},
                 "usar": "siempre, primero", "datos": ["negocio.nombre", "reservas"]},
    "hero": {"categoria": "hosteleria", "fn": hero,
             "variantes": {"tipografico": {"fotos": False}, "partido": {"fotos": False}, "foto": {"fotos": True},
                           "video": {"video": True}},
             "usar": "portada: eslogan + descripcion + acción; canvas vivo del motivo si no hay foto/video",
             "datos": ["negocio.eslogan", "negocio.descripcion", "fotos[0]", "video{src,poster}"]},
    "cinta": {"categoria": "comun", "fn": cinta, "variantes": {"nombres": {}}, "usar": "tras la portada: nombres reales en movimiento",
              "datos": ["destacados[].nombre"]},
    "destacados": {"categoria": "hosteleria", "fn": destacados, "variantes": {"tarjetas": {}, "lista": {}, "bento": {}, "zigzag": {"fotos": True}},
                   "usar": "3-6 productos estrella", "datos": ["destacados[]"]},
    "carta": {"categoria": "hosteleria", "fn": carta, "variantes": {"menu": {}},
              "usar": "carta completa con precios y alérgenos", "datos": ["carta[]"]},
    "horario": {"categoria": "hosteleria", "fn": horario, "variantes": {"tabla": {}},
                "usar": "horario con 'abierto ahora'", "datos": ["horario[]"]},
    "reservar": {"categoria": "comun", "fn": reservar, "variantes": {"banda": {}},
                 "usar": "si hay forma de reservar (web, teléfono, WhatsApp)", "datos": ["reservas"]},
    "eventos": {"categoria": "hosteleria", "fn": eventos, "variantes": {"lista": {}}, "usar": "si hay agenda real", "datos": ["eventos[]"]},
    "resenas": {"categoria": "comun", "fn": resenas, "variantes": {"citas": {}}, "usar": "solo con reseñas reales", "datos": ["resenas[]"]},
    "visitanos": {"categoria": "comun", "fn": visitanos, "variantes": {"tarjeta": {}}, "usar": "dirección, mapa y contacto", "datos": ["negocio"]},
    "faq": {"categoria": "comun", "fn": faq, "variantes": {"lista": {}}, "usar": "si hay preguntas reales", "datos": ["faq[]"]},
    "pie": {"categoria": "comun", "fn": pie, "variantes": {"firma": {}}, "usar": "siempre, último", "datos": ["negocio", "legal"]},
}
