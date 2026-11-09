"""
PROBAR INTERACCIONES DEL CLON (Bloque 3) · sin IA

  python probar_interacciones.py [carpeta] [--html=index.html]

Abre construccion/<html>, pulsa cada pestaña, bolita y disparador que midió el explorador y comprueba que el clon
hace lo mismo que la original:
  - pestaña con filtro: se ven justo sus tarjetas (tarjetas_visibles) y las otras no
  - pestaña con panel: se ve el texto de su panel
  - bolita: la foto pasa a la del color (si la original cambiaba de foto)
  - modal: se abre con su título y se cierra con Escape · desplegable: se abre y se cierra
Escribe construccion/interacciones_prueba.md y devuelve el % de comprobaciones correctas.
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from extraer import ESCRITORIO, NAV_ARGS  # noqa: E402
from puente_interactividad import compactar  # noqa: E402

JS_VE = r"""([n, texto]) => { const raiz = document.querySelector(`[data-clon-sec="${n}"]`) || document.body;
  const t = texto.replace(/\s+/g, ' ').trim().toLowerCase();
  for (const e of raiz.querySelectorAll('*')) {
    if ((e.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase() !== t) continue;
    if (e.children.length && [...e.children].some(c => (c.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase() === t)) continue;
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'; }
  return null; }"""
# ¿se ve en la sección una foto con la imagen de ese color? (vale para fotos que cambian de src y para fotos apiladas)
JS_FOTO = r"""([n, url]) => { const raiz = document.querySelector(`[data-clon-sec="${n}"]`) || document.body;
  return [...raiz.querySelectorAll('img')].some(i => i.getAttribute('src') === url && i.getBoundingClientRect().width > 0); }"""
JS_PULSAR = r"""([n, texto, i, tipo, grupo]) => { const raiz = document.querySelector(`[data-clon-sec="${n}"]`) || document.body;
  const norm = (t) => (t || '').replace(/\s+/g, ' ').trim().toLowerCase();
  let e = raiz.querySelector(`[data-${tipo}="${grupo}:${i}"]`);
  if (!e) { const t = norm(texto); let mejor = null;
    for (const c of raiz.querySelectorAll('*')) { if (norm(c.getAttribute('aria-label')) === t) { mejor = c; break; }
      if (norm(c.textContent) === t && (!mejor || mejor.contains(c))) mejor = c; }
    e = mejor && (mejor.closest('button, a, label, input, summary, [role="tab"], [role="button"], [tabindex]') || mejor); }
  if (!e) return false;
  (e.tagName === 'INPUT' && e.parentElement ? e.parentElement : e).click(); return true; }"""


def probar(carpeta, html="index.html"):
    from playwright.sync_api import sync_playwright
    carpeta = Path(carpeta)
    datos = compactar(json.loads((carpeta / "interactividad.json").read_text(encoding="utf-8")))
    f = carpeta / "construccion" / html
    filas, bien, total = [], 0, 0

    def apunta(ok, que):
        nonlocal bien, total
        total += 1
        bien += bool(ok)
        filas.append(f"- {'✅' if ok else '❌'} {que}")

    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        p = nav.new_context(viewport={"width": ESCRITORIO[0], "height": ESCRITORIO[1]}).new_page()
        p.goto(f.as_uri(), wait_until="load")
        p.wait_for_timeout(1500)
        inf = p.evaluate("window.clonInteracciones || null")
        if inf is None:
            apunta(False, "el runtime clon-interacciones.js no está en el clon")
        else:
            for x in inf["fallidos"]:
                apunta(False, f"gancho no encontrado: {x}")
        for n, s in datos["secciones"].items():
            for g in s.get("pestanas", []):
                titulos = sorted({t for q in g["pestanas"] for t in q["tarjetas_visibles"]})
                for i, q in enumerate(g["pestanas"]):
                    if not p.evaluate(JS_PULSAR, [n, q["texto"] or q["aria_label"], i, "tab", g["id"]]):
                        continue
                    p.wait_for_timeout(200)
                    if g.get("filtra_contenido") and titulos:
                        ver = set(q["tarjetas_visibles"])
                        mal = [t for t in titulos if p.evaluate(JS_VE, [n, t]) is not None and p.evaluate(JS_VE, [n, t]) != (t in ver)]
                        apunta(not mal, f'sec {n} pestaña "{q["texto"]}" muestra {sorted(ver) or "—"}' + (f" (fallan: {mal})" if mal else ""))
                    if q.get("panel") and (q["panel"].get("titulo") or q["panel"].get("texto")):
                        t = q["panel"].get("titulo") or q["panel"]["texto"]
                        apunta(p.evaluate(JS_VE, [n, t]) is True, f'sec {n} pestaña "{q["texto"]}" enseña su panel')
                # se deja como estaba (la pestaña por defecto): lo siguiente que se prueba puede estar en sus tarjetas
                ini = next((i for i, q in enumerate(g["pestanas"]) if q.get("activa_por_defecto")), 0)
                p.evaluate(JS_PULSAR, [n, g["pestanas"][ini]["texto"] or g["pestanas"][ini]["aria_label"], ini, "tab", g["id"]])
                p.wait_for_timeout(150)
            for g in s.get("variantes_color", []):
                # si el producto vive en una pestaña (tarjeta o panel), se abre esa pestaña antes, como haría alguien
                for gt in s.get("pestanas", []):
                    for j, q in enumerate(gt["pestanas"]):
                        panel = " ".join(str(v) for v in (q.get("panel") or {}).values())
                        if g.get("producto") and (g["producto"] in q["tarjetas_visibles"] or g["producto"] in panel) and not q.get("activa_por_defecto"):
                            p.evaluate(JS_PULSAR, [n, q["texto"] or q["aria_label"], j, "tab", gt["id"]])
                            p.wait_for_timeout(150)
                for i, c in enumerate(g["colores"]):
                    # sin foto propia (bolita agotada/deshabilitada en la original) no hay nada que comprobar
                    if not c.get("img_url") or not c.get("img_alt") or g.get("conmuta_imagen") is False:
                        continue
                    if not p.evaluate(JS_PULSAR, [n, c["color_nombre"], i, "color", g["id"]]):
                        continue
                    p.wait_for_timeout(150)
                    apunta(p.evaluate(JS_FOTO, [n, c["img_url"]]), f'sec {n} color "{c["color_nombre"]}" enseña su foto ("{c.get("img_alt")}")')
            for i, m in enumerate(s.get("modales", [])):
                if not p.evaluate(JS_PULSAR, [n, m["disparador"]["texto"], i, "modal", n]):
                    continue
                p.wait_for_timeout(200)
                t = m.get("titulo") or (m["bloques"][0]["texto"] if m["bloques"] else "")
                if m["tipo"] == "desplegable":
                    abre = p.evaluate(JS_VE, [n, m["bloques"][0]["texto"]]) is True if m["bloques"] else True
                    p.evaluate(JS_PULSAR, [n, m["disparador"]["texto"], i, "modal", n]); p.wait_for_timeout(150)
                    cierra = p.evaluate(JS_VE, [n, m["bloques"][0]["texto"]]) is not True if m["bloques"] else True
                    apunta(abre and cierra, f'sec {n} desplegable "{m["disparador"]["texto"]}" se abre y se cierra')
                else:
                    abre = p.evaluate("(t) => { const c = document.getElementById('clon-capa'); return !!c && c.textContent.includes(t); }", t)
                    p.keyboard.press("Escape"); p.wait_for_timeout(150)
                    cierra = p.evaluate("() => !document.getElementById('clon-capa')")
                    apunta(abre and cierra, f'sec {n} modal "{t}" se abre y se cierra con Escape')
        nav.close()
    pct = round(100 * bien / total) if total else 100
    texto = f"# Interacciones del clon · {html}\n\n**{bien} de {total} comprobaciones correctas ({pct} %)**\n\n" + "\n".join(filas) + "\n"
    (carpeta / "construccion" / "interacciones_prueba.md").write_text(texto, encoding="utf-8")
    return pct, bien, total, filas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    carpeta = Path(args[0]) if args else Path((BASE.parent / "workspace" / "ultimo_analisis.txt").read_text(encoding="utf-8").strip())
    pct, bien, total, filas = probar(carpeta, opc.get("html", "index.html"))
    print("\n".join(filas))
    print(f"\nInteracciones: {bien} de {total} correctas ({pct} %) -> construccion/interacciones_prueba.md")


if __name__ == "__main__":
    main()
