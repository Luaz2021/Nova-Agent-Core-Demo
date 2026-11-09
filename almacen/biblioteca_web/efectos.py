"""
EFECTOS · kit de movimiento y scroll de Nova (calidad fija, probado; ni Nova ni Qwen escriben animaciones a mano).

Dos tipos:
  A) DECORADORES: atributos que se ponen en el HTML de cualquier seccion y el motor (EFECTOS_JS) los anima:
       data-efecto="titular"   -> el titular sube palabra a palabra al entrar en pantalla
       data-efecto="relleno"   -> un parrafo se va "encendiendo" palabra a palabra con el scroll
       data-efecto="contador"  -> una cifra cuenta desde 0 al aparecer (el numero real va en el texto)
       data-efecto="magnetico" -> un boton sigue un poco al raton
  B) BLOQUES DE SCROLL: secciones completas con datos (sin Qwen), via secciones.json -> {"id", "efecto", "datos"}:
       pasos      -> imagen fija a un lado que cambia mientras avanzan los pasos de texto (scrollytelling)
       mascara    -> una foto se abre desde un circulo al bajar
       zoom       -> una foto empieza muy cerca y se aleja hasta verse entera, con un titular encima
       horizontal -> galeria que se mueve de lado mientras bajas
       apiladas   -> tarjetas que se quedan arriba y la siguiente se apila encima
       video      -> un video que avanza con el scroll (solo con un video REAL que de el usuario o de medios)
  C) FONDO VIVO de la portada (canvas 2D propio, 0 KB de librerias): "malla" (degradado que respira) o "particulas".

Reglas fijas: 1 efecto "espectacular" por pagina (fondo vivo, pasos, zoom, horizontal o video) + 2-3 sutiles.
Todo: prefers-reduced-motion -> estado final estatico; sin JS -> se ve el contenido; canvas en pausa fuera de pantalla
y con resolucion maxima x2; en movil (<760px) los bloques de scroll se convierten en una lista normal.
"""

from __future__ import annotations

import html
import json

ESPECTACULARES = {"pasos", "zoom", "horizontal", "video", "malla", "particulas"}
CATALOGO = {
    "titular": {"tipo": "decorador", "intensidad": "sutil", "uso": 'data-efecto="titular" en el h1 o h2'},
    "relleno": {"tipo": "decorador", "intensidad": "medio", "uso": 'data-efecto="relleno" en un parrafo destacado (1 por pagina)'},
    "contador": {"tipo": "decorador", "intensidad": "sutil", "uso": 'data-efecto="contador" en un elemento con una cifra REAL'},
    "magnetico": {"tipo": "decorador", "intensidad": "sutil", "uso": 'data-efecto="magnetico" en el boton principal'},
    "pasos": {"tipo": "bloque", "intensidad": "espectacular", "datos": {"titulo": "", "pasos": [{"titulo": "", "texto": ""}], "fotos": "1 por paso (de medios)"}},
    "mascara": {"tipo": "bloque", "intensidad": "medio", "datos": {"titulo": "", "texto": "", "foto": "de medios"}},
    "zoom": {"tipo": "bloque", "intensidad": "espectacular", "datos": {"titulo": "", "foto": "de medios"}},
    "horizontal": {"tipo": "bloque", "intensidad": "espectacular", "datos": {"titulo": "", "tarjetas": [{"titulo": "", "texto": "", "foto": "opcional"}]}},
    "apiladas": {"tipo": "bloque", "intensidad": "medio", "datos": {"titulo": "", "tarjetas": [{"titulo": "", "texto": ""}]}},
    "video": {"tipo": "bloque", "intensidad": "espectacular", "datos": {"titulo": "", "video": "URL real .mp4/.webm", "poster": "opcional"}},
    "malla": {"tipo": "fondo", "intensidad": "espectacular", "uso": '"fondo_vivo": "malla" en secciones.json'},
    "particulas": {"tipo": "fondo", "intensidad": "espectacular", "uso": '"fondo_vivo": "particulas" en secciones.json'},
}


def e(x) -> str:
    return html.escape(str(x or ""), quote=True)


def _img(foto: dict, clase: str, cargar: str = "lazy") -> str:
    if not foto:
        return f'<div class="{clase} ef-sinfoto" aria-hidden="true"></div>'
    return (f'<img class="{clase}" src="{e(foto["url"])}" srcset="{e(foto.get("url_movil", foto["url"]))} 800w, {e(foto["url"])} 1600w" '
            f'sizes="(max-width: 760px) 100vw, 60vw" alt="{e(foto.get("alt"))}" loading="{cargar}" decoding="async">')


# ------------------------------------------------------------------------------------------------ bloques
def pasos(sid: str, d: dict, fotos: list[dict]) -> str:
    items = d.get("pasos") or []
    imgs = "".join(_img(fotos[i % len(fotos)] if fotos else {}, "ef-pasos__img" + (" activa" if i == 0 else "")) for i in range(len(items)))
    textos = "".join(f'<li class="ef-pasos__paso"><span class="ef-pasos__n">{i + 1:02d}</span><h3>{e(p.get("titulo"))}</h3>'
                     f'<p>{e(p.get("texto"))}</p></li>' for i, p in enumerate(items))
    return f"""<section id="{sid}" class="seccion ef-pasos" data-bloque="pasos" aria-labelledby="{sid}-t">
  <div class="contenedor"><h2 class="t-head" id="{sid}-t" data-efecto="titular">{e(d.get("titulo"))}</h2></div>
  <div class="contenedor ef-pasos__rejilla">
    <div class="ef-pasos__visor" aria-hidden="true">{imgs}</div>
    <ol class="ef-pasos__lista" role="list">{textos}</ol>
  </div>
</section>"""


def mascara(sid: str, d: dict, fotos: list[dict]) -> str:
    return f"""<section id="{sid}" class="seccion ef-mascara" data-bloque="mascara" aria-labelledby="{sid}-t">
  <div class="contenedor rejilla-2">
    <div><h2 class="t-head" id="{sid}-t" data-efecto="titular">{e(d.get("titulo"))}</h2><p class="t-lead">{e(d.get("texto"))}</p></div>
    <div class="ef-mascara__marco">{_img(fotos[0] if fotos else {}, "ef-mascara__img")}</div>
  </div>
</section>"""


def zoom(sid: str, d: dict, fotos: list[dict]) -> str:
    return f"""<section id="{sid}" class="ef-zoom" data-bloque="zoom" aria-labelledby="{sid}-t">
  <div class="ef-zoom__fijo">
    {_img(fotos[0] if fotos else {}, "ef-zoom__img")}
    <div class="ef-zoom__velo" aria-hidden="true"></div>
    <h2 class="t-display ef-zoom__titulo" id="{sid}-t">{e(d.get("titulo"))}</h2>
  </div>
</section>"""


def horizontal(sid: str, d: dict, fotos: list[dict]) -> str:
    tarjetas = d.get("tarjetas") or []
    t = "".join(f'<article class="ef-hz__tarjeta">{_img(fotos[i % len(fotos)], "ef-hz__img") if fotos else ""}'
                f'<h3>{e(c.get("titulo"))}</h3><p>{e(c.get("texto"))}</p></article>' for i, c in enumerate(tarjetas))
    return f"""<section id="{sid}" class="ef-hz" data-bloque="horizontal" aria-labelledby="{sid}-t">
  <div class="ef-hz__fijo">
    <div class="contenedor"><h2 class="t-head" id="{sid}-t">{e(d.get("titulo"))}</h2></div>
    <div class="ef-hz__pista">{t}</div>
  </div>
</section>"""


def apiladas(sid: str, d: dict, fotos: list[dict]) -> str:
    tarjetas = d.get("tarjetas") or []
    t = "".join(f'<li class="ef-ap__tarjeta" style="--i:{i}"><span class="ef-ap__n">{i + 1:02d}</span><h3 class="t-head">{e(c.get("titulo"))}</h3>'
                f'<p class="t-lead">{e(c.get("texto"))}</p></li>' for i, c in enumerate(tarjetas))
    return f"""<section id="{sid}" class="seccion ef-ap" data-bloque="apiladas" aria-labelledby="{sid}-t">
  <div class="contenedor"><h2 class="t-head" id="{sid}-t" data-efecto="titular">{e(d.get("titulo"))}</h2>
  <ol class="ef-ap__lista" role="list">{t}</ol></div>
</section>"""


def video(sid: str, d: dict, fotos: list[dict]) -> str:
    if not d.get("video"):
        return ""  # sin video real no se pinta (nunca un video inventado)
    return f"""<section id="{sid}" class="ef-video" data-bloque="video" aria-labelledby="{sid}-t">
  <div class="ef-video__fijo">
    <video class="ef-video__v" src="{e(d["video"])}" muted playsinline preload="auto" {f'poster="{e(d["poster"])}"' if d.get("poster") else ""}></video>
    <h2 class="t-display ef-video__titulo" id="{sid}-t">{e(d.get("titulo"))}</h2>
  </div>
</section>"""


BLOQUES = {"pasos": pasos, "mascara": mascara, "zoom": zoom, "horizontal": horizontal, "apiladas": apiladas, "video": video}


def bloque(efecto: str, sid: str, datos: dict, fotos: list[dict]) -> str:
    return BLOQUES[efecto](sid, datos or {}, fotos or [])


# ------------------------------------------------------------------------------------------------ CSS
EFECTOS_CSS = """
/* ===== kit de efectos de Nova ===== */
[data-efecto="titular"] .ef-p { display: inline-block; overflow: clip; vertical-align: bottom; padding-bottom: .06em; }
[data-efecto="titular"] .ef-p > span { display: inline-block; transform: translateY(105%); transition: transform .9s cubic-bezier(.2,.75,.15,1); transition-delay: calc(var(--k) * 55ms); }
[data-efecto="titular"].visto .ef-p > span { transform: none; }
[data-efecto="relleno"] .ef-w { opacity: .18; transition: opacity .25s linear; }
[data-efecto="relleno"] .ef-w.on { opacity: 1; }
[data-efecto="magnetico"] { transition: transform .35s cubic-bezier(.2,.75,.15,1); will-change: transform; }

.ef-sinfoto { background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 35%, var(--bg)), color-mix(in srgb, var(--ink) 15%, var(--bg))); }

/* pasos (scrollytelling) */
.ef-pasos__rejilla { display: grid; gap: clamp(24px, 4vw, 64px); margin-top: clamp(24px, 4vw, 48px); }
.ef-pasos__visor { position: relative; aspect-ratio: 4 / 3; border-radius: var(--radius); overflow: hidden; }
.ef-pasos__img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transform: scale(1.06); transition: opacity .7s ease, transform 1.2s ease; }
.ef-pasos__img.activa { opacity: 1; transform: none; }
.ef-pasos__lista { list-style: none; margin: 0; padding: 0; display: grid; gap: 1.5rem; }
.ef-pasos__paso { padding: 1.25rem 0; border-top: 1px solid color-mix(in srgb, currentColor 20%, transparent); transition: opacity .4s; }
.ef-pasos__n { font-family: var(--font-display); color: var(--accent); font-size: var(--step-lead); }
.ef-pasos__paso h3 { font-family: var(--font-display); font-size: var(--step-head); margin: .3rem 0; }
@media (min-width: 900px) {
  .ef-pasos__rejilla { grid-template-columns: 1.1fr .9fr; align-items: start; }
  .ef-pasos__visor { position: sticky; top: 12vh; height: 76vh; aspect-ratio: auto; }
  .ef-pasos__paso { min-height: 70vh; display: flex; flex-direction: column; justify-content: center; opacity: .3; }
  .ef-pasos__paso.activo { opacity: 1; }
}

/* mascara */
.ef-mascara__marco { border-radius: var(--radius); overflow: hidden; aspect-ratio: 4 / 5; }
.ef-mascara__img { width: 100%; height: 100%; object-fit: cover; clip-path: circle(var(--r, 75%) at 50% 50%); transform: scale(calc(1.15 - var(--p, 1) * .15)); }

/* zoom */
.ef-zoom { height: 220vh; position: relative; }
.ef-zoom__fijo { position: sticky; top: 0; height: 100vh; overflow: hidden; display: grid; place-items: center; }
.ef-zoom__img, .ef-zoom__velo { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.ef-zoom__img { transform: scale(calc(1.6 - var(--p, 1) * .6)); }
.ef-zoom__velo { background: linear-gradient(180deg, rgba(0,0,0,.25), rgba(0,0,0,.55)); }  /* sobre foto: siempre oscuro */
.ef-zoom__titulo { position: relative; color: #fff; text-align: center; max-width: 14ch; padding: 0 var(--gutter);
  opacity: calc(.2 + var(--p, 1) * .8); text-shadow: 0 2px 30px rgba(0,0,0,.45); }

/* horizontal */
.ef-hz { height: 300vh; position: relative; }
.ef-hz__fijo { position: sticky; top: 0; height: 100vh; overflow: hidden; display: flex; flex-direction: column; justify-content: center; gap: 2rem; }
.ef-hz__pista { display: flex; gap: clamp(16px, 2vw, 32px); padding-inline: var(--gutter); width: max-content; transform: translateX(calc(var(--p, 0) * var(--recorrido, 0px) * -1)); }
.ef-hz__tarjeta { width: min(78vw, 420px); flex: none; background: var(--surface); border-radius: var(--radius); padding: 1.2rem; }
.ef-hz__img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: calc(var(--radius) * .7); }
.ef-hz__tarjeta h3 { font-family: var(--font-display); font-size: var(--step-lead); margin: .8rem 0 .3rem; }

/* apiladas */
.ef-ap__lista { list-style: none; margin: clamp(24px, 4vw, 48px) 0 0; padding: 0; display: grid; gap: 4vh; }
.ef-ap__tarjeta { position: sticky; top: calc(10vh + var(--i) * 18px); background: var(--surface); border-radius: var(--radius);
  padding: clamp(24px, 4vw, 56px); min-height: 42vh; box-shadow: 0 -12px 40px -24px color-mix(in srgb, var(--ink) 50%, transparent); }
.ef-ap__n { font-family: var(--font-display); color: var(--accent); font-size: var(--step-head); }

/* video */
.ef-video { height: 260vh; position: relative; }
.ef-video__fijo { position: sticky; top: 0; height: 100vh; overflow: hidden; display: grid; place-items: center; }
.ef-video__v { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.ef-video__titulo { position: relative; color: #fff; text-align: center; text-shadow: 0 2px 30px rgba(0,0,0,.5); padding: 0 var(--gutter); }

/* fondo vivo */
.ef-fondo { position: absolute; inset: 0; z-index: -1; width: 100%; height: 100%; pointer-events: none; }

/* movil: los bloques de scroll se vuelven lista normal (rapido y legible) */
@media (max-width: 759px) {
  .ef-zoom, .ef-hz, .ef-video { height: auto; }
  .ef-zoom__fijo, .ef-hz__fijo, .ef-video__fijo { position: relative; height: auto; min-height: 70vh; }
  .ef-zoom__img { transform: none; }
  .ef-hz__pista { width: auto; transform: none; overflow-x: auto; scroll-snap-type: x mandatory; }
  .ef-hz__tarjeta { scroll-snap-align: start; }
  .ef-ap__tarjeta { position: relative; top: 0; min-height: 0; }
}
@media (prefers-reduced-motion: reduce) {
  [data-efecto="titular"] .ef-p > span { transform: none; transition: none; }
  [data-efecto="relleno"] .ef-w { opacity: 1; }
  .ef-pasos__img { transition: none; }
  .ef-pasos__paso { opacity: 1 !important; }
  .ef-zoom, .ef-hz, .ef-video { height: auto; }
  .ef-zoom__fijo, .ef-hz__fijo, .ef-video__fijo { position: relative; height: auto; min-height: 70vh; }
  .ef-zoom__img, .ef-mascara__img { transform: none; clip-path: none; }
  .ef-hz__pista { transform: none; width: auto; overflow-x: auto; }
}
"""

# ------------------------------------------------------------------------------------------------ JS (motor unico)
EFECTOS_JS = r"""<script>
(() => {
  const calma = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const movil = () => innerWidth < 760;
  const io = (fn, m = '0px 0px -12% 0px') => new IntersectionObserver((es, o) => es.forEach(x => { if (x.isIntersecting) { fn(x.target); o.unobserve(x.target); } }), { rootMargin: m });
  // titular: palabra a palabra
  document.querySelectorAll('[data-efecto="titular"]').forEach(h => {
    if (calma) return;
    let k = 0; const partes = h.textContent.trim().split(/\s+/);
    h.setAttribute('aria-label', h.textContent.trim());
    h.innerHTML = partes.map(p => `<span class="ef-p" aria-hidden="true"><span style="--k:${k++}">${p.replace(/[<>&]/g, '')}</span></span>`).join(' ');
    io(t => t.classList.add('visto')).observe(h);
  });
  // contador
  document.querySelectorAll('[data-efecto="contador"]').forEach(el => {
    const m = el.textContent.match(/(\d[\d.,]*)/); if (!m || calma) return;
    const fin = parseFloat(m[1].replace(/\./g, '').replace(',', '.')), plantilla = el.textContent;
    io(() => { const t0 = performance.now(), d = 1400;
      const paso = (t) => { const p = Math.min(1, (t - t0) / d), v = Math.round(fin * (1 - Math.pow(1 - p, 3)));
        el.textContent = plantilla.replace(m[1], v.toLocaleString('es-ES')); if (p < 1) requestAnimationFrame(paso); else el.textContent = plantilla; };
      requestAnimationFrame(paso); }).observe(el);
  });
  // magnetico
  if (!calma && matchMedia('(pointer: fine)').matches) document.querySelectorAll('[data-efecto="magnetico"]').forEach(b => {
    b.addEventListener('pointermove', (ev) => { const r = b.getBoundingClientRect();
      b.style.transform = `translate(${(ev.clientX - r.left - r.width / 2) * .18}px, ${(ev.clientY - r.top - r.height / 2) * .25}px)`; });
    b.addEventListener('pointerleave', () => { b.style.transform = ''; });
  });
  // relleno: palabras en un span cada una
  const rellenos = [...document.querySelectorAll('[data-efecto="relleno"]')];
  rellenos.forEach(p => { if (calma) return; p.innerHTML = p.textContent.trim().split(/\s+/).map(w => `<span class="ef-w">${w.replace(/[<>&]/g, '')}</span>`).join(' '); });
  // bloques de scroll: progreso 0..1 de cada seccion
  const bloques = [...document.querySelectorAll('[data-bloque]')];
  const hz = bloques.filter(b => b.dataset.bloque === 'horizontal');
  const medirHz = () => hz.forEach(b => { const pista = b.querySelector('.ef-hz__pista'); b.style.setProperty('--recorrido', Math.max(0, pista.scrollWidth - innerWidth + 32) + 'px'); });
  const progreso = (el) => { const r = el.getBoundingClientRect(), total = r.height - innerHeight; return total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : (r.top < innerHeight * .8 ? 1 : 0); };
  let pedido = false;
  const pintar = () => {
    pedido = false;
    for (const p of rellenos) { if (calma) break; const r = p.getBoundingClientRect(), w = p.querySelectorAll('.ef-w');
      const f = Math.min(1, Math.max(0, (innerHeight * .85 - r.top) / (r.height + innerHeight * .45))); const n = Math.round(f * w.length);
      w.forEach((s, i) => s.classList.toggle('on', i < n)); }
    if (calma || movil()) return;
    for (const b of bloques) {
      const t = b.dataset.bloque;
      if (t === 'pasos') { const pasos = [...b.querySelectorAll('.ef-pasos__paso')], imgs = b.querySelectorAll('.ef-pasos__img');
        let act = 0; pasos.forEach((p, i) => { const r = p.getBoundingClientRect(); if (r.top < innerHeight * .55) act = i; });
        pasos.forEach((p, i) => p.classList.toggle('activo', i === act)); imgs.forEach((im, i) => im.classList.toggle('activa', i === act)); continue; }
      const p = t === 'mascara' ? Math.min(1, Math.max(0, (innerHeight - b.getBoundingClientRect().top) / (innerHeight * 1.1))) : progreso(b);
      b.style.setProperty('--p', p.toFixed(4));
      if (t === 'mascara') b.style.setProperty('--r', (12 + p * 63).toFixed(1) + '%');
      if (t === 'video') { const v = b.querySelector('video'); if (v && v.duration) v.currentTime = p * (v.duration - .05); }
    }
  };
  const pedir = () => { if (!pedido) { pedido = true; requestAnimationFrame(pintar); } };
  addEventListener('scroll', pedir, { passive: true }); addEventListener('resize', () => { medirHz(); pedir(); });
  medirHz(); pintar();
  // fondo vivo (canvas 2D): malla de degradado o particulas, en pausa fuera de pantalla
  document.querySelectorAll('canvas.ef-fondo').forEach(cv => {
    const ctx = cv.getContext('2d'), tipo = cv.dataset.fondo || 'malla', cs = getComputedStyle(document.documentElement);
    const col = (v) => cs.getPropertyValue(v).trim() || '#888';
    const colores = [col('--accent'), col('--field') || col('--surface'), col('--surface')];
    let W = 0, H = 0, vivo = true, t = 0;
    const ajustar = () => { const d = Math.min(2, devicePixelRatio || 1), r = cv.getBoundingClientRect(); W = r.width; H = r.height; cv.width = W * d; cv.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0); };
    const pts = Array.from({ length: 46 }, () => ({ x: Math.random(), y: Math.random(), vx: (Math.random() - .5) * .0006, vy: (Math.random() - .5) * .0006, r: 1 + Math.random() * 2.2 }));
    const dibujar = () => {
      ctx.clearRect(0, 0, W, H);
      if (tipo === 'particulas') {
        ctx.fillStyle = colores[0]; ctx.strokeStyle = colores[0];
        pts.forEach(p => { p.x = (p.x + p.vx + 1) % 1; p.y = (p.y + p.vy + 1) % 1; ctx.globalAlpha = .55; ctx.beginPath(); ctx.arc(p.x * W, p.y * H, p.r, 0, 7); ctx.fill(); });
        ctx.lineWidth = .6;
        for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) { const dx = (pts[i].x - pts[j].x) * W, dy = (pts[i].y - pts[j].y) * H, d = Math.hypot(dx, dy);
          if (d < 130) { ctx.globalAlpha = (1 - d / 130) * .25; ctx.beginPath(); ctx.moveTo(pts[i].x * W, pts[i].y * H); ctx.lineTo(pts[j].x * W, pts[j].y * H); ctx.stroke(); } }
      } else {
        colores.forEach((c, i) => { const x = W * (.3 + .4 * Math.sin(t * .00025 * (i + 1) + i * 2)), y = H * (.35 + .3 * Math.cos(t * .0002 * (i + 1.4) + i));
          const g = ctx.createRadialGradient(x, y, 0, x, y, Math.max(W, H) * .55); g.addColorStop(0, c); g.addColorStop(1, 'transparent');
          ctx.globalAlpha = i === 0 ? .55 : .4; ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); });
      }
      ctx.globalAlpha = 1;
    };
    const bucle = (ts) => { t = ts; if (vivo) { dibujar(); requestAnimationFrame(bucle); } };
    ajustar(); addEventListener('resize', ajustar); dibujar();
    if (calma) return;  // movimiento reducido: un fotograma quieto
    new IntersectionObserver(([x]) => { const antes = vivo; vivo = x.isIntersecting; if (vivo && !antes) requestAnimationFrame(bucle); }).observe(cv);
    requestAnimationFrame(bucle);
  });
})();
</script>"""


def canvas_fondo(tipo: str) -> str:
    return f'<canvas class="ef-fondo" data-fondo="{e(tipo)}" aria-hidden="true"></canvas>' if tipo in ("malla", "particulas") else ""


if __name__ == "__main__":
    print(json.dumps(CATALOGO, ensure_ascii=False, indent=1))
