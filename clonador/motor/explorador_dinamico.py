import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
explorador_dinamico.py - Explorador determinista de interactividad y medios (sin IA).

Abre la web igual que extraer.py (mismas secciones data-clon-sec) y saca lo que una foto no ve:
  1. Medios        -> vídeos (fuentes, poster, autoplay, fotograma, si es blob/streaming), canvas
                      (2D/WebGL: imagen real con toDataURL + captura), iframes (tipo, HTML interno, captura)
  2. Pestañas      -> clic en cada pestaña: qué tarjetas se ven, estilo activa/inactiva, y lo que
                      SOLO aparece dentro de esa pestaña (bolitas y modales escondidos)
  3. Bolitas       -> clic en cada color: nombre, hex real, imagen que se activa, estilo del anillo.
                      Modo configurador: si están bloqueadas, elige antes los pasos previos
  4. Modales       -> abre cada '+', desplegable o menú: título, bloques, imágenes, enlaces, estilo,
                      capa de fondo, transición, y cómo se cierra
  5. Hover         -> pasa el ratón por cada tipo de botón/enlace/tarjeta y anota qué propiedades cambian

Cada acción va en su propio try/except: lo que falla se apunta en "errores" y se sigue. Si un clic
cambia de página o un modal no se deja cerrar, se recarga y se continúa (ids deterministas).

Guarda:  workspace/<web>/interactividad.json            (o interactividad_movil.json con --movil)
         workspace/<web>/capturas_dinamicas/*.png        (pestañas, modales)
         workspace/<web>/medios_dinamicos/*               (fotogramas, canvas, HTML de iframes)

Uso:  python explorador_dinamico.py <url> [--movil] [--sin-capturas] [--sin-hover] [--cabecera] [--visible]
"""
import base64
import json
import re
import struct
import time
import zlib
from pathlib import Path
from urllib.parse import urlparse

from extraer import (ESCRITORIO, JS_SECCIONES, LOCALE, MAX_SECCIONES, MOVIL, NAV_ARGS, marcar_secciones, nombre_web,
                     opciones_movil, preparar_pagina)

BASE = Path(__file__).resolve().parent
SALIDA = Path(__file__).resolve().parent.parent / "workspace"
MAX_MODALES = 60
MAX_HOVER = 60


class Navego(Exception):
    """Un clic sacó a la página a otro documento."""


class NoCerro(Exception):
    """Un modal se abrió y no hubo forma de cerrarlo."""


# Antes de cargar: WebGL con preserveDrawingBuffer (si no, toDataURL devuelve negro) y se anota qué
# contexto pide cada canvas. Vale también dentro de los iframes.
JS_ANTES_DE_CARGAR = r"""
(() => { const orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (tipo, attrs) {
    if (/webgl/i.test(tipo)) attrs = Object.assign({}, attrs, { preserveDrawingBuffer: true });
    try { if (!this.dataset.clonCtx) this.dataset.clonCtx = tipo; } catch (e) {}
    return orig.call(this, tipo, attrs); }; })();
"""

# extraer.py oculta con display:none!important todo lo fijo (y lo que se llame 'modal') y congela las
# animaciones: bien para fotos, pero así los modales no pueden abrirse. Se deshace tras marcar secciones
# (salvo cookies, chats y avisos de país, que siguen fuera).
JS_DESHACER = r"""
() => { let n = 0;
  for (const st of document.querySelectorAll('style')) if (st.textContent.startsWith('*{animation:none!important')) { st.remove(); n++; }
  const QUEDAN = /(cookie|consent|gdpr|onetrust|cookiebot|usercentrics|didomi|truste|iubenda|sp_message|chat|intercom|drift|zendesk|hubspot|klaviyo|locale|geo-banner|country)/i;
  for (const e of document.querySelectorAll('[style*="display"]')) {
    if (e.style.getPropertyValue('display') === 'none' && e.style.getPropertyPriority('display') === 'important'
        && !QUEDAN.test((e.id || '') + ' ' + (e.getAttribute('class') || ''))) { e.style.removeProperty('display'); n++; } }
  return n; }
"""

# espera a que el DOM deje de cambiar (quieto ms seguidos sin mutaciones), con tope
JS_CALMA = r"""
([quieto, maximo]) => new Promise(res => { let t; const fin = () => { obs.disconnect(); res(true); };
  const obs = new MutationObserver(() => { clearTimeout(t); t = setTimeout(fin, quieto); });
  obs.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
  t = setTimeout(fin, quieto); setTimeout(fin, maximo); })
"""

# espera a que acaben las transiciones/animaciones CSS finitas (las infinitas y las ligadas al scroll no cuentan)
JS_ANIMACIONES = r"""
([id, maximo]) => { const raiz = id ? window.__clon.el(id) : null;
  const lista = (raiz ? raiz.getAnimations({ subtree: true }) : document.getAnimations()).filter(a => { try {
    return a.playState === 'running' && a.timeline === document.timeline && a.effect.getComputedTiming().iterations !== Infinity; } catch (e) { return false; } });
  return Promise.race([Promise.all(lista.map(a => a.finished.catch(() => 0))), new Promise(r => setTimeout(r, maximo))]).then(() => lista.length); }
"""

# Kit en window.__clon: todo lo que se detecta se marca con data-clon-x="<letra><n>" para pulsarlo luego
# desde Playwright. Letras: g grupo de pestañas, t pestaña, a ámbito, c tarjeta, s grupo de bolitas,
# w bolita, k ámbito de fotos, i/b imagen, m disparador, d modal, x cerrar, p paso previo, h hover,
# v vídeo, n canvas, f iframe.
JS_KIT = r"""
() => {
  const C = { n: 0, grupos: {}, antes: new Set(), antesInfo: {} };
  C.FUERA = 'header,footer,[role="banner"],[role="contentinfo"],#globalheader,#globalfooter,[id*="globalnav" i],[class*="globalnav" i],[class*="globalfooter" i],[id^="ac-gn"]';
  C.SEL_DLG = 'dialog,[role="dialog"],[role="alertdialog"],[aria-modal="true"],[class*="modal" i],[class*="drawer" i],[class*="overlay" i],[class*="popover" i],[class*="lightbox" i],[class*="sheet" i],[class*="menu" i],[class*="flyout" i]';
  C.limpio = (t) => (t || '').replace(/\s+/g, ' ').trim();
  C.abs = (u) => { try { return u ? new URL(u, location.href).href : ''; } catch (e) { return u || ''; } };
  C.clase = (e) => e.getAttribute('class') || '';
  // todos los que casan, también dentro de shadow DOM abiertos (reproductores, web components)
  C.todos = (sel) => { const out = [...document.querySelectorAll(sel)];
    const visitar = (raiz) => { for (const e of raiz.querySelectorAll('*')) if (e.shadowRoot) { out.push(...e.shadowRoot.querySelectorAll(sel)); visitar(e.shadowRoot); } };
    visitar(document); return out; };
  // visible de verdad: ocupa sitio y ni él ni sus padres están ocultos (aria=true: aria-hidden/inert también cuentan)
  C.visible = (e, aria) => {
    if (!e || !e.isConnected) return false;
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return false;
    for (let x = e; x && x.nodeType === 1; x = x.parentElement || (x.getRootNode() && x.getRootNode().host)) {
      const s = getComputedStyle(x);
      if (s.display === 'none' || s.visibility === 'hidden' || s.visibility === 'collapse' || +s.opacity < 0.05) return false;
      if (aria && (x.getAttribute('aria-hidden') === 'true' || x.hasAttribute('inert'))) return false;
    }
    return true;
  };
  C.sec = (e) => { let x = e;
    while (x) { const s = x.closest('[data-clon-sec]'); if (s) return s.dataset.clonSec;
      const c = x.closest('[data-clon-capa]'); if (c) return c.dataset.clonCapa;
      const r = x.getRootNode(); x = r && r.host; }
    return null; };
  C.id = (e, p) => { if (!e.dataset.clonX) e.dataset.clonX = p + (++C.n); return e.dataset.clonX; };
  C.el = (id) => document.querySelector(`[data-clon-x="${id}"]`) || C.todos(`[data-clon-x="${id}"]`)[0] || null;
  C.textoRef = (ids) => C.limpio((ids || '').split(/\s+/).map(i => { const x = i && document.getElementById(i); return x ? x.textContent : ''; }).join(' '));
  C.nombre = (e) => {
    const a = e.getAttribute('aria-label') || C.textoRef(e.getAttribute('aria-labelledby')) || e.getAttribute('title');
    if (a) return C.limpio(a);
    if (e.labels && e.labels.length) return C.limpio(e.labels[0].innerText || e.labels[0].textContent);
    const t = C.limpio(e.innerText || e.textContent); if (t) return t;
    const img = e.querySelector('img[alt]'); if (img && img.alt) return C.limpio(img.alt);
    return C.limpio(e.value || e.getAttribute('data-value') || '');
  };
  // en las bolitas el nombre suele estar en un hijo (button/input con aria-label dentro de un li)
  C.nombreSw = (e) => {
    const a = e.getAttribute('aria-label') || C.textoRef(e.getAttribute('aria-labelledby')); if (a) return C.limpio(a);
    const h = e.querySelector('[aria-label]'); if (h) return C.limpio(h.getAttribute('aria-label'));
    const ctl = e.control || e.querySelector('input'); if (ctl && ctl.getAttribute('aria-label')) return C.limpio(ctl.getAttribute('aria-label'));
    return C.nombre(e) || C.limpio(ctl && ctl.value);
  };
  // un radio escondido se pulsa por su <label>
  C.objetivo = (e) => (e.matches('input') && !C.visible(e, false) && e.labels && e.labels[0]) ? e.labels[0] : e;
  C.activo = (e) => { const x = e.control || e;
    return ['aria-selected', 'aria-checked', 'aria-pressed', 'aria-current'].some(a => { const v = e.getAttribute(a) || x.getAttribute(a); return v && v !== 'false'; })
      || !!x.checked || /(^|[\s_-])(active|selected|current|is-checked|checked)([\s_-]|$)/i.test(C.clase(e)); };
  C.apagado = (e) => { const ctl = e.matches('input,button') ? e : (e.control || e.querySelector('input,button'));
    return !!(ctl && ctl.disabled) || e.getAttribute('aria-disabled') === 'true' || (!!ctl && ctl.getAttribute('aria-disabled') === 'true'); };
  C.pareceBolita = (e) => { const r = e.getBoundingClientRect();
    return r.width >= 8 && r.height >= 8 && r.width <= 56 && r.height <= 56 && Math.abs(r.width - r.height) <= 8; };
  C.hex = (c) => { const m = c && c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); if (p.length > 3 && p[3] === 0) return null;
    return '#' + p.slice(0, 3).map(x => Math.round(x).toString(16).padStart(2, '0')).join(''); };
  // la "piel" de un elemento: lo necesario para dibujarlo igual (pestaña activa, anillo de bolita, modal)
  C.estiloCaja = (e) => { if (!e) return null; const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return { color: s.color, fondo: s.backgroundColor, fondo_imagen: s.backgroundImage === 'none' ? '' : s.backgroundImage.slice(0, 300),
      borde: `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}`, radio: s.borderRadius, padding: s.padding,
      fuente: `${s.fontWeight} ${s.fontSize}/${s.lineHeight} ${s.fontFamily.split(',')[0].replace(/"/g, '')}`, espaciado: s.letterSpacing,
      sombra: s.boxShadow, contorno: s.outlineStyle === 'none' ? '' : `${s.outlineWidth} ${s.outlineStyle} ${s.outlineColor} offset ${s.outlineOffset}`,
      subrayado: s.textDecorationLine, opacidad: s.opacity, transform: s.transform, transicion: s.transition,
      ancho: Math.round(r.width), alto: Math.round(r.height) }; };
  C.estiloId = (id) => C.estiloCaja(C.el(id));
  // color de una bolita: el relleno más interior que ocupe buena parte de ella (fondo, degradado o svg)
  C.color = (e) => {
    const R = e.getBoundingClientRect(), area = R.width * R.height; let hallado = null;
    // bolita hecha con una foto (Apple: <li><picture><img>): el hex se saca luego de la foto
    const img = [...e.querySelectorAll('img')].find(i => { const r = i.getBoundingClientRect(); return r.width * r.height >= area * 0.5; });
    if (img) return { hex: null, imagen: C.abs(img.currentSrc || img.src) };
    for (const x of [e, ...e.querySelectorAll('*')].slice(0, 12)) {
      const r = x.getBoundingClientRect(); if (r.width * r.height < area * 0.3) continue;
      const s = getComputedStyle(x);
      const h = C.hex(s.backgroundColor); if (h) hallado = { hex: h };
      if (s.backgroundImage && s.backgroundImage !== 'none') {
        const u = s.backgroundImage.match(/url\(["']?([^"')]+)/);
        hallado = { hex: C.hex((s.backgroundImage.match(/rgba?\([^)]+\)/) || [])[0]), fondo: u ? C.abs(u[1]) : s.backgroundImage.slice(0, 300) };
      }
      if (['circle', 'rect', 'path', 'ellipse'].includes(x.tagName)) { const f = C.hex(s.fill); if (f) hallado = { hex: f }; }
    }
    return hallado;
  };
  // ¿se puede pulsar o es solo un indicador decorativo?
  C.pulsable = (e) => e.matches('button,input,label,select,a[href],[role="radio"],[role="option"],[role="button"],[role="tab"],[tabindex]')
    || !!e.querySelector('button,input,a[href],[role="radio"],[role="option"]') || getComputedStyle(e).cursor === 'pointer';

  // ---------- tarjetas: cada titular sube hasta el bloque más grande que no contenga otro titular ----------
  C.titulares = (ambito, fuera = []) => {
    const ok = (h) => C.limpio(h.textContent).length > 1 && !fuera.some(f => f && f.contains(h));
    let hs = [...ambito.querySelectorAll('h2,h3,h4,h5,h6')].filter(ok);
    if (!hs.length) hs = [...ambito.querySelectorAll('[class*="title" i],[class*="headline" i],[class*="name" i]')].filter(ok);
    return hs.filter(h => !hs.some(o => o !== h && o.contains(h)));
  };
  C.tarjetas = (ambito, fuera = []) => {
    const hs = C.titulares(ambito, fuera);
    const cuenta = (x) => hs.filter(h => x.contains(h)).length;
    return hs.map(h => { let t = h; while (t.parentElement && t.parentElement !== ambito && cuenta(t.parentElement) === 1) t = t.parentElement; return t; });
  };
  C.titulo = (t) => { const h = C.titulares(t)[0]; return C.limpio(h ? h.textContent : C.nombre(t)).slice(0, 120); };
  C.imagenPrincipal = (t) => { let mejor = null, area = 0;
    for (const i of t.querySelectorAll('img')) { const r = i.getBoundingClientRect(); const a = r.width * r.height || i.naturalWidth * i.naturalHeight;
      if (a > area && (i.currentSrc || i.src)) { area = a; mejor = C.abs(i.currentSrc || i.src); } }
    return mejor || ''; };
  C.ficha = (t) => { const a = t.matches('a[href]') ? t : t.querySelector('a[href]');
    return { id: C.id(t, 'c'), titulo: C.titulo(t), visible: C.visible(t, false), enlace: a ? C.abs(a.getAttribute('href')) : '', imagen: C.imagenPrincipal(t) }; };

  // ---------- 1. medios: vídeo, canvas, iframes ----------
  C.detectarMedios = () => {
    const caja = (e) => { const r = e.getBoundingClientRect(); return { x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), ancho: Math.round(r.width), alto: Math.round(r.height) }; };
    const grande = (e, min) => { const r = e.getBoundingClientRect(); return r.width >= min && r.height >= min; };
    const deFondo = (e) => { const s = getComputedStyle(e); if (s.position === 'fixed') return true;
      const p = e.parentElement; if (!p) return false; const a = e.getBoundingClientRect(), b = p.getBoundingClientRect();
      return a.width >= b.width * 0.95 && a.height >= b.height * 0.95 && (p.innerText || '').trim().length > 0; };
    const videos = C.todos('video').filter(v => grande(v, 20)).map(v => { const s = getComputedStyle(v);
      return Object.assign({ id: C.id(v, 'v'), sec: C.sec(v), src: C.abs(v.currentSrc || v.getAttribute('src') || ''),
        fuentes: [...v.querySelectorAll('source')].map(x => ({ src: C.abs(x.getAttribute('src')), tipo: x.type || '', media: x.media || '' })),
        poster: C.abs(v.getAttribute('poster') || ''), autoplay: v.autoplay, loop: v.loop, muted: v.muted, playsinline: v.playsInline,
        controles: v.controls, preload: v.preload, resolucion: [v.videoWidth, v.videoHeight],
        duracion: isFinite(v.duration) ? Math.round(v.duration * 10) / 10 : null, reproduciendo: !v.paused,
        object_fit: s.objectFit, object_position: s.objectPosition, radio: s.borderRadius, de_fondo: deFondo(v) && !v.controls,
        visible: C.visible(v, false) }, caja(v)); });
    const canvas = C.todos('canvas').filter(c => grande(c, 20)).map(c => { const s = getComputedStyle(c);
      return Object.assign({ id: C.id(c, 'n'), sec: C.sec(c), contexto: c.dataset.clonCtx || 'desconocido', resolucion: [c.width, c.height],
        posicion: s.position, de_fondo: deFondo(c), visible: C.visible(c, false) }, caja(c)); });
    const iframes = C.todos('iframe').filter(f => grande(f, 50)).map(f => {
      const src = C.abs(f.getAttribute('src') || ''), s = getComputedStyle(f);
      const tipo = /youtube(-nocookie)?\.com|youtu\.be/i.test(src) ? 'youtube' : /vimeo\.com/i.test(src) ? 'vimeo'
        : /google\.[^/]+\/maps|maps\.google|openstreetmap|mapbox/i.test(src) ? 'mapa' : /spotify\.com/i.test(src) ? 'spotify'
        : /twitter\.com|\/\/x\.com/i.test(src) ? 'twitter' : /instagram\.com/i.test(src) ? 'instagram' : /calendly\.com/i.test(src) ? 'calendly'
        : /typeform|hsforms|jotform|forms\.gle|docs\.google\.com\/forms/i.test(src) ? 'formulario' : /recaptcha|captcha|challenge/i.test(src) ? 'captcha'
        : f.hasAttribute('srcdoc') ? 'srcdoc' : 'embed';
      return Object.assign({ id: C.id(f, 'f'), sec: C.sec(f), src, tipo, titulo: f.title || '', allow: f.getAttribute('allow') || '',
        loading: f.getAttribute('loading') || '', radio: s.borderRadius, visible: C.visible(f, false) }, caja(f)); });
    return { videos, canvas, iframes };
  };
  C.canvasDatos = (id) => { const c = C.el(id); if (!c) return { error: 'no existe' };
    try { return { url: c.toDataURL('image/png') }; } catch (e) { return { error: String(e.name || e) }; } };

  // ---------- 2. pestañas y filtros ----------
  C.ambitoDe = (cont) => { let a = cont.parentElement;
    while (a && a !== document.body) { if (C.tarjetas(a, [cont]).length >= 2 || a.hasAttribute('data-clon-sec')) return a; a = a.parentElement; }
    return cont.parentElement || document.body; };
  C.detectarTabs = (cabecera) => {
    const out = [], firmas = new Set();
    const registrar = (cont, ctrls, tipo) => {
      if (!cabecera && cont.closest(C.FUERA)) return;
      ctrls = [...new Set(ctrls.map(C.objetivo))].filter(c => C.visible(c, false) && !c.dataset.clonX);
      const nombres = ctrls.map(c => { const t = C.limpio(c.innerText); return t && t.length <= 60 ? t : C.nombre(c); });   // lo que se ve, no el aria-label
      if (ctrls.length < 2 || ctrls.length > 12 || nombres.some(n => n.length < 2 || n.length > 60)) return;
      if (ctrls.every(C.pareceBolita)) return;                // radios de color: son bolitas, no pestañas
      const firma = nombres.join('|'); if (firmas.has(firma)) return; firmas.add(firma);
      const gid = C.id(cont, 'g'), ambito = C.ambitoDe(cont);
      C.grupos[gid] = { ambito: C.id(ambito, 'a') };
      out.push({ id: gid, tipo, sec: C.sec(cont), etiqueta: C.limpio(cont.getAttribute('aria-label') || C.textoRef(cont.getAttribute('aria-labelledby'))),
        tabs: ctrls.map((c, i) => ({ id: C.id(c, 't'), texto: nombres[i], aria_label: c.getAttribute('aria-label') || '', activo: C.activo(c), controla: c.getAttribute('aria-controls') || '' })) });
    };
    for (const tl of document.querySelectorAll('[role="tablist"]')) registrar(tl, [...tl.querySelectorAll('[role="tab"]')], 'tablist');
    const porNombre = {};
    for (const r of document.querySelectorAll('input[type="radio"][name]')) (porNombre[r.name] = porNombre[r.name] || []).push(r);
    for (const rs of Object.values(porNombre)) { if (rs.length < 2) continue;
      let cont = rs[0].parentElement; while (cont && !rs.every(r => cont.contains(r))) cont = cont.parentElement;
      if (cont) registrar(cont, rs, 'radios'); }
    for (const cont of document.querySelectorAll('[class*="filter" i],[class*="tabnav" i],[class*="tab-nav" i],[class*="tabs" i],[class*="segment" i],[data-filter],[data-filters]')) {
      if (cont.closest('[role="tablist"]')) continue;
      registrar(cont, [...cont.querySelectorAll('button,[role="button"],a[href^="#"],[data-filter]')], 'filtro');
    }
    return out;
  };
  C.estadoTabs = (gid, tid) => {
    const g = C.grupos[gid], ambito = g && C.el(g.ambito); if (!ambito) return null;
    // solo lo que va después de la barra de pestañas (el titular de la sección no es una tarjeta)
    const cont = C.el(gid);
    const res = { tarjetas: C.tarjetas(ambito, [cont]).filter(t => cont.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING).map(C.ficha) };
    const tab = C.el(tid), ctl = tab && (tab.getAttribute('aria-controls') || (tab.control && tab.control.getAttribute('aria-controls')));
    const panel = ctl && document.getElementById(ctl.split(' ')[0]);
    if (panel && C.visible(panel, false)) res.panel = { id: panel.id, titulo: C.titulo(panel), texto: C.limpio(panel.innerText).slice(0, 800) };
    return res;
  };

  // ---------- 3. bolitas de color ----------
  C.detectarSwatches = (cabecera) => {
    const SEL = 'input[type="radio"],[role="radio"],[role="option"],button,label,a,li,span,[class*="swatch" i],[class*="color" i],[class*="colour" i]';
    const NO = /(diapositiva|slide|p[aá]gina|page|ir a|go to|anterior|siguiente|previous|next|paus|play|reproduc)/i;
    const vistos = new Set(); let cands = [];
    for (const e0 of document.querySelectorAll(SEL)) {
      const e = C.objetivo(e0);
      if (vistos.has(e)) continue; vistos.add(e);
      if (e.closest('[data-clon-x^="w"]') || e.querySelector('[data-clon-x^="w"]')) continue;   // ya explorada (o su li/label)
      if (e.closest('[data-clon-x^="t"],[data-clon-x^="g"]') || (!cabecera && e.closest(C.FUERA))) continue;
      if (!C.pareceBolita(e) || !C.visible(e, false) || NO.test(C.nombreSw(e))) continue;
      if (C.color(e)) cands.push(e);
    }
    cands = cands.filter(c => !cands.some(o => o !== c && o.contains(c)));        // li > button > span: el de fuera
    const grupos = new Map();
    for (const c of cands) {
      let cont = c.parentElement, hallado = null;
      for (let i = 0; i < 4 && cont; i++) { if (cands.filter(o => cont.contains(o)).length >= 2) { hallado = cont; break; } cont = cont.parentElement; }
      if (hallado && !grupos.has(hallado)) grupos.set(hallado, cands.filter(o => hallado.contains(o)));
    }
    const todos = [...grupos.keys()], validos = [];
    for (const [cont, items] of grupos) {
      if (items.length < 2 || items.length > 20 || todos.some(o => o !== cont && cont.contains(o))) continue;
      const cols = items.map(C.color);
      if (new Set(cols.map(c => c.hex || c.fondo || c.imagen)).size < 2) continue;   // puntos de carrusel: todos iguales
      validos.push([cont, items, cols]);
    }
    // los límites de cada tarjeta se miden solo contra grupos válidos (un '+' redondo junto a las bolitas no cuenta)
    const conts = validos.map(v => v[0]), out = [];
    for (const [cont, items, cols] of validos) {
      // ámbito de fotos: lo más grande sin otra fila de bolitas (en un configurador, la galería queda lejos)
      let card = cont;
      while (card.parentElement && card.parentElement !== document.body && !card.hasAttribute('data-clon-sec')
             && !conts.some(k => k !== cont && card.parentElement.contains(k))) card = card.parentElement;
      // título: el bloque más cercano con un solo titular (la tarjeta del producto o el paso "Color")
      let bloque = cont;
      while (bloque.parentElement && bloque.parentElement !== document.body && C.titulares(bloque.parentElement).length <= 1) bloque = bloque.parentElement;
      const activa = items.find(C.activo), inactiva = items.find(e => !C.activo(e) && !C.apagado(e));
      out.push({ id: C.id(cont, 's'), sec: C.sec(cont), tarjeta: { id: C.id(card, 'k'), titulo: C.titulo(bloque) }, interactivas: items.some(C.pulsable),
        estilo_activa: activa ? C.estiloCaja(activa) : null, estilo_inactiva: inactiva ? C.estiloCaja(inactiva) : null,
        colores: items.map((e, i) => ({ id: C.id(e, 'w'), nombre: C.nombreSw(e), hex: cols[i].hex, fondo: cols[i].fondo || '', imagen_bolita: cols[i].imagen || '',
                                        activo: C.activo(e), deshabilitado: C.apagado(e) })) });
    }
    return out;
  };
  C.estadoBolitas = (sid) => { const g = C.el(sid); return g ? [...g.querySelectorAll('[data-clon-x^="w"]')].concat(g.matches('[data-clon-x^="w"]') ? [g] : [])
    .map(e => ({ id: e.dataset.clonX, nombre: C.nombreSw(e), deshabilitado: C.apagado(e), activo: C.activo(e) })) : []; };
  // modo configurador: grupos de opciones ANTERIORES a las bolitas que aún no tienen nada elegido
  C.pasosPrevios = (sid) => {
    const g = C.el(sid); if (!g) return [];
    const raiz = g.closest('[data-clon-sec]') || document.body, grupos = new Map();
    for (const r of raiz.querySelectorAll('input[type="radio"][name],[role="radio"]')) {
      if (g.contains(r) || !(r.compareDocumentPosition(g) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
      const clave = r.name || (r.closest('[role="radiogroup"]') || r.parentElement);
      if (!grupos.has(clave)) grupos.set(clave, []); grupos.get(clave).push(r);
    }
    const out = [];
    for (const rs of grupos.values()) {
      if (rs.some(r => r.checked || r.getAttribute('aria-checked') === 'true')) continue;
      const r = rs.find(x => !x.disabled && x.getAttribute('aria-disabled') !== 'true'); if (!r) continue;
      const obj = C.objetivo(r);
      out.push({ id: C.id(obj, 'p'), texto: (C.limpio((obj.innerText || '').split('\n')[0]) || C.nombre(obj)).slice(0, 80) });   // "13 pulgadas", sin el precio
    }
    return out;
  };
  C.fotos = (kid, sid) => {
    const k = C.el(kid), grupo = C.el(sid); if (!k) return [];
    const out = [], area = (e) => { const r = e.getBoundingClientRect(); return Math.round(r.width * r.height); };
    for (const i of k.querySelectorAll('img')) { if (grupo && grupo.contains(i)) continue;
      out.push({ id: C.id(i, 'i'), src: C.abs(i.currentSrc || i.src), visible: C.visible(i, false), area: area(i), alt: i.alt || '' }); }
    for (const e of [k, ...k.querySelectorAll('*')]) { if (e.tagName === 'IMG' || (grupo && grupo.contains(e))) continue;
      const m = getComputedStyle(e).backgroundImage.match(/url\(["']?([^"')]+)/); if (!m) continue;
      out.push({ id: C.id(e, 'b'), src: C.abs(m[1]), visible: C.visible(e, false), area: area(e), alt: '' }); }
    return out;
  };

  // ---------- 4. modales, desplegables y menús ----------
  C.detectarModales = (cabecera, maximo) => {
    const NAVEG = /(anterior|siguiente|previous|next|pausa|pause|reproducir|play|diapositiva|slide|cerrar|close)/i;
    const PISTA = /(m[aá]s|more|info|detalle|detail|abrir|open|expand|ampliar|ver |learn|saber|men[uú])/i;
    const CLASE = /(modal|trigger|overlay|drawer|expand|toggle|accordion|popover|lightbox|disclosure|menu|hamburger|burger)/i;
    const out = [];
    for (const e of document.querySelectorAll('button,[role="button"],a[href^="#"],summary,[aria-haspopup],[aria-expanded],[aria-controls]')) {
      if (out.length >= maximo) break;
      if ('mxp'.includes((e.dataset.clonX || '-')[0])) continue;           // ya explorado / botón de cerrar / paso previo
      if (e.closest('[data-clon-x^="t"],[data-clon-x^="w"],[role="tab"],[role="tablist"]') || e.querySelector('[data-clon-x^="w"]')) continue;
      if ((!cabecera && e.closest(C.FUERA)) || !C.visible(e, true)) continue;
      const nom = C.nombre(e), txt = C.limpio(e.innerText), r = e.getBoundingClientRect(), hp = e.getAttribute('aria-haspopup');
      if (NAVEG.test(e.getAttribute('aria-label') || '')) continue;
      const ctl = e.getAttribute('aria-controls'), destino = ctl && document.getElementById(ctl.split(' ')[0]);
      const motivo = (hp && hp !== 'false') ? 'aria-haspopup'
        : e.hasAttribute('aria-expanded') ? 'aria-expanded'
        : e.tagName === 'SUMMARY' ? 'details'
        : /^[+＋]$/.test(txt) ? 'boton-mas'
        : (destino && destino.getAttribute('role') !== 'tabpanel') ? 'aria-controls'
        : (PISTA.test(nom) && (e.querySelector('svg') || CLASE.test(C.clase(e)))) ? 'icono-mas'
        : (CLASE.test(C.clase(e) + ' ' + e.id) && r.width <= 80 && r.height <= 80) ? 'clase'
        : null;
      if (!motivo) continue;
      out.push({ id: C.id(e, 'm'), motivo, sec: C.sec(e), nombre: nom.slice(0, 160), texto: txt.slice(0, 80),
        aria: { haspopup: hp || '', expanded: e.getAttribute('aria-expanded') || '', controls: ctl || '' } });
    }
    return out;
  };
  C.antesModal = (id) => {
    C.antes = new Set([...document.querySelectorAll(C.SEL_DLG)].filter(d => C.visible(d, false)));
    const e = C.el(id), ctl = e && e.getAttribute('aria-controls'), t = ctl && document.getElementById(ctl.split(' ')[0]);
    C.antesInfo = { expandido: e ? e.getAttribute('aria-expanded') : null, ctlVisible: t ? C.visible(t, false) : null,
                    abierto: e && e.tagName === 'SUMMARY' ? e.parentElement.open : null };
    return true;
  };
  C.contenido = (d, cont) => {
    const h = d.querySelector('h1,h2,h3,h4,[class*="title" i],[class*="headline" i]');
    const bloques = [];
    for (const x of d.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,figcaption,blockquote')) {
      if (x.tagName === 'LI' && x.querySelector('p,h1,h2,h3,h4,h5,h6')) continue;
      if (!C.visible(x, false)) continue;
      const t = C.limpio(x.innerText); if (t) bloques.push({ tag: x.tagName.toLowerCase(), texto: t, estilo: C.estiloCaja(x) });
    }
    const esCerrar = (b) => C.visible(b, false) && /(cerrar|close|dismiss)/i.test(C.nombre(b) + ' ' + C.clase(b));
    const botones = (x) => x ? [...x.querySelectorAll('button,[role="button"],a')] : [];
    const cerrar = botones(cont).find(esCerrar) || botones(cont.parentElement).find(esCerrar);
    const s = getComputedStyle(d), r = d.getBoundingClientRect();
    return {
      rol: d.getAttribute('role') || d.tagName.toLowerCase(),
      titulo: C.textoRef(d.getAttribute('aria-labelledby')) || (h ? C.limpio(h.innerText) : ''),
      texto: C.limpio(d.innerText).slice(0, 6000),
      bloques: bloques.slice(0, 150),
      imagenes: [...d.querySelectorAll('img')].filter(i => C.visible(i, false)).map(i => ({ src: C.abs(i.currentSrc || i.src), alt: i.alt || '' })).slice(0, 30),
      videos: [...d.querySelectorAll('video')].map(v => ({ src: C.abs(v.currentSrc || v.src), poster: C.abs(v.poster) })).slice(0, 10),
      enlaces: [...d.querySelectorAll('a[href]')].filter(a => C.visible(a, false)).map(a => ({ texto: C.nombre(a).slice(0, 120), href: C.abs(a.getAttribute('href')) })).slice(0, 80),
      cerrar: cerrar ? { id: C.id(cerrar, 'x'), nombre: C.nombre(cerrar), estilo: C.estiloCaja(cerrar) } : null,
      estilo: Object.assign(C.estiloCaja(d), { posicion: s.position, z: s.zIndex, x: Math.round(r.left), y: Math.round(r.top),
                ancho_pct: Math.round(r.width / innerWidth * 100), alto_pct: Math.round(r.height / innerHeight * 100), max_ancho: s.maxWidth,
                animacion: s.animationName === 'none' ? '' : `${s.animationName} ${s.animationDuration} ${s.animationTimingFunction}` }),
    };
  };
  C.despuesModal = (id) => {
    const e = C.el(id); if (!e) return null;
    let nuevos = [...document.querySelectorAll(C.SEL_DLG)].filter(d => !C.antes.has(d) && !d.contains(e) && C.visible(d, false) && C.limpio(d.innerText).length > 0);
    nuevos = nuevos.filter(d => !nuevos.some(o => o !== d && o.contains(d)));
    let cont = null, tipo = null;
    if (nuevos.length) { nuevos.sort((a, b) => C.limpio(b.innerText).length - C.limpio(a.innerText).length); cont = nuevos[0]; tipo = 'modal'; }
    const ctl = e.getAttribute('aria-controls'), t = ctl && document.getElementById(ctl.split(' ')[0]);
    if (!cont && t && C.visible(t, false) && C.antesInfo.ctlVisible === false) { cont = t; tipo = 'desplegable'; }
    if (!cont && e.tagName === 'SUMMARY' && e.parentElement.open && !C.antesInfo.abierto) { cont = e.parentElement; tipo = 'details'; }
    if (!cont && C.antesInfo.expandido === 'false' && e.getAttribute('aria-expanded') === 'true') {
      cont = e.nextElementSibling || (e.parentElement && e.parentElement.nextElementSibling);
      if (cont && !C.visible(cont, false)) cont = null; tipo = 'desplegable';
    }
    if (!cont) return null;
    const SEL_REAL = 'dialog,[role="dialog"],[role="alertdialog"],[aria-modal="true"]';
    const d = cont.matches(SEL_REAL) ? cont : (cont.querySelector(SEL_REAL) || cont);
    const res = Object.assign({ tipo, contenedor: C.id(cont, 'd'), dialogo: C.id(d, 'd') }, C.contenido(d, cont));
    if (res.cerrar) res.cerrar.es_el_disparador = res.cerrar.id === id;     // el '+' que gira y se vuelve 'x'
    // capa de fondo (backdrop): el contenedor, o el primer antepasado fijo que tapa la pantalla
    let capa = cont !== d ? cont : null;
    for (let x = d.parentElement; !capa && x && x !== document.body; x = x.parentElement) {
      const r = x.getBoundingClientRect(); if (getComputedStyle(x).position === 'fixed' && r.width >= innerWidth * 0.8 && r.height >= innerHeight * 0.8) capa = x; }
    if (capa) { const s = getComputedStyle(capa); res.capa = { posicion: s.position, fondo: s.backgroundColor, desenfoque: s.backdropFilter, z: s.zIndex, transicion: s.transition }; }
    if (!res.titulo && tipo !== 'modal') res.titulo = C.nombre(e).slice(0, 160);   // desplegable: su título es la pregunta
    res.disparador_abierto = C.estiloCaja(e);                                    // el '+' girado, el chevron hacia arriba...
    return res;
  };

  // ---------- 5. hover ----------
  C.PROPS_HOVER = ['color', 'backgroundColor', 'backgroundImage', 'borderTopColor', 'borderBottomColor', 'boxShadow', 'textDecorationLine',
                   'textUnderlineOffset', 'opacity', 'transform', 'scale', 'translate', 'filter', 'outlineStyle', 'outlineColor', 'fill', 'stroke',
                   'visibility', 'display', 'width', 'letterSpacing'];
  C.detectarHover = (cabecera, maximo) => {
    const firmas = new Set(), out = [];
    for (const e of document.querySelectorAll('a[href],button,[role="button"],[role="tab"],summary,[class*="card" i],[class*="tile" i]')) {
      if (out.length >= maximo) break;
      if ((!cabecera && e.closest(C.FUERA)) || !C.visible(e, true)) continue;
      const r = e.getBoundingClientRect(); if (r.width < 16 || r.height < 12) continue;
      // un ejemplar por "tipo" de elemento: misma etiqueta + clases + clase del padre
      const p = e.parentElement, firma = [e.tagName, C.clase(e).split(/\s+/).filter(Boolean).sort().join('.'), e.getAttribute('role') || '',
                                         p ? C.clase(p).split(/\s+/)[0] : ''].join('|');
      if (firmas.has(firma)) continue; firmas.add(firma);
      const s = getComputedStyle(e);
      out.push({ id: C.id(e, 'h'), sec: C.sec(e), texto: (C.limpio(e.innerText) || C.nombre(e)).slice(0, 60), firma, cursor: s.cursor, transicion: s.transition });
    }
    return out;
  };
  C.estilosHover = (id) => { const e = C.el(id); if (!e) return null;
    return [e, ...e.querySelectorAll('*')].slice(0, 10).map((x, i) => { const s = getComputedStyle(x);
      const o = { nodo: i === 0 ? 'self' : x.tagName.toLowerCase() + (C.clase(x) ? '.' + C.clase(x).split(/\s+/)[0] : '') };
      for (const p of C.PROPS_HOVER) o[p] = s[p]; return o; }); };

  window.__clon = C;
  return true;
}
"""


def _ignorar(fn, *a):
    try:
        fn(*a)
    except Exception:
        pass


def _err(ex):
    return str(ex).splitlines()[0][:200] if str(ex) else type(ex).__name__


def esperar_calma(page, quieto=400, maximo=3000):
    """DOM quieto + red tranquila + transiciones CSS acabadas. Si la página cambió de documento: Navego."""
    try:
        page.evaluate(JS_CALMA, [quieto, maximo])
    except Exception:
        page.wait_for_timeout(quieto)
    try:
        page.wait_for_load_state("networkidle", timeout=1500)
    except Exception:
        pass
    try:
        page.evaluate(JS_ANIMACIONES, [None, 1200])
    except Exception:
        page.wait_for_timeout(250)
    try:
        vivo = page.evaluate("() => !!window.__clon")
    except Exception:
        vivo = False
    if not vivo:                                     # el kit desaparece solo si el documento se ha cambiado
        raise Navego(page.url)


def clicar(page, cid):
    """Clic normal de Playwright (espera a que sea pulsable); si algo lo tapa o no llega, clic por JS."""
    loc = page.locator(f'[data-clon-x="{cid}"]').first
    _ignorar(lambda: loc.scroll_into_view_if_needed(timeout=2000))
    try:
        loc.click(timeout=2500)
        return "click"
    except Exception:
        pass
    try:
        if page.evaluate("id => { const e = window.__clon.el(id); if (!e) return false; e.click(); return true; }", cid):
            return "js"
    except Exception:
        pass
    return None


def _pixel_central(png):
    """Color del píxel central de un PNG (RGB/RGBA de 8 bits, lo que da Playwright) sin librerías."""
    pos, ancho, alto, prof, tipo, datos = 8, 0, 0, 0, 0, b""
    while pos < len(png):
        n, t = struct.unpack(">I4s", png[pos:pos + 8])
        cuerpo = png[pos + 8:pos + 8 + n]
        pos += 12 + n
        if t == b"IHDR":
            ancho, alto, prof, tipo = struct.unpack(">IIBB", cuerpo[:10])
        elif t == b"IDAT":
            datos += cuerpo
        elif t == b"IEND":
            break
    if prof != 8 or tipo not in (2, 6) or not ancho:
        return None
    bpp = 3 if tipo == 2 else 4
    crudo, fila = zlib.decompress(datos), ancho * bpp
    prev = bytearray(fila)
    for y in range(alto // 2 + 1):                   # solo hace falta deshacer los filtros hasta la fila central
        ini = y * (fila + 1)
        f, linea = crudo[ini], bytearray(crudo[ini + 1:ini + 1 + fila])
        for i in range(fila):
            a = linea[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                linea[i] = (linea[i] + a) & 255
            elif f == 2:
                linea[i] = (linea[i] + b) & 255
            elif f == 3:
                linea[i] = (linea[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                linea[i] = (linea[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = linea
    x = (ancho // 2) * bpp
    return "#%02x%02x%02x" % tuple(prev[x:x + 3])


def _hex_por_foto(page, cid):
    try:
        return _pixel_central(page.locator(f'[data-clon-x="{cid}"]').first.screenshot(timeout=3000, animations="disabled"))
    except Exception:
        return None


_HEX_IMAGEN = {}


def _hex_por_imagen(ctx, url):
    """Bolita hecha con una foto: se abre la foto sola (sin sombras, bordes ni opacidad de 'deshabilitada')."""
    if url not in _HEX_IMAGEN:
        _HEX_IMAGEN[url] = None
        p = ctx.new_page()
        try:
            p.goto(url, timeout=10000)
            _HEX_IMAGEN[url] = _pixel_central(p.locator("img").first.screenshot(timeout=3000))
        except Exception:
            pass
        finally:
            _ignorar(p.close)
    return _HEX_IMAGEN[url]


def _foto(loc, ruta, rel):
    """Captura de un elemento; devuelve la ruta relativa para el JSON o '' si no se pudo."""
    try:
        loc.screenshot(path=str(ruta), timeout=6000)
        return f"{rel}/{ruta.name}"
    except Exception:
        return ""


def _oir_medios(lista):
    """Apunta los vídeos/audios/listas de streaming que pide la página (lo único que hay detrás de un src blob:)."""
    vistos = set()

    def oir(r):
        try:
            u, ct = r.url, (r.headers.get("content-type") or "").lower()
            if u in vistos or re.search(r"\.(m4s|ts|aac)(\?|$)", u, re.I):     # trozos sueltos de streaming: ruido
                return
            if ct.startswith(("video/", "audio/")) or "mpegurl" in ct or "dash+xml" in ct or re.search(r"\.(mp4|webm|m3u8|mpd|mov)(\?|$)", u, re.I):
                vistos.add(u)
                lista.append({"url": u, "tipo": ct.split(";")[0], "bytes": int(r.headers.get("content-length") or 0)})
        except Exception:
            pass
    return oir


def preparar(page, url, cabecera, secciones=None, movil=False):
    """Carga y marca la página igual que extraer.py; devuelve lo detectado (ids deterministas).
    secciones (las del spec.json del análisis): las de esta carga se renumeran contra ellas (textos en común y
    posición), así la sección N de interactividad.json es la sección N del spec, aunque esta carga corte distinto."""
    preparar_pagina(page, url)
    if secciones:                                    # el mismo elemento que en el análisis (o, si no, cortar y emparejar)
        remapeadas = marcar_secciones(page, secciones, movil)
    else:
        page.evaluate(JS_SECCIONES, MAX_SECCIONES * (2 if movil else 1))
        remapeadas = 0
    page.evaluate(JS_DESHACER)
    page.evaluate(JS_KIT)
    return {
        "remapeadas": remapeadas,
        "medios": page.evaluate("() => window.__clon.detectarMedios()"),
        "tabs": page.evaluate("c => window.__clon.detectarTabs(c)", cabecera),
        "swatches": page.evaluate("c => window.__clon.detectarSwatches(c)", cabecera),
        "modales": page.evaluate("([c, m]) => window.__clon.detectarModales(c, m)", [cabecera, MAX_MODALES]),
    }


# ---------------------------------------------------------------- 1. medios
def explorar_medios(page, med, medir, medios_red):
    """Vídeos, canvas e iframes. No pulsa nada: se hace lo primero, con la página recién cargada."""
    rel = medir.name
    for v in med["videos"]:
        loc = page.locator(f'[data-clon-x="{v["id"]}"]').first
        _ignorar(lambda: loc.scroll_into_view_if_needed(timeout=2000))
        # que tenga imagen antes de fotografiarlo: play() y esperar a readyState >= 2 (hay fotograma)
        listo = page.evaluate("""id => { const v = window.__clon.el(id); if (!v) return false; v.muted = true; const p = v.play(); if (p) p.catch(() => 0);
            return new Promise(r => { const t0 = Date.now(), mira = () => v.readyState >= 2 ? r(true) : Date.now() - t0 > 5000 ? r(false) : setTimeout(mira, 150); mira(); }); }""", v["id"])
        if listo:
            v.update(page.evaluate("""id => { const v = window.__clon.el(id); return { resolucion: [v.videoWidth, v.videoHeight],
                duracion: isFinite(v.duration) ? Math.round(v.duration * 10) / 10 : null, src: window.__clon.abs(v.currentSrc || v.src) }; }""", v["id"]))
        else:
            v["nota_reproduccion"] = "no llegó a tener imagen (códec no soportado, carga lenta o error): usa 'poster'"
        v["es_blob"] = v["src"].startswith("blob:")
        if v["es_blob"]:
            v["nota"] = "src blob: (streaming MSE/HLS): el archivo no se puede bajar tal cual; mira 'medios_red' y 'poster'"
        a = _foto(loc, medir / f"video_{v['id']}_a.png", rel)
        page.wait_for_timeout(700)
        b = _foto(loc, medir / f"video_{v['id']}_b.png", rel)
        v["fotograma"] = a
        v["animado"] = bool(a and b and (medir / f"video_{v['id']}_a.png").read_bytes() != (medir / f"video_{v['id']}_b.png").read_bytes())
        _ignorar((medir / f"video_{v['id']}_b.png").unlink)
    for c in med["canvas"]:
        loc = page.locator(f'[data-clon-x="{c["id"]}"]').first
        datos = {}
        try:
            datos = page.evaluate("id => window.__clon.canvasDatos(id)", c["id"])
        except Exception as ex:
            datos = {"error": _err(ex)}
        if datos.get("url", "").startswith("data:image/png;base64,"):
            ruta = medir / f"canvas_{c['id']}_real.png"
            ruta.write_bytes(base64.b64decode(datos["url"].split(",", 1)[1]))
            c["imagen_real"] = f"{rel}/{ruta.name}"           # lo que hay pintado, sin nada encima
        else:
            c["imagen_real"] = ""
            c["nota"] = ("canvas 'tainted' (pinta imágenes de otro dominio): solo vale la captura"
                         if "Security" in datos.get("error", "") else f"toDataURL falló: {datos.get('error', '?')}")
        a = _foto(loc, medir / f"canvas_{c['id']}.png", rel)
        page.wait_for_timeout(700)
        b = _foto(loc, medir / f"canvas_{c['id']}_b.png", rel)
        c["captura"] = a                                          # lo que ve el usuario (con lo que tenga encima)
        c["animado"] = bool(a and b and (medir / f"canvas_{c['id']}.png").read_bytes() != (medir / f"canvas_{c['id']}_b.png").read_bytes())
        _ignorar((medir / f"canvas_{c['id']}_b.png").unlink)
    origen = urlparse(page.url).netloc
    for f in med["iframes"]:
        loc = page.locator(f'[data-clon-x="{f["id"]}"]').first
        m = re.search(r"(?:embed/|v=|youtu\.be/|video/)([\w-]{6,})", f["src"])
        if m and f["tipo"] in ("youtube", "vimeo"):
            f["video_id"] = m.group(1)
        try:
            marco = loc.element_handle(timeout=3000).content_frame()
            if marco:
                f["url_real"] = marco.url
                f["mismo_origen"] = urlparse(marco.url).netloc in ("", origen)
                f["titulo_doc"] = marco.title()
                html = marco.content()
                if f["tipo"] != "captcha" and len(html) < 3_000_000:
                    # el HTML de dentro, con <base> para que sus rutas relativas sigan funcionando fuera
                    html = re.sub(r"<head([^>]*)>", lambda x: f'<head{x.group(1)}><base href="{marco.url}">', html, count=1, flags=re.I)
                    ruta = medir / f"iframe_{f['id']}.html"
                    ruta.write_text(html, encoding="utf-8")
                    f["html"] = f"{rel}/{ruta.name}"
                    f["html_kb"] = round(len(html) / 1024)
        except Exception as ex:
            f["nota"] = f"no se pudo leer por dentro: {_err(ex)}"
        f["captura"] = _foto(loc, medir / f"iframe_{f['id']}.png", rel)
    if medios_red:
        for v in med["videos"]:
            if v["es_blob"]:
                v["posibles_fuentes"] = [x["url"] for x in medios_red if re.search(r"m3u8|mpd|mpegurl|dash", x["url"] + x["tipo"], re.I)][:5]
    return med


# ---------------------------------------------------------------- 2. pestañas
def explorar_tabs(page, g, capdir, cabecera):
    pestanas, tarjetas, extras, estilos = [], {}, [], {}
    inicial = next((t for t in g["tabs"] if t["activo"]), g["tabs"][0])
    for t in g["tabs"]:
        entrada = {"texto": t["texto"], "aria_label": t["aria_label"], "activa_por_defecto": t["activo"], "controla": t["controla"]}
        try:
            entrada["metodo"] = clicar(page, t["id"])
            if not entrada["metodo"]:
                entrada["error"] = "no se pudo pulsar"
                pestanas.append(entrada)
                continue
            esperar_calma(page)
            st = page.evaluate("([g, t]) => window.__clon.estadoTabs(g, t)", [g["id"], t["id"]]) or {"tarjetas": []}
            entrada["tarjetas_visibles"] = [c["titulo"] for c in st["tarjetas"] if c["visible"]]
            if st.get("panel"):
                entrada["panel"] = st["panel"]
            # mismas tarjetas repetidas en cada panel (Apple pinta un panel por pestaña): se fusionan por título + imagen
            for c in st["tarjetas"]:
                if c["visible"]:
                    d = tarjetas.setdefault((c["titulo"], c["imagen"]), {"titulo": c["titulo"], "enlace": c["enlace"], "imagen": c["imagen"], "en_pestanas": []})
                    if t["texto"] not in d["en_pestanas"]:
                        d["en_pestanas"].append(t["texto"])
            if not estilos:                          # piel de la pestaña activa y de una inactiva, en el mismo instante
                otra = next((x for x in g["tabs"] if x["id"] != t["id"]), None)
                estilos = {"estilo_activa": page.evaluate("id => window.__clon.estiloId(id)", t["id"]),
                           "estilo_inactiva": page.evaluate("id => window.__clon.estiloId(id)", otra["id"]) if otra else None}
            # lo que solo existe dentro de esta pestaña: se explora después, volviendo a ella
            nuevos_sw = page.evaluate("c => window.__clon.detectarSwatches(c)", cabecera)
            nuevos_m = page.evaluate("([c, m]) => window.__clon.detectarModales(c, m)", [cabecera, MAX_MODALES])
            extras += [{"fase": "bolitas", "item": x, "pestana": t, "inicial": inicial} for x in nuevos_sw]
            extras += [{"fase": "modales", "item": x, "pestana": t, "inicial": inicial} for x in nuevos_m]
            if nuevos_sw or nuevos_m:
                entrada["contenido_propio"] = {"grupos_color": len(nuevos_sw), "modales": len(nuevos_m)}
            if capdir:
                ambito = page.evaluate("id => window.__clon.grupos[id].ambito", g["id"])
                entrada["captura"] = _foto(page.locator(f'[data-clon-x="{ambito}"]').first, capdir / f"pestanas_{g['id']}_{t['id']}.png", capdir.name)
        except Navego:
            raise
        except Exception as ex:
            entrada["error"] = _err(ex)
        pestanas.append(entrada)
    _ignorar(clicar, page, inicial["id"])
    _ignorar(esperar_calma, page)
    hechas = {p["texto"] for p in pestanas if "tarjetas_visibles" in p}
    for d in tarjetas.values():
        d["siempre_visible"] = set(d["en_pestanas"]) == hechas
    info = {
        "id": g["id"], "tipo": g["tipo"], "etiqueta": g["etiqueta"],
        "filtra_contenido": any(not d["siempre_visible"] for d in tarjetas.values()) or any("panel" in p for p in pestanas),
        **estilos,
        "pestanas": pestanas,
        "tarjetas": list(tarjetas.values()),
    }
    return info, extras


# ---------------------------------------------------------------- 3. bolitas
def firma_sw(s):
    return (s["tarjeta"]["titulo"], tuple(c["nombre"] for c in s["colores"]))


def desbloquear(page, s):
    """Modo configurador: elige la primera opción libre de cada paso anterior hasta que las bolitas se activen."""
    hechos = []
    for p in page.evaluate("id => window.__clon.pasosPrevios(id)", s["id"]):
        if not clicar(page, p["id"]):
            continue
        esperar_calma(page)
        hechos.append(p["texto"])
        estado = page.evaluate("id => window.__clon.estadoBolitas(id)", s["id"])
        if not estado:                               # la web volvió a pintar las bolitas: se buscan de nuevo por nombre
            nombres = {c["nombre"] for c in s["colores"]}
            nuevo = next((x for x in page.evaluate("c => window.__clon.detectarSwatches(c)", True)
                          if {c["nombre"] for c in x["colores"]} == nombres), None)
            if not nuevo:
                break
            s.update({k: nuevo[k] for k in ("id", "tarjeta", "colores", "estilo_activa", "estilo_inactiva")})
            estado = page.evaluate("id => window.__clon.estadoBolitas(id)", s["id"])
        por_id = {e["id"]: e for e in estado}
        for c in s["colores"]:
            if c["id"] in por_id:
                c["deshabilitado"], c["activo"] = por_id[c["id"]]["deshabilitado"], por_id[c["id"]]["activo"]
        if not all(c["deshabilitado"] for c in s["colores"]):
            break
    return hechos


def explorar_swatches(page, s):
    fotos = lambda: page.evaluate("([k, s]) => window.__clon.fotos(k, s)", [s["tarjeta"]["id"], s["id"]])
    desbloqueo = []
    if s["interactivas"] and all(c["deshabilitado"] for c in s["colores"]):
        desbloqueo = desbloquear(page, s)
    antes = {f["id"]: f for f in fotos()}
    inicial = next((c for c in s["colores"] if c["activo"]), None)
    foto_fija = max((f for f in antes.values() if f["visible"]), key=lambda f: f["area"], default=None)
    colores = []
    for c in s["colores"]:
        foto_bolita = c["imagen_bolita"] or (c["fondo"] if c["fondo"].startswith("http") else "")
        hex_ = c["hex"] or (foto_bolita and _hex_por_imagen(page.context, foto_bolita)) or _hex_por_foto(page, c["id"])
        entrada = {"color_nombre": c["nombre"], "color_hex": hex_, "img_url": "", "activo_por_defecto": c["activo"]}
        if c["fondo"] or c["imagen_bolita"]:
            entrada["bolita_imagen"] = c["fondo"] or c["imagen_bolita"]
        if c["deshabilitado"]:
            entrada["deshabilitado"] = True
        if not s["interactivas"] or c["deshabilitado"]:   # indicador decorativo o bloqueada: no se pulsa
            entrada["img_url"] = foto_fija["src"] if foto_fija else ""
            colores.append(entrada)
            continue
        try:
            entrada["metodo"] = clicar(page, c["id"])
            if not entrada["metodo"]:
                entrada["error"] = "no se pudo pulsar"
            else:
                esperar_calma(page, quieto=300, maximo=2000)
                despues = fotos()
                cambiadas = [f for f in despues if f["visible"] and f["area"] > 0
                             and (f["id"] not in antes or antes[f["id"]]["src"] != f["src"] or not antes[f["id"]]["visible"])]
                visibles = [f for f in despues if f["visible"] and f["area"] > 0]
                principal = max(cambiadas or visibles, key=lambda f: f["area"], default=None)
                if principal:
                    entrada["img_url"], entrada["img_alt"] = principal["src"], principal["alt"]
                entrada["cambio_imagen"] = bool(cambiadas)
                if len(cambiadas) > 1:                   # galerías: todas las fotos que cambian con el color
                    entrada["galeria"] = [f["src"] for f in sorted(cambiadas, key=lambda f: -f["area"])][:12]
                antes = {f["id"]: f for f in despues}
        except Navego:
            raise
        except Exception as ex:
            entrada["error"] = _err(ex)
        colores.append(entrada)
    if inicial:
        _ignorar(clicar, page, inicial["id"])
        _ignorar(esperar_calma, page, 300, 2000)
    salida = {"id": s["id"], "producto": s["tarjeta"]["titulo"], "tipo": "selector" if s["interactivas"] else "indicador",
              "conmuta_imagen": any(c.get("cambio_imagen") for c in colores),
              "estilo_activa": s.get("estilo_activa"), "estilo_inactiva": s.get("estilo_inactiva"), "colores": colores}
    if desbloqueo:
        salida["desbloqueado_eligiendo"] = desbloqueo
    if s["interactivas"] and all(c["deshabilitado"] for c in s["colores"]):
        salida["bloqueado"] = "todas las bolitas están deshabilitadas: la web exige elegir antes otra opción"
    return salida


# ---------------------------------------------------------------- 4. modales
def cerrar(page, abierto, disparador):
    for metodo in ("boton", "escape", "disparador"):
        try:
            if metodo == "boton":
                if not abierto.get("cerrar") or not clicar(page, abierto["cerrar"]["id"]):
                    continue
            elif metodo == "escape":
                page.keyboard.press("Escape")
            elif not clicar(page, disparador):
                continue
            esperar_calma(page, quieto=300, maximo=2000)
            if not page.evaluate("id => window.__clon.visible(window.__clon.el(id), false)", abierto["contenedor"]):
                return metodo
        except Navego:
            raise
        except Exception:
            continue
    return None


def explorar_modal(page, m, capdir):
    page.evaluate("id => window.__clon.antesModal(id)", m["id"])
    if not clicar(page, m["id"]):
        raise RuntimeError(f"no se pudo pulsar '{m['nombre'][:60]}'")
    esperar_calma(page)
    abierto = page.evaluate("id => window.__clon.despuesModal(id)", m["id"])
    if not abierto:
        return None                                  # no abrió nada: no es un modal
    salida = {"disparador": {"texto": m["nombre"] or m["texto"], "motivo": m["motivo"], "aria": m["aria"],
                             "estilo_abierto": abierto.get("disparador_abierto")}, "tipo": abierto["tipo"]}
    for k in ("rol", "titulo", "texto", "bloques", "imagenes", "videos", "enlaces", "estilo", "capa"):
        if k in abierto:
            salida[k] = abierto[k]
    if capdir:
        salida["captura"] = _foto(page.locator(f'[data-clon-x="{abierto["dialogo"]}"]').first, capdir / f"modal_{m['id']}.png", capdir.name)
    cierre = cerrar(page, abierto, m["id"])
    boton = abierto["cerrar"] or {}
    salida["cerrar"] = {"boton": boton.get("nombre", ""), "es_el_disparador": boton.get("es_el_disparador", False),
                        "estilo": boton.get("estilo"), "metodo_cierre": cierre}
    if not cierre:
        raise NoCerro(json.dumps(salida, ensure_ascii=False))
    return salida


# ---------------------------------------------------------------- 5. hover
def _hover_cdp(page, cid, foto=None):
    """:hover forzado desde las herramientas de desarrollo (CDP), sin ratón: vale aunque un canvas 3D o una barra fija
    tapen el elemento. Devuelve los estilos con el :hover puesto (y hace la foto si se pide); lo quita al acabar."""
    cdp = page.context.new_cdp_session(page)
    try:
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        raiz = cdp.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        nodo = cdp.send("DOM.querySelector", {"nodeId": raiz, "selector": f'[data-clon-x="{cid}"]'})["nodeId"]
        if not nodo:
            return None
        cdp.send("CSS.forcePseudoState", {"nodeId": nodo, "forcedPseudoClasses": ["hover"]})
        page.wait_for_timeout(60)
        _ignorar(page.evaluate, JS_ANIMACIONES, [cid, 1500])
        despues = page.evaluate("id => window.__clon.estilosHover(id)", cid)
        if foto:
            _ignorar(lambda: page.locator(f'[data-clon-x="{cid}"]').first.screenshot(path=str(foto), timeout=3000))
        cdp.send("CSS.forcePseudoState", {"nodeId": nodo, "forcedPseudoClasses": []})
        return despues
    except Exception:
        return None
    finally:
        _ignorar(cdp.detach)


def _diferencias(antes, despues):
    cambios = {}
    for i, (a, b) in enumerate(zip(antes, despues or [])):
        d = {p: [a[p], b[p]] for p in a if p != "nodo" and a[p] != b[p]}
        if d:
            cambios[f"{i}:{a['nodo']}"] = d
    return cambios


def explorar_hover(page, h, capdir=None):
    """Ratón real; si no llega o no cambia nada, :hover forzado por CDP. Foto antes/después si hay cambios."""
    antes = page.evaluate("id => window.__clon.estilosHover(id)", h["id"])
    if not antes:
        return None
    loc = page.locator(f'[data-clon-x="{h["id"]}"]').first
    _ignorar(lambda: loc.scroll_into_view_if_needed(timeout=2000))
    foto_antes = capdir / f"hover_{h['id']}_antes.png" if capdir else None
    if foto_antes:
        _ignorar(lambda: loc.screenshot(path=str(foto_antes), timeout=3000))
    cambios, forzado = {}, False
    try:
        try:
            loc.hover(timeout=1500)
        except Exception:                            # tapado por una barra fija o animándose: ratón al centro igualmente
            loc.hover(timeout=1500, force=True)
        page.wait_for_timeout(60)
        _ignorar(page.evaluate, JS_ANIMACIONES, [h["id"], 1500])
        cambios = _diferencias(antes, page.evaluate("id => window.__clon.estilosHover(id)", h["id"]))
    except Exception:
        pass
    foto_despues = capdir / f"hover_{h['id']}_despues.png" if capdir else None
    if cambios and foto_despues:
        _ignorar(lambda: loc.screenshot(path=str(foto_despues), timeout=3000))
    page.mouse.move(1, 1)
    page.wait_for_timeout(120)
    if not cambios:                                  # el ratón no llegó (canvas encima, scroll virtual...): CDP
        cambios = _diferencias(antes, _hover_cdp(page, h["id"], foto_despues))
        forzado = bool(cambios)
    if not cambios:
        for f in filter(None, (foto_antes, foto_despues)):
            _ignorar(f.unlink)
        return None
    info = {"elemento": h["firma"], "texto": h["texto"], "cursor": h["cursor"], "transicion": h["transicion"],
            "forzado": forzado, "cambios": cambios}
    if foto_antes and foto_antes.exists() and foto_despues and foto_despues.exists():
        info["capturas"] = [f"{capdir.name}/{foto_antes.name}", f"{capdir.name}/{foto_despues.name}"]
    return info


def resumen_md(res, max_hover=8):
    """Resumen corto para informe_pc.md (lo detallado está en interactividad.json)."""
    r, L = res["resumen"], []
    L.append(f"- {r['videos']} vídeos, {r['canvas']} canvas, {r['iframes']} iframes · {r['grupos_pestanas']} grupos de pestañas · "
             f"{r['grupos_colores']} grupos de color · {r['modales']} modales/desplegables · {r['hover']} hover · {r['errores']} errores")
    hovers = [(k, h) for k, s in res["secciones"].items() for h in s["hover"]]
    for k, h in hovers[:max_hover]:
        cambios = "; ".join(f"{p}: {str(a)[:28]} → {str(b)[:28]}" for d in h["cambios"].values() for p, (a, b) in d.items())
        L.append(f"- hover sec {k} \"{h['texto'][:25]}\"{' (forzado)' if h['forzado'] else ''}: {cambios[:160]}")
    return L


# ---------------------------------------------------------------- principal
def explorar(url, capturas=True, cabecera=False, visible=False, movil=False, hover=True, carpeta_salida=None):
    """carpeta_salida: la de analizar.py (workspace/<web>); si no se da, se calcula a partir de la URL."""
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    sufijo = "_movil" if movil else ""
    cabecera = cabecera or movil                     # en móvil el menú hamburguesa ES la interacción principal
    hover = hover and not movil
    out_dir = Path(carpeta_salida) if carpeta_salida else SALIDA / nombre_web(url)
    spec_path = out_dir / "referencia" / "spec.json"
    secs_spec = json.loads(spec_path.read_text(encoding="utf-8"))["secciones"] if spec_path.exists() else None
    out_dir.mkdir(parents=True, exist_ok=True)
    medir = out_dir / f"medios_dinamicos{sufijo}"
    medir.mkdir(exist_ok=True)
    capdir = (out_dir / f"capturas_dinamicas{sufijo}") if capturas else None
    for carpeta in filter(None, (medir, capdir)):
        carpeta.mkdir(exist_ok=True)
        for viejo in carpeta.glob("*.*"):
            viejo.unlink()
    secciones, errores, medios_red = {}, [], []

    def bloque(sec):
        return secciones.setdefault(str(sec) if sec else "sin_seccion",
                                    {"pestanas": [], "variantes_color": [], "modales": [], "hover": [],
                                     "medios": {"videos": [], "canvas": [], "iframes": []}})

    with sync_playwright() as pw:
        # Chrome/Edge reales traen H.264/AAC (el Chromium de Playwright no: los .mp4 de casi todas las webs no se ven)
        nav, navegador = None, ""
        for canal in ("chrome", "msedge", None):
            try:
                nav = pw.chromium.launch(args=NAV_ARGS, headless=not visible, **({"channel": canal} if canal else {}))
                navegador = canal or "chromium"
                break
            except Exception:
                continue
        if movil:
            ctx = nav.new_context(**opciones_movil(pw))          # el mismo iPhone 14 Pro que extraer.py
        else:
            ctx = nav.new_context(viewport={"width": ESCRITORIO[0], "height": ESCRITORIO[1]}, locale=LOCALE)
        ctx.add_init_script(JS_ANTES_DE_CARGAR)
        page = ctx.new_page()
        ctx.on("page", lambda p: p.opener() and _ignorar(p.close))   # target=_blank abiertos por la web: fuera
        page.on("dialog", lambda d: _ignorar(d.dismiss))
        page.on("response", _oir_medios(medios_red))
        page.set_default_timeout(8000)

        def recargar(motivo):
            errores.append(motivo)
            print(f"    ! {motivo[:120]} -> recargo la página")
            preparar(page, url, cabecera, secs_spec, movil)

        def en_pestana(ex, fn):
            """Ejecuta fn con la pestaña de la que depende el elemento (si depende de una) y la deja como estaba."""
            if not ex:
                return fn()
            if not clicar(page, ex["pestana"]["id"]):
                raise RuntimeError(f"no se pudo abrir la pestaña '{ex['pestana']['texto']}'")
            esperar_calma(page)
            item = ex["item"]
            if not page.evaluate("id => !!window.__clon.el(id)", item["id"]):
                # la web volvió a pintar la pestaña (o se recargó): se busca otra vez el mismo elemento por su contenido
                if ex["fase"] == "bolitas":
                    nuevo = next((x for x in page.evaluate("c => window.__clon.detectarSwatches(c)", cabecera) if firma_sw(x) == firma_sw(item)), None)
                else:
                    nuevo = next((x for x in page.evaluate("([c, m]) => window.__clon.detectarModales(c, m)", [cabecera, MAX_MODALES])
                                  if x["nombre"] == item["nombre"]), None)
                if not nuevo:
                    raise RuntimeError("el elemento ya no existe tras volver a la pestaña")
                item.clear()
                item.update(nuevo)
            try:
                return fn()
            finally:
                if ex["pestana"]["id"] != ex["inicial"]["id"]:
                    _ignorar(clicar, page, ex["inicial"]["id"])
                    _ignorar(esperar_calma, page)

        try:
            print(f"  abriendo {url} ({'móvil' if movil else 'escritorio'}, {navegador}) ...")
            det = preparar(page, url, cabecera, secs_spec, movil)
            if secs_spec:
                print(f"  secciones renumeradas contra spec.json: {det['remapeadas']} de {len(secs_spec)}")
            med = det["medios"]
            print(f"  detectado: {len(med['videos'])} vídeos, {len(med['canvas'])} canvas, {len(med['iframes'])} iframes, "
                  f"{len(det['tabs'])} grupos de pestañas, {len(det['swatches'])} grupos de bolitas, {len(det['modales'])} posibles modales")

            print("  1/5 medios")
            try:
                explorar_medios(page, med, medir, medios_red)
                for tipo in ("videos", "canvas", "iframes"):
                    for x in med[tipo]:
                        bloque(x["sec"])["medios"][tipo].append(x)
                for v in med["videos"]:
                    print(f"    [{v['sec']}] vídeo {v['ancho']}x{v['alto']} {'blob/streaming' if v['es_blob'] else v['src'][-50:]}"
                          f"{' (fondo)' if v['de_fondo'] else ''}{' animado' if v['animado'] else ''}")
                for c in med["canvas"]:
                    print(f"    [{c['sec']}] canvas {c['contexto']} {c['ancho']}x{c['alto']}{' animado' if c['animado'] else ''}"
                          f"{'' if c['imagen_real'] else ' (sin toDataURL)'}")
                for f in med["iframes"]:
                    print(f"    [{f['sec']}] iframe {f['tipo']} {f['ancho']}x{f['alto']} {f['src'][:60]}")
            except Exception as ex:
                errores.append(f"medios: {_err(ex)}")

            print("  2/5 pestañas y filtros")
            extras = []
            for g in det["tabs"]:
                try:
                    info, ext = explorar_tabs(page, g, capdir, cabecera)
                    extras += ext
                    bloque(g["sec"])["pestanas"].append(info)
                    print(f"    [{g['sec']}] {' | '.join(t['texto'] for t in g['tabs'])}  (filtra: {info['filtra_contenido']}"
                          f"{f', {len(ext)} elementos propios' if ext else ''})")
                except Navego as ex:
                    recargar(f"pestañas {g['id']}: cambió de página a {ex}")
                except Exception as ex:
                    errores.append(f"pestañas {g['id']}: {_err(ex)}")

            # Apple y compañía pintan una copia de las tarjetas por pestaña: lo ya visto (mismo contenido) no se repite
            vistos_sw = {firma_sw(s) for s in det["swatches"]}
            vistos_m = {m["nombre"] for m in det["modales"]}
            propios = []
            for e in extras:
                firma = firma_sw(e["item"]) if e["fase"] == "bolitas" else e["item"]["nombre"]
                visto = vistos_sw if e["fase"] == "bolitas" else vistos_m
                if firma not in visto:
                    visto.add(firma)
                    propios.append(e)
            extras = propios

            print("  3/5 bolitas de color")
            for s, ex_ in [(s, None) for s in det["swatches"]] + [(e["item"], e) for e in extras if e["fase"] == "bolitas"]:
                try:
                    info = en_pestana(ex_, lambda: explorar_swatches(page, s))
                    if ex_:
                        info["solo_en_pestana"] = ex_["pestana"]["texto"]
                    bloque(s["sec"])["variantes_color"].append(info)
                    estado = " BLOQUEADO" if "bloqueado" in info else (f" desbloqueado con: {', '.join(info['desbloqueado_eligiendo'])}" if "desbloqueado_eligiendo" in info else "")
                    print(f"    [{s['sec']}] {info['producto'][:40]} ({info['tipo']}{estado}): "
                          f"{', '.join(c['color_nombre'] + ' ' + (c['color_hex'] or '?') for c in info['colores'])}"
                          f"{'  -> conmuta foto' if info['conmuta_imagen'] else ''}")
                except Navego as ex:
                    recargar(f"bolitas {s['id']}: cambió de página a {ex}")
                except Exception as ex:
                    errores.append(f"bolitas {s['id']}: {_err(ex)}")

            print("  4/5 modales, desplegables y menús")
            for m, ex_ in [(m, None) for m in det["modales"]] + [(e["item"], e) for e in extras if e["fase"] == "modales"]:
                try:
                    info = en_pestana(ex_, lambda: explorar_modal(page, m, capdir))
                    if info:
                        if ex_:
                            info["solo_en_pestana"] = ex_["pestana"]["texto"]
                        bloque(m["sec"])["modales"].append(info)
                        print(f"    [{m['sec']}] {info['tipo']}: {(info.get('titulo') or m['nombre'])[:60]}")
                except Navego as ex:
                    recargar(f"modal {m['id']} ({m['nombre'][:40]}): cambió de página a {ex}")
                except NoCerro as ex:
                    bloque(m["sec"])["modales"].append(json.loads(str(ex)))
                    recargar(f"modal {m['id']} ({m['nombre'][:40]}): no se pudo cerrar")
                except Exception as ex:
                    errores.append(f"modal {m['id']}: {_err(ex)}")
                    _ignorar(page.keyboard.press, "Escape")

            if hover:
                print("  5/5 hover")
                n = 0
                for h in page.evaluate("([c, m]) => window.__clon.detectarHover(c, m)", [cabecera, MAX_HOVER]):
                    try:
                        info = explorar_hover(page, h, capdir)
                        if info:
                            bloque(h["sec"])["hover"].append(info)
                            n += 1
                    except Exception as ex:
                        errores.append(f"hover {h['id']} ({h['texto'][:30]}): {_err(ex)}")
                print(f"    {n} tipos de elemento cambian al pasar el ratón")
        finally:
            ctx.close()
            nav.close()

    orden = sorted(secciones, key=lambda k: (k == "sin_seccion", int(k) if k.isdigit() else 0))
    total = lambda f: sum(f(secciones[k]) for k in orden)
    resultado = {
        "url": url,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "dispositivo": "movil" if movil else "escritorio",
        "navegador": navegador,
        "viewport": {"ancho": (MOVIL if movil else ESCRITORIO)[0], "alto": (MOVIL if movil else ESCRITORIO)[1]},
        "selector_seccion": '[data-clon-sec="N"]',
        "resumen": {
            "videos": total(lambda s: len(s["medios"]["videos"])),
            "canvas": total(lambda s: len(s["medios"]["canvas"])),
            "iframes": total(lambda s: len(s["medios"]["iframes"])),
            "grupos_pestanas": total(lambda s: len(s["pestanas"])),
            "grupos_colores": total(lambda s: len(s["variantes_color"])),
            "modales": total(lambda s: len(s["modales"])),
            "hover": total(lambda s: len(s["hover"])),
            "errores": len(errores),
            "segundos": round(time.time() - t0, 1),
        },
        "secciones": {k: secciones[k] for k in orden},
        "medios_red": medios_red,
        "errores": errores,
    }
    resultado["numeracion"] = ("la del spec.json del análisis (renumerada por textos y posición)" if secs_spec
                               else "propia de esta carga: sin spec.json al lado, puede no coincidir con el análisis")
    ruta = out_dir / f"interactividad{sufijo}.json"
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    r = resultado["resumen"]
    print(f"\nListo en {r['segundos']}s: {r['videos']} vídeos, {r['canvas']} canvas, {r['iframes']} iframes, {r['grupos_pestanas']} pestañas, "
          f"{r['grupos_colores']} grupos de color, {r['modales']} modales, {r['hover']} hover, {r['errores']} errores -> {ruta}")
    return resultado


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else (BASE / "url.txt").read_text(encoding="utf-8").strip().splitlines()[0].strip()
    explorar(url, capturas="--sin-capturas" not in sys.argv, cabecera="--cabecera" in sys.argv, visible="--visible" in sys.argv,
             movil="--movil" in sys.argv, hover="--sin-hover" not in sys.argv)
