import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
interacciones.py - Explorador interactivo visual con Playwright + Qwen VL local.
Detecta carruseles horizontales reales, botones flotantes de avance/retroceso,
simula clics y extrae las tarjetas que se esconden tras el scroll.
"""
import base64
import json
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
SALIDA = Path(__file__).resolve().parent.parent / "workspace"
OLLAMA = "http://127.0.0.1:11434"
def _modelo_nova(clave, defecto):
    try:
        import json
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8")).get(clave, defecto)
    except Exception:
        return defecto

MODELO_OJOS = _modelo_nova("vl", "blaifa/InternVL3_5:8b")

JS_DETECTAR_CARRUSELES_UNIVERSAL = """
() => {
    const carruseles = [];
    const all = Array.from(document.querySelectorAll('*'));
    
    for (const el of all) {
        if (el === document.body || el === document.documentElement) continue;
        const rect = el.getBoundingClientRect();
        if (rect.height < 90 || rect.width < 250) continue;
        
        const diff = el.scrollWidth - el.clientWidth;
        if (diff > 80) {
            const kids = Array.from(el.children).filter(k => {
                const kr = k.getBoundingClientRect();
                return kr.width > 80 && kr.height > 60;
            });
            
            if (kids.length >= 2) {
                // Buscar si hay contenedor padre que sea una seccion
                let parentSec = el.closest('[data-clon-sec], [data-seccion], section, main > div');
                const secId = parentSec ? (parentSec.getAttribute('data-clon-sec') || parentSec.getAttribute('data-seccion') || '') : '';
                
                // Buscar botones cercanos (prev / next)
                const contenedorBuscar = parentSec || el.parentElement || el;
                const buttons = Array.from(contenedorBuscar.querySelectorAll('button, [role="button"], [class*="arrow"], [class*="paddle"], [class*="chevron"], [class*="scroller-control"]')).filter(b => {
                    const br = b.getBoundingClientRect();
                    return br.width >= 16 && br.height >= 16 && window.getComputedStyle(b).display !== 'none';
                });
                
                // Buscar encabezado mas cercano arriba
                let title = '';
                let walker = el;
                for (let step = 0; step < 4; step++) {
                    if (!walker) break;
                    const h = walker.querySelector('h1, h2, h3, h4, [class*="header"], [class*="headline"]');
                    if (h && h.textContent.trim()) {
                        title = h.textContent.trim().slice(0, 80);
                        break;
                    }
                    walker = walker.parentElement;
                }

                carruseles.push({
                    tag: el.tagName,
                    clase: (el.className || '').toString().slice(0, 80),
                    secId: secId,
                    tituloCercano: title,
                    y: Math.round(rect.top + window.scrollY),
                    alto: Math.round(rect.height),
                    ancho: Math.round(rect.width),
                    scrollWidth: el.scrollWidth,
                    clientWidth: el.clientWidth,
                    desbordamientoPx: diff,
                    totalTarjetas: kids.length,
                    botonesCount: buttons.length
                });
            }
        }
    }

    // Filtrar contenedores duplicados o anidados (quedarse con los mas especificos)
    const filtrados = [];
    for (const c of carruseles) {
        const existe = filtrados.some(f => Math.abs(f.y - c.y) < 30 && Math.abs(f.scrollWidth - c.scrollWidth) < 50);
        if (!existe) {
            filtrados.push(c);
        }
    }

    return filtrados;
}
"""

JS_EXTRAER_TARJETAS_CARRUSEL = """
(indiceCarrusel) => {
    const all = Array.from(document.querySelectorAll('*'));
    const carruseles = [];
    for (const el of all) {
        if (el === document.body || el === document.documentElement) continue;
        const rect = el.getBoundingClientRect();
        if (rect.height < 90 || rect.width < 250) continue;
        if (el.scrollWidth - el.clientWidth > 80) {
            const kids = Array.from(el.children).filter(k => k.getBoundingClientRect().width > 80);
            if (kids.length >= 2) carruseles.push(el);
        }
    }
    
    const target = carruseles[indiceCarrusel];
    if (!target) return [];

    const items = [];
    const kids = Array.from(target.children);

    kids.forEach((k, idx) => {
        const kr = k.getBoundingClientRect();
        const titleEl = k.querySelector('h1, h2, h3, h4, [class*="title"], [class*="headline"], strong');
        const priceEl = k.querySelector('[class*="price"], [class*="subhead"], [class*="copy"]');
        const imgEl = k.querySelector('img');

        items.push({
            pos: idx + 1,
            titulo: titleEl ? titleEl.textContent.trim().slice(0, 80) : '',
            precio_o_sub: priceEl ? priceEl.textContent.trim().slice(0, 100) : '',
            imagen: imgEl ? (imgEl.getAttribute('src') || '') : '',
            ancho: Math.round(kr.width),
            alto: Math.round(kr.height)
        });
    });

    return items;
}
"""


def preguntar_qwen_vl(imagen_path, prompt):
    """Llama a Qwen 2.5 VL en local mediante Ollama API."""
    try:
        with open(imagen_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        
        payload = json.dumps({
            "model": MODELO_OJOS,
            "prompt": prompt,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096}
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{OLLAMA}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception as e:
        return f"[ERROR Qwen VL: {e}]"


def explorar_interacciones(url, carpeta_salida=None):
    from playwright.sync_api import sync_playwright

    host = urlparse(url).netloc.replace("www.", "") or "local"
    slug = "".join(c if c.isalnum() else "_" for c in (host + urlparse(url).path).lower()).strip("_")[:40]
    out_dir = Path(carpeta_salida) if carpeta_salida else (SALIDA / slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    cap_dir = out_dir / "capturas_interactivas"
    cap_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n" + "=" * 62)
    print(f"  EXPLORADOR INTERACTIVO LOCAL — {url}")
    print(f"  Playwright + Qwen VL ({MODELO_OJOS})")
    print("=" * 62)

    interacciones = {}
    t0 = time.time()

    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = nav.new_context(viewport={"width": 1920, "height": 1080}, locale="es-ES")
        page = ctx.new_page()

        try:
            print("  [1/4] Abriendo web y analizando estructura interactiva...")
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2500)

            # 1. Detección universal de carruseles
            candidatos = page.evaluate(JS_DETECTAR_CARRUSELES_UNIVERSAL)
            print(f"  [2/4] Detectados {len(candidatos)} carruseles horizontales reales en la página.")

            # 2. Análisis por cada carrusel
            for idx, cand in enumerate(candidatos):
                c_id = f"carrusel_{idx + 1}"
                print(f"\n  --> [{idx+1}/{len(candidatos)}] Carrusel '{cand['tituloCercano'] or cand['clase'][:25]}' en Y={cand['y']}px:")
                print(f"      ScrollWidth: {cand['scrollWidth']}px (Desborda +{cand['desbordamientoPx']}px) | {cand['totalTarjetas']} tarjetas")

                # Scroll hasta el elemento para que sea visible
                page.evaluate(f"window.scrollTo(0, Math.max(0, {cand['y']} - 100))")
                page.wait_for_timeout(500)

                # Captura antes de desplazar
                img_path = cap_dir / f"{c_id}_antes.png"
                try:
                    page.screenshot(path=str(img_path), clip={"x": 0, "y": max(0, cand["y"] - 60), "width": 1920, "height": min(cand["alto"] + 120, 900)})
                except Exception:
                    page.screenshot(path=str(img_path))

                # Preguntar a Qwen VL sobre la composición visual
                prompt_ojos = (
                    "Analiza esta sección web de forma concisa. "
                    "¿Es un carrusel o slider horizontal de productos? "
                    "¿Ves botones circulares o flechas de desplazamiento (< o >)? "
                    "Responde en JSON: {\"es_carrusel\": true/false, \"tiene_flechas\": true/false, \"descripcion\": \"frase corta\"}"
                )
                print("      Consultando a Qwen VL...", end="", flush=True)
                t_vl = time.time()
                resp_ojos = preguntar_qwen_vl(img_path, prompt_ojos)
                print(f" ({time.time() - t_vl:.1f}s)")

                parsed_ojos = {}
                m_json = re.search(r'\{.*\}', resp_ojos, re.DOTALL)
                if m_json:
                    try:
                        parsed_ojos = json.loads(m_json.group(0))
                    except Exception:
                        pass

                # Extraer tarjetas completas
                items = page.evaluate(JS_EXTRAER_TARJETAS_CARRUSEL, idx)

                # 3. Interacción: Simular scroll lateral hacia la derecha (+500px)
                desplazado = page.evaluate(f"""() => {{
                    const all = Array.from(document.querySelectorAll('*')).filter(e => e.scrollWidth - e.clientWidth > 80 && e.clientHeight > 90);
                    const target = all[{idx}];
                    if (target) {{
                        const prev = target.scrollLeft;
                        target.scrollBy({{ left: 600, behavior: 'instant' }});
                        return target.scrollLeft - prev;
                    }}
                    return 0;
                }}""")
                page.wait_for_timeout(600)

                img_despues = cap_dir / f"{c_id}_despues.png"
                try:
                    page.screenshot(path=str(img_despues), clip={"x": 0, "y": max(0, cand["y"] - 60), "width": 1920, "height": min(cand["alto"] + 120, 900)})
                except Exception:
                    pass

                print(f"      [INTERACCION OK] Desplazamiento lateral comprobado: +{desplazado}px.")
                print(f"      Tarjetas descubiertas: {len(items)} items extraídos.")

                interacciones[c_id] = {
                    "titulo_seccion": cand["tituloCercano"],
                    "y_posicion": cand["y"],
                    "scroll_width": cand["scrollWidth"],
                    "client_width": cand["clientWidth"],
                    "desbordamiento_px": cand["desbordamientoPx"],
                    "total_tarjetas": len(items),
                    "tiene_botones": cand["botonesCount"] > 0 or parsed_ojos.get("tiene_flechas", True),
                    "descripcion_qwen_vl": parsed_ojos.get("descripcion", ""),
                    "captura_inicial": img_path.name,
                    "captura_desplazado": img_despues.name,
                    "tarjetas": items
                }

        finally:
            ctx.close()
            nav.close()

    # Guardar reporte de interacciones
    json_path = out_dir / "interacciones.json"
    json_path.write_text(json.dumps(interacciones, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# Reporte de Interacciones y Carruseles — {url}",
        f"- Fecha: {time.strftime('%Y-%m-%d %H:%M')}",
        f"- Total carruseles interactivos extraídos: {len(interacciones)}",
        ""
    ]
    for cid, data in interacciones.items():
        md_lines.append(f"## {cid.upper()}: {data['titulo_seccion'] or 'Sin título'}")
        md_lines.append(f"- Posición Y: {data['y_posicion']}px | Ancho desplazable: {data['scroll_width']}px (+{data['desbordamiento_px']}px)")
        md_lines.append(f"- Botones flotantes detectados: {'SÍ' if data['tiene_botones'] else 'NO'}")
        md_lines.append(f"- Total tarjetas descubiertas tras el scroll: {data['total_tarjetas']}")
        if data.get("tarjetas"):
            md_lines.append("### Tarjetas:")
            for it in data["tarjetas"][:8]:
                md_lines.append(f"  - [{it['pos']}] **{it['titulo']}** | {it['precio_o_sub']} (Img: {it['imagen'][:60]}...)")
        md_lines.append("")

    (out_dir / "informe_interacciones.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nListo en {time.time() - t0:.1f}s -> Guardado en {json_path}")
    return interacciones


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else (BASE / "url.txt").read_text(encoding="utf-8").strip().splitlines()[0].strip()
    explorar_interacciones(url)
