"""
NOVA HOOK - Antigravity llama a este script ANTES de cada herramienta del agente (PreToolUse, ~/.gemini/config/hooks.json)

Por que: las leyes de GEMINI.md son texto y el modelo a veces se las salta (webs enteras escritas desde la nube,
sesiones que queman millones de tokens). El hook lo comprueba el sistema, no el modelo.

Modos (nova_hooks_config.json, junto a este archivo):
  "registro" -> nunca bloquea; apunta cada llamada en memory/registros/telemetria_hooks.jsonl.
  "bloqueo"  -> ademas aplica las reglas (de mas grave a menos):
     deny  (prohibido, sin preguntar):
       - escribir en carpetas protegidas (nova_core, biblioteca_web, ~/.gemini/config o con un archivo .nova_protegido)
         o en .env
       - leer dentro de node_modules / .git / dist / build / .next / __pycache__
       - leer de golpe archivos enormes (> MAX_KB) o documentos/datos (.pdf .docx .xlsx .pptx .ipynb .jsonl ...)
         -> usar resumir.py / conversor.py, o buscar con grep/rg
       - WEB de mas de MAX_LINEAS escrita desde la nube, salvo que el usuario diga "escribelo tu" o de una web de
         referencia (lo apunta nova_hook_turno.py) -> la web sale de la biblioteca (montar.py, 0 tokens)
       - (Windows) ruta de programa con espacios y sin comillas: PowerShell no ejecuta nada y no avisa
     force_ask (Antigravity se lo pregunta al usuario):
       - la nube escribiendo mas de MAX_LINEAS de codigo (no web)
       - comandos destructivos (borrados recursivos, git push --force, git reset --hard, DROP TABLE, formatear...)
       - editar un proyecto git estando en la rama principal (Ley 5: primero una rama de pruebas)
       - FRENO DE GASTO: la conversacion pasa de cada TOPE_TOKENS reales (cache al 10 %) -> pregunta una vez por tope
       - mas de MAX_SEGUIDAS herramientas encadenadas sin que el usuario escriba -> pregunta una vez cada bloque
Siempre: si algo falla dentro del hook, responde "allow" (un hook roto no puede dejar a Nova sin trabajar) y lo apunta.

Formato (docs de Antigravity): entra por stdin un JSON con toolCall.name, toolCall.args y transcriptPath; sale por
stdout {"decision": "allow" | "deny" | "force_ask" | "auto_approve", "reason": "..."}.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CONFIG = AQUI / "nova_hooks_config.json"
ESTADO = AQUI / ".nova_hooks_estado.json"  # topes de gasto ya preguntados por conversacion
GEMINI = Path.home() / ".gemini"
ANTIGRAVITY = GEMINI / "antigravity"
REGISTRO = ANTIGRAVITY / "memory" / "registros" / "telemetria_hooks.jsonl"
PERFIL = ANTIGRAVITY / "memory" / "perfil_usuario.json"
WINDOWS = os.name == "nt"


def leer_json(p: Path, defecto):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return defecto


def _nombre_usuario() -> str:
    perfil = leer_json(PERFIL, {})
    nombre = str(perfil.get("nombre", "") if isinstance(perfil, dict) else "").strip()
    return nombre or "el usuario"


USUARIO = _nombre_usuario()

# El Python con el que corre el hook es el mismo que puso el instalador en hooks.json: el que funciona seguro.
PYTHON_NOVA = sys.executable or ("python" if WINDOWS else "python3")
PY = f'& "{PYTHON_NOVA}"' if WINDOWS else f'"{PYTHON_NOVA}"'  # forma correcta de lanzarlo en la terminal de Nova
MONTAR = ANTIGRAVITY / "almacen" / "biblioteca_web" / "montar.py"
OBRERO = ANTIGRAVITY / "scripts" / "nova_local_worker.py"
REDACTOR = GEMINI / "nova_core" / "redactor.py"
RESUMIR = GEMINI / "nova_core" / "resumir.py"

PROTEGIDAS = ("biblioteca_web", "nova_core")
PROTEGIDAS_RUTAS = (GEMINI / "config",)  # reglas y skills de Nova: solo las cambia el usuario a mano
MARCA_PROTEGIDO = ".nova_protegido"
# Secretos: ni se leen ni se muestran en la nube (los scripts que los necesitan los leen solos, en local)
RE_SECRETO = re.compile(
    r"(?i)(^|[\\/])vault([\\/]|$)|(^|[\\/])\.env(\.(?!example\b|sample\b|template\b)[\w.-]+)?$|(^|[\\/])\.env(?=[\s'\"]|$)"
    r"|oauth_creds\.json|(^|[\\/])secrets?[\w.-]*\.(json|env)|credentials[\w.-]*\.json|\.pem$|\.p12$|\.pfx$|id_rsa|id_ed25519"
    r"|(^|[\\/])[\w.-]*\.env$")
RE_CMD_SECRETO = re.compile(
    r"(?i)(vault[\\/]|oauth_creds\.json|secrets?[\w.-]*\.(json|env)|credentials[\w.-]*\.json|\.pem\b|id_rsa|id_ed25519"
    r"|[\\/ '\"]\.env(?!\.example|\.sample|\.template)\b|[\w-]+\.env\b)")
RE_CMD_ESCRIBE = re.compile(
    r"(?i)(^|[\s;|&('\"`{])(Set-Content|Add-Content|Out-File|New-Item|Copy-Item|Move-Item|Remove-Item|Rename-Item|copy|xcopy|"
    r"robocopy|move|ren|del|erase|rm|mv|cp|mkdir|md|tee|sed\s+-i|touch|chmod|ln)\b|>{1,2}")
# (Windows) ruta de un programa (.exe/.ps1/.bat/.cmd/.py) CON espacios y SIN comillas al empezar el comando
RE_RUTA_ESPACIO_SIN_COMILLAS = re.compile(
    r"(?i)(^|[;|]\s*|&&\s*)[a-z]:\\(?:[^\"'\\\r\n;|]+\\)*?[^\"'\\\r\n;|]* [^\"'\\\r\n;|]*\\"
    r"(?:[^\"'\\\r\n;|]+\\)*[^\"'\\\s;|]+\.(exe|ps1|bat|cmd|py)\b")
# (Windows) "python x.py" / "py -3 ..." a secas: en el sandbox de Antigravity el alias de la Store falla sin avisar
RE_PYTHON_ATAJO = re.compile(r"(?i)(^|[;&|(]|\bcmd(\.exe)?\s+/[ck]\s+\"?)\s*(python3?|py)(\.exe)?(?=\s|$)")
RAMAS_PRINCIPALES = {"main", "master", "production", "prod", "produccion", "release"}
RE_DOC_EN_SCRATCH = re.compile(r"(?i)[\\/]antigravity[\\/]scratch[\\/][^\"'|;&<>\n]*\.(pdf|docx|doc|xlsx|pptx)\b")

MAX_LINEAS = 150  # hasta 150 lineas las escribe Nova; mas, la Capa 0 local
MAX_KB = 200
TOPE_TOKENS = 300_000  # tokens REALES (cache al 10 %)
PRECIO_CACHE = 0.10    # Gemini cobra la entrada leida de cache con un 90 % de descuento
MAX_SEGUIDAS = 25
CARPETAS_BASURA = {"node_modules", ".git", "dist", "build", ".next", "__pycache__", ".venv", "venv", ".turbo", ".cache"}
EXT_PESADAS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ipynb", ".jsonl", ".parquet", ".zip", ".mp4",
               ".mov", ".db", ".sqlite", ".log"}
EXT_CODIGO = {".html", ".htm", ".css", ".scss", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".vue", ".svelte", ".py",
              ".java", ".kt", ".swift", ".dart", ".php", ".cs", ".go", ".rs", ".sql"}
EXT_WEB = {".html", ".htm", ".css", ".scss", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".vue", ".svelte", ".astro"}
RE_ESCRIBIR = re.compile(r"write|replace|edit|create_file|save_file", re.I)
RE_LEER = re.compile(r"read|view|open_file|cat_file|list_dir|list_files|grep_search|find_by_name", re.I)
RE_PELIGROSO = re.compile(
    r"(?i)\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r|Remove-Item\b[^\n]*-Recurse|\brd\s+/s|\brmdir\s+/s|\bdel\s+/[sq]|"
    r"git\s+push\s+[^\n]*(--force|-f\b)|git\s+reset\s+--hard|git\s+clean\s+-[a-z]*f|\bdrop\s+(table|database|schema)\b|"
    r"\btruncate\s+table\b|\bformat\s+[a-z]:|Format-Volume|\bmkfs\b|Clear-Content\b|\bdd\s+if=|\bsudo\s+rm\b"
)
CLAVES_RUTA = ("TargetFile", "targetFile", "AbsolutePath", "absolutePath", "path", "Path", "file_path", "filePath",
               "target_file", "DirectoryPath", "SearchPath", "SearchDirectory")
CLAVES_TEXTO = ("CodeContent", "content", "Content", "code", "ReplacementContent", "Replacement", "new_text", "newText",
                "replacement", "texto_nuevo", "ReplacementChunks", "chunks")
AUTORIZA_CODIGO = AQUI / ".autoriza_codigo.json"  # lo escribe nova_hook_turno.py con cada mensaje del usuario


def apuntar(fila: dict) -> None:
    try:
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    except Exception:
        pass


def dentro_de(p: Path, base: Path) -> bool:
    """True si p esta dentro de base (sin distinguir mayusculas en Windows)."""
    try:
        a, b = os.path.normcase(str(p.expanduser().resolve())), os.path.normcase(str(base.resolve()))
    except OSError:
        a, b = os.path.normcase(str(p)), os.path.normcase(str(base))
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def rama_git(p: Path) -> tuple[str, Path | None]:
    """(rama actual, carpeta del repo) si p esta dentro de un repo git; ("", None) si no. Solo lee .git/HEAD."""
    try:
        d = p if p.is_dir() else p.parent
        for carpeta in [d, *d.parents]:
            g = carpeta / ".git"
            if g.is_file():  # worktree o submodulo: "gitdir: <ruta>"
                destino = Path(g.read_text(encoding="utf-8").split(":", 1)[1].strip())
                g = destino if destino.is_absolute() else (carpeta / destino)
            if (g / "HEAD").is_file():
                head = (g / "HEAD").read_text(encoding="utf-8").strip()
                return (head.rsplit("/", 1)[-1] if head.startswith("ref:") else "(detached)"), carpeta
            if carpeta == carpeta.parent:
                break
    except (OSError, IndexError):
        pass
    return "", None


def ruta_de(args: dict) -> str:
    for k in CLAVES_RUTA:
        if isinstance(args.get(k), str):
            return args[k]
    return next((v for k, v in args.items() if isinstance(v, str) and re.search(r"path|file|target|dir", k, re.I)), "")


def lineas_nuevas(args: dict) -> int:
    total = 0
    for k in CLAVES_TEXTO:
        v = args.get(k)
        if isinstance(v, str):
            total += v.count("\n") + 1
        elif isinstance(v, list):
            for t in v:
                if isinstance(t, dict):
                    total += sum(str(x).count("\n") + 1 for kk, x in t.items() if re.search(r"replac|new|content", kk, re.I))
    return total


def protegida(ruta: str) -> bool:
    if not ruta:
        return False
    p = Path(ruta).expanduser()
    if any(parte.lower() in PROTEGIDAS for parte in p.parts):
        return True
    if any(dentro_de(p, base) for base in PROTEGIDAS_RUTAS):
        return True
    try:
        return any((c / MARCA_PROTEGIDO).exists() for c in p.parents)
    except OSError:
        return False


def gasto(transcript: str) -> tuple[int, int, int, dict]:
    """(tokens REALES = nuevos + cache al 10 % + salida, herramientas seguidas desde el ultimo mensaje del usuario,
    tamano del contexto en la ultima llamada, desglose {nuevos, cache, salida, bruto})."""
    nuevos = cache = salida = 0
    seguidas, contexto = 0, 0
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                if o.get("type") == "PLANNER_RESPONSE":
                    nuevos += int(o.get("input_tokens") or 0)
                    cache += int(o.get("cache_read_tokens") or 0)
                    salida += int(o.get("output_tokens") or 0)
                    contexto = int(o.get("input_tokens") or 0) + int(o.get("cache_read_tokens") or 0)
                if o.get("type") == "USER_INPUT":
                    seguidas = 0
                seguidas += len(o.get("tool_calls") or [])
    except OSError:
        pass
    real = int(nuevos + cache * PRECIO_CACHE + salida)
    return real, seguidas, contexto, {"nuevos": nuevos, "cache": cache, "salida": salida, "bruto": nuevos + cache + salida}


# Orden: dentro de ~/.gemini/antigravity, los ARCHIVOS NUEVOS solo se crean en estas carpetas.
CARPETAS_PERMITIDAS = {
    "scratch": "herramientas o scripts nuevos (pasan por revision del usuario)",
    "documentos_generados": "todo documento, imagen o txt que genere Nova (por proyecto: documentos_generados/<proyecto>/)",
    "proyectos": "ideas (_ideas/<nombre>.md) y conocimiento de cada proyecto (README.md, docs/)",
    "temporal": "adjuntos del chat",
    "memory": "notas de Nova (tasks.md, napkin.md, inbox_lecciones.md...)",
    "brain": "Antigravity", "conversations": "Antigravity", "cache": "Antigravity", "log": "Antigravity",
    "daemon": "Antigravity",
}


def sitio_no_permitido(p: Path) -> str:
    """'' si se puede escribir. Editar un archivo que YA existe siempre se permite."""
    try:
        r = p.expanduser().resolve()
        rel = r.relative_to(ANTIGRAVITY.resolve())
    except (ValueError, OSError):
        return ""  # fuera de antigravity (proyectos del usuario): no aplica
    if r.exists() or not rel.parts:
        return ""
    if rel.parts[0] in CARPETAS_PERMITIDAS:
        return ""
    guia = "; ".join(f"{k}/ = {v}" for k, v in list(CARPETAS_PERMITIDAS.items())[:5])
    return (f"No se crean archivos nuevos en antigravity/{rel.parts[0]}/. Cada cosa en su sitio: {guia}. "
            "Vuelve a crearlo en la carpeta que toca.")


def autoriza_web(conv: str) -> bool:
    return bool(conv) and leer_json(AUTORIZA_CODIGO, {}).get(conv) is True


def limpiar_comando(comando: str) -> str:
    c = comando.strip()
    if len(c) > 1 and c[0] == c[-1] == '"':  # a veces llega envuelto en comillas
        c = c[1:-1].strip()
    return c


def regla_contenido(nombre: str, args: dict, conv: str = "") -> tuple[str, str]:
    """Reglas sobre lo que hace la herramienta (archivos, comandos)."""
    ruta = ruta_de(args)
    p = Path(ruta).expanduser() if ruta else None
    comando = str(args.get("CommandLine") or args.get("command") or "")
    cmd_limpio = limpiar_comando(comando)
    if WINDOWS and cmd_limpio and RE_PYTHON_ATAJO.search(cmd_limpio):
        return "deny", (f"En el sandbox de Antigravity 'python'/'py' a secas puede no funcionar en Windows. Repite el comando "
                        f"asi: {PY} ... (es <PYTHON> en GEMINI.md).")
    if WINDOWS and cmd_limpio and RE_RUTA_ESPACIO_SIN_COMILLAS.search(cmd_limpio):
        return "deny", ("La ruta del programa tiene espacios y va SIN comillas: asi PowerShell no ejecuta nada y no avisa "
                        f"(parece que termino bien, pero no corrio). Repitelo asi: {PY} \"<script>\" <args> "
                        "(con & delante y la ruta entre comillas).")
    # Ley 5: nada "en caliente". Editar un proyecto con git en la rama principal -> antes una rama de pruebas.
    if RE_ESCRIBIR.search(nombre) and p and not dentro_de(p, GEMINI):
        rama, repo = rama_git(p)
        if rama in RAMAS_PRINCIPALES and repo is not None:
            return "force_ask", (f"LEY 5 (cero experimentos en vivo): vas a editar {p.name} en la rama PRINCIPAL '{rama}' de "
                                 f"{repo.name}. Primero crea una rama de pruebas: git -C \"{repo}\" switch -c nova/<arreglo>. "
                                 f"Solo si {USUARIO} dice que es en caliente, lo confirma aqui.")
    texto_args = ruta + " " + comando
    if RE_DOC_EN_SCRATCH.search(texto_args) and (RE_ESCRIBIR.search(nombre) or comando):
        return "deny", ("Los documentos (PDF, Word, Excel, PowerPoint) van a ~/.gemini/antigravity/documentos_generados/"
                        f"<proyecto>/, no a scratch. Usa el redactor: {PY} \"{REDACTOR}\" --escaleta <guion.json> "
                        "--salida ~/.gemini/antigravity/documentos_generados/<proyecto>/<nombre>.pdf")
    if comando and RE_CMD_SECRETO.search(comando) and not re.search(r"(?i)\.py\b|\bnode\b|\.mjs\b|\bnpm\b", comando):
        return "force_ask", ("AVISO CLAVES: ese comando muestra claves (vault, .env, credenciales) y su contenido viajara a los "
                             f"servidores del modelo. Solo si {USUARIO} lo ha pedido expresamente.")
    if comando and RE_CMD_ESCRIBE.search(comando):
        for trozo in re.findall(r"[A-Za-z]:\\[^\"'|;&<>]+|~[\\/][^\"'|;&<>\s]+|(?<![\w.])/[^\"'|;&<>\s]+", comando):
            if protegida(trozo.strip()):
                return "deny", (f"Comando que escribe en una carpeta protegida ({trozo.strip()[:120]}). "
                                f"Nova no escribe ahi ni por terminal. Pideselo a {USUARIO}.")
    if comando and RE_PELIGROSO.search(comando):
        return "force_ask", f"Comando destructivo: {comando[:160]}. {USUARIO} tiene que confirmarlo."
    if RE_ESCRIBIR.search(nombre) and p:
        if protegida(ruta):
            return "deny", f"Carpeta protegida ({ruta}): Nova no escribe aqui. Pideselo a {USUARIO}."
        if p.name.lower().startswith(".env"):
            return "deny", f"Los .env y las claves solo los toca {USUARIO}."
        sitio = sitio_no_permitido(p)
        if sitio:
            return "deny", sitio
        n = lineas_nuevas(args)
        # Web grande desde la nube: BLOQUEO salvo "escribelo tu" o web de referencia en el ultimo mensaje del usuario.
        if p.suffix.lower() in EXT_WEB and n > MAX_LINEAS:
            if autoriza_web(conv):
                return "allow", ""
            return "deny", (f"BLOQUEADO: {n} lineas de web ({p.name}) escritas desde la nube (limite {MAX_LINEAS}). Las webs "
                            "de negocio salen de la biblioteca en local (0 tokens): rellena <carpeta>/datos.json y lanza "
                            f"{PY} \"{MONTAR}\" --datos \"<carpeta>/datos.json\" --categoria auto --out \"<carpeta>/index.html\". "
                            f"Solo si {USUARIO} dice 'escribelo tu' (o da una web de referencia) puedes escribirla tu.")
        if p.suffix.lower() in EXT_CODIGO and n > MAX_LINEAS:
            return "force_ask", (f"La nube va a escribir {n} lineas de codigo en {p.name} (limite {MAX_LINEAS}). Algo tan grande "
                                 f"lo puede picar el obrero local: {PY} \"{OBRERO}\" --task \"<encargo>\". "
                                 f"{USUARIO} decide si lo autoriza.")
    if RE_LEER.search(nombre) and p and RE_SECRETO.search(str(p)):
        return "force_ask", (f"AVISO CLAVES: {p.name} guarda claves y, si se lee, su contenido viajara a los servidores del "
                             f"modelo. Solo si {USUARIO} lo ha pedido expresamente (los scripts las cargan solos en local).")
    if RE_LEER.search(nombre) and p:
        basura = set(x.lower() for x in p.parts) & CARPETAS_BASURA
        if basura:
            return "deny", (f"No se lee dentro de {', '.join(sorted(basura))}: son dependencias o archivos generados. "
                            "Busca en el codigo fuente del proyecto.")
        if p.suffix.lower() in EXT_PESADAS:
            return "deny", (f"{p.name} es un documento o archivo de datos: no se mete entero en la nube. Usa "
                            f"{PY} \"{RESUMIR}\" <archivo> (o conversor.py) o busca con grep/rg.")
        try:
            kb = p.stat().st_size / 1024 if p.is_file() else 0
        except OSError:
            kb = 0
        if kb > MAX_KB:
            return "deny", (f"{p.name} pesa {kb:.0f} KB: no se lee entero. Lee solo un rango de lineas, busca con grep/rg "
                            "o resumelo con resumir.py.")
    return "allow", ""


# ---------------------------------------------------------------- nivel verde: auto_approve (sin clic del usuario)
# Solo comandos de LECTURA o de las herramientas locales de Nova, y ediciones pequenas en proyectos.
RE_ENVOLTORIO = re.compile(r'(?is)^\s*(?:powershell(?:\.exe)?|pwsh)(?:\s+-\w+)*\s+-Command\s+(["\'])(.*)\1\s*$'
                           r'|^\s*cmd(?:\.exe)?\s+/[cC]\s+(["\']?)(.*)\3\s*$')
CMD_SEGUROS = [
    r"Test-Path\b", r"Get-ChildItem\b", r"(ls|dir|gci)\b", r"Get-Item\b", r"Get-ItemProperty\b", r"Resolve-Path\b",
    r"Get-Location\b", r"pwd\b", r"(Set-Location|cd|sl)\b", r"Get-Content\b", r"(cat|type|gc|head|tail|wc)\b",
    r"Select-String\b", r"(rg|grep|findstr)\b", r"Measure-Object\b", r"Select-Object\b", r"Sort-Object\b",
    r"Where-Object\b", r"Format-(Table|List)\b", r"Out-String\b", r"(Write-Output|Write-Host|echo)\b", r"Get-Command\b",
    r"(where|which)(\.exe)?\b", r"git\s+(status|diff|log|show|branch|rev-parse|remote\s+-v|ls-files)\b",
    r"[\"']?[^;|&\"']*(python3?|py)(\.exe)?[\"']?\s+[^;|&]*?(montar|nova_local_worker|nova_revisor|resumir|conversor|redactor)\.py\b",
    r"(python3?|py|node|npm|git|ollama)(\.exe)?\s+(--version|-V)\b", r"ollama\s+(list|ps)\b",
    r"npm\s+run\s+(dev|build|test|lint|preview|typecheck)\b",
    r"New-Item\s+(-ItemType\s+Directory|-Type\s+Directory|.*-ItemType\s+Directory)", r"(mkdir|md)\b",
]
RE_CMD_SEGURO = re.compile(r"(?i)^\s*&?\s*(" + "|".join(CMD_SEGUROS) + r")")
RE_PELIGRO_EN_SEGURO = re.compile(r"(?i)>|\|\s*(iex|Invoke-Expression|sh|bash|zsh|cmd|powershell)\b|Invoke-WebRequest|curl|wget|\$\(|`")


def comando_seguro(comando: str) -> bool:
    m = RE_ENVOLTORIO.match(comando)
    if m:
        comando = m.group(2) if m.group(2) is not None else m.group(4)
    if not comando.strip() or RE_PELIGRO_EN_SEGURO.search(comando):
        return False
    trozos = [t for t in re.split(r";|&&|\|\||\|", comando) if t.strip()]
    return all(RE_CMD_SEGURO.match(t) for t in trozos)


def nivel_verde(nombre: str, args: dict) -> bool:
    """True si la herramienta es segura y puede pasar sin clic (solo se llama si las reglas ya dieron 'allow')."""
    comando = str(args.get("CommandLine") or args.get("command") or "")
    if comando:
        return comando_seguro(comando)
    ruta = ruta_de(args)
    if RE_LEER.search(nombre):
        return True  # claves, pesados y basura ya se frenaron antes
    if RE_ESCRIBIR.search(nombre) and ruta:
        p = Path(ruta).expanduser()
        try:
            rel = p.resolve().relative_to(Path.home().resolve())
        except (ValueError, OSError):
            return False  # fuera de la carpeta personal: lo decide el usuario
        oculta = bool(rel.parts) and rel.parts[0].startswith(".")  # ~/.gemini, ~/.ssh, ~/.config...
        sistema = bool(rel.parts) and rel.parts[0].lower() in ("appdata", "library")
        return not oculta and not sistema and lineas_nuevas(args) <= MAX_LINEAS
    return False


def regla_gasto(conv: str, transcript: str) -> tuple[str, str, dict]:
    """Freno de gasto: pregunta UNA vez al cruzar cada tope de tokens y cada bloque de herramientas seguidas."""
    if not transcript:
        return "allow", "", {}
    total, seguidas, contexto, des = gasto(transcript)
    info = {"tokens_conv": total, "tokens_bruto": des["bruto"], "seguidas": seguidas, "contexto": contexto}
    estado = leer_json(ESTADO, {})
    e = estado.get(conv, {"tope": 0, "bloque": 0})
    decision, motivo = "allow", ""
    tope = total // TOPE_TOKENS
    if tope > e.get("tope", 0):
        e["tope"] = tope
        decision, motivo = "force_ask", (
            f"FRENO DE GASTO: esta conversacion lleva ~{total // 1000}k tokens REALES "
            f"({des['nuevos'] // 1000}k nuevos + {des['cache'] // 1000}k de cache al 10 % + {des['salida'] // 1000}k de salida; "
            f"sin descontar la cache serian {des['bruto'] // 1000}k). "
            f"{USUARIO} decide si se sigue o se abre una ventana nueva con el puente.")
    bloque = seguidas // MAX_SEGUIDAS
    if decision == "allow" and bloque > e.get("bloque", 0):
        e["bloque"] = bloque
        decision, motivo = "force_ask", (f"Llevo {seguidas} herramientas seguidas sin que {USUARIO} escriba. "
                                         "Pregunto antes de seguir.")
    if seguidas < MAX_SEGUIDAS:
        e["bloque"] = 0  # el usuario ha escrito: el contador de seguidas vuelve a empezar
    estado[conv] = e
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-200:])), encoding="utf-8")
    except OSError:
        pass
    return decision, motivo, info


def main() -> None:
    inicio = time.time()
    fila = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}
    salida = {"decision": "allow"}
    try:
        crudo = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")  # acepta BOM (PowerShell lo pone)
        datos = json.loads(crudo or "{}")
        llamada = datos.get("toolCall") or datos.get("tool_call") or {}
        nombre = llamada.get("name") or datos.get("toolName") or ""
        args = llamada.get("args") or llamada.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        conv = str(datos.get("conversationId", ""))
        modo = leer_json(CONFIG, {}).get("modo", "registro")
        fila.update({
            "conv": conv[:8], "herramienta": nombre, "claves_args": sorted(args.keys()), "ruta": ruta_de(args),
            "lineas": lineas_nuevas(args), "comando": str(args.get("CommandLine", ""))[:200], "modo": modo,
        })
        decision, motivo = regla_contenido(nombre, args, conv)
        dec_gasto, motivo_gasto, info = regla_gasto(conv, str(datos.get("transcriptPath") or ""))
        fila.update(info)
        if decision == "allow" and dec_gasto != "allow":
            decision, motivo = dec_gasto, motivo_gasto
        fila["decision_calculada"] = decision
        if motivo:
            fila["motivo"] = motivo[:200]
        if decision == "allow" and nivel_verde(nombre, args):
            decision, motivo = "auto_approve", ""
            fila["decision_calculada"] = decision
        if modo == "bloqueo" and decision != "allow":
            salida = {"decision": decision, "reason": motivo} if motivo else {"decision": decision}
    except Exception as e:  # un hook roto nunca deja a Nova sin trabajar
        fila["error_hook"] = f"{type(e).__name__}: {e}"
    fila["ms"] = round((time.time() - inicio) * 1000)
    fila["decision"] = salida["decision"]
    apuntar(fila)
    sys.stdout.write(json.dumps(salida, ensure_ascii=True))


if __name__ == "__main__":
    main()
