"""
NOVA PIPELINE LOCAL v1.0 (Capa 0 Obrero Local - 0 Tokens Nube)
==============================================================
Orquestador de Doble Contexto segun Ley 2 y Ley 14 de GEMINI.md:
- Contexto 1 (Sintaxis y Logica): Qwen 3.5 pica + linter local (Biome/Ruff en orquestador.py)
  en bucle cerrado de hasta 3 intentos a 0 warnings.
- Contexto 2 (Vision y Maquetacion): Playwright toma capturas (1280px, 375px y secciones),
  evalua desbordes en DOM (scrollWidth > innerWidth) e InternVL 3.5 audita contra el contrato.
- Embudo de Desacoplamiento (nova_pendiente.txt): Si tras 3 intentos en Contexto 1 o 2 persiste
  un fallo, se detiene forzosamente y vuelca el error exacto a nova_pendiente.txt sin fallback.
- Reporte Consolidado: Si todo pasa, genera reporte_final_ok.json para lectura en 1 llamada.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Inyectar rutas de modulos base de Nova
RUTA_SCRIPTS = Path(__file__).resolve().parent
RUTA_GEMINI = RUTA_SCRIPTS.parent.parent
RUTA_NOVA_CORE = RUTA_GEMINI / "nova_core"
RUTA_MEMORY = RUTA_GEMINI / "antigravity" / "memory"

sys.path.insert(0, str(RUTA_NOVA_CORE))
# Sin nova_core NO hay pipeline: antes se sustituia por funciones que decian "limpio" siempre (aprobado en falso).
ERROR_IMPORT: Exception | None = None
try:
    from ollama_comun import ensure_ollama_service, generar_qwen
    from orquestador import avisos_para_modelo, revisar
except ImportError as e:
    ERROR_IMPORT = e


def cargar_modelos() -> tuple[str, str]:
    """Carga los nombres oficiales de los modelos desde nova_modelos.json."""
    ruta_cfg = RUTA_SCRIPTS / "nova_modelos.json"
    coder = "qwen3.5:9b"
    vl = "blaifa/InternVL3_5:8b"
    if ruta_cfg.exists():
        try:
            cfg = json.loads(ruta_cfg.read_text(encoding="utf-8"))
            coder = cfg.get("coder", coder)
            vl = cfg.get("vl", vl)
        except Exception:
            pass
    return coder, vl


def limpiar_codigo_markdown(texto: str) -> str:
    """Extrae el codigo puro de un bloque markdown si viene envuelto en comillas triples."""
    m = re.search(r"```(?:[a-zA-Z0-9_\-\+]+)?\s*\n(.*?)\n```", texto, re.DOTALL)
    if m:
        return m.group(1).strip()
    return texto.strip()


def consultar_qwen(
    prompt: str,
    modelo: str,
    instrucciones_sistema: str | None = None,
    timeout: int = 900,
) -> str:
    """Invoca a qwen3.5:9b local via la API de Ollama (/api/chat)."""
    if not instrucciones_sistema:
        instrucciones_sistema = (
            "Eres un programador senior de elite bajo filosofia KISS 2026. "
            "Genera codigo conciso, estructurado con early returns, sin comentarios innecesarios "
            "y estrictamente funcional. Devuelve EXCLUSIVAMENTE el codigo sin texto introductorio ni conclusiones."
        )

    # generar_qwen: sin modo "pensar", contexto de 24k y modelo cargado entre vueltas. Antes iba con el contexto por
    # defecto de Ollama (4096) y el modo "pensar" encendido: la web de prueba del 08/11 salio cortada a mitad del CSS.
    msg, cortado = generar_qwen(prompt, modelo, sistema=instrucciones_sistema, timeout=timeout)
    if cortado:
        raise RuntimeError(
            "Qwen agoto los tokens: la respuesta salio CORTADA (archivo incompleto). "
            "Divide el contrato en partes mas pequenas."
        )
    return limpiar_codigo_markdown(msg)


def auditar_con_internvl(
    ruta_imagen: Path,
    criterios: str,
    modelo_vl: str,
    timeout: int = 180,
) -> tuple[bool, str]:
    """Envia una captura a InternVL 3.5 local para auditar desbordes, colisiones y estetica."""
    if not ruta_imagen.is_file():
        return False, f"No existe la imagen: {ruta_imagen}"

    img_b64 = base64.b64encode(ruta_imagen.read_bytes()).decode("utf-8")

    prompt = (
        "Eres el auditor visual de interfaces de Nova (InternVL 3.5 local). "
        f"Criterios de aceptacion del contrato: '{criterios}'. "
        "Examina la imagen con precision quirurgica buscando: "
        "1. Desbordes horizontales o contenido recortado lateralmente. "
        "2. Textos colisionados, solapados o ilegibles. "
        "3. Coherencia estetica y espaciados limpios. "
        "4. Contenido real: textos, titulos, botones o imagenes visibles. Una pagina en blanco, vacia o solo con "
        "un color de fondo se RECHAZA siempre. "
        "Responde ESTRICTAMENTE con este formato: "
        "CONTENIDO: [VISIBLE | VACIO]\n"
        "DESBORDES: [NINGUNO | DETECTADOS]\n"
        "COLISIONES: [NINGUNO | DETECTADAS]\n"
        "VEREDICTO: [APROBADO | RECHAZADO]\n"
        "DETALLES: [Breve explicacion de 1 linea]"
    )

    payload = {
        "model": modelo_vl,
        "prompt": prompt,
        "images": [img_b64],
        "options": {"temperature": 0.05},
        "stream": False,
    }

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        respuesta = res.get("response", "").strip()

    # solo vale un veredicto explicito y con contenido visible (antes bastaba "sin desbordes": una pagina en blanco
    # no tiene desbordes y pasaba)
    r = respuesta.upper()
    aprobado = "VEREDICTO: APROBADO" in r and "CONTENIDO: VACIO" not in r
    return aprobado, respuesta


# Una carpeta por tarea: <carpeta del proyecto>\nova_tareas\<fecha>_<proyecto>\ con contrato, capturas, reporte o
# pendiente. Antes reporte_final_ok.json / nova_pendiente.txt eran UNICOS: dos tareas seguidas se pisaban.
# En memory\ queda una copia del ultimo, con la ruta de su carpeta ("carpeta_tarea").
CARPETA_TAREA: Path | None = None


def preparar_carpeta_tarea(contrato: dict, ruta_contrato: Path) -> Path:
    archivo = Path(contrato.get("archivo_objetivo", ruta_contrato)).resolve()
    nombre = re.sub(r"[^a-z0-9]+", "_", str(contrato.get("proyecto", "tarea")).lower()).strip("_")[:40] or "tarea"
    carpeta = archivo.parent / "nova_tareas" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nombre}"
    (carpeta / "capturas").mkdir(parents=True, exist_ok=True)
    shutil.copy(ruta_contrato, carpeta / "contrato_diseno.json")
    return carpeta


def volcar_freno_pendiente(
    fase: str,
    archivo: Path,
    intentos: int,
    detalles: str,
    ruta_capturas: Path | None = None,
) -> None:
    """Escribe el fallo en nova_pendiente.txt y detiene el pipeline (Circuit Breaker)."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    contenido = [
        "=" * 70,
        f"[CIRCUIT BREAKER - FALLO EN {fase}]",
        f"Fecha: {stamp}",
        f"Archivo objetivo: {archivo}",
        f"Intentos agotados: {intentos}/3",
        f"Detalles del fallo:\n{detalles}",
    ]
    if ruta_capturas and ruta_capturas.exists():
        contenido.append(f"Capturas de auditoria conservadas en: {ruta_capturas}")
    contenido.append("ACCION REQUERIDA: Notificar a el usuario en 1 llamada. Cirugia manual edit_file <= 35% previa autorizacion.")
    contenido.append("=" * 70 + "\n")

    if CARPETA_TAREA:
        contenido.insert(-1, f"Carpeta de la tarea: {CARPETA_TAREA}")
    texto_freno = "\n".join(contenido)

    # En la carpeta de la tarea (o en el directorio actual si aun no existe) y una copia en memory
    (CARPETA_TAREA or Path(".")).joinpath("nova_pendiente.txt").write_text(texto_freno, encoding="utf-8")
    if RUTA_MEMORY.exists():
        (RUTA_MEMORY / "nova_pendiente.txt").write_text(texto_freno, encoding="utf-8")

    print("\n" + texto_freno)


# ---------- Correccion por trozos ----------
# Qwen devuelve SOLO lo que cambia, y se aplica si el texto viejo aparece exactamente una vez (como editar_archivo
# del orquestador). Si no da ningun bloque aplicable, quien llama decide (regenerar o frenar).
FORMATO_BLOQUES = (
    "Devuelve SOLO bloques de cambio, uno por cada cambio, con este formato exacto y sin el archivo entero:\n"
    "<<<<<<< BUSCAR\n<texto que hay ahora, copiado exacto, unas pocas lineas>\n=======\n<texto nuevo>\n>>>>>>> FIN\n"
    "No escribas nada mas fuera de los bloques."
)
RE_BLOQUE = re.compile(r"<<<<<<< BUSCAR\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>> FIN", re.S)


def aplicar_bloques(texto: str, respuesta: str) -> tuple[str, int, list[str]]:
    aplicados, fallos = 0, []
    for buscar, nuevo in RE_BLOQUE.findall(respuesta):
        veces = texto.count(buscar)
        if veces == 1:
            texto = texto.replace(buscar, nuevo, 1)
            aplicados += 1
        else:
            fallos.append(f"texto viejo encontrado {veces} veces: {buscar[:60]!r}")
    return texto, aplicados, fallos


def corregir_por_bloques(archivo: Path, fallo: str, modelo: str) -> tuple[bool, str]:
    contenido = archivo.read_text(encoding="utf-8", errors="ignore")
    prompt = (
        f"Archivo {archivo.name}:\n```\n{contenido}\n```\n\n"
        f"Fallos detectados que tienes que corregir:\n{fallo}\n\n{FORMATO_BLOQUES}"
    )
    try:
        respuesta, cortado = generar_qwen(prompt, modelo, sistema="Eres un programador senior. Corriges solo lo necesario.")
    except Exception as e:
        return False, f"Qwen no respondio a la correccion por trozos: {e}"
    if cortado:
        return False, "la correccion por trozos salio cortada"
    nuevo, n, fallos = aplicar_bloques(contenido, respuesta)
    if not n:
        return False, "Qwen no devolvio ningun cambio aplicable" + (f" ({'; '.join(fallos[:3])})" if fallos else "")
    archivo.write_text(nuevo, encoding="utf-8")
    return True, f"{n} cambio(s) aplicados por trozos" + (f", {len(fallos)} descartados" if fallos else "")


VACIAS_HTML = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def revisar_estructura_html(codigo: str) -> list[str]:
    """El orquestador no tiene linter de HTML (devolvia "limpio" sin mirar): esto comprueba lo minimo para que la
    pagina exista de verdad. Una web cortada a mitad del <style> (08/11) da varios problemas aqui."""
    from html.parser import HTMLParser

    problemas: list[str] = []
    bajo = codigo.lower()
    if "</html>" not in bajo:
        problemas.append("falta </html>: el archivo esta CORTADO o incompleto")
    if "<body" not in bajo:
        problemas.append("no hay <body>: la pagina no tiene contenido")

    class Pila(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.pila: list[tuple[str, int]] = []
            self.texto: list[str] = []
            self.en: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag not in VACIAS_HTML:
                self.pila.append((tag, self.getpos()[0]))
            self.en.append(tag)

        def handle_endtag(self, tag):
            for i in range(len(self.pila) - 1, -1, -1):
                if self.pila[i][0] == tag:
                    del self.pila[i:]
                    break

        def handle_data(self, data):
            if self.pila and self.pila[-1][0] not in ("style", "script", "title", "head"):
                self.texto.append(data.strip())

    p = Pila()
    p.feed(codigo)
    abiertas = [f"<{t}> (linea {n})" for t, n in p.pila if t not in ("p", "li", "td", "tr", "option")]
    if abiertas:
        problemas.append("etiquetas sin cerrar: " + ", ".join(abiertas[:8]))
    if len(" ".join(t for t in p.texto if t)) < 80:
        problemas.append("la pagina casi no tiene texto visible (menos de 80 caracteres)")
    return problemas


def ejecutar_contexto_1(
    contrato: dict,
    modelo_coder: str,
    max_intentos: int = 3,
) -> tuple[bool, int, str]:
    """Contexto 1: Qwen pica codigo y resuelve avisos de linter en bucle de hasta 3 intentos."""
    archivo_obj = Path(contrato["archivo_objetivo"]).resolve()
    archivo_obj.parent.mkdir(parents=True, exist_ok=True)

    instrucciones = contrato.get("instrucciones", "")
    cfg_c1 = contrato.get("contexto_1", {})
    criterios = cfg_c1.get("criterios", "Filosofia KISS, early returns, 0 warnings")
    lenguaje = cfg_c1.get("lenguaje", archivo_obj.suffix.lstrip("."))

    prompt_base = (
        f"Tarea de programacion para el archivo: {archivo_obj.name}\n"
        f"Lenguaje: {lenguaje}\n"
        f"Criterios de calidad: {criterios}\n\n"
        f"Instrucciones especificas:\n{instrucciones}\n"
    )

    if archivo_obj.exists():
        contenido_previo = archivo_obj.read_text(encoding="utf-8", errors="ignore")
        if contenido_previo.strip():
            prompt_base += f"\nContenido actual del archivo:\n```\n{contenido_previo}\n```\n"

    ultimo_error = ""
    reparable = False  # True si el archivo esta entero y solo quedan avisos del linter: se corrige por trozos

    # modo "verificar": la web ya la monto la biblioteca (montar.py). Qwen NO la regenera: solo se comprueba.
    if contrato.get("modo") == "verificar":
        if not archivo_obj.exists():
            return False, 0, f"modo verificar: no existe {archivo_obj}"
        codigo = archivo_obj.read_text(encoding="utf-8", errors="ignore")
        if archivo_obj.suffix.lower() in (".html", ".htm"):
            problemas = revisar_estructura_html(codigo)
            if problemas:
                return False, 1, "Estructura HTML (web montada):\n- " + "\n- ".join(problemas)
        return True, 1, "Web montada con la biblioteca de Nova: estructura HTML completa"

    for vuelta in range(1, max_intentos + 1):
        codigo = None
        if reparable:
            # correccion por trozos (texto viejo -> texto nuevo); si Qwen no da bloques aplicables, se regenera entero
            print(f"[CONTEXTO 1] Vuelta {vuelta}/{max_intentos} - Qwen corrigiendo por trozos...")
            ok_b, info = corregir_por_bloques(archivo_obj, ultimo_error, modelo_coder)
            print(f"[CONTEXTO 1] {info}")
            if ok_b:
                codigo = archivo_obj.read_text(encoding="utf-8", errors="ignore")

        if codigo is None:
            print(f"[CONTEXTO 1] Vuelta {vuelta}/{max_intentos} - Qwen generando codigo...")
            prompt_actual = prompt_base if vuelta == 1 else (
                f"{prompt_base}\n\n"
                f"ATENCION: En el intento anterior se detectaron estos fallos:\n"
                f"{ultimo_error}\n"
                "Corrige estos fallos de forma estricta. Devuelve el archivo completo corregido."
            )
            try:
                codigo = consultar_qwen(prompt_actual, modelo=modelo_coder)
            except Exception as e:
                ultimo_error = f"Error invocando Ollama Qwen: {e}"
                reparable = False
                continue
            if not codigo:
                ultimo_error = "Qwen devolvio una respuesta vacia."
                reparable = False
                continue
            # Escribir codigo en disco
            archivo_obj.write_text(codigo, encoding="utf-8")
        reparable = False

        # HTML: estructura minima (el orquestador no tiene linter de HTML y antes daba "limpio" sin mirar nada)
        es_html = archivo_obj.suffix.lower() in (".html", ".htm")
        if es_html:
            problemas = revisar_estructura_html(codigo)
            if problemas:
                ultimo_error = "Estructura HTML:\n- " + "\n- ".join(problemas)
                print(f"[CONTEXTO 1] Vuelta {vuelta} - {ultimo_error}")
                continue

        # Pasar linter / formateador de orquestador.py. Si el linter FALLA, es un fallo (antes contaba como limpio).
        print(f"[CONTEXTO 1] Vuelta {vuelta}/{max_intentos} - Validando con linter local...")
        try:
            resultado_lint = revisar(str(archivo_obj), autofix=True)
        except Exception as e:
            ultimo_error = f"El linter no pudo ejecutarse: {e}"
            print(f"[CONTEXTO 1] Vuelta {vuelta} - {ultimo_error}")
            continue
        avisos = resultado_lint.get("avisos", [])
        sin_linter = "sin linter" in str(resultado_lint.get("linter", ""))

        if not avisos:
            detalle = (
                "Estructura HTML completa (no hay linter de estilo para HTML)"
                if es_html and sin_linter
                else "Sin linter para este tipo de archivo: NO revisado"
                if sin_linter
                else "Linter limpio (0 warnings)"
            )
            print(f"[CONTEXTO 1 OK] Vuelta {vuelta}: {detalle}.")
            return True, vuelta, detalle

        ultimo_error = avisos_para_modelo(resultado_lint)
        reparable = True  # el archivo esta entero: la siguiente vuelta corrige por trozos
        print(f"[CONTEXTO 1] Vuelta {vuelta} detecto avisos:\n{ultimo_error}")

    return False, max_intentos, ultimo_error


# Avisos que no frenan pero tienen que salir en el reporte (p. ej. overflow-x: hidden tapando desbordes)
AVISOS: set[str] = set()

# Chequeo objetivo en el navegador, antes de preguntar a InternVL:
# - desbordes elemento a elemento: un elemento que se sale por la derecha cuenta aunque html/body tengan
#   overflow-x: hidden (eso los tapa, no los arregla); no cuentan los que estan dentro de un contenedor que recorta
#   a proposito (carruseles, marquesinas);
# - secciones del contrato: que existan, midan algo y tengan contenido;
# - texto visible en la pagina (una pagina en blanco no tiene desbordes y antes pasaba).
JS_CHEQUEO_DOM = r"""(selectores) => {
  const vw = innerWidth;
  const recorta = (e) => { for (let p = e.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement)
    if (getComputedStyle(p).overflowX !== 'visible') return true; return false; };
  const nombre = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList[0] ? '.' + e.classList[0] : '');
  const fuera = [];
  for (const e of document.body.querySelectorAll('*')) {
    const r = e.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && r.right > vw + 1 && !recorta(e)) { fuera.push(nombre(e) + ' +' + Math.round(r.right - vw) + 'px'); if (fuera.length >= 6) break; }
  }
  const ox = (e) => getComputedStyle(e).overflowX;
  const secciones = (selectores || []).map(s => { let e = null; try { e = document.querySelector(s); } catch (x) {}
    if (!e) return [s, 'no existe'];
    const r = e.getBoundingClientRect();
    if (r.height < 20) return [s, 'mide ' + Math.round(r.height) + 'px de alto'];
    if ((e.innerText || '').trim().length < 3 && !e.querySelector('img, svg, video, canvas, picture, iframe')) return [s, 'esta vacia'];
    return [s, 'ok']; });
  const visible = (document.body ? document.body.innerText : '').trim();
  // 08/11 (landing gym): fotos rotas, textos cortados, cajas de color vacias y hero sin titular pasaban como "OK"
  const vis = (e) => { const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05; };
  const rotas = [...document.images].filter(i => vis(i) && (!i.getAttribute('src') || (i.complete && i.naturalWidth === 0)))
    .map(i => (i.getAttribute('src') || '(sin src)').slice(-50));
  const cortados = [];
  for (const e of document.body.querySelectorAll('h1,h2,h3,h4,p,li,a,span,div')) {
    if (!vis(e) || !(e.innerText || '').trim() || e.children.length > 3 || e.getBoundingClientRect().width < 4) continue;
    if (e.closest('[data-efecto="titular"], .ef-zoom__fijo, .ef-hz__fijo, .ef-video__fijo')) continue;  // recorte a proposito del kit de efectos
    const s = getComputedStyle(e);
    const ocultaY = ['hidden', 'clip'].includes(s.overflowY) || ['hidden', 'clip'].includes(s.overflow);
    if (ocultaY && e.scrollHeight > e.clientHeight + 4 && s.webkitLineClamp === 'none') { cortados.push(nombre(e) + ' "' + e.innerText.trim().slice(0, 30) + '"'); if (cortados.length >= 6) break; }
  }
  const fondo = (e) => getComputedStyle(e).backgroundColor;
  const vacias = [];
  for (const e of document.body.querySelectorAll('div,section,article,figure,li,a')) {
    const r = e.getBoundingClientRect();
    if (!vis(e) || r.width < 120 || r.height < 80 || e.closest('[aria-hidden="true"]')) continue;  // decorativo: no cuenta
    const bg = fondo(e), pbg = e.parentElement ? fondo(e.parentElement) : '';
    const conColor = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== pbg || getComputedStyle(e).backgroundImage !== 'none' && false;
    if (conColor && !(e.innerText || '').trim() && !e.querySelector('img, svg, video, canvas, picture, iframe') && getComputedStyle(e).backgroundImage === 'none') {
      vacias.push(nombre(e) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); if (vacias.length >= 8) break; }
  }
  // contraste texto/fondo (08/11 gym por secciones: botones y titulos del mismo color que su fondo = invisibles)
  const rgb = (c) => { const n = (c.match(/[\d.]+/g) || []).map(Number);  // color-mix() sale como "color(srgb 0-1 0-1 0-1 / a)"
    return c.startsWith('color(') ? [n[0] * 255, n[1] * 255, n[2] * 255, ...(n.length > 3 ? [n[3]] : [])] : n; };
  const lum = ([r, g, b]) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const fondoReal = (e) => { for (let p = e; p; p = p.parentElement) { const c = rgb(getComputedStyle(p).backgroundColor);
    if (c.length >= 3 && (c.length < 4 || c[3] > 0.5)) return c.slice(0, 3); } return [255, 255, 255]; };
  const ilegibles = [];
  for (const e of document.body.querySelectorAll('h1,h2,h3,h4,p,li,a,button,span,td,th,small,strong')) {
    const propio = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!propio || !vis(e) || e.getBoundingClientRect().width < 4) continue;
    const c = rgb(getComputedStyle(e).color), f = fondoReal(e);
    if (c.length >= 4 && c[3] < 0.5) continue;
    const L1 = lum(c.slice(0, 3)), L2 = lum(f), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const grande = parseFloat(getComputedStyle(e).fontSize) >= 24;
    if (ratio < (grande ? 2.2 : 3)) { ilegibles.push(nombre(e) + ' "' + e.innerText.trim().slice(0, 25) + '" ' + ratio.toFixed(1) + ':1'); if (ilegibles.length >= 8) break; }
  }
  const h1 = [...document.querySelectorAll('h1')].find(h => vis(h) && (h.innerText || '').trim().length > 1);
  return { fuera, secciones, texto: visible.length, textoVisible: visible.slice(0, 8000), rotas, cortados, vacias, ilegibles, sin_titulo: !h1,
           tapado: ['hidden', 'clip'].includes(ox(document.documentElement)) || ['hidden', 'clip'].includes(ox(document.body)) };
}"""


def problemas_dom(dom: dict, vista: str) -> list[str]:
    """Lo que el navegador midio y es un fallo (no una opinion)."""
    out = []
    if dom.get("texto", 0) < 80:
        out.append(f"{vista}: la pagina casi no tiene texto visible ({dom.get('texto', 0)} caracteres).")
    malas = [f"{s} ({estado})" for s, estado in dom.get("secciones", []) if estado != "ok"]
    if malas:
        out.append(f"{vista}: secciones del contrato que faltan o estan vacias: {', '.join(malas)}.")
    if dom.get("fuera"):
        out.append(f"{vista}: elementos que se salen por la derecha: {', '.join(dom['fuera'])}.")
    if dom.get("rotas"):
        out.append(f"{vista}: {len(dom['rotas'])} imagen(es) rota(s) o sin archivo: {', '.join(dom['rotas'][:4])}. "
                   "Usa fotos reales de la carpeta o quita la imagen; nunca rutas inventadas.")
    if dom.get("cortados"):
        out.append(f"{vista}: textos cortados por su caja (overflow): {', '.join(dom['cortados'][:4])}.")
    if dom.get("vacias"):
        out.append(f"{vista}: cajas de color sin contenido: {', '.join(dom['vacias'][:4])}.")
    if dom.get("ilegibles"):
        out.append(f"{vista}: texto casi invisible por poco contraste con su fondo: {', '.join(dom['ilegibles'][:5])}.")
    if dom.get("sin_titulo"):
        out.append(f"{vista}: la pagina no tiene un titular h1 visible (el hero debe decir que es el negocio).")
    encontrados = {m.group(0)[:50] for m in RE_RELLENO.finditer(dom.get("textoVisible", ""))}
    # [EN MAYUSCULAS] = dato pendiente marcado a proposito (biblioteca / [PENDIENTE]): aviso, no fallo.
    # Mezcla de mayusculas y minusculas ("[Mapa Vectorial Estilizado]") = relleno inventado: fallo.
    pendientes = {x for x in encontrados if RE_PENDIENTE.fullmatch(x)}
    for p in sorted(pendientes):
        AVISOS.add(f"dato pendiente de el usuario: {p}")
    rellenos = sorted(encontrados - pendientes)
    if rellenos:
        out.append(f"{vista}: texto de relleno visible en la pagina (quitalo o pon el contenido real): {', '.join(rellenos[:5])}.")
    return out


# Relleno que se ve en la pagina: "[Mapa Vectorial Estilizado]" (08/11), lorem ipsum, placeholder, {{variable}}...
# "[PENDIENTE]" esta permitido: es lo que se pide para datos que el usuario no dio.
RE_RELLENO = re.compile(r"\[[^\]\n]{2,60}\]|lorem ipsum|placeholder|\{\{[^}]*\}\}|\bTODO\b|\bXXX\b", re.I)
RE_PENDIENTE = re.compile(r"\[[A-ZÁÉÍÓÚÜÑ0-9 €/.,&-]{2,60}\]")
RE_PRECIO = re.compile(r"\d{1,4}(?:[.,]\d{2})?\s?(?:€|eur\b)|(?:€|\$)\s?\d{1,4}(?:[.,]\d{2})?", re.I)
RE_TELEFONO = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\d[\s.-]?){9,12}\b")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def datos_posiblemente_inventados(texto_pagina: str, instrucciones: str) -> list[str]:
    """Precios, telefonos y emails de la pagina que NO estan en el pedido/contrato: Qwen se los pudo inventar
    (08/11: puso "18.50€ / 300ml" sin que el pedido diera precios). Es un aviso, no un freno."""
    base = re.sub(r"\s+", "", instrucciones.lower())
    raros = []
    for nombre, patron in (("precio", RE_PRECIO), ("telefono", RE_TELEFONO), ("email", RE_EMAIL)):
        for m in patron.finditer(texto_pagina):
            dato = m.group(0).strip()
            if re.sub(r"\s+", "", dato.lower()) not in base:
                raros.append(f"{nombre} {dato}")
    return sorted(set(raros))[:8]


def ejecutar_contexto_2(
    contrato: dict,
    modelo_coder: str,
    modelo_vl: str,
    max_intentos: int = 3,
) -> tuple[bool, int, str]:
    """Contexto 2: Playwright renderiza, comprueba desbordes DOM e InternVL audita estetica."""
    cfg_c2 = contrato.get("contexto_2", {})
    if not cfg_c2.get("activo", True):
        return True, 0, "Contexto 2 omitido por configuracion"

    archivo_obj = Path(contrato["archivo_objetivo"]).resolve()
    url_o_archivo = cfg_c2.get("url_o_archivo", str(archivo_obj))

    # Resolver URL local o remota
    if not url_o_archivo.startswith("http://") and not url_o_archivo.startswith("https://"):
        ruta_p = Path(url_o_archivo).resolve()
        if not ruta_p.exists():
            return False, 0, f"No existe el archivo para auditar: {ruta_p}"
        target_url = ruta_p.as_uri()
    else:
        target_url = url_o_archivo

    criterios = cfg_c2.get("criterios_visuales", "Cero overflow-x, sin colisiones de texto, responsive pulgar")
    secciones = cfg_c2.get("secciones", [])
    avisos_c2 = AVISOS
    # capturas en la carpeta de la tarea (se quedan: sirven para revisar despues lo que vio InternVL)
    dir_capturas = (CARPETA_TAREA / "capturas") if CARPETA_TAREA else Path.home() / "Pictures" / "capturas_nova" / "temp_pipeline_audit"
    dir_capturas.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, 0, "Playwright no esta instalado en Python. Imposible ejecutar Contexto 2."

    ultimo_fallo = ""

    for vuelta in range(1, max_intentos + 1):
        print(f"[CONTEXTO 2] Vuelta {vuelta}/{max_intentos} - Capturando con Playwright...")

        captura_desktop = dir_capturas / f"desktop_v{vuelta}.png"
        captura_mobile = dir_capturas / f"mobile_v{vuelta}.png"
        capturas_secciones: list[Path] = []
        desborde_detectado = False
        detalles_dom = ""

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # 1. Desktop Check (1280x800)
            # movimiento reducido: sin fundidos a medias en las capturas (08/11 InternVL vio una seccion "vacia")
            page_d = browser.new_page(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
            errores_js: list[str] = []
            page_d.on("pageerror", lambda ex: errores_js.append(str(ex)[:140]))
            try:
                page_d.goto(target_url, wait_until="load", timeout=15000)
                page_d.wait_for_timeout(800)
            except Exception as e:
                browser.close()
                return False, vuelta, f"Fallo cargando pagina en desktop: {e}"

            dom_d = page_d.evaluate(JS_CHEQUEO_DOM, secciones)
            problemas_d = problemas_dom(dom_d, "Desktop 1280px")
            # movimiento (kit de efectos): con animaciones ACTIVAS, bajar por la pagina; errores JS y canvas en blanco = fallo
            page_v = browser.new_page(viewport={"width": 1280, "height": 800})
            page_v.on("pageerror", lambda ex: errores_js.append(str(ex)[:140]))
            try:
                page_v.goto(target_url, wait_until="load", timeout=15000)
                page_v.wait_for_timeout(600)
                alto = page_v.evaluate("document.documentElement.scrollHeight")
                for y in range(0, int(alto), 600):
                    page_v.mouse.wheel(0, 600)
                    page_v.wait_for_timeout(90)
                page_v.wait_for_timeout(400)
                page_v.evaluate("scrollTo(0, 0)")
                page_v.wait_for_timeout(700)
                vacios = page_v.evaluate("""() => [...document.querySelectorAll('canvas')].filter(c => { const r = c.getBoundingClientRect();
                    if (r.width < 20 || r.height < 20) return false; const x = c.getContext('2d'); if (!x) return false;
                    try { const d = x.getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4 * 97) if (d[i] > 8) return false; }
                    catch (e) { return false; } return true; }).map(c => (c.className || 'canvas') + ' ' + Math.round(c.getBoundingClientRect().width) + 'px')""")
                if vacios:
                    problemas_d.append(f"Desktop 1280px: canvas en blanco (no dibuja nada): {', '.join(vacios[:3])}.")
            except Exception as e:
                avisos_c2.add(f"no se pudo probar el movimiento: {str(e)[:80]}")
            if errores_js:
                problemas_d.append(f"errores de JavaScript en la pagina: {' | '.join(dict.fromkeys(errores_js))}"[:400])
            if problemas_d:
                desborde_detectado = True
                detalles_dom += " ".join(problemas_d) + " "
            if dom_d.get("tapado"):
                avisos_c2.add("html/body con overflow-x: hidden: TAPA los desbordes en vez de evitarlos (medidos igualmente)")
            for dato in datos_posiblemente_inventados(dom_d.get("textoVisible", ""), contrato.get("instrucciones", "")):
                avisos_c2.add(f"dato que no esta en el pedido (posible invento de Qwen): {dato}")

            page_d.screenshot(path=str(captura_desktop), full_page=True)

            # Capturas de secciones especificas
            for idx, sel in enumerate(secciones):
                try:
                    loc = page_d.locator(sel).first
                    if loc.count() > 0:
                        sec_path = dir_capturas / f"sec_{idx}_v{vuelta}.png"
                        loc.screenshot(path=str(sec_path))
                        capturas_secciones.append(sec_path)
                except Exception:
                    pass

            # 2. Mobile Check (375x812 - iPhone/Standard Mobile)
            page_m = browser.new_page(viewport={"width": 375, "height": 812}, reduced_motion="reduce")
            try:
                page_m.goto(target_url, wait_until="load", timeout=15000)
                page_m.wait_for_timeout(500)
            except Exception as e:
                browser.close()
                return False, vuelta, f"Fallo cargando pagina en mobile: {e}"

            dom_m = page_m.evaluate(JS_CHEQUEO_DOM, secciones)
            problemas_m = problemas_dom(dom_m, "Mobile 375px")
            if problemas_m:
                desborde_detectado = True
                detalles_dom += " ".join(problemas_m) + " "

            page_m.screenshot(path=str(captura_mobile), full_page=True)
            browser.close()

        # Si el DOM ya detecto fallos (desbordes, secciones que faltan o vacias, pagina sin texto), es fallo directo
        if desborde_detectado:
            ultimo_fallo = f"[DOM] {detalles_dom.strip()}"
            print(f"[CONTEXTO 2] {ultimo_fallo}")
        else:
            # InternVL mira PC, movil y cada seccion (antes solo la captura movil): todas tienen que aprobar
            capturas = [("Desktop 1280px", captura_desktop), ("Mobile 375px", captura_mobile)] + [
                (f"seccion {sel}", c) for sel, c in zip(secciones, capturas_secciones)
            ]
            criterios_vl = criterios + (f". Partes que deben verse en la pagina: {', '.join(secciones)}" if secciones else "")
            rechazos = []
            for nombre, captura in capturas:
                print(f"[CONTEXTO 2] Vuelta {vuelta}/{max_intentos} - InternVL revisando {nombre}...")
                aprobado_vl, respuesta_vl = auditar_con_internvl(captura, criterios_vl, modelo_vl)
                if not aprobado_vl:
                    rechazos.append(f"{nombre}: {respuesta_vl}")
            if not rechazos:
                print(f"[CONTEXTO 2 OK] Auditoria visual aprobada en vuelta {vuelta} ({len(capturas)} capturas).")
                if not CARPETA_TAREA:  # sin carpeta de tarea son temporales
                    shutil.rmtree(dir_capturas, ignore_errors=True)
                return True, vuelta, (
                    f"DOM: secciones presentes y 0 desbordes en 1280px y 375px; InternVL: {len(capturas)} capturas "
                    "aprobadas (PC, movil y secciones)"
                )
            ultimo_fallo = "[INTERNVL RECHAZO] " + " | ".join(rechazos)
            print(f"[CONTEXTO 2] {ultimo_fallo}")

        # Si fallamos y quedan intentos, pedir a Qwen correccion CSS
        if vuelta < max_intentos:
            # por trozos (texto viejo -> texto nuevo) y solo lo que hace falta; antes Qwen reescribia el archivo entero
            print(f"[CONTEXTO 2] Qwen corrigiendo por trozos para la vuelta {vuelta + 1}...")
            try:
                ok_b, info = corregir_por_bloques(
                    archivo_obj,
                    f"{ultimo_fallo}\nCorrige el HTML/CSS para que todas las secciones se vean, sin elementos que se "
                    "salgan por la derecha (no lo tapes con overflow-x: hidden) y sin textos pisados.",
                    modelo_coder,
                )
                print(f"[CONTEXTO 2] {info}")
                if ok_b:
                    revisar(str(archivo_obj), autofix=True)
            except Exception as e:
                print(f"[CONTEXTO 2] Error al re-invocar Qwen: {e}")

    # Si se agotaron los intentos, conservar capturas para diagnostico de el usuario (ya estan en la carpeta de la tarea)
    if not CARPETA_TAREA:
        carpeta_fallos = Path.home() / "Pictures" / "capturas_nova" / "fallos_audit_visual"
        carpeta_fallos.mkdir(parents=True, exist_ok=True)
        for c in dir_capturas.glob("*.png"):
            shutil.copy(c, carpeta_fallos / c.name)

    return False, max_intentos, ultimo_fallo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nova Pipeline Local v1.0 - Capa 0 Obrero Local (Doble Contexto)"
    )
    parser.add_argument(
        "--contrato",
        type=str,
        required=True,
        help="Ruta al archivo contrato_diseno.json",
    )
    parser.add_argument(
        "--intentos",
        type=int,
        default=3,
        help="Maximo de intentos por contexto antes de circuit breaker (default: 3)",
    )
    args = parser.parse_args()

    ruta_contrato = Path(args.contrato).resolve()
    if not ruta_contrato.is_file():
        print(f"[ERROR] No se encuentra el contrato en: {ruta_contrato}")
        sys.exit(2)

    try:
        contrato = json.loads(ruta_contrato.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] El contrato no es un JSON valido: {e}")
        sys.exit(2)

    # 0. Sin nova_core (linter, Qwen) no hay pipeline: freno, nunca un "limpio" inventado
    if ERROR_IMPORT is not None:
        volcar_freno_pendiente(
            "ARRANQUE CAPA 0",
            Path(contrato.get("archivo_objetivo", "desconocido")),
            0,
            f"No se pudo cargar nova_core (orquestador.py / ollama_comun.py): {ERROR_IMPORT}",
        )
        sys.exit(1)

    # 1. Asegurar servicio de Ollama
    if not ensure_ollama_service():
        volcar_freno_pendiente(
            "ARRANQUE CAPA 0",
            Path(contrato.get("archivo_objetivo", "desconocido")),
            0,
            "Ollama no responde en 127.0.0.1:11434 y no pudo iniciarse automaticamente.",
        )
        sys.exit(1)

    modelo_coder, modelo_vl = cargar_modelos()
    archivo_obj = Path(contrato.get("archivo_objetivo", "")).resolve()
    global CARPETA_TAREA
    CARPETA_TAREA = preparar_carpeta_tarea(contrato, ruta_contrato)

    print("=" * 70)
    print(f"[NOVA PIPELINE LOCAL] Proyecto: {contrato.get('proyecto', 'Sin nombre')}")
    print(f"Archivo objetivo: {archivo_obj}")
    print(f"Carpeta de la tarea: {CARPETA_TAREA}")
    print(f"Modelos Capa 0: Coder={modelo_coder} | VL={modelo_vl}")
    print("=" * 70)

    # 2. Ejecutar Contexto 1 (Sintaxis y Linter)
    ok_c1, vueltas_c1, detalle_c1 = ejecutar_contexto_1(
        contrato, modelo_coder, max_intentos=args.intentos
    )
    if not ok_c1:
        volcar_freno_pendiente("CONTEXTO 1 (SINTAXIS/LINTER)", archivo_obj, vueltas_c1, detalle_c1)
        sys.exit(1)

    # 3. Ejecutar Contexto 2 (Vision y Maquetacion) si aplica
    tipo = contrato.get("tipo", "frontend").lower()
    es_ui = tipo in ("frontend", "ui", "web") or archivo_obj.suffix in (".html", ".jsx", ".tsx", ".vue")
    
    ok_c2 = True
    vueltas_c2 = 0
    detalle_c2 = "N/A (Tarea no visual)"

    if es_ui:
        ok_c2, vueltas_c2, detalle_c2 = ejecutar_contexto_2(
            contrato, modelo_coder, modelo_vl, max_intentos=args.intentos
        )
        if not ok_c2:
            volcar_freno_pendiente(
                "CONTEXTO 2 (VISION/MAQUETACION)",
                archivo_obj,
                vueltas_c2,
                detalle_c2,
                CARPETA_TAREA / "capturas",
            )
            sys.exit(1)

    # 4. Ambos contextos superados: Generar reporte_final_ok.json
    # Limpiar el freno anterior de memory (si lo habia): el ultimo estado ahora es este OK
    (RUTA_MEMORY / "nova_pendiente.txt").unlink(missing_ok=True)

    reporte_datos = {
        "estado": "OK",
        "proyecto": contrato.get("proyecto", ""),
        "archivo": str(archivo_obj),
        "carpeta_tarea": str(CARPETA_TAREA),
        "timestamp": datetime.now().isoformat(),
        "contexto_1": {
            "superado": True,
            "vueltas": vueltas_c1,
            "linter": detalle_c1,
        },
        "contexto_2": {
            "superado": ok_c2,
            "vueltas": vueltas_c2,
            "diagnostico": detalle_c2,
        },
        "avisos": sorted(AVISOS),
    }

    (CARPETA_TAREA / "reporte_final_ok.json").write_text(
        json.dumps(reporte_datos, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if RUTA_MEMORY.exists():
        (RUTA_MEMORY / "reporte_final_ok.json").write_text(
            json.dumps(reporte_datos, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print("\n" + "=" * 70)
    print(f"[CIERRE PIPELINE OK] Archivo: {archivo_obj.name}")
    print(f"Contexto 1: {vueltas_c1} vuelta(s) -> {detalle_c1}")
    print(f"Contexto 2: {vueltas_c2} vuelta(s) -> {detalle_c2}")
    print(f"Reporte emitido en: {CARPETA_TAREA / 'reporte_final_ok.json'} (0 tokens gastados en nube)")
    print("=" * 70)


if __name__ == "__main__":
    main()
