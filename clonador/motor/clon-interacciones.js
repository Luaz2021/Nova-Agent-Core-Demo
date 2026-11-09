/* clon-interacciones.js — runtime único de interacciones del clon (Bloque 3).
 *
 * Se escribe UNA vez y no lo toca Qwen. Lee los datos medidos por explorador_dinamico.py (interactividad.json),
 * que puente_interactividad.py mete en <script type="application/json" id="clon-datos">, y da vida a:
 *   - pestañas / filtros  (muestran u ocultan tarjetas, o cambian de panel)
 *   - bolitas de color    (cambian la foto del producto)
 *   - modales y desplegables (su contenido lo dibuja este script: el clon no lo trae)
 *   - hover               (reglas :hover con los cambios medidos)
 *
 * Doble enganche: primero el micro-contrato data-* que puede poner Qwen
 *   data-tab="<grupo>:<i>"   data-color="<grupo>:<i>"   data-modal="<sección>:<i>"
 * y si falta, por TEXTO (o aria-label) dentro de [data-clon-sec="N"]: así funciona también con el clon de crear.py.
 *
 * Al cargar no cambia nada de lo que se ve (las fotos de verificar siguen igual): solo engancha eventos.
 * window.clonInteracciones = { enganchados, fallidos } para comprobarlo desde fuera.
 */
(() => {
  const nodo = document.getElementById('clon-datos');
  if (!nodo) return;
  let datos;
  try { datos = JSON.parse(nodo.textContent); } catch (e) { return; }
  const informe = { enganchados: [], fallidos: [] };
  window.clonInteracciones = informe;
  const ok = (que) => informe.enganchados.push(que);
  const mal = (que) => informe.fallidos.push(que);

  const norm = (t) => (t || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const CLICABLE = 'button, a, label, input, select, summary, [role="tab"], [role="button"], [tabindex]';
  const visible = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };

  // elemento por texto o aria-label: el más interno con ese texto, subido a lo clicable que lo contenga
  const porTexto = (raiz, texto, clicable = true) => {
    const t = norm(texto);
    if (!t) return null;
    let mejor = null;
    for (const e of raiz.querySelectorAll('*')) {
      if (e.closest('#clon-capa')) continue;
      const etiqueta = norm(e.getAttribute('aria-label'));
      if (etiqueta === t) { mejor = e; break; }
      if (norm(e.textContent) === t && (!mejor || mejor.contains(e))) mejor = e;
    }
    if (mejor && clicable) mejor = mejor.closest(CLICABLE) && raiz.contains(mejor.closest(CLICABLE)) ? mejor.closest(CLICABLE) : mejor;
    return mejor;
  };
  // tarjeta de un producto: desde su título, el antepasado más grande que no contiene el título de otra tarjeta
  const tarjeta = (raiz, titulo, otros) => {
    const h = porTexto(raiz, titulo, false);
    if (!h) return null;
    const ajenos = otros.filter(o => norm(o) !== norm(titulo)).map(o => porTexto(raiz, o, false)).filter(Boolean);
    let t = h;
    while (t.parentElement && t.parentElement !== raiz && !ajenos.some(a => t.parentElement.contains(a))) t = t.parentElement;
    return t;
  };
  const marcar = (raiz, sel) => raiz.querySelector(sel);
  const pintar = (e, est) => {
    if (!e || !est) return;
    if (est.color) e.style.color = est.color;
    if (est.fondo) e.style.backgroundColor = est.fondo;
    if (est.borde) e.style.border = est.borde;
  };
  const letra = (e, est) => {
    if (!est) return;
    if (est.fuente) { e.style.font = est.fuente; e.style.fontFamily = 'inherit'; }
    if (est.color) e.style.color = est.color;
    if (est.espaciado && est.espaciado !== 'normal') e.style.letterSpacing = est.espaciado;
  };

  // ------------------------------------------------------------------ pestañas y filtros
  const pestanas = (n, raiz, g) => {
    const lista = g.pestanas || [];
    const botones = lista.map((p, i) => marcar(raiz, `[data-tab="${g.id}:${i}"]`) || porTexto(raiz, p.texto || p.aria_label));
    const titulos = [...new Set(lista.flatMap(p => p.tarjetas_visibles || []))];
    const tarjetas = Object.fromEntries(titulos.map(t => [t, tarjeta(raiz, t, titulos)]));
    // paneles: el que ya esté en el clon (por su texto) o uno dibujado aquí con el texto medido
    const textosPanel = lista.map(p => p.panel && (p.panel.titulo || p.panel.texto)).filter(Boolean);
    const paneles = lista.map((p) => {
      if (!p.panel) return null;
      // el contenedor del panel: desde su texto, hasta donde empieza el de otro panel (no solo el título)
      const t = p.panel.titulo || p.panel.texto;
      const dentro = t && tarjeta(raiz, t, textosPanel);
      if (dentro) return dentro;
      const d = document.createElement('div');
      d.setAttribute('data-clon-panel', g.id);
      d.style.display = 'none';
      const parrafo = document.createElement('p'); parrafo.textContent = p.panel.texto || p.panel.titulo || '';
      d.appendChild(parrafo);
      const ancla = botones.find(Boolean);
      if (ancla) (ancla.closest('[role="tablist"]') || ancla.parentElement).after(d);
      return d;
    });
    const activar = (i) => {
      botones.forEach((b, j) => { if (!b) return; pintar(b, j === i ? g.estilo_activa : g.estilo_inactiva); b.setAttribute('aria-selected', j === i ? 'true' : 'false'); });
      if (g.filtra_contenido && titulos.length) {
        const ver = new Set(lista[i].tarjetas_visibles || []);
        for (const t of titulos) if (tarjetas[t]) tarjetas[t].style.display = ver.has(t) ? '' : 'none';
      }
      paneles.forEach((p, j) => {
        if (!p) return;
        p.style.display = j === i ? '' : 'none';
        // los paneles ocultos de la original vienen con display:none en su clase: se enseñan a la fuerza
        if (j === i && getComputedStyle(p).display === 'none') p.style.display = 'block';
      });
    };
    botones.forEach((b, i) => {
      if (!b) { mal(`sec ${n} pestaña "${lista[i].texto}"`); return; }
      b.style.cursor = 'pointer';
      b.addEventListener('click', (ev) => { ev.preventDefault(); activar(i); });
      ok(`sec ${n} pestaña "${lista[i].texto}"`);
    });
    // el panel activo por defecto ya se ve (si estaba en el clon); los dibujados aquí empiezan ocultos salvo el activo
    const ini = Math.max(0, lista.findIndex(p => p.activa_por_defecto));
    paneles.forEach((p, j) => { if (p && p.hasAttribute('data-clon-panel')) p.style.display = j === ini ? '' : 'none'; });
  };

  // ------------------------------------------------------------------ bolitas de color
  const colores = (n, raiz, g, productos) => {
    const lista = g.colores || [];
    const bolitas = lista.map((c, i) => marcar(raiz, `[data-color="${g.id}:${i}"]`) || porTexto(raiz, c.color_nombre));
    // la tarjeta del producto llega hasta donde empieza la de otro producto de la sección (si no, cogería toda la rejilla)
    const caja = g.producto ? tarjeta(raiz, g.producto, productos) : null;
    const alt = (lista.find(c => c.img_alt) || {}).img_alt;
    const foto = (caja && caja.querySelector('img')) || (alt && [...raiz.querySelectorAll('img')].find(im => norm(im.alt) === norm(alt))) || null;
    bolitas.forEach((b, i) => {
      if (!b) { mal(`sec ${n} color "${lista[i].color_nombre}"`); return; }
      const c = lista[i];
      const pulsar = (ev) => {
        ev.preventDefault();
        bolitas.forEach((o, j) => { const est = j === i ? g.estilo_activa : g.estilo_inactiva; if (o && est && est.borde) o.style.border = est.borde; });
        if (foto && c.img_url && g.conmuta_imagen !== false) {
          const pic = foto.closest('picture');
          if (pic) pic.querySelectorAll('source').forEach(s => s.remove());
          foto.removeAttribute('srcset');
          foto.src = c.img_url;
        }
      };
      (b.tagName === 'INPUT' && b.parentElement ? b.parentElement : b).addEventListener('click', pulsar);
      b.style.cursor = 'pointer';
      ok(`sec ${n} color "${c.color_nombre}"`);
    });
  };

  // ------------------------------------------------------------------ modales y desplegables
  const bloquesHTML = (m, dentro) => {
    for (const b of m.bloques || []) {
      const e = document.createElement(/^(h[1-6]|p|li|span|strong)$/.test(b.tag) ? b.tag : 'p');
      e.textContent = b.texto; e.style.margin = '0 0 12px'; letra(e, b.estilo); dentro.appendChild(e);
    }
    for (const im of m.imagenes || []) {
      const e = document.createElement('img'); e.src = im.src || im.url || ''; e.alt = im.alt || '';
      e.style.maxWidth = '100%'; dentro.appendChild(e);
    }
    for (const a of m.enlaces || []) {
      const e = document.createElement('a'); e.textContent = a.texto; e.href = '#'; e.style.color = 'inherit';
      e.style.display = 'inline-block'; e.style.marginTop = '8px'; dentro.appendChild(e);
    }
  };
  const abrirModal = (m) => {
    cerrarModal();
    const capa = document.createElement('div');
    capa.id = 'clon-capa';
    const c = m.capa || {};
    capa.style.cssText = `position:fixed;inset:0;z-index:${parseInt(c.z) || 1000};background:${c.fondo || 'rgba(0,0,0,.5)'};` +
      'display:flex;align-items:center;justify-content:center;padding:24px;box-sizing:border-box';
    if (c.desenfoque && c.desenfoque !== 'none') capa.style.backdropFilter = c.desenfoque;
    const caja = document.createElement('div');
    const e = m.estilo || {};
    caja.setAttribute('role', 'dialog'); caja.setAttribute('aria-modal', 'true');
    caja.style.cssText = `position:relative;max-height:90vh;overflow:auto;box-sizing:border-box;width:${e.ancho ? e.ancho + 'px' : 'auto'};max-width:100%;` +
      `background:${e.fondo || '#fff'};border-radius:${e.radio || '0'};padding:${e.padding || '32px'};color:${e.color || 'inherit'};box-shadow:${e.sombra || 'none'}`;
    const x = document.createElement('button');
    x.type = 'button'; x.setAttribute('aria-label', 'Cerrar'); x.textContent = '✕';
    x.style.cssText = 'position:absolute;top:16px;right:16px;border:0;background:transparent;font-size:20px;cursor:pointer;color:inherit';
    pintar(x, (m.cerrar || {}).estilo && { color: m.cerrar.estilo.color });
    x.addEventListener('click', cerrarModal);
    caja.appendChild(x);
    bloquesHTML(m, caja);
    capa.appendChild(caja);
    capa.addEventListener('click', (ev) => { if (ev.target === capa) cerrarModal(); });
    document.body.appendChild(capa);
  };
  const cerrarModal = () => { const c = document.getElementById('clon-capa'); if (c) c.remove(); };
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') cerrarModal(); });

  const modales = (n, raiz, lista) => {
    lista.forEach((m, i) => {
      const d = marcar(raiz, `[data-modal="${n}:${i}"]`) || porTexto(raiz, (m.disparador || {}).texto);
      const nombre = `sec ${n} ${m.tipo || 'modal'} "${(m.disparador || {}).texto || m.titulo}"`;
      if (!d) { mal(nombre); return; }
      d.style.cursor = 'pointer';
      if (m.tipo === 'desplegable') {
        const panel = document.createElement('div');
        panel.setAttribute('data-clon-desplegable', `${n}:${i}`);
        panel.style.display = 'none'; panel.style.marginTop = '8px';
        bloquesHTML(m, panel);
        d.after(panel);
        d.setAttribute('aria-expanded', 'false');
        d.addEventListener('click', (ev) => { ev.preventDefault(); const abre = panel.style.display === 'none';
          panel.style.display = abre ? '' : 'none'; d.setAttribute('aria-expanded', abre ? 'true' : 'false'); });
      } else {
        d.addEventListener('click', (ev) => { ev.preventDefault(); abrirModal(m); });
      }
      ok(nombre);
    });
  };

  // ------------------------------------------------------------------ hover
  const reglas = [];
  const kebab = (p) => p.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase());
  const hover = (n, raiz, lista) => {
    lista.forEach((h, i) => {
      const propio = Object.entries(h.cambios || {}).find(([k]) => k.endsWith(':self'));
      if (!propio) return;
      const tag = (h.elemento || '').split('|')[0].toLowerCase();
      // sin espacios: el texto medido junta el de los hijos con espacios que el clon no siempre tiene ("pedidos. +")
      const junto = (x) => norm(x).replace(/ /g, '');
      const t = junto(h.texto);
      let e = null;
      for (const c of raiz.querySelectorAll(tag || '*')) if (junto(c.textContent) === t || junto(c.getAttribute('aria-label')) === t) { e = c; break; }
      // el explorador recorta el texto a 60 letras: se busca por el principio y, de los que empiezan igual (el
      // envoltorio, la tarjeta, el párrafo...), el más interno que parezca tarjeta (fondo o esquinas redondeadas)
      if (!e && (h.texto || '').length >= 55) {
        const cands = [...raiz.querySelectorAll(tag || '*')].filter(c => junto(c.textContent).startsWith(t));
        const tarjetaDe = (c) => { const s = getComputedStyle(c); return parseFloat(s.borderTopLeftRadius) > 0 || (s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent'); };
        const internos = cands.filter(c => !cands.some(o => o !== c && c.contains(o) && tarjetaDe(o)));
        e = internos.find(tarjetaDe) || cands[cands.length - 1] || null;
      }
      if (!e) e = porTexto(raiz, h.texto);
      if (!e) { mal(`sec ${n} hover "${(h.texto || '').slice(0, 30)}"`); return; }
      const id = `${n}-${i}`;
      e.setAttribute('data-clon-hover', id);
      const decl = Object.entries(propio[1]).map(([p, v]) => `${kebab(p)}:${v[1]} !important`).join(';');
      reglas.push(`[data-clon-hover="${id}"]{transition:${h.transicion && h.transicion !== 'all' ? h.transicion : 'all .25s'}}` +
                  `[data-clon-hover="${id}"]:hover{${decl}}`);
      ok(`sec ${n} hover "${(h.texto || '').slice(0, 30)}"`);
    });
  };

  // ------------------------------------------------------------------ arranque
  for (const [n, s] of Object.entries(datos.secciones || {})) {
    const raiz = document.querySelector(`[data-clon-sec="${n}"]`) || document.body;
    for (const g of s.pestanas || []) pestanas(n, raiz, g);
    const productos = [...new Set([...(s.variantes_color || []).map(g => g.producto),
      ...(s.pestanas || []).flatMap(g => g.pestanas.flatMap(p => p.tarjetas_visibles || []))].filter(Boolean))];
    for (const g of s.variantes_color || []) colores(n, raiz, g, productos);
    modales(n, raiz, s.modales || []);
    hover(n, raiz, s.hover || []);
  }
  if (reglas.length) {
    const st = document.createElement('style'); st.id = 'clon-hover'; st.textContent = reglas.join('\n');
    document.head.appendChild(st);
  }
})();
