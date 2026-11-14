"""
NOVA TAREA - un solo comando para la Capa 0 (Qwen pica, linter y InternVL revisan, 0 tokens de nube)

    python nova_tarea.py "lo que pide Alexander" --carpeta <ruta> [--archivo index.html]
           [--secciones hero,cafes,horario,pie] [--direccion "dirección de arte de Nova"]
           [--dominio ui-frontend] [--solo-contrato] [--intentos 3]

Por que existe: para usar el pipeline, Nova tenia que leer su codigo en cada ventana (10-15 llamadas de nube solo
para aprender el formato del contrato) y escribir el contrato a mano. Y las skills del indice dependian de que Flash
las abriera: en las webs del 07/11 abrio 0-4 de las 7 que manda el indice.

Que hace:
  1. Lee el indice del dominio (config/skills/index-<dominio>/SKILL.md) y las skills que manda abrir en su
     apartado 1, y mete un resumen de cada una (descripcion + reglas) DENTRO del contrato. Qwen las recibe siempre.
  2. Escribe contrato_diseno.json en la carpeta, con reglas fijas (HTML completo, una <section id> por seccion,
     nada de overflow-x: hidden para tapar desbordes, sin datos inventados).
  3. Lanza nova_pipeline_local.py y devuelve su resultado: reporte_final_ok.json o nova_pendiente.txt en
     <carpeta>/nova_tareas/<fecha>_<proyecto>/. Codigo de salida 0 = OK, 1 = freno (leer nova_pendiente.txt).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NOVA_HOME = Path.home() / ".gemini"
INDICES = NOVA_HOME / "config" / "skills"
ALMACEN = NOVA_HOME / "antigravity" / "almacen" / "skills"
PIPELINE = Path(__file__).resolve().parent / "nova_pipeline_local.py"

PRESUPUESTO_SKILLS = 6000  # caracteres (~1.700 tokens): el contexto de Qwen es de 24k y la web necesita sitio
PRESUPUESTO_DIRECCION = 6500
DRAW = ALMACEN / "gemini-ui-artisan" / "scripts" / "draw.mjs"
# sector de draw.mjs a partir del pedido (draw.mjs --list sectors)
SECTORES = [
    (r"cafe|cafeter|restaur|bar\b|panader|pasteler|comida|menu|carta", "restaurant"),
    (r"hotel|hostal|airbnb|alojamiento|apartamento|turis", "hospitality"),
    (r"u[ñn]as|manicur|sal[oó]n|peluquer|belleza|spa|est[eé]tica|barber", "health"),
    (r"tienda|ecommerce|e-commerce|productos|venta online|shop", "ecommerce"),
    (r"inmobiliar|piso|vivienda|alquiler", "real-estate"),
    (r"portfolio|portafolio|fot[oó]graf|filmmaker|cineasta", "studio-portfolio"),
    (r"saas|software|app|plataforma|dashboard", "saas"),
    (r"evento|boda|concierto|festival", "event"),
    (r"curso|academia|escuela|universidad|clases", "education"),
    (r"ong|fundaci[oó]n|asociaci[oó]n|gobierno|municipal|ministerio", "nonprofit"),
    (r"m[uú]sica|dj|banda|artista", "music"),
    (r"arquitect|interiorismo|reforma", "architecture"),
]
POR_SKILL = 1400
RE_SKILL = re.compile(r"skills[\\/]+([\w\-]+)[\\/]+SKILL\.md")

REGLAS_FIJAS = """REGLAS FIJAS (no negociables):
- Archivo HTML COMPLETO y autocontenido: <!doctype html>, <head> con <meta viewport>, <title> y el CSS en <style>,
  <body> con todo el contenido, y termina en </html>.
- Cada parte de la pagina es un <section id="..."> (o <header>/<footer> con id) con los ids que se piden abajo.
- PROHIBIDO overflow-x: hidden (o clip) en html o body para esconder desbordes: el contenido tiene que CABER
  (max-width: 100%, flex-wrap, grid con minmax, min-width: 0, tamanos con clamp()).
- Movil primero: se revisa a 375px y a 1280px. Botones de al menos 44px de alto.
- Textos: solo los del pedido o textos propios coherentes. No inventes datos legales, telefonos o direcciones que no
  esten en el pedido: pon [PENDIENTE].
- Imagenes: CERO <img> salvo rutas que vengan en el pedido. Nada de Unsplash, Pexels, picsum ni IDs inventados (salen
  rotas y el revisor lo detecta). Usa tipografia grande, color, degradados o SVG en linea como recurso visual.
- No inventes precios, promociones ("primera semana gratis"), cifras ni testimonios: o vienen en el pedido o no van.
- Toda caja con color de fondo lleva contenido. Nada de height fijo con overflow hidden en tarjetas de texto.
- Un solo <h1> visible en el hero con el nombre o la propuesta del negocio.
- Devuelve UNICAMENTE el codigo, sin explicaciones."""


def detectar_dominio(pedido: str, archivo: str) -> str:
    texto = f"{pedido} {archivo}".lower()
    if re.search(r"\b(app movil|android|ios|flutter|expo)\b", texto):
        return "mobile-dev"
    if re.search(r"\b(api|backend|base de datos|endpoint|supabase)\b", texto):
        return "backend-db"
    return "ui-frontend"


def skills_del_indice(dominio: str) -> list[str]:
    """Las skills que el indice manda abrir en su apartado 1 (el salto obligatorio), sin repetir."""
    indice = INDICES / f"index-{dominio}" / "SKILL.md"
    if not indice.exists():
        return []
    texto = indice.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"\n## 1\..*?(?=\n## )", texto, re.S)
    nombres = RE_SKILL.findall(m.group(0) if m else texto)
    return list(dict.fromkeys(nombres))


def resumen_skill(nombre: str) -> str:
    """Descripcion + reglas en vinetas de la skill, recortado a POR_SKILL caracteres."""
    ruta = ALMACEN / nombre / "SKILL.md"
    if not ruta.exists():
        return ""
    texto = ruta.read_text(encoding="utf-8", errors="ignore")
    desc = re.search(r'^description:\s*"?(.*?)"?\s*$', texto, re.M)
    cuerpo = re.sub(r"^---.*?---", "", texto, count=1, flags=re.S)
    cuerpo = re.sub(r"```.*?```", "", cuerpo, flags=re.S)  # los ejemplos de codigo no caben
    reglas = [
        l.strip()[:170]
        for l in cuerpo.splitlines()
        if re.match(r"\s*([-*]|\d+\.)\s+\S", l) and len(l.strip()) > 12
    ]
    salida = f"[{nombre}] {desc.group(1).strip() if desc else ''}\n" + "\n".join(reglas)
    return salida[:POR_SKILL]


def guia_skills(dominio: str) -> tuple[str, list[str]]:
    nombres = skills_del_indice(dominio)
    partes, usadas, total = [], [], 0
    for n in nombres:
        r = resumen_skill(n)
        if not r or total + len(r) > PRESUPUESTO_SKILLS:
            continue
        partes.append(r)
        usadas.append(n)
        total += len(r)
    return "\n\n".join(partes), usadas


def detectar_sector(pedido: str) -> str:
    texto = pedido.lower()
    return next((s for patron, s in SECTORES if re.search(patron, texto)), "other")


def sortear_direccion(pedido: str, sector: str, carpeta: Path) -> tuple[str, str]:
    """Direccion de arte repartida por draw.mjs (gemini-ui-artisan: 247 webs reales estudiadas). La elige el script,
    no el modelo: si elige el modelo sale siempre la opcion por defecto de la categoria (el "crema + serif" de Nova).
    draw.mjs recuerda los ultimos sorteos para que dos proyectos seguidos no se parezcan."""
    if not DRAW.exists():
        return "", "draw.mjs no encontrado"
    salida = Path(carpeta).resolve() / "nova_direccion"  # absoluta: draw.mjs corre con otro cwd
    try:
        r = subprocess.run(
            ["node", str(DRAW), "--sector", sector, "--brief", re.sub(r"\s+", " ", pedido)[:160], "--out", str(salida)],
            cwd=DRAW.parent.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        d = json.loads((salida / "direction.json").read_text(encoding="utf-8"))
    except Exception as e:
        return "", f"draw.mjs fallo: {e}"
    di, hero, ty, pal = d.get("direction", {}), d.get("hero", {}), d.get("type", {}), d.get("palette", {})
    partes = [
        f"DIRECCION: {di.get('name', '')}. IDEA: {di.get('idea', '')}",
        f"COMPOSICION: {di.get('composition', '')}",
        f"EVITAR: {di.get('pitfalls', '')}",
        f"HERO ({hero.get('name', '')}): {hero.get('blueprint', '')} MOVIL: {hero.get('mobile', '')} TITULAR: {hero.get('headline', '')}",
        "TIPOGRAFIA: " + "; ".join(f"<link href=\"{u}\" rel=\"stylesheet\">" for u in ty.get("links", [])[:1])
        + f" Titulares: {ty.get('display', {}).get('family', '')} ({ty.get('display', {}).get('settings', '')})."
        + f" Texto: {ty.get('text', {}).get('family', '')} ({ty.get('text', {}).get('settings', '')})."
        + " Escala CSS: " + "; ".join(f"--{k}: {v}" for k, v in (ty.get("scale") or {}).items()),
        "PALETA (" + pal.get("name", "") + "): " + "; ".join(
            f"--{k}: {v}" for k, v in pal.items() if isinstance(v, str) and v.startswith("#")
        ) + f". {pal.get('note', '')}",
        "SECCIONES: " + " | ".join(
            f"{s.get('role', '')} ({s.get('name', '')}): {str(s.get('blueprint', ''))[:420]}" for s in d.get("sections", [])
        ),
        f"MOVIMIENTO: {(d.get('motion') or {}).get('description', '')}",
        "FOTOS: aun no hay fotos descargadas. Donde vaya una foto pon un bloque con un color de la paleta y la foto "
        "prevista en un COMENTARIO HTML (no como texto visible): "
        + "; ".join(f"{p.get('alt', '')}" for p in (d.get("photos") or {}).get("photos", [])[:5]),
    ]
    texto = "\n".join(p for p in partes if p.strip())
    return texto[:PRESUPUESTO_DIRECCION], f"{di.get('name', '?')} · {ty.get('name', '?')} · {pal.get('name', '?')}"


def construir_contrato(args) -> tuple[dict, list[str]]:
    carpeta = Path(args.carpeta).resolve()
    archivo = carpeta / args.archivo
    dominio = args.dominio or detectar_dominio(args.pedido, args.archivo)
    guia, usadas = guia_skills(dominio)
    direccion_sorteada, resumen_direccion = ("", "sin sorteo")
    if dominio == "ui-frontend" and not args.sin_sorteo:
        direccion_sorteada, resumen_direccion = sortear_direccion(
            args.pedido, args.sector or detectar_sector(args.pedido), carpeta
        )
    print(f"[NOVA TAREA] Direccion de arte: {resumen_direccion}")
    ids = [s.strip().lstrip("#") for s in (args.secciones or "").split(",") if s.strip()]
    secciones_txt = (
        "IDS OBLIGATORIOS de las secciones, en este orden: " + ", ".join(ids)
        if ids
        else "Estructura minima: <header>, <main> y <footer>."
    )
    instrucciones = "\n\n".join(
        p
        for p in (
            f"PEDIDO DE ALEXANDER:\n{args.pedido}",
            f"DIRECCION DE ARTE SORTEADA (MANDA: adoptala tal cual, no la mezcles con el diseno que harias "
            f"por defecto; lo desconocido es la idea):\n{direccion_sorteada}" if direccion_sorteada else "",
            (f"NOTAS DE NOVA (solo si no chocan con la direccion sorteada):\n{args.direccion}" if direccion_sorteada
             else f"DIRECCION DE ARTE (Nova):\n{args.direccion}") if args.direccion else "",
            secciones_txt,
            REGLAS_FIJAS,
            f"GUIA DE LAS SKILLS DE NOVA ({dominio}), aplicala al disenar:\n{guia}" if guia else "",
        )
        if p
    )
    contrato = {
        "proyecto": args.proyecto or re.sub(r"\s+", " ", args.pedido)[:60],
        "archivo_objetivo": str(archivo),
        "tipo": "frontend" if dominio == "ui-frontend" else dominio,
        "dominio": dominio,
        "skills_incluidas": usadas,
        "instrucciones": instrucciones,
        "contexto_1": {"criterios": "HTML5 semantico completo, CSS en <style>, KISS", "lenguaje": archivo.suffix.lstrip(".")},
        "contexto_2": {
            "activo": archivo.suffix.lower() in (".html", ".htm"),
            "url_o_archivo": str(archivo),
            "criterios_visuales": "Todas las secciones visibles con contenido, cero desbordes en 1280px y 375px, "
            "sin textos pisados, responsive tactil",
            "secciones": [f"#{i}" for i in ids] or ["header", "main", "footer"],
        },
    }
    return contrato, usadas


BIBLIOTECA = ALMACEN.parent / "biblioteca_web"
ID_BLOQUE = {"cabecera": "#cabecera", "hero": "#inicio", "destacados": "#destacados", "carta": "#carta", "horario": "#horario",
             "reservar": "#reservar", "eventos": "#eventos", "resenas": "#resenas", "visitanos": "#visitanos", "faq": "#faq",
             "pie": "#pie"}


def modo_biblioteca(args, carpeta: Path) -> int:
    """Web por categoria: maquetacion de la biblioteca (bloques de calidad fija) + datos reales + direccion sorteada.
    Qwen solo escribe los textos que faltan (eslogan, descripciones), sin inventar datos. Luego el pipeline VERIFICA."""
    sys.path.insert(0, str(BIBLIOTECA))
    import montar  # noqa: E402
    import textos  # noqa: E402

    ruta_datos = Path(args.datos).resolve() if args.datos else carpeta / "datos.json"
    if not ruta_datos.exists():
        print(f"[NOVA TAREA] Falta {ruta_datos}. Copia {BIBLIOTECA / 'plantilla_datos.json'} y rellenala "
              "con los datos REALES que de Alexander (lo que no sepas, dejalo vacio: saldra [PENDIENTE]).")
        return 2
    datos = json.loads(ruta_datos.read_text(encoding="utf-8"))
    recetas = montar.cargar_recetas()
    if args.categoria not in recetas:  # "auto" o una que no existe: se deduce del tipo de negocio y del pedido
        cat, rec = montar.detectar_categoria(f"{datos.get('negocio', {}).get('tipo', '')} {args.pedido}")
        if not cat:
            print("[NOVA TAREA] No reconozco la categoria del negocio. Pon negocio.tipo en palabras normales "
                  f"(gimnasio, clinica, peluqueria...) o --categoria con una de: {', '.join(k for k in recetas if not k.startswith('_'))}")
            return 2
        args.categoria, args.receta = cat, args.receta or rec
    print(f"[NOVA TAREA] Categoria: {args.categoria} · receta: {args.receta or '(segun el tipo)'}")
    direccion = {}
    if not args.sin_sorteo:
        _, resumen = sortear_direccion(args.pedido or json.dumps(datos.get("negocio", {}), ensure_ascii=False),
                                       args.sector or recetas[args.categoria].get("sector") or "other", carpeta)
        print(f"[NOVA TAREA] Direccion de arte: {resumen}")
        ruta_dir = carpeta / "nova_direccion" / "direction.json"
        direccion = json.loads(ruta_dir.read_text(encoding="utf-8")) if ruta_dir.exists() else {}
    datos, generados, avisos_txt = textos.completar(datos)
    (carpeta / "datos_completos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[NOVA TAREA] Textos escritos por Qwen (revisalos): {', '.join(generados) or 'ninguno'}")
    pagina, avisos_m, usados = montar.montar(datos, args.categoria, args.receta, direccion, esqueleto=args.esqueleto)
    archivo = carpeta / args.archivo
    archivo.write_text(pagina, encoding="utf-8")
    print("[NOVA TAREA] Montada con bloques: " + ", ".join(f"{k}({v})" for k, v in usados.items()))
    for x in avisos_txt + avisos_m:
        print(f"[NOVA TAREA] aviso: {x}")
    contrato = {
        "proyecto": args.proyecto or datos.get("negocio", {}).get("nombre", "web"),
        "archivo_objetivo": str(archivo), "tipo": "frontend", "modo": "verificar", "categoria": args.categoria,
        "instrucciones": json.dumps(datos, ensure_ascii=False),  # para el chequeo de datos inventados
        "contexto_1": {"criterios": "web montada por la biblioteca", "lenguaje": "html"},
        "contexto_2": {"activo": True, "url_o_archivo": str(archivo),
                       "criterios_visuales": "Todas las secciones visibles con contenido, cero desbordes, textos legibles",
                       "secciones": [ID_BLOQUE[b] for b in usados if b in ID_BLOQUE]},
    }
    ruta = carpeta / "contrato_diseno.json"
    ruta.write_text(json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8")
    r = subprocess.run([sys.executable, "-u", str(PIPELINE), "--contrato", str(ruta), "--intentos", str(args.intentos)], cwd=carpeta)
    print("[NOVA TAREA] " + ("OK: lee reporte_final_ok.json de la carpeta de la tarea y ENSENA a Alexander los textos de Qwen y los datos [PENDIENTE]."
                             if r.returncode == 0 else "FRENO: lee nova_pendiente.txt y avisa a Alexander. NO lo arregles desde la nube sin su permiso."))
    return r.returncode


def modo_verificar(args, carpeta: Path) -> int:
    """Revisa una web YA hecha (por Qwen o arreglada por Nova) sin regenerarla: DOM (fotos rotas, textos cortados, cajas
    vacias, desbordes, rellenos) + InternVL en PC, movil y secciones. Es el paso que cierra cada ronda de arreglos."""
    archivo = (carpeta / args.archivo).resolve()
    if not archivo.exists():
        print(f"[NOVA TAREA] No existe {archivo}.")
        return 2
    secciones = [s.strip() if s.strip().startswith(("#", ".")) else f"#{s.strip()}" for s in args.secciones.split(",") if s.strip()]
    if not secciones:
        secciones = ["#" + i for i in re.findall(r'<(?:section|header|footer|main)[^>]*\bid="([^"]+)"', archivo.read_text(encoding="utf-8", errors="ignore"))][:10]
    contrato = {
        "proyecto": args.proyecto or carpeta.name, "archivo_objetivo": str(archivo), "tipo": "frontend", "modo": "verificar",
        "instrucciones": args.pedido or "",
        "contexto_1": {"criterios": "web ya hecha: solo se verifica", "lenguaje": "html"},
        "contexto_2": {"activo": True, "url_o_archivo": str(archivo),
                       "criterios_visuales": "Secciones con contenido, cero fotos rotas, cero textos cortados, titular visible, legible en movil",
                       "secciones": secciones},
    }
    ruta = carpeta / "contrato_verificar.json"
    ruta.write_text(json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8")
    r = subprocess.run([sys.executable, "-u", str(PIPELINE), "--contrato", str(ruta), "--intentos", "1"], cwd=carpeta)
    print("[NOVA TAREA] " + ("VERIFICADA: ensena a Alexander las capturas y que arreglaste." if r.returncode == 0 else
                             "SIGUE CON FALLOS: lee nova_pendiente.txt, arregla con edit_file (<= 30 lineas por cambio) y vuelve a "
                             "lanzar --verificar. Maximo 3 rondas; despues, avisa a Alexander con las capturas."))
    return r.returncode


CLONADOR = Path.home() / "clones_web" / "motor" / "clonar.py"


def modo_referencia(args, carpeta: Path) -> int:
    """Alexander da una web de REFERENCIA: el clonador de Claude (clones_web, carpeta protegida: solo se EJECUTA) la mide
    y la rehace en local, sin Qwen. Lo util se copia a <carpeta>/nova_referencia/<web>/ para trabajar SOLO ahi."""
    if not CLONADOR.exists():
        print(f"[NOVA TAREA] No encuentro el clonador en {CLONADOR}. Avisa a Alexander.")
        return 2
    cmd = [sys.executable, "-u", str(CLONADOR), args.referencia]
    if args.paginas > 1:
        cmd.append(f"--paginas={args.paginas}")
    print(f"[NOVA TAREA] Clonando la referencia {args.referencia} (tarda de 5 a 30 min; no lo cortes ni leas su codigo)")
    salida = []
    p = subprocess.Popen(cmd, cwd=CLONADOR.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace",
                         env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    for linea in p.stdout:
        salida.append(linea)
        print(linea, end="", flush=True)
    p.wait()
    texto = "".join(salida)
    m = re.findall(r"Listo en \d+ s -> (.+)", texto)
    if p.returncode != 0 or not m:
        print("[NOVA TAREA] FRENO: el clonador no pudo con esa web (bloqueo de robots, pagina vacia...). Avisa a Alexander "
              "con el ultimo aviso de arriba. NO intentes clonarla a mano desde la nube.")
        return 1
    origen = Path(m[-1].strip())
    destino = carpeta / "nova_referencia" / origen.name
    destino.mkdir(parents=True, exist_ok=True)
    copiar = [("construccion", "construccion"), ("react", "react"), ("assets", "assets"),
              ("fichas_secciones.md", "fichas_secciones.md"), ("diferencias_pc_movil.md", "diferencias_pc_movil.md"),
              ("informe_pc.md", "informe_pc.md"), ("informe_movil.md", "informe_movil.md")]
    for a, b in copiar:
        src = origen / a
        if src.is_dir():
            shutil.copytree(src, destino / b, dirs_exist_ok=True)
        elif src.is_file():
            shutil.copy2(src, destino / b)
    nota = re.findall(r"Parecido medio (\d+) % · lista (\d+) % · aprobadas (\d+) de (\d+)", texto)
    inter = re.findall(r"Interacciones: (\d+) de (\d+) correctas", texto)
    flojas = re.findall(r"Por debajo del 90 %: secciones (.+?) ->", texto)
    resumen = {
        "referencia": args.referencia, "clon_original": str(origen), "copia_de_trabajo": str(destino),
        "parecido_medio": int(nota[-1][0]) if nota else None,
        "secciones_aprobadas": f"{nota[-1][2]}/{nota[-1][3]}" if nota else None,
        "interacciones": f"{inter[-1][0]}/{inter[-1][1]}" if inter else None,
        "secciones_flojas": flojas[-1] if flojas else "",
        "archivos": {"clon": str(destino / "construccion" / "index.html"),
                     "final_medios_libres": str(destino / "construccion" / "index_final.html"),
                     "careo": str(destino / "construccion" / "revision.html"),
                     "react": str(destino / "react")},
        "uso": ("REFERENCIA de estructura y ritmo. Los textos, marcas, logos y fotos de la original NO se publican: se cambian "
                "por los datos reales de Alexander. Las secciones flojas (<90 %) las arregla Claude, no la nube."),
    }
    (destino / "resumen_referencia.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[NOVA TAREA] OK referencia: {destino}\\resumen_referencia.json · parecido {resumen['parecido_medio']} % · "
          f"flojas: {resumen['secciones_flojas'] or 'ninguna'}. Ensena a Alexander el careo (revision.html) antes de seguir.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Nova Tarea: pedido -> contrato con skills -> pipeline local")
    ap.add_argument("--verificar", action="store_true",
                    help="Solo revisar (DOM + InternVL, PC y movil) el --archivo ya hecho, sin regenerarlo. Tras cada arreglo de Nova")
    ap.add_argument("--referencia", default="", help="URL de una web de referencia que dio Alexander: la clona el motor de Claude")
    ap.add_argument("--paginas", type=int, default=1, help="Con --referencia: paginas del menu a clonar (1 = solo la home)")
    ap.add_argument("pedido", nargs="?", default="", help="Lo que pide Alexander, con sus datos")
    ap.add_argument("--categoria", default="", help="Web con la biblioteca: auto (la deduce) o hosteleria, deporte, salud, belleza, alojamiento, comercio, profesionales, educacion, oficios, eventos, ocio, inmobiliaria, motor, digital, asociaciones. Usa --datos (o datos.json de la carpeta)")
    ap.add_argument("--datos", default="", help="datos.json con los datos REALES del negocio (modo categoria)")
    ap.add_argument("--esqueleto", default="", help="Forzar estructura: editorial, inmersivo, bento, minimal, catalogo (por defecto: memoria anti-repeticion + direccion + radar)")
    ap.add_argument("--receta", default="", help="Receta de la categoria (cafeteria, restaurante, bar); por defecto se deduce")
    ap.add_argument("--carpeta", required=True, help="Carpeta del proyecto (se trabaja solo ahi)")
    ap.add_argument("--archivo", default="index.html", help="Archivo a crear (por defecto index.html)")
    ap.add_argument("--secciones", default="", help="ids de las secciones separados por comas")
    ap.add_argument("--direccion", default="", help="Direccion de arte (paleta, tipografia, estilo)")
    ap.add_argument("--dominio", default="", help="Indice a usar (ui-frontend, motion-3d...); por defecto se deduce")
    ap.add_argument("--proyecto", default="", help="Nombre corto del proyecto")
    ap.add_argument("--sector", default="", help="Sector para draw.mjs (restaurant, health, ecommerce...); por defecto se deduce")
    ap.add_argument("--sin-sorteo", action="store_true", help="No sortear direccion de arte (usar solo --direccion)")
    ap.add_argument("--intentos", type=int, default=3)
    ap.add_argument("--solo-contrato", action="store_true", help="Escribe el contrato y no lanza el pipeline")
    args = ap.parse_args()

    carpeta = Path(args.carpeta).resolve()
    if not carpeta.is_dir():
        print(f"[NOVA TAREA] No existe la carpeta {carpeta}: creala o revisa la ruta.")
        return 2
    if args.verificar:
        return modo_verificar(args, carpeta)
    if args.referencia:
        return modo_referencia(args, carpeta)
    if args.categoria:
        return modo_biblioteca(args, carpeta)
    if not args.pedido:
        print("[NOVA TAREA] Falta el pedido (o usa --categoria hosteleria --datos datos.json).")
        return 2
    contrato, usadas = construir_contrato(args)
    ruta = carpeta / "contrato_diseno.json"
    ruta.write_text(json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[NOVA TAREA] Contrato: {ruta}")
    print(f"[NOVA TAREA] Skills metidas en el contrato ({len(usadas)}): {', '.join(usadas) or 'ninguna'}")
    if args.solo_contrato:
        return 0

    r = subprocess.run(
        [sys.executable, "-u", str(PIPELINE), "--contrato", str(ruta), "--intentos", str(args.intentos)],
        cwd=carpeta,
    )
    print(
        "[NOVA TAREA] "
        + ("OK: lee reporte_final_ok.json de la carpeta de la tarea." if r.returncode == 0
           else "FRENO: lee nova_pendiente.txt de la carpeta de la tarea y avisa a Alexander. NO lo arregles desde la nube sin su permiso.")
    )
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
