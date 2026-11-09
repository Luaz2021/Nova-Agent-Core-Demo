import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
EXTRACTOR: ingeniería inversa automática del diseño de una web.

Abre la web en un navegador real (Playwright), quita ventanas emergentes (chats, cookies),
detecta las secciones y mide de cada una: fondo, textos (tamaño, peso, color, alineación),
botones, imágenes, columnas en escritorio y en móvil. Guarda:
  trabajo/<web>/spec.json                 todo lo medido
  trabajo/<web>/sec_N_escritorio.png      recorte de cada sección (escritorio 1280px)
  trabajo/<web>/sec_N_movil.png           recorte de cada sección (móvil 375px)
  trabajo/<web>/original_escritorio.png   página completa

Uso directo:  python extraer.py https://basecamp.com
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ESCRITORIO = (1920, 1080)
# Un solo móvil y un solo idioma para TODO el motor (extraer, capturar, comparar, explorador...): si cada script
# usara el suyo, las secciones y las fotos de móvil no coincidirían entre la original y el clon.
MOVIL_DISPOSITIVO = "iPhone 14 Pro"
MOVIL = (393, 852)
LOCALE = "es-ES"
MAX_ALTO = 65000  # px máximos de página que se miden (se captura por trozos: Chromium no pasa de ~16.000 por foto)
MAX_SECCIONES = 80
MOVIL_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.5 Mobile/15E148 Safari/604.1"
)


# WebGL en modo sin ventana: Chrome ya no activa solo el renderizado por software, hay que pedirlo
def _blindar_playwright():
    """Webs que se recargan solas una vez (redirecciones, intros): si una medida pilla la recarga, se espera
    a que la página vuelva y se repite, en vez de caerse con 'Execution context was destroyed'."""
    try:
        from playwright.sync_api import Page
    except Exception:
        return
    if getattr(Page, "_clon_blindado", False):
        return

    def envolver(orig):
        def seguro(self, *a, **k):
            for intento in range(3):
                try:
                    return orig(self, *a, **k)
                except Exception as ex:
                    if intento < 2 and re.search(
                        r"context was destroyed|navigating|frame was detached",
                        str(ex),
                        re.IGNORECASE,
                    ):
                        try:
                            self.wait_for_load_state("load", timeout=20000)
                        except Exception:
                            pass
                        self.wait_for_timeout(1500)
                        continue
                    raise

        return seguro

    for nombre in ("evaluate", "add_style_tag", "content"):
        setattr(Page, nombre, envolver(getattr(Page, nombre)))
    Page._clon_blindado = True


_blindar_playwright()

NAV_ARGS = [
    "--ignore-gpu-blocklist",
    "--enable-unsafe-swiftshader",
    "--enable-webgl",
    "--autoplay-policy=no-user-gesture-required",
]


JS_ESPERAR_ANIMACIONES = r"""
(maximo) => { const lista = document.getAnimations().filter(a => { try {
    return a.playState === 'running' && a.timeline === document.timeline && a.effect.getComputedTiming().iterations !== Infinity; } catch (e) { return false; } });
  return Promise.race([Promise.all(lista.map(a => a.finished.catch(() => 0))), new Promise(r => setTimeout(r, maximo))]).then(() => lista.length); }
"""


def esperar_aparecer(page, maximo=1500):
    """Tras llevar una sección a la vista: las webs la hacen aparecer con una animación (fundido, subida...) que
    arranca al verla. Se espera a que acabe (con tope) antes de fotografiarla; si no, la foto de la ORIGINAL sale a
    medias (sin la imagen) y el clon, que sí la tiene, sale castigado."""
    page.wait_for_timeout(250)
    try:
        page.evaluate(JS_ESPERAR_ANIMACIONES, maximo)
        # imágenes perezosas que acaban de entrar en pantalla: que terminen de cargar (con tope)
        page.evaluate(
            """(maximo) => Promise.race([Promise.all([...document.images].filter(i => { const r = i.getBoundingClientRect();
              return !i.complete && r.bottom > 0 && r.top < innerHeight; }).map(i => new Promise(ok => { i.onload = i.onerror = ok; }))),
            new Promise(ok => setTimeout(ok, maximo * 2))])""",
            maximo,
        )
    except Exception:
        page.wait_for_timeout(600)
    page.wait_for_timeout(150)


def foto_seccion(page, n, destino, alto_esperado=None):
    """Foto de la sección n (captura del elemento). Si sale con otra altura que la medida (la web estaba recolocando
    una rejilla por JavaScript, cargando algo...), se espera y se repite hasta 2 veces: se queda la más fiel."""
    loc = page.locator(f'[data-clon-sec="{n}"]')
    if loc.count() == 0:
        return
    el = loc.first
    el.scroll_into_view_if_needed(timeout=2500)
    esperar_aparecer(page)
    # vídeos de la sección que se reproducen una vez (el iPhone Duo que se despliega): la foto, cuando acaben (máx. 8 s);
    # si no, la referencia sale a medias y cada análisis da una foto distinta
    page.evaluate(
        """async (n) => { const vs = [...document.querySelectorAll(`[data-clon-sec="${n}"] video`)].filter(v => !v.loop);
        for (let i = 0; i < 32 && vs.some(v => !v.ended && !v.paused); i++) await new Promise(r => setTimeout(r, 250)); }""",
        n,
    )
    # lo fijo o pegajoso que NO es de esta sección (la cabecera que el tema fija al bajar) saldría pintado encima en
    # la foto, y en el clon no: se oculta mientras se hace la foto
    page.evaluate(JS_TAPAR_FIJOS, n)
    try:
        _foto_comprobada(page, el, Path(destino), alto_esperado)
    finally:
        page.evaluate(
            "() => { for (const [e, v, p] of window.__clonTapados || []) e.style.setProperty('opacity', v, p); window.__clonTapados = []; }"
        )


# con opacity y no con visibility: un hijo con «visibility: visible» (la barra de apple.com en móvil) se seguía viendo
JS_TAPAR_FIJOS = r"""(n) => { const s = document.querySelector(`[data-clon-sec="${n}"]`); window.__clonTapados = [];
  for (const e of document.querySelectorAll('body *')) { const p = getComputedStyle(e).position;
    if ((p === 'fixed' || p === 'sticky') && !s.contains(e) && !e.contains(s)) {
      window.__clonTapados.push([e, e.style.getPropertyValue('opacity'), e.style.getPropertyPriority('opacity')]);
      e.style.setProperty('opacity', '0', 'important'); } } }"""


def _foto_comprobada(page, el, destino, alto_esperado):
    from PIL import Image

    el.screenshot(path=str(destino), timeout=5000)
    if not alto_esperado:
        return
    fuera = lambda h: abs(h - alto_esperado) > max(30, alto_esperado * 0.08)
    mejor = Image.open(destino).height
    for _ in range(2):
        if not fuera(mejor):
            return
        page.wait_for_timeout(1500)
        esperar_aparecer(page)
        otra = destino.with_name("_" + destino.name)
        el.screenshot(path=str(otra), timeout=5000)
        h = Image.open(otra).height
        if abs(h - alto_esperado) < abs(mejor - alto_esperado):
            otra.replace(destino)
            mejor = h
        else:
            otra.unlink(missing_ok=True)


def nombre_web(url):
    """Carpeta de una web dentro de workspace/ (la misma en analizar, explorador_dinamico...)."""
    from urllib.parse import urlparse

    p = urlparse(url)
    host = p.netloc.replace("www.", "") or "local"
    return "".join(c if c.isalnum() else "_" for c in (host + p.path).lower()).strip(
        "_"
    )[:40]


def opciones_movil(pw):
    """Opciones de new_context para el móvil del motor: iPhone 14 Pro (agente, táctil, is_mobile) a 393x852.
    Densidad 1 a propósito: las fotos de la original y las del clon se comparan píxel a píxel (comparar.py
    fotografía el clon a densidad 1); con la x3 del iPhone las alturas no cuadrarían nunca."""
    dev = dict(
        pw.devices.get(MOVIL_DISPOSITIVO)
        or {"user_agent": MOVIL_UA, "is_mobile": True, "has_touch": True}
    )
    dev.pop("default_browser_type", None)
    dev.update(
        viewport={"width": MOVIL[0], "height": MOVIL[1]},
        device_scale_factor=1,
        locale=LOCALE,
    )
    return dev


class PaginaVacia(Exception):
    """La web no cargó contenido: caída, bloqueo anti-bots o página que necesita interacción."""


JS_SALUD = r"""
() => { const t = (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').trim();
  return { texto: t.length, muestra: t.slice(0, 200), nodos: document.querySelectorAll('*').length, titulo: document.title,
           imgs: document.images.length, canvas: document.querySelectorAll('canvas').length, url: location.href }; }
"""
BLOQUEO = re.compile(
    r"access denied|just a moment|verify you are human|are you a robot|captcha|attention required|"
    r"request blocked|forbidden|unusual traffic|enable javascript|checking your browser|cloudflare",
    re.IGNORECASE,
)


def comprobar_pagina(page, estado=None):
    """Espera a que la página tenga contenido (las SPA tardan) y, si no lo tiene, explica por qué."""
    for _ in range(11):  # hasta ~20 s: webs 3D con pantalla de carga
        try:
            sal = page.evaluate(JS_SALUD)
        except Exception:  # la web navegó/recargó mientras mirábamos
            page.wait_for_timeout(2000)
            continue
        if sal["texto"] >= 40 or sal["imgs"] >= 3 or sal["canvas"]:
            break
        page.wait_for_timeout(2000)
    texto = sal["muestra"] + " " + sal["titulo"]
    if estado and estado >= 400:
        raise PaginaVacia(
            f"la web respondió con error {estado}"
            + (" (bloqueo anti-bots)" if estado in (401, 403, 429, 503) else "")
        )
    if BLOQUEO.search(texto) and sal["texto"] < 1500:
        raise PaginaVacia(
            f'la web muestra una pantalla de bloqueo o verificación: "{sal["muestra"][:100]}"'
        )
    if sal["texto"] < 40 and sal["imgs"] < 3 and not sal["canvas"]:
        if sal["nodos"] > 20:
            raise PaginaVacia(
                f"tras 20 s la página sigue sin contenido HTML ({sal['nodos']} elementos, {sal['texto']} letras): "
                "suele ser una experiencia 3D que necesita GPU o un clic para empezar (no se puede clonar con HTML)"
            )
        raise PaginaVacia(
            f"la página llegó vacía ({sal['nodos']} elementos, {sal['texto']} letras de texto): "
            "seguramente bloquea navegadores automáticos o necesita iniciar sesión"
        )
    return sal


FUENTES = {  # fuente original (minúsculas, contiene) -> alternativa gratuita en Google Fonts
    "graphik": "Inter",
    "helvetica": "Inter",
    "swiss": "Inter",
    "arial": "Inter",
    # SF Pro (Apple) es más estrecha que Inter: con Inter los titulares se parten en otra línea. Inter Tight = misma letra, más ajustada
    "sf pro": "Inter Tight",
    "-apple-system": "Inter Tight",
    "system-ui": "Inter Tight",
    "segoe": "Inter",
    "inter": "Inter",
    "futura": "Jost",
    "avenir": "Nunito Sans",
    "gotham": "Montserrat",
    "proxima": "Montserrat",
    "circular": "DM Sans",
    "gt walsheim": "DM Sans",
    "aeonik": "DM Sans",
    "sohne": "Inter",
    "söhne": "Inter",
    "roboto": "Roboto",
    "open sans": "Open Sans",
    "lato": "Lato",
    "poppins": "Poppins",
    "montserrat": "Montserrat",
    "dm sans": "DM Sans",
    "manrope": "Manrope",
    "work sans": "Work Sans",
    "ibm plex": "IBM Plex Sans",
    "space grotesk": "Space Grotesk",
    "nunito": "Nunito Sans",
    "raleway": "Raleway",
    "rubik": "Rubik",
    "georgia": "Lora",
    "times": "Libre Baskerville",
    "garamond": "EB Garamond",
    "playfair": "Playfair Display",
    "canela": "Playfair Display",
    "gt super": "Playfair Display",
    "tiempos": "Source Serif 4",
    "lora": "Lora",
    "merriweather": "Merriweather",
    "mono": "JetBrains Mono",
    "courier": "JetBrains Mono",
    "menlo": "JetBrains Mono",
}

JS_LIMPIAR = r"""
() => {
  const vw = innerWidth, vh = innerHeight, quitados = [];
  const palabras = /(cookie|consent|gdpr|chat|intercom|drift|gorgias|zendesk|hubspot|popup|modal|newsletter-pop|klaviyo|onetrust|banner-pop)/i;
  for (const e of document.querySelectorAll('body *')) {
    const s = getComputedStyle(e);
    if (s.position !== 'fixed' && s.position !== 'sticky') continue;
    const r = e.getBoundingClientRect();
    const id = (e.id + ' ' + e.className).toString();
    const esCabecera = r.top <= 5 && r.height < 320 && r.width > vw * 0.9 && !palabras.test(id);
    if (esCabecera) continue;                 // cabecera fija arriba: se respeta (cambiarla mueve toda la página)
    if (s.position === 'sticky') continue;    // sticky = parte normal de la página, no se toca
    const fondo3d = (e.matches('canvas,video') || e.querySelector('canvas,video')) && r.width * r.height > vw * vh * 0.5
                    && !palabras.test(id) && (e.innerText || '').trim().length < 200;
    if (fondo3d) continue;                    // canvas 3D / vídeo fijo de fondo: es el diseño, no un estorbo
    // scroll virtual (Lusion, webs con scroll suave hecho a mano): TODA la página va dentro de una capa fija
    // que se mueve con transform. No es un estorbo: se devuelve al flujo normal para poder medirla y fotografiarla.
    const altoReal = Math.max(r.height, e.scrollHeight, ...[...e.children].map(c => c.scrollHeight));   // el transform no cambia scrollHeight de los hijos
    const contenido = altoReal > vh * 1.5 && (e.innerText || '').length > 200 && !palabras.test(id);
    if (contenido) { e.setAttribute('data-clon-flujo', ''); for (const c of e.children) c.setAttribute('data-clon-flujo-hijo', '');
      quitados.push('(scroll virtual desplegado)'); continue; }
    if (palabras.test(id) || (r.width * r.height > vw * vh * 0.15) || parseInt(s.zIndex || 0) > 1000 || s.position === 'fixed') {
      quitados.push(id.slice(0, 60)); e.style.setProperty('display', 'none', 'important');
    }
  }
  // gestores de consentimiento y avisos de país/idioma conocidos, estén donde estén (fijos o no, con shadow DOM o iframe)
  const CONOCIDOS = '#onetrust-consent-sdk,#onetrust-banner-sdk,#CybotCookiebotDialog,#usercentrics-root,#usercentrics-cmp-ui,#didomi-host,'
    + '.qc-cmp2-container,iframe[id^="sp_message"],[id^="sp_message_container"],#truste-consent-track,.truste_box_overlay,#cmplz-cookiebanner-container,'
    + '.cky-consent-container,.cky-overlay,#cookie-law-info-bar,#iubenda-cs-banner,#axeptio_overlay,#tarteaucitronRoot,.osano-cm-window,'
    + '#ac-localeswitcher,[id*="locale-switcher" i],[class*="locale-switcher" i],[class*="country-selector" i],[id*="geo-banner" i],[class*="geo-banner" i]';
  for (const e of document.querySelectorAll(CONOCIDOS)) { e.style.setProperty('display', 'none', 'important'); quitados.push((e.id || e.className || 'consent').toString().slice(0, 40)); }
  // aviso de país arriba del todo: bloque bajo con un <select> o botón "Continue/Continuar" y palabras de país/región
  for (const e of [...document.body.children].slice(0, 6)) { const r = e.getBoundingClientRect(); const t = (e.innerText || '').slice(0, 300);
    if (r.top < 150 && r.height < 200 && /country|region|país|región|pays|regione/i.test(t) && (e.querySelector('select') || /continu/i.test(t))) {
      e.style.setProperty('display', 'none', 'important'); quitados.push('aviso de país'); } }
  for (const x of [document.documentElement, document.body]) { x.style.setProperty('overflow', 'visible', 'important'); x.classList.remove('no-scroll', 'noscroll', 'overflow-hidden', 'modal-open'); }
  for (const f of document.querySelectorAll('iframe')) {
    const r = f.getBoundingClientRect();
    if (r.width < vw * 0.6) { f.style.setProperty('display', 'none', 'important'); quitados.push('iframe'); }
  }
  if (document.querySelector('[data-clon-flujo]') && !document.getElementById('clon-flujo')) {
    const st = document.createElement('style'); st.id = 'clon-flujo';
    st.textContent = '[data-clon-flujo]{position:relative!important;inset:auto!important;height:auto!important;max-height:none!important;overflow:visible!important;transform:none!important}'
                   + '[data-clon-flujo-hijo]{transform:none!important;will-change:auto!important}';
    document.head.appendChild(st);
  }
  document.documentElement.style.scrollBehavior = 'auto';
  return quitados.slice(0, 20);
}
"""

JS_COMUN = r"""
  const cajaDe = (e) => {
    const r = e.getBoundingClientRect(); let top = r.top, bottom = r.bottom, left = r.left, right = r.right;
    if (r.height < 40) {
      for (const d of [...e.querySelectorAll('*')].slice(0, 400)) {
        const q = d.getBoundingClientRect(); if (q.width < 2 || q.height < 2) continue;
        top = Math.min(top, q.top); bottom = Math.max(bottom, q.bottom); left = Math.min(left, q.left); right = Math.max(right, q.right);
      }
    }
    return { top: top + scrollY, bottom: bottom + scrollY, height: bottom - top, width: right - left, left };
  };
"""

JS_SECCIONES = (
    r"""
(maxSec) => {
"""
    + JS_COMUN
    + r"""
  const oculto = (e) => { const s = getComputedStyle(e); return s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0'
    || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'DIALOG', 'LINK', 'META'].includes(e.tagName); };
  // hijos reales: los display:contents se sustituyen por sus hijos
  const hijosReales = (e) => { const out = []; for (const c of e.children) { if (oculto(c)) continue;
      if (getComputedStyle(c).display === 'contents') out.push(...hijosReales(c)); else out.push(c); } return out; };
  const visible = (e) => { const c = cajaDe(e); return c.height >= 40 && c.width >= innerWidth * 0.5; };
  const hijos = (e) => hijosReales(e).filter(visible);
  const aplanar = (e) => { let h = hijos(e); while (h.length === 1 && cajaDe(h[0]).height > cajaDe(e).height * 0.85) { e = h[0]; h = hijos(e); } return e; };
  let lista = [];
  const expandir = (e, nivel) => {
    e = aplanar(e);
    for (const h of hijos(e)) {
      const hh = hijos(aplanar(h));
      if ((h.tagName === 'MAIN' || cajaDe(h).height > innerHeight * 1.6) && hh.length > 1 && nivel < 3) expandir(h, nivel + 1);
      else lista.push(h);
    }
  };
  expandir(document.body, 0);
  // fuera: capas gigantes sin texto (fondos decorativos que abarcan varias secciones)
  lista = lista.filter(e => !(cajaDe(e).height > innerHeight * 1.6 && !(e.innerText || '').trim() && !e.querySelector('img,svg,video')));
  // fuera: capas fijas sin texto (canvas 3D o vídeo de fondo): son fondo, no secciones
  lista = lista.filter(e => { const r = e.getBoundingClientRect(); const cab = ['HEADER', 'NAV'].includes(e.tagName) || (r.top <= 5 && r.height < 320);
    return cab || !(getComputedStyle(e).position === 'fixed' && (e.innerText || '').trim().length < 20); });
  // orden del documento (no por posición: un hero que se mete por detrás de la cabecera empieza en y=0)
  lista.sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1);
  // capas: bloques metidos dentro de otro anterior (texto encima de un hero). No son secciones:
  // se marcan como capa de la sección que los contiene y sus textos cuentan para ella.
  document.querySelectorAll('[data-clon-capa]').forEach(e => e.removeAttribute('data-clon-capa'));
  document.querySelectorAll('[data-clon-sec]').forEach(e => e.removeAttribute('data-clon-sec'));
  const fijo = (e) => ['fixed', 'sticky'].includes(getComputedStyle(e).position) || ['HEADER', 'NAV'].includes(e.tagName);
  const limpia = [], capas = [];
  for (const e of lista) {
    const c = cajaDe(e);
    const madre = fijo(e) ? null : limpia.find(p => { const q = cajaDe(p); return !fijo(p) && q.height > c.height && Math.min(c.bottom, q.bottom) - Math.max(c.top, q.top) >= Math.max(c.height * 0.8, 1); });
    if (madre) capas.push([e, madre]); else limpia.push(e);
  }
  const final = limpia.slice(0, maxSec);
  final.forEach((e, i) => e.setAttribute('data-clon-sec', String(i + 1)));
  for (const [e, m] of capas) if (m.dataset.clonSec) e.setAttribute('data-clon-capa', m.dataset.clonSec);
  return final.length;
}
"""
)

JS_MEDIR = (
    r"""
() => {
"""
    + JS_COMUN
    + r"""
  const rgb2hex = (c) => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); if (p.length > 3 && p[3] === 0) return null;
    return '#' + p.slice(0, 3).map(x => Math.round(x).toString(16).padStart(2, '0')).join('').toUpperCase(); };
  const fondo = (e) => {
    // 1) el propio elemento o un hijo que lo cubre casi entero  2) si no, el primer antepasado con color
    let x = e;
    for (let i = 0; i < 4 && x; i++) {
      const h = rgb2hex(getComputedStyle(x).backgroundColor); if (h) return h;
      const R = x.getBoundingClientRect();
      x = [...x.children].find(c => { const r = c.getBoundingClientRect(); return r.height > R.height * 0.8 && r.width > R.width * 0.8; });
    }
    for (let y = e.parentElement; y; y = y.parentElement) { const h = rgb2hex(getComputedStyle(y).backgroundColor); if (h) return h; }
    return null; };   // ningún color en el CSS: lo que se ve lo pinta otra cosa (canvas, vídeo) o es el blanco del navegador
  // canvas 3D o vídeo fijo detrás de la página: el color de fondo real no está en el CSS
  const fondoFijo = [...document.querySelectorAll('canvas,video')].some(c => { const r = c.getBoundingClientRect();
    let fijo = false; for (let x = c; x && x !== document.body; x = x.parentElement) if (getComputedStyle(x).position === 'fixed') { fijo = true; break; }
    return fijo && r.width * r.height > innerWidth * innerHeight * 0.5; });
  const columnasDe = (sec) => {
    const W = sec.getBoundingClientRect().width || innerWidth; let max = 1;
    const conts = [sec, ...sec.querySelectorAll('*')].filter(e => e.children.length >= 2).slice(0, 600);
    for (const e of conts) {
      const items = [...e.children].map(c => c.getBoundingClientRect()).filter(r => r.height > 40 && r.width >= W * 0.12 && r.width < W * 0.95);
      // misma fila: arriba, centro o abajo alineados (items-center / items-end dejan los "top" distintos)
      const fila = (a, b) => Math.abs(b.top - a.top) < 30 || Math.abs(b.bottom - a.bottom) < 30 || Math.abs((b.top + b.bottom) - (a.top + a.bottom)) < 60;
      for (const a of items) max = Math.max(max, items.filter(b => fila(a, b) && (b === a || b.left >= a.right - 4 || b.right <= a.left + 4)).length);
    }
    return Math.min(max, 12); };
  const unidad = (e, sec) => { let u = e;
    for (let k = 0; k < 3; k++) { const p = u.parentElement; if (!p || p === sec) break;
      const hs = [...p.children]; if (hs.length < 2 || (p.innerText || '').length > 300) break;
      const fs = parseFloat(getComputedStyle(e).fontSize) || 16;
      const palabras = hs.every(h => { const tx = (h.innerText || '').trim(); return tx && !/\s/.test(tx) && getComputedStyle(h).display.startsWith('inline')
                                       && h.getBoundingClientRect().height < fs * 2.5; });
      // pegadas como palabras de una frase (hueco ~ un espacio en cada línea), no enlaces de menú separados.
      // En móvil la frase puede ocupar varias líneas (una palabra por línea): se mira línea a línea.
      const cajas = hs.map(h => h.getBoundingClientRect()).sort((a, b) => a.top - b.top || a.left - b.left);
      const juntas = cajas.every((q, i) => i === 0 || Math.abs(q.top - cajas[i - 1].top) >= 4 || q.left - cajas[i - 1].right < fs * 0.6);
      const sinEnlaces = !hs.some(h => ['A', 'BUTTON', 'LI', 'IMG'].includes(h.tagName));
      if (palabras && juntas && sinEnlaces) u = p; else break; }
    return u; };
  const sy = scrollY;
  const out = [];
  let finAnterior = 0;
  const lista = [...document.querySelectorAll('[data-clon-sec]')].sort((a, b) => +a.dataset.clonSec - +b.dataset.clonSec);
  for (const sec of lista) {
    const C = cajaDe(sec);
    const arriba = Math.max(C.top, finAnterior);           // sin solapes: cada sección empieza donde acabó la anterior
    finAnterior = Math.max(finAnterior, C.bottom);
    const R = { top: arriba - sy, left: 0, height: Math.max(0, C.bottom - arriba), width: C.width };
    const S = getComputedStyle(sec);
    const esCarrusel = sec.scrollWidth > sec.clientWidth + 20 || !![...sec.querySelectorAll('*')].find(e => e.scrollWidth > e.clientWidth + 20 && e.children.length >= 3);
    const esGrid = S.display === 'grid' || S.display === 'inline-grid';
    let esBento = false;
    if (esGrid && sec.children.length >= 3) {
      const hs = [...sec.children].map(c => c.getBoundingClientRect());
      const ws = new Set(hs.map(h => Math.round(h.width / 40)));
      esBento = ws.size > 1;
    }
    const topologia = esCarrusel ? 'carrusel_horizontal' : (esBento ? 'bento_grid' : (columnasDe(sec) > 1 ? 'grid_columnas' : 'pila_vertical'));
    const bgImg = (S.backgroundImage || '').match(/url\(["']?([^"')]+)/);
    // y_caja/alto_caja: la caja propia, con solapes (cabecera transparente encima de la portada). Las fotos de la
    // original se hacen así (captura del elemento): el clon se recorta igual para comparar lo mismo
    const info = { n: +sec.dataset.clonSec, tag: sec.tagName.toLowerCase(), y: Math.round(R.top + sy), alto: Math.round(R.height), ancho: Math.round(R.width),
      y_caja: Math.round(C.top), alto_caja: Math.round(C.bottom - C.top),
      fondo: fondo(sec) || '#FFFFFF', fondo_dudoso: fondoFijo, imagen_fondo: bgImg ? bgImg[1] : null, textos: [], botones: [], imagenes: [] };
    // textos: elementos con texto propio
    const vistos = new Set();
    const enScrollSec = sec.scrollWidth > innerWidth + 10;
    const capas = [...document.querySelectorAll(`[data-clon-capa="${sec.dataset.clonSec}"]`)];
    for (const e of [sec, ...sec.querySelectorAll('*'), ...capas.flatMap(c => [c, ...c.querySelectorAll('*')])]) {
      const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
      const enScrollH = e.closest('[style*="overflow"], [class*="overflow"], [class*="scroll"], [class*="shelf"], [class*="carousel"], [class*="slider"], [class*="gallery"]') || (sec.scrollWidth > innerWidth + 10);
      const enScrollH2 = enScrollSec || e.closest('[style*="overflow"], [class*="overflow"], [class*="scroll"], [class*="shelf"], [class*="carousel"], [class*="slider"], [class*="gallery"]');
      if (!enScrollH2 && (r.right <= 0 || r.left >= innerWidth)) continue;
      const s = getComputedStyle(e); if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) continue;
      if (e.closest('[aria-hidden="true"]')) continue;
      let oculto = false; for (let x = e.parentElement; x && x !== sec.parentElement; x = x.parentElement) { if (+getComputedStyle(x).opacity === 0) { oculto = true; break; } }
      if (oculto) continue;
      const propio = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').replace(/\s+/g, ' ').trim();
      // texto animado palabra a palabra (o letra a letra): se sube hasta la línea completa
      const u = propio.length >= 1 ? unidad(e, sec) : e;
      if (propio.length >= 2 || (u !== e && propio.length >= 1)) {
        const t = (u === e ? e.innerText : [...u.children].map(c => (c.innerText || '').trim()).join(' ')).replace(/\s+/g, ' ').trim().slice(0, 160);
        const ru = u === e ? r : u.getBoundingClientRect();
        if (!t || vistos.has(t)) continue; vistos.add(t);
        info.textos.push({ t, tag: (u === e ? e : u).tagName.toLowerCase(), px: Math.round(parseFloat(s.fontSize)), peso: +s.fontWeight || 400,
          color: rgb2hex(s.color), fuente: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), may: s.textTransform === 'uppercase',
          alinea: s.textAlign, espaciado: s.letterSpacing === 'normal' ? 0 : Math.round(parseFloat(s.letterSpacing) * 100) / 100,
          lh: s.lineHeight === 'normal' ? null : Math.round(parseFloat(s.lineHeight)),
          x: Math.round(ru.left - R.left), y: Math.round(ru.top - R.top), w: Math.round(ru.width) });
      }
      const esBoton = (e.tagName === 'A' || e.tagName === 'BUTTON') && rgb2hex(s.backgroundColor) && e.innerText.trim().length > 1 && r.height < 90;
      if (esBoton && info.botones.length < 6) info.botones.push({ t: e.innerText.replace(/\s+/g, ' ').trim().slice(0, 60), fondo: rgb2hex(s.backgroundColor),
        color: rgb2hex(s.color), radio: Math.round(parseFloat(s.borderRadius) || 0), pad: s.padding, px: Math.round(parseFloat(s.fontSize)), peso: +s.fontWeight,
        w: Math.round(r.width), h: Math.round(r.height) });
      const reproductor = e.shadowRoot && e.shadowRoot.querySelector('video');      // <video> escondido en shadow DOM (mux-player…)
      if ((e.tagName === 'IMG' || e.tagName === 'SVG' || e.tagName === 'VIDEO' || e.tagName === 'PICTURE' || reproductor) && r.width >= 40 && r.height >= 30 && info.imagenes.length < 40) {
        info.imagenes.push({ tipo: reproductor ? 'video' : e.tagName.toLowerCase(), src: e.currentSrc || e.src || '', alt: e.alt || '', x: Math.round(r.left - R.left), y: Math.round(r.top - R.top),
          w: Math.round(r.width), h: Math.round(r.height), redonda: (parseFloat(s.borderRadius) || 0) >= r.width / 2 - 1 });
      }
    }
    // menús que aparecen con una animación (opacidad 0 al cargar): si no salió ningún texto, segunda pasada sin ese filtro
    if (!info.textos.length) for (const e of sec.querySelectorAll('a,button,span,p,li,h1,h2,h3,h4')) {
      const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
      const enScrollH2 = enScrollSec || e.closest('[style*="overflow"], [class*="overflow"], [class*="scroll"], [class*="shelf"], [class*="carousel"], [class*="slider"], [class*="gallery"]');
      if (!enScrollH2 && (r.right <= 0 || r.left >= innerWidth)) continue;
      const s = getComputedStyle(e); if (s.display === 'none') continue;
      const propio = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').replace(/\s+/g, ' ').trim();
      if (propio.length < 2) continue; const t = e.innerText.replace(/\s+/g, ' ').trim().slice(0, 160);
      if (!t || vistos.has(t)) continue; vistos.add(t);
      info.textos.push({ t, tag: e.tagName.toLowerCase(), px: Math.round(parseFloat(s.fontSize)), peso: +s.fontWeight || 400, color: rgb2hex(s.color),
        fuente: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), may: s.textTransform === 'uppercase', alinea: s.textAlign, espaciado: 0, lh: null,
        x: Math.round(r.left - R.left), y: Math.round(r.top - R.top), w: Math.round(r.width) });
      if (info.textos.length >= 20) break; }
    // ordenar textos por posición y quedarse con los más importantes
    info.textos.sort((a, b) => a.y - b.y || a.x - b.x);
    info.total_textos = info.textos.length;
    // ESTRUCTURA: carrusel horizontal y texto encima de una imagen/vídeo grande
    info.carrusel = [sec, ...sec.querySelectorAll('*')].slice(0, 1500).some(e => {
      const k = (typeof e.className === 'string' ? e.className : '') + ' ' + (e.id || '');
      if (/swiper-wrapper|slick-track|splide__list|flickity-slider|embla__container|carousel-track|glide__slides/i.test(k)) return true;
      if (e.children.length < 3 || e.clientWidth < 200) return false;
      const ox = getComputedStyle(e).overflowX;
      return e.scrollWidth > e.clientWidth * 1.15 && ox !== 'visible';
    });
    const medios = [...sec.querySelectorAll('img,video,canvas,picture')].map(m => m.getBoundingClientRect())
      .filter(q => q.width * q.height > Math.max(R.width * R.height * 0.3, 40000));
    info.superpuesto = info.textos.some(t => { const cx = R.left + t.x + Math.min(t.w, 200) / 2, cy = R.top + t.y + 5;
      return medios.some(q => cx > q.left && cx < q.right && cy > q.top && cy < q.bottom); });
    if (info.textos.length > 70) {
      const imp = [...info.textos].sort((a, b) => b.px - a.px).slice(0, 70);
      info.textos = info.textos.filter(t => imp.includes(t));
    }
    info.columnas = columnasDe(sec);
    info.alineacion = (() => { const c = info.textos.slice(0, 3).map(t => t.alinea); return c.filter(a => a === 'center').length >= 2 ? 'centrado' : 'izquierda'; })();
    out.push(info);
  }
  const fondoPag = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight,
    ...out.map(s => s.y + s.alto), ...[...document.querySelectorAll('body *')].slice(0, 4000).map(e => e.scrollHeight > e.clientHeight + 50 && e.clientHeight > innerHeight * 0.8 ? e.scrollHeight : 0));
  return { secciones: out, alto_total: fondoPag, titulo: document.title,
           fondo_body: fondo(document.body) || '#FFFFFF', fondo_fijo: fondoFijo, lang: document.documentElement.lang || 'en' };
}
"""
)


_CACHE_GOOGLE = Path(__file__).resolve().parent / "fuentes_google_cache.json"
_EN_GOOGLE = None


def esta_en_google(nombre):
    """¿La fuente original es de Google Fonts? (Plus Jakarta Sans, Montserrat...) Se pregunta una vez y se guarda."""
    global _EN_GOOGLE
    nombre = (nombre or "").strip().strip("\"'")
    if (
        not nombre
        or nombre.startswith("-")
        or nombre.lower()
        in ("sans-serif", "serif", "monospace", "system-ui", "inherit")
    ):
        return False
    if _EN_GOOGLE is None:
        try:
            _EN_GOOGLE = json.loads(_CACHE_GOOGLE.read_text(encoding="utf-8"))
        except Exception:
            _EN_GOOGLE = {}
    if nombre not in _EN_GOOGLE:
        import urllib.request
        import urllib.error

        try:
            url = "https://fonts.googleapis.com/css2?family=" + nombre.replace(" ", "+")
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=8,
            ) as r:
                # solo el catálogo libre (fonts.gstatic.com/s/...): Google también sirve algunas de pago
                # (Helvetica Neue) por /l/font?kit=..., y esas no cuentan
                _EN_GOOGLE[nombre] = (
                    r.status == 200
                    and "fonts.gstatic.com/s/" in r.read().decode("utf-8", "replace")
                )
        except urllib.error.HTTPError:
            _EN_GOOGLE[nombre] = False  # 400: no existe en Google Fonts
        except Exception:
            return False  # sin red: no se apunta, se volverá a preguntar
        try:
            _CACHE_GOOGLE.write_text(
                json.dumps(_EN_GOOGLE, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except Exception:
            pass
    return _EN_GOOGLE[nombre]


def fuente_google(nombre):
    # si la web ya usa una fuente de Google Fonts, la misma (la mejor sustituta es ella misma)
    if esta_en_google(nombre):
        return (nombre or "").strip().strip("\"'")
    n = (nombre or "").lower()
    for k, v in FUENTES.items():
        if k in n:
            return v
    if "serif" in n and "sans" not in n:
        return "Lora"
    return "Inter"


def color_dominante(img):
    """Color medio de una imagen PIL, en hex."""
    from PIL import ImageStat

    r, g, b = (
        int(v) for v in ImageStat.Stat(img.convert("RGB").resize((24, 24))).mean[:3]
    )
    return f"{r:02X}{g:02X}{b:02X}"


def preparar_pagina(page, url):
    estado = None
    try:
        r = page.goto(url, wait_until="networkidle", timeout=45000)
        estado = r.status if r else None
    except Exception:
        page.wait_for_timeout(4000)
    page.wait_for_timeout(1500)
    comprobar_pagina(page, estado)
    for intento in range(
        2
    ):  # si la web se recarga sola a mitad (redirecciones, intro), se repite una vez
        try:
            _preparar(page)
            return
        except Exception as ex:
            if intento == 0 and re.search(
                r"context was destroyed|navigat|Target closed", str(ex), re.IGNORECASE
            ):
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    page.wait_for_timeout(3000)
                continue
            raise


def _preparar(page):
    page.add_style_tag(content=CSS_DESPLEGAR + CSS_PINTAR)
    page.evaluate(JS_DESPLEGAR)
    page.evaluate(JS_LIMPIAR)
    page.evaluate(JS_PEREZOSAS)
    # bajar poco a poco para que carguen imágenes perezosas y animaciones (releyendo el alto: la página crece al cargar)
    y, inicial = 0, page.evaluate("document.documentElement.scrollHeight")
    while y < min(page.evaluate("document.documentElement.scrollHeight"), MAX_ALTO):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(110)
        y += 600
    final = page.evaluate(
        "Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)"
    )
    page.evaluate(
        f"window.__clonInfinita = {str(final > MAX_ALTO and final > inicial * 1.5).lower()}; window.__clonAltoReal = {final}"
    )
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(800)
    page.evaluate(JS_LIMPIAR)
    page.evaluate(JS_PEREZOSAS)
    page.evaluate(JS_REVELAR)
    try:
        page.evaluate("document.fonts && document.fonts.ready.then(() => true)")
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.add_style_tag(
        content="*{animation:none!important;transition:none!important;caret-color:transparent!important}"
    )


CSS_DESPLEGAR = "html,body{height:auto!important;max-height:none!important;min-height:0!important;overflow:visible!important}"
# content-visibility:auto deja sin pintar lo que está fuera de pantalla (huecos en blanco en la captura completa)
CSS_PINTAR = (
    "*{content-visibility:visible!important;contain-intrinsic-size:none!important}"
)
JS_PEREZOSAS = r"""
() => { let n = 0;
  for (const e of document.querySelectorAll('img[loading="lazy"],iframe[loading="lazy"]')) { e.loading = 'eager'; n++; }
  for (const e of document.querySelectorAll('img[data-src],img[data-lazy-src],img[data-original],source[data-srcset],img[data-srcset]')) {
    const src = e.dataset.src || e.dataset.lazySrc || e.dataset.original; if (src && (!e.getAttribute('src') || e.src.startsWith('data:'))) { e.src = src; n++; }
    if (e.dataset.srcset) { e.srcset = e.dataset.srcset; n++; } }
  for (const e of document.querySelectorAll('[data-bg],[data-background-image]')) { const u = e.dataset.bg || e.dataset.backgroundImage; if (u && !e.style.backgroundImage) e.style.backgroundImage = `url("${u}")`; }
  return n; }
"""
# animaciones de "aparecer al hacer scroll": solo los elementos marcados por esas librerías se fuerzan visibles
JS_REVELAR = r"""
() => { const sel = '[data-aos],[data-sal],[data-scroll],[data-animate],[data-animation],[data-reveal],[data-w-id],[data-framer-appear-id],.aos-init,.wow,.reveal,.fade-in,.fadeIn,.fade-up,.animate__animated,[class*="sr-"],[class*="reveal"],[class*="fade-in"],[class*="appear"],[class*="in-view"],[class*="inview"]';
  let n = 0;
  for (const e of document.querySelectorAll(sel)) { const s = getComputedStyle(e);
    if (+s.opacity < 0.05 || s.visibility === 'hidden' || (s.transform !== 'none' && +s.opacity < 1)) {
      e.style.setProperty('opacity', '1', 'important'); e.style.setProperty('visibility', 'visible', 'important');
      e.style.setProperty('transform', 'none', 'important'); e.style.setProperty('clip-path', 'none', 'important'); n++; } }
  return n; }
"""
JS_DESPLEGAR = r"""
() => { let n = 0;
  for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e);
    if (['auto', 'scroll', 'hidden'].includes(s.overflowY) && e.scrollHeight > e.clientHeight + 100 && e.clientHeight > innerHeight * 0.7 && e.clientWidth > innerWidth * 0.9) {
      e.style.setProperty('height', 'auto', 'important'); e.style.setProperty('max-height', 'none', 'important'); e.style.setProperty('overflow', 'visible', 'important'); n++; } }
  return n; }
"""


JS_FONDO_FIJO = r"""
(alto) => { let n = 0;   // vídeo fijo de fondo: en la captura completa solo saldría en la primera pantalla
  for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e); if (s.position !== 'fixed') continue;
    const r = e.getBoundingClientRect(); if (r.width * r.height < innerWidth * innerHeight * 0.5) continue;
    if (!(e.matches('video,mux-player') || e.querySelector('video,mux-player'))) continue;
    e.style.setProperty('position', 'absolute', 'important'); e.style.setProperty('top', '0', 'important');
    e.style.setProperty('height', alto + 'px', 'important'); e.style.setProperty('bottom', 'auto', 'important'); n++;
    for (const v of e.querySelectorAll('video')) v.style.setProperty('object-fit', 'cover', 'important'); }
  return n; }
"""


def _foto_completa(page, ruta, ancho, alto, trozo=8000):
    """Página completa por trozos de ≤8.000 px pegados (Chromium no saca fotos de más de ~16.000 px)."""
    from PIL import Image

    alto = max(int(alto or 0), 1)
    try:
        return _foto_trozos(page, ruta, ancho, alto, trozo)
    except Exception as ex:
        if "Clipped area" not in str(ex):
            raise
        # webs raras (scroll horizontal, alto 0): foto sin recorte y se ajusta al tamaño pedido
        page.screenshot(path=str(ruta), full_page=True)
        im = Image.open(ruta).convert("RGB")
        lienzo = Image.new("RGB", (ancho, max(alto, 1)), "white")
        lienzo.paste(
            im.crop((0, 0, min(ancho, im.width), min(alto, im.height))), (0, 0)
        )
        lienzo.save(ruta)
        return min(alto, im.height)


def _foto_trozos(page, ruta, ancho, alto, trozo):
    from PIL import Image

    if alto <= trozo:
        page.screenshot(
            path=str(ruta),
            full_page=True,
            clip={"x": 0, "y": 0, "width": ancho, "height": alto},
        )
        return Image.open(ruta).height
    lienzo = Image.new("RGB", (ancho, alto), "white")
    tmp = Path(str(ruta) + ".trozo.png")
    hecho = 0
    for y in range(0, alto, trozo):
        h = min(trozo, alto - y)
        page.screenshot(
            path=str(tmp),
            full_page=True,
            clip={"x": 0, "y": y, "width": ancho, "height": h},
        )
        t = Image.open(tmp).convert("RGB")
        lienzo.paste(t, (0, y))
        hecho = y + t.height
    tmp.unlink(missing_ok=True)
    lienzo.save(ruta)
    return hecho


def capturar(page, ruta, ancho, alto):
    """Captura de página completa y, después, la página vuelve a su sitio: para la foto, Chromium estira la ventana a
    toda la página y las rejillas que se colocan por JavaScript (isotope, masonry...) se recolocan para esa ventana
    gigante y no vuelven solas (una rejilla de proyectos pasaba de 928 a 1348 px y las fotos de sección salían mal)."""
    try:
        _capturar(page, ruta, ancho, alto)
    finally:
        try:
            page.evaluate("window.dispatchEvent(new Event('resize'))")
            page.wait_for_timeout(800)
        except Exception:
            pass


def _capturar(page, ruta, ancho, alto):
    """Captura de página completa (por trozos si es muy larga). Si la web hace scroll dentro de <body> y solo sale
    la primera pantalla, se despliega el body y, si aun así falla, se pega la página bajando el scroll."""
    from PIL import Image

    try:
        page.evaluate(JS_FONDO_FIJO, alto)
    except Exception:
        pass
    if _foto_completa(page, ruta, ancho, alto) >= alto * 0.95:
        return
    page.add_style_tag(content=CSS_DESPLEGAR)
    page.wait_for_timeout(500)
    if _foto_completa(page, ruta, ancho, alto) >= alto * 0.95:
        return
    vh = page.evaluate("innerHeight")
    # ¿se puede bajar de verdad? si el scroll no se mueve, pegar trozos repetiría la primera pantalla: se queda lo que hay
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_timeout(200)
    if (
        page.evaluate(
            "Math.max(scrollY, document.scrollingElement ? document.scrollingElement.scrollTop : 0)"
        )
        < 100
    ):
        page.evaluate("window.scrollTo(0, 0)")
        return
    lienzo = Image.new("RGB", (ancho, alto), "white")
    tmp = Path(str(ruta) + ".trozo.png")
    for y in range(0, alto, vh):
        page.evaluate(f"""(() => {{ const y = {y}; window.scrollTo(0, y);
            for (const e of [document.scrollingElement, document.body, document.documentElement]) if (e) e.scrollTop = y; }})()""")
        page.wait_for_timeout(250)
        page.screenshot(path=str(tmp))
        trozo = Image.open(tmp).convert("RGB")
        lienzo.paste(trozo.crop((0, 0, ancho, min(vh, alto - y))), (0, y))
    tmp.unlink(missing_ok=True)
    page.evaluate("window.scrollTo(0,0)")
    lienzo.save(ruta)


def fondo_pixeles(img):
    """Color de fondo REAL de un recorte (lo que se ve, aunque lo pinte un canvas 3D o una imagen):
    el color más repetido en los bordes izquierdo y derecho. None si no hay uno claro."""
    from collections import Counter

    im = img.convert("RGB")
    w, h = im.size
    if w < 40 or h < 10:
        return None
    franjas = [im.crop((0, 0, 24, h)), im.crop((w - 24, 0, w, h))]
    cuenta = Counter()
    for f in franjas:
        f = f.resize((6, min(200, max(4, h // 8))))
        cuenta.update((r // 8 * 8, g // 8 * 8, b // 8 * 8) for r, g, b in f.getdata())
    (r, g, b), n = cuenta.most_common(1)[0]
    if n / sum(cuenta.values()) < 0.35:
        return None
    return f"#{min(r + 4, 255):02X}{min(g + 4, 255):02X}{min(b + 4, 255):02X}"


def _dist_hex(a, b):
    a, b = a.lstrip("#"), b.lstrip("#")
    return sum(abs(int(a[i : i + 2], 16) - int(b[i : i + 2], 16)) for i in (0, 2, 4))


def recortar(captura, seccs, sufijo, carpeta):
    from PIL import Image

    if not Path(captura).exists():
        return
    try:
        img = Image.open(captura)
    except Exception:
        return
    for s in seccs:
        destino = carpeta / f"sec_{s['n']}_{sufijo}.png"
        if not destino.exists():
            y0, y1 = (
                max(0, s.get("y_" + sufijo, 0)),
                min(img.height, s.get("y_" + sufijo, 0) + s.get("alto_" + sufijo, 100)),
            )
            if y1 - y0 >= 10:
                try:
                    rec = img.crop((0, y0, img.width, y1))
                    rec.save(destino)
                except Exception:
                    pass
        if destino.exists():
            try:
                rec = Image.open(destino)
                if sufijo == "escritorio":
                    real = fondo_pixeles(rec)
                    if (
                        real
                        and s.get("fondo")
                        and s.get("fondo_dudoso")
                        and _dist_hex(real, s["fondo"]) > 60
                    ):
                        s["fondo_css"], s["fondo"] = s["fondo"], real
                    for im in s.get("imagenes", []):
                        caja = (im["x"], im["y"], im["x"] + im["w"], im["y"] + im["h"])
                        try:
                            im["color"] = color_dominante(rec.crop(caja))
                        except Exception:
                            im["color"] = "DDDDDD"
                    if s.get("imagen_fondo"):
                        s["color_imagen_fondo"] = color_dominante(rec)
            except Exception:
                pass


def recargar_medios(page):
    """Tras cambiar el tamaño de la ventana, las webs cambian de imagen/vídeo (srcset, fuentes móviles) y los cargan al verlos:
    se vuelve a recorrer la página para que todo esté cargado antes de medir y fotografiar (si no, la foto sale en blanco)."""
    page.wait_for_timeout(800)
    page.evaluate(JS_PEREZOSAS)
    alto = min(page.evaluate("document.documentElement.scrollHeight"), MAX_ALTO)
    for y in range(0, alto, 500):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(90)
    page.evaluate("window.scrollTo(0, 0)")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.evaluate("""() => Promise.all([...document.images].filter(i => !i.complete).slice(0, 80)
        .map(i => new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 4000); })))""")
    page.evaluate(JS_REVELAR)
    page.wait_for_timeout(600)


JS_FIRMAS = r"""
() => [...document.querySelectorAll('[data-clon-sec]')].map(e => { const r = e.getBoundingClientRect();
  let t = (e.innerText || '');
  for (const c of document.querySelectorAll(`[data-clon-capa="${e.dataset.clonSec}"]`)) t += '\n' + (c.innerText || '');
  return { n: +e.dataset.clonSec, y: Math.round(r.top + scrollY), texto: t.replace(/\s+/g, ' ').slice(0, 30000) }; })
"""
JS_RENUMERAR = r"""
(mapa) => { const capas = [...document.querySelectorAll('[data-clon-capa]')].map(c => [c, c.dataset.clonCapa]);
  const secs = [...document.querySelectorAll('[data-clon-sec]')].map(e => [e, e.dataset.clonSec]);
  for (const [e, n] of secs) { if (mapa[n]) e.setAttribute('data-clon-sec', mapa[n]); else e.removeAttribute('data-clon-sec'); }
  for (const [c, n] of capas) { if (mapa[n]) c.setAttribute('data-clon-capa', mapa[n]); else c.removeAttribute('data-clon-capa'); }
  return Object.keys(mapa).length; }
"""


# La "ruta" de cada sección en el DOM de PC (id, etiqueta+clases y posición en el árbol). En otra carga (móvil,
# explorador, captura) se busca ese MISMO elemento: es más fiable que volver a cortar la página, porque en móvil un
# bloque alto (el pie de Apple) se parte en 6 trozos y ninguno comparte texto suficiente para emparejarlo.
JS_RUTAS = r"""
() => [...document.querySelectorAll('[data-clon-sec]')].map(e => {
  const p = [];
  for (let x = e; x && x !== document.body; x = x.parentElement) {
    let i = 1; for (let h = x.previousElementSibling; h; h = h.previousElementSibling) if (h.tagName === x.tagName) i++;
    p.unshift(`${x.tagName.toLowerCase()}:nth-of-type(${i})`); }
  const clases = [...e.classList].filter(c => /^[A-Za-z_][\w-]*$/.test(c) && !c.startsWith('data-clon')).slice(0, 4);
  return { n: +e.dataset.clonSec, id: /^[A-Za-z][\w-]*$/.test(e.id || '') ? e.id : '', ruta: 'body > ' + p.join(' > '),
           clases: e.tagName.toLowerCase() + clases.map(c => '.' + c).join('') }; })
"""
JS_MARCAR_RUTAS = r"""
(rutas) => {
  document.querySelectorAll('[data-clon-sec]').forEach(e => e.removeAttribute('data-clon-sec'));
  document.querySelectorAll('[data-clon-capa]').forEach(e => e.removeAttribute('data-clon-capa'));
  const usados = []; let n = 0;
  // alto real: el suyo o, si mide 0 (cabecera transparente de WordPress: todo va en una capa absoluta encima de la
  // portada), el que ocupan sus hijos
  // (y el ancho igual: el #globalheader de apple.com es un div «inline» de 0x0 con el menú fijo dentro)
  const hijos = (e, eje) => { let a = Infinity, b = -Infinity;
    for (const c of [...e.querySelectorAll('*')].slice(0, 400)) { const q = c.getBoundingClientRect();
      if (q.width > 0 && q.height > 0) { a = Math.min(a, eje === 'y' ? q.top : q.left); b = Math.max(b, eje === 'y' ? q.bottom : q.right); } }
    return b > a ? b - a : 0; };
  const alto = (e) => { const r = e.getBoundingClientRect(); return r.height > 2 ? r.height : hijos(e, 'y'); };
  const ancho = (e) => { const r = e.getBoundingClientRect(); return r.width > 2 ? r.width : hijos(e, 'x'); };
  const vale = (e) => { if (!e) return false;
    return alto(e) > 2 && ancho(e) > innerWidth * 0.5 && !usados.some(u => u.contains(e) || e.contains(u)); };
  for (const r of rutas) {
    let e = null;
    try { if (r.id) e = document.getElementById(r.id); } catch (x) {}
    if (!vale(e)) { try { e = document.querySelector(r.ruta); } catch (x) { e = null; } }
    if (!vale(e)) { try { const c = document.querySelectorAll(r.clases); e = c.length === 1 ? c[0] : null; } catch (x) { e = null; } }
    if (vale(e)) { e.setAttribute('data-clon-sec', String(r.n)); usados.push(e); n++; }
  }
  return n; }
"""


def marcar_secciones(page, secciones, movil=False):
    """Marca data-clon-sec en ESTA carga con la numeración del análisis: primero el mismo elemento de PC (su ruta en el
    spec); si no aparecen ni el 70 %, se corta otra vez la página y se empareja por textos y posición (remapear)."""
    rutas = [dict(s["ruta"], n=s["n"]) for s in secciones if s.get("ruta")]
    if rutas:
        hallados = page.evaluate(JS_MARCAR_RUTAS, rutas)
        if hallados >= 0.7 * len(secciones):
            return hallados
    page.evaluate(JS_SECCIONES, MAX_SECCIONES * (2 if movil else 1))
    return remapear(page, secciones, None if movil else "y_escritorio")


def remapear(page, secciones, campo_y="y_escritorio"):
    """Otra carga de la web (o la versión móvil) puede detectar las secciones con otra numeración.
    Cada bloque se empareja con la sección que comparte sus textos; las secciones sin texto, por posición
    (campo_y) o, en móvil, por el orden entre sus vecinas ya emparejadas. Luego se renumera en la página."""
    firmas = page.evaluate(JS_FIRMAS)
    pares = []
    for f in firmas:
        for s in secciones:
            ts = [t["t"][:60] for t in s["textos"]]
            sc = sum(1 for t in ts if t in f["texto"]) / len(ts) if ts else 0
            dy = abs(f["y"] - s[campo_y]) if campo_y else 10**6
            pares.append((-round(sc, 3), dy, f["n"], s["n"]))
    pares.sort()
    mapa, usados_f, usados_s = {}, set(), set()
    for nsc, dy, fn, sn in pares:
        if fn in usados_f or sn in usados_s or (nsc > -0.2 and dy > 400):
            continue
        mapa[fn] = sn
        usados_f.add(fn)
        usados_s.add(sn)
    # sin texto en común: por orden, entre las vecinas ya emparejadas
    orden_f = sorted(f["n"] for f in firmas)
    inv = {sn: fn for fn, sn in mapa.items()}
    for s in secciones:
        sn = s["n"]
        if sn in usados_s:
            continue
        antes = max((inv[x] for x in inv if x < sn), default=0)
        despues = min((inv[x] for x in inv if x > sn), default=10**6)
        libre = next(
            (fn for fn in orden_f if antes < fn < despues and fn not in usados_f), None
        )
        if libre is not None:
            mapa[libre] = sn
            inv[sn] = libre
            usados_f.add(libre)
            usados_s.add(sn)
    page.evaluate(JS_RENUMERAR, {str(k): str(v) for k, v in mapa.items()})
    return len(mapa)


def extraer(url, carpeta=None, forzar=False):
    from playwright.sync_api import sync_playwright

    host = re.sub(
        r"[^a-z0-9]+", "_", re.sub(r"^https?://(www\.)?", "", url.lower())
    ).strip("_")[:40]
    carpeta = Path(carpeta or BASE / "trabajo" / host)
    carpeta.mkdir(parents=True, exist_ok=True)
    spec_path = carpeta / "spec.json"
    if spec_path.exists() and not forzar:
        previo = json.loads(spec_path.read_text(encoding="utf-8"))
        faltan = [
            x["n"]
            for x in previo["secciones"]
            if not (carpeta / f"sec_{x['n']}_escritorio.png").exists()
        ]
        if faltan:
            print(
                f"  faltan recortes de escritorio de las secciones {faltan}: repito la extracción"
            )
            forzar = True
    if spec_path.exists() and not forzar:
        print(
            f"  (uso la extracción guardada de {host}; borra {spec_path.name} para repetirla)"
        )
        return json.loads(spec_path.read_text(encoding="utf-8")), carpeta

    for viejo in carpeta.glob(
        "vision_*.txt"
    ):  # las descripciones de los ojos dependen de los recortes
        viejo.unlink()
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        ctx = nav.new_context(
            viewport={"width": ESCRITORIO[0], "height": ESCRITORIO[1]}, locale=LOCALE
        )
        page = ctx.new_page()
        print(f"  abriendo {url} ...")
        preparar_pagina(page, url)
        n = page.evaluate(JS_SECCIONES, MAX_SECCIONES)
        print(f"  {n} secciones detectadas")
        datos = page.evaluate(JS_MEDIR)
        rutas = {
            r["n"]: {k: r[k] for k in ("id", "ruta", "clases")}
            for r in page.evaluate(JS_RUTAS)
        }
        for s in datos["secciones"]:
            if s["n"] in rutas:
                s["ruta"] = rutas[s["n"]]
        alto = min(datos["alto_total"], MAX_ALTO)
        capturar(page, carpeta / "original_escritorio.png", ESCRITORIO[0], alto)
        for s in datos["secciones"]:
            s["y_escritorio"], s["alto_escritorio"] = s["y"], s["alto"]

        datos["alto_real"] = page.evaluate("window.__clonAltoReal || 0")
        datos["infinita"] = page.evaluate("!!window.__clonInfinita")

        # Captura nativa de secciones en ESCRITORIO por elemento DOM (sin tijeras ni desajustes)
        for s in datos["secciones"]:
            try:
                foto_seccion(
                    page,
                    s["n"],
                    carpeta / f"sec_{s['n']}_escritorio.png",
                    s.get("alto_caja"),
                )
            except Exception:
                pass
            # Clasificación de acción matemática DOM (carrusel, video, estática)
            try:
                accion = page.evaluate(
                    """(n) => {
                    const el = document.querySelector(`[data-clon-sec="${n}"]`);
                    if (!el) return { tipo: 'estatica', detalle: 'sin elemento' };
                    const diff = el.scrollWidth - el.clientWidth;
                    const subScroll = Array.from(el.querySelectorAll('*')).some(k => (k.scrollWidth - k.clientWidth > 40) && k.clientHeight > 50);
                    const tieneVideo = !!el.querySelector('video');
                    const tieneCanvas = !!el.querySelector('canvas');
                    const tieneIframe = !!el.querySelector('iframe');
                    const tieneDetails = !!el.querySelector('details, [aria-expanded="true"]');
                    if (diff > 40 || subScroll) return { tipo: 'carrusel_horizontal', detalle: 'slider con desbordamiento horizontal' };
                    if (tieneVideo) return { tipo: 'video_loop', detalle: 'video en bucle' };
                    if (tieneCanvas) return { tipo: 'canvas_3d', detalle: 'lienzo interactivo o 3D' };
                    if (tieneIframe) return { tipo: 'iframe_embebido', detalle: 'contenido externo o reproductor' };
                    if (tieneDetails) return { tipo: 'acordeon', detalle: 'desplegable interactivo' };
                    return { tipo: 'estatica', detalle: 'bloque fijo' };
                }""",
                    s["n"],
                )
                s["comportamiento"] = accion
            except Exception:
                s["comportamiento"] = {"tipo": "estatica", "detalle": "por defecto"}

        # MÓVIL: emulación del iPhone 14 Pro (la misma en todo el motor: opciones_movil)
        print(f"  móvil: emulando {MOVIL_DISPOSITIVO} ({MOVIL[0]}x{MOVIL[1]})...")
        ctx_movil = nav.new_context(**opciones_movil(pw))
        pm = ctx_movil.new_page()
        try:
            preparar_pagina(pm, url)
            n_m = marcar_secciones(pm, datos["secciones"], movil=True)
            print(f"  móvil: {n_m} de {len(datos['secciones'])} secciones localizadas")
            movil = pm.evaluate(JS_MEDIR)
            datos["movil_real"] = True
            datos["movil_medido"] = movil
            alto_m = min(movil.get("alto_total", 8000), MAX_ALTO)
            capturar(pm, carpeta / "original_movil.png", MOVIL[0], alto_m)
            por_n = {s["n"]: s for s in movil.get("secciones", [])}
            for s in datos["secciones"]:
                m = por_n.get(s["n"], {})
                s["y_movil"], s["alto_movil"] = m.get("y", 0), m.get("alto", 0)
                s["columnas_movil"] = m.get("columnas", 1)
                px_movil = {t["t"]: t["px"] for t in m.get("textos", [])}
                for t in s["textos"]:
                    t["px_movil"] = px_movil.get(t["t"])
            # Captura nativa de secciones en MÓVIL por elemento DOM
            for s in datos["secciones"]:
                try:
                    foto_seccion(
                        pm,
                        s["n"],
                        carpeta / f"sec_{s['n']}_movil.png",
                        por_n.get(s["n"], {}).get("alto_caja"),
                    )
                except Exception:
                    pass
        except Exception as ex_m:
            print(f"  (móvil: fallo en emulación iPhone ({ex_m}))")
        finally:
            ctx_movil.close()
        nav.close()

    recortar(
        carpeta / "original_escritorio.png", datos["secciones"], "escritorio", carpeta
    )
    recortar(carpeta / "original_movil.png", datos["secciones"], "movil", carpeta)

    # tokens globales
    fuentes = {}
    colores_texto, colores_fondo = {}, {}
    for s in datos["secciones"]:
        colores_fondo[s["fondo"]] = colores_fondo.get(s["fondo"], 0) + s["alto"]
        for t in s["textos"]:
            fuentes[t["fuente"]] = fuentes.get(t["fuente"], 0) + len(t["t"])
            if t["color"]:
                colores_texto[t["color"]] = colores_texto.get(t["color"], 0) + len(
                    t["t"]
                )
    orden = lambda d: [k for k, _ in sorted(d.items(), key=lambda x: -x[1])]
    mapa = {f: fuente_google(f) for f in fuentes}
    spec = {
        "url": url,
        "titulo": datos["titulo"],
        "lang": datos["lang"],
        "fondo_body": datos["fondo_body"],
        "fuentes_originales": orden(fuentes),
        "fuentes_google": mapa,
        "colores_texto": orden(colores_texto)[:6],
        "colores_fondo": orden(colores_fondo)[:6],
        "secciones": datos["secciones"],
        "movil_medido": datos.get("movil_medido"),
        "alto_real": datos.get("alto_real", 0),
        "infinita": datos.get("infinita", False),
        "tope_secciones": len(datos["secciones"]) >= MAX_SECCIONES,
        "alto_medido": alto,
        "movil_real": datos.get("movil_real", False),
    }
    spec_path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"  extracción guardada en {carpeta}")
    return spec, carpeta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python extraer.py https://web.com")
        sys.exit(1)
    s, c = extraer(sys.argv[1], forzar="--forzar" in sys.argv)
    for sec in s["secciones"]:
        print(
            f"  sección {sec['n']}: {sec['alto']}px, fondo {sec['fondo']}, {sec['columnas']} col, "
            f"{sec['total_textos']} textos, {len(sec['imagenes'])} imágenes | {sec['textos'][0]['t'][:50] if sec['textos'] else ''}"
        )
