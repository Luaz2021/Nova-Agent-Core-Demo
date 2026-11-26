r"""NOVA DIRECTOR · orquestador casero por fases (26/11/2026, Claude; idea y prueba A/B del usuario).

"El arquitecto no vive en la obra": los modelos caros entran con un PAQUETE pequeno, deciden y se van.
Cada llamada es una conversacion NUEVA de la CLI de Antigravity (`agy -p`), sin el chat de nadie:

  1. PLANOS      (Neon High)        idea + radiografia -> .director\arquitectura.md + .director\fases.json
  2. OBRA        (Hydrogen High)    una conversacion por fase, solo con su ficha; en paralelo las que no dependen
                                    entre si ni tocan los mismos archivos. Tras cada fase, los CRITERIOS (comandos)
                                    los comprueba el director, no el modelo. Falla -> 2o intento en la misma
                                    conversacion (cache) -> Neon High -> Carbon -> se para y avisa.
  3. INSPECCION  (Neon Extra High)  escaneres (nova_seguridad.py) + diff de TODO el proyecto + criterios ->
                                    hallazgos.json. Critico/alto -> Hydrogen arregla solo eso -> criterios ->
                                    reinspeccion corta (Neon High, solo el diff del arreglo).

Uso (desde cualquier sitio; el proyecto es la carpeta de trabajo de los modelos):
  <PYTHON> nova_director.py todo       <proyecto> --idea TAREA.md [--radiografia RADIOGRAFIA.md]
  <PYTHON> nova_director.py planos     <proyecto> --idea TAREA.md [--radiografia ...]
  <PYTHON> nova_director.py obra       <proyecto>
  <PYTHON> nova_director.py inspeccion <proyecto>
  <PYTHON> nova_director.py estado     <proyecto>
  <PYTHON> nova_director.py modelos            (comprueba que los slugs de director.json existen en `agy models`)

Todo queda en <proyecto>\.director\ (estado.json con el gasto por llamada, paquetes, informes, foto inicial).
Ajustes en director.json (modelos, paralelo, intentos, presupuesto). Prueba sin gastar: DIRECTOR_AGY=<simulador>.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 26/11 (el usuario: "me saltan muchas ventanas negras"): lanzado con pythonw (sin consola), CADA programa de consola que
# arranca el director (agy, powershell de los criterios, escaneres, tasklist) abria su propia ventana. Todo sin ventana.
SIN_VENTANA = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


# v3.3: piezas de sistema (Windows / macOS / Linux) ----------------------------------------------------------------
WIN, MAC = os.name == "nt", sys.platform == "darwin"


def _vivo(pid) -> bool:
    if not pid:
        return False
    if not WIN:
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, ValueError):
            return False
    try:
        p = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=20,
                           creationflags=SIN_VENTANA)
        return str(pid) in p.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def _matar_arbol(pid) -> None:
    """Para un proceso y sus hijos (el servidor de la app, uvicorn...)."""
    if WIN:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, creationflags=SIN_VENTANA)
        return
    import signal

    try:
        os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
    except (OSError, ValueError):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except (OSError, ValueError):
            pass


def _sonar(wav=None) -> None:
    """Un clip .wav (o un pitido si no hay) en los 3 sistemas, sin ventanas."""
    try:
        if WIN:
            import winsound

            if wav:
                winsound.PlaySound(str(wav), winsound.SND_FILENAME)
            else:
                for _ in range(3):
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    time.sleep(0.6)
            return
        if wav:
            for prog in (["afplay"] if MAC else ["paplay", "aplay"]):
                if shutil.which(prog):
                    subprocess.run([prog, str(wav)], capture_output=True, timeout=60)
                    return
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


def _devtools_port_dirs() -> list:
    """Donde deja Antigravity su DevToolsActivePort en cada sistema (aviso en el chat por el puerto de depuracion)."""
    if WIN:
        base = Path(os.environ.get("APPDATA", ""))
    elif MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return [base / "Antigravity", base / "antigravity"]
_run_original = subprocess.run


def _run_sin_ventana(*args, **kwargs):
    kwargs.setdefault("creationflags", SIN_VENTANA)
    return _run_original(*args, **kwargs)


subprocess.run = _run_sin_ventana

AQUI = Path(__file__).resolve().parent
CONFIG = AQUI / "director.json"
NOVA = Path.home() / ".gemini" / "antigravity"
SEGURIDAD = NOVA / "herramientas" / "seguridad" / "nova_seguridad.py"
IGNORAR = {".director", ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
           ".mypy_cache", "dist", "build", ".idea", ".vscode"}
EXT_TEXTO = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".xml", ".json", ".md", ".txt", ".html", ".css",
             ".sql", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".properties", ".gradle", ".sh", ".ps1", ".env.example"}
CANDADO = threading.Lock()


# ----------------------------------------------------------------------------------------------- utilidades
def cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def log(proy: Path, texto: str) -> None:
    linea = f"[{time.strftime('%H:%M:%S')}] {texto}"
    print(linea, flush=True)
    with CANDADO, open(proy / ".director" / "director.log", "a", encoding="utf-8") as f:
        f.write(linea + "\n")


ERRORES = Path.home() / ".gemini" / "antigravity" / "memory" / "registros" / "director_errores.jsonl"


def registrar_error(proy: Path, tipo: str, **datos) -> None:
    """26/11 noche (el usuario: "los errores deben ir apuntados para la revision semanal y cazar lo que falla"): un registro
    central de TODO lo que va mal en el director (viaja por Drive; lo resume nova_revisor.py seccion 9).
    tipo: fase_falla | cli_error | pausa | parado | inspeccion_sin_informe."""
    fila = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "proyecto": proy.name, "tipo": tipo}
    fila.update({k: (str(v)[:800] if isinstance(v, str) else v) for k, v in datos.items()})
    try:
        ERRORES.parent.mkdir(parents=True, exist_ok=True)
        with CANDADO, open(ERRORES, "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    except OSError:
        pass


def leer_estado(proy: Path) -> dict:
    try:
        return json.loads((proy / ".director" / "estado.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"llamadas": [], "fases": {}, "etapa": "nueva"}


def guardar_estado(proy: Path, e: dict) -> None:
    with CANDADO:
        (proy / ".director" / "estado.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def familia(slug: str) -> str:
    s = slug.lower()
    return "neon" if "neon" in s else "carbon" if "carbon" in s else "hydrogen"


def gasto(uso: dict) -> tuple[int, int, int]:
    """(nuevos, cache, salida) de lo que devuelva la CLI en 'usage', sin depender de los nombres exactos."""
    nuevos = cache = salida = 0
    for k, v in (uso or {}).items():
        if not isinstance(v, (int, float)):
            continue
        k = k.lower()
        if "cache" in k:
            cache += int(v)
        elif "total" in k:
            continue
        elif "output" in k or "thinking" in k or "candidates" in k or "completion" in k:
            salida += int(v)
        elif "input" in k or "prompt" in k:
            nuevos += int(v)
    return nuevos, cache, salida


def ponderado_total(e: dict) -> int:
    return int(sum(x.get("ponderado", 0) for x in e["llamadas"]))


# --------------------------------------------------------------------------------------- llamar a la CLI agy
def comando_agy(c: dict) -> list[str]:
    sim = os.environ.get("DIRECTOR_AGY")
    if sim:
        return [sys.executable, sim]
    agy = c.get("agy", "agy")
    if isinstance(agy, list):
        return list(agy)
    if not shutil.which(agy):  # el instalador avisa de que puede no estar en el PATH de esta consola
        exe = "agy.exe" if WIN else "agy"  # v3.3: macOS/Linux
        for p in (Path.home() / "agy" / "bin" / exe, Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / exe,
                  Path.home() / ".local" / "bin" / exe, Path("/opt/homebrew/bin") / exe, Path("/usr/local/bin") / exe):
            if p.exists():
                return [str(p)]
    return [agy]


def llamar(proy: Path, rol: str, modelo_clave: str, paquete: Path, conversacion: str | None = None) -> dict:
    """Una llamada sin ventana. El prompt es corto: el paquete va en un archivo (la linea de comandos de Windows
    corta a ~32k caracteres). Devuelve {ok, respuesta, conversacion}."""
    c = cfg()
    slug = c["modelos"][modelo_clave]
    e = leer_estado(proy)
    if ponderado_total(e) > c["presupuesto_ponderado"]:
        raise SystemExit(f"[DIRECTOR] PRESUPUESTO agotado ({ponderado_total(e)} > {c['presupuesto_ponderado']}): "
                         "se para aqui. Sube 'presupuesto_ponderado' en director.json si el usuario lo aprueba.")
    prompt = (f"[NOVA DIRECTOR · {rol}] Lee ENTERO el paquete {paquete} y haz exactamente lo que pide. "
              "No abras el chat de nadie ni archivos que el paquete no necesite. Trabaja en esta carpeta.")
    # 26/11 (probado): sin ventana la CLI solo confia en System32 -> el terminal da "acceso denegado" en el proyecto.
    # La carpeta del proyecto se marca confiable SOLO para esta llamada (--settings no se guarda).
    ajustes = json.dumps({"trustedWorkspaces": [str(proy)]})
    cmd = (comando_agy(c) + ["-p", prompt, "--model", slug, "--output-format", "json", "--settings", ajustes]
           + list(c.get("args_extra", [])))
    if conversacion:
        cmd += ["--conversation", conversacion]
    t0 = time.time()
    log(proy, f"-> {rol} con {slug}{' (misma conversacion)' if conversacion else ''}")
    try:
        p = subprocess.run(cmd, cwd=proy, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=c["timeout_llamada_s"])
        salida, err, codigo = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        salida, err, codigo = "", "timeout", -1
    except FileNotFoundError:
        raise SystemExit("[DIRECTOR] No encuentro la CLI 'agy'. Instalala (ver LEEME.md) o ajusta 'agy' en director.json.")
    try:
        r = json.loads(salida.strip().splitlines()[-1]) if salida.strip() else {}
    except (ValueError, IndexError):
        r = {"response": salida[-2000:]}
    nuevos, cache, sal = gasto(r.get("usage") or {})
    acum = {"nuevos": nuevos, "cache": cache, "salida": sal}
    # 26/11 (medido en la v3): al CONTINUAR una conversacion (--conversation) agy devuelve el uso ACUMULADO de toda
    # la conversacion, no el de esta llamada -> se resta lo ya contado de esa conversacion.
    if conversacion:
        previas = [x for x in leer_estado(proy)["llamadas"] if x.get("conversacion") == conversacion]
        if previas:
            ult = previas[-1].get("acum") or {k: previas[-1][k] for k in acum}
            nuevos, cache, sal = (max(0, acum[k] - ult.get(k, 0)) for k in ("nuevos", "cache", "salida"))
    real = nuevos + cache * 0.1 + sal
    fila = {"rol": rol, "modelo": slug, "segundos": round(time.time() - t0), "codigo": codigo,
            "estado": r.get("status"), "conversacion": r.get("conversation_id") or conversacion,
            "nuevos": nuevos, "cache": cache, "salida": sal, "acum": acum,
            "ponderado": int(real * cfg()["peso"].get(familia(slug), 1))}
    with CANDADO:
        e = leer_estado(proy)
        e["llamadas"].append(fila)
    guardar_estado(proy, e)
    ok = codigo == 0 and str(r.get("status") or "ok").lower() not in ("error", "failed", "denied")
    if not ok:
        log(proy, f"   {rol}: la CLI devolvio codigo {codigo} / {r.get('status')} {err[-300:]}")
        registrar_error(proy, "cli_error", rol=rol, modelo=slug, codigo=codigo, estado=str(r.get("status")),
                        detalle=err[-300:])
    return {"ok": ok, "respuesta": str(r.get("response") or ""), "conversacion": fila["conversacion"]}


# ------------------------------------------------------------------------------------- foto y diff del proyecto
def archivos_texto(raiz: Path) -> dict[str, Path]:
    out = {}
    for p in raiz.rglob("*"):
        rel = p.relative_to(raiz)
        if any(parte in IGNORAR for parte in rel.parts) or not p.is_file():
            continue
        if p.name.lower() == "desktop.ini":  # 26/11: Google Drive lo pone en cada carpeta, en UTF-16 (bytes nulos)
            continue
        if (p.suffix.lower() in EXT_TEXTO or p.name in ("Dockerfile", "requirements.txt")) and p.stat().st_size < 400_000:
            with open(p, "rb") as fh:
                if b"\x00" in fh.read(8192):  # binario o UTF-16: agy rechaza un paquete con bytes nulos
                    continue
            out[str(rel)] = p
    return out


def git_excluir(proy: Path) -> None:
    """26/11 noche (D6, ramas del trabajo): si el proyecto es un repo git, `.director/` va a .git/info/exclude (local,
    no toca el .gitignore del repo) para que nunca se suba. El director nunca hace commit/push (regla de la ficha)."""
    ex = proy / ".git" / "info" / "exclude"
    if not (proy / ".git").is_dir():
        return
    try:
        texto = ex.read_text(encoding="utf-8") if ex.exists() else ""
        if ".director/" not in texto:
            ex.parent.mkdir(parents=True, exist_ok=True)
            ex.write_text(texto.rstrip("\n") + ("\n" if texto else "") + ".director/\n", encoding="utf-8")
    except OSError:
        pass


def foto(proy: Path) -> None:
    destino = proy / ".director" / "foto_inicial"
    if destino.exists():
        return
    for rel, p in archivos_texto(proy).items():
        (destino / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, destino / rel)
    destino.mkdir(parents=True, exist_ok=True)


def diff(proy: Path, base: Path, limite: int) -> str:
    ahora, antes = archivos_texto(proy), archivos_texto(base) if base.exists() else {}
    trozos = []
    for rel in sorted(set(ahora) | set(antes)):
        a = antes[rel].read_text(encoding="utf-8", errors="replace").splitlines() if rel in antes else []
        b = ahora[rel].read_text(encoding="utf-8", errors="replace").splitlines() if rel in ahora else []
        if a != b:
            trozos.append("\n".join(difflib.unified_diff(a, b, f"antes/{rel}", f"ahora/{rel}", lineterm="", n=2)))
    texto = "\n\n".join(trozos).replace("\x00", "")
    if len(texto) > limite:
        texto = texto[:limite] + f"\n\n[... diff cortado en {limite} caracteres: lee tu los archivos que falten]"
    return texto


# ------------------------------------------------------------------------------------------------ criterios
def comprobar(proy: Path, criterios: list[str]) -> tuple[bool, str]:
    """Los criterios los ejecuta el director (maquina = gratis). Devuelve (todo_ok, informe con los errores)."""
    informe, ok = [], True
    for cmd in criterios:
        try:
            shell = (["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd] if WIN
                     else ["bash", "-lc", cmd])  # v3.3: en macOS/Linux los criterios van en bash
            p = subprocess.run(shell, cwd=proy,
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=cfg()["timeout_criterio_s"])
            bien, texto = p.returncode == 0, (p.stdout + p.stderr)
        except subprocess.TimeoutExpired:
            bien, texto = False, "TIMEOUT"
        ok &= bien
        informe.append(f"$ {cmd}\n-> {'OK' if bien else 'FALLA'}\n" + ("" if bien else texto[-3000:]))
    return ok, "\n".join(informe)


# ---------------------------------------------------------------------------------------------------- PLANOS
FORMATO_FASES = """{
  "ruta": "sin_ui | con_ui | web_negocio | clon | legacy",
  "fases": [
    {"id": "F1", "titulo": "...", "objetivo": "que debe quedar hecho (2-4 lineas)",
     "herramienta": "obra | pausa",
     "skills": ["0-2 indices de la lista INDICES DE SKILLS que esta fase necesita, p. ej. index-security-deploy"],
     "instrucciones_nova": "solo en 'pausa': que debe hacer Nova con que herramienta y que tiene que quedar",
     "archivos": ["ruta/relativa.py", "..."],
     "depende_de": [],
     "criterios": ["comando (PowerShell en Windows, bash en macOS/Linux) que sale con codigo 0 si la fase esta bien"],
     "critica": false}
  ]
}"""
CATALOGO = AQUI / "catalogo.md"
SKILLS = Path.home() / ".gemini" / "config" / "skills"
SKILL_AUDITORIA = NOVA / "almacen" / "skills" / "security-audit-cloudflare" / "SKILL.md"


def indices_skills() -> str:
    """26/11 noche (el usuario: "el full stack se beneficia de TODAS las skills: ciberseguridad, diseno, backend..."): los
    indices de skills de Nova (config\\skills\\index-*) con su descripcion, para que el arquitecto asigne a cada fase
    los que necesita y el director se los meta en el sobre."""
    lineas = []
    for p in sorted(SKILLS.glob("index-*/SKILL.md")):
        desc = ""
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()[:12]:
            if ln.lower().startswith("description:"):
                desc = ln.split(":", 1)[1].strip().strip('"')[:160]
                break
        lineas.append(f"- `{p.parent.name}`: {desc}")
    return "\n".join(lineas)


class Pausa(Exception):
    """El director se para a proposito: preguntas para el usuario o una fase 'pausa' (diseno, vale...)."""


def pausar(proy: Path, titulo: str, texto: str) -> None:
    (proy / ".director" / "PAUSA.md").write_text(
        f"# EN PAUSA · {titulo}\n\n{texto}\n\nCuando este hecho: `<PYTHON> nova_director.py lanzar \"{proy}\" "
        "--continuar` (Nova) o `continuar` (a mano).\n", encoding="utf-8")
    e = leer_estado(proy)
    e["etapa"] = "pausa"
    guardar_estado(proy, e)
    log(proy, f"PAUSA: {titulo}")
    registrar_error(proy, "pausa", titulo=titulo, detalle=texto[:600])
    raise Pausa(titulo)


def planos(proy: Path, idea: Path, radiografia: Path | None) -> None:
    """v4 (26/11): ESPECIFICAR + PLANOS en una llamada. Con el CATALOGO de herramientas elige la ruta (con/sin UI...),
    escribe spec.md con criterios de aceptacion y, si falta un dato que cambia el diseno, PREGUNTA en vez de suponer
    (la especificacion floja es ~40 % de los fallos de sistemas multiagente: MAST, Berkeley 2025)."""
    d = proy / ".director"
    d.mkdir(exist_ok=True)
    foto(proy)
    respuestas = d / "respuestas.md"
    (d / "fases.json").unlink(missing_ok=True)
    paquete = d / "paquete_planos.md"
    paquete.write_text(
        "# PAQUETE · ESPECIFICAR Y PLANOS (eres el ARQUITECTO: entras, decides y te vas)\n\n"
        "## Que tienes que hacer\n"
        f"1. Escribe `{d / 'spec.md'}` (maximo 60 lineas): objetivo, usuarios y roles, la RUTA elegida del catalogo y "
        "por que, requisitos numerados R1..Rn cada uno con su criterio 'CUANDO ..., EL SISTEMA DEBE ...', pantallas o "
        "endpoints, datos, y 'Fuera de alcance'.\n"
        f"2. Escribe `{d / 'preguntas.json'}`: {{\"bloqueantes\": [\"...\"], \"supuestos\": [\"lo que decidiste tu y por que\"]}}. "
        "Bloqueante = un dato que cambia el diseno y no esta en el enunciado ni en las respuestas (no preguntes "
        "gustos ni lo que puedas decidir con sentido comun).\n"
        "3. SOLO si no hay bloqueantes:\n"
        f"   a. `{d / 'arquitectura.md'}` (maximo 60 lineas): modulos, capas, datos, seguridad (de donde salen las claves, "
        "como se guardan contrasenas y dinero), riesgos. Si hay back y front: el CONTRATO (endpoints con entrada/salida) "
        "para que puedan ir en paralelo.\n"
        f"   b. `{d / 'fases.json'}` con EXACTAMENTE este formato:\n```json\n{FORMATO_FASES}\n```\n"
        "Reglas de las fases:\n"
        "- Sigue las cajas de la RUTA del catalogo. Tamano: 1-2 archivos -> 1 fase; mediano 2-3; grande 3-5; nunca >6. "
        "Cada fase de tamano MEDIO que un modelo rapido (Hydrogen) pueda hacer sin alucinar.\n"
        "- `herramienta: pausa` para lo que necesita al usuario o una herramienta interactiva (estudio web, clonador): "
        "el director se para y Nova lo hace con `instrucciones_nova`; sus `criterios` comprueban que quedo hecho.\n"
        "- Se breve: decide y escribe, sin explorar el disco ni ejecutar nada.\n"
        "- `archivos`: los que la fase CREA o MODIFICA. Dos fases que tocan el mismo archivo NO pueden ir en paralelo: "
        "ponlas en `depende_de`.\n"
        "- `criterios`: comandos que comprueban SOLO lo de esa fase y lo anterior (py_compile, tests de ESA parte con "
        "-k o su archivo, compilar). NUNCA tests de fases futuras: fallarian por fuerza. La ultima fase pasa TODO.\n"
        f"- Los `criterios` se ejecutan en {'PowerShell (Windows)' if WIN else 'bash (' + ('macOS' if MAC else 'Linux') + ')'}: "
        "escribelos con esa sintaxis.\n"
        "- Proyecto en una carpeta sincronizada (Google Drive, OneDrive, iCloud) y Python: "
        "`uv run --with-requirements requirements.txt <comando>` (nada de .venv dentro de esa carpeta).\n"
        "- `critica: true` si toca autenticacion, claves, permisos, dinero o datos personales.\n"
        "- NO escribas codigo ni toques nada fuera de .director. No leas otros archivos salvo los de este paquete "
        "y, si existen, los tests del proyecto (sin modificarlos).\n\n"
        f"## CATALOGO DE HERRAMIENTAS Y RUTAS\n\n{CATALOGO.read_text(encoding='utf-8', errors='replace')}\n\n"
        "## INDICES DE SKILLS DE NOVA (asigna a cada fase en `skills` los 0-2 que necesite: auth/permisos/claves -> "
        "seguridad; pantallas -> ui-frontend; BD/API -> backend-db; Android -> mobile; 3D/animacion -> motion-3d...)\n\n"
        f"{indices_skills()}\n\n"
        f"## Idea / enunciado\n\n{idea.read_text(encoding='utf-8', errors='replace')}\n\n"
        + (f"## RESPUESTAS DEL USUARIO A TUS PREGUNTAS\n\n{respuestas.read_text(encoding='utf-8', errors='replace')}\n\n"
           if respuestas.exists() else "")
        + (f"## Radiografia del proyecto existente\n\n{radiografia.read_text(encoding='utf-8', errors='replace')}\n"
           if radiografia else "## Proyecto\n\nNuevo (no hay codigo previo salvo los tests si los hay).\n"),
        encoding="utf-8")
    log(proy, "ESPECIFICAR + PLANOS")
    r = llamar(proy, "PLANOS", "planos", paquete)
    try:
        bloqueantes = json.loads((d / "preguntas.json").read_text(encoding="utf-8")).get("bloqueantes") or []
    except (OSError, ValueError):
        bloqueantes = []
    if bloqueantes and not (d / "fases.json").exists():
        pausar(proy, "preguntas para el usuario", "Antes de disenar falta saber:\n" + "\n".join(
            f"{i}. {q}" for i, q in enumerate(bloqueantes, 1)) + f"\n\nNova: preguntaselas al usuario y escribe sus "
            f"respuestas (numeradas) en `{respuestas}`.")
    fases = validar_fases(proy)
    if not r["ok"] or not fases:
        raise SystemExit("[DIRECTOR] Los planos no salieron bien (mira .director\\director.log). Se para aqui.")
    e = leer_estado(proy)
    e["etapa"] = "planos"
    e["ruta"] = json.loads((d / "fases.json").read_text(encoding="utf-8")).get("ruta", "?")
    e["fases"] = {f["id"]: {"estado": "pendiente"} for f in fases}
    guardar_estado(proy, e)
    log(proy, f"PLANOS OK: ruta {e['ruta']} · {len(fases)} fases ({sum(f.get('critica', False) for f in fases)} "
              f"criticas, {sum(f.get('herramienta') == 'pausa' for f in fases)} pausas)")


def validar_fases(proy: Path) -> list[dict]:
    try:
        fases = json.loads((proy / ".director" / "fases.json").read_text(encoding="utf-8"))["fases"]
        ids = {f["id"] for f in fases}
        for f in fases:
            assert f["id"] and f["objetivo"] and isinstance(f["archivos"], list) and f["criterios"]
            assert all(x in ids for x in f.get("depende_de", []))
        return fases
    except (OSError, ValueError, KeyError, AssertionError, TypeError) as ex:
        log(proy, f"fases.json no valido: {ex!r}")
        return []


# ------------------------------------------------------------------------------------------------------ OBRA
def lecturas_del_arnes(proy: Path, f: dict) -> str:
    """26/11 noche (el usuario: "te pasas por los huevos el arnes que tu mismo armaste"): la ficha de obra NO llevaba los kits
    de Nova ni sus skills ni referencias -> Hydrogen disenaba a ciegas. Ahora, como Nova con sus carriles: segun los
    archivos de la fase, el kit de su carril (nova_carriles.por_ruta) + en front el indice de diseno, los tokens del
    estudio y las IMAGENES de referencia del proyecto (diseno\\referencias\\: Mobbin, capturas del clonador...)."""
    kits: list[str] = []
    try:
        sys.path.insert(0, str(Path.home() / ".gemini" / "nova_core"))
        import nova_carriles
        for a in f.get("archivos", []):
            for c in nova_carriles.por_ruta(str(proy / a)):
                k = str(nova_carriles.kit(c))
                if k not in kits and Path(k).exists():
                    kits.append(k)
    except Exception:
        pass
    for s in f.get("skills") or []:  # los indices que el arquitecto asigno a esta fase
        p = SKILLS / str(s).strip() / "SKILL.md"
        if p.exists() and str(p) not in kits:
            kits.append(str(p))
    carriles_dir = NOVA / "herramientas" / "carriles"
    por_ext = {".html": "carril_web.md", ".css": "carril_web.md", ".js": "carril_web.md", ".jsx": "carril_web.md",
               ".tsx": "carril_web.md", ".vue": "carril_web.md", ".py": "carril_backend.md", ".sql": "carril_backend.md",
               ".java": str(Path.home() / ".gemini" / "config" / "skills" / "index-java" / "SKILL.md"),
               ".kt": str(Path.home() / ".gemini" / "config" / "skills" / "index-mobile-dev" / "SKILL.md")}
    for a in f.get("archivos", []):
        k = por_ext.get(Path(a).suffix.lower())
        if k:
            k = str(carriles_dir / k) if not Path(k).is_absolute() else k
            if k not in kits and Path(k).exists():
                kits.append(k)
    front = any(Path(a).suffix.lower() in (".html", ".css", ".js", ".jsx", ".tsx", ".vue") for a in f.get("archivos", []))
    extra: list[str] = []
    if front:
        ui = Path.home() / ".gemini" / "config" / "skills" / "index-ui-frontend" / "SKILL.md"
        if ui.exists() and str(ui) not in kits:
            kits.append(str(ui))
        tokens = proy / "estudio" / "estilos" / "00_tokens.css"
        if tokens.exists():
            extra.append(f"- Tokens del estudio (usa SOLO estas variables): `{tokens}`")
        refs = sorted((proy / "diseno" / "referencias").glob("*.png"))[:4] if (proy / "diseno").exists() else []
        if refs:
            extra.append("- REFERENCIAS REALES (miralas con read_file ANTES de componer; copia su composicion y densidad, "
                         "no su contenido): " + ", ".join(f"`{r}`" for r in refs))
        adn = proy / "diseno" / "adn.json"
        if adn.exists():
            extra.append(f"- ADN de diseno de esas referencias: `{adn}`")
        extra.append("- NADA de lo generico de IA: eyebrow en mayusculas sobre el titulo, badge encima del H1, 3 tarjetas "
                     "identicas con icono, pasos 1-2-3, franjas de cifras, degradados, brillos, glass, logo de iniciales, "
                     "copy de marketing ('sin friccion', 'siguiente nivel') en pantallas de trabajo. Una app de uso diario "
                     "ensena DATOS y ACCIONES, no un discurso.")
    if not kits and not extra:
        return ""
    return ("## Antes de escribir: lee en UNA llamada en paralelo (es lo esencial de tus skills de este tema)\n"
            + "\n".join(f"- `{k}`" for k in kits) + ("\n" if kits else "") + "\n".join(extra) + "\n\n")


def ficha(proy: Path, f: dict, extra: str = "") -> Path:
    d = proy / ".director" / "fases"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{f['id']}{'_arreglo' if extra else ''}.md"
    p.write_text(
        f"# FICHA DE OBRA · {f['id']} · {f['titulo']}\n\n"
        f"Arquitectura (leela si necesitas contexto): `{proy / '.director' / 'arquitectura.md'}`\n\n"
        f"## Objetivo\n{f['objetivo']}\n\n"
        + lecturas_del_arnes(proy, f)
        + "## Archivos que creas o modificas (solo estos)\n" + "\n".join(f"- `{a}`" for a in f["archivos"]) + "\n\n"
        "## Cuando acabes, esto tiene que salir con codigo 0 (lo comprueba el director, pruebalo tu antes)\n"
        + "\n".join(f"- `{c}`" for c in f["criterios"]) + "\n\n"
        "## Reglas\n- Cambios por fragmentos (edit_file) en archivos que ya existen; no reescribas archivos enteros.\n"
        "- No modifiques tests ni archivos de otras fases. No pidas confirmacion: haz la fase entera.\n"
        "- Nunca claves/contrasenas con valor por defecto en el codigo; dinero con Decimal.\n"
        "- Archivos de web (.html/.css/.js): MAXIMO 150 lineas cada uno (el hook frena los mas grandes): parte en "
        "modulos desde el principio (p. ej. js/api.js, js/vistas_cliente.js, css/base.css, css/componentes.css).\n"
        "- Herramientas de Nova (estudio web, revisar.py...): `& $env:NOVA_PYTHON \"<script>\" ...` (python a secas NO "
        "funciona aqui). El codigo del proyecto: `uv run --with-requirements requirements.txt ...`.\n"
        "- Git: NUNCA commit, push, checkout, reset ni clean (eso lo decide el usuario).\n"
        "- Si el hook te frena algo que de verdad necesitas, NO lo esquives: dilo en tu respuesta final (que y por que).\n"
        + (f"\n## LO QUE FALLO EN EL INTENTO ANTERIOR (arreglalo)\n```\n{extra}\n```\n" if extra else ""),
        encoding="utf-8")
    return p


def hacer_fase(proy: Path, f: dict, conv: str | None = None) -> tuple[bool, str | None]:
    """v3 (26/11): `conv` = conversacion de Hydrogen que ya hizo fases anteriores de esta misma linea -> la fase
    entra en ella y reaprovecha la cache (en la v2 cada fase nueva pagaba ~50k de entrada). Devuelve (ok, conv)."""
    c = cfg()
    errores = ""
    desde = time.strftime("%Y-%m-%d %H:%M:%S")
    convs: list[str] = []
    # escalera: Hydrogen (intentos_obra, todos en su conversacion = cache) -> Neon -> Carbon (conversaciones nuevas)
    pasos = [("obra", True)] * c["intentos_obra"] + [("arreglo", False), ("arreglo_2", False)]
    for i, (clave, misma_conv) in enumerate(pasos):
        if clave != "obra" and (frenos := frenos_hook(convs, desde)):
            # 26/11 noche (D2c): si Hydrogen fallo y el HOOK le freno algo, Neon/Carbon chocarian con el mismo freno:
            # se PAUSA y el usuario decide (el "dale seguir" por proyecto: .director\permisos.json)
            pausar(proy, f"{f['id']} · el hook freno algo que la fase necesita", texto_frenos(proy, f, frenos))
        paquete = ficha(proy, f, errores)
        r = llamar(proy, f"OBRA {f['id']} intento {i + 1}", clave, paquete, conv if misma_conv else None)
        if clave == "obra":
            conv = r["conversacion"]
        if r["conversacion"]:
            convs.append(r["conversacion"])
        ok, errores = comprobar(proy, f["criterios"])
        log(proy, f"   {f['id']} intento {i + 1} ({c['modelos'][clave]}): {'OK' if ok else 'FALLA criterios'}")
        if ok:
            return True, conv
        registrar_error(proy, "fase_falla", fase=f["id"], titulo=f["titulo"], intento=i + 1,
                        modelo=c["modelos"][clave], error=errores[-600:])
    return False, conv


TELEMETRIA = Path(os.environ.get("DIRECTOR_TELEMETRIA") or NOVA / "memory" / "registros" / "telemetria_hooks.jsonl")


def frenos_hook(convs: list[str], desde: str) -> list[dict]:
    """Frenos del hook (deny / force_ask) en estas conversaciones desde `desde` (la telemetria guarda conv[:8])."""
    cortos = {c[:8] for c in convs if c}
    if not cortos or not TELEMETRIA.exists():
        return []
    salida = []
    try:
        with open(TELEMETRIA, "rb") as fh:
            fh.seek(max(0, TELEMETRIA.stat().st_size - 3_000_000))
            for linea in fh.read().decode("utf-8", errors="replace").splitlines():
                try:
                    x = json.loads(linea)
                except ValueError:
                    continue
                if (x.get("conv") in cortos and str(x.get("t", "")) >= desde
                        and x.get("decision") in ("deny", "force_ask")):
                    salida.append(x)
    except OSError:
        return []
    return salida


def texto_frenos(proy: Path, f: dict, frenos: list[dict]) -> str:
    vistos, lineas = set(), []
    for x in frenos:
        que = (x.get("comando") or x.get("ruta") or "")[:160]
        if que in vistos:
            continue
        vistos.add(que)
        lineas.append(f"- `{que}` -> {str(x.get('motivo', ''))[:200]}")
    return (f"La fase {f['id']} ({f['titulo']}) no pasa sus criterios y en sus conversaciones el hook de Nova freno:\n\n"
            + "\n".join(lineas[:8]) + "\n\n## Para Nova\nExplicale al usuario QUE se freno y POR QUE (en palabras "
            "sencillas). Si dice que lo permite, anade a `" + str(proy / ".director" / "permisos.json") + "`:\n"
            '`{"permitir": [{"patron": "<regex que casa con ese comando o ruta>", "motivo": "<lo que dijo el usuario>"}]}`\n'
            "(solo para este proyecto; nunca vale para claves, cofre ni la zona blindada) y lanza con --continuar. "
            "Si no lo permite, dile que la fase necesita otro enfoque y espera su decision.")


def obra(proy: Path) -> None:
    c = cfg()
    fases = {f["id"]: f for f in validar_fases(proy)}
    if not fases:
        raise SystemExit("[DIRECTOR] No hay fases.json valido: ejecuta antes 'planos'.")
    foto(proy)
    e = leer_estado(proy)
    hechas = {k for k, v in e["fases"].items() if v.get("estado") == "hecha"}
    en_marcha: dict = {}
    # v3: conversaciones de Hydrogen LIBRES {conv: {"fases": n, "ultima": id}} para encadenar fases seguidas
    libres: dict[str, dict] = {}
    max_fases = c.get("max_fases_por_conversacion", 4)

    def elegir_conv(f: dict) -> str | None:
        candidatas = [(cid, v) for cid, v in libres.items() if v["fases"] < max_fases]
        if not candidatas:
            return None
        # mejor la que acaba de hacer una fase de la que esta depende (tiene ese codigo en su contexto)
        candidatas.sort(key=lambda x: (x[1]["ultima"] not in f.get("depende_de", []), -x[1]["fases"]))
        cid = candidatas[0][0]
        info = libres.pop(cid)
        usadas[cid] = info
        return cid

    usadas: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=c["max_paralelo"]) as pool:
        while len(hechas) < len(fases):
            ocupados = {a for fid in en_marcha for a in fases[fid]["archivos"]}
            listas = [f for fid, f in fases.items() if fid not in hechas and fid not in en_marcha
                      and all(d in hechas for d in f.get("depende_de", []))
                      and not (set(f["archivos"]) & ocupados)]
            espera = None  # v4: fase 'pausa' lista (diseno, vale del usuario...) que aun no esta hecha
            resuelta = False
            for f in [x for x in listas if x.get("herramienta") == "pausa"]:
                listas.remove(f)
                ok_p, _ = comprobar(proy, f["criterios"])
                if ok_p:  # Nova/el usuario ya lo hicieron
                    log(proy, f"PAUSA {f['id']} ya resuelta (criterios OK)")
                    hechas.add(f["id"])
                    e = leer_estado(proy)
                    e["fases"][f["id"]] = {"estado": "hecha"}
                    guardar_estado(proy, e)
                    resuelta = True
                else:
                    espera = espera or f
            if resuelta:  # hay fases que dependian de esa pausa: recalcular cuales estan listas
                continue
            for f in listas[: c["max_paralelo"] - len(en_marcha)]:
                conv = elegir_conv(f)
                log(proy, f"OBRA {f['id']}: {f['titulo']}" + (f" (sigue en la conversacion {conv[:8]})" if conv else ""))
                en_marcha[f["id"]] = pool.submit(hacer_fase, proy, f, conv)
                ocupados |= set(f["archivos"])
            if not en_marcha:
                if len(hechas) == len(fases):
                    break
                if espera:  # todo lo que se podia hacer sin el usuario esta hecho
                    e = leer_estado(proy)
                    e["fases"][espera["id"]] = {"estado": "esperando"}
                    guardar_estado(proy, e)
                    pausar(proy, f"{espera['id']} · {espera['titulo']}",
                           f"{espera['objetivo']}\n\n## Para Nova\n{espera.get('instrucciones_nova', '')}\n\n"
                           "## Se da por hecha cuando esto sale bien\n" + "\n".join(f"- `{x}`" for x in espera["criterios"]))
                raise SystemExit("[DIRECTOR] Fases bloqueadas (dependencias imposibles). Revisa fases.json.")
            time.sleep(1)
            for fid, fut in list(en_marcha.items()):
                if fut.done():
                    del en_marcha[fid]
                    e = leer_estado(proy)
                    ok_fase, conv_fase = fut.result()
                    if conv_fase:  # la conversacion queda libre para la siguiente fase de su linea
                        previa = usadas.pop(conv_fase, {"fases": 0})
                        libres[conv_fase] = {"fases": previa["fases"] + 1, "ultima": fid}
                    if ok_fase:
                        hechas.add(fid)
                        e["fases"][fid] = {"estado": "hecha"}
                        guardar_estado(proy, e)
                    else:
                        e["fases"][fid] = {"estado": "fallida"}
                        e["etapa"] = "obra_parada"
                        guardar_estado(proy, e)
                        raise SystemExit(f"[DIRECTOR] La fase {fid} falla tras Hydrogen, Neon y Carbon. Se para: "
                                         f"mira .director\\fases\\{fid}_arreglo.md (ultimo error). Toca Claude/el usuario.")
    e = leer_estado(proy)
    e["etapa"] = "obra_hecha"
    guardar_estado(proy, e)
    log(proy, "OBRA terminada: todas las fases pasan sus criterios")


# ------------------------------------------------------------------------------------------------ INSPECCION
FORMATO_HALLAZGOS = """{"hallazgos": [{"id": "H1", "gravedad": "critica|alta|media|baja", "archivo": "ruta",
  "linea": 0, "problema": "que pasa y como se explota", "arreglo": "cambio minimo",
  "contradice_enunciado": false}],
 "zonas_criticas": ["ruta/de/archivo.py"],
 "veredicto": "apto | apto con avisos | no apto"}"""
REGLAS_INSPECTOR = (
    "REGLAS DE GASTO: todo lo que necesitas esta en este paquete. NO ejecutes comandos ni pruebas. Lee como MAXIMO {n} "
    "archivos del proyecto, y solo si el paquete no basta. Escribe los dos archivos de salida y termina.\n"
    "`contradice_enunciado: true` si arreglarlo obliga a cambiar lo que pide el enunciado o sus tests (p. ej. un "
    "registro publico que el enunciado manda abierto): se avisa al usuario, no se arregla solo.\n")


def escaneres(proy: Path) -> str:
    if os.environ.get("DIRECTOR_SIN_ESCANERES"):
        return "(escaneres desactivados para esta prueba)"
    if not SEGURIDAD.exists():
        return "(nova_seguridad.py no esta: sin escaneres)"
    try:
        p = subprocess.run([os.environ.get("NOVA_PYTHON") or sys.executable, str(SEGURIDAD), str(proy)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        ruta = next((ln.split("paquete:")[-1].strip() for ln in p.stdout.splitlines() if "paquete:" in ln), "")
        return Path(ruta).read_text(encoding="utf-8")[:20000] if ruta else p.stdout[-3000:]
    except (OSError, subprocess.TimeoutExpired) as ex:
        return f"(escaneres fallaron: {ex})"


def visual(proy: Path) -> str:
    """Ruta con_ui: revision visual local (0 tokens) para que el inspector la tenga en el paquete."""
    if leer_estado(proy).get("ruta") != "con_ui" or os.environ.get("DIRECTOR_SIN_ESCANERES"):
        return ""
    rv = NOVA / "herramientas" / "revision_visual" / "revisar.py"
    if not rv.exists():
        return "## Revision visual\n\n(revisar.py no esta)\n\n"
    servidor, objetivo = arrancar_app(proy)  # 26/11 noche (D5): si la app SIRVE su web (FastAPI), revisar la URL
    try:
        p = subprocess.run([os.environ.get("NOVA_PYTHON") or sys.executable, str(rv), objetivo]
                           + ([] if objetivo.startswith("http") else ["--todas"]),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        informe = next((ln.split("Informe:")[-1].strip() for ln in p.stdout.splitlines() if "Informe:" in ln), "")
        texto = Path(informe).read_text(encoding="utf-8")[:12000] if informe else p.stdout[-3000:]
    except (OSError, subprocess.TimeoutExpired) as ex:
        texto = f"(fallo: {ex})"
    finally:
        if servidor:
            _matar_arbol(servidor.pid)
    return f"## Revision visual (capturas PC y movil, automatica; {objetivo})\n\n{texto}\n\n"


def arrancar_app(proy: Path):
    """Si el proyecto es una app Python que sirve su web (app/main.py con FastAPI), la arranca con uvicorn en un puerto
    libre y devuelve (proceso, url). Si no, (None, carpeta). La primera version miraba la carpeta y salian '0 paginas'."""
    import socket
    import urllib.request
    main_py = proy / "app" / "main.py"
    if not main_py.exists() or "FastAPI" not in main_py.read_text(encoding="utf-8", errors="replace"):
        return None, str(proy)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    tmp = proy / ".director" / "visual.db"
    cmd = ["uv", "run", "--with-requirements", "requirements.txt", "python", "-c",
           f"import uvicorn; from app.main import crear_app; uvicorn.run(crear_app(r'{tmp}'), host='127.0.0.1', "
           f"port={puerto}, log_level='warning')"]
    try:
        srv = subprocess.Popen(cmd, cwd=proy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               **({"creationflags": SIN_VENTANA} if WIN else {"start_new_session": True}))
    except OSError:
        return None, str(proy)
    url = f"http://127.0.0.1:{puerto}/"
    for _ in range(90):
        try:
            with urllib.request.urlopen(url, timeout=2):
                return srv, url
        except Exception:
            time.sleep(1)
    _matar_arbol(srv.pid)
    return None, str(proy)


def inspeccion(proy: Path) -> None:
    c = cfg()
    d = proy / ".director"
    fases = validar_fases(proy)
    todos = list(dict.fromkeys(x for f in fases for x in f["criterios"]))
    ok, informe_crit = comprobar(proy, todos)
    paquete = d / "paquete_inspeccion.md"
    paquete.write_text(
        "# PAQUETE · INSPECCION FINAL (eres el INSPECTOR: seguridad primero)\n\n"
        "El codigo lo escribio un modelo rapido por fases. Los tests pueden pasar y aun asi estar MAL. Busca lo que un "
        "proyecto real necesita aunque el enunciado no lo diga:\n"
        "- Secretos y claves: en el codigo, con valor por defecto (`os.environ.get('X', 'algo')` = tokens falsificables), "
        "en logs o en respuestas.\n- Autenticacion y permisos: quien puede ver/cambiar que (otro usuario, otro rol, ids "
        "ajenos), tokens (firma, caducidad, algoritmo).\n- Inyeccion (SQL, comandos, rutas), validacion de entradas, "
        "errores 500 con datos raros.\n- Dinero con float, fechas/zonas horarias, condiciones de carrera.\n"
        "- Dependencias sin version, lo que pide el enunciado y no esta.\n"
        "Los ESCANERES dan falsos positivos (p. ej. contrasenas de los tests, f-strings con solo `?`): confirmalos o "
        "descartalos con una linea. NO modifiques nada del proyecto.\n"
        + (f"METODO (skill de auditoria de Nova; cuenta como 1 de tus lecturas): `{SKILL_AUDITORIA}` - intenta "
           "DESMONTAR cada candidato: de donde entra el dato, por donde pasa, donde hace dano; sin camino real no cuenta.\n"
           if SKILL_AUDITORIA.exists() else "")
        + REGLAS_INSPECTOR.format(n=5) + "\n"
        f"Escribe `{d / 'hallazgos.json'}` con este formato:\n```json\n{FORMATO_HALLAZGOS}\n```\n"
        "(`zonas_criticas`: los 2-6 archivos donde un fallo haria mas dano: auth, permisos, dinero, datos personales)\n"
        f"y `{d / 'INSPECCION.md'}` (maximo 50 lineas) para el usuario: veredicto, hallazgos por gravedad, que esta bien.\n\n"
        "Ademas de la seguridad: comprueba requisito a requisito de la SPEC si esta cumplido (en INSPECCION.md, una "
        "tabla corta R1..Rn: cumplido / parcial / falta). Lo que falte es hallazgo 'alta'.\n\n"
        + (f"## SPEC (lo que se pidio)\n\n{(d / 'spec.md').read_text(encoding='utf-8', errors='replace')}\n\n"
           if (d / "spec.md").exists() else "")
        + f"## Arquitectura prevista\n\n{(d / 'arquitectura.md').read_text(encoding='utf-8', errors='replace')}\n\n"
        f"## Criterios ({'todos OK' if ok else 'HAY FALLOS'})\n```\n{informe_crit[-6000:]}\n```\n\n"
        + visual(proy)
        + f"## Escaneres automaticos\n\n{escaneres(proy)}\n\n"
        f"## Diff completo desde el inicio\n```diff\n{diff(proy, d / 'foto_inicial', c['max_diff_caracteres'])}\n```\n",
        encoding="utf-8")
    # v3 (26/11): PASO 1 revisa TODO con el paquete cerrado; PASO 2 Neon Extra High SOLO las zonas criticas.
    # v5 (26/11, medido en la v3: inspeccion = 9 de 12 puntos del 5h): paso 1 y reinspeccion con Neon Medium, y MODOS:
    #   completa = paso 1 + paso 2 (si hay algo critico) + arreglo + reinspeccion · ligera = solo paso 1 (avisa, no
    #   arregla) · ninguna = solo maquinas (criterios + escaneres), 0 tokens.
    modo = leer_estado(proy).get("inspeccion") or c.get("inspeccion_modo", "completa")
    if modo == "ninguna":
        (d / "INSPECCION.md").write_text(
            f"# Inspeccion (solo maquinas, modo 'ninguna')\n\nCriterios: {'todos OK' if ok else 'HAY FALLOS'}\n\n"
            f"```\n{informe_crit[-3000:]}\n```\n\n## Escaneres\n\n{escaneres(proy)[:6000]}\n", encoding="utf-8")
        (d / "hallazgos.json").write_text(json.dumps({"hallazgos": [], "veredicto": "sin revisar por modelo"}),
                                          encoding="utf-8")
        log(proy, "INSPECCION modo 'ninguna': solo criterios y escaneres")
        e = leer_estado(proy)
        e["etapa"] = "inspeccionada"
        guardar_estado(proy, e)
        return
    pedir_informe(proy, "INSPECCION paso 1", "inspeccion_1", paquete)
    if modo == "completa":
        zonas = zonas_criticas(proy, fases)
        if zonas:
            profunda(proy, zonas, informe_crit, ok)
    else:
        log(proy, "INSPECCION modo 'ligera': sin revision profunda ni arreglos automaticos")
        e = leer_estado(proy)
        e["etapa"] = "inspeccionada"
        guardar_estado(proy, e)
        return
    graves = leer_graves(proy)
    if graves and c.get("reinspeccion"):
        arreglar_hallazgos(proy, graves, todos)
    e = leer_estado(proy)
    e["etapa"] = "inspeccionada"
    guardar_estado(proy, e)
    log(proy, f"INSPECCION terminada: {len(leer_graves(proy))} critico/alto pendientes · "
              f"gasto total {ponderado_total(e)} ponderados · informe: {d / 'INSPECCION.md'}")


def pedir_informe(proy: Path, rol: str, clave: str, paquete: Path) -> None:
    """Llama al inspector y exige hallazgos.json + INSPECCION.md (2 intentos; la v2 acabo una vez en SUCCESS sin nada)."""
    d = proy / ".director"
    antes = (d / "hallazgos.json").stat().st_mtime if (d / "hallazgos.json").exists() else 0
    for intento in (1, 2):
        log(proy, f"{rol} ({cfg()['modelos'][clave]})" + (" reintento" if intento == 2 else ""))
        r = llamar(proy, rol + (" reintento" if intento == 2 else ""), clave, paquete)
        h = d / "hallazgos.json"
        if h.exists() and h.stat().st_mtime > antes and (d / "INSPECCION.md").exists():
            try:
                json.loads(h.read_text(encoding="utf-8"))
                return
            except ValueError:
                pass
        log(proy, f"   {rol}: no dejo hallazgos.json valido + INSPECCION.md. Dijo: {r['respuesta'][:300]}")
        registrar_error(proy, "inspeccion_sin_informe", rol=rol, intento=intento, respuesta=r["respuesta"][:300])
    raise SystemExit(f"[DIRECTOR] {rol} fallo 2 veces sin informe. Se para (mira director.log).")


def zonas_criticas(proy: Path, fases: list[dict]) -> list[str]:
    """Archivos para la revision profunda. Vacio (= sin paso 2, ahorro) si ninguna fase es critica y el paso 1 no
    encontro nada critico/alto."""
    try:
        h = json.loads((proy / ".director" / "hallazgos.json").read_text(encoding="utf-8"))
        z = h.get("zonas_criticas") or []
        graves = any(str(x.get("gravedad", "")).lower() in ("critica", "alta") for x in h.get("hallazgos", []))
    except (OSError, ValueError):
        z, graves = [], False
    if not any(f.get("critica") for f in fases) and not graves:
        return []
    if not z:  # si el paso 1 no las dice: los archivos de las fases marcadas criticas
        z = [a for f in fases if f.get("critica") for a in f["archivos"]]
    return [a for a in dict.fromkeys(z) if (proy / a).is_file()][:4]  # 26/11 noche (D5): 6 -> 4 (paso 2 = ~750k)


def profunda(proy: Path, zonas: list[str], informe_crit: str, ok: bool) -> None:
    d = proy / ".director"
    previo = (d / "hallazgos.json").read_text(encoding="utf-8")
    codigo = "\n\n".join(f"### {a}\n```\n{(proy / a).read_text(encoding='utf-8', errors='replace')[:15000]}\n```"
                         for a in zonas)
    paquete = d / "paquete_inspeccion_profunda.md"
    paquete.write_text(
        "# PAQUETE · INSPECCION PROFUNDA (solo las zonas criticas; eres el inspector senior)\n\n"
        "Un inspector anterior reviso todo el proyecto (sus hallazgos abajo). Tu trabajo: en ESTOS archivos, "
        "(1) confirma o descarta cada hallazgo suyo que les afecte, (2) busca lo que se le escapo: escalada de "
        "privilegios, acceso a datos ajenos, tokens/claves, dinero, entradas que rompen (NaN, Infinity, enormes), "
        "carreras.\n" + REGLAS_INSPECTOR.format(n=3) + "\n"
        f"Reescribe `{d / 'hallazgos.json'}` (mismo formato) con TODOS los hallazgos: los del inspector anterior que "
        f"sigan valiendo + los tuyos (marca los tuyos con \"de\": \"profunda\"). Anade al final de `{d / 'INSPECCION.md'}` "
        "una seccion '## Revision profunda' (maximo 20 lineas).\n\n"
        f"## Hallazgos del inspector anterior\n```json\n{previo}\n```\n\n"
        f"## Criterios ({'todos OK' if ok else 'HAY FALLOS'})\n```\n{informe_crit[-3000:]}\n```\n\n"
        f"## Codigo de las zonas criticas\n\n{codigo}\n", encoding="utf-8")
    pedir_informe(proy, "INSPECCION paso 2 (profunda)", "inspeccion", paquete)


def leer_graves(proy: Path) -> list[dict]:
    """Critico/alto que se arreglan solos. Los que contradicen el enunciado se avisan al usuario, no se tocan."""
    try:
        h = json.loads((proy / ".director" / "hallazgos.json").read_text(encoding="utf-8")).get("hallazgos", [])
    except (OSError, ValueError):
        log(proy, "AVISO: no hay hallazgos.json valido (la inspeccion no lo escribio).")
        return []
    return [x for x in h if str(x.get("gravedad", "")).lower() in ("critica", "alta")
            and not x.get("contradice_enunciado")]


def arreglar_hallazgos(proy: Path, graves: list[dict], criterios: list[str]) -> None:
    d = proy / ".director"
    shutil.rmtree(d / "foto_prearreglo", ignore_errors=True)
    for rel, p in archivos_texto(proy).items():
        (d / "foto_prearreglo" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d / "foto_prearreglo" / rel)
    paquete = d / "paquete_arreglo.md"
    paquete.write_text(
        "# PAQUETE · ARREGLAR HALLAZGOS DE LA INSPECCION (solo estos, cambios minimos)\n\n"
        + json.dumps(graves, ensure_ascii=False, indent=1)
        + "\n\nNo cambies nada mas. No modifiques tests. Cuando acabes deben pasar:\n"
        + "\n".join(f"- `{x}`" for x in criterios) + "\n", encoding="utf-8")
    log(proy, f"ARREGLO de {len(graves)} hallazgos critico/alto (Hydrogen)")
    r = llamar(proy, "ARREGLO HALLAZGOS", "obra", paquete)
    ok, informe = comprobar(proy, criterios)
    if not ok:  # 2o intento en la MISMA conversacion (cache), con el error
        (d / "paquete_arreglo.md").write_text(paquete.read_text(encoding="utf-8")
                                              + f"\n\n## TRAS TU ARREGLO FALLAN LOS CRITERIOS\n```\n{informe[-4000:]}\n```\n",
                                              encoding="utf-8")
        llamar(proy, "ARREGLO HALLAZGOS 2", "obra", paquete, r["conversacion"])
        ok, informe = comprobar(proy, criterios)
    log(proy, f"   criterios tras el arreglo: {'OK' if ok else 'FALLAN'}")
    rp = d / "paquete_reinspeccion.md"
    rp.write_text(
        "# PAQUETE · REINSPECCION CORTA\n\nComprueba SOLO si estos hallazgos quedaron arreglados sin romper nada.\n"
        "REGLAS DE GASTO: todo esta en este paquete (el diff del arreglo y los criterios ya ejecutados). NO ejecutes "
        "nada y lee como MAXIMO 2 archivos. No busques hallazgos nuevos.\n\n"
        + json.dumps(graves, ensure_ascii=False, indent=1)
        + f"\n\n## Diff del arreglo\n```diff\n{diff(proy, d / 'foto_prearreglo', 40000)}\n```\n"
        f"## Criterios ({'todos OK' if ok else 'FALLAN'})\n```\n{informe[-4000:]}\n```\n\n"
        f"Reescribe `{d / 'hallazgos.json'}` (mismo formato: quita los arreglados, deja el resto tal cual) y anade al "
        f"final de `{d / 'INSPECCION.md'}` una seccion '## Reinspeccion' (maximo 10 lineas).\n", encoding="utf-8")
    llamar(proy, "REINSPECCION", "reinspeccion", rp)


# -------------------------------------------------------------------------------------------- estado y modelos
def estado(proy: Path) -> None:
    e = leer_estado(proy)
    print(f"Etapa: {e.get('etapa')} · fases: " + ", ".join(f"{k}={v.get('estado')}" for k, v in e["fases"].items()))
    por = {}
    for x in e["llamadas"]:
        m = por.setdefault(x["modelo"], {"llamadas": 0, "ponderado": 0, "segundos": 0})
        m["llamadas"] += 1
        m["ponderado"] += x["ponderado"]
        m["segundos"] += x["segundos"]
    for m, v in por.items():
        print(f"  {m:28} {v['llamadas']:3} llamadas · {v['ponderado']:>9} ponderados · {v['segundos']} s")
    print(f"  TOTAL {ponderado_total(e)} ponderados (presupuesto {cfg()['presupuesto_ponderado']})")


def modelos() -> None:
    c = cfg()
    try:
        p = subprocess.run(comando_agy(c) + ["models"], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise SystemExit("[DIRECTOR] No encuentro 'agy'. Ver LEEME.md (instalacion).")
    print(p.stdout or p.stderr)
    for clave, slug in c["modelos"].items():
        print(f"{'OK ' if slug in p.stdout else 'NO '} {clave:13} {slug}")


# ------------------------------------------------------------------ desde NOVA: lanzar, avisar y resumir (26/11)
ULTIMO = NOVA / "memory" / "director_ultimo.json"  # el ultimo proyecto lanzado (para "resumen" sin carpeta)
CUPO_5H_1PC = 220_000  # ponderados por 1 % del 5h (calibrado 26/11 con 3 lecturas del visor)
VOZ = "http://127.0.0.1:5010"
CLIPS = NOVA / "voice_cache" / "marina"


def en_marcha(proy: Path) -> int | None:
    """PID del director que corre sobre este proyecto, o None."""
    try:
        pid = json.loads((proy / ".director" / "en_marcha.json").read_text(encoding="utf-8"))["pid"]
        return pid if _vivo(pid) else None
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return None


def lanzar(proy: Path, idea: Path | None, radiografia: Path | None, continuar: bool = False) -> None:
    """Lo que ejecuta NOVA: arranca 'todo' (o 'continuar' tras una pausa) en segundo plano, SIN ventana y fuera de su
    terminal (si no, Antigravity lo mata al acabar el comando), y vuelve en 2 s. Al terminar avisa Marina."""
    if (pid := en_marcha(proy)):
        print(f"[DIRECTOR] Ya hay un director trabajando en este proyecto (PID {pid}). No lances otro: espera el aviso.")
        return
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else sys.executable)
    args = [exe, str(Path(__file__).resolve()), "continuar" if continuar else "todo", str(proy), "--avisar"]
    if idea:
        args += ["--idea", str(idea)]
    if radiografia:
        args += ["--radiografia", str(radiografia)]
    for k, v in os.environ.items():  # WMI no hereda el entorno: las variables de prueba van como argumentos
        if k.startswith("DIRECTOR_") or k.startswith("AGY_F2"):
            args += ["--entorno", f"{k}={v}"]
    linea = subprocess.list2cmdline(args)
    pid = None
    if not WIN:  # v3.3 macOS/Linux: sesion propia = no muere al cerrarse la terminal de Antigravity
        pid = subprocess.Popen(args, cwd=proy, start_new_session=True, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
    try:  # WMI: el proceso nace fuera del "job" de la terminal de Antigravity (truco de session_guard)
        if not WIN:
            raise StopIteration
        ps = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$env:DIR_CMD; "
              "CurrentDirectory=$env:DIR_CWD}; $r.ProcessId")
        p = subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps], capture_output=True,
                           text=True, timeout=60, env={**os.environ, "DIR_CMD": linea, "DIR_CWD": str(proy)})
        pid = int(p.stdout.strip().splitlines()[-1])
    except StopIteration:
        pass
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        flags = 0x00000008 | 0x08000000 | 0x00000200 | 0x01000000  # DETACHED, NO_WINDOW, NEW_GROUP, BREAKAWAY
        pid = subprocess.Popen(args, cwd=proy, creationflags=flags, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
    (proy / ".director" / "en_marcha.json").write_text(
        json.dumps({"pid": pid, "desde": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
    ULTIMO.parent.mkdir(parents=True, exist_ok=True)
    ULTIMO.write_text(json.dumps({"proyecto": str(proy), "lanzado": time.strftime("%Y-%m-%d %H:%M:%S")},
                                 ensure_ascii=False), encoding="utf-8")
    print(f"[DIRECTOR] LANZADO en segundo plano (PID {pid}). Tarda ~20-40 min y trabaja solo con la CLI agy.\n"
          "NOVA: NO esperes, NO consultes el estado ni abras sus archivos ahora (gastarias tokens para nada). "
          "Dile al usuario, tal cual: 'Lanzado el director; Marina te avisa cuando acabe. Luego preguntame como "
          "fue.' Cuando pregunte: <PYTHON> <este script> resumen")


def avisar(texto: str, tipo: str = "fin") -> None:
    """Marina por el servidor de voces; si no esta cargado, su clip grabado del tipo (fin | pausa | parado);
    si no hay clip, un pitido. Se apaga con "voz_marina": false en director.json (queda el aviso en el chat de Antigravity)."""
    if cfg().get("voz_marina", True) is False:
        return
    import urllib.request as ur
    try:
        with ur.urlopen(VOZ + "/", timeout=1.5) as r:
            listo = bool(json.loads(r.read().decode("utf-8") or "{}").get("modelo_cargado"))
        if listo:
            req = ur.Request(VOZ + "/hablar", headers={"Content-Type": "application/json"},
                             data=json.dumps({"voz": "marina", "estilo": "crudo", "texto": texto}).encode("utf-8"))
            with ur.urlopen(req, timeout=120):
                return
    except Exception:
        pass
    clips = sorted(CLIPS.glob(f"aviso_director_{tipo}_*.wav")) or sorted(CLIPS.glob("aviso_director_*.wav"))
    _sonar(clips[0] if clips else None)  # v3.3: Windows, macOS y Linux


def avisar_nova(texto: str, espera_max_s: int = 1800) -> bool:
    """26/11 noche (el usuario: "algo que haga que Nova me diga las preguntas; no voy a estar vigilando"): escribe un mensaje
    en el chat de Antigravity que este abierto y lo ENVIA (como Nova Voz, por el puerto de depuracion). Nova lo recibe,
    ejecuta 'resumen' y le pregunta/explica al usuario. Solo escribe si el cuadro de mensaje esta VACIO (no pisa lo que
    el usuario este escribiendo): si no, reintenta cada 30 s hasta espera_max_s. Sin Antigravity abierto: False."""
    import urllib.request
    try:
        import websocket
    except ImportError:
        return False
    fin = time.time() + espera_max_s
    while time.time() < fin:
        url = None
        for d in _devtools_port_dirs():
            try:
                puerto = (d / "DevToolsActivePort").read_text().split()[0]
                paginas = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json", timeout=2).read())
                paginas = [p for p in paginas if p.get("type") == "page" and not str(p.get("url", "")).startswith("data:")]
                paginas.sort(key=lambda p: p.get("title") != "Antigravity")
                if paginas:
                    url = paginas[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                continue
        if not url:
            return False
        try:
            ws = websocket.create_connection(url, suppress_origin=True, timeout=5)
            n = [0]

            def cdp(metodo, params=None):
                n[0] += 1
                ws.send(json.dumps({"id": n[0], "method": metodo, "params": params or {}}))
                while True:
                    r = json.loads(ws.recv())
                    if r.get("id") == n[0]:
                        return r

            def js(expr):
                return cdp("Runtime.evaluate", {"expression": expr, "returnByValue": True}).get(
                    "result", {}).get("result", {}).get("value")

            caja = "document.querySelector('[contenteditable=\"true\"]')"
            libre = js(f"(() => {{ const el = {caja}; return !!el && el.innerText.trim() === ''; }})()")
            if libre:
                js(f"{caja}.focus()")
                cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
                cdp("Input.insertText", {"text": texto})
                enviado = False
                for _ in range(10):
                    time.sleep(0.2)
                    enviado = js("(() => { const b = document.querySelector('button[aria-label=\"Send message\"]');"
                                 " if (b && !b.disabled) { b.click(); return true; } return false; })()")
                    if enviado:
                        break
                if not enviado:
                    cdp("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter",
                                                   "windowsVirtualKeyCode": 13})
                    cdp("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter",
                                                   "windowsVirtualKeyCode": 13})
                ws.close()
                return True
            ws.close()
        except Exception:
            pass
        time.sleep(30)  # el usuario esta escribiendo (o Antigravity ocupado): reintentar
    return False


def resumen(proy: Path) -> None:
    """Todo lo que Nova necesita para explicarle el resultado al usuario, en una sola salida corta."""
    d = proy / ".director"
    e = leer_estado(proy)
    pond = ponderado_total(e)
    print(f"PROYECTO: {proy}")
    if en_marcha(proy):
        print("ESTADO: TODAVIA TRABAJANDO (no ha terminado). Dile al usuario que espere el aviso de Marina.")
    print(f"RUTA: {e.get('ruta', '?')} · ETAPA: {e.get('etapa')} · FASES: "
          + ", ".join(f"{k} {v.get('estado')}" for k, v in e["fases"].items()))
    if (d / "PAUSA.md").exists():
        print("\n" + (d / "PAUSA.md").read_text(encoding="utf-8").strip() + "\n")
        print("NOVA: haz lo que pide la PAUSA (o preguntaselo al usuario) y luego lanza con --continuar.")
    fin = d / "fin.json"
    if fin.exists():
        f = json.loads(fin.read_text(encoding="utf-8"))
        print(f"TERMINO: {f.get('cuando')} · {f.get('resultado')}")
    print(f"GASTO: {pond} ponderados ~ {pond / CUPO_5H_1PC:.1f} % del cupo de 5 h de Gemini "
          f"({len(e['llamadas'])} llamadas)")
    try:
        h = json.loads((d / "hallazgos.json").read_text(encoding="utf-8"))
        print(f"VEREDICTO DE LA INSPECCION: {h.get('veredicto')}")
        for x in h.get("hallazgos", []):
            marca = " [CONTRADICE EL ENUNCIADO: decide el usuario]" if x.get("contradice_enunciado") else ""
            print(f"- {x.get('gravedad', '?').upper()} {x.get('id')}: {str(x.get('problema'))[:220]}{marca}")
    except (OSError, ValueError):
        print("INSPECCION: sin hallazgos.json (no llego a inspeccionar o fallo).")
    print(f"INFORME COMPLETO PARA EL USUARIO: {d / 'INSPECCION.md'}")
    print("NOVA: explicaselo en corto (que se hizo, si pasa las pruebas, lo critico en palabras sencillas, lo que "
          "tiene que decidir el y cuanto gasto). No releas el codigo.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["lanzar", "todo", "continuar", "planos", "obra", "inspeccion", "estado",
                                       "resumen", "modelos"])
    ap.add_argument("proyecto", nargs="?")
    ap.add_argument("--idea")
    ap.add_argument("--radiografia")
    ap.add_argument("--continuar", action="store_true", help="con 'lanzar': seguir tras una PAUSA")
    ap.add_argument("--inspeccion", choices=["completa", "ligera", "ninguna"],
                    help="cuanta inspeccion (por defecto 'inspeccion_modo' de director.json)")
    ap.add_argument("--avisar", action="store_true", help="al terminar, aviso de Marina (lo pone 'lanzar')")
    ap.add_argument("--entorno", action="append", default=[], help=argparse.SUPPRESS)
    try:  # 26/11: la consola de Windows (cp1252) rompia con caracteres como el de 'aprox.'
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    a = ap.parse_args()
    for kv in a.entorno:
        k, _, v = kv.partition("=")
        os.environ[k] = v
    if a.accion == "modelos":
        return modelos()
    if not a.proyecto and a.accion in ("resumen", "estado") and ULTIMO.exists():
        a.proyecto = json.loads(ULTIMO.read_text(encoding="utf-8"))["proyecto"]
    if not a.proyecto:
        ap.error("falta la carpeta del proyecto")
    proy = Path(a.proyecto).resolve()
    (proy / ".director").mkdir(parents=True, exist_ok=True)
    if a.accion == "estado":
        return estado(proy)
    if a.accion == "resumen":
        return resumen(proy)
    d = proy / ".director"
    if a.inspeccion:  # se guarda en el estado: vale para 'lanzar' (proceso aparte) y para 'continuar'
        e = leer_estado(proy)
        e["inspeccion"] = a.inspeccion
        guardar_estado(proy, e)
    if a.accion == "continuar":  # tras una PAUSA: si era de preguntas, rehace los planos con las respuestas
        e = leer_estado(proy)
        if not (d / "fases.json").exists():
            a.idea = a.idea or e.get("idea")
            a.accion = "todo"
        (d / "PAUSA.md").unlink(missing_ok=True)
    if (a.accion in ("todo", "planos") or (a.accion == "lanzar" and not a.continuar)) and not a.idea:
        ap.error("necesita --idea <archivo con el enunciado>")
    if a.accion == "lanzar":
        return lanzar(proy, Path(a.idea).resolve() if a.idea else None,
                      Path(a.radiografia).resolve() if a.radiografia else None, a.continuar)
    resultado = "con error"
    # 26/11 noche (D2): la marca de "director trabajando" SIEMPRE (no solo con 'lanzar'): el hook la usa para saber
    # que la llamada es del director (sin ventana) y aplicar sus reglas (borrar en el proyecto, permisos.json, sin voz)
    (d / "en_marcha.json").write_text(json.dumps({"pid": os.getpid(), "desde": time.strftime("%Y-%m-%d %H:%M:%S")}),
                                      encoding="utf-8")
    git_excluir(proy)
    try:
        if a.accion in ("todo", "planos"):
            e = leer_estado(proy)
            e["idea"] = str(Path(a.idea).resolve())
            guardar_estado(proy, e)
            planos(proy, Path(a.idea).resolve(), Path(a.radiografia).resolve() if a.radiografia else None)
        if a.accion in ("todo", "obra", "continuar"):
            obra(proy)
        if a.accion in ("todo", "inspeccion", "continuar"):
            inspeccion(proy)
        estado(proy)
        resultado = "terminado"
    except Pausa as ex:
        resultado = f"en pausa: {ex}"
        print(f"[DIRECTOR] EN PAUSA: {ex}. Lee {d / 'PAUSA.md'}")
    except SystemExit as ex:
        resultado = f"parado: {ex}"
        registrar_error(proy, "parado", motivo=str(ex))
        raise
    finally:
        (proy / ".director" / "en_marcha.json").unlink(missing_ok=True)
        if a.avisar:
            (proy / ".director" / "fin.json").write_text(
                json.dumps({"cuando": time.strftime("%Y-%m-%d %H:%M:%S"), "resultado": resultado},
                           ensure_ascii=False), encoding="utf-8")
            n = len(leer_graves(proy)) if resultado == "terminado" else 0
            avisar(f"el usuario, el director necesita que decidas algo en {proy.name}. Preguntale a Nova."
                   if resultado.startswith("en pausa") else
                   f"el usuario, el director ha terminado {proy.name}. "
                   + ("Todo listo, preguntale a Nova como fue." if resultado == "terminado" and not n else
                      f"Hay {n} avisos importantes, preguntale a Nova." if resultado == "terminado" else
                      "Se ha parado antes de acabar, preguntale a Nova que paso."),
                   "pausa" if resultado.startswith("en pausa") else "fin" if resultado == "terminado" else "parado")
            # 26/11 noche: ademas de la voz, Nova se entera SOLA en el chat y le habla al usuario
            que = ("esta EN PAUSA y necesita al usuario (preguntas, vale de diseno o un permiso)"
                   if resultado.startswith("en pausa") else "ha TERMINADO" if resultado == "terminado"
                   else "se ha PARADO antes de acabar")
            ok_chat = avisar_nova(f"[director] Nova: el director de '{proy.name}' {que}. Ejecuta `& $env:NOVA_PYTHON "
                                  f"\"{Path(__file__).resolve()}\" resumen \"{proy}\"` y haz lo que diga tu kit del carril "
                                  "proyecto (preguntale o explicale al usuario).")
            log(proy, f"aviso en el chat de Antigravity: {'enviado' if ok_chat else 'no se pudo (Antigravity cerrado)'}")


if __name__ == "__main__":
    main()
