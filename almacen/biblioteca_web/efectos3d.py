"""
EFECTOS 3D · nivel 3D de la biblioteca de Nova (09/11/2026, Claude, a pedido de Luaz). Hermano de efectos.py.
Ni Nova ni Qwen escriben 3D: estos fragmentos son fijos y probados; montar.py los pone segun el estilo.

Regla de Luaz: "2 en 3D por web" con condiciones:
  - PROTAGONISTA (WebGL, Three.js por CDN, en la portada):
      liquido      -> degradado liquido con shader (colores de la paleta)
      formas       -> formas 3D flotando con luz suave, siguen un poco al raton
      particulas3d -> nube de particulas en 3D que gira y sigue al raton
  - LIGERO (sin WebGL, CSS 3D): profundidad -> fotos y tarjetas se inclinan en 3D al mover el raton
  - BLOQUES con contenido REAL del cliente (si no lo hay, no se pintan):
      producto_3d -> <model-viewer> de Google con un modelo .glb real (gira, zoom, AR en movil)
      lottie      -> animacion Lottie (.json de LottieFiles u otro)
Siempre: Three.js solo se descarga cuando la portada se ve; el 3D se pausa fuera de pantalla (nunca dos animando);
movil (<760px) y "reducir movimiento" -> sin WebGL (queda un fondo quieto con la paleta); sin JS -> se ve todo.
Colores: los lee de la paleta (--accent, --surface, --bg, --ink), igual que canvas_fondo de efectos.py.
"""

from __future__ import annotations

import html

THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
MODEL_VIEWER = "https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js"
LOTTIE = "https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"
PROTAGONISTAS = ("liquido", "formas", "particulas3d")


def e(x) -> str:
    return html.escape(str(x or ""), quote=True)


def canvas(tipo: str) -> str:
    return f'<canvas class="ef3d" data-3d="{e(tipo)}" aria-hidden="true"></canvas>' if tipo in PROTAGONISTAS else ""


def producto_3d(d: dict) -> str:
    p = d.get("producto_3d") or {}
    if not str(p.get("glb", "")).lower().split("?")[0].endswith((".glb", ".gltf")):
        return ""  # sin modelo real no se pinta (nunca uno inventado)
    poster = f' poster="{e(p["poster"])}"' if p.get("poster") else ""
    return f"""<section class="seccion ef3d-producto" id="producto-3d" aria-labelledby="producto-3d-t">
  <div class="contenedor rejilla-2">
    <div class="pila" style="--pila:1rem"><h2 class="t-head" id="producto-3d-t">{e(p.get("titulo") or "Miralo por todos los lados")}</h2>
      <p class="t-lead">{e(p.get("texto") or "Gira el modelo con el dedo o el raton. En el movil puedes verlo en tu casa con realidad aumentada.")}</p></div>
    <model-viewer class="ef3d-producto__visor" src="{e(p["glb"])}" alt="{e(p.get("alt") or p.get("titulo") or "Modelo 3D")}"{poster}
      camera-controls auto-rotate rotation-per-second="18deg" ar shadow-intensity="1" loading="lazy" touch-action="pan-y"></model-viewer>
  </div>
</section>
<script type="module" src="{MODEL_VIEWER}"></script>"""


def lottie(d: dict) -> str:
    l = d.get("lottie") or {}
    if not str(l.get("json", "")).lower().split("?")[0].endswith(".json"):
        return ""
    return f"""<section class="seccion ef3d-lottie" id="animacion" aria-label="{e(l.get("alt") or "Animacion")}">
  <div class="contenedor pila" style="--pila:1rem;text-align:center">
    {f'<h2 class="t-head">{e(l["titulo"])}</h2>' if l.get("titulo") else ""}
    <div class="ef3d-lottie__caja" data-lottie="{e(l["json"])}" aria-hidden="true"></div>
  </div>
</section>
<script src="{LOTTIE}" defer></script>"""


CSS = """
/* efectos3d.py */
.hero--3d { position: relative; isolation: isolate; overflow: hidden; }
.ef3d { position: absolute; inset: 0; z-index: -1; width: 100%; height: 100%; pointer-events: none; opacity: 0; transition: opacity 1.2s ease; }
.ef3d.listo { opacity: 1; }
.ef3d[data-3d="formas"].listo, .ef3d[data-3d="particulas3d"].listo { opacity: .75; }
.hero--3d-liquido { background: radial-gradient(120% 90% at 80% 10%, color-mix(in srgb, var(--accent) 22%, var(--bg)), var(--bg) 60%); }
@media (max-width: 759px), (prefers-reduced-motion: reduce) { .ef3d { display: none; } }
[data-3d-ligero] .prof { transform-style: preserve-3d; transition: transform .5s cubic-bezier(.2,.75,.15,1); will-change: transform; }
.ef3d-producto__visor { width: 100%; aspect-ratio: 1 / 1; background: var(--surface); border-radius: var(--radius); --poster-color: transparent; }
.ef3d-lottie__caja { width: min(520px, 100%); aspect-ratio: 1 / 1; margin-inline: auto; }
"""

JS = r"""<script>
(() => {
  const calma = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const raton = matchMedia('(pointer: fine)').matches;
  const cs = getComputedStyle(document.documentElement);
  const col = (v, d) => cs.getPropertyValue(v).trim() || d;
  // LIGERO: profundidad 3D con CSS (sin WebGL)
  if (document.body.hasAttribute('data-3d-ligero') && !calma && raton) {
    document.querySelectorAll('.des__tarjeta, .hero__foto-partida, .ef-hz__tarjeta, .des__zz img, .ef-mascara__marco').forEach(el => {
      el.classList.add('prof');
      el.addEventListener('pointermove', ev => { const r = el.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width - .5, y = (ev.clientY - r.top) / r.height - .5;
        el.style.transform = `perspective(900px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg) translateZ(6px)`; });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });
  }
  // LOTTIE (solo con animacion real del cliente)
  document.querySelectorAll('[data-lottie]').forEach(caja => {
    new IntersectionObserver(([x], io) => { if (!x.isIntersecting || !window.lottie) return; io.disconnect();
      const a = lottie.loadAnimation({ container: caja, renderer: 'svg', loop: !calma, autoplay: !calma, path: caja.dataset.lottie });
      if (calma) a.addEventListener('DOMLoaded', () => a.goToAndStop(a.totalFrames - 1, true)); }).observe(caja);
  });
  // PROTAGONISTA WebGL
  if (calma || matchMedia('(max-width: 759px)').matches) return;
  const lienzos = [...document.querySelectorAll('canvas.ef3d')];
  if (!lienzos.length) return;
  let T = null;
  const cargar = async () => (T = T || await import('__THREE__'));
  lienzos.forEach(cv => new IntersectionObserver(async ([x]) => {
    if (x.isIntersecting && !cv._ini) { cv._ini = true; try { await cargar(); escena(cv); } catch (err) { cv.remove(); } }
    if (cv._vivo) cv._vivo(x.isIntersecting);
  }, { rootMargin: '120px' }).observe(cv));

  function escena(cv) {
    const r = new T.WebGLRenderer({ canvas: cv, alpha: true, antialias: true, powerPreference: 'low-power' });
    r.setPixelRatio(Math.min(devicePixelRatio, 2));
    const tipo = cv.dataset['3d'], C = (v, d) => new T.Color(col(v, d));
    const raton3 = { x: 0, y: 0 };
    addEventListener('pointermove', ev => { raton3.x = ev.clientX / innerWidth - .5; raton3.y = ev.clientY / innerHeight - .5; }, { passive: true });
    let escenaT, cam, paso;
    if (tipo === 'liquido') {
      escenaT = new T.Scene(); cam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const u = { t: { value: 0 }, m: { value: new T.Vector2() }, a: { value: C('--accent', '#556') }, b: { value: C('--surface', '#ddd') }, c: { value: C('--bg', '#fff') } };
      const mat = new T.ShaderMaterial({ uniforms: u, vertexShader: 'varying vec2 v; void main(){ v = uv; gl_Position = vec4(position, 1.0); }',
        fragmentShader: `varying vec2 v; uniform float t; uniform vec2 m; uniform vec3 a, b, c;
          float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
          float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
            return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + 1.), f.x), f.y); }
          void main(){ vec2 p = v * 2.2 + m * .35; float q = n(p + t * .06) + .5 * n(p * 2. - t * .05);
            float k = smoothstep(.35, 1.25, q + .25 * sin(t * .2 + v.x * 3.));
            vec3 col = mix(c, mix(b, a, k), .55 * k + .15); gl_FragColor = vec4(col, 1.0); }` });
      escenaT.add(new T.Mesh(new T.PlaneGeometry(2, 2), mat));
      cv.parentElement.classList.add('hero--3d-liquido');
      paso = (s) => { u.t.value = s; u.m.value.set(raton3.x, -raton3.y); };
    } else {
      escenaT = new T.Scene(); cam = new T.PerspectiveCamera(42, 1, .1, 100); cam.position.z = 7;
      const grupo = new T.Group(); escenaT.add(grupo);
      if (tipo === 'formas') {
        escenaT.add(new T.AmbientLight(0xffffff, .9)); const luz = new T.DirectionalLight(0xffffff, 1.4); luz.position.set(3, 4, 5); escenaT.add(luz);
        const geos = [new T.IcosahedronGeometry(.7, 0), new T.TorusGeometry(.55, .2, 24, 64), new T.SphereGeometry(.5, 32, 32), new T.OctahedronGeometry(.6), new T.TorusKnotGeometry(.4, .14, 96, 12)];
        const cols = [C('--accent', '#556'), C('--surface', '#ddd'), C('--ink', '#222')];
        for (let i = 0; i < 7; i++) {
          const m = new T.Mesh(geos[i % geos.length], new T.MeshStandardMaterial({ color: cols[i % cols.length], roughness: .35, metalness: .15 }));
          m.position.set((i % 2 ? 1 : -1) * (1.6 + (i * .7) % 2.6), (i * 1.37) % 4 - 2, -(i % 3)); m.userData.f = i * 1.7; grupo.add(m);
        }
        paso = (s) => { grupo.children.forEach(m => { m.rotation.x = s * .25 + m.userData.f; m.rotation.y = s * .18 + m.userData.f; m.position.y += Math.sin(s + m.userData.f) * .0015; });
          grupo.rotation.y += (raton3.x * .5 - grupo.rotation.y) * .04; grupo.rotation.x += (raton3.y * .3 - grupo.rotation.x) * .04; };
      } else {  // particulas3d
        const n = 1800, pos = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) { const r3 = 2.4 + Math.random() * 2.2, a = Math.random() * 6.283, b = Math.acos(2 * Math.random() - 1);
          pos.set([r3 * Math.sin(b) * Math.cos(a), r3 * Math.sin(b) * Math.sin(a), r3 * Math.cos(b)], i * 3); }
        const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(pos, 3));
        grupo.add(new T.Points(g, new T.PointsMaterial({ color: C('--accent', '#556'), size: .035, transparent: true, opacity: .85 })));
        paso = (s) => { grupo.rotation.y = s * .05 + raton3.x * .6; grupo.rotation.x = raton3.y * .4; };
      }
    }
    const medir = () => { const w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return; r.setSize(w, h, false);
      if (cam.isPerspectiveCamera) { cam.aspect = w / h; cam.updateProjectionMatrix(); } };
    new ResizeObserver(medir).observe(cv); medir();
    let vivo = true; const t0 = performance.now();
    const bucle = () => { if (!vivo) return; paso((performance.now() - t0) / 1000); r.render(escenaT, cam); requestAnimationFrame(bucle); };
    cv._vivo = (v) => { const antes = vivo; vivo = v; if (v && !antes) requestAnimationFrame(bucle); };
    cv.classList.add('listo'); requestAnimationFrame(bucle);
  }
})();
</script>""".replace("__THREE__", THREE)
