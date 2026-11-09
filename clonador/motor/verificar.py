import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
PASO 3 · VERIFICAR (y que Qwen repare)

  python verificar.py                (usa el último análisis)
  python verificar.py --solo=10      (solo las 10 primeras secciones)
  python verificar.py --umbral=90 --lista=90

Por cada sección del clon (construccion/index.html), 4 controles:
  1. parecido visual con la original (PC 60 % + móvil 40 %)
  2. lista de comprobación automática, sacada de las medidas de la original (textos, tamaños, pesos, colores, columnas, fondo...)
  3. estructura (carrusel, texto encima de imagen)
  4. Qwen con ojos describe lo que ve distinto (solo si falla)
Aprobada si parecido >= 90 % y lista >= 90 %. Si no: Qwen Coder la repara (máx. 3 intentos, se queda la mejor versión).
Lo que siga en rojo va a pendientes_nova.md: lo arregla Claude con código y lo apunta en correcciones.md (antes -> después).
Al final: index_final.html con medios de libre uso.
"""
import base64
import io
import json
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
import comparar as cmp  # noqa: E402
from construir import (CAR_POR_TOKEN, NUM_PREDICT, OLLAMA, MODELO, copiar_imgs, escribir_forense, log, preguntar,  # noqa: E402
                       revision_html, vestir_final)

def _modelo_nova(clave, defecto):
    try:
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8")).get(clave, defecto)
    except Exception:
        return defecto


MODELO_OJOS = _modelo_nova("vl", "blaifa/InternVL3_5:8b")
# Qwen devuelve la sección ENTERA: tiene que caber en su salida (8K tokens) con un 10 % de margen para lo que añada.
# Unos 13.600 caracteres; más grande -> directo a Claude (antes, con 4K de salida, todo lo de > ~7.500 salía cortado).
MAX_CODIGO_QWEN = int(NUM_PREDICT * 0.9 * CAR_POR_TOKEN)

SISTEMA = """Eres un desarrollador front-end experto en Tailwind CSS. Te doy UNA sección de una página (HTML con clases de Tailwind)
y la lista de diferencias que un verificador midió contra la web original.
Corrige SOLO esas diferencias, cambiando lo mínimo (clases, y la estructura solo si la lista lo pide).
REGLAS
- Devuelve el elemento completo, empezando por la MISMA etiqueta con su atributo data-clon-sec, y nada más (sin explicaciones).
- Conserva todos los textos, todas las imágenes/vídeos con sus atributos (data-medio, data-w, data-h) y el resto de clases.
- Tamaños exactos con corchetes: text-[48px] (móvil) md:text-[64px] (escritorio). Colores exactos: text-[#1D1D1F].
- Nada de <style>, <script>, @apply ni la clase "container"."""


# ---------------------------------------------------------------- utilidades
def bloque_seccion(html, n):
    """(inicio, fin) del elemento con data-clon-sec="n", emparejando etiquetas."""
    m = re.search(rf'<([a-zA-Z0-9]+)[^>]*\sdata-clon-sec="{n}"', html)
    if not m:
        return None
    tag = m.group(1)
    prof = 0
    for t in re.finditer(rf"<(/?){tag}\b[^>]*?(/?)>", html[m.start():], re.I):
        if t.group(2):
            continue
        prof += -1 if t.group(1) else 1
        if prof == 0:
            return m.start(), m.start() + t.end()
    return None


def equilibrado(fr):
    vacios = {"img", "br", "hr", "input", "source", "meta", "link", "wbr", "area", "col", "embed", "track", "path", "circle",
              "rect", "line", "polyline", "polygon", "ellipse", "use", "stop"}
    pila = []
    for cierre, tag, auto in re.findall(r"<(/?)([a-zA-Z0-9]+)[^>]*?(/?)>", fr):
        tag = tag.lower()
        if tag in vacios or auto:
            continue
        if cierre:
            if not pila or pila[-1] != tag:
                return False
            pila.pop()
        else:
            pila.append(tag)
    return not pila


def palabras(fr):
    return set(re.findall(r"[a-záéíóúñ0-9]{3,}", re.sub(r"<[^>]+>", " ", fr).lower()))


def respuesta_valida(nuevo, viejo, n):
    if f'data-clon-sec="{n}"' not in nuevo[:400]:
        return "falta data-clon-sec"
    if not equilibrado(nuevo):
        return "HTML desequilibrado"
    if len(nuevo) < len(viejo) * 0.5:
        return "borró demasiado"
    pv = palabras(viejo)
    if pv and len(pv & palabras(nuevo)) / len(pv) < 0.9:
        return "perdió textos"
    return None


def limpiar_respuesta(t):
    m = re.search(r"```(?:html)?\s*(.*?)```", t, re.S)
    t = (m.group(1) if m else t).strip()
    i = t.find("<")
    return t[i:].strip() if i >= 0 else ""


def ojos_ok():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5) as r:
            return any(MODELO_OJOS in m["name"] or "internvl" in m["name"].lower() or "vl" in m["name"].lower() for m in json.loads(r.read())["models"])
    except Exception:
        return False


def _b64(ruta, alto_max=1400):
    from PIL import Image
    im = Image.open(ruta).convert("RGB")
    if im.height > alto_max:
        im = im.crop((0, 0, im.width, alto_max))
    im.thumbnail((900, 900))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def ojos_diferencias(orig, gen):
    """Qwen con ojos: diferencias visibles entre original y clon (texto corto). La nota NO la pone él, la pone el verificador."""
    datos = {"model": MODELO_OJOS, "stream": False, "images": [_b64(orig), _b64(gen)],
             "prompt": "La imagen 1 es una sección de una web original y la imagen 2 es una copia. Di en español de 3 a 5 diferencias "
                       "VISIBLES y concretas de la copia respecto a la original (elementos que faltan o sobran, posición, tamaño, color, "
                       "disposición). Una por línea, empezando por '- '. No describas lo que es igual.",
             "options": {"temperature": 0, "seed": 42, "num_predict": 220}}
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(datos).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        t = json.loads(r.read())["response"]
    return [l.strip() for l in t.splitlines() if l.strip().startswith("-")][:5]


def medir_una(html, n, s, spec, ref_dir, med, out):
    """Mide SOLO la sección n: misma página, pero con las demás secciones ocultas -> página corta, ~10 veces más rápido.
    Se conservan los contenedores de alrededor (anchos, fondos), así que la sección se ve igual que en la página entera."""
    solo = html.replace("</head>", f'<style>[data-clon-sec]:not([data-clon-sec="{n}"]){{display:none!important}}</style></head>', 1)
    tmp = out / f"_sec_{n}.html"
    tmp.write_text(solo, encoding="utf-8")
    try:
        r = cmp.comparar({**spec, "secciones": [s]}, ref_dir, tmp, med)["secciones"].get(n)
    finally:
        tmp.unlink(missing_ok=True)
    return r or {"similitud": 0, "lista": 0, "escritorio": 0, "movil": 0, "diferencias": []}


def quitar_marca(html, libres_seed):
    """Fondos CSS con imágenes de la marca -> foto libre; <source> y srcset de la marca fuera."""
    cont = {"n": 0}

    def url(m):
        cont["n"] += 1
        return f'url("https://picsum.photos/seed/{libres_seed}bg{cont["n"]}/1600/1000")'
    html = re.sub(r'url\(\s*["\']?https?://[^"\')]+\.(?:jpe?g|png|webp|avif|gif)[^"\')]*["\']?\s*\)', url, html, flags=re.I)
    html = re.sub(r"<source\b[^>]*>", "", html, flags=re.I)
    html = re.sub(r'\s(?:srcset|sizes)="[^"]*"', "", html)
    return html


def plano_de(carpeta, n):
    """El plano medido de la sección (claude/sec_N.md, de auto_planos.py o escrito a mano), sin la línea de marca."""
    ruta = Path(carpeta) / "claude" / f"sec_{n}.md"
    if not ruta.exists():
        return ""
    return "\n".join(l for l in ruta.read_text(encoding="utf-8").splitlines() if not l.startswith("<!--")).strip()


# ---------------------------------------------------------------- principal
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opc = {k: int(v) for k, v in re.findall(r"--(umbral|lista|solo|intentos)=(\d+)", " ".join(sys.argv))}
    max_intentos = opc.get("intentos", 3)
    umbral, umbral_lista, solo = opc.get("umbral", 90), opc.get("lista", 90), opc.get("solo", 0)
    carpeta = Path(args[0]) if args else Path(((BASE.parent / "workspace") / "ultimo_analisis.txt").read_text(encoding="utf-8").strip())
    datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8"))
    ref_dir = Path(datos["carpeta_referencia"])
    spec = json.loads((ref_dir / "spec.json").read_text(encoding="utf-8"))
    out = carpeta / "construccion"
    ruta = out / "index.html"
    if not ruta.exists():
        log("No hay construccion/index.html: ejecuta antes 2_CREAR.")
        sys.exit(1)
    if not (carpeta / "claude").exists():           # análisis antiguo, de antes de que crear.py hiciera los planos
        try:
            import auto_planos
            auto_planos.generar_planos(carpeta)
        except Exception as ex:
            log(f"  (aviso planos: {ex})")
    if not (carpeta / "claude").exists():           # análisis antiguo, de antes de que crear.py hiciera los planos
        try:
            import auto_planos
            auto_planos.generar_planos(carpeta)
        except Exception as ex:
            log(f"  (aviso planos: {ex})")
    img_dir = out / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    med = out / "_medidas"
    secs = spec["secciones"][:solo] if solo else spec["secciones"]
    hay_ojos = ojos_ok()
    log(f"VERIFICAR - {datos['url']} · {len(secs)} secciones · aprobar con parecido >= {umbral}% y lista >= {umbral_lista}%"
        + ("" if hay_ojos else " · (sin Qwen con ojos)"))
    # la original tiene que estar fotografiada con el MISMO móvil que el clon: si la referencia es de otra herramienta
    # o de un motor antiguo (375 px en vez de 393), las notas de móvil no valen nada
    try:
        from PIL import Image
        from extraer import MOVIL
        ancho_ref = Image.open(ref_dir / "original_movil.png").width
        if ancho_ref != MOVIL[0]:
            log(f"  ⚠ la referencia de móvil mide {ancho_ref} px y el motor mide a {MOVIL[0]} px: las notas de móvil no son "
                f"fiables. Vuelve a analizar la web (python analizar.py {datos['url']} --sin-ojos)")
    except Exception:
        pass
    t0 = time.time()
    html = ruta.read_text(encoding="utf-8")
    log("  midiendo el clon entero...")
    medida = cmp.comparar(spec, ref_dir, ruta, med)["secciones"]
    estado, historial = {}, {}
    titulo = f"Clon de estudio · {datos['url']}"

    for i, s in enumerate(secs):
        n = s["n"]
        r = medida.get(n, {"similitud": 0, "escritorio": 0, "movil": 0, "lista": 0, "diferencias": ["no se pudo medir"]})
        pct = int(100 * i / len(secs))
        t = int(time.time() - t0)
        log(f"\n  [{'#' * (pct * 24 // 100)}{'-' * (24 - pct * 24 // 100)}] {pct:3d}%  sección {n} ({i + 1}/{len(secs)})  ({t // 60}:{t % 60:02d})")
        log(f"      parecido {r['similitud']}% (PC {r['escritorio']}%, móvil {r['movil']}%) · lista {r['lista']}%")
        copiar_imgs(n, ref_dir, med, img_dir)
        caja = bloque_seccion(html, n)
        codigo = html[caja[0]:caja[1]] if caja else ""
        historial[n] = [(codigo, r)]
        mejor = (codigo, r)
        aprobada = lambda x: x["similitud"] >= umbral and x["lista"] >= umbral_lista
        motivo = ""
        if s.get("escena"):
            motivo = "escena 3D/animada (va el vídeo)"
        elif not caja:
            motivo = "la sección no está en el clon"
        elif len(codigo) > MAX_CODIGO_QWEN and not aprobada(r):
            motivo = f"demasiado grande para Qwen 7B ({len(codigo) // 1000} KB)"
        intento = 0
        while not motivo and not aprobada(mejor[1]) and intento < max_intentos:
            intento += 1
            difs = list(mejor[1]["diferencias"])
            if hay_ojos and intento == 1:
                try:
                    vistas = ojos_diferencias(img_dir / f"orig_{n}_pc.png", img_dir / f"gen_{n}_pc.png")
                    difs += [f"(ojos) {v.lstrip('- ')}" for v in vistas]
                    log(f"      ojos: {len(vistas)} diferencias vistas")
                except Exception:
                    pass
            if not difs:
                difs = ["El parecido visual es bajo aunque las medidas coinciden: revisa espaciados (padding/margin), tamaños de las cajas y la posición de cada bloque."]
            lista = "\n".join(f"- {d}" for d in difs[:10])
            log(f"      Qwen repara (intento {intento}/{max_intentos}, {len(difs)} diferencias)")
            plano = plano_de(carpeta, n)
            nuevo = limpiar_respuesta(preguntar(f"SECCIÓN {n} (código actual):\n{mejor[0]}\n\n"
                                                + (f"PLANO MEDIDO DE LA ORIGINAL (referencia; si choca con las diferencias, mandan las diferencias):\n{plano}\n\n" if plano else "")
                                                + f"DIFERENCIAS MEDIDAS CONTRA LA ORIGINAL:\n{lista}\n\n"
                                                f"Devuelve la sección {n} completa corregida.", SISTEMA))
            fallo = respuesta_valida(nuevo, mejor[0], n)
            if fallo:
                log(f"      respuesta descartada ({fallo})")
                historial[n].append((nuevo, {**mejor[1], "similitud": 0, "lista": 0, "descartada": fallo}))
                continue
            prueba = html.replace(mejor[0], nuevo, 1)
            r2 = medir_una(prueba, n, s, spec, ref_dir, med, out)
            historial[n].append((nuevo, r2))
            log(f"      -> parecido {r2['similitud']}% · lista {r2['lista']}%")
            if r2["similitud"] + r2["lista"] > mejor[1]["similitud"] + mejor[1]["lista"]:
                html, mejor = prueba, (nuevo, r2)
                copiar_imgs(n, ref_dir, med, img_dir)
                ruta.write_text(html, encoding="utf-8")
        rr = mejor[1]
        est = ("escena (vídeo)" if s.get("escena") else "aprobada" if aprobada(rr) else f"para Claude{' · ' + motivo if motivo else ''}")
        estado[n] = {"nota": rr["similitud"], "pc": rr["escritorio"], "movil": rr["movil"], "lista": rr["lista"],
                     "diferencias": rr["diferencias"], "intentos": intento, "umbral": umbral, "estado": f"{est} · lista {rr['lista']}%"
                     if not est.startswith("escena") else est}
        ruta.write_text(html, encoding="utf-8")
        (out / "revision.html").write_text(revision_html(estado, ref_dir, img_dir, titulo), encoding="utf-8")

    # --- resumen
    normales = {n: e for n, e in estado.items() if not e["estado"].startswith("escena")}
    pend = [n for n, e in normales.items() if not e["estado"].startswith("aprobada")]
    media = round(sum(e["nota"] for e in normales.values()) / max(len(normales), 1))
    media_l = round(sum(e["lista"] for e in normales.values()) / max(len(normales), 1))
    L = [f"# Pendientes para Claude — {datos['url']}", "",
         f"Parecido medio {media}% · lista media {media_l}% · aprobadas {len(normales) - len(pend)}/{len(normales)} "
         f"(parecido >= {umbral}% y lista >= {umbral_lista}%)", "",
         "Nova: arregla el CÓDIGO de cada sección en construccion/index.html y apunta en correcciones.md el antes -> después.", ""]
    for n in pend:
        e = estado[n]
        L.append(f"## Sección {n}: parecido {e['nota']}% (PC {e['pc']}%, móvil {e['movil']}%) · lista {e['lista']}% · {e['estado']}")
        L += [f"- {d}" for d in e["diferencias"][:10]]
        L += [f"- imágenes: construccion/img/orig_{n}_pc.png vs gen_{n}_pc.png (y _movil)", ""]
    (out / "pendientes_nova.md").write_text("\n".join(L), encoding="utf-8")
    if not (out / "correcciones.md").exists():
        (out / "correcciones.md").write_text(f"# Correcciones de Nova — {datos['url']}\n\nSolo código: por sección, lo que dejó Qwen (antes), "
                                             "el código corregido (después) y las diferencias medidas.\n", encoding="utf-8")
    est_forense = {n: {**e, "estado": "aprobada" if e["estado"].startswith("aprobada") else e["estado"]} for n, e in estado.items()}
    escribir_forense(out, carpeta, datos, historial, est_forense, umbral)
    vestir_final(out, carpeta)
    final = out / "index_final.html"
    final.write_text(quitar_marca(final.read_text(encoding="utf-8"), carpeta.name[:10]), encoding="utf-8")
    shutil.rmtree(med, ignore_errors=True)
    if (carpeta / "interactividad.json").exists():      # Bloque 3: ¿el clon hace lo mismo que la original al pulsar?
        try:
            import probar_interacciones
            pct, bien, total, _ = probar_interacciones.probar(carpeta, "index_final.html")
            log(f"  interacciones: {bien} de {total} correctas ({pct} %) -> construccion/interacciones_prueba.md")
        except Exception as ex:
            log(f"  (aviso interacciones: {ex})")
    t = int(time.time() - t0)
    log(f"\n  [{'#' * 24}] 100%  terminado ({t // 60}:{t % 60:02d})")
    log("\n".join(L[:3]) + f"\n\nRevisión: {out / 'revision.html'}\nPendientes: {out / 'pendientes_nova.md'}\nFinal: {final}")


if __name__ == "__main__":
    main()

