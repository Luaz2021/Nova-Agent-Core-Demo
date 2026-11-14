"""
NOVA HOOK - Antigravity llama a este script ANTES de cada herramienta del agente (PreToolUse, ~/.gemini/config/hooks.json)

Por que: las leyes de GEMINI.md son texto y Flash se las salta (07/11: la nube pico las webs con write_file aunque la
ley 14 lo prohibia, y una sesion quemo 8 millones de tokens). El hook lo comprueba el sistema, no el modelo.

Modos (nova_hooks_config.json, junto a este archivo):
  "registro" -> nunca bloquea; apunta cada llamada en memory/registros/telemetria_hooks.jsonl.
  "bloqueo"  -> ademas aplica las reglas (de mas grave a menos):
     deny  (prohibido, sin preguntar):
       - escribir en carpetas protegidas (clones_web o con un archivo .nova_protegido) o en .env
       - leer dentro de node_modules / .git / dist / build / .next / __pycache__
       - leer de golpe archivos enormes (> MAX_KB) o documentos/datos (.pdf .docx .xlsx .pptx .ipynb .jsonl .parquet...)
         -> usar resumir.py / conversor.py, o buscar con grep/rg
     force_ask (Antigravity se lo pregunta a Alexander siempre):
       - la nube escribiendo mas de MAX_LINEAS de codigo (el codigo nuevo lo pica Qwen con nova_tarea.py)
       - comandos destructivos (borrados recursivos, git push --force, git reset --hard, DROP TABLE, formatear...)
       - FRENO DE GASTO: la conversacion pasa de cada TOPE_TOKENS (1M, 2M, 3M...) -> pregunta una vez por tope
       - mas de MAX_SEGUIDAS herramientas encadenadas sin que Alexander escriba -> pregunta una vez cada bloque
Siempre: si algo falla dentro del hook, responde "allow" (un hook roto no puede dejar a Nova sin trabajar) y lo apunta.

Formato (docs de Antigravity): entra por stdin un JSON con toolCall.name, toolCall.args y transcriptPath; sale por
stdout {"decision": "allow" | "deny" | "force_ask", "reason": "..."}.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CONFIG = AQUI / "nova_hooks_config.json"
ESTADO = (
    AQUI / ".nova_hooks_estado.json"
)  # topes de gasto ya preguntados por conversacion
REGISTRO = (
    Path.home()
    / ".gemini"
    / "antigravity"
    / "memory"
    / "registros"
    / "telemetria_hooks.jsonl"
)

PROTEGIDAS = (
    "clones_web",
    "motor_clones",
    "biblioteca_web",
    "nova_core",
    "respaldos_claude",
    "nova_env",
)
# 11/11 (Claude): el codigo oficial de Nova. Nova no lo edita con sus herramientas de archivos (en el PC lo parcheaba
# "para arreglar" y dejaba restos). Si algo falla -> nova_doctor.ps1. Por terminal se sigue pudiendo EJECUTAR.
_RAIZ_NOVA = str(Path.home() / ".gemini" / "antigravity").lower()
CODIGO_OFICIAL = (_RAIZ_NOVA + "\\scripts\\", _RAIZ_NOVA + "\\herramientas\\")
# Copiar a mano desde Drive (en el PC Nova copio carpetas enteras saltandose el sync y dejo duplicados)
RE_COPIA_DE_DRIVE = re.compile(
    r"(?i)\b(Copy-Item|copy|xcopy|robocopy|cp|Move-Item|move|mv|Expand-Archive)\b.*"
    r"(Mi unidad|My Drive|Google Drive|\bG:[\\/])"
)
# pip/uv instalando en el Python de Nova o en el de Windows (las librerias de Nova las pone el Doctor)
RE_PIP_INSTALA = re.compile(r"(?i)\b(pip3?|uv\s+pip)\s+install\b|-m\s+pip\s+install\b")
RE_VENV_PROYECTO = re.compile(
    r"(?i)[\\/]\.?venv[\\/]|--target\b|\bproyectos[\\/]|\bscratch[\\/]"
)
_GEM = str(Path.home() / ".gemini").lower()
PROTEGIDAS_RUTAS = (
    _GEM + "\\config",
)  # reglas y skills de Nova: solo las cambian Claude o Alexander
# Secretos: ni se leen ni se muestran en la nube (los scripts que los necesitan los leen solos, en local)
RE_SECRETO = re.compile(
    r"(?i)(^|[\\/])vault([\\/]|$)|(^|[\\/])\.env(\.(?!example\b|sample\b|template\b)[\w.-]+)?$|(^|[\\/])\.env(?=[\s'\"]|$)"
    r"|oauth_creds\.json|(^|[\\/])secrets?[\w.-]*\.json|credentials[\w.-]*\.json|\.pem$|\.p12$|\.pfx$|id_rsa|id_ed25519"
    r"|(^|[\\/])[\w.-]*\.env$"
)
RE_CMD_SECRETO = re.compile(
    r"(?i)(vault[\\/]|oauth_creds\.json|secrets?[\w.-]*\.json|credentials[\w.-]*\.json|\.pem\b|id_rsa|id_ed25519"
    r"|[\\/ '\"]\.env(?!\.example|\.sample|\.template)\b|[\w-]+\.env\b)"
)
RE_CMD_ESCRIBE = re.compile(
    r"(?i)(^|[\s;|&('\"`{])(Set-Content|Add-Content|Out-File|New-Item|Copy-Item|Move-Item|Remove-Item|Rename-Item|copy|xcopy|"
    r"robocopy|move|ren|del|erase|rm|mv|cp|mkdir|md|tee|sed\s+-i)\b|>{1,2}"
)
MARCA_PROTEGIDO = ".nova_protegido"
# 12/11 (Claude): Nova escribio la clave de Gamma a mano en scripts de scratch. Las claves SOLO viven en el cofre
# (vault\secrets.json, lo rellena Alexander) y el codigo las lee en local (os.environ / el cofre). Formas conocidas:
RE_CLAVE_API = re.compile(
    r"\bsk-(?:gamma-|ant-|proj-)?[A-Za-z0-9_-]{20,}"  # Gamma, Anthropic, OpenAI
    r"|\bsk_[a-f0-9]{32,}"  # ElevenLabs
    r"|\bAIza[0-9A-Za-z_-]{30,}"  # Google / Gemini
    r"|\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}"  # GitHub
    r"|\bxox[abprs]-[A-Za-z0-9-]{20,}"  # Slack
    r"|\bAKIA[0-9A-Z]{16}\b"  # AWS
    r"|\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9]{16,}"  # Resend
    r"|\bsb_(?:secret|publishable)_[A-Za-z0-9_-]{20,}"  # Supabase
    r"|\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}"  # JWT (service_role de Supabase...)
    r"|\b(?:hf|gsk|pk_live|sk_live|rk_live)_[A-Za-z0-9]{20,}"  # HuggingFace, Groq, Stripe
    r"|(?i:\b(?:api[_-]?key|apikey|secret|token|password|passwd|clave)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-./+=]{24,}[\"'])"
)
MSG_CLAVE = (
    "Las CLAVES DE API no se escriben en codigo, comandos ni documentos: viven SOLO en el cofre "
    "(G:\\Mi unidad\\Antigravity\\vault\\secrets.json), que rellena Alexander. En el codigo leela en local: "
    'os.environ.get("NOMBRE_API_KEY") (las carga nova_vault_sync.ps1) o el cofre con json. Si falta una clave, '
    "pidele a Alexander que la anada al cofre; no la pegues tu."
)


def lleva_clave(nombre: str, args: dict, comando: str) -> bool:
    if comando and RE_CLAVE_API.search(comando):
        return True
    if not RE_ESCRIBIR.search(nombre):
        return False
    textos = []
    for k in (
        CLAVES_TEXTO
    ):  # solo el texto NUEVO: quitar una clave vieja de un script si se deja
        v = args.get(k)
        for item in v if isinstance(v, list) else [v]:
            if isinstance(item, dict):
                textos += [
                    x
                    for c, x in item.items()
                    if isinstance(x, str)
                    and re.search(r"(?i)replace|new|nuevo|content$", c)
                    and not re.search(r"(?i)target|old|viejo", c)
                ]
            elif isinstance(item, str):
                textos.append(item)
    return any(RE_CLAVE_API.search(t) for t in textos)


def _python_del_equipo() -> str:
    """11/11 (Claude): el Python de ESTE equipo (laptop 3.14, PC 3.13/3.11). Antes la ruta de la laptop iba a mano y en
    el PC el hook mandaba a Nova a un python.exe que no existe. Mismo orden que scripts\\nova_python.ps1."""
    import os

    la = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    propio = Path.home() / ".gemini" / "nova_env"
    cands = (
        [str(propio / "Scripts" / "python.exe"), str(propio / "bin" / "python3"), str(propio / "bin" / "python")]
        if (propio / ".huella_nova").is_file() or (propio / "bin" / "python").is_file()
        else []
    )
    cands += [os.environ.get("NOVA_PYTHON", "")]
    cands += [
        str(la / "Python" / f"pythoncore-{v}-64" / "python.exe")
        for v in ("3.14", "3.13", "3.12")
    ]
    cands += [
        str(la / "Programs" / "Python" / f"Python{v}" / "python.exe")
        for v in ("314", "313", "312")
    ]
    cands += [f"C:\\Python{v}\\python.exe" for v in ("314", "313", "312", "311")]
    for c in cands:
        if c and Path(c).is_file():
            return c
    exe = Path(sys.executable)  # el Python que corre este hook (pythonw -> python)
    return (
        str(exe.with_name("python.exe"))
        if exe.with_name("python.exe").is_file()
        else str(exe)
    )


PYTHON_NOVA = _python_del_equipo()
# "python x.py", "py -3 ...", "cmd /c python ...", "& python ..." (no cuenta si ya va con ruta: ...\python.exe)
# ruta de un programa (.exe/.ps1/.bat/.cmd/.py) CON espacios y SIN comillas al empezar el comando (o tras ; | &&)
# (el espacio tiene que estar DENTRO de una carpeta, "...\Alexander Martinez\...", no entre el programa y sus argumentos)
RE_RUTA_ESPACIO_SIN_COMILLAS = re.compile(
    r"(?i)(^|[;|]\s*|&&\s*)[a-z]:\\(?:[^\"'\\\r\n;|]+\\)*?[^\"'\\\r\n;|]* [^\"'\\\r\n;|]*\\"
    r"(?:[^\"'\\\r\n;|]+\\)*[^\"'\\\s;|]+\.(exe|ps1|bat|cmd|py)\b"
)
RE_PYTHON_ATAJO = re.compile(
    r"(?i)(^|[;&|(]|\bcmd(\.exe)?\s+/[ck]\s+\"?)\s*(python3?|py)(\.exe)?(?=\s|$)"
)
RAMAS_PRINCIPALES = {"main", "master", "production", "prod", "produccion", "release"}


def rama_git(p: Path) -> tuple[str, Path | None]:
    """(rama actual, carpeta del repo) si p esta dentro de un repo git; ("", None) si no. Solo lee .git\\HEAD."""
    try:
        d = p if p.is_dir() else p.parent
        for carpeta in [d, *d.parents]:
            g = carpeta / ".git"
            if g.is_file():  # worktree o submodulo: "gitdir: <ruta>"
                destino = Path(g.read_text(encoding="utf-8").split(":", 1)[1].strip())
                g = destino if destino.is_absolute() else (carpeta / destino)
            if (g / "HEAD").is_file():
                head = (g / "HEAD").read_text(encoding="utf-8").strip()
                return (
                    head.rsplit("/", 1)[-1] if head.startswith("ref:") else "(detached)"
                ), carpeta
            if carpeta == carpeta.parent:
                break
    except (OSError, IndexError):
        pass
    return "", None


RE_DOC_EN_SCRATCH = re.compile(
    r"(?i)[\\/]antigravity[\\/]scratch[\\/][^\"'|;&<>\n]*\.(pdf|docx|doc|xlsx|pptx)\b"
)
MAX_LINEAS = 150  # linea dulce 08/11: hasta 150 lineas las escribe Nova; mas, Qwen por secciones (nova_secciones.py)
MAX_KB = 200
TOPE_TOKENS = 300_000  # 09/11: tokens REALES (cache al 10 %); antes 1M contando la cache entera (~200k reales)
TOPE_CONTEXTO = 100_000  # regla de Alexander: contexto de la ventana > 100k -> /compact
MAX_SEGUIDAS = 25
CARPETAS_BASURA = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    ".turbo",
    ".cache",
}
EXT_PESADAS = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ipynb",
    ".jsonl",
    ".parquet",
    ".zip",
    ".mp4",
    ".mov",
    ".db",
    ".sqlite",
    ".log",
}
EXT_CODIGO = {
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".vue",
    ".svelte",
    ".py",
    ".java",
    ".kt",
    ".swift",
    ".dart",
    ".php",
    ".cs",
    ".go",
    ".rs",
    ".sql",
}
RE_ESCRIBIR = re.compile(r"write|replace|edit|create_file|save_file", re.IGNORECASE)
RE_LEER = re.compile(
    r"read|view|open_file|cat_file|list_dir|list_files|grep_search|find_by_name", re.IGNORECASE
)
RE_PELIGROSO = re.compile(
    r"(?i)\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r|Remove-Item\b[^\n]*-Recurse|\brd\s+/s|\brmdir\s+/s|\bdel\s+/[sq]|"
    r"git\s+push\s+[^\n]*(--force|-f\b)|git\s+reset\s+--hard|git\s+clean\s+-[a-z]*f|\bdrop\s+(table|database|schema)\b|"
    r"\btruncate\s+table\b|\bformat\s+[a-z]:|Format-Volume|\bmkfs\b|Clear-Content\b"
)
CLAVES_RUTA = (
    "TargetFile",
    "targetFile",
    "AbsolutePath",
    "absolutePath",
    "path",
    "Path",
    "file_path",
    "filePath",
    "target_file",
    "DirectoryPath",
    "SearchPath",
    "SearchDirectory",
)
CLAVES_TEXTO = (
    "CodeContent",
    "content",
    "Content",
    "code",
    "ReplacementContent",
    "Replacement",
    "new_text",
    "newText",
    "replacement",
    "texto_nuevo",
    "ReplacementChunks",
    "chunks",
)


def leer_json(p: Path, defecto):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return defecto


def apuntar(fila: dict) -> None:
    try:
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    except Exception:
        pass


def ruta_de(args: dict) -> str:
    for k in CLAVES_RUTA:
        if isinstance(args.get(k), str):
            return args[k]
    return next(
        (
            v
            for k, v in args.items()
            if isinstance(v, str) and re.search(r"path|file|target|dir", k, re.IGNORECASE)
        ),
        "",
    )


def lineas_nuevas(args: dict) -> int:
    total = 0
    for k in CLAVES_TEXTO:
        v = args.get(k)
        if isinstance(v, str):
            total += v.count("\n") + 1
        elif isinstance(v, list):
            for t in v:
                if isinstance(t, dict):
                    total += sum(
                        str(x).count("\n") + 1
                        for kk, x in t.items()
                        if re.search(r"replac|new|content", kk, re.IGNORECASE)
                    )
    return total


def protegida(ruta: str) -> bool:
    if not ruta:
        return False
    p = Path(ruta)
    if str(p).lower().startswith(_GEM) and any(parte.lower() in PROTEGIDAS for parte in p.parts):
        return True
    if str(p).lower().startswith(PROTEGIDAS_RUTAS):
        return True
    return any((c / MARCA_PROTEGIDO).exists() for c in p.parents)


PRECIO_CACHE = 0.10  # 09/11: Gemini cobra la entrada leida de cache con un 90 % de descuento (cache implicita)


def gasto(transcript: str) -> tuple[int, int, int, dict]:
    """(tokens REALES de la conversacion = nuevos + cache al 10 % + salida, herramientas seguidas desde el ultimo
    mensaje de Alexander, tamano del contexto en la ultima llamada, desglose {nuevos, cache, salida, bruto})."""
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
                    contexto = int(o.get("input_tokens") or 0) + int(
                        o.get("cache_read_tokens") or 0
                    )
                if o.get("type") == "USER_INPUT":
                    seguidas = 0
                seguidas += len(o.get("tool_calls") or [])
    except OSError:
        pass
    real = int(nuevos + cache * PRECIO_CACHE + salida)
    return (
        real,
        seguidas,
        contexto,
        {
            "nuevos": nuevos,
            "cache": cache,
            "salida": salida,
            "bruto": nuevos + cache + salida,
        },
    )


# Orden de Nova (08/11): dentro de .gemini\antigravity, los ARCHIVOS NUEVOS solo se crean en estas carpetas.
ANTIGRAVITY = (Path.home() / ".gemini" / "antigravity").resolve()
CARPETAS_PERMITIDAS = {
    "scratch": "herramientas o scripts nuevos (pasan por inspeccion de Alexander y Claude)",
    "documentos_generados": "todo documento, imagen o txt que genere Nova (por proyecto: documentos_generados\\<proyecto>\\)",
    "proyectos": "ideas (_ideas\\<nombre>.md) y conocimiento de cada proyecto (README.md, docs\\)",
    "temporal": "adjuntos del chat (lo gestiona el puente)",
    "brain": "artefactos propios de Antigravity",
    "conversations": "Antigravity",
    "cache": "Antigravity",
    "log": "Antigravity",
    "daemon": "Antigravity",
}


def sitio_no_permitido(p: Path) -> str:
    """'' si se puede escribir. Editar un archivo que YA existe siempre se permite (tasks.md, mis_quejas.md...)."""
    try:
        r = p.resolve()
        rel = r.relative_to(ANTIGRAVITY)
    except (ValueError, OSError):
        return ""  # fuera de antigravity (proyectos del Escritorio, etc.): no aplica
    if r.exists() or not rel.parts:
        return ""
    if rel.parts[0] in CARPETAS_PERMITIDAS:
        return ""
    guia = "; ".join(f"{k}\\ = {v}" for k, v in list(CARPETAS_PERMITIDAS.items())[:4])
    return (
        f"No se crean archivos nuevos en antigravity\\{rel.parts[0]}\\. Cada cosa en su sitio: {guia}. "
        f"Vuelve a crearlo en la carpeta que toca."
    )


EXT_WEB = {
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".vue",
    ".svelte",
    ".astro",
}
AUTORIZA_CODIGO = (
    AQUI / ".autoriza_codigo.json"
)  # lo escribe nova_hook_turno.py con cada mensaje de Alexander
NOVA_TAREA = str(Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_tarea.py")


def autoriza_web(conv: str) -> bool:
    return bool(conv) and leer_json(AUTORIZA_CODIGO, {}).get(conv) is True


def regla_contenido(nombre: str, args: dict, conv: str = "") -> tuple[str, str]:
    """Reglas sobre lo que hace la herramienta (archivos, comandos)."""
    ruta = ruta_de(args)
    p = Path(ruta) if ruta else None
    comando = str(args.get("CommandLine") or args.get("command") or "")
    # 09/11 (Claude): el permiso de pago de Brave solo lo da Alexander. Nova no lee la clave ni llama a /pase_pago.
    if re.search(
        r"(?i)pase_pago|GRANT_PAYMENT_PASS|_permitirPago|\.clave\b|nova_core[\\/]+\.[\w*?]|nova_core[\\/]+\*",
        ruta + " " + comando + " " + json.dumps(args, ensure_ascii=False),
    ):
        return "deny", (
            "El permiso de pago de Brave solo lo da Alexander escribiendo 'autorizo el pago'. Nova no toca esa "
            "clave ni llama a /pase_pago."
        )
    if lleva_clave(nombre, args, comando):
        return "deny", MSG_CLAVE
    # 09/11 (Claude): en el sandbox de Antigravity el atajo python/py de Windows falla ("El sistema no tiene acceso al
    # archivo") y Nova se pasaba 10 intentos probando node, typst, Edge... Se frena al primero con la ruta buena.
    # 09/11 tarde: Antigravity a veces manda el comando envuelto en comillas ("python x.py") y la regla no lo veia
    cmd_limpio = comando.strip()
    if len(cmd_limpio) > 1 and cmd_limpio[0] == cmd_limpio[-1] == '"':
        cmd_limpio = cmd_limpio[1:-1].strip()
    if cmd_limpio and RE_PYTHON_ATAJO.search(cmd_limpio):
        return "deny", (
            f"En el sandbox de Antigravity 'python'/'py' a secas NO funciona. Repite el comando asi: "
            f'& "{PYTHON_NOVA}" ... (es <PYTHON> en GEMINI.md).'
        )
    # 09/11 tarde (web del cafe): "C:\Users\Usuario\...\python.exe" SIN comillas -> PowerShell no ejecuta
    # NADA y no da error (salida vacia, codigo 0). Nova creyo que nova_tarea.py habia fallado y escribio la web desde
    # la nube (372 lineas). Se frena aqui con la forma buena.
    if cmd_limpio and RE_RUTA_ESPACIO_SIN_COMILLAS.search(cmd_limpio):
        return "deny", (
            "La ruta del programa tiene espacios y va SIN comillas: asi PowerShell no ejecuta nada y no avisa "
            f'(parece que termino bien, pero no corrio). Repitelo asi: & "{PYTHON_NOVA}" "<script>" <args> '
            "(con & delante y la ruta entre comillas)."
        )
    # 11/11 (Claude) BLINDAJE: cuando algo falla Nova no improvisa arreglos en el equipo.
    if cmd_limpio and RE_COPIA_DE_DRIVE.search(cmd_limpio):
        return "deny", (
            "No copies nada de Drive a mano: Drive llega a este equipo SOLO con el sync "
            "(<PYTHON> <NOVA_HOME>\\antigravity\\scripts\\nova_sync_pedir.py Bajar). Si falta algo despues del "
            "sync, ejecuta el Doctor (powershell -ExecutionPolicy Bypass -File "
            '"<NOVA_HOME>\\antigravity\\scripts\\nova_doctor.ps1") y cuentale a Alexander su ultima linea.'
        )
    if (
        cmd_limpio
        and RE_PIP_INSTALA.search(cmd_limpio)
        and not RE_VENV_PROYECTO.search(cmd_limpio)
    ):
        return "deny", (
            "Las librerias de Nova las instala el Doctor en su Python propio (nova_core\\requisitos_nova.txt), "
            "no tu con pip. Ejecuta el Doctor (powershell -ExecutionPolicy Bypass -File "
            '"<NOVA_HOME>\\antigravity\\scripts\\nova_doctor.ps1"); si falta una libreria nueva, diselo a '
            "Alexander para que Claude la anada a la lista. Para un PROYECTO usa su propio .venv."
        )
    # 09/11 Ley 5 vigilada: nada "en caliente". Editar un proyecto con git estando en la rama principal -> que Nova
    # cree antes una rama de pruebas (git switch -c nova/<arreglo>) o que Alexander lo confirme con un clic.
    if RE_ESCRIBIR.search(nombre) and p and not str(p).lower().startswith(_GEM):
        rama, repo = rama_git(p)
        if rama in RAMAS_PRINCIPALES and not autoriza_web(conv):
            return "force_ask", (
                f"LEY 5 (cero experimentos en vivo): vas a editar {p.name} en la rama PRINCIPAL '{rama}' de "
                f'{repo.name}. Primero crea una rama de pruebas: git -C "{repo}" switch -c nova/<arreglo> '
                "(no copia nada, es instantaneo). Solo si Alexander dice que es en caliente, lo confirma aqui."
            )
    # Documentos para Alexander: a documentos_generados\<proyecto>, nunca a scratch (regla de la ley 6)
    texto_args = ruta + " " + comando
    if RE_DOC_EN_SCRATCH.search(texto_args) and (RE_ESCRIBIR.search(nombre) or comando):
        return "deny", (
            "Los documentos (PDF, Word, Excel, PowerPoint) van a <NOVA_HOME>\\antigravity\\documentos_generados\\"
            "<proyecto>\\, no a scratch. Usa el redactor por tipos: <PYTHON> <NOVA_HOME>\\nova_core\\redactar.py "
            "nuevo --guion <guion.json> --carpeta <proyecto>  (tipos: redactar.py tipos)"
        )
    if (
        comando
        and RE_CMD_SECRETO.search(comando)
        and not re.search(r"(?i)\.py\b|\bnode\b|\.mjs\b|\bnpm\b", comando)
    ):
        return "force_ask", (
            "AVISO CLAVES: ese comando muestra claves (vault, .env, credenciales) y su contenido viajara a los "
            "servidores del modelo. Solo si Alexander lo ha pedido expresamente."
        )
    if comando and RE_CMD_ESCRIBE.search(comando):
        for trozo in re.findall(
            r"[A-Za-z]:\\[^\"'|;&<>]+|~[\\/][^\"'|;&<>\s]+", comando
        ):
            if protegida(trozo.strip()):
                return "deny", (
                    f"Comando que escribe en una carpeta protegida ({trozo.strip()[:120]}). "
                    "Nova no escribe ahi ni por terminal. Pideselo a Alexander."
                )
    if comando and RE_PELIGROSO.search(comando):
        return (
            "force_ask",
            f"Comando destructivo: {comando[:160]}. Alexander tiene que confirmarlo.",
        )
    if RE_ESCRIBIR.search(nombre) and p:
        if protegida(ruta):
            return (
                "deny",
                f"Carpeta protegida ({ruta}): Nova no escribe aqui. Pideselo a Alexander.",
            )
        if str(p).lower().startswith(CODIGO_OFICIAL):
            return "deny", (
                f"{p.name} es codigo oficial de Nova (scripts/herramientas): no se parchea desde el chat. Si algo "
                "no funciona, ejecuta el Doctor (powershell -ExecutionPolicy Bypass -File "
                '"<NOVA_HOME>\\antigravity\\scripts\\nova_doctor.ps1") y cuentale a Alexander el resultado. '
                "Una herramienta NUEVA va a scratch\\<AAAAMMDD>_<nombre>\\."
            )
        if p.name.lower().startswith(".env"):
            return "deny", "Los .env y las claves solo los toca Alexander."
        sitio = sitio_no_permitido(p)
        if sitio:
            return "deny", sitio
        n = lineas_nuevas(args)
        # 09/11 tarde (Claude, a pedido de Luaz): una WEB grande desde la nube ya no es un clic (se aprobaba sin leer:
        # cafe_especialidad 372 y 460 lineas). Es BLOQUEO salvo que Alexander dijera "escribelo tu" en su ultimo mensaje
        # (lo apunta nova_hook_turno.py en .autoriza_codigo.json); con permiso pasa sin clic.
        if p.suffix.lower() in EXT_WEB and n > MAX_LINEAS:
            if autoriza_web(conv):
                return "allow", ""
            return "deny", (
                f"BLOQUEADO: {n} lineas de web ({p.name}) escritas desde la nube (limite {MAX_LINEAS}). Las webs las "
                f'hace la Capa 0 en local: & "{PYTHON_NOVA}" "{NOVA_TAREA}" "<pedido>" --carpeta "<ruta>" '
                "(con & y comillas). Si nova_tarea.py no imprime lineas [NOVA TAREA], el comando esta mal escrito: "
                "corrigelo. Solo si Alexander dice 'escribelo tu' puedes escribirla tu."
            )
        if p.suffix.lower() in EXT_CODIGO and n > MAX_LINEAS:
            return "force_ask", (
                f"La nube va a escribir {n} lineas de codigo en {p.name} (limite 150). Algo tan grande lo pica "
                "Qwen por secciones: <PYTHON> <NOVA_HOME>\\antigravity\\scripts\\nova_secciones.py --carpeta <ruta> "
                "(Nova escribe secciones.json). Alexander decide si lo autoriza."
            )
    if RE_LEER.search(nombre) and p and RE_SECRETO.search(str(p)):
        return "force_ask", (
            f"AVISO CLAVES: {p.name} guarda claves y, si se lee, su contenido viajara a los servidores del "
            "modelo. Solo si Alexander lo ha pedido expresamente (los scripts las cargan solos en local)."
        )
    if RE_LEER.search(nombre) and p:
        if set(x.lower() for x in p.parts) & CARPETAS_BASURA:
            return "deny", (
                f"No se lee dentro de {', '.join(sorted(set(x.lower() for x in p.parts) & CARPETAS_BASURA))}: "
                "son dependencias o archivos generados. Busca en el codigo fuente del proyecto."
            )
        if p.suffix.lower() in EXT_PESADAS:
            return "deny", (
                f"{p.name} es un documento o archivo de datos: no se mete entero en la nube. Usa "
                "<PYTHON> <NOVA_HOME>\\nova_core\\resumir.py (o conversor.py) o busca con grep/rg."
            )
        try:
            kb = p.stat().st_size / 1024 if p.is_file() else 0
        except OSError:
            kb = 0
        if kb > MAX_KB:
            return "deny", (
                f"{p.name} pesa {kb:.0f} KB: no se lee entero. Lee solo un rango de lineas, busca con grep/rg "
                "o resumelo con resumir.py."
            )
    return "allow", ""


# ---------------------------------------------------------------- nivel verde: auto_approve (sin clic de Alexander)
# Antigravity: "auto_approve" aprueba cuando el modo Default preguntaria, respetando las reglas de File Permissions.
# Solo comandos de LECTURA o de la piramide de Nova, y ediciones pequenas en proyectos. Lo demas sigue el modo Default.
RE_ENVOLTORIO = re.compile(
    r'(?is)^\s*(?:powershell(?:\.exe)?|pwsh)(?:\s+-\w+)*\s+-Command\s+(["\'])(.*)\1\s*$|^\s*cmd(?:\.exe)?\s+/[cC]\s+(["\']?)(.*)\3\s*$'
)
CMD_SEGUROS = [
    r"Test-Path\b",
    r"Get-ChildItem\b",
    r"(ls|dir|gci)\b",
    r"Get-Item\b",
    r"Get-ItemProperty\b",
    r"Resolve-Path\b",
    r"Get-Location\b",
    r"pwd\b",
    r"(Set-Location|cd|sl)\b",
    r"Get-Content\b",
    r"(cat|type|gc)\b",
    r"Select-String\b",
    r"(rg|grep|findstr)\b",
    r"Measure-Object\b",
    r"Select-Object\b",
    r"Sort-Object\b",
    r"Where-Object\b",
    r"Format-(Table|List)\b",
    r"Out-String\b",
    r"(Write-Output|Write-Host|echo)\b",
    r"Get-Command\b",
    r"where(\.exe)?\b",
    r"git\s+(status|diff|log|show|branch|rev-parse|remote|ls-files|add|commit|push|pull|fetch|clone|switch|checkout|init|stash|tag)\b",
    r"gh\s+(repo|pr|issue|release|auth|status|api|gist|run|workflow)\b",
    r"(python|py|python3)(\.exe)?\s+[^;|&]*?(nova_tarea|nova_secciones|nova_auditoria|nova_pipeline_local|resumir|conversor|orquestador)\.py\b",
    r"(python|py|node|npm|git|ollama)(\.exe)?\s+(--version|-V)\b",
    r"ollama\s+(list|ps)\b",
    r"node\s+\S*draw\.mjs\b",
    r"npm\s+run\s+(dev|build|test|lint|preview|typecheck)\b",
    r"New-Item\s+(-ItemType\s+Directory|-Type\s+Directory|.*-ItemType\s+Directory)",
    r"(mkdir|md)\b",
]
RE_CMD_SEGURO = re.compile(r"(?i)^\s*&?\s*(" + "|".join(CMD_SEGUROS) + r")")
RE_PELIGRO_EN_SEGURO = re.compile(
    r"(?i)>|\|\s*(iex|Invoke-Expression|sh|bash|cmd|powershell)\b|Invoke-WebRequest|curl|wget|\$\(|`"
)


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
        r = str(Path(ruta)).lower()
        casa = str(Path.home()).lower()
        fuera = (
            (not r.startswith(casa))
            or "\\appdata\\" in r
            or "\\.gemini\\" in r
            or r.startswith(casa + "\\.")
        )
        return not fuera and lineas_nuevas(args) <= MAX_LINEAS
    return False


def regla_gasto(conv: str, transcript: str) -> tuple[str, str, dict]:
    """Freno de gasto: pregunta UNA vez al cruzar cada tope de tokens y cada bloque de herramientas seguidas."""
    if not transcript:
        return "allow", "", {}
    total, seguidas, contexto, des = gasto(transcript)
    info = {
        "tokens_conv": total,
        "tokens_bruto": des["bruto"],
        "seguidas": seguidas,
        "contexto": contexto,
    }
    estado = leer_json(ESTADO, {})
    e = estado.get(conv, {"tope": 0, "bloque": 0, "compact": False})
    decision, motivo = "allow", ""
    # 09/11: el aviso de /compact a los 100k ya NO es un clic aqui: lo pone nova_hook_turno.py (aviso_bufer) dentro del
    # chat, con la copia del .txt, el contador de 5 compactaciones y el salto de ventana (Ley 16).
    tope = total // TOPE_TOKENS
    if decision == "allow" and tope > e.get("tope", 0):
        e["tope"] = tope
        decision, motivo = (
            "force_ask",
            (
                f"FRENO DE GASTO: esta conversacion lleva ~{total // 1000}k tokens REALES "
                f"({des['nuevos'] // 1000}k nuevos + {des['cache'] // 1000}k de cache al 10 % + {des['salida'] // 1000}k de salida; "
                f"sin descontar la cache serian {des['bruto'] // 1000}k). "
                "Alexander decide si se sigue o se abre una ventana nueva con el puente."
            ),
        )
    bloque = seguidas // MAX_SEGUIDAS
    if decision == "allow" and bloque > e.get("bloque", 0):
        e["bloque"] = bloque
        decision, motivo = (
            "force_ask",
            (
                f"Llevo {seguidas} herramientas seguidas sin que Alexander escriba. "
                "Pregunto antes de seguir."
            ),
        )
    if seguidas < MAX_SEGUIDAS:
        e["bloque"] = (
            0  # Alexander ha escrito: el contador de seguidas vuelve a empezar
        )
    estado[conv] = e
    try:
        ESTADO.write_text(json.dumps(estado), encoding="utf-8")
    except OSError:
        pass
    return decision, motivo, info


def main() -> None:
    inicio = time.time()
    fila = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}
    salida = {"decision": "allow"}
    try:
        crudo = sys.stdin.buffer.read().decode(
            "utf-8-sig", errors="replace"
        )  # acepta BOM (PowerShell lo pone)
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
        fila.update(
            {
                "conv": conv[:8],
                "herramienta": nombre,
                "claves_args": sorted(args.keys()),
                "ruta": ruta_de(args),
                "lineas": lineas_nuevas(args),
                "comando": str(args.get("CommandLine", ""))[:200],
                "modo": modo,
            }
        )
        if fila["comando"] and re.search(
            r"nova_tarea\.py|nova_pipeline_local\.py|nova_local_worker\.py|nova_auditoria\.py",
            fila["comando"],
        ):
            fila["piramide"] = True
        decision, motivo = regla_contenido(nombre, args, conv)
        dec_gasto, motivo_gasto, info = regla_gasto(
            conv, str(datos.get("transcriptPath") or "")
        )
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
            salida = (
                {"decision": decision, "reason": motivo}
                if motivo
                else {"decision": decision}
            )
    except Exception as e:  # un hook roto nunca deja a Nova sin trabajar
        fila["error_hook"] = f"{type(e).__name__}: {e}"
    fila["ms"] = round((time.time() - inicio) * 1000)
    fila["decision"] = salida["decision"]
    apuntar(fila)
    print(json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    main()

