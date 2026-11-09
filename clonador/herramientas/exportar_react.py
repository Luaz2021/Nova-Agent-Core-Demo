"""
EXPORTAR A REACT · los DATOS de la web, sin IA y en local (herramienta aparte: solo LEE del motor y del workspace)

  python herramientas/exportar_react.py [carpeta]          (sin carpeta: el último análisis)

Escribe workspace/<web>/react/:
  datos_web.ts     textos, precios, etiquetas, enlaces, fotos y pestañas de cada sección, sacados del clon fiel
                   (que es la web real congelada) y de interactividad.json. Los componentes React lo importan.
  assets/          las fotos que usan esos datos (copiadas de las que el motor ya descargó)

Para que el modelo que escribe los componentes (Qwen / Nova) NO invente nada: no escribe ni un texto ni un precio,
solo la maqueta, y lee todo de aquí. Al final se comprueba que cada texto del archivo está en la web capturada.
"""

import json
import re
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # clones_web/
sys.path.insert(0, str(RAIZ / "motor"))
sys.dont_write_bytecode = True  # no deja nada en motor/__pycache__
from extraer import ESCRITORIO, NAV_ARGS  # noqa: E402

# por sección: grupos de tarjetas (hijos repetidos de un mismo padre) y lo suelto (titulares, textos, enlaces)
JS_DATOS = r"""
() => {
  const norm = (t) => (t || '').replace(/\s+/g, ' ').trim();
  const visible = (e) => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0.05; };
  const textoPropio = (e) => norm([...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' '));
  // ¿tiene algún texto que se vea? (los de 1x1 px son solo para lectores de pantalla)
  const trozosVisibles = (e) => [...e.querySelectorAll('*')].concat(e).some(x => visible(x) && /[\p{L}\p{N}]/u.test(textoPropio(x)));
  // texto de un párrafo con hijos en línea; si un hijo pega su texto al siguiente sin espacio, el hueco lo pone el
  // CSS (::before/::after o margen): se marca con « · » o con un espacio
  const seps = new Set();   // separadores que vienen del CSS: comprobar() los quita antes de buscar el texto en la web
  const pseudo = (e, p) => { const c = getComputedStyle(e, p).content;
    const t = c && c !== 'none' && c !== 'normal' ? c.replace(/^["']|["']$/g, '').trim() : ''; if (t) seps.add(t); return t; };
  const conSeparadores = (e) => { let t = '';
    for (const n of e.childNodes) {
      if (n.nodeType === 3) { t += n.textContent; continue; }
      if (n.nodeType !== 1) continue;
      const antes = pseudo(n, '::before'), despues = pseudo(n, '::after'), s = getComputedStyle(n);
      const hueco = parseFloat(s.marginRight) + parseFloat(s.paddingRight) > 2;
      t += (antes ? ` ${antes} ` : '') + n.textContent + (despues ? ` ${despues} ` : hueco ? ' ' : '');
    }
    return norm(t); };
  // trozos de texto con su estilo, en orden del documento
  const trozos = (raiz) => { const out = [];
    const tipoEnlace = (a) => a.tagName === 'BUTTON' || (parseFloat(getComputedStyle(a).borderTopLeftRadius) > 8
      && getComputedStyle(a).backgroundColor !== 'rgba(0, 0, 0, 0)') ? 'boton' : 'enlace';
    const apunta = (e, t, enlace) => { const s = getComputedStyle(e);
      out.push({ t, px: parseFloat(s.fontSize), peso: parseInt(s.fontWeight) || 400, color: s.color, tag: e.tagName.toLowerCase(),
                 enlace: enlace ? tipoEnlace(enlace) : null, el: enlace || e }); };
    const ver = (e) => { if (!visible(e)) return; const propio = textoPropio(e);
      const hijos = [...e.children].filter(visible);
      const enLinea = hijos.every(h => getComputedStyle(h).display.startsWith('inline') && !h.querySelector('img, svg, picture'));
      const enlace = e.closest('a, button'), dentro = enlace && raiz.contains(enlace) ? enlace : null;
      // titular que es un logo (iPad mini, Apple Watch): el texto está oculto para lectores de pantalla o en el alt
      if (/^H[1-6]$/.test(e.tagName) && e.querySelector('img') && !trozosVisibles(e)) {
        const t = norm(e.textContent) || norm(e.querySelector('img').getAttribute('alt'));
        if (t) { apunta(e, t, dentro); return; }
      }
      if (propio && enLinea && hijos.length) {
        // párrafo con enlaces/negritas dentro: el texto ENTERO (si no, quedan huecos "consulta a nuestro . Puede"),
        // con los separadores que la web pone por CSS («Crimen» ::after «·» «Para salvar...»)
        apunta(e, conSeparadores(e), dentro);
        if (!dentro) for (const a of e.querySelectorAll('a, button')) if (visible(a) && norm(a.textContent)) apunta(a, norm(a.textContent), a);
        return;
      }
      if (propio && /[\p{L}\p{N}€$]/u.test(propio)) apunta(e, propio, dentro);
      for (const h of e.children) ver(h); };
    ver(raiz); return out; };
  const fotos = (raiz) => [...raiz.querySelectorAll('img')].filter(visible).map(i => { const r = i.getBoundingClientRect();
    return { src: i.currentSrc || i.getAttribute('src') || '', alt: i.getAttribute('alt') || '', ancho: Math.round(r.width), alto: Math.round(r.height) }; })
    .filter(f => f.src && !f.src.startsWith('data:') && f.ancho >= 24 && f.alto >= 24);
  // grupo de tarjetas: un padre con 2+ hijos visibles parecidos (misma etiqueta, tamaño parecido) y con texto
  const grupos = (sec) => { const cands = [];
    // la propia sección también puede ser el padre de las tarjetas (la cuadrícula de promos de apple.com)
    for (const p of [sec, ...sec.querySelectorAll('*')]) {
      const hs = [...p.children].filter(h => visible(h) && norm(h.textContent).length > 2);
      if (hs.length < 2) continue;
      const tag = hs[0].tagName, r0 = hs[0].getBoundingClientRect();
      const iguales = hs.filter(h => { const r = h.getBoundingClientRect(); return h.tagName === tag && Math.abs(r.width - r0.width) <= r0.width * 0.15; });
      if (iguales.length < 2 || iguales.length < hs.length * 0.6) continue;
      // tarjetas de verdad: cada una con algo más que una línea (titular + texto, foto, precio...)
      const ricas = iguales.filter(h => trozos(h).length >= 2 || h.querySelector('img'));
      if (ricas.length < 2) continue;
      // y parecidas POR DENTRO (foto sí/no, cantidad de textos): una fila de 2 columnas de Elementor (texto | foto)
      // no son 2 tarjetas
      const conFoto = ricas.filter(h => h.querySelector('img')).length;
      if (conFoto && conFoto < ricas.length * 0.6) continue;
      const nt = ricas.map(h => Math.max(1, trozos(h).length));
      if (Math.max(...nt) > 3 * Math.min(...nt)) continue;
      cands.push({ p, hs: iguales });
    }
    // de los grupos anidados, el de fuera (las tarjetas, no las líneas de dentro de cada una)
    return cands.filter(c => !cands.some(o => o !== c && o.hs.some(h => h.contains(c.p))));
  };
  const out = [];
  for (const sec of [...document.querySelectorAll('[data-clon-sec]')].sort((a, b) => +a.dataset.clonSec - +b.dataset.clonSec)) {
    const gs = grupos(sec);
    const enTarjeta = (e) => gs.some(g => g.hs.some(h => h.contains(e)));
    const fondo = getComputedStyle(sec).backgroundColor;
    out.push({
      n: +sec.dataset.clonSec, fondo,
      sueltos: trozos(sec).filter(x => !enTarjeta(x.el)).map(({ el, ...x }) => x),
      fotos_sueltas: fotos(sec).filter(f => ![...sec.querySelectorAll('img')].some(i => (i.currentSrc || i.getAttribute('src')) === f.src && enTarjeta(i))),
      // fondo de cada tarjeta: el suyo o el del primer hijo que lo pinta (las promos de apple.com alternan blanco/negro)
      grupos: gs.map(g => g.hs.map(h => ({ trozos: trozos(h).map(({ el, ...x }) => x), fotos: fotos(h),
        fondo: [h, ...h.querySelectorAll('*')].map(x => getComputedStyle(x).backgroundColor).find(c => !/rgba\(0, 0, 0, 0\)|transparent/.test(c)) || null }))),
    });
  }
  return { titulo: document.title, secciones: out, separadores: [...seps] };
}
"""
PRECIO = re.compile(r"(\d[\d.,]*\s?(€|EUR|\$|USD)|(€|\$)\s?\d[\d.,]*)")


def _rgb_hex(c):
    m = re.findall(r"[\d.]+", c or "")
    if len(m) >= 3 and (len(m) < 4 or float(m[3]) > 0.05):
        return "#" + "".join(f"{int(float(x)):02X}" for x in m[:3])
    return None


def _clasificar(trozos):
    """Papel de cada texto: titular (el más grande), etiqueta ("Nuevo": corto, de otro color, encima del titular),
    precio, enlaces/botones y el resto como textos. Todo tal cual sale de la web."""
    if not trozos:
        return {}
    cuerpo = max(trozos, key=lambda x: len(x["t"]))["color"]
    # el titular es el texto más grande aunque sea un enlace (en las fichas de proyecto el nombre ES el enlace);
    # los botones no cuentan
    titular = max(
        (x for x in trozos if x["enlace"] != "boton"),
        key=lambda x: (x["px"], x["peso"]),
        default=None,
    )
    out = {
        "titulo": titular["t"] if titular else None,
        "etiqueta": None,
        "precio": None,
        "textos": [],
        "enlaces": [],
    }
    vistos = set()
    for i, x in enumerate(trozos):
        if x is titular or x["t"] in vistos:
            continue
        vistos.add(x["t"])
        if x["enlace"]:
            out["enlaces"].append({"texto": x["t"], "estilo": x["enlace"]})
        elif PRECIO.search(x["t"]) and len(x["t"]) <= 40 and not out["precio"]:
            out["precio"] = x["t"]
        elif (
            len(x["t"]) <= 20
            and x["color"] != cuerpo
            and titular
            and i < trozos.index(titular)
        ) and not out["etiqueta"]:
            out["etiqueta"] = x["t"]
        else:
            out["textos"].append(x["t"])
    return out


def exportar(carpeta):
    from playwright.sync_api import sync_playwright

    carpeta = Path(carpeta).resolve()
    base = carpeta / "construccion" / "base"
    fiel = base / "clon_fiel.html"
    if not fiel.exists():
        raise SystemExit(f"No está {fiel}: primero crear.py")
    spec = json.loads(
        (carpeta / "referencia" / "spec.json").read_text(encoding="utf-8")
    )
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        p = nav.new_page(viewport={"width": ESCRITORIO[0], "height": ESCRITORIO[1]})
        # sin red: solo hace falta la maqueta (las fotos tienen su tamaño en el CSS), no descargar nada
        p.route(
            "**/*",
            lambda r: r.abort() if r.request.url.startswith("http") else r.continue_(),
        )
        p.goto(fiel.as_uri(), wait_until="load")
        p.wait_for_timeout(500)
        crudo = p.evaluate(JS_DATOS)
        nav.close()

    # fotos: la que el motor ya descargó en assets/ (por nombre de archivo); si no está, la URL original
    origen_assets = carpeta / "assets"
    locales = (
        {f.name.lower(): f for f in origen_assets.glob("*")}
        if origen_assets.exists()
        else {}
    )
    fm = (
        origen_assets / "_mapa.json"
    )  # URL -> archivo (analizar.py): dos fotos con el mismo nombre no se confunden
    mapa = json.loads(fm.read_text(encoding="utf-8")) if fm.exists() else {}
    destino = carpeta / "react"
    (destino / "assets").mkdir(parents=True, exist_ok=True)
    usadas = {}

    def foto(f):
        if mapa:
            local = locales.get(
                (mapa.get(f["src"]) or mapa.get(f["src"].split("?")[0]) or "").lower()
            )
        else:  # análisis antiguo, sin mapa: por nombre de archivo
            local = locales.get(
                re.sub(r"[^\w.\-]", "_", Path(f["src"].split("?")[0]).name).lower()
            )
        if local:
            shutil.copy(local, destino / "assets" / local.name)
            usadas[local.name] = f["src"]
            src = "/assets/" + local.name
        else:
            src = f["src"]
        return {"src": src, "alt": f["alt"], "ancho": f["ancho"], "alto": f["alto"]}

    inter = {}
    fi = carpeta / "interactividad.json"
    if fi.exists():
        inter = json.loads(fi.read_text(encoding="utf-8")).get("secciones", {})

    secciones = []
    for s in crudo["secciones"]:
        suelto = _clasificar(s["sueltos"])
        sec = {
            "n": s["n"],
            "fondo": _rgb_hex(s["fondo"]),
            "titulo": suelto.get("titulo"),
            "textos": suelto.get("textos", []),
            "enlaces": suelto.get("enlaces", []),
            "imagenes": [foto(f) for f in s["fotos_sueltas"]],
            "grupos": [],
        }
        for g in s["grupos"]:
            tarjetas = []
            for h in g:
                c = _clasificar(h["trozos"])
                t = {k: v for k, v in c.items() if v}
                if _rgb_hex(h.get("fondo")):
                    t["fondo"] = _rgb_hex(h["fondo"])
                if h[
                    "fotos"
                ]:  # la foto grande de la tarjeta (no el logo que hace de titular)
                    t["imagen"] = foto(
                        max(h["fotos"], key=lambda f: f["ancho"] * f["alto"])
                    )
                tarjetas.append(t)
            sec["grupos"].append(tarjetas)
        # pestañas medidas por el explorador: qué tarjetas enseña cada una
        for g in (inter.get(str(s["n"])) or {}).get("pestanas", []):
            sec.setdefault("pestanas", []).append(
                [
                    {
                        "texto": q.get("texto") or q.get("aria_label"),
                        "tarjetas": q.get("tarjetas_visibles") or [],
                    }
                    for q in g.get("pestanas", [])
                ]
            )
        secciones.append(sec)

    datos = {
        "url": spec["url"],
        "titulo": crudo["titulo"],
        "fuentes": spec.get("fuentes_google"),
        "fondo": spec.get("fondo_body"),
        "secciones": secciones,
    }
    comprobar(datos, fiel, crudo.get("separadores", []))
    ts = (
        f"// Generado por clones_web/motor/exportar_react.py desde {spec['url']} ({time.strftime('%Y-%m-%d %H:%M')}).\n"
        "// Son los textos, precios y fotos REALES de la web: no se editan a mano (se regenera) ni los escribe la IA.\n\n"
        "export interface Imagen { src: string; alt: string; ancho: number; alto: number }\n"
        "export interface Enlace { texto: string; estilo: 'boton' | 'enlace' }\n"
        "export interface Tarjeta { titulo?: string; etiqueta?: string; precio?: string; textos?: string[]; enlaces?: Enlace[]; imagen?: Imagen; fondo?: string }\n"
        "export interface Pestana { texto: string; tarjetas: string[] }\n"
        "export interface Seccion { n: number; fondo: string | null; titulo: string | null; textos: string[]; enlaces: Enlace[];\n"
        "  imagenes: Imagen[]; grupos: Tarjeta[][]; pestanas?: Pestana[][] }\n\n"
        f"export const web = {json.dumps({k: v for k, v in datos.items() if k != 'secciones'}, ensure_ascii=False, indent=2)} as const;\n\n"
        f"export const secciones: Seccion[] = {json.dumps(secciones, ensure_ascii=False, indent=2)};\n\n"
        "export const seccion = (n: number) => secciones.find(s => s.n === n)!;\n"
    )
    (destino / "datos_web.ts").write_text(ts, encoding="utf-8")
    n_tarj = sum(len(g) for s in secciones for g in s["grupos"])
    print(
        f"React: {len(secciones)} secciones, {n_tarj} tarjetas, {len(usadas)} fotos locales -> {destino / 'datos_web.ts'}"
    )
    return destino / "datos_web.ts"


def comprobar(datos, fiel, separadores=()):
    """Ningún texto inventado: cada texto del archivo tiene que estar en la web capturada (clon fiel).
    Los separadores que pone el CSS (::after «·») no están en el HTML: se quitan antes de buscar."""
    import html as H

    # sin espacios: al quitar las etiquetas quedan huecos donde iba un enlace ("socio . Puede" frente a "socio. Puede")
    plano = re.sub(
        r"\s+", "", H.unescape(re.sub(r"<[^>]+>", "", fiel.read_text(encoding="utf-8")))
    )

    def textos(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("src", "alt", "estilo", "fondo", "url", "fuentes"):
                    continue
                yield from textos(v)
        elif isinstance(o, list):
            for v in o:
                yield from textos(v)
        elif isinstance(o, str):
            yield o

    def limpio(t):
        for sep in separadores:
            t = t.replace(sep, "")
        return re.sub(r"\s+", "", t)

    malos = [t for t in textos(datos["secciones"]) if limpio(t) not in plano]
    if malos:
        raise SystemExit(
            f"Hay {len(malos)} textos que no están en la web capturada (no debería pasar): {malos[:5]}"
        )


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    carpeta = (
        Path(args[0])
        if args
        else Path(
            (RAIZ / "workspace" / "ultimo_analisis.txt")
            .read_text(encoding="utf-8")
            .strip()
        )
    )
    exportar(carpeta)


if __name__ == "__main__":
    main()
