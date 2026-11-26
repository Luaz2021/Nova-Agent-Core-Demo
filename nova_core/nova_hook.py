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
     force_ask (Antigravity se lo pregunta al usuario siempre):
       - la nube escribiendo mas de MAX_LINEAS de codigo (el codigo nuevo lo pica Qwen con nova_tarea.py)
       - comandos destructivos (borrados recursivos, git push --force, git reset --hard, DROP TABLE, formatear...)
       - FRENO DE GASTO: la conversacion pasa de cada TOPE_TOKENS (1M, 2M, 3M...) -> pregunta una vez por tope
       - mas de MAX_SEGUIDAS herramientas encadenadas sin que el usuario escriba -> pregunta una vez cada bloque
Siempre: si algo falla dentro del hook, responde "allow" (un hook roto no puede dejar a Nova sin trabajar) y lo apunta.

Formato (docs de Antigravity): entra por stdin un JSON con toolCall.name, toolCall.args y transcriptPath; sale por
stdout {"decision": "allow" | "deny" | "force_ask", "reason": "..."}.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path


def _w(x) -> str:
    """v3.3: forma canonica de una ruta para COMPARAR en Windows, macOS y Linux (barras \\ y minusculas).
    Las constantes y las rutas que llegan pasan por aqui; asi "\\nova_core\\" encaja tambien en /Users/ana/..."""
    s = str(x or "").strip().strip('"').strip("'")
    if s.startswith("~"):
        s = str(Path.home()) + s[1:]
    return s.replace("/", "\\").lower()

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

# 17/11 (Claude, decision del usuario): sus herramientas (nova_core, biblioteca_web, clones_web, scripts, herramientas) YA
# NO son intocables: en modo ENCARGO/TOTAL las mejora ella con copia automatica (respaldos_nova). Siguen intocables:
# las copias de seguridad, su Python y el ZONA BLINDADA (abajo).
PROTEGIDAS = (
    "respaldos_claude",
    "respaldos_nova",
    "nova_env",
)
# ZONA BLINDADA: lo que decide que puede hacer Nova. Si pudiera editarlo, el freno no existiria. NUNCA, en ningun modo.
_NC = _w(Path.home() / ".gemini" / "nova_core")
ZONA_BLINDADA = (
    _NC + "\\nova_hook.py",
    _NC + "\\nova_hook_turno.py",
    _NC + "\\nova_hooks_config.json",
    _NC + "\\hook_tool.bat",
    _NC + "\\hook_turno.bat",
    _NC + "\\nova_autonomia.py",  # 22/11: freno de autonomia
    _NC + "\\nova_verificacion.py",  # 23/11: freno de verificacion (no dar la razon sin comprobar)
    _NC + "\\.",  # estados de los hooks (.nova_modo.json, .autoriza_codigo.json, .nova_hooks_estado.json...)
    _w(Path.home() / ".gemini" / "config") + "\\",  # hooks.json, GEMINI.md, skills
    _w(Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_doctor.ps1"),  # escribe hooks.json
    _w(Path.home() / ".gemini" / "antigravity" / "scripts" / "session_guard.ps1"),
    # 17/11: el sync ("solo Subir escribe en Drive", blindado), el Doctor multiplataforma y el actualizador.
    # Si Nova pudiera editarlos, podria saltarse el blindaje.
    _w(Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_sync.py"),
    _w(Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_sync_pedir.py"),
    _w(Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_doctor.py"),
    _w(Path.home() / ".gemini" / "antigravity" / "scripts" / "actualizar_nova.py"),
)
# Sus herramientas: en ENCARGO/TOTAL las puede crear y mejorar (copia antes en respaldos_nova\<fecha>\)
ZONAS_HERRAMIENTAS = (
    Path.home() / ".gemini" / "antigravity" / "herramientas",
    Path.home() / ".gemini" / "antigravity" / "scripts",
    Path.home() / ".gemini" / "antigravity" / "almacen",
    Path.home() / ".gemini" / "nova_core",
    Path.home() / ".gemini" / "antigravity" / "clonador",
)
RESPALDOS_NOVA = Path.home() / ".gemini" / "respaldos_nova"
MODO_NOVA = Path(__file__).resolve().parent / ".nova_modo.json"  # lo escribe nova_hook_turno.py


def protegida_para(ruta: str, modo: str) -> bool:
    """protegida() con la regla del 17/11: sus HERRAMIENTAS no son 'prohibidas' aunque tengan la marca
    .nova_protegido (la marca sigue frenando al linter): en CHARLA se pregunta y en ENCARGO/TOTAL las mejora con copia
    (lo decide main()). Copias, su Python, config y las marcas que el usuario ponga en SUS proyectos se respetan siempre."""
    if not protegida(ruta):
        return False
    p = Path(ruta)
    r = _w(p)
    if any(parte.lower() in PROTEGIDAS for parte in p.parts) or r.startswith(PROTEGIDAS_RUTAS):
        return True
    return not any(r.startswith(_w(z) + "\\") for z in ZONAS_HERRAMIENTAS)


def es_freno(ruta: str) -> bool:
    r = _w(ruta)
    return any(r == f.rstrip("\\") or r.startswith(f) for f in ZONA_BLINDADA)


# 22/11 (Claude, el usuario: "si yo le doy permiso explicito, que pueda editar, incluida la zona protegida"). El permiso lo
# apunta nova_hook_turno.py SOLO desde el mensaje real del usuario (lastUserInput: una web o un adjunto no lo
# escriben) en .autoriza_codigo.json, clave "protegido:<conv>", y dura hasta su siguiente mensaje (tope 30 min).
# Con permiso: la zona protegida se edita sin clic y con copia en respaldos_nova\<fecha>\protegido\. El NUCLEO (los
# hooks, hooks.json y GEMINI.md) pregunta con un clic. NUNCA, ni con permiso: los estados de los hooks (ahi vive el
# permiso: si Nova los tocara se daria permiso sola), claves y cofre, las copias de seguridad y su Python.
PERMISO_MAX_S = 30 * 60
_CFG = _w(Path.home() / ".gemini" / "config")
NUCLEO = (
    _NC + "\\nova_hook.py",
    _NC + "\\nova_hook_turno.py",
    _NC + "\\nova_hooks_config.json",
    _NC + "\\hook_tool.bat",
    _NC + "\\hook_turno.bat",
    _NC + "\\nova_autonomia.py",
    _NC + "\\nova_verificacion.py",
    _CFG + "\\hooks.json",
    _CFG + "\\gemini.md",
)


def _norm(ruta: str) -> str:
    return _w(ruta)


def es_nucleo(ruta: str) -> bool:
    return _norm(ruta) in NUCLEO


def intocable(ruta: str) -> bool:
    """Lo que ni con permiso del usuario: estados de los hooks, claves, copias de seguridad y el Python de Nova."""
    r = _norm(ruta)
    return (r.startswith(_NC + "\\.") or bool(RE_SECRETO.search(r)) or ".clave" in r
            or any(x in PROTEGIDAS for x in r.split("\\")))  # v3.3: r ya es canonica (\\) en los 3 sistemas


def permiso_usuario(conv: str) -> bool:
    if not conv:
        return False
    t = leer_json(AUTORIZA_CODIGO, {}).get("protegido:" + conv)
    try:
        return 0 <= time.time() - float(t) <= PERMISO_MAX_S
    except (TypeError, ValueError):
        return False


def respaldar_protegido(rutas: list[str]) -> list[str]:
    """Copia (una vez al dia por archivo) lo protegido que Nova cambia con permiso del usuario."""
    import shutil
    hechos = []
    gem = Path.home() / ".gemini"
    for ruta in rutas:
        try:
            p = Path(ruta.strip().strip('"').strip("'"))
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(gem)
            except ValueError:
                rel = Path(p.name)
            destino = RESPALDOS_NOVA / time.strftime("%Y-%m-%d") / "protegido" / rel
            if destino.exists():
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, destino)
            hechos.append(str(destino))
        except (OSError, ValueError):
            pass
    return hechos


MSG_NUCLEO = ("PERMISO DEL USUARIO + CLIC: {n} es el nucleo de tus reglas (hooks o GEMINI.md). El usuario te ha dado "
              "permiso, pero este archivo lo confirma el con un clic. Copia automatica en respaldos_nova.")
MSG_PIDE_PERMISO = (" Si de verdad hace falta, pidele al usuario permiso EXPLICITO (que escriba 'te doy permiso' o "
                    "'te autorizo') y vuelve a intentarlo en ese turno.")


def modo_de(conv: str) -> dict:
    """{'modo': charla|encargo|total, 'zonas': [...], 'total_hasta': ts} de esta conversacion."""
    try:
        e = json.loads(MODO_NOVA.read_text(encoding="utf-8")).get(conv) or {}
    except (OSError, ValueError):
        e = {}
    e.setdefault("modo", "charla")
    if e["modo"] == "total" and time.time() > float(e.get("total_hasta") or 0):
        e["modo"] = "encargo"
    return e


def respaldar(rutas: list[str]) -> list[str]:
    """Copia (una vez al dia por archivo) los archivos de sus HERRAMIENTAS antes de que Nova los cambie."""
    import shutil
    hechos = []
    hoy = RESPALDOS_NOVA / time.strftime("%Y-%m-%d")
    for ruta in rutas:
        try:
            p = Path(ruta.strip().strip('"').strip("'"))
            if not p.is_file():
                continue
            base = next((z for z in ZONAS_HERRAMIENTAS if _w(p).startswith(_w(z) + "\\")), None)
            if base is None:
                continue
            destino = hoy / base.name / p.relative_to(base)
            if destino.exists():
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, destino)
            hechos.append(str(destino))
        except (OSError, ValueError):
            pass
    return hechos
# 11/11 (Claude): el codigo oficial de Nova. Nova no lo edita con sus herramientas de archivos (en el PC lo parcheaba
# "para arreglar" y dejaba restos). Si algo falla -> nova_doctor.ps1. Por terminal se sigue pudiendo EJECUTAR.
_RAIZ_NOVA = _w(Path.home() / ".gemini" / "antigravity")
# v3.2: os.sep (antes "\\" fijo: en macOS/Linux ninguna proteccion de rutas funcionaba)
CODIGO_OFICIAL = (_RAIZ_NOVA + "\\" + "scripts" + "\\", _RAIZ_NOVA + "\\" + "herramientas" + "\\")
# Copiar a mano desde Drive (en el PC Nova copio carpetas enteras saltandose el sync y dejo duplicados)
RE_COPIA_DE_DRIVE = re.compile(
    r"(?i)\b(Copy-Item|copy|xcopy|robocopy|cp|Move-Item|move|mv|Expand-Archive)\b.*"
    r"(Mi unidad|My Drive|Google Drive|\bG:[\\/])"
)
# pip/uv instalando en el Python de Nova o en el de Windows (las librerias de Nova las pone el Doctor)
RE_PIP_INSTALA = re.compile(r"(?i)\b(pip3?|uv\s+pip)\s+install\b|-m\s+pip\s+install\b")
# 26/11 (Claude, prueba A/B del orquestador): Nova creo el venv del proyecto en %LOCALAPPDATA%\venvs\<proyecto> (lo
# correcto: un .venv dentro de Drive tarda minutos) y este patron solo aceptaba \venv\ o \.venv\ -> deny -> la devolvio
# a Drive. Ahora vale tambien \venvs\, \env\ y una variable $venv... ; y pip sobre el Python de Nova se frena SIEMPRE,
# aunque en el comando salga un .venv.
RE_VENV_PROYECTO = re.compile(
    r"(?i)[\\/]\.?venvs?[\\/]|[\\/]\.?env[\\/]|\$venv\w*|--target\b|\bproyectos[\\/]|\bscratch[\\/]"
)
RE_PIP_EN_NOVA = re.compile(
    r"(?i)(nova_python|nova_env)[^;|&\n]*?(-m\s+pip\s+install|\bpip3?\s+install|\buv\s+pip\s+install)"
)
# 26/11: leer la salida larga de SUS propios comandos (Antigravity la guarda en brain\<conv>\.system_generated\steps\N\;
# la CLI agy ademas en ...\tasks\task-N.log para los comandos en segundo plano)
RE_SALIDA_PROPIA = re.compile(
    r"(?i)\\brain\\([\w\-]{8,})\\\.system_generated\\(steps\\\d+|tasks)\\[^\\]+$")
# 26/11 noche (D2e): el hook de turno (Ley 3) le pide apuntar la leccion -> anadir al inbox SIEMPRE vale (solo anadir)
RE_ANADE_LECCION = re.compile(r"(?i)^\s*add-content\b[^;|&`]*inbox_lecciones\.md\b[^;|&`]*$")
# 26/11 noche (D3, prueba desde Nova): en CHARLA, lanzar el director pedia clic ("fuera de su zona"); es lo que el carril
# 'proyecto' le manda hacer. Solo ESTE comando (con NOVA_PYTHON y una sola orden, sin ; | &): lanzar/resumen/estado/modelos.
RE_DIRECTOR_NOVA = re.compile(
    r"(?i)^\s*&\s*(\$env:NOVA_PYTHON|\"[^\"]*nova_env\\scripts\\python\.exe\")\s+\"[^\"]*\\herramientas\\director\\"
    r"nova_director\.py\"\s+(lanzar|resumen|estado|modelos)\b[^;|&`]*$"
    # v3.3 macOS/Linux: "<NOVA_HOME>/nova_env/bin/python" "<...>/herramientas/director/nova_director.py" lanzar ...
    r"|^\s*\"?[^\"\s]*nova_env/bin/python3?\"?\s+\"?[^\"\s]*/herramientas/director/"
    r"nova_director\.py\"?\s+(lanzar|resumen|estado|modelos)\b[^;|&`]*$")
# 26/11 noche (D2a): en las llamadas del DIRECTOR, borrar dentro del proyecto o de TEMP no pregunta; esto SIGUE preguntando
RE_BORRAR_PELIGROSO = re.compile(r"(?i)\|\s*(iex|invoke-expression|sh|bash|cmd|powershell)\b|invoke-expression|\biex\b|"
                                 r"git\s+(rm|clean|reset|push|checkout)|\.\.[\\/]|format-volume|\bformat\b\s+[a-z]:")


def proyecto_director(datos: dict) -> Path | None:
    """26/11 noche (D2): la llamada viene del NOVA DIRECTOR (CLI agy sin ventana: nadie puede darle al clic) si el
    transcript es de la CLI (.gemini\\antigravity-cli\\brain) y el workspace tiene un director EN MARCHA
    (.director\\en_marcha.json de menos de 6 h). Devuelve la carpeta del proyecto o None."""
    tp = str(datos.get("transcriptPath") or "").lower()
    if tp and "antigravity-cli" not in tp:
        return None
    for w in datos.get("workspacePaths") or []:
        p = Path(re.sub(r"^file:/+", "", str(w)))
        marca = p / ".director" / "en_marcha.json"
        try:
            if marca.is_file() and time.time() - marca.stat().st_mtime < 6 * 3600:
                return p
        except OSError:
            continue
    return None


def borrado_en_proyecto(args: dict, datos: dict, proy: Path) -> bool:
    """D2a: un borrado del director es seguro si TODO lo que nombra esta dentro del proyecto o de TEMP, no es la carpeta
    del proyecto entera ni .director, y no lleva nada de RE_BORRAR_PELIGROSO. Sin rutas: solo si trabaja en el proyecto."""
    comando = str(args.get("CommandLine") or args.get("command") or "")
    if comando and RE_BORRAR_PELIGROSO.search(comando):
        return False
    raices = [_norm(str(proy))] + [_norm(t) for t in (os.environ.get("TEMP"), os.environ.get("TMP")) if t]
    rutas = ([ruta_de(args)] if ruta_de(args) else []) + [
        next(g for g in m.groups() if g) for m in RE_RUTA_EN_CMD.finditer(comando)]
    rutas = [r for r in rutas if r]
    for r in rutas:
        n = _norm(r)
        if n == _norm(str(proy)) or "\\.director" in n or not any(n == z or n.startswith(z + "\\") for z in raices):
            return False
    if rutas:
        return True
    cwd = _norm(str(args.get("Cwd") or args.get("cwd") or datos.get("cwd") or ""))
    en_proy = bool(cwd) and (cwd == raices[0] or cwd.startswith(raices[0] + "\\"))
    return en_proy or _norm(str(proy)).lower() in comando.replace("/", "\\").lower()


def permiso_director(proy: Path, nombre: str, args: dict, motivo: str) -> str:
    """D2c: el "dale seguir" del usuario POR PROYECTO. <proyecto>\\.director\\permisos.json =
    {"permitir": [{"patron": "<regex sobre el comando o la ruta>", "motivo": "por que lo permitio"}]} (lo escribe Nova
    cuando el usuario dice que si). Nunca salta la zona blindada, el nucleo, las claves ni el cofre."""
    if re.search(r"(?i)blindad|nucleo|n[uú]cleo|clave|cofre|vault|secreto|pago", motivo):
        return ""
    try:
        reglas = json.loads((proy / ".director" / "permisos.json").read_text(encoding="utf-8")).get("permitir") or []
    except (OSError, ValueError):
        return ""
    texto = str(args.get("CommandLine") or args.get("command") or "") + " " + ruta_de(args)
    for r in reglas:
        try:
            if r.get("patron") and re.search(r["patron"], texto, re.IGNORECASE):
                return r["patron"]
        except re.error:
            continue
    return ""
_GEM = _w(Path.home() / ".gemini")
PROTEGIDAS_RUTAS = (
    _GEM + "\\" + "config",
)  # reglas y skills de Nova: solo las cambian Claude o el usuario
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
# (vault\secrets.json, lo rellena el usuario) y el codigo las lee en local (os.environ / el cofre). Formas conocidas:
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
    "(<NOVA_HOME>/config/secrets.env), que rellena el usuario con nova_claves.py. En el codigo leela en local: "
    'os.environ.get("NOMBRE_API_KEY") o el cofre. Si falta una clave, '
    "pidele al usuario que la anada (nova_claves.py); no la pegues tu."
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
# (el espacio tiene que estar DENTRO de una carpeta, "...\Ana Maria\...", no entre el programa y sus argumentos)
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


def ramas_ajenas(repo: Path) -> list[str]:
    """17/11 (Claude, regla del usuario: "Nova puede subir y modificar main de mi GitHub; solo tiene prohibido hacer
    cambios directos cuando hay ramas de otras personas"). Ramas del remoto cuyo ultimo cambio es de OTRA persona
    (autor distinto de tu user.email/user.name de git y que no son ramas nova/...). Lista vacia = repo tuyo."""
    import subprocess
    try:
        def git(*a):
            return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, timeout=4,
                                  encoding="utf-8", errors="replace").stdout
        yo = {git("config", "user.email").strip().lower(), git("config", "user.name").strip().lower()} - {""}
        ajenas = []
        for linea in git("for-each-ref", "--format=%(refname:short)\t%(authoremail)\t%(authorname)",
                         "refs/remotes").splitlines():
            partes = linea.split("\t")
            if len(partes) < 3 or partes[0].endswith("/HEAD"):
                continue
            rama, correo, nombre = partes[0], partes[1].strip("<>").lower(), partes[2].strip().lower()
            if rama.split("/", 1)[-1].startswith("nova/") or rama.split("/", 1)[-1] in RAMAS_PRINCIPALES:
                continue
            if yo and correo not in yo and nombre not in yo:
                ajenas.append(rama)
        return ajenas
    except Exception:
        return []  # sin git o sin remoto: no hay ramas de otros que proteger


RE_GIT_SUBE = re.compile(r"(?i)\bgit\b[^;|&]*\b(commit|push)\b")
RE_ENV_ARCHIVO = re.compile(r"(?i)(^|[\\/])\.env(\.(?!example\b|sample\b|template\b)[\w.-]+)?$|(^|[\\/])[\w.-]+\.env$|"
                            r"(^|[\\/])(secrets?|credentials)[\w.-]*\.json$|\.(pem|p12|pfx)$|id_rsa|id_ed25519")


def secretos_en_git(comando: str, args: dict) -> str:
    """Que se va a subir con este git commit/push y si lleva claves o archivos de secretos. '' si esta limpio."""
    import subprocess
    m = RE_GIT_C.search(comando)
    carpeta = (m and next(g for g in m.groups()[1:] if g)) or str(args.get("Cwd") or args.get("cwd") or "")
    if not carpeta:
        return ""

    def git(*a):
        try:
            return subprocess.run(["git", "-C", carpeta, *a], capture_output=True, text=True, timeout=6,
                                  encoding="utf-8", errors="replace").stdout
        except Exception:
            return ""
    if re.search(r"(?i)\bpush\b", comando):
        rango = "@{u}..HEAD" if git("rev-parse", "--abbrev-ref", "@{u}").strip() else "HEAD"
        archivos = git("diff", "--name-only", rango) if rango != "HEAD" else git("ls-files")
        cambios = git("diff", rango) if rango != "HEAD" else ""
    else:
        todos = re.search(r"(?i)\bcommit\b[^;|&]*\s-[a-z]*a", comando)  # git commit -a / -am
        archivos = git("diff", "--name-only") + git("diff", "--cached", "--name-only") if todos else \
            git("diff", "--cached", "--name-only")
        cambios = (git("diff") if todos else "") + git("diff", "--cached")
    for f in archivos.splitlines():
        if RE_ENV_ARCHIVO.search(f.strip()):
            return f"el archivo {f.strip()} (guarda claves)"
    nuevas = "\n".join(l[1:] for l in cambios.splitlines() if l.startswith("+") and not l.startswith("+++"))
    if RE_CLAVE_API.search(nuevas):
        return "una clave de API dentro de los cambios"
    return ""


RE_HERRAMIENTA_SQL = re.compile(r"(?i)sql|query|postgres|supabase|database|mysql|sqlite")
RE_SQL_PELIGRO = re.compile(r"(?is)^\s*(delete\s+from\s+\S+|update\s+\S+\s+set\b.*)$")


def sql_sin_where(texto: str) -> str:
    """Sentencia DELETE FROM / UPDATE ... SET sin WHERE (afecta a toda la tabla). '' si no hay."""
    if not re.search(r"(?i)\b(delete\s+from|update\s+\S+\s+set)\b", texto):
        return ""
    for frase in re.split(r";|\\n|\n|\"|'", texto):
        m = re.search(r"(?is)\b(delete\s+from\s+\S+.*|update\s+\S+\s+set\b.*)", frase)
        if m and not re.search(r"(?i)\bwhere\b", m.group(1)):
            return " ".join(m.group(1).split())
    return ""


RE_GIT_CAMBIA = re.compile(r"(?i)\bgit\b[^;|&]*\b(commit|push|merge|rebase|cherry-pick|am)\b")
RE_GIT_C = re.compile(r'(?i)\bgit\s+-C\s+("([^"]+)"|\'([^\']+)\'|(\S+))')


RE_DOC_EN_SCRATCH = re.compile(
    r"(?i)[\\/]antigravity[\\/]scratch[\\/][^\"'|;&<>\n]*\.(pdf|docx|doc|xlsx|pptx)\b"
)
MAX_LINEAS = 150  # linea dulce 08/11: hasta 150 lineas las escribe Nova; mas, Qwen por secciones (nova_secciones.py)
MAX_KB = 200
EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_KB_IMAGEN = 3072  # 26/11: las imagenes hasta 3 MB se pueden ver (no se cuentan como texto)
TOPE_TOKENS = 300_000  # 09/11: tokens REALES (cache al 10 %); 20/11: ahora coste PONDERADO (nova_cupo.py)
TRAMO_ORQ_PCT = 3  # 20/11: con orquestador, aviso de voz cada 3 % del cupo semanal de Argon/Neon (no frena)


# 20/11 (Claude): herramientas del MCP REA que EJECUTAN, depuran, instrumentan o modifican el programa o el movil.
# Sacadas del catalogo real de rea-agents 6.10.1 (263 herramientas). Las de solo lectura pasan libres.
REA_EJECUTA = {
    "capture_native_ui_scenario", "execute_rizin_command", "start_gdb_session", "gdb_console",
    "start_rizin_debug_session", "rizin_debug_command", "start_frida_session", "load_frida_script",
    "resume_frida_session", "instrument_with_frida", "push_adb_file", "install_adb_package", "uninstall_adb_package",
    "start_adb_app", "start_adb_activity", "stop_adb_app", "capture_browser_scenario", "observe_web_execution",
    "capture_electron_scenario", "start_build_computer", "start_build_capture", "capture_process_scenario",
    "record_build_consent",
}


def herramienta_rea_ejecuta(nombre: str) -> str | None:
    n = (nombre or "").lower()
    if "rea" not in n:
        return None
    return next((h for h in REA_EJECUTA if n == h or n.endswith("_" + h) or n.endswith("__" + h)), None)


def consultas_asesor(transcript: str) -> int:
    """20/11: cuantas veces se ha invocado ya al sub-agente asesor en esta conversacion."""
    n = 0
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if '"invoke_subagent"' in linea and "asesor" in linea.lower() and '"tool_calls"' in linea:
                    n += 1
    except OSError:
        pass
    return n


def texto_cupo(des: dict) -> str:
    """', ~2.1 % del cupo semanal de Argon/Neon + 0.8 % de Gemini' (vacio si no hay datos de cupo)."""
    try:
        import nova_cupo

        return f", {nova_cupo.linea_cupo(des)} del cupo semanal" if des.get("pct") else ""
    except Exception:
        return ""
TOPE_CONTEXTO = 100_000  # regla del usuario: contexto de la ventana > 100k -> /compact
MAX_SEGUIDAS = 25
MAX_SEGUIDAS_VOZ = 150  # 17/11: encargos por voz ([voz]): Nova trabaja de corrido; solo frena un bucle sin fin
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


def carpeta_sync_nube(r: str) -> bool:
    """v3.2: la carpeta de Nova Sync en Google Drive SOLO la toca nova_sync.py (blindaje: solo Subir escribe en Drive)."""
    try:
        cfg = json.loads((Path.home() / ".gemini" / "config" / "nova_sync.json").read_text(encoding="utf-8"))
        nube = _w(cfg.get("carpeta", ""))
    except (OSError, ValueError):
        return False
    return bool(nube) and _w(Path(r)).startswith(nube)
# 24/11 (Claude, el usuario: "siempre reemplaza todo el archivo"): VIGILANTE DE REESCRITURAS. Solo MIDE, nunca frena.
# Si Nova sobrescribe entero un archivo que ya existia, compara viejo/nuevo y apunta cuanto cambio de verdad.
# "innecesaria" = archivo de REESCRITURA_MIN_LINEAS+ lineas y menos de REESCRITURA_MAX_PCT % cambiado (debio usar
# edit_file). Lo resume nova_revisor.py (seccion 8). Si un dia se convierte en freno, calibrar con estos datos.
REESCRITURA_MIN_LINEAS = 40
REESCRITURA_MAX_PCT = 30.0
REESCRITURA_MAX_BYTES = 1_500_000  # archivos mas grandes: solo se apunta el tamano (el diff seria lento)
RE_SOBRESCRIBE = re.compile(r"^(write_file|write_to_file|create_file|save_file)$", re.IGNORECASE)
# 25/11 (el usuario: "activalo"): el vigilante pasa a FRENO en archivos de codigo. Frena UNA vez por archivo y conversacion
# (la segunda pasa: nunca un bucle). No frena si el usuario pide reescribirlo entero en su mensaje.
EXT_CODIGO = {".py", ".java", ".kt", ".kts", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".html", ".css", ".scss", ".xml",
              ".cs", ".php", ".dart", ".sql", ".vue", ".gradle", ".ps1", ".sh", ".go", ".rs", ".swift", ".c", ".cpp", ".h"}
RE_PIDE_REESCRIBIR = re.compile(
    r"(?i)\b(reescr[ií]b\w*|rehaz\w*|desde\s+cero|sobrescr[ií]b\w*|entero|completo|de\s+nuevo\s+todo)\b")
MSG_REESCRITURA = (
    "FRENO DE REESCRITURA (lo vigila un hook): vas a sobrescribir ENTERO {archivo} ({antes} lineas) para cambiar solo "
    "{cambiadas} ({pct} %). Usa edit_file SOLO en los trozos que cambian (Target = texto exacto actual, Replacement = "
    "texto nuevo); asi no se pierde codigo y gastas menos. Si de verdad hay que rehacerlo entero, dilo y vuelve a "
    "intentarlo (este freno salta una sola vez por archivo).")


def freno_reescritura(conv: str, fila: dict, pedido: str) -> str:
    r = fila.get("reescritura") or {}
    ruta = str(fila.get("ruta") or "")
    if not r.get("innecesaria") or Path(ruta).suffix.lower() not in EXT_CODIGO or RE_PIDE_REESCRIBIR.search(pedido):
        return ""
    estado = leer_json(ESTADO, {})
    clave = "reescr:" + conv
    ya = estado.get(clave, [])
    if ruta.lower() in ya:
        fila["reescritura_soltada"] = True
        return ""
    estado[clave] = (ya + [ruta.lower()])[-50:]
    try:
        ESTADO.write_text(json.dumps(estado), encoding="utf-8")
    except OSError:
        pass
    fila["reescritura_frenada"] = True
    return MSG_REESCRITURA.format(archivo=Path(ruta).name, antes=r.get("antes"), cambiadas=r.get("cambiadas"),
                                  pct=r.get("pct"))


# 25/11 (Claude, fase 3): REGLAS DE CAPAS (estilo ArchUnit, pocas y claras). En Java MVC: la vista no importa java.sql
# y el controller/dao/repository no importa javax.swing. El mensaje dice como arreglarlo. Una vez por archivo.
REGLAS_CAPAS = (
    (re.compile(r"(?i)[\\/]views?[\\/][^\\/]+\.java$"), re.compile(r"(?m)^\s*import\s+java\.sql\b"),
     "la VISTA no habla con la base de datos: el SQL va en el controller o el DAO, y la vista llama a sus metodos."),
    (re.compile(r"(?i)[\\/](controllers?|dao|repository|repositorio)[\\/][^\\/]+\.java$"),
     re.compile(r"(?m)^\s*import\s+javax\.swing\b"),
     "el CONTROLLER/DAO no toca la interfaz: devuelve datos (List<Object[]>, boolean...) y la vista los pinta y "
     "muestra los mensajes."),
)


def freno_capas(conv: str, ruta: str, args: dict) -> str:
    nuevo = "\n".join(str(args.get(k)) for k in ("Content", "CodeContent", "content", "Replacement", "ReplacementContent")
                      if isinstance(args.get(k), str))
    if not nuevo or not ruta:
        return ""
    for re_ruta, re_import, regla in REGLAS_CAPAS:
        if re_ruta.search(ruta) and re_import.search(nuevo):
            estado = leer_json(ESTADO, {})
            clave = "capas:" + conv
            if ruta.lower() in estado.get(clave, []):
                return ""
            estado[clave] = (estado.get(clave, []) + [ruta.lower()])[-50:]
            try:
                ESTADO.write_text(json.dumps(estado), encoding="utf-8")
            except OSError:
                pass
            return (f"REGLA DE CAPAS (lo vigila un hook): en {Path(ruta).name} {regla} Mueve ese codigo a su capa y "
                    "vuelve a intentarlo (si el proyecto de verdad lo hace asi a proposito, dilo y repite).")
    return ""


def medir_reescritura(nombre: str, args: dict) -> dict | None:
    if not RE_SOBRESCRIBE.match(nombre or "") or args.get("Append") is True:
        return None
    ruta = ruta_de(args)
    nuevo = next((args[k] for k in ("Content", "CodeContent", "content", "code") if isinstance(args.get(k), str)), None)
    if not ruta or nuevo is None:
        return None
    p = Path(ruta)
    try:
        if not p.is_file():
            return None  # archivo nuevo: escribirlo entero es lo normal
        tam = p.stat().st_size
        if tam > REESCRITURA_MAX_BYTES:
            return {"antes_bytes": tam, "grande": True}
        viejo = p.read_bytes().decode("utf-8", errors="replace").lstrip("﻿")
    except OSError:
        return None
    import difflib

    a, b = viejo.splitlines(), nuevo.lstrip("﻿").splitlines()
    cambiadas = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            cambiadas += max(i2 - i1, j2 - j1)
    pct = round(100.0 * cambiadas / max(len(a), len(b), 1), 1)
    return {
        "antes": len(a),
        "despues": len(b),
        "cambiadas": cambiadas,
        "pct": pct,
        "innecesaria": len(a) >= REESCRITURA_MIN_LINEAS and pct < REESCRITURA_MAX_PCT,
    }


def protegida(ruta: str) -> bool:
    if not ruta:
        return False
    p = Path(ruta)
    if carpeta_sync_nube(ruta):
        return True
    if "nova_voz_clon" in _w(p) or "voz_clon" in [x.lower() for x in p.parts]:
        return True  # v3.2: pack de voz (voces con licencia propia y su aceptacion): Nova no lo toca a mano
    if _w(p).startswith(_GEM) and any(parte.lower() in PROTEGIDAS for parte in p.parts):
        return True
    if _w(p).startswith(PROTEGIDAS_RUTAS):
        return True
    return any((c / MARCA_PROTEGIDO).exists() for c in p.parents)


PRECIO_CACHE = 0.10  # 09/11: Gemini cobra la entrada leida de cache con un 90 % de descuento (cache implicita)


def gasto(transcript: str) -> tuple[int, int, int, dict]:
    """(coste PONDERADO de la conversacion, herramientas seguidas desde el ultimo mensaje del usuario, tamano del
    contexto en la ultima llamada, desglose {nuevos, cache, salida, bruto, real, ponderado, pct, orquestador...}).
    20/11 (Claude, el usuario: "el orquestador se come el cupo semanal de un tiron"): se mide con nova_cupo.py, que pondera
    por modelo (Flash/Hydrogen x1, Neon/Argon x4, Opus x10) y calcula el % del cupo semanal. Antes todos contaban igual."""
    try:
        import nova_cupo

        r = nova_cupo.medir(transcript)
        return r["ponderado"], r["seguidas"], r["contexto"], r
    except Exception:  # si nova_cupo falla, el calculo de siempre (sin ponderar)
        pass
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
    "scratch": "herramientas o scripts nuevos (pasan por inspeccion del usuario y Claude)",
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
)  # lo escribe nova_hook_turno.py con cada mensaje del usuario
NOVA_TAREA = str(Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_tarea.py")
ESTUDIO = str(Path.home() / ".gemini" / "antigravity" / "herramientas" / "estudio_web" / "estudio.py")  # 15/11: webs


def autoriza_web(conv: str) -> bool:
    return bool(conv) and leer_json(AUTORIZA_CODIGO, {}).get(conv) is True


def regla_contenido(nombre: str, args: dict, conv: str = "", modo: str = "charla") -> tuple[str, str]:
    """Reglas sobre lo que hace la herramienta (archivos, comandos). modo: charla | encargo | total."""
    ruta = ruta_de(args)
    p = Path(ruta) if ruta else None
    comando = str(args.get("CommandLine") or args.get("command") or "")
    # 17/11 ZONA BLINDADA: los hooks, config\ y el Doctor no los cambia Nova por su cuenta (ni escribir ni borrar).
    # 22/11: con permiso EXPLICITO del usuario en su mensaje si (ver permiso_usuario); el nucleo con un clic.
    perm = permiso_usuario(conv)
    via_permiso = False
    if (RE_ESCRIBIR.search(nombre) or RE_HERRAMIENTA_BORRA.search(nombre)) and ruta and es_freno(ruta):
        if perm and not intocable(ruta):
            if es_nucleo(ruta):
                return "force_ask", MSG_NUCLEO.format(n=Path(ruta).name)
            via_permiso = True
        else:
            return "deny", (f"{Path(ruta).name} es parte de tu ZONA BLINDADA (hooks, config o Doctor): no lo cambias tu "
                            "por tu cuenta." + ("" if intocable(ruta) else MSG_PIDE_PERMISO))
    if comando and (RE_CMD_ESCRIBE.search(comando) or RE_CMD_NUNCA_SOLO.search(comando)):
        for m in RE_RUTA_EN_CMD.finditer(comando):
            r_cmd = next(g for g in m.groups() if g)
            if es_freno(r_cmd):
                if perm and not intocable(r_cmd):
                    if es_nucleo(r_cmd):
                        return "force_ask", MSG_NUCLEO.format(n=Path(r_cmd).name)
                    via_permiso = True
                    continue
                return "deny", ("Ese comando toca tu ZONA BLINDADA (hooks, config o Doctor): no lo cambias tu por tu "
                                "cuenta." + ("" if intocable(r_cmd) else MSG_PIDE_PERMISO))
    # 09/11 (Claude): el permiso de pago de Brave solo lo da el usuario. Nova no lee la clave ni llama a /pase_pago.
    if re.search(
        r"(?i)pase_pago|GRANT_PAYMENT_PASS|_permitirPago|\.clave\b|nova_core[\\/]+\.[\w*?]|nova_core[\\/]+\*",
        ruta + " " + comando + " " + json.dumps(args, ensure_ascii=False),
    ):
        return "deny", (
            "El permiso de pago de Brave solo lo da el usuario escribiendo 'autorizo el pago'. Nova no toca esa "
            "clave ni llama a /pase_pago."
        )
    if lleva_clave(nombre, args, comando):
        return "deny", MSG_CLAVE
    # 22/11 (Claude, el usuario: "le deje una ventana de Brave para que trabaje en segundo plano y yo miro YouTube"): sin
    # args.tabId la extension actua en la pestana ACTIVA de la ultima ventana que toco el usuario (su YouTube).
    if comando and RE_PUENTE_EXECUTE.search(comando):
        accion = RE_ACCION_PUENTE.search(comando)
        if accion and accion.group(1).lower() in ACCIONES_EN_PAGINA and not re.search(r"(?i)tabId", comando):
            return "deny", (f"PUENTE DE BRAVE SIN tabId: '{accion.group(1)}' actuaria en la pestana que el usuario este "
                            "mirando (p. ej. su YouTube), no en la tuya. Haz LIST_TABS una vez, apunta el id de tu "
                            "pestana y manda SIEMPRE \"args\":{\"tabId\":<id>, ...} en cada accion.")
    # 17/11 (el usuario: "¿choca con GitGuardian? que no pueda hacer push con api keys o contrasenas sueltas"): antes de
    # cada git commit / git push se mira LO QUE VA A SALIR. Clave o .env dentro -> bloqueado, en TODOS los modos.
    if comando and RE_GIT_SUBE.search(comando):
        fuga = secretos_en_git(comando, args)
        if fuga:
            return "deny", (f"GIT CON SECRETOS: {fuga}. Eso acabaria publicado en GitHub. Saca la clave del archivo "
                            "(leela con os.environ / el cofre), anade el archivo a .gitignore, quitalo del commit "
                            "(git restore --staged <archivo>) y vuelve a intentarlo.")
    # 17/11 (el usuario: "o hacer de la bd un DELETE/UPDATE sin WHERE"): una orden de base de datos que borra o reescribe
    # la tabla ENTERA se pregunta siempre (como DROP/TRUNCATE).
    texto_sql = comando + " " + (json.dumps(args, ensure_ascii=False) if RE_HERRAMIENTA_SQL.search(nombre) else "")
    sql_mala = sql_sin_where(texto_sql)
    if sql_mala:
        return "force_ask", (f"BASE DE DATOS SIN WHERE: '{sql_mala[:120]}' afectaria a TODAS las filas de la tabla. "
                             "el usuario tiene que confirmarlo (o anade un WHERE).")
    # 09/11 (Claude): en el sandbox de Antigravity el atajo python/py de Windows falla ("El sistema no tiene acceso al
    # archivo") y Nova se pasaba 10 intentos probando node, typst, Edge... Se frena al primero con la ruta buena.
    # 09/11 tarde: Antigravity a veces manda el comando envuelto en comillas ("python x.py") y la regla no lo veia
    cmd_limpio = comando.strip()
    if len(cmd_limpio) > 1 and cmd_limpio[0] == cmd_limpio[-1] == '"':
        cmd_limpio = cmd_limpio[1:-1].strip()
    if cmd_limpio and RE_PYTHON_ATAJO.search(cmd_limpio):
        # 26/11 (prueba full stack del director): el mensaje solo decia NOVA_PYTHON y para el codigo de un PROYECTO eso
        # falla (el Python de Nova no tiene sus librerias: FastAPI, etc.). Ahora explica los dos casos.
        return "deny", (
            "En el sandbox de Antigravity 'python'/'py' a secas NO funciona. Repitelo segun lo que sea: "
            f'HERRAMIENTA de Nova (estudio.py, revisar.py, nova_*.py...) -> & "{PYTHON_NOVA}" "<script>" ... '
            "(es <PYTHON> en GEMINI.md) · codigo de un PROYECTO (sus tests, su app) -> uv run --with-requirements "
            "requirements.txt python ... (en su carpeta; nunca pip en el Python de Nova)."
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
            "No copies archivos de Nova a mano desde otra carpeta o nube: las mejoras llegan con /actualizar-nova. "
            "Si falta algo, ejecuta el Doctor (<PYTHON> \"<NOVA_HOME>/antigravity/scripts/nova_doctor.py\" --reparar) "
            "y cuentale al usuario su ultima linea."
        )
    # v3.2 Nova Sync: los borrados masivos (--forzar) y desconectar los decide el usuario en una terminal, no Nova
    if cmd_limpio and re.search(r"(?i)nova_sync(_pedir)?\.py\b.*(--forzar|\bdesconectar\b)", cmd_limpio):
        return "deny", (
            "Forzar borrados masivos o desconectar Nova Sync lo decide el usuario: dile que lo ejecute el en una "
            "terminal si de verdad lo quiere. Tu usa nova_sync_pedir.py bajar|subir|espejo|estado|configurar."
        )
    # v3.2 Pack de voz: la licencia de las voces (LICENCIA_VOCES.md) la acepta el USUARIO, nunca Nova por el
    consentido = False
    try:  # el usuario escribio "acepto la licencia de las voces" hace menos de 30 min (lo apunta nova_hook_turno.py)
        consentido = time.time() - json.loads((AQUI / ".voces_licencia_usuario.json").read_text(encoding="utf-8"))["fecha"] < 1800
    except (OSError, ValueError, KeyError):
        pass
    if cmd_limpio and (
        re.search(r"(?i)\bACEPTO\b", cmd_limpio) and re.search(r"(?i)voz_clon|instalar\.(ps1|sh)", cmd_limpio)
        or re.search(r"(?i)-{1,2}aceptado\b", cmd_limpio) and re.search(r"(?i)voz_clon", cmd_limpio) and not consentido
        or re.search(r"(?i)licencia_voces_aceptada", cmd_limpio)
    ):
        return "deny", (
            "La licencia de las voces Ayla y Marina la acepta el usuario en persona: ensenale el resumen de LICENCIA_VOCES.md "
            "y pidele que escriba en el chat 'acepto la licencia de las voces'. Entonces podras instalar el pack."
        )
    # G2b (17/11): "& ...\\instalar.ps1" lo bloquea la Execution Policy de Windows -> el comando EXACTO
    if (
        cmd_limpio
        and re.search(r"(?i)voz_clon[\\/]+instalar\.ps1", cmd_limpio)
        and not re.search(r"(?i)-(ExecutionPolicy|ep)\s+Bypass", cmd_limpio)
    ):
        return "deny", (
            "En Windows el instalador de la voz se lanza SIEMPRE asi (si no, Windows lo bloquea): powershell "
            "-ExecutionPolicy Bypass -File \"<NOVA_HOME>\\antigravity\\herramientas\\voz_clon\\instalar.ps1\" -Aceptado "
            "(-Aceptado solo si el usuario escribio 'acepto la licencia de las voces'). Si se lo das al usuario, dale "
            "ese comando exacto, nunca '& instalar.ps1'."
        )
    if (
        cmd_limpio
        and RE_PIP_INSTALA.search(cmd_limpio)
        and (RE_PIP_EN_NOVA.search(cmd_limpio) or not RE_VENV_PROYECTO.search(cmd_limpio))
    ):
        return "deny", (
            "Las librerias de Nova las instala el Doctor en su Python propio (nova_core\\requisitos_nova.txt), "
            "no tu con pip. Ejecuta el Doctor (<PYTHON> \"<NOVA_HOME>/antigravity/scripts/nova_doctor.py\" --reparar); "
            "si falta una libreria nueva, diselo al usuario para que lo reporte con /reportar-fallo. Para un PROYECTO: "
            "si esta en una carpeta sincronizada (Google Drive, OneDrive, iCloud, Dropbox), "
            "uv run --with-requirements requirements.txt <comando> (sin .venv dentro: tarda minutos); si no, "
            "su propio .venv."
        )
    # 09/11 Ley 5 vigilada: nada "en caliente". Editar un proyecto con git estando en la rama principal -> que Nova
    # cree antes una rama de pruebas (git switch -c nova/<arreglo>) o que el usuario lo confirme con un clic.
    if RE_ESCRIBIR.search(nombre) and p and not _w(p).startswith(_GEM):
        rama, repo = rama_git(p)
        if rama in RAMAS_PRINCIPALES and not autoriza_web(conv):
            return "force_ask", (
                f"LEY 5 (cero experimentos en vivo): vas a editar {p.name} en la rama PRINCIPAL '{rama}' de "
                f'{repo.name}. Primero crea una rama de pruebas: git -C "{repo}" switch -c nova/<arreglo> '
                "(no copia nada, es instantaneo). Solo si el usuario dice que es en caliente, lo confirma aqui."
            )
    # Documentos para el usuario: a documentos_generados\<proyecto>, nunca a scratch (regla de la ley 6; solo en CHARLA)
    texto_args = ruta + " " + comando
    if modo == "charla" and RE_DOC_EN_SCRATCH.search(texto_args) and (RE_ESCRIBIR.search(nombre) or comando):
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
            "servidores del modelo. Solo si el usuario lo ha pedido expresamente."
        )
    if comando and RE_CMD_ESCRIBE.search(comando):
        for trozo in re.findall(
            r"[A-Za-z]:\\[^\"'|;&<>]+|~[\\/][^\"'|;&<>\s]+", comando
        ):
            if protegida_para(trozo.strip(), modo):
                if perm and not intocable(trozo):
                    via_permiso = True
                    continue
                return "deny", (
                    f"Comando que escribe en una carpeta protegida ({trozo.strip()[:120]}). "
                    "Nova no escribe ahi ni por terminal. Pideselo al usuario."
                )
    if comando and RE_PELIGROSO.search(comando):
        return (
            "force_ask",
            f"Comando destructivo: {comando[:160]}. el usuario tiene que confirmarlo.",
        )
    if RE_ESCRIBIR.search(nombre) and p:
        if protegida_para(ruta, modo):
            if perm and not intocable(ruta):
                via_permiso = True
            else:
                return (
                    "deny",
                    f"Carpeta protegida ({ruta}): Nova no escribe aqui." + ("" if intocable(ruta) else MSG_PIDE_PERMISO),
                )
        # 17/11: sus scripts/herramientas YA no son intocables: en ENCARGO/TOTAL los mejora con copia automatica; en
        # CHARLA se le pregunta al usuario (lo decide el bloque de modos de main()).
        if p.name.lower().startswith(".env"):
            return "deny", "Los .env y las claves solo los toca el usuario."
        sitio = sitio_no_permitido(p) if modo == "charla" and not via_permiso else ""
        if sitio:
            return "deny", sitio
        n = lineas_nuevas(args)
        # 09/11 tarde (Claude, a pedido del usuario): una WEB grande desde la nube ya no es un clic (se aprobaba sin leer:
        # cafe_especialidad 372 y 460 lineas). Es BLOQUEO salvo que el usuario dijera "escribelo tu" en su ultimo mensaje
        # (lo apunta nova_hook_turno.py en .autoriza_codigo.json); con permiso pasa sin clic.
        if p.suffix.lower() in EXT_WEB and n > MAX_LINEAS:
            if autoriza_web(conv) or modo == "total":
                return "allow", ""
            return "deny", (
                f"BLOQUEADO: {n} lineas de web ({p.name}) escritas desde la nube de una vez (limite {MAX_LINEAS}). "
                f'Las webs se hacen con el ESTUDIO: & "{PYTHON_NOVA}" "{ESTUDIO}" ficha "<carpeta>" "<pedido>" y sigue '
                "sus pasos: tus estilos van partidos en estudio/estilos/NN_*.css y tus secciones en estudio/secciones/<id>.html "
                f"(cada archivo <= {MAX_LINEAS} lineas); el volumen lo pica Qwen con 'estudio.py picar'. "
                "Solo si el usuario dice 'escribelo tu' puedes escribir un archivo mas grande."
            )
        if modo == "charla" and p.suffix.lower() in EXT_CODIGO and n > MAX_LINEAS:
            return "force_ask", (
                f"La nube va a escribir {n} lineas de codigo en {p.name} (limite 150). Algo tan grande lo pica "
                "Qwen por secciones: <PYTHON> <NOVA_HOME>\\antigravity\\scripts\\nova_secciones.py --carpeta <ruta> "
                "(Nova escribe secciones.json). el usuario decide si lo autoriza."
            )
    if RE_LEER.search(nombre) and p and RE_SECRETO.search(str(p)):
        return "force_ask", (
            f"AVISO CLAVES: {p.name} guarda claves y, si se lee, su contenido viajara a los servidores del "
            "modelo. Solo si el usuario lo ha pedido expresamente (los scripts las cargan solos en local)."
        )
    if RE_LEER.search(nombre) and p:
        # 26/11 noche (D2d): la salida de SU propio comando (steps\N\output.txt, tasks\task-N.log) no es un "documento"
        m_salida = RE_SALIDA_PROPIA.search(_norm(str(p)))
        if m_salida and conv and m_salida.group(1).lower() == re.sub(r"[^\w\-]", "", conv).lower():
            return "allow", ""
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
        # 26/11 (Claude, auditoria de Carbon): una IMAGEN no es texto: no tiene "rango de lineas" y en tokens cuesta lo
        # mismo pese 50 KB o 900 KB. El estudio web y la revision visual generan hojas de 200-600 KB que Nova TIENE que ver.
        if p.suffix.lower() in EXT_IMAGEN and kb <= MAX_KB_IMAGEN:
            return ("permiso_usuario", "") if via_permiso else ("allow", "")
        if p.suffix.lower() in EXT_IMAGEN:
            return "deny", (
                f"{p.name} pesa {kb / 1024:.1f} MB: demasiado para mandarla entera. Haz una copia reducida (max. 1600 px, "
                "JPG calidad 80, con PIL) en temporal\\ y lee esa."
            )
        if kb > MAX_KB:
            return "deny", (
                f"{p.name} pesa {kb:.0f} KB: no se lee entero. Lee solo un rango de lineas, busca con grep/rg "
                "o resumelo con resumir.py."
            )
    return ("permiso_usuario", "") if via_permiso else ("allow", "")


# ---------------------------------------------------------------- nivel verde: auto_approve (sin clic del usuario)
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
    r"(python|py|python3)(\.exe)?\s+[^;|&]*?(nova_tarea|nova_secciones|nova_auditoria|nova_pipeline_local|resumir|conversor|orquestador|estudio)\.py\b",
    r"(python|py|node|npm|git|ollama)(\.exe)?\s+(--version|-V)\b",
    r"ollama\s+(list|ps)\b",
    r"node\s+\S*draw\.mjs\b",
    r"npm\s+run\s+(dev|build|test|lint|preview|typecheck)\b",
    r"New-Item\s+(-ItemType\s+Directory|-Type\s+Directory|.*-ItemType\s+Directory)",
    r"(mkdir|md)\b",
    r"(ForEach-Object|foreach|%)\s*\{",  # 26/11: solo lectura; lo de dentro de {} se revisa abajo (RE_ESCRIBE_EN_BLOQUE)
]
RE_CMD_SEGURO = re.compile(r"(?i)^\s*&?\s*(" + "|".join(CMD_SEGUROS) + r")")
# 26/11: "$(" solo se permite como $($var.Prop) dentro de un texto; cualquier otro $( puede ejecutar algo.
RE_PELIGRO_EN_SEGURO = re.compile(
    r"(?i)>|\|\s*(iex|Invoke-Expression|sh|bash|cmd|powershell)\b|Invoke-WebRequest|curl|wget|"
    r"\$\((?!\s*\$[\w.]+(\[[^\]]*\])?\s*\))|`"
)
# 26/11 (Claude): hueco cerrado. Antes "Get-ChildItem | Where-Object { Remove-Item $_ }" pasaba sin clic porque solo
# se miraba la primera palabra de cada trozo. Si hay un bloque { } con algo que escribe, borra o lanza: no es seguro.
RE_ESCRIBE_EN_BLOQUE = re.compile(
    r"(?i)\b(Remove|Set|New|Move|Copy|Rename|Stop|Start|Invoke|Clear|Export|Install|Uninstall|Restart|Add)-\w+|Out-File"
    r"|\b(del|rm|rd|ri|rmdir|mv|move|cp|copy|ren|kill|erase)\b|\[(System\.)?IO\.|WriteAll|\.Delete\(|\.Kill\("
)


def comando_seguro(comando: str) -> bool:
    m = RE_ENVOLTORIO.match(comando)
    if m:
        comando = m.group(2) if m.group(2) is not None else m.group(4)
    if not comando.strip() or RE_PELIGRO_EN_SEGURO.search(comando):
        return False
    if "{" in comando and RE_ESCRIBE_EN_BLOQUE.search(comando):
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
        r = _w(Path(ruta))
        casa = _w(Path.home())
        fuera = (
            (not r.startswith(casa))
            or "\\appdata\\" in r
            or "\\.gemini\\" in r
            or r.startswith(casa + "\\.")
            or carpeta_sync_nube(r)
        )
        return not fuera and lineas_nuevas(args) <= MAX_LINEAS
    return False


# ------------------------------------------------------------------------------------------------------------------
# 17/11 (Claude, el usuario: "si le pedi la web, eso no necesita mi permiso; los permisos son para archivos de fuera
# del proyecto"): en un ENCARGO POR VOZ ([voz]) lo que Nova haga DENTRO de su zona de proyectos pasa sin preguntar.
# Zona = antigravity\scratch\ (donde Nova crea los proyectos) + las carpetas de trabajo de la conversacion, salvo que
# esas carpetas contengan la casa de Nova (nova_core, config, vault...). Lo destructivo/prohibido ya lo frenaron antes
# regla_contenido y las reglas de claves: aqui solo se quita el clic a lo normal y de dentro.
# ------------------------------------------------------------------------------------------------------------------
ZONA_PROYECTOS = Path.home() / ".gemini" / "antigravity" / "scratch"
# tambien es "su sitio" en un encargo: los documentos que entrega y la ficha de cada proyecto
ZONAS_EXTRA = (Path.home() / ".gemini" / "antigravity" / "documentos_generados",
               Path.home() / ".gemini" / "antigravity" / "proyectos")
CASA_NOVA = Path.home() / ".gemini" / "nova_core"
GEMINI_DIR = Path.home() / ".gemini"  # sus reglas, skills y herramientas: LEERLAS siempre puede (las claves ya se frenan antes)
RE_RUTA_EN_CMD = re.compile(
    r'"([A-Za-z]:[\\/][^"]+)"|\'([A-Za-z]:[\\/][^\']+)\'|(?<![\w"\'])([A-Za-z]:[\\/][^\s;|&"\'<>]+)'
    # v3.3 macOS/Linux: rutas absolutas (/Users/..., /home/...) y con ~ (~/.gemini/...), con o sin comillas
    r'|"((?:/|~/)[^"]+)"|\'((?:/|~/)[^\']+)\'|(?<![\w"\'/.:])((?:/(?:Users|home|Volumes|mnt|media|opt|tmp|var|private)/|~/)'
    r'[^\s;|&"\'<>]+)'
)

# 24/11 (Claude, el usuario: "toda las cagadas me las como yo"; hoy Nova escribio activity_main.xml de practica_pm sin
# pedirlo). MODO PRACTICAS: un archivo DENTRO de una carpeta practica_* / practicas_* / entregable_* es trabajo de
# clase del usuario: Nova explica y propone, NO escribe. Se desbloquea solo con su permiso explicito en SU mensaje
# ("hazlo tu", "te doy permiso", "encargate"...: permiso_usuario, dura hasta su siguiente mensaje). Lo generado por el
# build/IDE (build, .gradle, .idea, bin...) no cuenta. Va en cualquier nivel (charla, encargo, total).
RE_PRACTICA = re.compile(r"(?i)[\\/](practicas?|entregables?)_[^\\/]+[\\/]")
RE_PRACTICA_GENERADO = re.compile(
    r"(?i)[\\/](build|\.gradle|\.idea|\.kotlin|\.metadata|\.settings|bin|out|target|node_modules|\.nova_respaldo)[\\/]"
)
MSG_PRACTICA = (
    "MODO PRACTICAS (lo vigila un hook): {archivo} es de una practica de clase del usuario y aqui NO escribes tu. "
    "Explicale que cambiarias, donde y por que (fragmento corto en el chat, al nivel del curso, sin modernizar: nada "
    "de Compose, streams o records si el proyecto no los usa) y deja que lo haga el. Solo si el dice 'hazlo tu' o "
    "'te doy permiso' en su mensaje lo escribes tu, y solo el trozo necesario con edit_file."
)


def es_practica(ruta: str) -> bool:
    r = (ruta or "").replace("/", "\\")
    return bool(RE_PRACTICA.search(r)) and not RE_PRACTICA_GENERADO.search(r)


def practica_tocada(nombre: str, args: dict) -> str:
    """Ruta de practica que esta llamada ESCRIBE (herramienta de escritura o comando que escribe), o ''."""
    if RE_ESCRIBIR.search(nombre or ""):
        ruta = ruta_de(args)
        return ruta if es_practica(ruta) else ""
    comando = str(args.get("CommandLine") or args.get("command") or "")
    if comando and RE_CMD_ESCRIBE.search(comando):
        for m in RE_RUTA_EN_CMD.finditer(comando):
            ruta = next(g for g in m.groups() if g)
            if es_practica(ruta):
                return ruta
    return ""
# Nunca sin preguntar, aunque sea dentro del proyecto: ejecutar codigo bajado/encadenado y BORRAR (el usuario 17/11:
# "eliminar archivos y demas" sigue pidiendo permiso)
RE_CMD_NUNCA_SOLO = re.compile(
    r"(?i)\|\s*(iex|invoke-expression|sh|bash|cmd|powershell)\b|invoke-expression|\biex\b|"
    r"remove-item|\brm\b|\brmdir\b|\brd\b|\bdel\b|\berase\b|clear-content|\bri\b|git\s+(rm|clean|reset)"
)
RE_HERRAMIENTA_BORRA = re.compile(r"(?i)delete|remove|unlink|trash")


def _norm(p: str) -> str:
    return _w(p).rstrip("\\")  # v3.3: misma forma en Windows, macOS y Linux (y ~ expandido)


def raices_encargo(datos: dict, e: dict | None = None) -> list[str]:
    """Zona de trabajo segun el modo. CHARLA: solo scratch. ENCARGO/TOTAL: scratch + documentos_generados + proyectos +
    SUS HERRAMIENTAS (con copia) + carpetas de trabajo de la conversacion + las carpetas que el usuario nombro."""
    e = e or {"modo": "encargo"}
    raices = [_norm(str(ZONA_PROYECTOS))]
    # 26/11 (Claude, auditoria de Carbon): la carpeta de artefactos de ESTA conversacion (brain\<id>: task.md, planes,
    # scratch de Antigravity) es de Nova en cualquier modo; en CHARLA pedia clic 9 de 17 veces. Su transcript
    # (.system_generated) sigue fuera: ver dentro_de().
    conv_id = re.sub(r"[^\w\-]", "", str(datos.get("conversationId") or ""))
    if len(conv_id) >= 8:
        raices.append(_norm(str(ANTIGRAVITY / "brain" / conv_id)))
    # 23/11 (Claude, el usuario: "el chat esta dentro de ese proyecto y me va pidiendo como 5 permisos"): la carpeta en la que
    # el usuario ABRIO la conversacion (workspace de Antigravity) es su zona de trabajo tambien en CHARLA. Borrar sigue
    # preguntando siempre (clasificar_encargo) y la zona blindada nunca se toca.
    casa = _norm(str(CASA_NOVA))
    for w in datos.get("workspacePaths") or []:
        from urllib.parse import unquote

        w = unquote(re.sub(r"^file://", "", str(w)))  # v3.3: file:///Users/ana (Mac) conserva su "/" inicial
        if re.match(r"^/[A-Za-z]:[\\/]", w):  # file:///C:/... (Windows)
            w = w[1:]
        nw = _norm(w)
        if nw and len(nw) > 3 and not casa.startswith(nw + "\\"):  # nunca una carpeta que contenga nova_core
            raices.append(nw)
    if e.get("modo") == "charla":
        return raices
    raices += [_norm(str(z)) for z in ZONAS_EXTRA] + [_norm(str(z)) for z in ZONAS_HERRAMIENTAS]
    raices += [_norm(z) for z in (e.get("zonas") or []) if len(_norm(z)) > 3]
    return raices


def dentro_de(ruta: str, raices: list[str]) -> bool:
    r = _norm(ruta)
    if "\\.system_generated" in r:  # 26/11: el transcript de Antigravity nunca es zona de trabajo
        return False
    return any(r == z or r.startswith(z + "\\") for z in raices) and "\\.." not in r


RE_PUENTE_EXECUTE = re.compile(r"(?i)(127\.0\.0\.1|localhost):5005/execute")
RE_ACCION_PUENTE = re.compile(r"""(?i)["']?action["']?\s*:\s*["']([a-z_]+)["']""")
ACCIONES_EN_PAGINA = {"click", "click_at", "type", "scroll", "press_key", "hover", "find", "locate", "get_text",
                      "get_selection", "snapshot", "screenshot", "point_check", "upload_file", "go_back",
                      "go_forward", "reload_tab", "navigate_tab", "wait", "close_tab"}
RE_LLAMADA_HTTP = re.compile(r"(?i)\b(invoke-restmethod|invoke-webrequest|irm|iwr|curl(\.exe)?)\b")
RE_URL_HOST = re.compile(r"(?i)\bhttps?://([^/\s'\"`:]+)")
RE_GUARDA_ARCHIVO = re.compile(r"(?i)-outfile\b|--output\b|\s-o\s|-OutFile")
RE_SOLO_MIRA = re.compile(r"(?i)^\s*(\$\w+\s*=\s*)?(netstat|findstr|get-nettcpconnection|write-output|echo)\b")


def solo_servicios_locales(comando: str) -> bool:
    """True si el comando SOLO habla con servicios de este equipo (127.0.0.1 / localhost) y no guarda archivos."""
    if RE_CMD_ESCRIBE.search(comando) or RE_GUARDA_ARCHIVO.search(comando) or RE_CMD_NUNCA_SOLO.search(comando):
        return False
    # 22/11: las URL de DENTRO del -Body son datos (navigate a una web), no a quien se llama
    sin_body = re.sub(r"(?is)-body\s+('[^']*'|\"[^\"]*\"|@'.*?'@|\$\w+)", "", comando)
    hosts = [h.lower() for h in RE_URL_HOST.findall(sin_body)]
    if not hosts or not RE_LLAMADA_HTTP.search(comando):
        return False
    return all(h in ("127.0.0.1", "localhost", "[::1]") for h in hosts)


def clasificar_encargo(nombre: str, args: dict, datos: dict, e: dict | None = None) -> tuple[str, str]:
    """('dentro', '') pasa sin preguntar; ('borrar'|'fuera', detalle) se pregunta al usuario.
    dentro = todo lo que toca esta en su zona (segun el modo), o es LEER sus propias reglas/herramientas (~/.gemini),
    o un comando de solo lectura sin rutas de fuera. En TOTAL todo es 'dentro' salvo borrar."""
    if RE_HERRAMIENTA_BORRA.search(nombre):
        return "borrar", ruta_de(args)
    comando0 = str(args.get("CommandLine") or args.get("command") or "")
    if comando0 and RE_ANADE_LECCION.search(comando0):  # 26/11 noche (D2e): la Ley 3 pide la leccion; anadirla vale siempre
        return "dentro", ""
    if comando0 and RE_DIRECTOR_NOVA.search(comando0):  # 26/11 noche (D3): lanzar/resumir el director = su camino por defecto
        return "dentro", ""
    if comando0 and RE_CMD_NUNCA_SOLO.search(comando0):
        return "borrar", comando0[:200]
    if (e or {}).get("modo") == "total":
        return "dentro", ""
    raices = raices_encargo(datos, e)
    casa = [_norm(str(GEMINI_DIR))]
    comando = str(args.get("CommandLine") or args.get("command") or "")
    if comando:
        if RE_CMD_NUNCA_SOLO.search(comando):
            return "borrar", comando[:200]
        rutas = [next(g for g in m.groups() if g) for m in RE_RUTA_EN_CMD.finditer(comando)]
        cwd = str(args.get("Cwd") or args.get("cwd") or datos.get("cwd") or "")
        solo_lee = comando_seguro(comando) and not RE_CMD_ESCRIBE.search(comando)
        zona = raices + (casa if solo_lee else [])
        # 22/11 (Claude, el usuario: "le dije hazlo tu y me pide permiso por cada paso"): en ENCARGO sin carpeta, cada llamada
        # al puente de Brave (127.0.0.1:5005: switch_tab, click, type) o a Penpot/Ollama en local caia en "comando que no
        # dice donde actua" -> clic en cada paso. Hablar SOLO con servicios de este equipo, sin rutas ni escribir
        # archivos, es trabajo dentro de su encargo.
        if not rutas and solo_servicios_locales(comando):
            return "dentro", ""
        # 22/11: leer/buscar en SU propia carpeta (.gemini: brain, registros, skills) sin escribir ni borrar nada
        if rutas and not RE_CMD_ESCRIBE.search(comando) and all(dentro_de(r, casa) for r in rutas):
            return "dentro", ""
        fuera = [r for r in rutas + ([cwd] if cwd else []) if not dentro_de(r, zona)]
        if fuera:
            return "fuera", fuera[0]
        if rutas or cwd or solo_lee:
            return "dentro", ""
        return "fuera", comando[:200]  # comando que no dice donde actua
    ruta = ruta_de(args)
    if not ruta:
        return "dentro", ""  # herramientas sin archivo (buscar en internet, pensar...)
    # 26/11 (prueba A/B): leer la salida truncada de SU propio comando pedia clic y Nova estuvo 9 min parada.
    # Solo LEER y solo su conversacion; el resto de .system_generated (el transcript) sigue fuera.
    m = RE_SALIDA_PROPIA.search(_norm(ruta))
    conv_id = re.sub(r"[^\w\-]", "", str(datos.get("conversationId") or "")).lower()
    if m and conv_id and m.group(1) == conv_id and RE_LEER.search(nombre) and not RE_ESCRIBIR.search(nombre):
        return "dentro", ""
    if dentro_de(ruta, raices) or (RE_LEER.search(nombre) and not RE_ESCRIBIR.search(nombre) and dentro_de(ruta, casa)):
        return "dentro", ""
    return "fuera", ruta


AVISO_GASTO_VOZ = Path.home() / ".gemini" / "antigravity" / "voice_cache" / "aviso_gasto.json"


def regla_gasto(conv: str, transcript: str, encargo_voz: bool = False) -> tuple[str, str, dict]:
    """Freno de gasto: pregunta UNA vez al cruzar cada tope de tokens y cada bloque de herramientas seguidas.
    17/11 (Claude, el usuario: "cuando es una web o algo concreto deberia avanzar asi como tu"): en los encargos
    hechos por voz (llegan con la marca [voz]) Nova trabaja de corrido: el bloque de seguidas sube a
    MAX_SEGUIDAS_VOZ (solo frena un bucle sin fin). El freno de GASTO se mantiene (lo pregunta Ayla en voz alta)."""
    if not transcript:
        return "allow", "", {}
    max_seguidas = MAX_SEGUIDAS_VOZ if encargo_voz else MAX_SEGUIDAS
    total, seguidas, contexto, des = gasto(transcript)
    info = {
        "tokens_conv": total,
        "tokens_real": des.get("real", total),
        "tokens_bruto": des["bruto"],
        "seguidas": seguidas,
        "contexto": contexto,
    }
    if des.get("pct"):
        info["pct_cupo"] = des["pct"]
    if des.get("pct_5h"):
        info["pct_cupo_5h"] = des["pct_5h"]  # 25/11: limite de 5 horas
    estado = leer_json(ESTADO, {})
    e = estado.get(conv, {"tope": 0, "bloque": 0, "compact": False})
    decision, motivo = "allow", ""
    if des.get("orquestador"):
        # 20/11 (Claude, el usuario: "los orquestadores a libre albedrio, solo con un vigilante"): con Orchestrator
        # (Neon/Argon) NO hay freno de gasto ni de herramientas seguidas (hoy salto 32 veces en una conversacion):
        # solo AVISA por voz (clip de Marina) cada TRAMO_ORQ_PCT % del cupo de Argon/Neon. La seguridad (claves,
        # borrar, rutas, pagos) la sigue mirando regla_contenido. El informe lo escribe nova_hook_turno.py (Stop).
        info["orquestador"] = True
        # 24-25/11: una sola bolsa Gemini; el aviso va por el limite de 5 horas (el que antes se agota)
        tramo = int((des.get("pct_5h") or des["pct"]).get("gemini", 0) // TRAMO_ORQ_PCT)
        if tramo > e.get("tramo_orq", 0):
            e["tramo_orq"] = tramo
            info["aviso_orquestador"] = des["pct"]
            try:
                AVISO_HOOK_VOZ.write_text(json.dumps({"hora": time.time(), "tipo": "gasto"}), encoding="utf-8")
            except OSError:
                pass
        estado[conv] = e
        try:
            ESTADO.write_text(json.dumps(estado), encoding="utf-8")
        except OSError:
            pass
        return "allow", "", info
    # 09/11: el aviso de /compact a los 100k ya NO es un clic aqui: lo pone nova_hook_turno.py (aviso_bufer) dentro del
    # chat, con la copia del .txt, el contador de 5 compactaciones y el salto de ventana (Ley 16).
    tope = total // TOPE_TOKENS
    if decision == "allow" and tope > e.get("tope", 0) and encargo_voz:
        # 17/11: en encargos por voz el freno de gasto NO para a Nova: Ayla se lo dice al usuario en voz alta
        e["tope"] = tope
        try:
            AVISO_GASTO_VOZ.write_text(json.dumps({"hora": time.time(), "tokens": total, "conv": conv[:8]}),
                                       encoding="utf-8")
        except OSError:
            pass
        info["aviso_gasto_voz"] = total
    elif decision == "allow" and tope > e.get("tope", 0):
        e["tope"] = tope
        decision, motivo = (
            "force_ask",
            (
                f"FRENO DE GASTO: esta conversacion lleva ~{des.get('real', total) // 1000}k tokens REALES "
                f"({des['nuevos'] // 1000}k nuevos + {des['cache'] // 1000}k de cache al 10 % + {des['salida'] // 1000}k de salida; "
                f"sin descontar la cache serian {des['bruto'] // 1000}k) = coste ponderado ~{total // 1000}k "
                f"(pesados x4, Opus x10){texto_cupo(des)}. "
                "el usuario decide si se sigue o se abre una ventana nueva con el puente."
            ),
        )
    bloque = seguidas // max_seguidas
    if decision == "allow" and bloque > e.get("bloque", 0):
        e["bloque"] = bloque
        decision, motivo = (
            "force_ask",
            (
                f"Llevo {seguidas} herramientas seguidas sin que el usuario escriba. "
                "Pregunto antes de seguir."
            ),
        )
    if seguidas < max_seguidas:
        e["bloque"] = (
            0  # el usuario ha escrito: el contador de seguidas vuelve a empezar
        )
    estado[conv] = e
    try:
        ESTADO.write_text(json.dumps(estado), encoding="utf-8")
    except OSError:
        pass
    return decision, motivo, info


AVISO_HOOK_VOZ = Path.home() / ".gemini" / "antigravity" / "voice_cache" / "aviso_hook.json"


def avisar_marina(salida: dict) -> None:
    """18/11 (Claude, el usuario: "la voz de Marina para que avise del hook"): si el hook frena a Nova, deja aviso_hook.json;
    la aduana (nova_voz.py --solo-aduana) lo dice con un clip de Marina ya grabado (sin cargar ningun modelo)."""
    dec = salida.get("decision")
    if dec not in ("deny", "force_ask"):
        return
    motivo = str(salida.get("reason", ""))
    if motivo.startswith("FRENO DE GASTO") or "herramientas seguidas" in motivo:
        tipo = "gasto"
    elif motivo.startswith("BORRAR"):
        tipo = "borrar"
    elif dec == "deny":
        tipo = "bloqueo"
    else:
        tipo = "permiso"
    try:
        AVISO_HOOK_VOZ.write_text(json.dumps({"hora": time.time(), "tipo": tipo}), encoding="utf-8")
    except OSError:
        pass


# 22/11 (Claude, el usuario: "si, que el hook vigile windows-mcp"). windows-mcp da a Nova la laptop entera (PowerShell,
# archivos, Registro, procesos, clics). Antigravity lo manda como call_mcp_tool {ServerName, ToolName, Arguments(json)}
# y el hook no veia DENTRO: se saltaba el zona blindada, la zona protegida y las reglas deny de Antigravity. Ahora cada
# llamada peligrosa se TRADUCE a su equivalente y pasa por las mismas reglas que la terminal y los archivos normales:
#   PowerShell -> run_command | FileSystem write/copy/move -> write_to_file (move: ademas borra el origen) |
#   FileSystem delete -> delete_file | FileSystem read -> view_file | App con una consola -> run_command |
#   Registry set/delete y Process kill -> SIEMPRE pregunta. Clics, teclado, capturas y abrir apps: libres.
RE_SERVIDOR_WINDOWS = re.compile(r"(?i)windows")
RE_EXE_CONSOLA = re.compile(r"(?i)(^|[\\/])(powershell|pwsh|cmd|wscript|cscript|python[\d.]*|pythonw|py|reg|regedit|"
                            r"bash|wsl|node|mshta|rundll32)(\.exe)?$")


def _sin_comillas(v) -> str:
    v = str(v or "").strip()
    try:
        w = json.loads(v)
        return w if isinstance(w, str) else v
    except ValueError:
        return v.strip('"')


def traducir_windows_mcp(args: dict):
    """None si no es windows-mcp (o es inofensivo). Si no: (etiqueta, nombre_equivalente, args_equivalentes, forzar)."""
    if not RE_SERVIDOR_WINDOWS.search(_sin_comillas(args.get("ServerName"))):
        return None
    tool = _sin_comillas(args.get("ToolName")).lower()
    a = args.get("Arguments") or {}
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except ValueError:
            a = {}
    if not isinstance(a, dict):
        a = {}
    modo = str(a.get("mode") or "").lower()
    etiqueta = f"windows-mcp.{tool}" + (f".{modo}" if modo else "")
    if tool == "powershell":
        return etiqueta, "run_command", {"CommandLine": str(a.get("command") or "")}, ""
    if tool == "filesystem":
        ruta, destino = str(a.get("path") or ""), str(a.get("destination") or "")
        if modo == "write":
            return etiqueta, "write_to_file", {"TargetFile": ruta, "CodeContent": str(a.get("content") or "")}, ""
        if modo in ("copy", "move"):
            if modo == "move" and ruta and (es_freno(ruta) or protegida(ruta)):
                return etiqueta, "delete_file", {"Path": ruta}, ""  # mover = borrar el origen
            return etiqueta, "write_to_file", {"TargetFile": destino, "CodeContent": ""}, ""
        if modo == "delete":
            return etiqueta, "delete_file", {"Path": ruta}, ""
        if modo in ("read", "info"):
            return etiqueta, "view_file", {"AbsolutePath": ruta}, ""
        return None  # list / search: mirar es libre
    if tool == "registry" and modo in ("set", "delete"):
        return etiqueta, "", {}, (f"REGISTRO DE WINDOWS: Nova quiere {'cambiar' if modo == 'set' else 'borrar'} "
                                  f"{a.get('path')}\\{a.get('name') or ''}. Puede romper Windows o programas. El usuario decide.")
    if tool == "process" and modo == "kill":
        return etiqueta, "", {}, (f"MATAR PROCESO: Nova quiere cerrar a la fuerza {a.get('name') or a.get('pid')}. "
                                  "Se pierde lo que no estuviera guardado. El usuario decide.")
    if tool == "app" and modo == "launch_executable" and RE_EXE_CONSOLA.search(str(a.get("executable") or "").strip()):
        return etiqueta, "run_command", {"CommandLine": f"{a.get('executable')} {a.get('args') or ''}"}, ""
    return None


def main() -> None:
    inicio = time.time()
    fila = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}
    salida = {"decision": "allow"}
    proy_dir = None
    try:
        crudo = sys.stdin.buffer.read().decode(
            "utf-8-sig", errors="replace"
        )  # acepta BOM (PowerShell lo pone)
        datos = json.loads(crudo or "{}")
        try:
            proy_dir = proyecto_director(datos)  # 26/11 noche (D2): llamada del NOVA DIRECTOR (sin ventana)?
        except Exception:
            proy_dir = None
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
        forzar_mcp = etiqueta_mcp = ""
        if nombre == "call_mcp_tool":  # 22/11: windows-mcp -> su equivalente (lo vigilan las mismas reglas)
            trad = traducir_windows_mcp(args)
            if trad:
                etiqueta_mcp, nombre_eq, args_eq, forzar_mcp = trad
                if nombre_eq:
                    nombre, args = nombre_eq, args_eq
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
                # 23/11: que carpeta de trabajo manda Antigravity (para confirmar la zona del chat en CHARLA)
                "workspace": [str(w)[-80:] for w in (datos.get("workspacePaths") or [])][:3],
            }
        )
        try:  # 24/11: vigilante de reescrituras (solo mide; un fallo aqui no cambia la decision)
            reescritura = medir_reescritura(nombre, args)
            if reescritura:
                fila["reescritura"] = reescritura
        except Exception as ex:
            fila["error_reescritura"] = str(ex)[:150]
        if fila["comando"] and re.search(
            r"nova_tarea\.py|nova_pipeline_local\.py|nova_local_worker\.py|nova_auditoria\.py|estudio\.py",
            fila["comando"],
        ):
            fila["piramide"] = True
        # 17/11: NIVEL DE AUTONOMIA de esta conversacion (charla | encargo | total), lo pone nova_hook_turno.py con lo
        # que dice el usuario. Un mensaje [voz] siempre es encargo.
        nivel_e = modo_de(conv)
        if str(datos.get("lastUserInput") or "").lstrip().startswith("[voz]") and nivel_e["modo"] == "charla":
            nivel_e["modo"] = "encargo"
        nivel = nivel_e["modo"]
        fila["nivel"] = nivel
        decision, motivo = regla_contenido(nombre, args, conv, nivel)
        if decision != "deny":  # 24/11: MODO PRACTICAS (antes que zonas y modos: la carpeta del chat no lo salta)
            ruta_p = practica_tocada(nombre, args)
            if ruta_p:
                fila["practica"] = True
                if permiso_usuario(conv):
                    fila["practica_permiso"] = True
                else:
                    decision, motivo = "deny", MSG_PRACTICA.format(archivo=Path(ruta_p).name)
        if decision != "deny":  # 25/11: FRENO DE REESCRITURAS (el usuario: "agarra todo y remplaza todo")
            freno_r = freno_reescritura(conv, fila, str(datos.get("lastUserInput") or ""))
            if freno_r:
                decision, motivo = "deny", freno_r
        if decision != "deny" and RE_ESCRIBIR.search(nombre):  # 25/11: reglas de capas (Java MVC)
            freno_c = freno_capas(conv, ruta_de(args), args)
            if freno_c:
                fila["capas"] = True
                decision, motivo = "deny", freno_c
        if forzar_mcp and decision != "deny":  # 22/11: Registro (cambiar/borrar) y matar procesos -> siempre pregunta
            decision, motivo = "force_ask", forzar_mcp
        if etiqueta_mcp:
            fila["mcp"] = etiqueta_mcp
        via_permiso = decision == "permiso_usuario"  # 22/11: zona protegida con permiso explicito del usuario
        if via_permiso:
            decision = "allow"
            fila["permiso_usuario"] = True
        dec_gasto, motivo_gasto, info = regla_gasto(
            conv, str(datos.get("transcriptPath") or ""), nivel != "charla"
        )
        fila.update(info)
        if decision == "allow" and dec_gasto != "allow":
            decision, motivo = dec_gasto, motivo_gasto
        rea_h = herramienta_rea_ejecuta(nombre)
        if decision == "allow" and rea_h:
            # 20/11 (Claude): REA que ejecuta/intercepta/modifica -> SIEMPRE pregunta (su propio aviso legal dice que
            # autorizar a inspeccionar no autoriza a ejecutar ni interceptar). record_build_consent: el consentimiento
            # lo da el usuario con sus palabras, nunca Nova.
            decision, motivo = "force_ask", (
                f"REA EJECUTA: Nova quiere usar '{rea_h}', que ejecuta, depura, instrumenta o modifica el programa o el "
                "dispositivo. Solo con programas tuyos o con permiso. El usuario decide.")
        if decision == "allow" and nombre == "invoke_subagent" and "asesor" in json.dumps(args).lower():
            # 20/11 (Claude, piramide del usuario): el asesor (Hydrogen xhigh) nunca arranca sin que el usuario lo sepa:
            # si no lo ha pedido el en su mensaje, pregunta; y como mucho 2 consultas por conversacion.
            previas = consultas_asesor(str(datos.get("transcriptPath") or ""))
            pedido = str(datos.get("lastUserInput") or "")
            fila["consultas_asesor"] = previas
            if previas >= 2:
                decision, motivo = "force_ask", (
                    "ASESOR: ya van 2 consultas al asesor en esta conversacion (tope). Si sigue sin salir, toca una "
                    "consulta de ventana (nova_consulta.py: Carbon -> Neon -> Opus). El usuario decide.")
            elif not re.search(r"(?i)asesor|consult|s[ií],? (cons|preg)|adelante|dale", pedido):
                decision, motivo = "force_ask", (
                    "ASESOR: Nova quiere consultar al asesor (modelo mas fuerte, solo lectura, ~50-70k del cupo "
                    "Gemini). El usuario decide.")
        if decision == "allow" and RE_ESCRIBIR.search(nombre):
            # 20/11 (Claude): CARRILES. Si el tema de la conversacion tiene kit obligatorio y Nova va a escribir un
            # archivo de ese tema sin haberlo leido, se frena UNA vez (la segunda pasa: nunca un bucle).
            try:
                import nova_carriles

                carril = nova_carriles.pendiente_de_leer(conv, str(datos.get("transcriptPath") or ""), ruta_de(args))
                if carril:
                    fila["carril"] = carril
                    decision, motivo = "deny", (
                        f"CARRIL {carril.upper()}: antes de escribir este archivo lee el kit del tema con read_file "
                        f"(una llamada): \"{nova_carriles.kit(carril)}\". Aplica lo que dice y vuelve a intentarlo.")
            except Exception as ex:
                fila["error_carriles"] = str(ex)[:150]
        fila["decision_calculada"] = decision
        if motivo:
            fila["motivo"] = motivo[:200]
        if decision == "allow":
            # 17/11 MODOS: dentro de su zona trabaja sola; BORRAR siempre pregunta; fuera de la zona: en CHARLA leer
            # es libre y escribir pregunta, en ENCARGO pregunta (Nova Voz lo pregunta en voz alta), en TOTAL no hay fuera.
            zona, detalle = clasificar_encargo(nombre, args, datos, nivel_e)
            fila["zona_encargo"] = zona
            if zona == "borrar" and proy_dir and borrado_en_proyecto(args, datos, proy_dir):
                zona = "dentro"  # 26/11 noche (D2a): el director borra sus temporales dentro del proyecto o de TEMP
                fila["director_borra"] = True
            if zona == "borrar":
                decision, motivo = "force_ask", f"BORRAR: Nova quiere eliminar algo ({detalle[:160]}). El usuario decide."
            elif via_permiso:  # 22/11: El usuario lo autorizo en su mensaje -> sin clic, con copia antes
                decision, motivo = "auto_approve", ""
                comando_p = str(args.get("CommandLine") or args.get("command") or "")
                tocadas_p = ([ruta_de(args)] if RE_ESCRIBIR.search(nombre) else []) + (
                    [next(g for g in m.groups() if g) for m in RE_RUTA_EN_CMD.finditer(comando_p)]
                    if comando_p and RE_CMD_ESCRIBE.search(comando_p) else [])
                copias = respaldar_protegido([t for t in tocadas_p if t])
                if copias:
                    fila["respaldo"] = copias[:3]
            elif zona == "dentro":
                decision, motivo = "auto_approve", ""
                comando_w = str(args.get("CommandLine") or args.get("command") or "")
                tocadas = ([ruta_de(args)] if RE_ESCRIBIR.search(nombre) else []) + (
                    [next(g for g in m.groups() if g) for m in RE_RUTA_EN_CMD.finditer(comando_w)]
                    if comando_w and RE_CMD_ESCRIBE.search(comando_w) else [])
                copias = respaldar([t for t in tocadas if t])
                if copias:
                    fila["respaldo"] = copias[:3]
            elif nivel == "charla" and nivel_verde(nombre, args) and not RE_ESCRIBIR.search(nombre):
                decision, motivo = "auto_approve", ""  # en charla, leer y mirar es libre
            elif nivel == "charla":
                decision, motivo = "force_ask", (
                    f"MODO CHARLA: Nova quiere crear o cambiar algo fuera de scratch y de la carpeta del chat ({detalle[:160]}). El usuario decide "
                    "(si le da un trabajo o una carpeta, pasa a ENCARGO y ya no pregunta).")
            else:
                decision, motivo = "force_ask", (
                    f"FUERA DE SU ZONA: Nova quiere tocar algo fuera de su carpeta de trabajo ({detalle[:160]}). "
                    "el usuario decide.")
            fila["decision_calculada"] = decision
        if proy_dir and decision in ("deny", "force_ask"):  # 26/11 noche (D2c): el "dale seguir" del usuario por proyecto
            patron = permiso_director(proy_dir, nombre, args, motivo)
            if patron:
                fila["permiso_director"] = patron[:80]
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
    if proy_dir:  # 26/11 noche (D2b): frenos del director sin voz (avisa el director al acabar, pausar o parar)
        fila["director"] = str(proy_dir)[-60:]
    else:
        avisar_marina(salida)
    fila["ms"] = round((time.time() - inicio) * 1000)
    fila["decision"] = salida["decision"]
    apuntar(fila)
    print(json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    main()

