import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
DISECCIONADOR - análisis completo de una web en un solo comando.

  python diseccionar.py https://web.com            (o sin URL: lee url.txt)
  python diseccionar.py URL --clonar               (además genera el clon fiel v8)

Qué averigua (con un navegador real, a 375 / 768 / 1280 px):
  - TIPO de web: landing, tienda, aplicación/SPA, blog... con sus motivos
  - TECNOLOGÍA: React/Next/Vue/Nuxt/Angular/Svelte/Astro, Shopify/WordPress/Webflow/Wix/Squarespace,
    Tailwind/Bootstrap, GSAP/AOS/Lenis/Swiper/Lottie/Three.js, analítica...
  - IFRAMES y contenido especial (vídeos, mapas, formularios, pagos, chats, canvas, shadow DOM)
  - SISTEMA DE DISEÑO: paleta, escala tipográfica, espaciados, radios, sombras, breakpoints reales
  - COMPONENTES repetidos (tarjetas, opiniones, menús...) y cuántas veces aparecen
  - MOVIMIENTO: animaciones activas, elementos que cambian con el scroll, sticky, carruseles, hover
  - SECCIONES: medidas, columnas en móvil/tablet/escritorio, textos, botones, imágenes
  - RENDIMIENTO y ACCESIBILIDAD básicos

Resultado en diseccion/<web>/:
  informe_web.md      RESUMEN COMPACTO (pensado para que Claude lo lea gastando pocos tokens)
  fichas_secciones.md una ficha por sección (lo que se le pasa a Qwen, sección a sección)
  diseccion.json      todos los datos
  capturas/           página completa en 3 anchos + recorte de cada sección
"""
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from extraer import (CSS_DESPLEGAR, JS_DESPLEGAR, JS_LIMPIAR, JS_SECCIONES, JS_MEDIR, MAX_SECCIONES,  # noqa: E402
                     capturar, fuente_google, preparar_pagina)

ANCHOS = {"movil": (375, 812), "tablet": (768, 1024), "escritorio": (1280, 800)}

# ---------------------------------------------------------------- JavaScript de análisis
JS_TECNOLOGIA = r"""
() => {
  const w = window, d = document, ev = [];
  const scripts = [...d.scripts].map(s => s.src).filter(Boolean);
  const html = d.documentElement.outerHTML.slice(0, 400000);
  const hay = (cond, nombre, cat, prueba) => { try { if (cond()) ev.push({ nombre, cat, prueba }); } catch (e) {} };
  const conClave = (pref) => { const els = d.querySelectorAll('body *'); for (let i = 0; i < Math.min(els.length, 400); i++) for (const k in els[i]) if (k.startsWith(pref)) return true; return false; };
  // frameworks de JavaScript
  hay(() => w.__NEXT_DATA__ || d.getElementById('__NEXT_DATA__') || scripts.some(s => s.includes('/_next/')), 'Next.js', 'framework', '__NEXT_DATA__ / _next');
  hay(() => w.__NUXT__ || w.$nuxt || scripts.some(s => s.includes('/_nuxt/')), 'Nuxt', 'framework', '__NUXT__ / _nuxt');
  hay(() => w.React || d.querySelector('[data-reactroot]') || conClave('__reactFiber') || conClave('__reactContainer'), 'React', 'framework', 'fibra de React en el DOM');
  hay(() => w.Vue || d.querySelector('[data-v-app]') || [...d.querySelectorAll('*')].slice(0, 2000).some(e => [...e.attributes].some(a => a.name.startsWith('data-v-'))), 'Vue', 'framework', 'atributos data-v-');
  hay(() => d.querySelector('[ng-version]'), 'Angular', 'framework', '[ng-version]');
  hay(() => d.querySelector('[class*="svelte-"]'), 'Svelte', 'framework', 'clases svelte-');
  hay(() => d.querySelector('astro-island') || html.includes('astro-'), 'Astro', 'framework', 'astro-island');
  hay(() => d.getElementById('___gatsby'), 'Gatsby', 'framework', '#___gatsby');
  hay(() => w.jQuery, 'jQuery ' + (w.jQuery && w.jQuery.fn ? w.jQuery.fn.jquery : ''), 'librería', 'window.jQuery');
  hay(() => w.Alpine || d.querySelector('[x-data]'), 'Alpine.js', 'framework', '[x-data]');
  hay(() => w.htmx || d.querySelector('[hx-get],[hx-post]'), 'htmx', 'framework', 'hx-*');
  // plataformas
  hay(() => w.Shopify || scripts.some(s => s.includes('cdn.shopify')), 'Shopify', 'plataforma', 'window.Shopify');
  hay(() => html.includes('/wp-content/') || html.includes('/wp-includes/'), 'WordPress', 'plataforma', '/wp-content/');
  hay(() => w.wc || d.querySelector('.woocommerce'), 'WooCommerce', 'plataforma', '.woocommerce');
  hay(() => d.documentElement.dataset.wfSite || html.includes('webflow'), 'Webflow', 'plataforma', 'data-wf-site');
  hay(() => html.includes('wixstatic') || w.wixBiSession, 'Wix', 'plataforma', 'wixstatic');
  hay(() => html.includes('squarespace'), 'Squarespace', 'plataforma', 'squarespace');
  hay(() => html.includes('framerusercontent') || d.querySelector('[data-framer-name]'), 'Framer', 'plataforma', 'framer');
  // CSS
  const clases = [...d.querySelectorAll('[class]')].slice(0, 3000).flatMap(e => (typeof e.className === 'string' ? e.className : '').split(/\s+/));
  const tw = clases.filter(c => /^(sm:|md:|lg:|xl:|hover:)?(p[xytrbl]?|m[xytrbl]?|w|h|text|bg|flex|grid|gap|rounded|font|leading|tracking)-/.test(c) || /\[.+\]/.test(c)).length;
  const bs = clases.filter(c => /^(col-(sm|md|lg|xl)-\d+|row|container(-fluid)?|btn(-primary|-secondary)?|d-(flex|none|block)|navbar(-expand.*)?)$/.test(c)).length;
  if (tw > 40) ev.push({ nombre: 'Tailwind CSS', cat: 'css', prueba: tw + ' clases de utilidad' });
  if (bs > 15 || w.bootstrap) ev.push({ nombre: 'Bootstrap', cat: 'css', prueba: bs + ' clases tipo Bootstrap' });
  // animación y scroll
  hay(() => w.gsap || w.TweenMax, 'GSAP', 'animación', 'window.gsap');
  hay(() => w.ScrollTrigger || (w.gsap && w.gsap.plugins && w.gsap.plugins.scrollTrigger), 'GSAP ScrollTrigger', 'animación', 'ScrollTrigger');
  hay(() => w.AOS || d.querySelector('[data-aos]'), 'AOS (aparecer al hacer scroll)', 'animación', '[data-aos]');
  hay(() => w.lenis || w.Lenis || d.documentElement.classList.contains('lenis'), 'Lenis (scroll suave)', 'animación', 'lenis');
  hay(() => d.querySelector('[data-scroll-container]') || w.LocomotiveScroll, 'Locomotive Scroll', 'animación', '[data-scroll-container]');
  hay(() => w.lottie || w.bodymovin || d.querySelector('lottie-player,dotlottie-player'), 'Lottie', 'animación', 'lottie');
  hay(() => w.THREE || w.__THREE__ || d.querySelector('canvas[data-engine*="three"]') || scripts.some(s => /three(\.module)?(\.min)?\.js/.test(s)), 'Three.js (3D)' + (w.__THREE__ ? ' r' + w.__THREE__ : ''), '3d', 'window.__THREE__');
  hay(() => w.PIXI || w.__PIXI_APP__ || w.__PIXI_DEVTOOLS__, 'PixiJS (2D WebGL)', '3d', 'window.PIXI');
  hay(() => w.BABYLON, 'Babylon.js (3D)', '3d', 'window.BABYLON');
  hay(() => d.querySelector('spline-viewer') || scripts.some(s => s.includes('splinetool')), 'Spline (3D)', '3d', 'spline-viewer');
  hay(() => w.rive || scripts.some(s => s.includes('rive')) && d.querySelector('canvas'), 'Rive', 'animación', 'window.rive');
  hay(() => w.createUnityInstance || scripts.some(s => s.includes('UnityLoader') || s.includes('.loader.js') && html.includes('unity')), 'Unity WebGL', '3d', 'createUnityInstance');
  hay(() => w.p5, 'p5.js', '3d', 'window.p5');
  hay(() => d.querySelector('[data-barba]') || w.barba, 'Barba.js (transiciones de página)', 'animación', '[data-barba]');
  hay(() => w.Swup || d.querySelector('#swup'), 'Swup (transiciones de página)', 'animación', '#swup');
  hay(() => w.Howl || w.Howler, 'Howler (audio)', 'animación', 'window.Howler');
  hay(() => w.Hls || scripts.some(s => s.includes('hls')), 'hls.js (vídeo en streaming)', 'componentes', 'window.Hls');
  hay(() => d.querySelector('mux-player,mux-video') || scripts.some(s => s.includes('mux')), 'Mux (vídeo)', 'componentes', 'mux-player');
  hay(() => d.querySelector('lite-youtube,iframe[src*="youtube"]'), 'YouTube (vídeo)', 'componentes', 'youtube');
  hay(() => d.querySelector('lite-vimeo,iframe[src*="vimeo"]') || w.Vimeo, 'Vimeo (vídeo)', 'componentes', 'vimeo');
  hay(() => d.querySelector('[data-framer-appear-id],[style*="--framer"]'), 'Framer Motion', 'animación', 'atributos framer');
  hay(() => w.Swiper || d.querySelector('.swiper,.swiper-container'), 'Swiper (carrusel)', 'componentes', '.swiper');
  hay(() => d.querySelector('.slick-slider'), 'Slick (carrusel)', 'componentes', '.slick-slider');
  hay(() => d.querySelector('.splide'), 'Splide (carrusel)', 'componentes', '.splide');
  hay(() => d.querySelector('.flickity-enabled'), 'Flickity (carrusel)', 'componentes', '.flickity');
  hay(() => d.querySelector('.glide'), 'Glide (carrusel)', 'componentes', '.glide');
  // analítica y terceros
  hay(() => w.gtag || w.dataLayer, 'Google Analytics/Tag Manager', 'analítica', 'dataLayer');
  hay(() => w.fbq, 'Meta Pixel', 'analítica', 'fbq');
  hay(() => w.hj, 'Hotjar', 'analítica', 'hj');
  hay(() => w.klaviyo || w._learnq, 'Klaviyo', 'marketing', 'klaviyo');
  hay(() => w.Intercom, 'Intercom (chat)', 'terceros', 'Intercom');
  hay(() => w.zE || w.zESettings, 'Zendesk (chat)', 'terceros', 'zE');
  hay(() => w.Stripe, 'Stripe (pagos)', 'terceros', 'Stripe');
  const fuentesCargadas = [...d.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, ''));
  const metaGen = (d.querySelector('meta[name="generator"]') || {}).content || null;
  return { evidencias: ev, fuentesCargadas: [...new Set(fuentesCargadas)].slice(0, 20), generador: metaGen,
           titulo: d.title, descripcion: (d.querySelector('meta[name="description"]') || {}).content || null,
           idioma: d.documentElement.lang || null, scripts: scripts.length };
}
"""

JS_ESPECIALES = r"""
() => {
  const tipo = (src) => { const s = (src || '').toLowerCase();
    if (/youtube|youtu\.be|vimeo|wistia|loom/.test(s)) return 'vídeo';
    if (/google\.[a-z.]+\/maps|maps\.google|mapbox|openstreetmap/.test(s)) return 'mapa';
    if (/typeform|hubspot|forms\.gle|docs\.google\.com\/forms|jotform|tally/.test(s)) return 'formulario';
    if (/stripe|paypal|checkout|klarna|afterpay/.test(s)) return 'pago';
    if (/intercom|zendesk|drift|crisp|tawk|gorgias|livechat/.test(s)) return 'chat';
    if (/recaptcha|hcaptcha|turnstile/.test(s)) return 'captcha';
    if (/calendly|cal\.com/.test(s)) return 'agenda';
    if (/spotify|soundcloud/.test(s)) return 'audio';
    if (/twitter|instagram|facebook|tiktok/.test(s)) return 'red social';
    if (!s || s.startsWith('about:')) return 'vacío/dinámico';
    try { return new URL(s, location.href).host === location.host ? 'misma web (app embebida)' : 'externo'; } catch (e) { return 'externo'; }
  };
  const iframes = [...document.querySelectorAll('iframe')].map(f => { const r = f.getBoundingClientRect();
    return { src: (f.src || f.getAttribute('data-src') || '').slice(0, 140), tipo: tipo(f.src || f.getAttribute('data-src')),
             w: Math.round(r.width), h: Math.round(r.height), visible: r.width > 20 && r.height > 20 && getComputedStyle(f).visibility !== 'hidden' }; });
  let sombras = 0; for (const e of document.querySelectorAll('*')) if (e.shadowRoot) sombras++;
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 10 && r.height > 10; };
  // canvas: qué contexto usa (webgl = 3D) y si ocupa la pantalla como fondo fijo
  const contexto = (c) => { try { if (c.getContext('webgl2')) return 'webgl2'; } catch (e) {}
    try { if (c.getContext('webgl')) return 'webgl'; } catch (e) {} return '2d u otro'; };
  const lienzos = [...document.querySelectorAll('canvas')].filter(vis).map(c => { const r = c.getBoundingClientRect(); let fijo = false;
    for (let x = c; x && x !== document.body; x = x.parentElement) if (['fixed', 'sticky'].includes(getComputedStyle(x).position)) { fijo = true; break; }
    return { w: Math.round(r.width), h: Math.round(r.height), contexto: contexto(c), fijo,
             pantalla: Math.round(100 * Math.min(r.width, innerWidth) * Math.min(r.height, innerHeight) / (innerWidth * innerHeight)) }; }).slice(0, 8);
  return { iframes, shadowRoots: sombras,
    canvas: lienzos.length, lienzos,
    videos: (() => { const todos = [...document.querySelectorAll('video')];        // también los escondidos en shadow DOM (mux-player, etc.)
        for (const h of document.querySelectorAll('*')) if (h.shadowRoot) todos.push(...h.shadowRoot.querySelectorAll('video'));
        const reprod = [...document.querySelectorAll('mux-player,mux-video,media-controller,lite-youtube,lite-vimeo,youtube-video,vimeo-video,hls-video')];
        return [...new Set(todos)].concat(reprod.filter(p => !todos.some(v => p.contains(v) || (p.shadowRoot && p.shadowRoot.contains(v))))); })()
      .filter(vis).map(v => { const r = v.getBoundingClientRect(); if (v.tagName !== 'VIDEO') v = Object.assign({}, { autoplay: v.hasAttribute('autoplay'), loop: v.hasAttribute('loop'),
        muted: v.hasAttribute('muted'), controls: !v.hasAttribute('nohotkeys'), currentSrc: v.getAttribute('src') || v.getAttribute('playback-id') || v.tagName.toLowerCase(), poster: v.getAttribute('poster') || '', querySelector: () => null });
      const src = v.currentSrc || v.src || (v.querySelector('source') || {}).src || '';
      return { autoplay: v.autoplay, loop: v.loop, muted: v.muted, controles: v.controls, w: Math.round(r.width), h: Math.round(r.height),
               src: src.slice(0, 140), poster: (v.poster || '').slice(0, 140), streaming: /\.m3u8|blob:/.test(src),
               fondo: v.autoplay && v.muted && v.loop && !v.controls }; }).slice(0, 12),
    svgs: document.querySelectorAll('svg').length,
    formularios: [...document.querySelectorAll('form')].map(f => ({ campos: [...f.querySelectorAll('input,select,textarea')].map(i => i.type || i.tagName.toLowerCase()).slice(0, 12), accion: (f.getAttribute('action') || '').slice(0, 60) })).slice(0, 10),
    customElements: [...new Set([...document.querySelectorAll('*')].map(e => e.tagName.toLowerCase()).filter(t => t.includes('-')))].slice(0, 25) };
}
"""

JS_DISENO = r"""
() => {
  const rgb2hex = (c) => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
    if (p.length > 3 && p[3] === 0) return null; return '#' + p.slice(0, 3).map(x => Math.round(x).toString(16).padStart(2, '0')).join('').toUpperCase() + (p.length > 3 && p[3] < 1 ? Math.round(p[3] * 255).toString(16).padStart(2, '0').toUpperCase() : ''); };
  const cont = (o, k, n = 1) => { if (k == null || k === '') return; o[k] = (o[k] || 0) + n; };
  const texto = {}, fondo = {}, borde = {}, tam = {}, pesos = {}, fuentes = {}, alturas = {}, espacios = {}, radios = {}, sombras = {}, ejemploTam = {};
  const els = [...document.querySelectorAll('body *')];
  let n = 0;
  for (const e of els) {
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) continue;
    if (++n > 6000) break;
    const propio = [...e.childNodes].filter(x => x.nodeType === 3).map(x => x.textContent).join('').trim();
    if (propio.length > 1) {
      const peso = propio.length;
      cont(texto, rgb2hex(s.color), peso); cont(tam, s.fontSize, peso); cont(pesos, s.fontWeight, peso);
      cont(fuentes, s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), peso); cont(alturas, s.lineHeight, peso);
      if (!ejemploTam[s.fontSize]) ejemploTam[s.fontSize] = { t: propio.slice(0, 40), tag: e.tagName.toLowerCase(), peso: s.fontWeight, may: s.textTransform === 'uppercase', tracking: s.letterSpacing };
    }
    cont(fondo, rgb2hex(s.backgroundColor), Math.round(r.width * r.height / 1000));
    if (parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== 'none') cont(borde, rgb2hex(s.borderTopColor));
    for (const p of ['marginTop', 'marginBottom', 'paddingTop', 'paddingBottom', 'paddingLeft', 'rowGap', 'columnGap']) { const v = parseFloat(s[p]); if (v > 0) cont(espacios, Math.round(v) + 'px'); }
    const rad = parseFloat(s.borderTopLeftRadius); if (rad > 0) cont(radios, (rad >= Math.min(r.width, r.height) / 2 - 1 ? 'círculo/píldora' : Math.round(rad) + 'px'));
    if (s.boxShadow && s.boxShadow !== 'none') cont(sombras, s.boxShadow.slice(0, 90));
  }
  const top = (o, k = 12) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, k);
  // ancho máximo de contenido típico
  const anchos = {}; for (const e of els.slice(0, 4000)) { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    if (s.maxWidth !== 'none' && s.maxWidth.endsWith('px') && r.width > 300) cont(anchos, s.maxWidth); }
  return { colores_texto: top(texto, 10), colores_fondo: top(fondo, 10), colores_borde: top(borde, 6), tamanos: top(tam, 12).map(([k, v]) => [k, v, ejemploTam[k]]),
           pesos: top(pesos, 6), fuentes: top(fuentes, 6), alturas_linea: top(alturas, 8), espacios: top(espacios, 14), radios: top(radios, 6),
           sombras: top(sombras, 5), anchos_max: top(anchos, 5), elementos_visibles: n };
}
"""

JS_COMPONENTES = r"""
() => {
  // firma estructural: etiqueta + etiquetas de hijos y nietos (sin clases ni textos)
  const firma = (e) => e.tagName + '>' + [...e.children].map(c => c.tagName + '(' + [...c.children].map(g => g.tagName).join(',') + ')').join('|');
  const grupos = {};
  for (const e of document.querySelectorAll('body *')) {
    if (e.children.length < 2) continue;
    const r = e.getBoundingClientRect(); if (r.width < 60 || r.height < 40 || r.width > innerWidth * 0.95) continue;
    const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden') continue;
    const f = firma(e); (grupos[f] = grupos[f] || []).push(e);
  }
  const secDe = (el) => { const s = el.closest('[data-clon-sec]'); return s ? +s.dataset.clonSec : null; };
  const nombre = (e) => { const t = (e.innerText || '');
    const img = e.querySelector('img,picture,svg'), precio = /[$€£]\s?\d|\d[.,]\d{2}\s?[$€£]/.test(t), estrellas = /★|☆|stars?/i.test(t) || e.querySelector('[class*="star"]');
    const boton = e.querySelector('button,a[class*="btn"],a[class*="button"]'), titulo = e.querySelector('h1,h2,h3,h4,h5,h6');
    if (img && precio) return 'tarjeta de producto'; if (estrellas) return 'opinión / valoración'; if (e.tagName === 'LI' || e.querySelector('li a')) return 'elemento de lista o menú';
    if (img && titulo && boton) return 'tarjeta con imagen, título y botón'; if (img && titulo) return 'tarjeta con imagen y título';
    if (e.querySelector('input')) return 'formulario o campo'; if (img) return 'bloque con imagen'; if (titulo) return 'bloque de texto con título'; return 'bloque repetido'; };
  const out = [];
  for (const [f, lista] of Object.entries(grupos)) {
    if (lista.length < 3) continue;
    // descartar grupos anidados entre sí (quedarse con los más externos)
    const externos = lista.filter(e => !lista.some(o => o !== e && o.contains(e)));
    if (externos.length < 3) continue;
    const r = externos[0].getBoundingClientRect();
    out.push({ nombre: nombre(externos[0]), veces: externos.length, ancho: Math.round(r.width), alto: Math.round(r.height),
               secciones: [...new Set(externos.map(secDe).filter(Boolean))].slice(0, 8),
               ejemplo: (externos[0].innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70) });
  }
  out.sort((a, b) => (b.veces * b.ancho * b.alto) - (a.veces * a.ancho * a.alto));
  // quitar repetidos del mismo tipo y tamaño
  const vistos = new Set(); return out.filter(c => { const k = c.nombre + c.ancho + c.alto; if (vistos.has(k)) return false; vistos.add(k); return true; }).slice(0, 12);
}
"""

JS_MUESTRA_SCROLL = r"""
(paso) => {
  // posición y opacidad de los elementos grandes y con texto, para detectar los que se mueven con el scroll
  if (!window.__clonMuestra) {
    const cand = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
      return r.width > 40 && r.height > 20 && s.display !== 'none' && (e.children.length === 0 || e.querySelector('img,h1,h2,h3,p')); }).slice(0, 700);
    cand.forEach((e, i) => e.setAttribute('data-clon-m', i)); window.__clonMuestra = cand.length;
  }
  const out = {};
  for (const e of document.querySelectorAll('[data-clon-m]')) { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    out[e.dataset.clonM] = [Math.round(r.top + scrollY), Math.round(r.left), Math.round(+s.opacity * 100), s.transform === 'none' ? '' : s.transform.slice(0, 60)]; }
  return out;
}
"""

JS_MOVIMIENTO = r"""
() => {
  const anims = document.getAnimations ? document.getAnimations().slice(0, 40).map(a => { const t = a.effect && a.effect.target;
    return { nombre: a.animationName || a.transitionProperty || (a.constructor && a.constructor.name), duracion: a.effect && a.effect.getTiming ? a.effect.getTiming().duration : null,
             repite: a.effect && a.effect.getTiming ? a.effect.getTiming().iterations : null, elemento: t ? (t.tagName.toLowerCase() + (t.className && typeof t.className === 'string' ? '.' + t.className.split(' ')[0] : '')) : null }; }) : [];
  const fijos = [...document.querySelectorAll('body *')].filter(e => ['sticky', 'fixed'].includes(getComputedStyle(e).position) && e.getBoundingClientRect().height > 10)
    .slice(0, 10).map(e => ({ pos: getComputedStyle(e).position, el: e.tagName.toLowerCase(), alto: Math.round(e.getBoundingClientRect().height), texto: (e.innerText || '').replace(/\s+/g, ' ').slice(0, 40) }));
  const carruseles = [...document.querySelectorAll('body *')].filter(e => { const s = getComputedStyle(e); const r = e.getBoundingClientRect();
    return r.width > 200 && ['hidden', 'auto', 'scroll', 'clip'].includes(s.overflowX) && e.scrollWidth > e.clientWidth * 1.15 && e.children.length >= 2; })
    .slice(0, 8).map(e => ({ el: e.tagName.toLowerCase(), visible: e.clientWidth, total: e.scrollWidth, scrollSnap: getComputedStyle(e).scrollSnapType !== 'none', texto: (e.innerText || '').replace(/\s+/g, ' ').slice(0, 40) }));
  const marquesinas = [...document.querySelectorAll('marquee,[class*="marquee"],[class*="ticker"]')].length;
  return { animaciones: anims, fijos, carruseles, marquesinas };
}
"""

JS_RENDIMIENTO = r"""
() => {
  const nav = performance.getEntriesByType('navigation')[0] || {};
  const rec = performance.getEntriesByType('resource');
  const porTipo = {}; let peso = 0;
  for (const r of rec) { const t = r.initiatorType; porTipo[t] = (porTipo[t] || 0) + 1; peso += r.transferSize || 0; }
  const imgs = [...document.images];
  const formatos = {}; for (const i of imgs) { const m = (i.currentSrc || i.src || '').split('?')[0].match(/\.(\w{3,4})$/); const f = m ? m[1].toLowerCase() : 'otro'; formatos[f] = (formatos[f] || 0) + 1; }
  const h = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(x => +x.tagName[1]);
  let saltos = 0; for (let i = 1; i < h.length; i++) if (h[i] > h[i - 1] + 1) saltos++;
  return {
    carga_ms: Math.round(nav.loadEventEnd || 0), dom_listo_ms: Math.round(nav.domContentLoadedEventEnd || 0),
    peticiones: rec.length, peso_kb: Math.round(peso / 1024), por_tipo: porTipo, nodos_dom: document.getElementsByTagName('*').length,
    imagenes: imgs.length, formatos, imagenes_lazy: imgs.filter(i => i.loading === 'lazy').length,
    a11y: { sin_alt: imgs.filter(i => !i.hasAttribute('alt')).length, h1: h.filter(x => x === 1).length, saltos_titulos: saltos,
            botones_sin_nombre: [...document.querySelectorAll('button')].filter(b => !(b.innerText || '').trim() && !b.getAttribute('aria-label')).length,
            lang: !!document.documentElement.lang }
  };
}
"""

JS_COLUMNAS = r"""
() => { const columnasDe = (sec) => {
    const W = sec.getBoundingClientRect().width || innerWidth; let max = 1;
    const conts = [sec, ...sec.querySelectorAll('*')].filter(e => e.children.length >= 2).slice(0, 600);
    for (const e of conts) {
      const items = [...e.children].map(c => c.getBoundingClientRect()).filter(r => r.height > 40 && r.width >= W * 0.12 && r.width < W * 0.95);
      for (const a of items) max = Math.max(max, items.filter(b => Math.abs(b.top - a.top) < 30).length);
    }
    return Math.min(max, 12); };
  return [...document.querySelectorAll('[data-clon-sec]')].map(sec => [+sec.dataset.clonSec, columnasDe(sec), Math.round(sec.getBoundingClientRect().height)]); }
"""


# ---------------------------------------------------------------- análisis en Python
def css_de_la_web(page):
    """Descarga las hojas de estilo (sin restricciones CORS) y saca breakpoints, :hover, @keyframes y transiciones."""
    hojas = page.evaluate("[...document.querySelectorAll('link[rel~=\"stylesheet\"]')].map(l => l.href).filter(Boolean)")
    textos = [page.evaluate("[...document.querySelectorAll('style')].map(s => s.textContent).join('\\n')")]
    for h in hojas[:30]:
        try:
            r = page.request.get(h, timeout=15000)
            if r.ok:
                textos.append(r.text())
        except Exception:
            pass
    css = "\n".join(textos)
    bp = Counter()
    for m in re.finditer(r"@media[^{]*\((min|max)-width:\s*([\d.]+)(px|em|rem)\)", css):
        v = float(m.group(2)) * (16 if m.group(3) in ("em", "rem") else 1)
        bp[f"{m.group(1)}-width {int(v)}px"] += 1
    hover = re.findall(r"([^{}]{1,80}):hover", css)
    return {"hojas": len(hojas), "kb_css": len(css) // 1024, "breakpoints": bp.most_common(8),
            "reglas_hover": len(hover), "ejemplos_hover": [h.strip()[-50:] for h in hover[:5]],
            "keyframes": sorted(set(re.findall(r"@keyframes\s+([\w-]+)", css)))[:15],
            "transiciones": len(re.findall(r"transition\s*:", css)),
            "variables_css": len(set(re.findall(r"(--[\w-]+)\s*:", css))),
            "scroll_timeline": "animation-timeline" in css or "view-timeline" in css}


def detectar_movimiento_scroll(page):
    """Muestrea los elementos en 4 posiciones de scroll y devuelve los que cambian de posición relativa u opacidad."""
    alto = page.evaluate("document.documentElement.scrollHeight")
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(400)
    muestras = []
    for frac in (0, 0.25, 0.5, 0.8):
        page.evaluate(f"window.scrollTo(0, {int(alto * frac)})")
        page.wait_for_timeout(700)
        muestras.append(page.evaluate(JS_MUESTRA_SCROLL, frac))
    page.evaluate("window.scrollTo(0,0)")
    cambian = []
    for k in muestras[0]:
        vals = [m.get(k) for m in muestras if m.get(k)]
        if len(vals) < 2:
            continue
        dy = max(v[0] for v in vals) - min(v[0] for v in vals)
        dop = max(v[2] for v in vals) - min(v[2] for v in vals)
        dtr = len({v[3] for v in vals}) > 1
        if dy > 8 or dop > 15 or dtr:
            cambian.append({"id": k, "desplaza_px": dy, "cambia_opacidad": dop, "cambia_transform": dtr})
    return cambian


def clasificar(tec, esp, diseno, comps, secciones, rend):
    """Tipo de web con motivos (heurística)."""
    nombres = {e["nombre"].split(" ")[0] for e in tec["evidencias"]}
    puntos = Counter()
    motivos = {}

    def sumar(tipo, n, motivo):
        puntos[tipo] += n
        motivos.setdefault(tipo, []).append(motivo)
    if {"Shopify", "WooCommerce"} & nombres:
        sumar("tienda online", 4, "plataforma de comercio")
    if any(c["nombre"] == "tarjeta de producto" for c in comps):
        sumar("tienda online", 3, "tarjetas con precio")
    if len(secciones) >= 6:
        sumar("landing / web de marketing", 2, f"{len(secciones)} secciones verticales")
    if sum(1 for s in secciones if s.get("botones")) >= 3:
        sumar("landing / web de marketing", 1, "varias llamadas a la acción")
    if {"React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt"} & nombres and len(secciones) <= 4:
        sumar("aplicación web (SPA)", 3, "framework de JS con pocas secciones")
    apps = [f for f in esp["iframes"] if f["visible"] and f["tipo"] in ("misma web (app embebida)", "externo") and f["w"] > 500]
    if apps:
        sumar("aplicación web (SPA)", 2, f"{len(apps)} iframe(s) grandes de aplicación")
    if len(esp["formularios"]) >= 2 or sum(len(f["campos"]) for f in esp["formularios"]) > 8:
        sumar("aplicación web (SPA)", 1, "muchos campos de formulario")
    if rend["nodos_dom"] > 0 and len(secciones) <= 3:
        sumar("aplicación web (SPA)", 1, "página corta")
    gl = [c for c in esp.get("lienzos", []) if c["contexto"].startswith("webgl") and c["pantalla"] >= 50]
    if gl:
        sumar("experiencia 3D / WebGL", 6, f"canvas WebGL que ocupa el {gl[0]['pantalla']}% de la pantalla" + (" (fondo fijo)" if gl[0]["fijo"] else ""))
    if {"Three.js", "Babylon.js", "Spline", "Unity", "PixiJS"} & nombres:
        sumar("experiencia 3D / WebGL", 2, "motor 3D cargado")
    if not puntos:
        sumar("web informativa", 1, "sin señales claras")
    tipo, _ = puntos.most_common(1)[0]
    return {"tipo": tipo, "puntos": dict(puntos), "motivos": motivos.get(tipo, [])}


# ---------------------------------------------------------------- informe
def informe_md(d):
    t, e, ds, cs, mv, r, css = d["tecnologia"], d["especiales"], d["diseno"], d["componentes"], d["movimiento"], d["rendimiento"], d["css"]
    L = [f"# Disección: {d['url']}", f"_{d['fecha']} · {t['titulo'][:80]}_", ""]
    c = d["clasificacion"]
    L += [f"**Tipo:** {c['tipo']} ({'; '.join(c['motivos'])})", ""]
    por_cat = {}
    for ev in t["evidencias"]:
        por_cat.setdefault(ev["cat"], []).append(ev["nombre"])
    L.append("## Tecnología")
    L += [f"- **{k}:** {', '.join(v)}" for k, v in por_cat.items()] or ["- (no se detectó ninguna conocida)"]
    if t.get("generador"):
        L.append(f"- generador: {t['generador']}")
    L += [f"- fuentes cargadas: {', '.join(t['fuentesCargadas'][:8]) or '—'}", ""]
    L.append("## Contenido especial")
    vis = [f for f in e["iframes"] if f["visible"]]
    L.append(f"- iframes: {len(e['iframes'])} ({len(vis)} visibles)" + "".join(f"\n  - {f['tipo']} {f['w']}x{f['h']} · {urlparse(f['src']).netloc or '—'}" for f in vis[:6]))
    L.append(f"- vídeos: {len(e['videos'])} · canvas: {e['canvas']} · shadow DOM: {e['shadowRoots']} · SVG: {e['svgs']} · formularios: {len(e['formularios'])}")
    for c in e.get("lienzos", [])[:4]:
        L.append(f"  - canvas {c['w']}x{c['h']} · {c['contexto']}{' · FIJO de fondo' if c['fijo'] else ''} · ocupa {c['pantalla']}% de la pantalla")
    for v in e["videos"][:6]:
        tipo = "vídeo de fondo (autoplay, mudo, en bucle)" if v.get("fondo") else ("vídeo con controles" if v.get("controles") else "vídeo")
        L.append(f"  - {tipo} {v['w']}x{v.get('h', '?')}" + (" · streaming" if v.get("streaming") else "") + (f" · {v['src'].rsplit('/', 1)[-1][:50]}" if v.get("src") else ""))
    if e["customElements"]:
        L.append(f"- componentes web propios: {', '.join(e['customElements'][:10])}")
    L.append("")
    L.append("## Sistema de diseño")
    fg = {f: fuente_google(f) for f, _ in ds["fuentes"]}
    L.append("- **fuentes:** " + ", ".join(f"{f} ({n}) → {fg[f]}" for f, n in ds["fuentes"][:4]))
    L.append("- **texto:** " + ", ".join(f"`{c}`" for c, _ in ds["colores_texto"][:6]))
    L.append("- **fondos:** " + ", ".join(f"`{c}`" for c, _ in ds["colores_fondo"][:6]))
    if ds["colores_borde"]:
        L.append("- **bordes:** " + ", ".join(f"`{c}`" for c, _ in ds["colores_borde"][:4]))
    L.append("- **escala tipográfica** (tamaño · peso · ejemplo):")
    for tam, _, ej in sorted(ds["tamanos"], key=lambda x: -float(x[0][:-2]))[:8]:
        if ej:
            L.append(f"  - {tam} · {ej['peso']}{' · MAYÚS' if ej['may'] else ''} · <{ej['tag']}> \"{ej['t'][:30]}\"")
    L.append("- **espaciados frecuentes:** " + ", ".join(v for v, _ in sorted(ds["espacios"][:10], key=lambda x: float(x[0][:-2]))))
    L.append("- **radios:** " + (", ".join(v for v, _ in ds["radios"]) or "esquinas rectas"))
    if ds["sombras"]:
        L.append(f"- **sombras:** {len(ds['sombras'])} tipos (p. ej. `{ds['sombras'][0][0][:60]}`)")
    if ds["anchos_max"]:
        L.append("- **ancho máximo de contenido:** " + ", ".join(v for v, _ in ds["anchos_max"][:3]))
    L.append("- **breakpoints:** " + (", ".join(f"{b} ({n})" for b, n in css["breakpoints"][:6]) or "—"))
    L.append(f"- CSS: {css['hojas']} hojas, {css['kb_css']} KB, {css['variables_css']} variables CSS")
    L.append("")
    L.append("## Componentes repetidos")
    L += [f"- {c['nombre']} ×{c['veces']} ({c['ancho']}x{c['alto']}px) · secciones {c['secciones']} · \"{c['ejemplo'][:45]}\"" for c in cs[:8]] or ["- —"]
    L.append("")
    L.append("## Movimiento e interacción")
    L.append(f"- animaciones activas al cargar: {len(mv['animaciones'])}" + (f" ({', '.join(sorted({str(a['nombre']) for a in mv['animaciones']})[:6])})" if mv["animaciones"] else ""))
    L.append(f"- elementos que cambian con el scroll: {len(mv['scroll'])}" + (f" (máx. desplazamiento {max(x['desplaza_px'] for x in mv['scroll'])}px)" if mv["scroll"] else ""))
    L.append(f"- fijos/sticky: " + ("; ".join(f"{f['pos']} {f['el']} {f['alto']}px \"{f['texto'][:25]}\"" for f in mv["fijos"][:4]) or "—"))
    L.append(f"- carruseles: {len(mv['carruseles'])}" + ("".join(f"\n  - {c['el']} {c['visible']}→{c['total']}px{' (scroll-snap)' if c['scrollSnap'] else ''} \"{c['texto'][:30]}\"" for c in mv["carruseles"][:4])))
    L.append(f"- reglas :hover: {css['reglas_hover']} · @keyframes: {', '.join(css['keyframes'][:6]) or '—'} · transiciones: {css['transiciones']}" + (" · usa animaciones ligadas al scroll (CSS)" if css["scroll_timeline"] else ""))
    L.append("")
    L.append(f"## Secciones ({len(d['secciones'])}) — columnas móvil/tablet/escritorio")
    for s in d["secciones"]:
        col = f"{s['columnas_por_ancho'].get('movil', '?')}/{s['columnas_por_ancho'].get('tablet', '?')}/{s['columnas_por_ancho'].get('escritorio', '?')}"
        primero = s["textos"][0]["t"][:40] if s["textos"] else "(sin texto)"
        L.append(f"- S{s['n']}: " + (f"**{s['escena'].upper()}** · " if s.get("escena") else "") + f"{s['alto']}px · fondo `{s['fondo']}` · col {col} · {s['total_textos']} textos, {len(s['botones'])} botones, {len(s['imagenes'])} imágenes · \"{primero}\"")
    L.append("")
    L.append("## Rendimiento y accesibilidad")
    L.append(f"- carga {r['carga_ms']} ms · {r['peticiones']} peticiones · {r['peso_kb']} KB · {r['nodos_dom']} nodos DOM · {r['imagenes']} imágenes ({', '.join(f'{k}:{v}' for k, v in r['formatos'].items())}), {r['imagenes_lazy']} lazy")
    a = r["a11y"]
    L.append(f"- imágenes sin alt: {a['sin_alt']} · h1: {a['h1']} · saltos en títulos: {a['saltos_titulos']} · botones sin nombre: {a['botones_sin_nombre']} · lang: {'sí' if a['lang'] else 'no'}")
    L.append("")
    L.append("## Recomendación para clonarla")
    L += [f"- {x}" for x in d["recomendaciones"]]
    return "\n".join(L) + "\n"


def recomendaciones(d):
    rec = []
    t = d["clasificacion"]["tipo"]
    vis = [f for f in d["especiales"]["iframes"] if f["visible"]]
    if t.startswith("experiencia 3D"):
        rec.append("Web 3D/WebGL: lo que se ve en 3D está dibujado en un canvas y NO se puede copiar con HTML ni Tailwind. "
                   "Plan: Qwen clona la capa de HTML (textos, menú, botones, secciones) y el 3D se sustituye por el vídeo grabado del scroll "
                   "o por fotogramas; rehacer el 3D de verdad es trabajo de Three.js por escenas (Claude), no de Qwen 7B.")
    texto_canvas = [c for c in d["especiales"].get("lienzos", []) if c["contexto"] == "2d u otro" and c["pantalla"] >= 40]
    if texto_canvas:
        rec.append(f"Canvas 2D grande ({texto_canvas[0]['pantalla']}% de la pantalla): puede tener texto o gráficos DIBUJADOS que no se pueden medir; mira las capturas.")
    fondo_v = [v for v in d["especiales"]["videos"] if v.get("fondo")]
    if fondo_v:
        rec.append(f"{len(fondo_v)} vídeo(s) de fondo: en el clon, <video autoplay muted loop playsinline> con un vídeo propio o el póster como imagen.")
    if t.startswith("aplicación"):
        rec.append("Es una aplicación: el clon visual solo copia el aspecto. La lógica (datos, login, estados) hay que programarla aparte.")
    if vis:
        tipos = Counter(f["tipo"] for f in vis)
        rec.append("Iframes visibles (" + ", ".join(f"{k}×{v}" for k, v in tipos.items()) + "): no se copian; sustituir por una captura, un embed propio o un hueco del mismo tamaño.")
    if d["especiales"]["canvas"] or d["especiales"]["videos"]:
        rec.append("Hay canvas/vídeo: se capturan como imagen o se sustituyen por un vídeo propio.")
    if d["movimiento"]["scroll"] or d["movimiento"]["animaciones"]:
        rec.append(f"Tiene movimiento ({len(d['movimiento']['scroll'])} elementos con scroll, {len(d['movimiento']['animaciones'])} animaciones): la captura sale estática; hace falta una fase de movimiento (IntersectionObserver / animation-timeline).")
    if d["movimiento"]["carruseles"]:
        rec.append(f"{len(d['movimiento']['carruseles'])} carrusel(es): rehacer con scroll-snap (CSS) o unas líneas de JS.")
    if d["componentes"]:
        rec.append("Componentes repetidos detectados: programarlos una vez y reutilizarlos (" + ", ".join(f"{c['nombre']}×{c['veces']}" for c in d["componentes"][:3]) + ").")
    fuentes = [f for f, _ in d["diseno"]["fuentes"][:3]]
    rec.append("Fuentes: " + ", ".join(f"{f} → {fuente_google(f)}" for f in fuentes) + " (las originales pueden ser de pago).")
    grandes = [s for s in d["secciones"] if s.get("total_textos", 0) > 30]
    if grandes:
        rec.append("Secciones muy cargadas para Qwen 7B (partirlas en subbloques): " + ", ".join(f"S{s['n']} ({s['total_textos']} textos)" for s in grandes))
    rec.append("Plan: Claude define el sistema de diseño e instrucciones cortas → Qwen escribe una sección por petición con su ficha → el verificador la compara con la original.")
    return rec


def fichas_md(d):
    fg = d["fuentes_google"]
    L = [f"# Fichas por sección — {d['url']}", "",
         "Tokens globales: fuentes " + ", ".join(f"{k}→{v}" for k, v in list(fg.items())[:4]) +
         " · texto " + ", ".join(c for c, _ in d["diseno"]["colores_texto"][:4]) +
         " · fondos " + ", ".join(c for c, _ in d["diseno"]["colores_fondo"][:4]), ""]
    for s in d["secciones"]:
        col = s["columnas_por_ancho"]
        L.append(f"## Sección {s['n']}")
        L.append(f"- alto {s['alto']}px (móvil {s.get('alto_movil', '?')}px) · fondo {s['fondo']} · columnas móvil {col.get('movil', '?')}, tablet {col.get('tablet', '?')}, escritorio {col.get('escritorio', '?')} · alineación {s.get('alineacion', '?')}")
        if s.get("imagen_fondo"):
            L.append(f"- imagen de fondo (color dominante #{s.get('color_imagen_fondo', '?')})")
        for t in s["textos"][:18]:
            mv = f"/{t['px_movil']}" if t.get("px_movil") and t["px_movil"] != t["px"] else ""
            L.append(f"  - <{t['tag']}> \"{t['t'][:90]}\" {t['px']}{mv}px p{t['peso']} {t['color']} {fg.get(t['fuente'], 'Inter')}{' MAYÚS' if t['may'] else ''} {t['alinea']}")
        if s["total_textos"] > 18:
            L.append(f"  - (+{s['total_textos'] - 18} textos más)")
        for b in s["botones"][:4]:
            L.append(f"  - botón \"{b['t'][:30]}\" fondo {b['fondo']} texto {b['color']} radio {b['radio']}px pad {b['pad']} {b['px']}px")
        for im in s["imagenes"][:6]:
            L.append(f"  - imagen {im['w']}x{im['h']} en ({im['x']},{im['y']}){' redonda' if im.get('redonda') else ''} color #{im.get('color', '?')}")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- principal
def diseccionar(url, clonar=False):
    from playwright.sync_api import sync_playwright
    from extraer import extraer, recortar
    print(f"DISECCIONADOR - {url}")
    spec, carpeta_sec = extraer(url, forzar=True)          # secciones, medidas y recortes (escritorio + móvil)
    host = carpeta_sec.name
    out = (BASE.parent / "workspace") / host
    (out / "capturas").mkdir(parents=True, exist_ok=True)
    d = {"url": url, "fecha": time.strftime("%Y-%m-%d %H:%M"), "fuentes_google": spec["fuentes_google"]}
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1280, "height": 800}, locale="en-US")
        page = ctx.new_page()
        print("  [1/7] tecnología (antes de tocar la página)")
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
        except Exception:
            page.wait_for_timeout(4000)
        page.wait_for_timeout(1500)
        d["tecnologia"] = page.evaluate(JS_TECNOLOGIA)
        d["rendimiento"] = page.evaluate(JS_RENDIMIENTO)
        d["especiales"] = page.evaluate(JS_ESPECIALES)          # antes de limpiar (la limpieza oculta iframes pequeños)
        print("  [2/7] movimiento (muestreo de scroll y animaciones)")
        d["movimiento"] = page.evaluate(JS_MOVIMIENTO)
        try:
            d["movimiento"]["scroll"] = detectar_movimiento_scroll(page)
        except Exception as ex:
            d["movimiento"]["scroll"] = []
            print(f"    (muestreo de scroll falló: {ex})")
        print("  [3/7] hojas de estilo (breakpoints, :hover, @keyframes)")
        d["css"] = css_de_la_web(page)
        print("  [4/7] preparar página (sin ventanas emergentes, scroll desbloqueado)")
        preparar_pagina(page, url)
        page.evaluate(JS_SECCIONES, MAX_SECCIONES)
        print("  [5/7] contenido especial, diseño y componentes")
        d["diseno"] = page.evaluate(JS_DISENO)
        d["componentes"] = page.evaluate(JS_COMPONENTES)
        print("  [6/7] columnas y capturas en 3 anchos")
        cols = {}
        for nombre, (w, h) in ANCHOS.items():
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(1000)
            page.add_style_tag(content=CSS_DESPLEGAR)
            page.evaluate(JS_DESPLEGAR)
            page.evaluate(JS_LIMPIAR)
            for n, c, _ in page.evaluate(JS_COLUMNAS):
                cols.setdefault(n, {})[nombre] = c
            alto = min(page.evaluate("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)"), 14000)
            try:
                capturar(page, out / "capturas" / f"pagina_{nombre}.png", w, alto)
            except Exception as ex:
                print(f"    (captura {nombre} falló: {ex})")
        nav.close()
    for s in spec["secciones"]:
        s["columnas_por_ancho"] = cols.get(s["n"], {"escritorio": s.get("columnas"), "movil": s.get("columnas_movil")})
        for v in ("escritorio", "movil"):
            p = carpeta_sec / f"sec_{s['n']}_{v}.png"
            if p.exists():
                (out / "capturas" / p.name).write_bytes(p.read_bytes())
    d["secciones"] = spec["secciones"]
    print("  [7/7] clasificar y escribir informes")
    d["clasificacion"] = clasificar(d["tecnologia"], d["especiales"], d["diseno"], d["componentes"], d["secciones"], d["rendimiento"])
    d["recomendaciones"] = recomendaciones(d)
    (out / "diseccion.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    inf = informe_md(d)
    (out / "informe_web.md").write_text(inf, encoding="utf-8")
    (out / "fichas_secciones.md").write_text(fichas_md(d), encoding="utf-8")
    if clonar:
        try:
            from capturar import capturar_web
            print("  [extra] clon fiel (v8)")
            capturar_web(url, out / "clon")
        except Exception as ex:
            print(f"  (clon fiel falló: {ex})")
    (BASE / "ultima_diseccion.txt").write_text(str(out), encoding="utf-8")
    print(f"\nInforme ({len(inf) // 4} tokens aprox.): {out / 'informe_web.md'}\n")
    print(inf)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else (BASE / "url.txt").read_text(encoding="utf-8").strip().splitlines()[0].strip()
    diseccionar(url, clonar="--clonar" in sys.argv)
