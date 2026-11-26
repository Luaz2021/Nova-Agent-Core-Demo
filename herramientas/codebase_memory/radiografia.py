"""RADIOGRAFIA DE PROYECTOS DE CODIGO (25/11/2026, Claude) sobre el MCP "codebase" (codebase-memory-mcp).

Para traer un proyecto grande, una rama o codigo legacy y saber, sin leerlo entero ni gastar nube:
quien conecta con quien, que hace cada pieza, como esta montado, donde es fragil y si se puede trocear.

  analizar <carpeta> [--nombre X] [--explicar] [--profundidad N] [--excluir carpeta1,carpeta2]
        Indexa (local, segundos) y escribe RADIOGRAFIA.md + datos.json en
        antigravity\\documentos_generados\\radiografias\\<fecha>_<nombre>\\
        Cada pieza lleva una FICHA (archivos, funciones, comentarios): Nova explica que hace a partir de ella.
        --explicar: (opcional, lento: 20-40 s por pieza) que lo haga Qwen local en vez de Nova.
  impacto <proyecto> <funcion> [--profundidad 3]   que se rompe si tocas esa funcion (quien la llama)
  cambios <proyecto>                               impacto de los cambios sin commit (git diff)
  mapa [--cerrar] [--minutos 60]                   abre / cierra el mapa visual (http://127.0.0.1:9749)
  proyectos                                        lista los proyectos ya indexados

No escribe nada dentro del proyecto analizado. Indices en herramientas\\codebase_memory\\.cache (no viajan).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
EXE = AQUI / "bin" / ("codebase-memory-mcp.exe" if os.name == "nt" else "codebase-memory-mcp")  # v3.3: 3 sistemas
CACHE = AQUI / ".cache"
NOVA = AQUI.parents[2]  # ...\.gemini
SALIDA = NOVA / "antigravity" / "documentos_generados" / "radiografias"
ESTADO_MAPA = CACHE / "mapa_visor.json"
PUERTO = 9749
SIN_VENTANA = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW solo existe en Windows
MODELOS = NOVA / "antigravity" / "scripts" / "nova_modelos.json"


# ------------------------------------------------------------------ motor
def cbm(herramienta: str, timeout: int = 1800, **args) -> str:
    """Lanza una herramienta del codebase en modo CLI y devuelve stdout (texto)."""
    if not EXE.exists():
        sys.exit(f"No esta el programa del codebase en {EXE}. Instalalo con: <PYTHON> herramientas/codebase_memory/instalar.py")
    env = dict(os.environ, CBM_CACHE_DIR=str(CACHE))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(args, f)
    try:
        p = subprocess.run([str(EXE), "cli", "--quiet", herramienta, "--args-file", f.name],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=env, timeout=timeout, creationflags=SIN_VENTANA)
    finally:
        os.unlink(f.name)
    if p.returncode != 0:
        err = " ".join(l for l in p.stderr.splitlines() if "preloading" not in l).strip()
        raise RuntimeError(f"{herramienta}: {err or p.stdout[:300]}")
    return p.stdout


def consulta(proyecto: str, cypher: str) -> list[list]:
    """Cypher de solo lectura; devuelve TODAS las filas (pagina con cursor)."""
    filas, cursor = [], None
    while True:
        args = {"project": proyecto, "query": cypher, "format": "json", "max_rows": 20000}
        if cursor:
            args["cursor"] = cursor
        r = json.loads(cbm("query_graph", **args))
        filas += r.get("rows", [])
        cursor = r.get("next_cursor") if r.get("has_more") else None
        if not cursor:
            return filas


def num(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def nombre_proyecto(carpeta: Path, nombre: str | None) -> str:
    base = nombre or carpeta.name
    return "rx_" + re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_").lower()


# ------------------------------------------------------------------ piezas (modulos)
def asignar_piezas(archivos: list[str], profundidad: int | None) -> dict[str, str]:
    """Agrupa cada archivo en una 'pieza' (carpeta). Si todo esta en una carpeta, cada archivo es una pieza."""
    carpetas = {a: str(Path(a).parent).replace("\\", "/") for a in archivos}
    partes = [c.split("/") if c != "." else [] for c in carpetas.values()]
    # prefijo comun (src/main/java/com/empresa/... en Java)
    comun = 0
    if partes and all(partes):
        while all(len(p) > comun for p in partes) and len({p[comun] for p in partes}) == 1:
            comun += 1
    raices = ("src/main/java/", "src/main/kotlin/", "app/src/main/java/", "src/main/", "src/", "lib/", "app/")
    def pieza_con(prof):
        out = {}
        for a, c in carpetas.items():
            p = c.split("/") if c != "." else []
            trozo = p[comun:comun + prof]
            resto = "/".join(p[comun:]) + "/"
            for r in raices:  # src/main/java/com/x -> com/x : la raiz de codigo no es una pieza
                if comun == 0 and resto.startswith(r):
                    q = resto[len(r):].strip("/").split("/") if resto[len(r):].strip("/") else []
                    trozo = q[:prof]
                    break
            out[a] = "/".join(trozo) if trozo else "(raiz)"
        return out
    if profundidad:
        res = pieza_con(profundidad)
    else:
        res = pieza_con(1)
        for prof in range(2, 6):  # baja de nivel mientras haya pocas piezas
            if len(set(res.values())) >= 4:
                break
            otra = pieza_con(prof)
            if len(set(otra.values())) > 40:
                break
            res = otra
    if len(set(res.values())) <= 1:  # proyecto plano: una pieza por archivo
        return {a: Path(a).stem for a in archivos}
    # pocas piezas y una enorme (49 scripts en motor/): esa se parte por archivo para ver sus micro-procesos
    tam = Counter(res.values())
    if not profundidad and len(tam) < 6:
        for p, n in tam.items():
            if n > 15 and len(tam) - 1 + n <= 60:
                for a in archivos:
                    if res[a] == p:
                        res[a] = f"{p}/{Path(a).stem}"
    return res


def ciclos(grafo: dict[str, set[str]]) -> list[list[str]]:
    """Componentes fuertemente conexas de tamano > 1 (Tarjan iterativo)."""
    indice, bajo, pila, en_pila, res, i = {}, {}, [], set(), [], [0]
    for raiz in list(grafo):
        if raiz in indice:
            continue
        trabajo = [(raiz, iter(sorted(grafo.get(raiz, ()))))]
        indice[raiz] = bajo[raiz] = i[0]; i[0] += 1; pila.append(raiz); en_pila.add(raiz)
        while trabajo:
            v, hijos = trabajo[-1]
            avanzo = False
            for w in hijos:
                if w not in indice:
                    indice[w] = bajo[w] = i[0]; i[0] += 1; pila.append(w); en_pila.add(w)
                    trabajo.append((w, iter(sorted(grafo.get(w, ())))))
                    avanzo = True
                    break
                if w in en_pila:
                    bajo[v] = min(bajo[v], indice[w])
            if avanzo:
                continue
            trabajo.pop()
            if trabajo:
                bajo[trabajo[-1][0]] = min(bajo[trabajo[-1][0]], bajo[v])
            if bajo[v] == indice[v]:
                comp = []
                while True:
                    w = pila.pop(); en_pila.discard(w); comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    res.append(sorted(comp))
    return res


# ------------------------------------------------------------------ Qwen local
def explicar_piezas(piezas_info: dict[str, dict]) -> dict[str, str]:
    try:
        modelo = json.loads(MODELOS.read_text(encoding="utf-8"))["coder"]
    except (OSError, ValueError, KeyError):
        modelo = "qwen3.5:9b"
    out = {}
    # tope: las 10 piezas mas grandes (20-40 s cada una con Qwen 9B en la laptop); el resto, por sus nombres
    grandes = sorted(piezas_info, key=lambda p: -piezas_info[p]["n_funciones"])[:10]
    for nombre, info in ((p, piezas_info[p]) for p in grandes):
        funciones = ", ".join(info["funciones"][:25])
        docs = " | ".join(info["docs"][:6])
        prompt = (f"Eres un arquitecto de software. Pieza '{nombre}' de un proyecto. Archivos: "
                  f"{', '.join(info['archivos'][:15])}. Funciones/clases: {funciones}. Comentarios: {docs}.\n"
                  "En espanol, en 1 o 2 frases cortas y sin inventar: que hace esta pieza. Solo la respuesta.")
        cuerpo = json.dumps({"model": modelo, "prompt": prompt, "stream": False, "think": False,
                             "options": {"temperature": 0.2, "num_predict": 120}}).encode()
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/generate", cuerpo,
                                         {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                txt = json.loads(r.read()).get("response", "")
            txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S).strip().replace("\n", " ")
            out[nombre] = txt[:400]
        except Exception as e:  # Ollama apagado: no se inventa nada
            out[nombre] = f"(sin explicacion: Ollama no respondio: {type(e).__name__})"
            break
    return out


# ------------------------------------------------------------------ analizar
FRAMEWORK = re.compile(r"^(handle_|on_?[A-Z_]|visit_|do_|test|setUp|tearDown|run$|actionPerformed|paint|"
                       r"doGet|doPost|onCreate|onClick|toString|equals|hashCode|compareTo|get[A-Z]|set[A-Z]|is[A-Z])")


def analizar(carpeta: Path, nombre: str | None, explicar: bool, profundidad: int | None,
             excluir: str | None = None) -> Path:
    carpeta = carpeta.resolve()
    if not carpeta.is_dir():
        sys.exit(f"No existe la carpeta: {carpeta}")
    proyecto = nombre_proyecto(carpeta, nombre)
    t0 = time.time()
    print(f"Indexando {carpeta} ...", flush=True)
    idx = json.loads(cbm("index_repository", repo_path=str(carpeta).replace("\\", "/"),
                         name=proyecto, mode="moderate"))
    print(f"  {idx.get('nodes')} nodos, {idx.get('edges')} relaciones en {time.time() - t0:.0f} s", flush=True)

    arq = json.loads(cbm("get_architecture", project=proyecto, aspects=["languages", "entry_points", "routes"],
                         format="json"))
    funcs = consulta(proyecto, "MATCH (f:Function) RETURN f.qualified_name, f.name, f.file_path, f.complexity, "
                               "f.cognitive, f.lines, f.is_entry_point, f.is_test, f.docstring")
    funcs += consulta(proyecto, "MATCH (f:Method) RETURN f.qualified_name, f.name, f.file_path, f.complexity, "
                                "f.cognitive, f.lines, f.is_entry_point, f.is_test, f.docstring")
    clases = consulta(proyecto, "MATCH (c:Class) RETURN c.qualified_name, c.name, c.file_path, c.docstring")
    llamadas = consulta(proyecto, "MATCH (a)-[r:CALLS]->(b) RETURN a.file_path, b.file_path, b.qualified_name")
    imports = consulta(proyecto, "MATCH (a)-[r:IMPORTS]->(b) RETURN a.file_path, b.file_path")
    # scripts que lanzan a otros (subprocess "python paso.py", rutas a otros archivos): tambien es depender
    imports += consulta(proyecto, "MATCH (a)-[r:REFERENCES_FILE]->(b) RETURN a.file_path, b.file_path")
    similares = consulta(proyecto, "MATCH (a)-[r:SIMILAR_TO]->(b) RETURN a.qualified_name, a.file_path, "
                                   "b.qualified_name, b.file_path, r.jaccard")
    referencias = consulta(proyecto, "MATCH (a)-[r:CALL_REFERENCE]->(b) RETURN b.qualified_name")
    usos = consulta(proyecto, "MATCH (a)-[r:USAGE]->(b) RETURN b.qualified_name")
    tablas = consulta(proyecto, "MATCH (t:Table) RETURN t.name")

    fuera = [e.strip().strip("/\\").replace("\\", "/") + "/" for e in (excluir or "").split(",") if e.strip()]
    propio = lambda ruta: (bool(ruta) and not str(ruta).startswith("<")
                           and not any(str(ruta).replace("\\", "/").startswith(e) for e in fuera))
    funcs = [f for f in funcs if propio(f[2])]
    clases = [c for c in clases if propio(c[2])]
    archivos = sorted({f[2] for f in funcs if propio(f[2])} | {c[2] for c in clases if propio(c[2])}
                      | {a for a, b, _ in llamadas if propio(a)})
    pieza_de = asignar_piezas(archivos, profundidad)

    # --- grafo de piezas
    dep = defaultdict(Counter)        # pieza -> pieza destino -> llamadas
    internas = Counter()
    entrantes_fn = Counter()          # funcion -> llamadas desde OTROS archivos
    llamadores_fn = defaultdict(set)  # funcion -> archivos que la llaman
    for a, b, qn in llamadas:
        if not (propio(a) and propio(b)):
            continue
        pa, pb = pieza_de.get(a), pieza_de.get(b)
        if pa is None or pb is None:
            continue
        if pa == pb:
            internas[pa] += 1
        else:
            dep[pa][pb] += 1
        if a != b:
            entrantes_fn[qn] += 1
            llamadores_fn[qn].add(a)
    for a, b in imports:
        if propio(a) and propio(b):
            pa, pb = pieza_de.get(a), pieza_de.get(b)
            if pa and pb and pa != pb:
                dep[pa][pb] += 0  # cuenta la dependencia aunque no haya llamada resuelta
                dep[pa].setdefault(pb, 0)
    piezas = sorted(set(pieza_de.values()))
    grafo = {p: set(dep[p]) for p in piezas}
    nudos = ciclos(grafo)
    en_nudo = {p for c in nudos for p in c}

    llamado = {qn for _, _, qn in llamadas} | {r[0] for r in referencias} | {u[0] for u in usos}
    info = {}
    for p in piezas:
        arch = [a for a in archivos if pieza_de[a] == p]
        fs = [f for f in funcs if f[2] in arch]
        ce = len(dep[p])                                    # de cuantas piezas depende
        ca = sum(1 for q in piezas if p in dep[q])          # cuantas piezas dependen de ella
        sale = sum(dep[p].values())
        coh = internas[p] / (internas[p] + sale) if internas[p] + sale else 0.0
        inest = ce / (ca + ce) if ca + ce else 0.0
        if p in en_nudo:
            veredicto = "NUDO: en un ciclo de dependencias (si se rompe, arrastra a las otras)"
        elif ca + ce == 0:
            veredicto = ("AISLADA: el indice no le ve conexiones (script suelto, muerto, o lanza/es lanzado por "
                         "subprocess con nombres armados en ejecucion: comprobar)")
        elif coh >= 0.6 and ca + ce <= 3:
            veredicto = "INDEPENDIENTE: buena candidata a pieza/servicio aparte"
        elif ca >= 3 and inest <= 0.3:
            veredicto = "BASE: muchas dependen de ella (tocar con cuidado)"
        else:
            veredicto = "ACOPLADA: depende de varias / varias de ella"
        info[p] = {
            "archivos": [Path(a).name for a in arch], "rutas": arch, "n_archivos": len(arch),
            "funciones": [f[1] for f in fs], "n_funciones": len(fs),
            "lineas": sum(num(f[5]) for f in fs), "docs": [str(f[8]).strip()[:120] for f in fs if f[8]],
            "depende_de": dict(dep[p]), "dependen_de_ella": ca, "ce": ce,
            "cohesion": round(coh, 2), "inestabilidad": round(inest, 2), "veredicto": veredicto,
        }

    # --- funciones fragiles, monstruo, muertas, duplicadas
    qn_info = {f[0]: f for f in funcs}
    fragiles = sorted(((qn, n) for qn, n in entrantes_fn.items() if qn in qn_info), key=lambda x: -x[1])[:15]
    copias = Counter((f[1], num(f[5]), num(f[4])) for f in funcs if str(f[7]).lower() != "true")
    monstruos, vistos_m = [], set()
    for f in sorted((f for f in funcs if str(f[7]).lower() != "true"), key=lambda f: (-num(f[4]), -num(f[5]))):
        clave = (f[1], num(f[5]), num(f[4]))
        if clave not in vistos_m:
            vistos_m.add(clave)
            monstruos.append(f)
        if len(monstruos) >= 15:
            break
    candidatas = [f for f in funcs if f[0] not in llamado
                  and str(f[6]).lower() != "true" and str(f[7]).lower() != "true"
                  and not f[1].startswith("__") and f[1] != "main"]
    es_constructor = lambda f: str(f[0]).split(".")[-2:-1] == [f[1]]  # Clase.Clase (se llama con new)
    muertas = [f for f in candidatas if not FRAMEWORK.match(f[1]) and not es_constructor(f)]
    n_framework = len(candidatas) - len(muertas)
    dupes, vistos = [], set()
    for a, fa, b, fb, j in similares:
        try:
            j = float(j)
        except (TypeError, ValueError):
            continue
        clave = tuple(sorted((a, b)))
        if j >= 0.85 and fa != fb and propio(fa) and propio(fb) and clave not in vistos:
            vistos.add(clave)
            dupes.append((a, fa, b, fb, j))
    dupes.sort(key=lambda x: -x[4])

    explic = explicar_piezas(info) if explicar else {}

    # --- informe
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    destino = SALIDA / f"{fecha}_{proyecto[3:]}"
    destino.mkdir(parents=True, exist_ok=True)
    corto = lambda qn: ".".join(str(qn).split(".")[-2:])
    md = []
    w = md.append
    total_lin = sum(num(f[5]) for f in funcs if propio(f[2]))
    w(f"# Radiografia · {carpeta.name} · {datetime.now():%d/%m/%Y %H:%M}\n")
    w(f"Carpeta: `{carpeta}` · proyecto en el indice: `{proyecto}` (para `impacto` / `cambios`).\n")
    w("## 1. Resumen\n")
    langs = ", ".join(f"{r[0]} ({r[1]})" for r in arq.get("languages", {}).get("rows", [])[:8])
    w(f"- Lenguajes (archivos): {langs or 'sin datos'}")
    w(f"- {len(archivos)} archivos con codigo · {len(funcs)} funciones/metodos · {len(clases)} clases · "
      f"~{total_lin:,} lineas en funciones".replace(",", "."))
    w(f"- {len(piezas)} piezas · {len(nudos)} ciclo(s) de dependencias · {len(dupes)} pares de codigo casi "
      f"duplicado · {len(muertas)} funciones sin llamadas conocidas")
    ent = [r for r in arq.get("entry_points", {}).get("rows", []) if propio(r[1])]
    if ent:
        w(f"- Puntos de entrada ({len(ent)}): " + ", ".join(f"`{r[1]}`" for r in ent[:10]))
    rutas = arq.get("routes", {}).get("rows", [])
    if rutas:
        w(f"- Rutas / llamadas HTTP: " + ", ".join(f"`{(r[0] + ' ' if r[0] else '') + r[1]}`" for r in rutas[:10]))
    if tablas:
        w(f"- Tablas de base de datos: " + ", ".join(f"`{str(t[0]).strip('`[]')}`" for t in tablas[:20]))
    w("")
    w("## 2. Como esta montado (mapa de piezas)\n")
    w("Flecha A --> B = A usa a B (el numero son llamadas). Rojo = en un ciclo.\n")
    w("```mermaid\nflowchart LR")
    ids = {p: f"P{i}" for i, p in enumerate(piezas)}
    for p in piezas:
        w(f'  {ids[p]}["{p} ({info[p]["n_archivos"]})"]')
    for p in piezas:
        for q, n in sorted(dep[p].items(), key=lambda x: -x[1])[:12]:
            w(f"  {ids[p]} -->|{n}| {ids[q]}" if n else f"  {ids[p]} -.-> {ids[q]}")
    for p in en_nudo:
        w(f"  style {ids[p]} fill:#f4cccc,stroke:#c00")
    w("```\n")
    w("## 3. Piezas: que hace cada una y lo independiente que es\n")
    w("Cohesion = cuanto se llama a si misma (alto = bien). Inestabilidad 0 = base de la que dependen; 1 = solo depende de otras.\n")
    w("| Pieza | Archivos | Funciones | Usa a | La usan | Cohesion | Veredicto |")
    w("|---|---|---|---|---|---|---|")
    orden = sorted(piezas, key=lambda p: (p not in en_nudo, -info[p]["dependen_de_ella"], p))
    for p in orden:
        i = info[p]
        w(f"| `{p}` | {i['n_archivos']} | {i['n_funciones']} | {i['ce']} | {i['dependen_de_ella']} | "
          f"{i['cohesion']:.2f} | {i['veredicto'].split(':')[0]} |")
    w("")
    for p in orden:
        i = info[p]
        w(f"**{p}** — {i['veredicto']}")
        if explic.get(p):
            w(f"  - Que hace (Qwen local, comprobar): {explic[p]}")
        else:
            w("  - Que hace: [NOVA: explicalo en 1-2 frases con la ficha de abajo; no leas el codigo]")
        w(f"  - Archivos: {', '.join(i['archivos'][:12])}{' …' if len(i['archivos']) > 12 else ''}")
        clave_fn = [n for n in dict.fromkeys(i["funciones"]) if not FRAMEWORK.match(n) and not n.startswith("_")]
        if clave_fn:
            w(f"  - Funciones: {', '.join(clave_fn[:12])}{' …' if len(clave_fn) > 12 else ''}")
        if i["docs"]:
            w(f"  - Comentarios: {' | '.join(d.replace(chr(10), ' ')[:90] for d in i['docs'][:3])}")
        if i["depende_de"]:
            w(f"  - Usa a: {', '.join(f'{q} ({n})' for q, n in sorted(i['depende_de'].items(), key=lambda x: -x[1]))}")
    w("")
    w("## 4. Ciclos (lo primero a romper para trocear)\n")
    if nudos:
        for c in nudos:
            w(f"- {' <-> '.join(c)}: ninguna de estas piezas se puede separar sola. Romper con una interfaz o mover "
              "lo comun a una pieza base.")
    else:
        w("- Ninguno: las piezas se pueden separar sin arrastrar a otras en circulo. Buena señal.")
    w("")
    w("## 5. Puntos fragiles (si los tocas, se cae mas)\n")
    w("Funciones llamadas desde mas archivos. Antes de cambiarlas: `radiografia.py impacto <proyecto> <funcion>`.\n")
    for qn, n in fragiles[:12]:
        f = qn_info[qn]
        w(f"- `{corto(qn)}` ({f[2]}): {n} llamadas desde {len(llamadores_fn[qn])} archivo(s)")
    if not fragiles:
        w("- No se detectan llamadas entre archivos (scripts sueltos o lenguaje con resolucion textual).")
    w("")
    w("## 6. Funciones monstruo (candidatas a partir)\n")
    w("| Funcion | Archivo | Lineas | Complejidad | Cognitiva |\n|---|---|---|---|---|")
    for f in monstruos[:12]:
        n = copias[(f[1], num(f[5]), num(f[4]))]
        w(f"| `{corto(f[0])}`{f' (x{n} copias)' if n > 1 else ''} | {f[2]} | {num(f[5])} | {num(f[3])} | {num(f[4])} |")
    w("\nCognitiva > 25 o mas de 80 lineas = dificil de entender y de probar: partir en funciones pequenas.\n")
    w("## 7. Codigo duplicado (copiar-pegar)\n")
    por_archivos = Counter(tuple(sorted((fa, fb))) for _, fa, _, fb, _ in dupes)
    if por_archivos:
        w("Archivos que comparten funciones casi iguales (>= 85 %). Muchas = archivo copiado entero.\n")
        for (fa, fb), n in por_archivos.most_common(12):
            w(f"- {n} funcion(es): `{fa}` ≈ `{fb}`")
        if len(por_archivos) > 12:
            w(f"- … y {len(por_archivos) - 12} parejas de archivos mas (datos.json).")
    else:
        w("- Nada relevante (>= 85 % de parecido entre archivos distintos).")
    w("")
    w("## 8. Posible codigo muerto (comprobar antes de borrar)\n")
    w("Nadie lo llama segun el indice. OJO: puede usarse por reflexion, eventos, plantillas o desde fuera.\n")
    for f in sorted(muertas, key=lambda f: f[2])[:20]:
        w(f"- `{corto(f[0])}` ({f[2]})")
    if len(muertas) > 20:
        w(f"- … y {len(muertas) - 20} mas (datos.json).")
    if n_framework:
        w(f"- (No se listan {n_framework} metodos con nombre de framework: get/set, handle_, onClick, toString… "
          "los llama la libreria, no tu codigo.)")
    w("")
    w("## 9. Diagnostico para refactorizar / trocear en piezas\n")
    indep = [p for p in piezas if info[p]["veredicto"].startswith("INDEPENDIENTE")]
    base = [p for p in piezas if info[p]["veredicto"].startswith("BASE")]
    pasos = []
    if nudos:
        pasos.append(f"Romper los {len(nudos)} ciclo(s) de la seccion 4: es lo que impide que un fallo se quede en un solo pedazo.")
    if base:
        pasos.append(f"Blindar las piezas BASE ({', '.join(base[:6])}): tests antes de tocarlas, cambios pequenos.")
    if monstruos and num(monstruos[0][4]) > 25:
        pasos.append(f"Partir las funciones monstruo (empieza por `{corto(monstruos[0][0])}`).")
    if dupes:
        enteros = [k for k, n in por_archivos.items() if n >= 5]
        pasos.append(f"Unificar el codigo duplicado ({len(dupes)} funciones en {len(por_archivos)} parejas de archivos)"
                     + (f"; {len(enteros)} parejas parecen archivos copiados enteros: quedate con uno" if enteros else "")
                     + ".")
    if indep:
        pasos.append(f"Candidatas a pieza/servicio aparte (ya casi independientes): {', '.join(indep[:8])}.")
    if muertas:
        pasos.append(f"Revisar las {len(muertas)} funciones sin llamadas: borrar lo muerto aligera el legacy.")
    for k, s in enumerate(pasos or ["Proyecto pequeno y ordenado: nada urgente."], 1):
        w(f"{k}. {s}")
    w("\n---\nHecho en local con codebase-memory-mcp (indice) + radiografia.py"
      + (" + Qwen (explicaciones)" if explic else "") + ". 0 tokens de nube.")
    (destino / "RADIOGRAFIA.md").write_text("\n".join(md), encoding="utf-8")
    datos = {"proyecto": proyecto, "carpeta": str(carpeta), "piezas": info, "ciclos": nudos,
             "fragiles": fragiles, "duplicados": dupes, "muertas": [f[0] for f in muertas],
             "monstruos": [[f[0], f[2], num(f[5]), num(f[3]), num(f[4])] for f in monstruos]}
    (destino / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Listo en {time.time() - t0:.0f} s: {destino / 'RADIOGRAFIA.md'}")
    print(f"Proyecto en el indice: {proyecto}")
    return destino


# ------------------------------------------------------------------ impacto / cambios
def impacto(proyecto: str, funcion: str, profundidad: int) -> None:
    print(f"Si cambias `{funcion}`, esto la usa (hasta {profundidad} saltos hacia atras):\n")
    print(cbm("trace_path", project=proyecto, function_name=funcion, direction="inbound",
              depth=profundidad, risk_labels=True))


def cambios(proyecto: str) -> None:
    print("Impacto de los cambios sin commit (git diff) sobre el resto del proyecto:\n")
    print(cbm("detect_changes", project=proyecto, scope="impact", depth=2))


# ------------------------------------------------------------------ mapa visual
def _vivo(pid: int) -> bool:
    if os.name != "nt":  # v3.3: macOS/Linux
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                       creationflags=SIN_VENTANA)
    return str(pid) in r.stdout


def _matar(pid: int) -> None:
    if os.name != "nt":
        import signal

        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)  # el guardian va en su propia sesion: cae con su servidor
        except OSError:
            pass
        return
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=SIN_VENTANA)


def mapa(cerrar: bool, minutos: int) -> None:
    estado = json.loads(ESTADO_MAPA.read_text()) if ESTADO_MAPA.exists() else {}
    if cerrar:
        for clave in ("guardian", "servidor"):
            pid = estado.get(clave)
            if pid and _vivo(pid):
                _matar(pid)
        ESTADO_MAPA.unlink(missing_ok=True)
        subprocess.run([str(EXE), "config", "set", "ui_enabled", "false"], capture_output=True,
                       env=dict(os.environ, CBM_CACHE_DIR=str(CACHE)), creationflags=SIN_VENTANA)
        print("Mapa cerrado.")
        return
    if estado.get("guardian") and _vivo(estado["guardian"]):
        print(f"El mapa ya esta abierto: http://127.0.0.1:{PUERTO}")
        return
    # un guardian oculto mantiene vivo el visor (se cierra solo al llegar al tiempo)
    pyw = Path(sys.executable).with_name("pythonw.exe")
    extra = ({"creationflags": SIN_VENTANA | 0x00000008 | 0x00000200} if os.name == "nt"  # oculto y desligado
             else {"start_new_session": True})  # v3.3: macOS/Linux, sigue vivo aunque se cierre la terminal
    g = subprocess.Popen([str(pyw if pyw.exists() else sys.executable), str(Path(__file__)), "_guardian_mapa",
                          str(minutos)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, **extra)
    for _ in range(40):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}", timeout=1)
            print(f"Mapa abierto: http://127.0.0.1:{PUERTO}  (se cierra solo en {minutos} min; "
                  "cerrar ya: radiografia.py mapa --cerrar)")
            return
        except Exception:
            pass
    print(f"El visor no respondio en 20 s (guardian PID {g.pid}). Prueba otra vez o cierra con --cerrar.")


def _guardian_mapa(minutos: int) -> None:
    env = dict(os.environ, CBM_CACHE_DIR=str(CACHE))
    srv = subprocess.Popen([str(EXE), f"--ui=true", f"--port={PUERTO}"], stdin=subprocess.PIPE,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, creationflags=SIN_VENTANA)
    ESTADO_MAPA.write_text(json.dumps({"guardian": os.getpid(), "servidor": srv.pid,
                                       "hasta": time.time() + minutos * 60}))
    try:
        srv.wait(timeout=minutos * 60)
    except subprocess.TimeoutExpired:
        srv.kill()
    finally:
        subprocess.run([str(EXE), "config", "set", "ui_enabled", "false"], capture_output=True, env=env,
                       creationflags=SIN_VENTANA)
        ESTADO_MAPA.unlink(missing_ok=True)


# ------------------------------------------------------------------ main
def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "_guardian_mapa":
        _guardian_mapa(int(sys.argv[2]))
        return
    ap = argparse.ArgumentParser(description="Radiografia de proyectos de codigo (codebase, local).")
    sub = ap.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("analizar"); a.add_argument("carpeta"); a.add_argument("--nombre")
    a.add_argument("--explicar", action="store_true"); a.add_argument("--profundidad", type=int)
    a.add_argument("--excluir", help="carpetas a ignorar, separadas por comas (p. ej. archivo,tests)")
    i = sub.add_parser("impacto"); i.add_argument("proyecto"); i.add_argument("funcion")
    i.add_argument("--profundidad", type=int, default=3)
    c = sub.add_parser("cambios"); c.add_argument("proyecto")
    m = sub.add_parser("mapa"); m.add_argument("--cerrar", action="store_true"); m.add_argument("--minutos", type=int, default=60)
    sub.add_parser("proyectos")
    x = ap.parse_args()
    try:
        if x.orden == "analizar":
            analizar(Path(x.carpeta), x.nombre, x.explicar, x.profundidad, x.excluir)
        elif x.orden == "impacto":
            impacto(x.proyecto, x.funcion, x.profundidad)
        elif x.orden == "cambios":
            cambios(x.proyecto)
        elif x.orden == "mapa":
            mapa(x.cerrar, x.minutos)
        else:
            print(cbm("list_projects"))
    except RuntimeError as e:
        sys.exit(f"Fallo del codebase: {e}")


if __name__ == "__main__":
    main()
