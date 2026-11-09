import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
CAPTURA COMPLETA (v8): convierte lo que DIBUJA el navegador en un HTML estático casi idéntico.

No mira el código fuente (da igual si la web usa React, Bootstrap, Tailwind, Shopify...):
lee los estilos ya calculados de cada elemento a 1280px y a 375px y los escribe como CSS:
  - estilos de móvil como base y los de escritorio dentro de @media (min-width: 768px)
  - pseudo-elementos ::before/::after (iconos de fuente, adornos)
  - SVG copiados tal cual (incluidos los <symbol> de los sprites)
  - iframes, canvas y vídeos -> captura de imagen de esa zona
  - fuentes: las originales (--fuentes originales) o alternativas de Google Fonts
  - sin scripts, sin rastreadores, sin ventanas emergentes

Resultado: <carpeta>/clon_fiel.html  (+ assets/)
"""
import html as H
import json
import re
from pathlib import Path

from extraer import (ESCRITORIO, MOVIL, LOCALE, CSS_DESPLEGAR, JS_DESPLEGAR, JS_LIMPIAR, JS_SECCIONES, MAX_SECCIONES, NAV_ARGS,
                     fuente_google, marcar_secciones, opciones_movil, preparar_pagina, recargar_medios, remapear)

PROPS = [
    "display", "position", "top", "right", "bottom", "left", "z-index", "float", "clear", "box-sizing",
    "width", "height", "min-width", "min-height", "max-width", "max-height",
    "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding-top", "padding-right", "padding-bottom", "padding-left",
    "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
    "border-top-style", "border-right-style", "border-bottom-style", "border-left-style",
    "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
    "border-top-left-radius", "border-top-right-radius", "border-bottom-right-radius", "border-bottom-left-radius",
    "background-color", "background-image", "background-size", "background-position", "background-repeat",
    # texto con degradado (apple.com «Pantalla PROLED XDR»): sin el recorte al texto sale un bloque de color
    "background-clip", "-webkit-background-clip", "-webkit-text-fill-color",
    "color", "font-family", "font-size", "font-weight", "font-style", "line-height", "letter-spacing",
    "text-align", "text-transform", "text-decoration-line", "text-decoration-color", "white-space", "word-break",
    "text-overflow", "overflow-x", "overflow-y", "opacity", "visibility", "transform", "transform-origin",
    "box-shadow", "text-shadow", "filter", "mix-blend-mode",
    "flex-direction", "flex-wrap", "justify-content", "align-items", "align-content", "align-self",
    "flex-grow", "flex-shrink", "flex-basis", "order", "row-gap", "column-gap",
    "grid-template-columns", "grid-template-rows", "grid-template-areas", "grid-auto-rows", "grid-auto-columns", "justify-self", "grid-column-start", "grid-column-end",
    "grid-row-start", "grid-row-end", "grid-auto-flow", "place-items",
    "object-fit", "object-position", "vertical-align", "list-style-type", "aspect-ratio", "clip-path",
    "fill", "stroke", "cursor",
    "scrollbar-width",          # carruseles: Apple oculta la barra con scrollbar-width:none (si no, sale una barra gris)
]
HEREDADAS = {"color", "font-family", "font-size", "font-weight", "font-style", "line-height", "letter-spacing",
             "text-align", "text-transform", "white-space", "word-break", "visibility", "list-style-type", "cursor",
             "fill", "stroke"}

JS_CAPTURA = r"""
([props, heredadas, vista, inicial]) => {
  const IGNORAR = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'LINK', 'META', 'HEAD', 'TITLE', 'BASE', 'DIALOG']);
  const REEMPLAZADOS = new Set(['IMG', 'SVG', 'VIDEO', 'CANVAS', 'IFRAME', 'INPUT', 'SELECT', 'TEXTAREA', 'PICTURE', 'EMBED', 'OBJECT']);
  const HER = new Set(heredadas);
  // estilos por defecto de cada etiqueta, medidos en un iframe limpio
  let marco = document.getElementById('__clon_marco');
  if (!marco) { marco = document.createElement('iframe'); marco.id = '__clon_marco'; marco.style.cssText = 'position:absolute;left:-9999px;width:800px;height:600px;border:0';
    document.documentElement.appendChild(marco); }
  const dd = marco.contentDocument; const defs = {};
  const defecto = (tag) => { if (defs[tag]) return defs[tag];
    let el; try { el = dd.createElement(tag.toLowerCase().includes('-') ? 'div' : tag); } catch (e) { el = dd.createElement('div'); }
    if (el.tagName === 'A') el.setAttribute('href', '#');      // un <a> con href: así sale el azul y el subrayado del navegador
    dd.body.appendChild(el); const s = dd.defaultView.getComputedStyle(el); const o = {}; for (const p of props) o[p] = s.getPropertyValue(p);
    el.remove(); return (defs[tag] = o); };
  // etiquetas con valor heredable propio del navegador (<small> = smaller, <h1> = 2em, <ul> = disc, <b> = bold...):
  // si la web lo anula y queda igual al del padre, en el clon volvería el del navegador -> se guarda igual.
  // Se averigua midiendo la etiqueta dentro de una sonda con valores heredables raros: lo que no hereda, es propio
  const sonda = dd.createElement('div');
  sonda.style.cssText = 'color:rgb(1,2,3);font-family:zzz;font-size:7px;font-weight:300;font-style:italic;line-height:3px;' +
    'letter-spacing:1px;text-align:right;text-transform:uppercase;white-space:pre;word-break:break-all;list-style-type:square;' +
    'cursor:wait;fill:rgb(1,2,3);stroke:rgb(1,2,3)';
  dd.body.appendChild(sonda);
  const enSonda = {}; { const s = dd.defaultView.getComputedStyle(sonda); for (const p of heredadas) enSonda[p] = s.getPropertyValue(p); }
  const propiasC = {};
  const propias = (tag) => { if (propiasC[tag]) return propiasC[tag];
    let el; try { el = dd.createElement(tag.toLowerCase().includes('-') ? 'div' : tag); } catch (e) { el = dd.createElement('div'); }
    if (el.tagName === 'A') el.setAttribute('href', '#');
    sonda.appendChild(el); const s = dd.defaultView.getComputedStyle(el);
    const set = new Set(heredadas.filter(p => s.getPropertyValue(p) !== enSonda[p]));
    el.remove(); return (propiasC[tag] = set); };
  let contador = inicial;
  const datos = {};           // k -> {estilos, antes, despues, caja}
  const especiales = [];      // iframes / canvas / video -> captura
  const sitiosEsp = [];       // y dónde estaban (cadena de contenedores), por si la web los quita o los cambia
  const revelados = [];       // paneles de pestañas ocultos: se miden enseñándolos un momento y quedan ocultos en el clon
  const visitar = (el, padreEst) => {
    if (IGNORAR.has(el.tagName) || el.id === '__clon_marco') return;
    let k = el.getAttribute('data-k');
    if (!k) { k = 'k' + (contador++); el.setAttribute('data-k', k); }
    let cs = getComputedStyle(el);
    let revelar = null;
    if (cs.display === 'none' && el.hasAttribute('data-clon-revelar')) {
      revelar = { estilo: el.getAttribute('style'), oculto: el.hidden };
      el.hidden = false; el.style.setProperty('display', 'block', 'important');
      cs = getComputedStyle(el);
    }
    const r = el.getBoundingClientRect();
    const est = {};
    if (cs.display === 'none') { est['display'] = 'none'; datos[k] = { e: est }; return; }
    const def = defecto(el.tagName);
    // enlaces, botones y campos traen color/fuente propios del navegador: ahí lo "heredado" se compara con su valor por defecto
    const propioUA = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName);
    for (const p of props) {
      const v = cs.getPropertyValue(p);
      if (HER.has(p) && propioUA) { if (v === def[p] && padreEst && padreEst[p] === v) continue; }
      else if (HER.has(p)) { if (padreEst && padreEst[p] === v && !propias(el.tagName).has(p)) continue; if (!padreEst && v === def[p]) continue; }
      else if (v === def[p]) continue;
      // "aparecer al hacer scroll": un elemento con texto y tamaño que está invisible es una animación a medias -> visible en el clon
      // el relleno del texto solo cuenta si NO es el color normal (degradados: transparente); si no, fijaría el color y
      // anularía los cambios de color al pasar el ratón
      if (p === '-webkit-text-fill-color' && v === cs.color) continue;
      if ((p === 'opacity' && parseFloat(v) < 0.05) || (p === 'visibility' && v === 'hidden')) {
        if ((el.innerText || '').trim() && r.width > 2 && r.height > 2) continue; }
      est[p] = v;
    }
    // ancho y alto: solo cuando importan (si no, el contenido manda y la página sigue siendo fluida)
    const tag = el.tagName.toUpperCase();
    const esRepl = REEMPLAZADOS.has(tag);
    const padre = el.parentElement;
    const anchoPadre = padre ? padre.clientWidth - parseFloat(getComputedStyle(padre).paddingLeft) - parseFloat(getComputedStyle(padre).paddingRight) : innerWidth;
    const ocupaTodo = Math.abs(r.width - anchoPadre) < 2 && !['inline', 'inline-block', 'inline-flex'].includes(cs.display);
    const sinHijos = el.children.length === 0 && !(el.textContent || '').trim();
    const absoluto = cs.position === 'absolute' || cs.position === 'fixed';
    const conFondo = cs.backgroundImage && cs.backgroundImage !== 'none';
    const recorta = (cs.overflowY === 'hidden' || cs.overflowY === 'clip') && el.scrollHeight > el.clientHeight + 2;
    // bloque en flujo normal que está desplazado sin que sus márgenes lo expliquen (la web lo centra con algo que
    // getComputedStyle no enseña): se guarda la posición REAL -> margin auto si está centrado, si no el margen medido
    // También dentro de un flex: en columna (Elementor centra su e-con-inner de 1500px con margin:0 auto y
    // getComputedStyle dice 0px) o en fila con un solo hijo en flujo
    const psP = padre ? getComputedStyle(padre) : null;
    const enFlex = psP && ['flex', 'inline-flex'].includes(psP.display);
    const enFlujo = padre ? [...padre.children].filter(h => { const s = getComputedStyle(h); return s.display !== 'none' && !['absolute', 'fixed'].includes(s.position); }).length : 0;
    const flexCol = enFlex && psP.flexDirection.startsWith('column') && ['normal', 'stretch', 'flex-start', 'start'].includes(psP.alignItems)
      && ['auto', 'normal', 'stretch'].includes(cs.alignSelf);
    const flexFila = enFlex && psP.flexDirection.startsWith('row') && ['normal', 'flex-start', 'start'].includes(psP.justifyContent) && enFlujo === 1;
    const enBloque = cs.display === 'block' && psP && ['block', 'flow-root'].includes(psP.display);
    if (padre && ['static', 'relative'].includes(cs.position) && (enBloque || flexCol || flexFila)) {
      const ps = psP, pr = padre.getBoundingClientRect();
      const ini = pr.left + parseFloat(ps.borderLeftWidth) + parseFloat(ps.paddingLeft);
      const fin = pr.right - parseFloat(ps.borderRightWidth) - parseFloat(ps.paddingRight);
      const izq = r.left - ini - (parseFloat(cs.left) || 0), der = fin - r.right;
      if (izq - parseFloat(cs.marginLeft) > 2 && r.width < fin - ini - 2) {
        if (Math.abs(izq - der) <= 2) { est['margin-left'] = 'auto'; est['margin-right'] = 'auto'; }
        else est['margin-left'] = izq.toFixed(2) + 'px';
      }
    }
    // un div sin ancho se estira solo; un <button>/<input>/<select>/<table> NO (se encoge a su contenido y parte el texto):
    // a esos, si ocupaban todo el padre, width:100% (sigue siendo fluido)
    // ...y tampoco un elemento de una fila flex que no crece solo (flex-grow 0): sin ancho se encoge a su contenido
    // (la barra legal de un pie de WordPress pasa de 1610 a 1066 px y los enlaces se parten)
    const itemFila = enFlex && psP.flexDirection.startsWith('row') && parseFloat(cs.flexGrow) === 0;
    const encoge = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'FIELDSET', 'TABLE'].includes(tag) || itemFila;
    if (ocupaTodo && !esRepl && !absoluto && encoge) est['width'] = '100%';
    else if (ocupaTodo && !esRepl && !absoluto) delete est['width'];
    else if (!esRepl && !absoluto && !sinHijos && cs.display === 'block' && !cs.width.endsWith('px')) delete est['width'];
    // ancho que solo envuelve al contenido (un <span> de enlace mide justo lo que su texto): fijarlo en px es frágil,
    // con la fuente servida por Google el texto mide una décima más y salta de línea. Se prueba con max-content y,
    // si mide lo mismo, el ancho lo vuelve a decidir el contenido
    if (est['width'] && est['width'] !== '100%' && !esRepl && !absoluto && !sinHijos && (el.textContent || '').trim()) {
      const prevW = el.style.getPropertyValue('width'), prioW = el.style.getPropertyPriority('width');
      el.style.setProperty('width', 'max-content', 'important');
      const mc = el.getBoundingClientRect().width;
      if (prevW) el.style.setProperty('width', prevW, prioW); else el.style.removeProperty('width');
      if (Math.abs(mc - r.width) <= 1) delete est['width'];
    }
    if (!(esRepl || sinHijos || absoluto || recorta)) {
      delete est['height'];
      // ¿la altura la decide el contenido o está fijada a mano (banners, heros...)? si sobra espacio, guardar min-height
      const rg = document.createRange(); rg.selectNodeContents(el); const rc = rg.getBoundingClientRect();
      const pv = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) + parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth);
      // si TODOS los hijos van fuera del flujo (absolute/fixed: las tarjetas de Apple) el contenido no da altura,
      // aunque el Range los cuente: la altura la pone la hoja de la web y hay que guardarla como min-height
      const fuera = [...el.children].filter(h => { const p = getComputedStyle(h).position; return p === 'absolute' || p === 'fixed'; }).length;
      const textoSuelto = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
      const contenido = (el.children.length && fuera === el.children.length && !textoSuelto) ? 0 : (rc.height || 0);
      // si lo que "sobra" es justo su propio margen (Elementor: el contenedor mide titular + margin-bottom y el margen
      // vuelve a sumarse fuera) no es una altura fijada: guardarla como min-height lo duplicaría en el clon
      const margenes = parseFloat(cs.marginTop) + parseFloat(cs.marginBottom);
      // el contenido medido con Range incluye texto que desborda la caja del hijo (63 frente a 60): también se mira
      // la caja que ocupan los hijos en flujo
      const enFlujo = [...el.children].map(h => [h, getComputedStyle(h)]).filter(([h, s]) => s.display !== 'none' && s.position !== 'absolute' && s.position !== 'fixed')
        .map(([h]) => h.getBoundingClientRect());
      const cajaHijos = enFlujo.length ? Math.max(...enFlujo.map(q => q.bottom)) - Math.min(...enFlujo.map(q => q.top)) : contenido;
      const esMargen = margenes > 0 && (Math.abs(r.height - pv - contenido - margenes) <= 2 || Math.abs(r.height - pv - cajaHijos - margenes) <= 2);
      if (r.height - pv - contenido > 4 && !esMargen && !['inline'].includes(cs.display)) {
        est['min-height'] = (cs.boxSizing === 'border-box' ? r.height : r.height - pv).toFixed(2) + 'px';
      }
      // altura impuesta que APRIETA el contenido (flex en columna con altura fija: los hijos se encogen y los márgenes
      // no suman): con height:auto crecería. Se prueba de verdad y, si crece, la altura se guarda tal cual
      if (['flex', 'inline-flex', 'grid', 'inline-grid', 'block', 'flow-root'].includes(cs.display)) {
        const prev = el.style.getPropertyValue('height'), prio = el.style.getPropertyPriority('height');
        el.style.setProperty('height', 'auto', 'important');
        const libre = el.getBoundingClientRect().height;
        if (prev) el.style.setProperty('height', prev, prio); else el.style.removeProperty('height');
        if (libre > r.height + 2) {
          est['height'] = (cs.boxSizing === 'border-box' ? r.height : r.height - pv).toFixed(2) + 'px';
          delete est['min-height'];
        }
      }
    }
    if (!est['transform']) delete est['transform-origin'];          // solo importa si hay transformación
    for (const lado of ['top', 'right', 'bottom', 'left'])            // bordes sin estilo: su color/ancho no se ven
      if (cs.getPropertyValue('border-' + lado + '-style') === 'none') { delete est['border-' + lado + '-color']; delete est['border-' + lado + '-width'];
        // ...pero si el navegador le pone borde por defecto (<button>, <input>, <fieldset>), el "none" hay que escribirlo
        if (def['border-' + lado + '-style'] === 'none') delete est['border-' + lado + '-style']; else est['border-' + lado + '-style'] = 'none'; }
    if (cs.getPropertyValue('text-decoration-line') === 'none') delete est['text-decoration-color'];
    if (cs.position === 'fixed') est['position'] = 'absolute';
    if (est['background-image']) est['background-image'] = est['background-image'].replace(/url\("?(?!data:)([^")]+)"?\)/g, (m, u) => 'url("' + new URL(u, document.baseURI).href + '")');
    const d = { e: est, x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) };
    // en PC se guarda además el valor REAL de cada propiedad: si el móvil cambia algo que aquí no se apuntó (por ser el
    // valor por defecto, el del padre o por limpieza), el clon de PC vuelve a este valor exacto y no a uno adivinado
    if (vista === 'escritorio') { const c = {}; for (const p of props) c[p] = cs.getPropertyValue(p); d.c = c; }
    for (const ps of ['::before', '::after']) {
      const p = getComputedStyle(el, ps); const c = p.getPropertyValue('content');
      // con display:none no se pinta (Apple pone el › en ::before y ::after y oculta uno): no se copia
      if (c && c !== 'none' && c !== 'normal' && p.getPropertyValue('display') !== 'none') {
        const o = { content: c };
        for (const q of ['display', 'position', 'top', 'right', 'bottom', 'left', 'width', 'height', 'color', 'background-color', 'background-image',
          'background-size', 'font-family', 'font-size', 'font-weight', 'line-height', 'margin-right', 'margin-left',
          'padding-left', 'padding-right', 'padding-top', 'padding-bottom', 'vertical-align', 'border-top-left-radius',
          'border-top-right-radius', 'border-bottom-left-radius', 'border-bottom-right-radius', 'transform', 'opacity', 'z-index'])
          { const v = p.getPropertyValue(q); const pos0 = ['top', 'right', 'bottom', 'left'].includes(q);
            if (v && v !== 'auto' && v !== 'none' && v !== 'normal' && (pos0 || v !== '0px') && v !== 'rgba(0, 0, 0, 0)') o[q] = v; }
        if (o['background-image']) o['background-image'] = o['background-image'].replace(/url\("?(?!data:)([^")]+)"?\)/g, (m, u) => 'url("' + new URL(u, document.baseURI).href + '")');
        d[ps === '::before' ? 'antes' : 'despues'] = o;
      }
    }
    datos[k] = d;
    if (['IFRAME', 'CANVAS', 'VIDEO', 'EMBED', 'OBJECT'].includes(tag) && r.width > 4 && r.height > 4) {
      especiales.push(k);
      // su sitio, en este mismo instante: hay webs que cambian el vídeo por otro al acabar (apple.com, a los 4 s)
      // o lo quitan en móvil; con la cadena de contenedores se puede reponer en el clon (JS_REPONER_ESPECIALES)
      const cadena = [];
      for (let x = el; x && x !== document.body && x.getAttribute('data-k'); x = x.parentElement) {
        let a = x.previousElementSibling; while (a && !a.getAttribute('data-k')) a = a.previousElementSibling;
        cadena.push({ k: x.getAttribute('data-k'), enLinea: getComputedStyle(x).display.startsWith('inline'), antes: a ? a.getAttribute('data-k') : null });
      }
      sitiosEsp.push({ k, cadena, src: el.currentSrc || el.src || '' });
    }
    if (tag === 'SVG') return;                          // el SVG se copia entero, no hace falta bajar
    const hijos = el.shadowRoot ? [...el.shadowRoot.children] : [...el.children];
    for (const h of hijos) {
      if (h.tagName === 'SLOT') { for (const a of h.assignedElements()) visitar(a, cs); continue; }
      visitar(h, cs);
    }
    if (revelar) {                                      // vuelve a quedar oculto, en la web y en el clon
      if (revelar.estilo === null) el.removeAttribute('style'); else el.setAttribute('style', revelar.estilo);
      el.hidden = revelar.oculto;
      d.e['display'] = 'none'; if (d.c) d.c['display'] = 'none';
      revelados.push(k);
    }
  };
  visitar(document.body, null);
  const altoPag = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
  return { datos, especiales, sitiosEsp, contador, altoPag, revelados };
}
"""

# lo que falte se reconstruye: los contenedores que la web quitó (con su clase: sus estilos de PC) y dentro el mismo
# <picture> que pone JS_SERIALIZAR a un vídeo/canvas/iframe, ya serializado (data-clon-crudo); en móvil queda oculto
# porque esos elementos no tienen estilos de móvil (display:none por defecto)
JS_REPONER_ESPECIALES = r"""
(sitios) => { let n = 0; const vivo = (k) => document.querySelector(`[data-k="${k}"]`);
  for (const s of sitios) {
    if (vivo(s.k)) continue;
    const i = s.cadena.findIndex(c => vivo(c.k));        // el primer antepasado que sigue en la página
    if (i < 1) continue;
    let html = `<picture class="${s.k}"><source media="(min-width: 768px)" srcset="assets/${s.k}_escritorio.png"><img src="assets/${s.k}_movil.png" alt="" style="width:100%;height:100%;object-fit:cover"></picture>`;
    for (const c of s.cadena.slice(1, i)) { const t = c.enLinea ? 'span' : 'div'; html = `<${t} class="${c.k}">${html}</${t}>`; }
    const padre = vivo(s.cadena[i].k), hueco = s.cadena[i - 1];
    const x = document.createElement('span'); x.setAttribute('data-clon-crudo', html);
    const a = hueco.antes ? [...padre.children].find(c => c.getAttribute('data-k') === hueco.antes) : null;
    if (a) a.after(x); else padre.prepend(x);
    n++;
  }
  return n; }
"""

JS_SERIALIZAR = r"""
([ocultos, soloNuevos]) => {
  const OCULTOS = new Set(ocultos || []);   // ocultos en PC y en móvil (menús desplegables, modales...): no se copian
  const VACIOS = new Set(['AREA', 'BASE', 'BR', 'COL', 'EMBED', 'HR', 'IMG', 'INPUT', 'SOURCE', 'TRACK', 'WBR']);
  const IGNORAR = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'LINK', 'META', 'HEAD', 'TITLE', 'BASE', 'DIALOG']);
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const escA = (t) => esc(t).replace(/"/g, '&quot;');
  // document.baseURI y no location.href: en la copia congelada (set_content + <base>) location.href es about:blank
  const abs = (u) => { try { return new URL(u, document.baseURI).href; } catch (e) { return u; } };
  const NATIVAS = new Set(['A', 'ABBR', 'ARTICLE', 'ASIDE', 'B', 'BLOCKQUOTE', 'BUTTON', 'CITE', 'CODE', 'DD', 'DIV', 'DL', 'DT', 'EM', 'FIGCAPTION',
    'FIGURE', 'FOOTER', 'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEADER', 'HR', 'I', 'IMG', 'INPUT', 'LABEL', 'LI', 'MAIN', 'MARK', 'NAV', 'OL', 'OPTION',
    'P', 'PICTURE', 'PRE', 'Q', 'S', 'SECTION', 'SELECT', 'SMALL', 'SOURCE', 'SPAN', 'STRONG', 'SUB', 'SUP', 'TABLE', 'TBODY', 'TD', 'TEXTAREA', 'TFOOT',
    'TH', 'THEAD', 'TR', 'U', 'UL', 'BR', 'DETAILS', 'SUMMARY', 'TIME', 'ADDRESS', 'BODY']);
  const ser = (n) => {
    if (n.nodeType === 3) return esc(n.textContent);
    if (n.nodeType !== 1) return '';
    const el = n, tagU = el.tagName.toUpperCase();
    if (IGNORAR.has(tagU) || el.id === '__clon_marco') return '';
    if (el.hasAttribute('data-clon-crudo')) return el.getAttribute('data-clon-crudo');   // bloque solo-móvil ya serializado
    const k = el.getAttribute('data-k'); if (!k || OCULTOS.has(k)) return '';
    if (tagU === 'SVG') { const c = el.cloneNode(true); c.removeAttribute('data-k'); c.querySelectorAll('[data-k]').forEach(x => x.removeAttribute('data-k'));
      c.setAttribute('class', k); return c.outerHTML; }
    if (['IFRAME', 'CANVAS', 'VIDEO', 'EMBED', 'OBJECT'].includes(tagU))
      return `<picture class="${k}"><source media="(min-width: 768px)" srcset="assets/${k}_escritorio.png"><img src="assets/${k}_movil.png" alt="" style="width:100%;height:100%;object-fit:cover"></picture>`;
    let tag = tagU.toLowerCase();
    if (!NATIVAS.has(tagU)) { const d = getComputedStyle(el).display; tag = (d.startsWith('inline') ? 'span' : 'div'); }
    if (tag === 'body') tag = 'div';
    let at = ` class="${k}"` + (el.getAttribute('data-clon-sec') ? ` data-clon-sec="${el.getAttribute('data-clon-sec')}"` : '');
    if (tagU === 'A') at += ' href="#"';
    if (tagU === 'IMG') at += ` src="${escA(abs(el.currentSrc || el.src || ''))}" alt="${escA(el.alt || '')}"`;
    if (tagU === 'SOURCE' && el.srcset) at += ` srcset="${escA(el.srcset.split(',').map(s => { const p = s.trim().split(/\s+/); p[0] = abs(p[0]); return p.join(' '); }).join(', '))}"` + (el.media ? ` media="${escA(el.media)}"` : '');
    if (tagU === 'INPUT') at += ` type="${escA(el.type || 'text')}" placeholder="${escA(el.placeholder || '')}" aria-label="${escA(el.getAttribute('aria-label') || el.placeholder || el.name || 'campo')}"` + (el.type !== 'password' && el.value && el.type !== 'hidden' ? ` value="${escA(el.value)}"` : '');
    if (tagU === 'BUTTON') at += ' type="button"';
    if (tagU === 'TEXTAREA') at += ` placeholder="${escA(el.placeholder || '')}"`;
    if (el.getAttribute('aria-label') && tagU !== 'INPUT') at += ` aria-label="${escA(el.getAttribute('aria-label'))}"`;
    if (VACIOS.has(tagU)) return `<${tag}${at}>`;
    const hijos = el.shadowRoot ? [...el.shadowRoot.childNodes] : [...el.childNodes];
    let dentro = '';
    for (const h of hijos) {
      if (h.nodeType === 1 && h.tagName === 'SLOT') { for (const a of h.assignedNodes()) dentro += ser(a); continue; }
      dentro += ser(h);
    }
    return `<${tag}${at}>${dentro}</${tag}>`;
  };
  if (soloNuevos) {
    // bloques que la web monta SOLO en móvil (marcas nuevas, k >= límite, colgando de un padre que ya existía en PC):
    // se devuelven serializados con su sitio (padre y hermano anterior de PC) para meterlos en el clon
    // "nuevo" = nodo que no estaba en la página de PC (allí se marcaron todos con data-clon-pc); el número de data-k no
    // sirve: lo que en PC colgaba de algo oculto se quedó sin marca y en móvil la recibe sin ser nuevo
    const viejo = (e) => !!(e && e.hasAttribute && e.hasAttribute('data-clon-pc'));
    const nuevos = [];
    for (const el of document.querySelectorAll('[data-k]')) {
      if (viejo(el) || !viejo(el.parentElement)) continue;
      // solo lo que se VE en móvil (los menús que la web prepara ocultos no entran: saldrían repetidos en el clon)
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1 || (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true }))) continue;
      let prev = el.previousElementSibling;
      while (prev && !(viejo(prev) && prev.hasAttribute('data-k'))) prev = prev.previousElementSibling;
      const html = ser(el);
      if (html) nuevos.push({ padre: el.parentElement.getAttribute('data-k'), antes: prev ? prev.getAttribute('data-k') : null, html });
    }
    return { nuevos };
  }
  // sprites SVG: <symbol>/<defs> sueltos que los <use> necesitan
  const sprites = [...document.querySelectorAll('svg symbol, svg defs')].map(s => s.outerHTML).join('');
  return { cuerpo: ser(document.body), sprites, titulo: document.title, lang: document.documentElement.lang || 'en',
           hojas: [...document.querySelectorAll('link[rel~="stylesheet"]')].map(l => l.href).filter(Boolean),
           estilosInline: [...document.querySelectorAll('style')].map(s => s.textContent).join('\n') };
}
"""


def _css(props):
    return ";".join(f"{p}:{v}" for p, v in props.items())


def construir_css(esc, mov):
    """Reglas: base = móvil; @media (min-width:768px) = lo que cambia en escritorio."""
    base, media, pseudo_b, pseudo_m = [], [], [], []
    for k in sorted(set(esc) | set(mov), key=lambda x: int(x[1:])):
        e, m = esc.get(k, {"e": {"display": "none"}}), mov.get(k, {"e": {"display": "none"}})
        me, ee = dict(m.get("e", {})), dict(e.get("e", {}))
        if me:
            base.append(f".{k}{{{_css(me)}}}")
        dif = {p: v for p, v in ee.items() if me.get(p) != v}
        # propiedades que tenía el móvil y la captura de PC no guardó (por ser iguales al padre, al valor por defecto, o
        # porque se limpiaron: bordes sin estilo, anchos fluidos...): en PC vuelven a su valor REAL medido. Nada de
        # "revert": devuelve el valor de la hoja del navegador (un <button> recupera su borde gris, un h3 su tamaño).
        real = e.get("c", {})
        for p in me:
            if p not in ee:
                if p in ("width", "min-width"):
                    dif[p] = "auto"                   # en PC el ancho lo daba el contenido: que siga siendo fluido
                elif p in ("height", "min-height"):
                    # en PC la altura no se apuntó (la daba la hoja de la web o el contenido): auto, pero con la altura que
                    # medía de verdad como mínimo; si no, un bloque con hijos absolutos (tarjetas de Apple) se queda en 0px
                    dif["height"] = "auto"
                    if "min-height" not in ee and e.get("h"):
                        quita = 0 if real.get("box-sizing") == "border-box" else sum(
                            float(re.sub(r"[^\d.]", "", real.get(x, "0") or "0") or 0)
                            for x in ("padding-top", "padding-bottom", "border-top-width", "border-bottom-width"))
                        dif["min-height"] = f"{max(0, e['h'] - quita):.0f}px"
                elif real.get(p):
                    dif[p] = real[p]
                else:
                    dif[p] = "inherit" if p in HEREDADAS else "revert"
        if dif:
            media.append(f".{k}{{{_css(dif)}}}")
        for lado, clave in (("before", "antes"), ("after", "despues")):
            pm, pe = m.get(clave), e.get(clave)
            if pm:
                pseudo_b.append(f".{k}::{lado}{{{_css(pm)}}}")
            if pe and pe != pm:
                pseudo_m.append(f".{k}::{lado}{{{_css(pe)}}}")
            elif pm and not pe:
                pseudo_m.append(f".{k}::{lado}{{content:none}}")
    return ("\n".join(base + pseudo_b)
            + "\n@media (min-width: 768px){\n" + "\n".join(media + pseudo_m) + "\n}\n")


# @font-face leídos del CSSOM de la página (también los de hojas que el servidor no da por fuera: Apple /wss/fonts)
JS_CARAS = r"""
() => { const out = [];
  const ver = (sh) => { let reglas; try { reglas = sh.cssRules; } catch (e) { return; }
    for (const r of reglas) {
      if (r.type === 3 && r.styleSheet) ver(r.styleSheet);
      if (r.type === 5) out.push(r.cssText.replace(/url\("?(?!data:)([^")]+)"?\)/g, (m, u) => 'url("' + new URL(u, sh.href || document.baseURI).href + '")'));
    } };
  [...document.styleSheets].forEach(ver);
  return out.join('\n'); }
"""


# las fuentes de iconos no se pueden enlazar (el servidor de la web no da permiso CORS a otro origen: el clon no las
# carga): se descargan DESDE la página original, donde sí hay permiso, y van dentro del clon como data:
JS_BAJAR_FUENTES = r"""
async (urls) => { const out = {};
  for (const u of urls) { try { const r = await fetch(u); if (!r.ok) continue;
    const b = new Uint8Array(await r.arrayBuffer()); let s = '';
    for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    out[u] = btoa(s); } catch (e) {} }
  return out; }
"""


def incrustar_fuentes(page, caras):
    """Las reglas @font-face dadas, con su woff2 (o woff) dentro como data: (descargado desde la propia página)."""
    elegidas = {}
    for b in re.findall(r"@font-face\s*{[^}]*}", caras or "", re.I):
        urls = re.findall(r'url\("?([^")]+)"?\)\s*format\("?(woff2|woff)"?\)', b)
        if urls:
            elegidas[b] = sorted(urls, key=lambda x: x[1] != "woff2")[0]
    datos = page.evaluate(JS_BAJAR_FUENTES, sorted({u for u, _ in elegidas.values()})) if elegidas else {}
    out = []
    for b, (u, fmt) in elegidas.items():
        if datos.get(u):
            out.append(re.sub(r"src\s*:[^;}]+;?", f'src: url("data:font/{fmt};base64,{datos[u]}") format("{fmt}");', b, count=1))
    return "\n".join(out)


def fuentes_originales(page, hojas, estilos_inline):
    """Copia las reglas @font-face de las hojas de estilo de la web (con URLs absolutas)."""
    reglas = []
    textos = [(page.url, estilos_inline)]
    # primero las hojas de fuentes (Apple pone las suyas en /wss/fonts?families=..., más allá de la hoja 25)
    for h in sorted(hojas, key=lambda u: 0 if "font" in u.lower() else 1)[:40]:
        try:
            r = page.request.get(h, timeout=15000)
            if r.ok:
                textos.append((h, r.text()))
        except Exception:
            pass
    for base, css in textos:
        for bloque in re.findall(r"@font-face\s*{[^}]*}", css or "", re.I):
            def absoluta(m, base=base):
                u = m.group(2)
                if u.startswith("data:"):
                    return m.group(0)
                from urllib.parse import urljoin
                return f"url({m.group(1)}{urljoin(base, u)}{m.group(1)})"
            reglas.append(re.sub(r"url\((['\"]?)([^'\")]+)\1\)", absoluta, bloque))
    return "\n".join(dict.fromkeys(reglas))


def es_de_iconos(familia):
    """Fuentes de iconos (SF Pro Icons, Font Awesome, Material Icons/Symbols, icomoon...): pintan caracteres privados."""
    f = (familia or "").lower()
    return "icon" in f or "awesome" in f or "material symbols" in f or "glyph" in f


def solo_iconos(css_fuentes):
    """De las reglas @font-face de la web, las de fuentes de iconos."""
    return "\n".join(b for b in re.findall(r"@font-face\s*{[^}]*}", css_fuentes or "", re.I)
                     if es_de_iconos((re.search(r"font-family\s*:\s*([^;]+)", b) or [None, ""])[1].strip().strip("\"'")))


_PESOS_GOOGLE = {}


def familia_google(f):
    """Parámetro family= de Google Fonts que esa familia acepta: si se piden pesos que no tiene, Google responde 400 y
    no carga NINGUNA fuente del enlace. Se prueba de más a menos pesos (una vez por familia)."""
    if f not in _PESOS_GOOGLE:
        import urllib.request
        base = "family=" + f.replace(" ", "+")
        _PESOS_GOOGLE[f] = base
        for opc in (":ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400", ":wght@300;400;500;600;700;800",
                    ":wght@400;500;600;700", ":wght@400;700", ""):
            try:
                with urllib.request.urlopen(urllib.request.Request("https://fonts.googleapis.com/css2?" + base + opc,
                                                                   headers={"User-Agent": "Mozilla/5.0"}), timeout=8) as r:
                    if r.status == 200:
                        _PESOS_GOOGLE[f] = base + opc
                        break
            except Exception:
                continue
    return _PESOS_GOOGLE[f]


def sustituir_fuentes(css):
    """Cambia cada font-family por su alternativa de Google Fonts y devuelve el <link> necesario."""
    usadas = set()

    def cambiar(m):
        primera = m.group(1).split(",")[0].strip().strip("\"'")
        if es_de_iconos(primera):
            return m.group(0)              # los iconos (› de Apple, Font Awesome...) no tienen equivalente: se quedan
        g = fuente_google(primera)
        usadas.add(g)
        return f"font-family:'{g}',sans-serif"
    css = re.sub(r"font-family:([^;}]+)", cambiar, css)
    fam = "&".join(familia_google(f) for f in sorted(usadas))
    link = f'<link href="https://fonts.googleapis.com/css2?{fam}&display=swap" rel="stylesheet">' if usadas else ""
    return css, link


# La fuente gratuita nunca mide igual que la de la marca (Inter Tight es más estrecha que SF Pro en los párrafos y más
# ancha en algunos titulares): los textos se parten en otro sitio. Con la web ORIGINAL abierta se mide cada texto con
# su fuente y con la sustituta (cargada con un nombre propio, sin tocar la web) y la diferencia se reparte entre sus
# letras con letter-spacing: en el clon cada texto ocupa lo mismo que en la original.
JS_FAMILIAS = r"""
() => [...new Set([...document.querySelectorAll('[data-k]')]
  .filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
  .map(e => getComputedStyle(e).fontFamily))]
"""

JS_COMPENSAR = r"""
async ([fuentes, mapa]) => {
  const bytes = (s) => { const t = atob(s), u = new Uint8Array(t.length); for (let i = 0; i < t.length; i++) u[i] = t.charCodeAt(i); return u.buffer; };
  for (const f of fuentes) {
    try { const ff = new FontFace(f.familia, bytes(f.datos), { weight: f.peso, style: f.estilo, unicodeRange: f.rango });
          await ff.load(); document.fonts.add(ff); } catch (e) {}
  }
  const caja = document.createElement('span');
  caja.style.cssText = 'position:absolute;left:-99999px;top:0;white-space:nowrap;visibility:hidden;margin:0;padding:0;border:0';
  document.body.appendChild(caja);
  const COPIAR = ['fontSize', 'fontWeight', 'fontStyle', 'fontStretch', 'letterSpacing', 'wordSpacing', 'textTransform',
    'fontFeatureSettings', 'fontVariationSettings', 'fontKerning', 'fontVariantLigatures', 'fontVariantCaps', 'fontOpticalSizing'];
  const out = {};
  for (const el of document.querySelectorAll('[data-k]')) {
    // solo el texto PROPIO del elemento: los hijos con texto se compensan cada uno con su letra
    const texto = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').replace(/\s+/g, ' ').trim();
    const n = [...texto].length;
    if (n < 2) continue;
    const cs = getComputedStyle(el);
    const alias = mapa[cs.fontFamily];
    if (!alias || cs.display === 'none') continue;
    for (const p of COPIAR) caja.style[p] = cs[p];
    caja.textContent = texto;
    caja.style.fontFamily = cs.fontFamily;
    const wo = caja.getBoundingClientRect().width;
    caja.style.fontFamily = `"${alias}", sans-serif`;
    const ws = caja.getBoundingClientRect().width;
    // medio píxel menos que la original: con encaje exacto (Apple: texto + › = ancho de la caja) el redondeo de
    // subpíxel lo manda a la línea siguiente
    const fs = parseFloat(cs.fontSize) || 16, delta = (wo - ws - 0.5) / n;
    // más de un 15 % de la letra por carácter no es diferencia de fuente (fuente de iconos, texto que no se pinta...)
    if (!wo || !ws || Math.abs(delta) < 0.01 || Math.abs(delta) > fs * 0.15) continue;
    const ls = cs.letterSpacing === 'normal' ? 0 : (parseFloat(cs.letterSpacing) || 0);
    out[el.getAttribute('data-k')] = (ls + delta).toFixed(3) + 'px';
  }
  caja.remove();
  return out;
}
"""
_BINARIOS = {}        # familia de Google -> archivos (latin y latin-ext) en base64, una sola descarga por ejecución


def binarios_google(page, familias):
    import base64
    falta = [f for f in familias if f not in _BINARIOS]
    if falta:
        fam = "&".join(familia_google(f) for f in falta)
        for f in falta:
            _BINARIOS[f] = []
        try:
            css = page.request.get(f"https://fonts.googleapis.com/css2?{fam}&display=swap", timeout=20000).text()
        except Exception:
            css = ""
        bajados = {}
        for bloque in re.findall(r"@font-face\s*{[^}]*}", css):
            def valor(p, b=bloque):
                m = re.search(p + r"\s*:\s*([^;]+);", b)
                return m.group(1).strip() if m else ""
            familia, rango = valor("font-family").strip("'\""), valor("unicode-range")
            url = re.search(r"url\(([^)]+)\)", bloque)
            if familia not in _BINARIOS or not url or ("U+0000-00FF" not in rango and "U+0100" not in rango):
                continue
            if url.group(1) not in bajados:
                try:
                    r = page.request.get(url.group(1), timeout=20000)
                    bajados[url.group(1)] = base64.b64encode(r.body()).decode() if r.ok else None
                except Exception:
                    bajados[url.group(1)] = None
            if bajados[url.group(1)]:
                _BINARIOS[familia].append({"familia": "__clon_" + familia, "peso": valor("font-weight"),
                                           "estilo": valor("font-style"), "rango": rango, "datos": bajados[url.group(1)]})
    return [x for f in familias for x in _BINARIOS.get(f, [])]


def compensar_letras(page):
    """{k: letter-spacing} para que cada texto mida con la fuente sustituta lo mismo que en la página abierta."""
    try:
        mapa = {f: fuente_google(f.split(",")[0].strip().strip("\"'")) for f in page.evaluate(JS_FAMILIAS)
                if not es_de_iconos(f.split(",")[0].strip().strip("\"'"))}
        fuentes = binarios_google(page, sorted(set(mapa.values())))
        if not fuentes:
            return {}
        return page.evaluate(JS_COMPENSAR, [fuentes, {f: "__clon_" + g for f, g in mapa.items()}])
    except Exception as ex:
        print(f"  (compensación de letras: {ex})")
        return {}


def aplicar_compensacion(datos, comp):
    for k, ls in comp.items():
        d = datos.get(k)
        if d and d.get("e", {}).get("display") != "none":
            d["e"]["letter-spacing"] = ls
            if "c" in d:
                d["c"]["letter-spacing"] = ls


# los estilos metidos por JavaScript (insertRule, CSS-in-JS) no salen en page.content(): se pasan a texto
JS_CONGELAR_CSS = r"""
() => { for (const sh of [...document.styleSheets]) { try {
    const n = sh.ownerNode; if (!n || n.tagName !== 'STYLE') continue;
    const reglas = [...sh.cssRules].map(r => r.cssText).join('\n');
    if (reglas.length > (n.textContent || '').length + 20) n.textContent = reglas; } catch (e) {} }
  try { const extra = (document.adoptedStyleSheets || []).map(sh => [...sh.cssRules].map(r => r.cssText).join('\n')).join('\n');
    if (extra) document.head.appendChild(Object.assign(document.createElement('style'), { textContent: extra })); } catch (e) {} }
"""
# los bloques solo-móvil entran en la copia de PC en su sitio, como fragmento ya serializado (data-clon-crudo)
JS_INSERTAR_MOVIL = r"""
(nuevos) => { let n = 0;
  for (const x of nuevos) {
    const p = document.querySelector(`[data-k="${x.padre}"]`); if (!p) continue;
    const h = document.createElement('div'); h.setAttribute('data-clon-crudo', x.html);
    const a = x.antes && [...p.children].find(c => c.getAttribute('data-k') === x.antes);
    if (a) a.after(h); else p.prepend(h);
    n++; }
  return n; }
"""
# paneles de pestañas que la web tiene ocultos (los de las pestañas no activas): JS_CAPTURA los mide igual y se quedan
# en el clon ocultos, para que clon-interacciones.js los enseñe al pulsar su pestaña
JS_MARCAR_PANELES = r"""
() => { let n = 0;
  const marca = (e) => { if (e && !e.hasAttribute('data-clon-revelar') && getComputedStyle(e).display === 'none') { e.setAttribute('data-clon-revelar', ''); n++; } };
  document.querySelectorAll('[role="tabpanel"]').forEach(marca);
  document.querySelectorAll('[role="tab"][aria-controls]').forEach(t => marca(document.getElementById(t.getAttribute('aria-controls'))));
  return n; }
"""
JS_CAJA = "(k) => { const e = document.querySelector(`[data-k='${k}']`); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top + scrollY, r.width, r.height]; }"
# fotograma de un vídeo/canvas tal cual (sin los textos que la web pone encima): se dibuja en un canvas. Si la web cambió
# el elemento por otro (apple.com lo hace al acabar el vídeo), se busca por su dirección. null si el navegador no deja
# leerlo (vídeo de otro dominio sin CORS) o aún no tiene imagen.
JS_FOTOGRAMA = r"""
([k, src]) => { let e = document.querySelector(`[data-k="${k}"]`);
  if (!e && src) e = [...document.querySelectorAll('video')].find(v => (v.currentSrc || v.src) === src);
  if (!e) return null;
  const ancho = e.tagName === 'VIDEO' ? e.videoWidth : e.tagName === 'CANVAS' ? e.width : 0;
  const alto = e.tagName === 'VIDEO' ? e.videoHeight : e.tagName === 'CANVAS' ? e.height : 0;
  if (!ancho || !alto) return null;
  try { const c = document.createElement('canvas'); c.width = ancho; c.height = alto;
        c.getContext('2d').drawImage(e, 0, 0, ancho, alto); return c.toDataURL('image/png'); } catch (x) { return null; } }
"""


# vídeos de la carga móvil REAL: el motor pasa a móvil cambiando el tamaño de la ventana, pero hay webs que solo montan
# su vídeo al cargar en un móvil (apple.com: el iPhone Duo que se despliega). Se carga aparte como iPhone, se espera a que
# acaben y se guarda el fotograma final de cada vídeo visible con su caja en la página.
JS_VIDEOS_VISIBLES = r"""
() => [...document.querySelectorAll('video')].map(v => { const r = v.getBoundingClientRect();
  return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, src: v.currentSrc || v.src || '',
           listo: v.readyState >= 2 && (v.ended || v.loop || v.paused || v.currentTime > 0) }; })
  .filter(v => v.w > 40 && v.h > 40 && v.src)
"""
# en el clon móvil: la foto (<img>, dentro de <picture> o no) que ocupa la caja del vídeo recibe el fotograma SOLO en
# móvil: una <source media="(max-width: 767px)"> primera dentro de su <picture> (el PC no cambia). Ya serializada
# (data-clon-crudo) porque no tiene data-k.
JS_PONER_VIDEOS_MOVIL = r"""
(vids) => { let n = 0;
  const imgs = [...document.querySelectorAll('img[data-k]')].map(i => { const r = i.getBoundingClientRect();
    return { i, x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; }).filter(b => b.w > 40 && b.h > 40);
  for (const v of vids) {
    // la que más se solapa con el vídeo (área común / área del vídeo)
    let mejor = null, mejorS = 0.6;
    for (const b of imgs) {
      const iw = Math.max(0, Math.min(v.x + v.w, b.x + b.w) - Math.max(v.x, b.x));
      const ih = Math.max(0, Math.min(v.y + v.h, b.y + b.h) - Math.max(v.y, b.y));
      const s = (iw * ih) / Math.max(1, Math.max(v.w * v.h, b.w * b.h));
      if (s > mejorS) { mejor = b; mejorS = s; }
    }
    if (!mejor) continue;
    const pic = mejor.i.parentElement && mejor.i.parentElement.tagName === 'PICTURE' ? mejor.i.parentElement : null;
    if (!pic) continue;
    const s = document.createElement('source');
    s.setAttribute('data-clon-crudo', `<source media="(max-width: 767px)" srcset="assets/${v.archivo}">`);
    pic.prepend(s); n++;
  }
  return n; }
"""


def _videos_movil(pw, nav, url, carpeta_assets):
    """Fotograma final de cada vídeo visible al cargar la web COMO MÓVIL (vmov_N.png) y su caja."""
    import base64
    from PIL import Image, ImageStat
    salida = []
    try:
        ctx = nav.new_context(**opciones_movil(pw))
        p = ctx.new_page()
        preparar_pagina(p, url)
        for _ in range(16):                      # hasta 8 s a que los vídeos acaben (o estén en bucle / parados)
            vids = p.evaluate(JS_VIDEOS_VISIBLES)
            if vids and all(v["listo"] for v in vids):
                break
            p.wait_for_timeout(500)
        for n, v in enumerate(p.evaluate(JS_VIDEOS_VISIBLES)):
            # el ÚLTIMO fotograma (el estado final que se queda en pantalla): se lleva el vídeo a la vista (muchas webs solo
            # lo arrancan al verlo) y se salta al final, sin depender de que se reproduzca
            datos = p.evaluate(r"""async (src) => { const e = [...document.querySelectorAll('video')].find(x => (x.currentSrc || x.src) === src);
                if (!e) return null;
                e.scrollIntoView({ block: 'center' });
                for (let i = 0; i < 20 && e.readyState < 2; i++) await new Promise(r => setTimeout(r, 250));
                if (!e.videoWidth) return null;
                if (isFinite(e.duration) && e.duration > 0 && !e.loop) {
                  e.pause();
                  await new Promise(r => { e.addEventListener('seeked', r, { once: true }); e.currentTime = Math.max(0, e.duration - 0.05); setTimeout(r, 3000); });
                }
                try { const c = document.createElement('canvas'); c.width = e.videoWidth; c.height = e.videoHeight;
                      c.getContext('2d').drawImage(e, 0, 0); return c.toDataURL('image/png'); } catch (x) { return null; } }""", v["src"])
            if not datos:
                continue
            destino = Path(carpeta_assets) / f"vmov_{n}.png"
            destino.write_bytes(base64.b64decode(datos.split(",", 1)[1]))
            if max(ImageStat.Stat(Image.open(destino).convert("L")).stddev) > 4:
                salida.append({**v, "archivo": destino.name})
        ctx.close()
    except Exception as ex:
        print(f"  (aviso vídeos móvil: {ex})")
    return salida


def _fotograma(page, k, src, destino):
    """El fotograma limpio de un vídeo/canvas; True si salió una imagen con contenido."""
    import base64
    from PIL import Image, ImageStat
    try:
        datos = page.evaluate(JS_FOTOGRAMA, [k, src])
        if not datos:
            return False
        destino.write_bytes(base64.b64decode(datos.split(",", 1)[1]))
        return max(ImageStat.Stat(Image.open(destino).convert("L")).stddev) > 4
    except Exception:
        return False


def _foto_especial(page, k, destino, ref_img, src=""):
    """Foto de un vídeo/canvas/iframe: primero su fotograma limpio (sin textos encima); si no se puede, foto del
    elemento; y si sale en blanco (el vídeo aún no pintó nada), ese trozo de la captura de la web original."""
    from PIL import Image, ImageStat
    if _fotograma(page, k, src, destino):
        return
    try:
        page.locator(f'[data-k="{k}"]').first.screenshot(path=str(destino), timeout=8000)
        if max(ImageStat.Stat(Image.open(destino).convert("L")).stddev) > 4:
            return
    except Exception:
        pass
    caja = page.evaluate(JS_CAJA, k)
    if not caja or not ref_img or not Path(ref_img).exists():
        return
    x, y, w, h = [int(v) for v in caja]
    img = Image.open(ref_img)
    caja = (max(0, x), max(0, y), min(img.width, x + w), min(img.height, y + h))
    if caja[2] - caja[0] > 4 and caja[3] - caja[1] > 4:            # fuera de pantalla o sin tamaño: se deja como esté
        img.crop(caja).save(destino)


def capturar_web(url, carpeta, fuentes="originales", imagenes="originales", spec=None, ref_dir=None):
    from playwright.sync_api import sync_playwright
    carpeta = Path(carpeta)
    (carpeta / "assets").mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        ctx = nav.new_context(viewport={"width": ESCRITORIO[0], "height": ESCRITORIO[1]}, locale=LOCALE)
        page = ctx.new_page()
        print(f"  captura completa: abriendo {url}")
        preparar_pagina(page, url)
        page_url = page.url
        # mismas secciones que el extractor y con la MISMA numeración: el mismo elemento de PC (ruta del spec) o, si no, cortar y emparejar
        n_secciones = marcar_secciones(page, spec["secciones"]) if spec else page.evaluate(JS_SECCIONES, MAX_SECCIONES)
        page.evaluate(JS_MARCAR_PANELES)
        esc = page.evaluate(JS_CAPTURA, [PROPS, sorted(HEREDADAS), "escritorio", 0])
        comp_pc = compensar_letras(page) if fuentes != "originales" else {}
        page.evaluate("() => document.querySelectorAll('*').forEach(e => e.setAttribute('data-clon-pc', ''))")
        caras_cssom = page.evaluate(JS_CARAS)
        iconos_dentro = incrustar_fuentes(page, solo_iconos(caras_cssom)) if fuentes != "originales" else ""
        # capturas de iframes / canvas / vídeos en escritorio
        ref_esc = Path(ref_dir) / "original_escritorio.png" if ref_dir else None
        ref_mov = Path(ref_dir) / "original_movil.png" if ref_dir else None
        fuentes_esp = {x["k"]: x.get("src", "") for x in esc.get("sitiosEsp", [])}  # dirección de cada vídeo
        for k in esc["especiales"]:
            _foto_especial(page, k, carpeta / "assets" / f"{k}_escritorio.png", ref_esc, fuentes_esp.get(k, ""))
        # dónde estaba cada vídeo/canvas/iframe de PC (lo apunta JS_CAPTURA): hay webs que lo QUITAN del HTML al pasar
        # a móvil (el vídeo del iPhone Duo de apple.com) y el clon se serializa en móvil; sin esto se perdía en PC
        sitios_pc = esc.get("sitiosEsp", [])
        page.evaluate(JS_CONGELAR_CSS)
        foto_pc = page.content()                     # copia congelada de PC (con data-k y data-clon-sec)
        page.set_viewport_size({"width": MOVIL[0], "height": MOVIL[1]})
        recargar_medios(page)
        vivos = page.evaluate("document.querySelectorAll('[data-k]').length")
        # La web puede redibujarse al cambiar de tamaño: entera (React/Vue montan otro árbol en móvil) o SOLO ALGUNOS
        # bloques (Apple cambia la rejilla de tarjetas de PC por un carrusel de móvil). En los dos casos lo que se veía
        # en PC ya no está en la página viva, y copiarla dejaría el clon de PC sin esas tarjetas. Si desaparece algo
        # visible en PC, el móvil se mide sobre la copia congelada de PC, sin JavaScript, con sus mismas hojas de estilo.
        presentes = set(page.evaluate("[...document.querySelectorAll('[data-k]')].map(e => e.getAttribute('data-k'))"))
        visibles_pc = [k for k, v in esc["datos"].items() if v.get("w", 0) > 0 and v.get("h", 0) > 0]
        perdidos = [k for k in visibles_pc if k not in presentes]
        mov_vivo, nuevos = None, []
        if vivos < esc["contador"] * 0.5 or len(perdidos) > max(10, len(visibles_pc) * 0.005):
            print(f"  la web se redibuja al pasar a móvil ({len(perdidos)} elementos visibles en PC desaparecen, "
                  f"{vivos} de {esc['contador']} siguen): medición mixta (página viva + copia de PC)")
            # medición MIXTA: lo que sigue vivo se mide aquí, en la página real (sus estilos de móvil de verdad: la
            # letra de 14px, el pie de 12px...); solo lo que desapareció se mide en la copia congelada de PC
            page.add_style_tag(content=CSS_DESPLEGAR)
            page.evaluate(JS_DESPLEGAR)
            page.evaluate(JS_LIMPIAR)
            page.evaluate(JS_MARCAR_PANELES)
            mov_vivo = page.evaluate(JS_CAPTURA, [PROPS, sorted(HEREDADAS), "movil", esc["contador"]])
            comp_vivo = compensar_letras(page) if fuentes != "originales" else {}
            # lo que la web monta SOLO en móvil (Apple cambia la rejilla de tarjetas de PC por una galería deslizable):
            # se copia tal cual de la página viva, con sus estilos de móvil reales, y en PC se oculta
            nuevos = page.evaluate(JS_SERIALIZAR, [[], True])["nuevos"]
            ctx2 = nav.new_context(viewport={"width": MOVIL[0], "height": MOVIL[1]}, locale=LOCALE)
            page = ctx2.new_page()
            base = f'<base href="{H.escape(page_url)}">'
            quieta = re.sub(r"(?is)<script\b.*?</script>", "", foto_pc)          # sin los scripts de la web: ya no se redibuja
            quieta = re.sub(r"(?i)<head([^>]*)>", lambda m: f"<head{m.group(1)}>{base}", quieta, count=1)
            try:
                page.set_content(quieta, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_load_state("load", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
        page.add_style_tag(content=CSS_DESPLEGAR)
        page.evaluate(JS_DESPLEGAR)
        page.evaluate(JS_LIMPIAR)
        # en la copia congelada, las marcas nuevas siguen donde acabó la página viva (no se pisan con las suyas)
        page.evaluate(JS_MARCAR_PANELES)
        mov = page.evaluate(JS_CAPTURA, [PROPS, sorted(HEREDADAS), "movil", mov_vivo["contador"] if mov_vivo else esc["contador"]])
        comp_movil = compensar_letras(page) if fuentes != "originales" else {}
        if mov_vivo:
            vivos_k = [k for k in mov_vivo["datos"] if k in presentes and k in esc["datos"] and k in mov["datos"]]
            for k in vivos_k:
                mov["datos"][k] = mov_vivo["datos"][k]
                comp_movil.pop(k, None)
                if k in comp_vivo:
                    comp_movil[k] = comp_vivo[k]
            # bloques solo-móvil: sus estilos de la página viva; los de PC que en móvil ya no existen, ocultos en móvil
            solo_movil = {k for x in nuevos for k in re.findall(r'class="(k\d+)"', x["html"])}
            for k in solo_movil:
                if k in mov_vivo["datos"]:
                    mov["datos"][k] = mov_vivo["datos"][k]
                    if k in comp_vivo:
                        comp_movil[k] = comp_vivo[k]
            if nuevos:
                for k in perdidos:
                    mov["datos"][k] = {"e": {"display": "none"}}
                    comp_movil.pop(k, None)
            print(f"  móvil: {len(vivos_k)} elementos medidos en la página viva; {len(nuevos)} bloques solo-móvil "
                  f"({len(solo_movil)} elementos) sustituyen a {len(perdidos)} de PC")
        if comp_pc or comp_movil:
            aplicar_compensacion(esc["datos"], comp_pc)
            aplicar_compensacion(mov["datos"], comp_movil)
            print(f"  fuente sustituta compensada con letter-spacing: {len(comp_pc)} textos en PC, {len(comp_movil)} en móvil")
        for k in set(esc["especiales"]) | set(mov["especiales"]):
            _foto_especial(page, k, carpeta / "assets" / f"{k}_movil.png", ref_mov, fuentes_esp.get(k, ""))
            for v in ("escritorio", "movil"):   # si falta una de las dos, usar la otra
                a, b = carpeta / "assets" / f"{k}_{v}.png", carpeta / "assets" / f"{k}_{'movil' if v == 'escritorio' else 'escritorio'}.png"
                if not a.exists() and b.exists():
                    a.write_bytes(b.read_bytes())
        # los paneles de pestañas ocultos se quedan (ocultos): clon-interacciones.js los enseña con su pestaña
        paneles = set(esc.get("revelados", [])) | set(mov.get("revelados", [])) | set((mov_vivo or {}).get("revelados", []))
        ocultos = [k for k, v in esc["datos"].items() if v.get("e", {}).get("display") == "none" and k not in paneles
                   and mov["datos"].get(k, {"e": {"display": "none"}}).get("e", {}).get("display") == "none"]
        if mov_vivo and nuevos:
            page.evaluate(JS_INSERTAR_MOVIL, nuevos)
        vids = _videos_movil(pw, nav, page_url, carpeta / "assets")
        if vids:
            n_v = page.evaluate(JS_PONER_VIDEOS_MOVIL, vids)
            print(f"  {len(vids)} vídeos de la carga móvil real: {n_v} puestos en el clon móvil (su fotograma final)")
        repuestos = page.evaluate(JS_REPONER_ESPECIALES, sitios_pc)
        if repuestos:
            print(f"  {repuestos} vídeos/canvas/iframes que la web quita en móvil: repuestos en el clon (solo PC)")
        ser = page.evaluate(JS_SERIALIZAR, [ocultos, False])
        print(f"  {len(ocultos)} elementos ocultos en PC y móvil (menús, modales): fuera del clon"
              + (f"; {len(paneles)} paneles de pestañas ocultos se quedan" if paneles else ""))
        css_fuentes = fuentes_originales(page, ser["hojas"], ser["estilosInline"])
        css_fuentes = "\n".join(dict.fromkeys(re.findall(r"@font-face\s*{[^}]*}", css_fuentes + "\n" + caras_cssom, re.I)))
        if fuentes != "originales":
            # con fuentes de Google, de la web solo quedan las de iconos (las incrustadas al final: mandan)
            css_fuentes = solo_iconos(css_fuentes) + "\n" + iconos_dentro
        nav.close()

    css = construir_css(esc["datos"], mov["datos"])
    link_google = ""
    if fuentes != "originales":
        css, link_google = sustituir_fuentes(css)
    cuerpo = ser["cuerpo"]
    if imagenes == "relleno":
        cuerpo = re.sub(r'(<img [^>]*src=")[^"]*(")', r'\1data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22/%3E\2', cuerpo)
        css = re.sub(r'url\("http[^"]*"\)', "none", css)
    html = f"""<!DOCTYPE html>
<html lang="{ser['lang']}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ser['titulo']} (clon de estudio)</title>
{link_google}
<style>
{css_fuentes}
html,body{{margin:0;padding:0;overflow-x:clip}}
img,svg,video{{max-width:none}}
{css}
</style>
</head>
<body>
<svg style="display:none" aria-hidden="true">{ser['sprites']}</svg>
{cuerpo}
</body>
</html>
"""
    ruta = carpeta / "clon_fiel.html"
    ruta.write_text(html, encoding="utf-8")
    (carpeta / "captura_info.json").write_text(json.dumps({"url": url, "elementos": esc["contador"], "alto": esc["altoPag"],
                                                           "especiales": esc["especiales"], "secciones": n_secciones}, indent=1), encoding="utf-8")
    print(f"  clon fiel: {esc['contador']} elementos, {len(html) // 1024} KB -> {ruta.name}")
    return ruta


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python capturar.py URL carpeta_salida [--google] [--relleno]")
        sys.exit(1)
    capturar_web(sys.argv[1], sys.argv[2], "google" if "--google" in sys.argv else "originales",
                 "relleno" if "--relleno" in sys.argv else "originales")
