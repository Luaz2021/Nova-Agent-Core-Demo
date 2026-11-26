"""
NOVA HOOK DE TURNO (Antigravity: PreInvocation + Stop). Complementa a nova_hook.py (PreToolUse), que solo ve herramientas.

Problema que arregla: Nova pegaba 75-100 lineas de codigo EN EL CHAT (sin herramienta), y eso no lo ve PreToolUse.
  - PreInvocation: si el usuario pide codigo, antes de cada llamada al modelo se inyecta un recordatorio efimero
    (no se acumula en el historial) con la regla: codigo de mas de 150 lineas -> Qwen por secciones (nova_secciones.py).
  - Stop: al terminar el turno, si la respuesta trae mas de MAX_LINEAS lineas de codigo y el usuario no dijo
    "escribelo tu", obliga a Nova a seguir UNA vez (por mensaje del usuario) para corregirlo y avisarle.

Uso:  python nova_hook_turno.py pre   |   python nova_hook_turno.py stop
Siempre: si algo falla, no bloquea (devuelve {}) y lo apunta en memory/registros/telemetria_hooks.jsonl.
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

# v3.2: CREATE_NO_WINDOW solo existe en Windows (en macOS/Linux subprocess da ValueError y el hook revienta)
SIN_VENTANA = 0x08000000 if os.name == "nt" else 0

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / ".nova_turno_estado.json"
REGISTRO = Path.home() / ".gemini" / "antigravity" / "memory" / "registros" / "telemetria_hooks.jsonl"
MAX_LINEAS = 150

# 26/11 (Claude, auditoria de Carbon): antes bastaba UNA palabra suelta ("tengo clase", "en funcion de", "que programa
# usas") y saltaba en cada ronda de herramientas (36 veces en una conversacion). Ahora hace falta VERBO de construir o
# cambiar + algo de codigo, y solo se avisa en el primer paso del mensaje (ver mas abajo: invocationNum == 0).
_VERBO_CODIGO = (r"escr[ií]be(me|lo)?|hazme|haz(lo)?|crea(me|lo)?|genera(me|lo)?|program[ae](me|lo)?|implementa(lo)?|"
                 r"arregla(lo)?|corrige(lo)?|refactoriza(lo)?|modifica(lo)?|edita(lo)?|a[nñ]ade|agrega|cambia|monta(me)?|"
                 r"desarrolla|codifica")
_COSA_CODIGO = (r"script|c[oó]digo|funci[oó]n|m[eé]todo|clase|componente|endpoint|algoritmo|regex|consulta sql|query|"
                r"programa|api|crud|dao|bot|app|python|javascript|typescript|react|html|css|sql|bash|powershell|java|"
                r"kotlin|swift|dart|rust|php|\.py|\.js|\.java|\.html|\.css")
RE_PIDE_CODIGO = re.compile(rf"(?i)\b({_VERBO_CODIGO})\b.{{0,60}}?\b({_COSA_CODIGO})(\b|$)")
RE_AUTORIZA = re.compile(r"(?i)escr[ií]be(lo|melo)\s+t[uú]|hazlo\s+t[uú]|p[eé]ga(lo|melo)\s+(aqu[ií]|en el chat)|en el chat")

RECORDATORIO = (
    "REGLA DE NOVA (ley 14, la vigila un hook): El usuario pide codigo. Hasta 150 lineas en 1-2 archivos: escribelo TU con "
    "edit_file/write_file (no en el chat). Una WEB: empieza con `<PYTHON> <NOVA_HOME>\\antigravity\\herramientas\\estudio_web\\"
    "estudio.py ficha <carpeta> \"<pedido>\"` y sigue sus pasos (tu diriges y escribes estilos/portada en trozos <= 150 lineas; "
    "Qwen pica el resto con 'estudio.py picar'). Otra pieza grande: secciones.json MASTICADO + "
    "`<PYTHON> <NOVA_HOME>\\antigravity\\scripts\\nova_secciones.py --carpeta <ruta>` (Qwen en local). "
    "Si dice 'escribelo tu', lo escribes. No leas el codigo de los scripts de Nova: solo ejecutalos."
)


def apuntar(d: dict) -> None:
    try:
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), **d}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def lineas_de_codigo(texto: str) -> int:
    """Lineas dentro de bloques ``` (si el ultimo bloque quedo sin cerrar por recorte, cuenta hasta el final)."""
    total, dentro = 0, False
    for linea in texto.splitlines():
        if linea.strip().startswith("```"):
            dentro = not dentro
            continue
        if dentro:
            total += 1
    return total


def respuestas_del_turno(transcript: str) -> tuple[str, str]:
    """(id del ultimo mensaje del usuario, texto de las respuestas del modelo desde entonces)."""
    ultimo_id, textos = "", []
    with open(transcript, encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                o = json.loads(linea)
            except ValueError:
                continue
            if o.get("type") == "USER_INPUT":
                ultimo_id, textos = str(o.get("step_index", "")), []
            elif o.get("type") == "PLANNER_RESPONSE" and o.get("content"):
                textos.append(str(o["content"]))
    return ultimo_id, "\n".join(textos)


def leer_estado() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- adjuntos (09/11, Claude, a pedido del usuario)
# Antigravity guarda lo que el usuario pega en brain/<conv>/.user_uploaded/ y nova_puente_capturas.py (cada 2 s) lo
# mueve a temporal/<AAAA-MM>/<fecha>_<nombre> y deja <nombre>.resumen.md (documento) o .vista.md (imagen) leido EN LOCAL.
# Antes Nova contestaba sin esperar y analizaba el original en la nube. Ahora, en la 1a llamada del turno, el hook espera
# a que el .md este listo y le ordena a Nova leer ESE .md. (El hook no puede quitar el adjunto del mensaje: la API de
# Antigravity no lo permite; si Antigravity lee el archivo al llamar al modelo, como el puente ya lo movio, no lo sube.)
DIR_BRAIN = Path.home() / ".gemini" / "antigravity" / "brain"
DIR_TEMPORAL = Path.home() / ".gemini" / "antigravity" / "temporal"
ESPERA_MAX_S = 45  # InternVL tarda ~15 s por imagen; un PDF corto ~2 s
MAX_CHARS_ADJUNTO = 12000  # ~3k tokens por adjunto como mucho (el puente ya resume con Qwen lo largo)


def _segundos_desde(iso: str) -> float:
    from datetime import datetime, timezone
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds()
    except (ValueError, TypeError):
        return 1e9


def adjuntos_del_turno(datos: dict, ventana_s: float = 180) -> list[str]:
    """Nombres de los archivos que el usuario pego en este turno (carpeta .user_uploaded + 'media' del transcript;
    del transcript solo si ese mensaje es reciente, para no repetir el adjunto de un turno anterior)."""
    nombres: list[str] = []
    conv = str(datos.get("conversationId") or "")
    sube = DIR_BRAIN / conv / ".user_uploaded"
    if conv and sube.is_dir():
        nombres += [p.name for p in sube.iterdir() if p.is_file()]
    transcript = datos.get("transcriptPath") or ""
    if transcript and Path(transcript).exists():
        media: list = []
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                if o.get("type") == "USER_INPUT":
                    media = (o.get("media") or []) if _segundos_desde(str(o.get("created_at", ""))) < ventana_s else []
        nombres += [Path(str(m.get("uri", ""))).name for m in media if isinstance(m, dict) and m.get("uri")]
    # Aduana (nova_voz.py + aduana.js): el adjunto no subio; en el mensaje va "[adjunto local: <archivo en temporal>]"
    nombres += RE_ADJUNTO_LOCAL.findall(str(datos.get("lastUserInput") or ""))
    return list(dict.fromkeys(n.strip() for n in nombres if n and n.strip()))


RE_ADJUNTO_LOCAL = re.compile(r"\[adjunto local:\s*([^\]\r\n]+?)\s*\]")


def buscar_md(nombre: str) -> Path | None:
    """El .vista.md / .resumen.md / .nota.md que el puente dejo para ese adjunto (el mas reciente).
    Vale para el nombre original de Antigravity (media_xxx.pdf -> <fecha>_media_xxx.pdf.*.md) y para el nombre exacto
    que pone la aduana (<fecha>_cotizacion.pdf -> <fecha>_cotizacion.pdf.*.md)."""
    if any(c in nombre for c in "*?[]/\\"):
        return None
    hallados = [p for patron in (f"*/*_{nombre}.*.md", f"*/{nombre}.*.md") for p in DIR_TEMPORAL.glob(patron)
                if time.time() - p.stat().st_mtime < 3600]
    return max(hallados, key=lambda p: p.stat().st_mtime) if hallados else None


PUENTE = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_puente_capturas.py"


def lanzar_puente(conv: str) -> bool:
    """Puente en modo 'una vez' para esta conversacion (mueve + lee en local). Sin ventana; no se espera aqui:
    el bucle de aviso_adjuntos sigue mirando si aparece el .md."""
    import subprocess
    try:
        pyw = Path(sys.executable).with_name("pythonw.exe")
        subprocess.Popen([str(pyw if pyw.exists() else sys.executable), str(PUENTE), "--mover", "--procesar", "--conv-id", conv],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=SIN_VENTANA)  # CREATE_NO_WINDOW
        return True
    except OSError as e:
        apuntar({"evento": "PreInvocation", "error_lanzar_puente": str(e)})
        return False


def aviso_adjuntos(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:  # solo en la primera llamada al modelo del turno
        return ""
    nombres = adjuntos_del_turno(datos)
    if not nombres:
        return ""
    t0 = time.time()
    conv = str(datos.get("conversationId") or "")
    sube = DIR_BRAIN / conv / ".user_uploaded"
    listos: dict[str, Path] = {}
    lanzado = False
    while time.time() - t0 < ESPERA_MAX_S:
        for n in nombres:
            if n not in listos and (md := buscar_md(n)):
                listos[n] = md
        if len(listos) == len(nombres):
            break
        # 09/11: con Antigravity recien abierto el puente (daemon de session_guard) aun no corre y el archivo se queda
        # en .user_uploaded. A los 1,5 s sin moverse, el hook lanza el puente UNA vez para esta conversacion.
        if not lanzado and time.time() - t0 > 1.5 and conv and sube.is_dir() and any(p.is_file() for p in sube.iterdir()):
            lanzado = lanzar_puente(conv)
        time.sleep(0.5)
    faltan = [n for n in nombres if n not in listos]
    apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "adjuntos_local", "adjuntos": len(nombres),
             "listos": len(listos), "espera_s": round(time.time() - t0, 1), "puente_lanzado_por_hook": lanzado})
    # 09/11 v2: Antigravity NO deja a Nova abrir archivos de .gemini\antigravity ("hardcoded system protection
    # boundary"), asi que el contenido del .md va aqui mismo. Ademas ahorra llamadas: cada herramienta reenvia ~20k tokens.
    partes = ["REGLA DE NOVA (adjuntos, la vigila un hook): el usuario ha pegado un adjunto y YA esta leido EN LOCAL "
              "(0 tokens de nube). Su contenido esta AQUI ABAJO. Trabaja SOLO con este texto: NO abras el original, NO "
              "intentes extraerlo con Python/PowerShell ni pidas permisos para hacerlo, y no busques el .md (Antigravity "
              "bloquea esa carpeta)."]
    for n, md in listos.items():
        try:
            texto = md.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            texto = f"(no se pudo leer {md.name}: {e})"
        if len(texto) > MAX_CHARS_ADJUNTO:
            texto = texto[:MAX_CHARS_ADJUNTO] + "\n[... recortado: es largo. Responde con esto y dile al usuario que hay mas.]"
        partes.append(f"\n===== ADJUNTO {n} =====\n{texto.strip()}\n===== FIN {n} =====")
    if faltan:
        partes.append("Aun procesandose en local: " + ", ".join(faltan) + ". Dile al usuario que lo repita en unos "
                      "segundos; no lo analices tu.")
    partes.append("Si este texto no basta para responder, dile al usuario que falta y por que.")
    return "\n".join(partes)


# ---------------------------------------------------------------- interruptor de MCP (09/11, Claude, a pedido del usuario)
# Playwright (~5.100 tokens) y Postgres (~5.000) viajan en CADA mensaje si estan encendidos. Van apagados y se
# encienden aqui solo si el usuario pide algo que los necesita; session_guard.ps1 los apaga al cerrar Antigravity.
NOVA_MCP = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_mcp.py"
PIDE_MCP = {  # 09/11 tarde: playwright va FIJO encendido (carga bajo demanda, no cuesta tokens); solo postgres
    "postgres": re.compile(r"(?i)\b(postgres(ql)?|supabase|base(s)? de datos|bbdd|sql|psql)\b"),
    # 22/11 (Claude, N3): codebase-memory-mcp = radiografia de un proyecto de codigo (quien llama a quien, arquitectura)
    "codebase": re.compile(r"(?i)\b(revisa(r)? (todo )?(el|mi|este|ese) (proyecto|c[oó]digo)|(mira|analiza|entiende|"
                           r"explica(me)?) (todo )?(el|mi|este|ese) (proyecto|c[oó]digo)|estructura del (proyecto|c[oó]digo)|"
                           r"arquitectura del (proyecto|c[oó]digo)|qui[eé]n (llama|usa) a|d[oó]nde se (usa|llama)|"
                           r"refactoriz\w*|codebase|radiograf[ií]a del (proyecto|c[oó]digo))\b"),
    # 22/11 (Claude, el usuario usa Penpot para los mockups de AutoCheck): @penpot/mcp (herramientas\penpot_mcp)
    "penpot": re.compile(r"(?i)\bpen\s?pot\b"),
}
# 22/11: al encender penpot, lo que tiene que hacer el usuario en el navegador (Nova no puede tocar Brave Shields)
AVISO_PENPOT = (
    "PENPOT: el servidor tarda hasta ~1-2 min la 1a vez en este equipo (se instala solo). Tus herramientas de Penpot "
    "necesitan el archivo abierto en Penpot con el plugin conectado: Plugins -> http://localhost:4400/manifest.json -> "
    "'Connect to MCP server'. Si tienes el puente del navegador, abre tu la pestana (LIST_TABS + SWITCH_TAB y SIEMPRE "
    "args.tabId); si no, dile al usuario esos pasos en 2 lineas. Si no conecta, pidele que permita localhost para "
    "design.penpot.app en su navegador (escudos / red privada). Si falta Node.js, diselo (nodejs.org). "
    "Empieza SIEMPRE leyendo high_level_overview."
)
PIDE_BRAVE = re.compile(r"(?i)\b(en )?(mi |el )?brave\b|\bmi (navegador|sesi[oó]n)\b")


def interruptor_mcp(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    pedido = str(datos.get("lastUserInput") or "")
    pedido = RE_ADJUNTO_LOCAL.sub("", pedido)  # que el nombre de un adjunto no encienda nada
    avisos = []
    if PIDE_BRAVE.search(pedido):
        avisos.append("Para navegar en el Brave del usuario (con sus sesiones) usa el puente de Brave "
                      "(http://127.0.0.1:5005: /status, /snapshot, /screenshot, POST /execute), NO Playwright.")
    for nombre, patron in PIDE_MCP.items():
        if patron.search(pedido):
            import subprocess
            try:
                # timeout 35 s: la recarga en caliente (RefreshMcpServers) reinicia los MCP y tarda ~10 s
                r = subprocess.run([sys.executable, str(NOVA_MCP), "activar", nombre], capture_output=True, timeout=35,
                                   creationflags=SIN_VENTANA)
                salida = r.stdout.decode("utf-8", "replace").strip()
            except Exception as e:
                salida = f"error: {e}"
            apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": f"mcp_{nombre}",
                     "resultado": salida[:120]})
            if nombre == "penpot":
                avisos.append(AVISO_PENPOT)
            if "NO INSTALADO" in salida:
                avisos.append(f"El MCP {nombre} no esta instalado en este equipo: trabaja sin el (lee los archivos como "
                              "siempre) y al final ofrecele al usuario instalarlo (una vez, ~50 MB, suma verificada): "
                              "<PYTHON> \"<NOVA_HOME>/antigravity/herramientas/codebase_memory/instalar.py\". "
                              "Lanzalo solo si te dice que si.")
            elif "recargado en caliente" in salida:
                avisos.append(f"Se ha ENCENDIDO el MCP {nombre} ({salida}). Si sus herramientas aun no te aparecen en esta "
                              "llamada, apareceran en la siguiente; si tampoco, dile al usuario que repita el pedido y PARA "
                              "(no investigues). Nunca pidas contraseñas en el chat. Se apaga solo al cerrar Antigravity.")
            elif "ya estaba" not in salida:
                # 09/11 P4: sin recarga en caliente Nova creia que las herramientas llegarian y se puso a investigar
                # (list_resources, leer archivos, docker ps -> abrio Docker; ~95k tokens) y acabo pidiendo la contraseña.
                avisos.append(f"Se ha ACTIVADO el MCP {nombre} en la configuracion, pero sus herramientas NO estaran hasta "
                              "reabrir Antigravity. Dile al usuario SOLO esto, en una linea: 'He activado " + nombre +
                              "; cierra y abre Antigravity y repite el pedido.' y PARA. No investigues (nada de docker, "
                              "puertos, archivos del MCP ni list_resources) y NUNCA pidas contraseñas en el chat.")
    return ("REGLA DE NOVA (MCP bajo demanda, la vigila un hook): " + " ".join(avisos)) if avisos else ""


# ---------------------------------------------------------------- pase de pago en Brave (09/11, Claude, a pedido del usuario)
# La extension v4 bloquea botones de pago/compra. Solo se desbloquea UN pago (10 min) si el usuario lo escribe/dice.
# lastUserInput es el mensaje real del usuario (una web o un adjunto no pueden escribirlo). La clave solo la tienen
# este hook y el puente; nova_hook.py impide que Nova la lea o llame a /pase_pago.
# Solo primera persona y afirmativo: "autorizo el pago", "te doy permiso para comprar", "tienes mi permiso para pagar".
# NO: "no autorizo el pago", "¿autorizaste el pago?", "la autorizacion del pago fallo", "nunca te permito comprar".
RE_AUTORIZA_PAGO = re.compile(r"(?i)(?<![\w¿?])(autorizo|te autorizo|te doy permiso|tienes (mi )?permiso|te permito)\b"
                              r"[^.?!\n]{0,40}?\b(pag(o|os|ar|a|ues)|compr(a|as|ar|e)|suscri\w*)\b")
RE_NIEGA_PAGO = re.compile(r"(?i)\b(no|nunca|jam[aá]s|ni)\s+(te\s+)?(autorizo|doy|tienes|permito)\b")
CLAVE_PASE = AQUI / ".pase_pago.clave"


def autoriza_pago(pedido: str) -> bool:
    """True solo si el usuario autoriza en afirmativo (la frase que lo dice no es pregunta ni negacion)."""
    for m in RE_AUTORIZA_PAGO.finditer(pedido):
        ini = max(pedido.rfind(c, 0, m.start()) for c in ".!?\n¿¡") + 1  # inicio de esa frase
        fin = min([i for i in (pedido.find(c, m.end()) for c in ".!?\n") if i >= 0] or [len(pedido)])
        frase = pedido[ini:fin + 1]
        if "?" in frase or "¿" in pedido[max(0, ini - 1):m.start()] or RE_NIEGA_PAGO.search(frase):
            continue
        return True
    return False


def pase_de_pago(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    pedido = RE_ADJUNTO_LOCAL.sub("", str(datos.get("lastUserInput") or ""))
    if not autoriza_pago(pedido):
        return ""
    import urllib.request
    try:
        clave = CLAVE_PASE.read_text(encoding="utf-8").strip()
        req = urllib.request.Request("http://127.0.0.1:5005/pase_pago", method="POST",
                                     data=json.dumps({"minutos": 10, "motivo": pedido[:200]}).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "X-Nova-Clave": clave})
        with urllib.request.urlopen(req, timeout=8) as r:
            ok = json.loads(r.read()).get("ok")
    except Exception as e:
        ok = False
        apuntar({"evento": "PreInvocation", "decision": "pase_pago_error", "error": f"{type(e).__name__}: {e}"[:160]})
    apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": "pase_pago", "ok": bool(ok)})
    if not ok:
        return ("REGLA DE NOVA (pagos): el usuario quiere autorizar un pago, pero el puente de Brave no respondio (¿Brave cerrado "
                "o la extension sin conectar?). Diselo; no intentes pagar.")
    return ("REGLA DE NOVA (pagos, la vigila un hook): el usuario ha AUTORIZADO UN SOLO PAGO en Brave durante 10 minutos. "
            "Antes de pulsar el boton final dile en una frase que vas a pagar (que, cuanto, donde). Tras ese pago el "
            "permiso se gasta solo. Los numeros de tarjeta y contraseñas NO los escribes nunca: los pone el usuario o el "
            "autocompletado de Brave.")


# ---------------------------------------------------------------- guardian de tokens en el chat (Ley 16, 09/11 Claude)
# Flujo del usuario: al pasar de 100k -> copia del chat al .txt de memory\chat_logs (con la fecha del chat) y aviso
# "escribe /compact" (hasta 5 compactaciones); con 5 hechas -> "salta de ventana" (el puente queda listo y en la
# ventana nueva basta con "seguimos"). El guardian de memoria (nova_buffer_guardian.py) hace la copia y el aviso por
# voz; este hook pone el aviso DENTRO del chat (antes solo salia si Nova usaba una herramienta, y como un clic).
# 20/11 noche (Claude, el usuario: "nunca me salio el compact"): Antigravity COMPACTA SOLO hacia los ~100k (paso CHECKPOINT).
# Con el tope en 100k el aviso entraba el mismo segundo que la compactacion automatica y nunca se veia.
# Ahora se avisa ANTES (80k y 90k) y, si Antigravity compacto solo, se dice cuantas van.
# 23/11 (Claude, el usuario: "me salta a cada rato y me estresa"): los modelos nuevos compactan solos y el contexto pasa de
# 200k (una conversacion iba por 202k con 12 avisos). Ahora: MAXIMO 3 avisos por conversacion, a 200k, 350k y 500k.
# Las compactaciones automaticas solo se apuntan en el chat (sin voz) y a la 5a se sugiere ventana nueva.
AVISOS_BUFER = (200_000, 350_000, 500_000)
TOPE_BUFER = AVISOS_BUFER[0]
GUARDIAN = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_buffer_guardian.py"
CHAT_LOGS = Path.home() / ".gemini" / "antigravity" / "memory" / "chat_logs"


def medir_bufer(transcript: str) -> tuple[int, int]:
    """(contexto actual = entrada+cache de la ultima llamada, compactaciones hechas = pasos CHECKPOINT)."""
    contexto = compactaciones = 0
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if "CHECKPOINT" not in linea and "PLANNER_RESPONSE" not in linea:
                    continue
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                if o.get("type") == "CHECKPOINT":
                    compactaciones += 1
                    contexto = 0
                elif o.get("type") == "PLANNER_RESPONSE":
                    t = (o.get("input_tokens") or 0) + (o.get("cache_read_tokens") or 0)
                    if t:
                        contexto = t
    except OSError:
        pass
    return contexto, compactaciones


# 22/11 (Claude, N8): medido en chat_logs, Flash solo escribia la linea del bufer en 24 de 45 avisos (~53 %).
# Ahora el aviso deja la linea PENDIENTE y el Stop comprueba que salio en la respuesta: si no, 1 "continue" pidiendo
# SOLO la linea; si tampoco, se apunta y se suelta (nunca un bucle). El guardian ya avisa con Marina en paralelo.
RE_LINEA_BUFER = re.compile(r"\[(BUFER EN \d+k|COMPACTACION AUTOMATICA \d/5|LIMITE DE SESION)")


def pendiente_bufer(conv: str, linea: str) -> None:
    estado = leer_estado()
    estado[f"bufer_pend:{conv}"] = {"linea": linea, "insistido": False}
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass


def revisar_bufer(datos: dict, texto_turno: str) -> dict:
    conv = str(datos.get("conversationId", ""))
    estado = leer_estado()
    clave = f"bufer_pend:{conv}"
    pend = estado.get(clave)
    if not pend:
        return {}
    if RE_LINEA_BUFER.search(texto_turno):
        estado.pop(clave, None)
        decision, salida = "bufer_ok", {}
    elif not pend.get("insistido"):
        pend["insistido"] = True
        estado[clave] = pend
        decision = "bufer_continue"
        salida = {"decision": "continue", "reason": (
            "[HOOK NOVA] Te faltó la linea del bufer (Ley 16). Sin repetir nada de lo anterior, responde SOLO con esta "
            f"linea, tal cual: {pend.get('linea')}")}
    else:
        estado.pop(clave, None)
        decision, salida = "bufer_no_escrita", {}
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": decision})
    return salida


def aviso_bufer(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:  # una vez por mensaje del usuario
        return ""
    transcript = str(datos.get("transcriptPath") or "")
    if not transcript or not Path(transcript).exists():
        return ""
    contexto, hechas = medir_bufer(transcript)
    conv = str(datos.get("conversationId", ""))
    estado = leer_estado()
    clave = f"bufer:{conv}"
    previo = estado.get(clave) or {}
    avisados = list(previo.get("avisados") or [])
    if hechas > int(previo.get("hechas") or 0):
        # Antigravity compacto solo desde el ultimo mensaje: decirselo al usuario con el contador
        estado[clave] = {"hechas": hechas, "tokens": contexto, "avisados": avisados}
        try:
            ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
        except OSError:
            pass
        apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "aviso_compactacion_auto",
                 "contexto": contexto, "compactaciones": hechas})
        if hechas >= 5:
            linea = (f"[COMPACTACION AUTOMATICA {hechas}/5 | Limite de sesion | Abre una ventana nueva y escribe "
                     "\"seguimos\"]")
        else:
            linea = f"[COMPACTACION AUTOMATICA {hechas}/5 | Bufer en {contexto // 1000}k | Antigravity resumio la conversacion]"
        pendiente_bufer(conv, linea)
        return ("AVISO DE BUFER (lo vigila un hook): Antigravity acaba de COMPACTAR esta conversacion el solo (perdiste "
                "el detalle de lo anterior; trabaja con el resumen). Responde al usuario con normalidad y EMPIEZA tu "
                f"respuesta con esta linea, tal cual: {linea}")
    if contexto < TOPE_BUFER:
        return ""
    # el umbral mas alto que ya se ha pasado; se avisa solo si no se aviso antes (max. 3 por conversacion)
    umbral = max(u for u in AVISOS_BUFER if contexto >= u)
    if umbral in avisados or len(avisados) >= len(AVISOS_BUFER):
        return ""
    avisados.append(umbral)
    estado[clave] = {"hechas": hechas, "tokens": contexto, "avisados": avisados}
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    # Antes de cada aviso: copia del chat al .txt (el guardian escribe chat_<fecha>_inicio-<HHmm>_conv-<id>.txt)
    import subprocess
    try:
        subprocess.run([sys.executable, str(GUARDIAN), "--silent"], capture_output=True, timeout=25, creationflags=SIN_VENTANA)
    except Exception:
        pass
    copia = next(iter(sorted(CHAT_LOGS.glob(f"chat_*_conv-{conv[:8]}.txt"))), None)
    donde = f"memory\\chat_logs\\{copia.name}" if copia else "memory\\chat_logs"
    k = contexto // 1000
    apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "aviso_bufer", "contexto": contexto, "compactaciones": hechas})
    if hechas >= 5:
        linea = (f"[LIMITE DE SESION 5/5 | Bufer en {k}k | Chat respaldado y puente guardado | Abre una ventana nueva y "
                 "escribe \"seguimos\"]")
        extra = "Ya se hicieron 5 compactaciones: NO ofrezcas /compact; toca saltar de ventana."
    else:
        n = len(avisados)
        consejo = {1: "Si vas a seguir mucho, /compact lo deja en ~17k", 2: "Cada mensaje ya cuesta mucho cupo: /compact o ventana nueva",
                   3: "Ultimo aviso: mejor ventana nueva (escribe \"seguimos\")"}.get(n, "")
        linea = f"[BUFER EN {k}k | Aviso {n}/3 | Chat respaldado | Compactaciones {hechas}] {consejo}."
        extra = "No hay mas avisos de bufer despues de este." if n >= 3 else f"Quedan {3 - n} avisos como maximo."
    pendiente_bufer(conv, linea)
    return (f"AVISO DE BUFER (Ley 16, lo vigila un hook): el contexto va por {k}k tokens. La copia del chat "
            f"esta en {donde}. {extra} Responde al usuario con normalidad y TERMINA tu respuesta con esta linea, tal "
            f"cual: {linea}")


# ---------------------------------------------------------------- aprendizaje automatico SIN ruido (Ley 3, 09/11 Claude)
# Antes dependia de que Nova se acordara (skill con trigger model_decision): desde el 08/11 no apunto nada.
# Solo cuando hay SEÑAL (el usuario corrige o el turno anterior tuvo 2+ comandos fallidos) se le pide UNA linea.
RE_CORRIGE = re.compile(
    r"(?i)\b(te equivocaste|te has equivocado|est[aá] mal|lo hiciste mal|eso no (es|era)|no era eso|no es as[ií]|"
    r"otra vez (lo mismo|igual|mal)|sigue (igual|sin|fallando)|no funciona|no sirve|fallaste|no (me )?(hiciste|haces|hace) caso|"
    r"te dije que|ya te dije|error tuyo|mal hecho|corr[ií]gelo|no hagas eso|por qu[eé] hiciste)\b")
INBOX = r"<NOVA_HOME>\antigravity\memory\inbox_lecciones.md"
# 23/11 (Claude, el usuario: "una sola entrada"): quejas del usuario, lecciones de Nova y correcciones de Claude van al MISMO
# inbox con un tema fijo (los de los carriles). El /destilar las pasa a memory\aprendido.jsonl y nova_aprendido.py kits
# las pone en el bloque "Errores que ya cometiste" de cada kit, que es lo que Nova lee antes de trabajar.
FORMATO_LECCION = ("`- [AAAA-MM-DD] [tema] (de: {de}) cuando ... -> hacer en su lugar` (tema SOLO uno de: web, backend, "
                   "consola, redaccion, investigacion, video, rea, nova)")


def fallos_turno_anterior(transcript: str) -> int:
    """Comandos fallidos entre el penultimo y el ultimo mensaje del usuario."""
    turnos: list[int] = [0]
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if '"USER_INPUT"' in linea:
                    turnos.append(0)
                elif '"GENERIC"' in linea:
                    m = re.search(r"exited with code (-?\d+)", linea)
                    if (m and m.group(1) != "0") or '"status": "ERROR"' in linea or '"status":"ERROR"' in linea:
                        turnos[-1] += 1
    except OSError:
        return 0
    return turnos[-2] if len(turnos) >= 2 else 0  # el ultimo bloque es el turno que empieza ahora


def fallos_turno_actual(transcript: str) -> tuple[int, int]:
    """(numero de mensaje del usuario, comandos fallidos desde ese mensaje). 20/11: para la piramide."""
    turno, fallos = 0, 0
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if '"USER_INPUT"' in linea:
                    turno, fallos = turno + 1, 0
                elif '"GENERIC"' in linea:
                    m = re.search(r"exited with code (-?\d+)", linea)
                    if (m and m.group(1) != "0") or '"status": "ERROR"' in linea or '"status":"ERROR"' in linea:
                        fallos += 1
    except OSError:
        pass
    return turno, fallos


def aviso_asesor(datos: dict) -> str:
    """20/11 (Claude, piramide del usuario): a mitad de turno, si ya van 2 fallos desde el ultimo mensaje del usuario,
    Nova PARA de probar a ciegas y le pregunta si consulta al asesor (Hydrogen xhigh). Una vez por mensaje."""
    if int(datos.get("invocationNum") or 0) == 0:
        return ""
    transcript = str(datos.get("transcriptPath") or "")
    if not transcript or not Path(transcript).exists():
        return ""
    turno, fallos = fallos_turno_actual(transcript)
    # 20/11 noche: turno 0 = conversacion sin mensajes del usuario = un SUBAGENTE (p. ej. el propio asesor).
    # En prueba real le salto al asesor "pregunta al asesor"; el aviso es solo para la Nova principal.
    if turno == 0 or fallos < 2:
        return ""
    conv = str(datos.get("conversationId", ""))
    estado = leer_estado()
    clave = f"asesor:{conv}:{turno}"
    if estado.get(clave):
        return ""
    estado[clave] = True
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-200:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "aviso_asesor", "fallos": fallos})
    return ("PIRAMIDE (lo vigila un hook): llevas 2 fallos desde el ultimo mensaje del usuario. NO sigas probando a "
            "ciegas. En una frase dile que fallo y preguntale: '?Consulto al asesor (modelo mas fuerte, solo lectura, "
            "~50-70k del cupo Gemini)?'. Si dice que si: invoke_subagent con TypeName 'asesor' y una pregunta concreta "
            "(que intentabas, el error exacto, que archivos mirar). Si ya consultaste al asesor en esta conversacion, "
            "usa send_message al MISMO asesor. Si el asesor tampoco lo saca: propon una consulta de ventana con "
            "nova_consulta.py (Carbon -> Neon -> Opus -> Claude).")


def aviso_leccion(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    pedido = RE_ADJUNTO_LOCAL.sub("", str(datos.get("lastUserInput") or ""))
    transcript = str(datos.get("transcriptPath") or "")
    corrige = bool(RE_CORRIGE.search(pedido))
    fallos = fallos_turno_anterior(transcript) if transcript and Path(transcript).exists() else 0
    if not corrige and fallos < 2:
        return ""
    motivo = "el usuario te esta corrigiendo" if corrige else f"en tu turno anterior fallaron {fallos} comandos"
    conv = str(datos.get("conversationId", ""))
    apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "pedir_leccion",
             "corrige": corrige, "fallos": fallos})
    # 09/11 tarde: el Stop comprueba que el inbox cambio (Nova Flash Low ignoraba el aviso)
    estado = leer_estado()
    estado[f"leccion:{conv}"] = {"firma": firma_inbox(), "motivo": motivo, "pedido": pedido[:300], "insistido": False}
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    return (f"APRENDIZAJE (Ley 3, lo vigila un hook): {motivo}. Primero resuelve lo que pide. Al final, SOLO si aprendiste "
            f"algo nuevo y reutilizable (no si fue un fallo de red o un servicio caido), anade UNA linea al final de {INBOX} "
            "con run_command (Add-Content -Encoding utf8) con este formato exacto: "
            + FORMATO_LECCION.format(de="usuario" if corrige else "nova") + " y termina con '(leccion apuntada)'. "
            "Si NO hay nada que aprender, termina tu respuesta con '(sin leccion)'. Un hook comprueba que hiciste una de las dos.")


INBOX_REAL = Path.home() / ".gemini" / "antigravity" / "memory" / "inbox_lecciones.md"
RE_SIN_LECCION = re.compile(r"(?i)\(\s*sin lecci[oó]n\s*\)")


def firma_inbox() -> list:
    try:
        st = INBOX_REAL.stat()
        return [st.st_size, st.st_mtime_ns]
    except OSError:
        return [0, 0]


def aviso_destilar(datos: dict) -> str:
    """23/11 (Claude): el /destilar estuvo sin hacerse 16 dias (73 lecciones atascadas que Nova nunca releia). Si el inbox
    pasa de 15 lecciones, UNA vez al dia se le dice al usuario que toca destilar con Claude."""
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    try:
        import nova_aprendido

        n = nova_aprendido.pendientes_inbox()
        if n < nova_aprendido.AVISO_INBOX:
            return ""
    except Exception:
        return ""
    estado = leer_estado()
    hoy = time.strftime("%Y-%m-%d")
    if estado.get("destilar_avisado") == hoy:
        return ""
    estado["destilar_avisado"] = hoy
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": "aviso_destilar",
             "inbox": n})
    return (f"AVISO DE APRENDIZAJE (lo vigila un hook): hay {n} lecciones en el inbox sin destilar. Al final de tu "
            f"respuesta anade UNA linea para el usuario: 'Hay {n} lecciones sin destilar: pidele a Claude /destilar'.")


def revisar_leccion(datos: dict, texto_turno: str) -> dict:
    """Stop: si se pidio leccion y el inbox no cambio ni Nova dijo '(sin leccion)': 1a vez -> continue para que la apunte;
    2a vez -> el hook apunta una linea en bruto (marcada para revisar) para no perder la correccion."""
    conv = str(datos.get("conversationId", ""))
    estado = leer_estado()
    clave = f"leccion:{conv}"
    pend = estado.get(clave)
    if not pend:
        return {}
    hecho = firma_inbox() != pend.get("firma") or RE_SIN_LECCION.search(texto_turno)
    if hecho:
        estado.pop(clave, None)
        decision = "leccion_ok"
        salida: dict = {}
    elif not pend.get("insistido"):
        pend["insistido"] = True
        decision = "leccion_continue"
        salida = {"decision": "continue", "reason": (
            "[HOOK NOVA] Te pidieron apuntar una leccion (Ley 3) y el inbox no ha cambiado. Ahora, sin repetir el trabajo: "
            f"si aprendiste algo, anade UNA linea a {INBOX} con run_command (Add-Content -Encoding utf8), formato "
            + FORMATO_LECCION.format(de="usuario o nova") + ", y responde solo '(leccion apuntada)'. "
            "Si no hay nada que aprender, responde solo '(sin leccion)'.")}
    else:
        estado.pop(clave, None)
        decision = "leccion_en_bruto"
        salida = {}
        bruto = re.sub(r"\s+", " ", str(pend.get("pedido") or "")).strip()[:200]
        try:
            with INBOX_REAL.open("a", encoding="utf-8") as f:
                f.write(f"- [{time.strftime('%Y-%m-%d')}] [nova] (de: usuario) REVISAR {pend.get('motivo')}: \"{bruto}\" -> "
                        "PENDIENTE: Nova no apunto la leccion; se mira en el /destilar\n")
        except OSError as e:
            decision = f"leccion_en_bruto_error: {e}"
    if clave in estado:
        estado[clave] = pend
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": decision})
    return salida


# 09/11 tarde (Claude, a pedido del usuario): nova_hook.py BLOQUEA webs de >150 lineas escritas desde la nube salvo que
# el usuario lo autorice en SU mensaje ("escribelo tu", "hazlo tu"). Este hook ve el mensaje; nova_hook.py no. Se apunta
# aqui (por conversacion, se renueva con cada mensaje del usuario) y nova_hook.py lo lee.
AUTORIZA_CODIGO = AQUI / ".autoriza_codigo.json"
RE_AUTORIZA_WEB = re.compile(r"(?i)\b(escr[ií]be(lo|la|melo|mela)|hazlo|hazla|hazmela|h[aá]zmelo)\s+t[uú]\b|\b(tienes\s+permiso|luz\s+verde|haz\s+los\s+cambios|s[uú]belo|ed[ií]talo|haz\s+(el\s+)?(commit|push)|sube\s+a\s+github)\b")
# 09/11 (regla del usuario): por defecto webs minimalistas con la biblioteca (0 nube); si da una WEB DE REFERENCIA, la nube
# puede escribirla ("no queda de otra"): un enlace + una palabra de referencia en SU mensaje.
RE_REFERENCIA_WEB = re.compile(r"(?i)https?://\S+|www\.\S+")
RE_PALABRA_REFERENCIA = re.compile(r"(?i)\b(referencia|parecid[ao]|como (esta|esa|la de)|igual que|estilo de|inspir[aá]te|"
                                   r"inspirad[ao]|basad[ao] en|tipo esta|al estilo)\b")


# 22/11 (Claude, el usuario: "si le doy permiso explicito, que pueda editar, incluida la zona protegida"). Solo afirmativo y
# en primera persona: "te doy permiso", "tienes mi permiso", "te autorizo", "luz verde", "desbloquealo".
# NO: "no te doy permiso", "¿te di permiso?", "autorizo el pago" (eso es el pase de pago, aparte).
RE_PERMISO_PROT = re.compile(r"(?i)(?<![\w¿?])(te\s+doy\s+(el\s+|mi\s+)?permiso|tienes\s+(mi\s+|el\s+)?permiso|"
                             r"te\s+autorizo|autorizo|permiso\s+(concedido|expl[ií]cito)|luz\s+verde|"
                             r"desbloqu[eé]a(lo|la|te)?|puedes\s+editar(lo|la)?|"
                             # 22/11 (el usuario: "cuando pongo encargate tu o hazlo tu, que tambien se desbloquee si la
                             # tarea lo necesita"): delegar la tarea entera tambien es permiso explicito
                             r"enc[aá]rgate(\s+t[uú])?|h[aá]z(lo|la|melo|mela)\s+t[uú])\b")
RE_NIEGA_PROT = re.compile(r"(?i)\b(no|nunca|jam[aá]s|ni|sin)\s+(te\s+)?(doy|tienes|autorizo|permiso|luz|desbloque|puedes)")
RE_ES_PAGO = re.compile(r"(?i)\b(pag(o|os|ar|a|ues)|compr(a|as|ar|e)|suscri\w*)\b")


def permiso_protegido(msg: str) -> bool:
    """True si el usuario da permiso explicito (afirmativo, no pregunta ni negacion, no es un pago)."""
    for m in RE_PERMISO_PROT.finditer(msg):
        ini = max(msg.rfind(c, 0, m.start()) for c in ".!?\n¿¡") + 1
        fin = min([i for i in (msg.find(c, m.end()) for c in ".!?\n") if i >= 0] or [len(msg)])
        frase = msg[ini:fin + 1]
        if "?" in frase or "¿" in msg[max(0, ini - 1):m.start()] or RE_NIEGA_PROT.search(frase) or RE_ES_PAGO.search(frase):
            continue
        return True
    return False


MSG_PERMISO = ("PERMISO DEL USUARIO (lo vigila un hook): en ESTE mensaje te autoriza a editar la zona protegida (skills, "
               "config, scripts del Doctor/sync) sin preguntar; el hook guarda copia antes en respaldos_nova. Los hooks, "
               "hooks.json y GEMINI.md los confirma el con un clic (GEMINI.md tiene tope de 23.784 caracteres: no lo "
               "pases). Ni con permiso: estados de los hooks, claves/cofre, copias de seguridad y nova_env. El permiso "
               "acaba con su siguiente mensaje: haz SOLO lo que te ha pedido.")


def apuntar_autorizacion(datos: dict) -> None:
    if int(datos.get("invocationNum") or 0) != 0:
        return
    conv = str(datos.get("conversationId") or "")
    if not conv:
        return
    try:
        estado = json.loads(AUTORIZA_CODIGO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        estado = {}
    msg = RE_ADJUNTO_LOCAL.sub("", str(datos.get("lastUserInput") or ""))
    estado[conv] = bool(RE_AUTORIZA_WEB.search(msg) or (RE_REFERENCIA_WEB.search(msg) and RE_PALABRA_REFERENCIA.search(msg)))
    # 22/11: permiso para la zona protegida (lo lee nova_hook.py: permiso_usuario). Se renueva con cada mensaje.
    estado.pop("protegido:" + conv, None)
    if permiso_protegido(msg):
        estado["protegido:" + conv] = time.time()
    try:
        AUTORIZA_CODIGO.write_text(json.dumps(dict(list(estado.items())[-100:])), encoding="utf-8")
    except OSError:
        pass


# ------------------------------------------------------------------------------------------------------------------
# 17/11 (Claude, decision del usuario): NIVELES DE AUTONOMIA, que se cambian HABLANDO (nada de PowerShell).
#   CHARLA ......... por defecto: lee y trabaja en scratch; crear/modificar fuera o borrar -> se pregunta.
#   ENCARGO ........ le das un trabajo (voz [voz], "encargate", "hazlo tu", "crea/hazme/arregla..."): trabaja SOLA en
#                    su zona (scratch, documentos_generados, proyectos, las carpetas que nombres en tu mensaje) y
#                    puede mejorar SUS HERRAMIENTAS (con copia automatica). Borrar o salir de la zona -> pregunta.
#   TOTAL .......... "Nova, permiso total (N horas/minutos)": todo sin preguntar hasta que acabe el tiempo, salvo
#                    BORRAR (siempre pregunta), claves, pagos y el ZONA BLINDADA (hooks/config/Doctor: nunca).
#   "Nova, para" / "modo charla" vuelve a CHARLA. El estado vive en .nova_modo.json y lo lee nova_hook.py.
# ------------------------------------------------------------------------------------------------------------------
MODO_NOVA = AQUI / ".nova_modo.json"
RE_MODO_TOTAL = re.compile(r"(?i)\b(permiso|confianza|control)\s+total\b")
RE_TIEMPO = re.compile(r"(?i)(\d+|una|un|media)\s*(h|hora|horas|min|minuto|minutos)\b")
RE_MODO_CHARLA = re.compile(r"(?i)\b(nova,?\s+para\b|para\s+nova\b|modo\s+charla|quita(r|le)?\s+(el\s+)?permiso|"
                            r"sin\s+permisos|ya\s+no\s+tienes\s+permiso)")
RE_MODO_ENCARGO = re.compile(
    r"(?i)^\s*\[voz\]|\b(enc[aá]rgate|modo\s+encargo|h[aá]zlo\s+t[uú]|h[aá]zmelo|tienes\s+(mi\s+)?permiso|luz\s+verde|"
    r"trabaja\s+en|en\s+la\s+carpeta|bajo\s+mi\s+responsabilidad)\b|"
    r"^\s*(nova,?\s+)?(crea|cr[eé]ame|haz|hazme|monta|m[oó]ntame|genera|prepara|pr[eé]parame|arregla|modifica|edita|"
    r"mueve|organiza|instala|actualiza|sube|programa|dise[nñ]a|redacta|termina|contin[uú]a|sigue)\b")
RE_RUTA_MENSAJE = re.compile(
    r'"([A-Za-z]:\\[^"]+)"|\'([A-Za-z]:\\[^\']+)\'|(?<![\w"\'])([A-Za-z]:\\[^\s"\'<>|,;]+)'
    # v3.3 macOS/Linux: /Users/..., /home/..., ~/...
    r'|"((?:/|~/)[^"]+)"|\'((?:/|~/)[^\']+)\'|(?<![\w"\'/.:])((?:/(?:Users|home|Volumes|mnt|media)/|~/)[^\s"\'<>|,;]+)')


def _tiempo_total(msg: str) -> float:
    m = RE_TIEMPO.search(msg)
    if not m:
        return 3600.0  # por defecto, una hora
    n = {"una": 1, "un": 1, "media": 0.5}.get(m.group(1).lower(), None)
    n = float(n if n is not None else m.group(1))
    return n * (60 if m.group(2).lower().startswith("m") else 3600)


def carpetas_del_mensaje(msg: str) -> list[str]:
    """Rutas de carpeta que el usuario escribe en su mensaje: pasan a ser zona del encargo."""
    zonas = []
    for m in RE_RUTA_MENSAJE.finditer(msg):
        r = Path(next(g for g in m.groups() if g).rstrip(".\\/")).expanduser()
        d = r if r.is_dir() else (r.parent if r.parent.is_dir() else None)
        if d is not None and len(str(d)) > 3:
            zonas.append(str(d))
    return zonas


def actualizar_modo(datos: dict) -> dict:
    """Con cada mensaje NUEVO del usuario: decide el modo de la conversacion y lo guarda. Devuelve el estado."""
    conv = str(datos.get("conversationId") or "")
    try:
        todo = json.loads(MODO_NOVA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        todo = {}
    e = todo.get(conv) or {"modo": "charla", "zonas": [], "total_hasta": 0}
    if e.get("modo") == "total" and time.time() > float(e.get("total_hasta") or 0):
        e["modo"] = "encargo"  # se acabo el tiempo de confianza total: sigue el encargo, ya sin carta blanca
    if conv and int(datos.get("invocationNum") or 0) == 0:
        msg = RE_ADJUNTO_LOCAL.sub("", str(datos.get("lastUserInput") or ""))
        if RE_MODO_CHARLA.search(msg):
            e = {"modo": "charla", "zonas": [], "total_hasta": 0}
        elif RE_MODO_TOTAL.search(msg):
            e["modo"], e["total_hasta"] = "total", time.time() + _tiempo_total(msg)
        elif RE_MODO_ENCARGO.search(msg) and e.get("modo") != "total":
            e["modo"] = "encargo"
        nuevas = carpetas_del_mensaje(msg)
        if nuevas:
            e["zonas"] = list(dict.fromkeys(list(e.get("zonas") or []) + nuevas))[-10:]
            if e.get("modo") == "charla":
                e["modo"] = "encargo"  # darle una carpeta para trabajar ya es un encargo
        todo[conv] = e
        try:
            MODO_NOVA.write_text(json.dumps(dict(list(todo.items())[-100:]), ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return e


def aviso_modo(e: dict) -> str:
    """Una linea al empezar cada mensaje: Nova SABE que puede hacer sin chocarse con el hook."""
    zonas = "; ".join(e.get("zonas") or [])
    extra = f" + {zonas}" if zonas else ""
    freno = "Nunca toques los hooks, config\\ ni el Doctor (son tu zona blindada: el sistema lo impide)."
    if e.get("modo") == "total":
        hasta = time.strftime("%H:%M", time.localtime(float(e.get("total_hasta") or 0)))
        return (f"[MODO NOVA: CONFIANZA TOTAL hasta las {hasta}] el usuario te deja hacer TODO sin preguntar: crear, "
                f"modificar y mover en cualquier carpeta, y mejorar tus herramientas (se guarda copia sola). BORRAR "
                f"siempre lo pregunta el sistema. Claves y pagos, como siempre. {freno}")
    if e.get("modo") == "encargo":
        return (f"[MODO NOVA: ENCARGO] Trabajas SOLA, sin pedir permiso, dentro de tu zona: antigravity\\scripts, "
                f"herramientas, scratch, documentos_generados, proyectos, nova_core (menos los hooks){extra}. Puedes "
                f"crear, modificar y mover ahi, y mejorar tus herramientas (se guarda copia sola antes). BORRAR algo o "
                f"salir de la zona: el sistema se lo pregunta al usuario, no hace falta que lo pidas tu. {freno}")
    return ("[MODO NOVA: CHARLA] Puedes leer y trabajar en antigravity\\scratch y en la carpeta en la que el usuario "
            "abrio este chat (su proyecto). Crear o modificar fuera de ahi, o "
            "borrar, el sistema se lo pregunta al usuario. Si te pide un trabajo o te da una carpeta, pasas a ENCARGO "
            f"solo. {freno}")


DOCTOR_ESTADO = Path.home() / ".gemini" / "antigravity" / "memory" / "doctor_estado.json"
DOCTOR_PS = r"<NOVA_HOME>/antigravity/scripts/nova_doctor.py"


def aviso_doctor(datos: dict) -> str:
    """11/11 (Claude): si el Nova Doctor de ESTE equipo encontro fallos (Python de Nova, hooks, Ollama, voz, aduana...),
    se lo cuenta a Nova UNA vez por conversacion para que avise al usuario. Nova no repara nada a mano."""
    conv = str(datos.get("conversationId") or "")
    try:
        est = json.loads(DOCTOR_ESTADO.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
    if est.get("ok", True) or not conv or conv in (est.get("avisado") or []):
        return ""
    est["avisado"] = (list(est.get("avisado") or []) + [conv])[-50:]
    try:
        DOCTOR_ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "aviso_doctor"})
    fallos = "; ".join(str(f) for f in (est.get("fallos") or []))[:600]
    return (f"[NOVA DOCTOR {est.get('fecha', '')}] En este equipo hay fallos: {fallos}. Al empezar tu respuesta diselo a "
            "el usuario en UNA linea. NO intentes arreglarlo tu (nada de pip, copiar archivos a mano ni editar scripts): si quiere, "
            f"vuelve a pasar el Doctor con: <PYTHON> \"<NOVA_HOME>/antigravity/scripts/nova_doctor.py\" --reparar y le das su ultima linea. "
            "Si sigue fallando, ofrece /reportar-fallo.")


def aviso_informe_mensual() -> str:
    """v3.2: si el usuario dijo SI al informe al instalar, una vez al mes Nova se lo propone (nunca lo envia sola)."""
    mem = Path.home() / ".gemini" / "antigravity" / "memory"
    try:
        if not json.loads((mem / "perfil_usuario.json").read_text(encoding="utf-8-sig")).get("telemetry_opt_in"):
            return ""
    except (OSError, ValueError):
        return ""
    marca = mem / "informe_ultimo_aviso.txt"
    try:
        if not marca.exists():  # la primera vez solo se apunta la fecha: el primer aviso llega al mes de instalar
            marca.write_text(time.strftime("%Y-%m-%d"), encoding="utf-8")
            return ""
        if time.time() - marca.stat().st_mtime < 30 * 86400:
            return ""
        marca.write_text(time.strftime("%Y-%m-%d"), encoding="utf-8")
    except OSError:
        return ""
    return ("[INFORME MENSUAL] El usuario acepto ayudar a mejorar Nova. Al final de tu respuesta, en UNA linea, ofrecele "
            "preparar el informe del mes (/enviar-informe: solo lecciones, servilleta y tipos de error; el lo revisa antes). "
            "No lo prepares ni lo envies sin que diga que si.")


def aviso_actualizacion() -> str:
    """v3.2: Nova se mantiene al dia SOLA. Una vez al dia comprueba en segundo plano si hay parche (actualizar_nova.py
    --check) y, si lo hay, se lo ofrece al usuario (como mucho una vez cada 3 dias). Con su SI, ejecuta /actualizar-nova."""
    import subprocess
    ag = Path.home() / ".gemini" / "antigravity"
    mem = ag / "memory"
    estado = mem / "actualizacion_disponible.json"
    marca = mem / "actualizacion_ultimo_aviso.txt"
    act = ag / "scripts" / "actualizar_nova.py"
    doc = ag / "scripts" / "nova_doctor.py"

    def fondo(*args):
        subprocess.Popen([sys.executable, *args], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=SIN_VENTANA)
    try:
        # AUTOREPARACION (sin intervencion humana): actualizacion a medias (descargas fallidas, o el actualizador viejo
        # pidio "ejecutalo otra vez") -> se termina SOLA en segundo plano: el usuario ya dijo que si al empezarla.
        reciente = any(time.time() - b.stat().st_mtime < 86400 for b in (ag / "backups").glob("backup_previo_*")) \
            if (ag / "backups").exists() else False
        a_medias = mem / "actualizacion_a_medias.json"
        terminar = mem / "actualizacion_terminando.txt"
        if act.exists() and (a_medias.exists() or reciente and estado.exists() and json.loads(estado.read_text(encoding="utf-8")).get("hay")) \
                and not (terminar.exists() and time.time() - terminar.stat().st_mtime < 1800):
            terminar.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
            estado.unlink(missing_ok=True)
            fondo(str(act))
            return ("[ACTUALIZACION] Estoy terminando en segundo plano la actualizacion que empezo el usuario (descargas "
                    "pendientes y revision del Doctor). No hace falta que haga nada; diselo en UNA linea.")
        # MANTENIMIENTO DIARIO: Doctor reparando + comprobar si hay version nueva
        if (not estado.exists()) or time.time() - estado.stat().st_mtime > 86400:
            if act.exists():
                fondo(str(act), "--check")
            if doc.exists():
                fondo(str(doc), "--reparar")
            return ""
        d = json.loads(estado.read_text(encoding="utf-8"))
        if not d.get("hay") or (marca.exists() and time.time() - marca.stat().st_mtime < 3 * 86400):
            return ""
        marca.write_text(time.strftime("%Y-%m-%d"), encoding="utf-8")
    except (OSError, ValueError):
        return ""
    return (f"[ACTUALIZACION] Hay una version nueva de Nova (v{d.get('version')}, {d.get('archivos')} archivos). Al final de tu "
            "respuesta, en UNA linea, ofrecele actualizar. Si dice que si: /actualizar-nova (si dice 'ejecutalo otra vez', "
            "repitelo UNA vez) y despues el Doctor. Nunca sin su si.")


RE_ACEPTA_VOCES = re.compile(r"(?i)\bacepto\b.{0,40}\blicencia\b.{0,30}\bvoce?s?\b")
CONSENTIMIENTO_VOCES = AQUI / ".voces_licencia_usuario.json"


def consentimiento_voces(pedido: str) -> str:
    """v3.2: la licencia de las voces la acepta el USUARIO escribiendolo en el chat; el hook lo apunta (30 min) y solo
    entonces nova_hook.py deja lanzar el instalador del pack de voz con -Aceptado."""
    if not RE_ACEPTA_VOCES.search(pedido or ""):
        return ""
    try:
        CONSENTIMIENTO_VOCES.write_text(json.dumps({"fecha": time.time(), "texto": pedido[:200]}), encoding="utf-8")
    except OSError:
        return ""
    return ("[VOCES] El usuario ACEPTO la licencia de las voces (LICENCIA_VOCES.md) en este mensaje. Lanza el instalador "
            "del pack de voz con la aceptacion: Windows `powershell -ExecutionPolicy Bypass -File "
            "\"<NOVA_HOME>\\antigravity\\herramientas\\voz_clon\\instalar.ps1\" -Aceptado`; Mac/Linux "
            "`sh <NOVA_HOME>/antigravity/herramientas/voz_clon/instalar.sh --aceptado`. Avisale de que descarga varios GB.")


# ---------------------------------------------------------------- vigilante del orquestador (20/11 Claude)
# el usuario: "los orquestadores a libre albedrio, solo con un vigilante". Con Orchestrator (Neon/Argon) no se frena nada por
# gasto (lo quita nova_hook.py) ni hay aviso de bufer (el contexto crece por diseno: cada relevo reenvia la conversacion
# entera). A cambio: una linea de gasto en cada mensaje y un INFORME al acabar cada turno para ver donde fallo.
DIR_INFORMES_ORQ = Path.home() / ".gemini" / "antigravity" / "memory" / "registros" / "orquestador"


def medir_conv(transcript: str) -> dict:
    try:
        import nova_cupo

        return nova_cupo.medir(transcript)
    except Exception:
        return {}


def aviso_orquestador(datos: dict, r: dict) -> str:
    if not r.get("orquestador") or int(datos.get("invocationNum") or 0) != 0:
        return ""
    import nova_cupo

    linea = (f"[ORQUESTADOR | {r['real'] // 1000}k reales | {nova_cupo.linea_cupo(r)} del cupo semanal | "
             f"{r['relevos']} relevos | {r['revisiones']} revisiones de plan]")
    return ("VIGILANTE DEL ORQUESTADOR (lo pone un hook, no te frena): cada relevo entre el modelo que planifica y el que "
            "ejecuta reenvia la conversacion ENTERA sin cache. Trabaja con normalidad; si la tarea es corta o mediana, "
            "recomienda al usuario una ventana con Hydrogen (y consulta de ventana a Carbon/Neon solo si hace falta). "
            f"TERMINA tu respuesta con esta linea, tal cual: {linea}")


def informe_orquestador(datos: dict, r: dict) -> None:
    """Informe por conversacion en memory\\registros\\orquestador\\<fecha>_<conv>.md (se reescribe cada turno)."""
    if not r.get("orquestador"):
        return
    import nova_cupo

    conv = str(datos.get("conversationId", ""))
    DIR_INFORMES_ORQ.mkdir(parents=True, exist_ok=True)
    frenos = []
    try:
        with open(REGISTRO, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if f'"conv": "{conv[:8]}"' not in linea:
                    continue
                o = json.loads(linea)
                if o.get("decision") in ("deny", "force_ask") or o.get("error_hook"):
                    frenos.append(f"- {o.get('t', '')[11:]} `{o.get('herramienta', o.get('evento', ''))}` -> "
                                  f"{o.get('decision', 'error')}: {str(o.get('motivo') or o.get('error_hook') or o.get('ruta') or '')[:140]}")
    except (OSError, ValueError):
        pass
    filas = "\n".join(
        f"| `{m}` | {nova_cupo.familia(m)} x{nova_cupo.PESO.get(nova_cupo.familia(m), 1)} | {v['llamadas']} | "
        f"{v['nuevos'] // 1000}k | {int(v['real']) // 1000}k |"
        for m, v in sorted(r["por_modelo"].items(), key=lambda x: -x[1]["real"]))
    texto = (
        f"# Informe del orquestador · conversacion `{conv[:8]}`\n"
        f"*Actualizado {time.strftime('%Y-%m-%d %H:%M:%S')} (lo escribe nova_hook_turno.py al acabar cada turno)*\n\n"
        f"- **Gasto:** {r['real'] // 1000}k tokens reales · coste ponderado {r['ponderado'] // 1000}k · "
        f"**{nova_cupo.linea_cupo(r)} del cupo semanal**\n"
        f"- **Relevos entre modelos:** {r['relevos']} · **revisiones obligatorias del plan:** {r['revisiones']} · "
        f"**caches perdidas:** {r['caches_perdidas']} · llamadas al modelo: {r['llamadas']}\n"
        f"- Contexto en la ultima llamada: {r['contexto'] // 1000}k\n\n"
        "| Modelo | Cupo y peso | Llamadas | Nuevos | Reales |\n|---|---|---|---|---|\n"
        f"{filas}\n\n## Frenos y fallos del hook en esta conversacion\n"
        + ("\n".join(frenos[-40:]) if frenos else "- (ninguno)") + "\n\n"
        "## Para mejorar\n- Muchos relevos o revisiones con poco trabajo hecho = tarea demasiado pequena para el orquestador "
        "(mejor Hydrogen + consulta de ventana).\n- Caches perdidas altas = el contexto se reenvia entero: abrir ventana nueva "
        "con un dosier corto.\n")
    (DIR_INFORMES_ORQ / f"{time.strftime('%Y-%m-%d')}_{conv[:8]}.md").write_text(texto, encoding="utf-8")


# 24/11 (Claude, el usuario): MODO PRACTICAS. Si el chat trabaja en una carpeta practica_* / entregable_* (workspace o ruta
# en su mensaje), una vez por mensaje se le recuerda a Nova como trabajar ahi. El freno real esta en nova_hook.py
# (deny al escribir sin permiso); esto es para que explique bien en vez de chocar con el freno.
RE_PRACTICA = re.compile(r"(?i)[\\/](practicas?|entregables?)_[^\\/\"'\s]+")
MSG_PRACTICAS = (
    "MODO PRACTICAS (lo vigila un hook): esta carpeta es una practica de clase del usuario. Quiere APRENDER: explica "
    "paso a paso, propone el cambio con un fragmento corto y deja que lo escriba el. No escribes archivos de la "
    "practica salvo que diga 'hazlo tu' o 'te doy permiso' en su mensaje (el hook lo frena). Nivel del curso: respeta "
    "el estilo que ya tiene el proyecto (XML y Activities, Swing/WindowBuilder, JDBC...); nada de Compose, streams, "
    "records ni 'modernizar' si el proyecto no lo usa. Si te da permiso: solo el trozo necesario con edit_file.")


def aviso_practicas(datos: dict, pedido: str) -> str:
    rutas = [str(w) for w in (datos.get("workspacePaths") or [])]
    rutas.append(pedido)  # rutas pegadas en su mensaje (pueden llevar espacios: "G:\Mi unidad\...\practica_x")
    if not any(RE_PRACTICA.search(r.replace("/", "\\")) for r in rutas):
        return ""
    if permiso_protegido(RE_ADJUNTO_LOCAL.sub("", pedido)):
        apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8],
                 "decision": "practicas_con_permiso"})
        return ""
    apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": "aviso_practicas"})
    return MSG_PRACTICAS


# 25/11 (Claude, fase 2): AGENTS.md DEL PROYECTO (el estandar de la industria). Si la carpeta del chat tiene un
# AGENTS.md en su raiz, se le pasa a Nova una vez por mensaje (estructura, como compilar, reglas, que no tocar), sin
# depender de que lo lea. Maximo AGENTS_MAX caracteres (si es mas largo: el principio y que lo lea entero).
AGENTS_MAX = 3000


def aviso_agents(datos: dict) -> str:
    for w in datos.get("workspacePaths") or []:
        raiz = Path(str(w).replace("file:///", "").replace("%20", " "))
        f = raiz / "AGENTS.md"
        try:
            if not f.is_file():
                continue
            texto = f.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": "aviso_agents",
                 "ruta": str(f)[-80:]})
        corte = "" if len(texto) <= AGENTS_MAX else f"\n[... recortado: lee el resto en {f}]"
        return (f"AGENTS.md DEL PROYECTO ({f}): reglas de ESTE proyecto, mandan sobre las generales.\n"
                f"{texto[:AGENTS_MAX]}{corte}")
    return ""


def pre(datos: dict) -> dict:
    pedido = str(datos.get("lastUserInput") or "")
    apuntar_autorizacion(datos)
    pasos = []
    aviso_v = consentimiento_voces(pedido)
    if aviso_v:
        pasos.append({"ephemeralMessage": aviso_v})
    aviso_u = aviso_actualizacion()
    if aviso_u:
        pasos.append({"ephemeralMessage": aviso_u})
    aviso_i = aviso_informe_mensual()
    if aviso_i:
        pasos.append({"ephemeralMessage": aviso_i})
    modo = actualizar_modo(datos)
    if int(datos.get("invocationNum") or 0) == 0:  # una vez por mensaje del usuario (no en cada paso)
        pasos.append({"ephemeralMessage": aviso_modo(modo)})
        try:  # 25/11: AGENTS.md del proyecto
            aviso_ag = aviso_agents(datos)
            if aviso_ag:
                pasos.append({"ephemeralMessage": aviso_ag})
        except Exception as ex:
            apuntar({"evento": "PreInvocation", "error_agents": str(ex)[:200]})
        try:  # 24/11: modo practicas
            aviso_p = aviso_practicas(datos, pedido)
            if aviso_p:
                pasos.append({"ephemeralMessage": aviso_p})
        except Exception as ex:
            apuntar({"evento": "PreInvocation", "error_practicas": str(ex)[:200]})
        if permiso_protegido(RE_ADJUNTO_LOCAL.sub("", pedido)):  # 22/11: permiso explicito del usuario
            pasos.append({"ephemeralMessage": MSG_PERMISO})
        try:  # 23/11: "¿seguro?" / "/verifica" -> investigar ANTES de responder (nova_verificacion.py)
            import nova_verificacion

            if nova_verificacion.RE_VERIFICA.search(RE_ADJUNTO_LOCAL.sub("", pedido)):
                pasos.append({"ephemeralMessage": nova_verificacion.MSG_PRE_VERIFICA})
                apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8],
                         "decision": "pide_verificar"})
        except Exception as ex:
            apuntar({"evento": "PreInvocation", "error_verificacion": str(ex)[:200]})
        try:  # 20/11: carriles por tema (nova_carriles.py): el codigo decide que kit de skills leer, no Flash
            import nova_carriles

            aviso_c = nova_carriles.mensaje_turno(str(datos.get("conversationId", "")), pedido,
                                                  str(datos.get("transcriptPath") or ""))
            if aviso_c:
                pasos.append({"ephemeralMessage": aviso_c})
                apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8],
                         "decision": "carril", "carriles": nova_carriles.leer_estado().get(
                             str(datos.get("conversationId", "")), {}).get("activos", [])})
        except Exception as ex:
            apuntar({"evento": "PreInvocation", "error_carriles": str(ex)[:200]})
    aviso_a = aviso_asesor(datos)
    if aviso_a:
        pasos.append({"ephemeralMessage": aviso_a})
    aviso_d = aviso_doctor(datos)
    if aviso_d:
        pasos.append({"ephemeralMessage": aviso_d})
    aviso_l = aviso_leccion(datos)
    if aviso_l:
        pasos.append({"ephemeralMessage": aviso_l})
    aviso_dest = aviso_destilar(datos)
    if aviso_dest:
        pasos.append({"ephemeralMessage": aviso_dest})
    transcript_p = str(datos.get("transcriptPath") or "")
    r_conv = medir_conv(transcript_p) if transcript_p and Path(transcript_p).exists() else {}
    if r_conv.get("orquestador"):  # 20/11: con orquestador, vigilante en vez de aviso de bufer
        aviso_o = aviso_orquestador(datos, r_conv)
        if aviso_o:
            pasos.append({"ephemeralMessage": aviso_o})
    else:
        aviso_b = aviso_bufer(datos)
        if aviso_b:
            pasos.append({"ephemeralMessage": aviso_b})
    aviso_pago = pase_de_pago(datos)
    if aviso_pago:
        pasos.append({"ephemeralMessage": aviso_pago})
    aviso_mcp = interruptor_mcp(datos)
    if aviso_mcp:
        pasos.append({"ephemeralMessage": aviso_mcp})
    aviso = aviso_adjuntos(datos)
    if aviso:
        pasos.append({"ephemeralMessage": aviso})
    if (int(datos.get("invocationNum") or 0) == 0 and RE_PIDE_CODIGO.search(pedido)
            and not RE_AUTORIZA.search(pedido)):
        apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": "recordatorio_codigo"})
        pasos.append({"ephemeralMessage": RECORDATORIO})
    return {"injectSteps": pasos} if pasos else {}


FIN_TURNO_VOZ = Path.home() / ".gemini" / "antigravity" / "voice_cache" / "nova_turno_fin.json"


def avisar_voz(datos: dict) -> None:
    """17/11 (Claude): senal de FIN DE TURNO para Nova Voz Live (aviso al instante, sin leer la pantalla).
    Tambien anota si este hook recibe las variables de agentapi (solo SI/NO, nunca los valores)."""
    try:
        texto = ""
        transcript = datos.get("transcriptPath") or ""
        if transcript and Path(transcript).exists():
            texto = respuestas_del_turno(transcript)[1]
        voz = re.findall(r"(?m)^\s*VOZ:\s*(.+)$", texto)
        FIN_TURNO_VOZ.parent.mkdir(parents=True, exist_ok=True)
        FIN_TURNO_VOZ.write_text(json.dumps({
            "hora": time.time(),
            "conversationId": str(datos.get("conversationId", "")),
            "terminationReason": str(datos.get("terminationReason", "")),
            "fullyIdle": datos.get("fullyIdle"),  # False = sigue una tarea en segundo plano: NO ha terminado
            "voz": voz[-1].strip() if voz else "",
            "texto": texto[-1500:],
        }, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # el aviso de voz nunca rompe el hook


def revisar_autonomia(datos: dict) -> dict:
    """22/11 (Claude, el usuario: "que busque solucion y no excusas"): si Nova cierra el turno con una excusa sin haberlo
    intentado (nova_autonomia.py decide), 1 "continue" para que pruebe 2 soluciones. Una vez por mensaje del usuario."""
    transcript = str(datos.get("transcriptPath") or "")
    conv = str(datos.get("conversationId", ""))
    try:
        import nova_autonomia

        info = nova_autonomia.analizar_turno(transcript)
        tipo, frase = nova_autonomia.decidir(info, str(datos.get("lastUserInput") or ""))
    except Exception as ex:  # el freno nunca rompe el hook
        apuntar({"evento": "Stop", "conv": conv[:8], "error_autonomia": str(ex)[:200]})
        return {}
    if not tipo:
        if frase:  # paso sin frenar por una excepcion (bloqueo real, permiso, practica...): queda apuntado
            apuntar({"evento": "Stop", "conv": conv[:8], "decision": "autonomia_" + frase})
        return {}
    estado = leer_estado()
    clave = f"autonomia:{conv}:{info.get('id')}"
    # 22/11 noche: "pide_confirmacion" (en un encargo cierra cada paso con "dime sigue") puede seguir hasta MAX_SIGUE veces
    # por mensaje del usuario (cada vez avanza un paso); las excusas, 1 vez. Nunca un bucle infinito.
    tope = nova_autonomia.MAX_SIGUE if tipo == "pide_confirmacion" else 1
    hechas = estado.get(clave) or 0
    hechas = 1 if hechas is True else int(hechas)
    if hechas >= tope:  # ya se le insistio lo maximo en este mensaje del usuario: se suelta
        apuntar({"evento": "Stop", "conv": conv[:8], "decision": "autonomia_soltada", "tipo": tipo, "frase": frase[:150]})
        return {}
    estado[clave] = hechas + 1
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": "autonomia_continue", "tipo": tipo, "frase": frase[:150],
             "llamadas": info.get("llamadas"), "fallos": info.get("fallos"), "vez": hechas + 1})
    if tipo == "pide_confirmacion":
        return {"decision": "continue", "reason": nova_autonomia.MSG_SIGUE}
    return {"decision": "continue", "reason": nova_autonomia.MSG_CONTINUE.format(tipo=tipo, frase=frase[:120])}


def revisar_verificacion(datos: dict) -> dict:
    """23/11 (Claude, el usuario: "siempre me da la razon para quedar bien y no aprendo"): si Nova EMPIEZA dando la razon sin
    haber comprobado nada en el turno (o el usuario pidio "¿seguro?" y no investigo), 1 "continue" para comprobarlo y
    responder en modo profe. nova_verificacion.py decide. Una vez por mensaje del usuario."""
    transcript = str(datos.get("transcriptPath") or "")
    conv = str(datos.get("conversationId", ""))
    try:
        import nova_verificacion

        turno = nova_verificacion.ultimo_turno(transcript)
        tipo, frase = nova_verificacion.decidir(turno, str(datos.get("lastUserInput") or ""))
    except Exception as ex:  # el freno nunca rompe el hook
        apuntar({"evento": "Stop", "conv": conv[:8], "error_verificacion": str(ex)[:200]})
        return {}
    if not tipo:
        if frase:
            apuntar({"evento": "Stop", "conv": conv[:8], "decision": "verificacion_" + frase})
        return {}
    estado = leer_estado()
    import hashlib

    # clave = el mensaje REAL del usuario (lastUserInput): aunque el "continue" anada pasos, nunca se repite
    huella = hashlib.sha1(str(datos.get("lastUserInput") or turno.get("id")).encode("utf-8")).hexdigest()[:12]
    clave = f"verificacion:{conv}:{huella}"
    if estado.get(clave):  # ya se le insistio en este mensaje del usuario: se suelta (nunca un bucle)
        apuntar({"evento": "Stop", "conv": conv[:8], "decision": "verificacion_soltada", "tipo": tipo})
        return {}
    estado[clave] = True
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": "verificacion_continue", "tipo": tipo, "frase": frase[:150]})
    return {"decision": "continue", "reason": nova_verificacion.mensaje(tipo, frase)}


def revisar_visual(datos: dict) -> dict:
    """23/11 (Claude, regla web-001 x5): si Nova cambio archivos web de un proyecto y cierra diciendo que esta listo sin
    haber pasado revision_visual\\revisar.py despues del ultimo cambio, la frena (hasta 2 veces por mensaje del usuario:
    si arregla algo tras revisar, tiene que volver a revisar)."""
    transcript = str(datos.get("transcriptPath") or "")
    conv = str(datos.get("conversationId", ""))
    try:
        import nova_verificacion

        info = nova_verificacion.revision_turno(transcript)
        tipo, archivos = nova_verificacion.decidir_revision(info, str(datos.get("lastUserInput") or ""))
    except Exception as ex:  # el freno nunca rompe el hook
        apuntar({"evento": "Stop", "conv": conv[:8], "error_revision_visual": str(ex)[:200]})
        return {}
    if not tipo:
        if archivos:
            apuntar({"evento": "Stop", "conv": conv[:8], "decision": "revision_visual_" + archivos})
        return {}
    import hashlib

    estado = leer_estado()
    huella = hashlib.sha1(str(datos.get("lastUserInput") or "").encode("utf-8")).hexdigest()[:12]
    clave = f"revision_visual:{conv}:{huella}"
    veces = int(estado.get(clave) or 0)
    if veces >= 2:  # nunca un bucle
        apuntar({"evento": "Stop", "conv": conv[:8], "decision": "revision_visual_soltada", "archivos": archivos[:150]})
        return {}
    estado[clave] = veces + 1
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": "revision_visual_continue", "archivos": archivos[:150],
             "vez": veces + 1})
    return {"decision": "continue", "reason": nova_verificacion.mensaje_revision(info, archivos)}


# 25/11 (Claude, fase 3): VERIFICAR ANTES DE "LISTO". Si en este mensaje Nova cambio archivos de codigo y no compilo
# ni probo nada DESPUES del ultimo cambio, se la frena UNA vez por mensaje del usuario (nunca un bucle).
EXT_COMPILA = {".java", ".kt", ".kts", ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cs", ".php", ".dart", ".go", ".rs",
               ".c", ".cpp"}
RE_VERIFICA_CMD = re.compile(
    r"(?i)\b(javac|java\s|gradlew|gradle\s|mvn\b|python|py_compile|pytest|node\s|npm\s|npx\s|pnpm\s|tsc\b|dotnet\s|"
    r"flutter\s|dart\s|php\s|go\s+(build|test|run)|cargo\s|orquestador\.py|revisar\.py)")
RE_SIN_PROBAR = re.compile(r"(?i)\b(no\s+(lo\s+)?(compiles|pruebes|ejecutes)|sin\s+(compilar|probar|ejecutar))\b")


def revisar_compilado(datos: dict) -> dict:
    transcript = str(datos.get("transcriptPath") or "")
    conv = str(datos.get("conversationId", ""))
    pedido = str(datos.get("lastUserInput") or "")
    if RE_SIN_PROBAR.search(pedido):
        return {}
    try:
        import nova_verificacion as nv

        cambiados, verificado = [], False
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                if o.get("type") == "USER_INPUT":
                    cambiados, verificado = [], False
                elif o.get("type") == "PLANNER_RESPONSE":
                    for tc in o.get("tool_calls") or []:
                        nombre = str(tc.get("name") or "")
                        ruta = nv._ruta_args(tc.get("args"))
                        if (re.search(r"write|edit|replace", nombre) and Path(ruta).suffix.lower() in EXT_COMPILA
                                and (".gemini" not in ruta.lower() or "scratch" in ruta.lower())):
                            cambiados.append(Path(ruta).name)
                            verificado = False
                        elif RE_VERIFICA_CMD.search(nv._comando(tc.get("args"))):
                            verificado = True
    except Exception as ex:  # el freno nunca rompe el hook
        apuntar({"evento": "Stop", "conv": conv[:8], "error_compilado": str(ex)[:200]})
        return {}
    if not cambiados or verificado:
        return {}
    import hashlib

    estado = leer_estado()
    clave = "compilado:" + conv + ":" + hashlib.sha1(pedido.encode("utf-8")).hexdigest()[:12]
    if estado.get(clave):
        apuntar({"evento": "Stop", "conv": conv[:8], "decision": "compilado_soltado"})
        return {}
    estado[clave] = True
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    archivos = ", ".join(sorted(set(cambiados))[:6])
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": "compilado_continue", "archivos": archivos[:150]})
    return {"decision": "continue", "reason": (
        f"[HOOK NOVA · VERIFICACION] Cambiaste codigo ({archivos}) y no compilaste ni probaste nada despues. Antes de "
        "decir listo: compila o ejecuta lo que toca (javac / gradlew assembleDebug / python -m py_compile / npm test... "
        "o `<PYTHON> <NOVA_HOME>\\nova_core\\orquestador.py revisar <archivos>`), arregla lo que falle y entonces "
        "cierra con lo que verificaste. Si no se puede compilar aqui, dilo claro en una linea.")}


def stop(datos: dict) -> dict:
    avisar_voz(datos)
    transcript = datos.get("transcriptPath") or ""
    if not transcript or not Path(transcript).exists():
        return {}
    try:  # 20/11: informe del orquestador (nunca rompe el hook)
        informe_orquestador(datos, medir_conv(transcript))
    except Exception as ex:
        apuntar({"evento": "Stop", "conv": str(datos.get("conversationId", ""))[:8], "error_informe_orq": str(ex)[:200]})
    conv = str(datos.get("conversationId", ""))
    ultimo_id, texto = respuestas_del_turno(transcript)
    n = lineas_de_codigo(texto)
    pedido = str(datos.get("lastUserInput") or "")
    if n <= MAX_LINEAS or RE_AUTORIZA.search(pedido):
        return (revisar_leccion(datos, texto) or revisar_bufer(datos, texto) or revisar_autonomia(datos)
                or revisar_visual(datos) or revisar_compilado(datos) or revisar_verificacion(datos))
    estado = leer_estado()
    clave = f"{conv}:{ultimo_id}"
    if estado.get(clave):  # una sola correccion por mensaje del usuario (nunca un bucle)
        return {}
    estado[clave] = True
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-200:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "lineas_codigo_chat": n, "decision": "continue"})
    return {"decision": "continue", "reason": (
        f"[HOOK NOVA] Has escrito unas {n} lineas de codigo en el chat desde la nube: eso incumple la ley 14 (el codigo va "
        "en archivos, y mas de 150 lineas las pica Qwen por secciones). Ahora, en un mensaje corto: 1) dile al usuario que te has saltado la regla, "
        "2) ofrecele lanzarlo con `<PYTHON> <NOVA_HOME>\\antigravity\\scripts\\nova_tarea.py \"<pedido>\" --carpeta <ruta>` "
        "(pregunta la carpeta si no la sabes). NO vuelvas a pegar el codigo.")}


def main() -> None:
    t0 = time.time()
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        datos = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", errors="replace") or "{}")
        salida = pre(datos) if modo == "pre" else stop(datos) if modo == "stop" else {}
    except Exception as ex:  # un hook roto nunca deja a Nova sin trabajar
        apuntar({"evento": modo, "error_hook": f"{ex.__class__.__name__}: {ex}", "ms": round((time.time() - t0) * 1000)})
        salida = {}
    # ASCII puro (í...): la consola de Windows usa cp1252 y un caracter raro del adjunto rompia la salida
    sys.stdout.write(json.dumps(salida, ensure_ascii=True))


if __name__ == "__main__":
    main()
