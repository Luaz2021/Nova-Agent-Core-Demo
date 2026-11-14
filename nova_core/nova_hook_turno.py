"""
NOVA HOOK DE TURNO (Antigravity: PreInvocation + Stop). Complementa a nova_hook.py (PreToolUse), que solo ve herramientas.

Problema que arregla: Nova pegaba 75-100 lineas de codigo EN EL CHAT (sin herramienta), y eso no lo ve PreToolUse.
  - PreInvocation: si Alexander pide codigo, antes de cada llamada al modelo se inyecta un recordatorio efimero
    (no se acumula en el historial) con la regla: codigo de mas de 150 lineas -> Qwen por secciones (nova_secciones.py).
  - Stop: al terminar el turno, si la respuesta trae mas de MAX_LINEAS lineas de codigo y Alexander no dijo
    "escribelo tu", obliga a Nova a seguir UNA vez (por mensaje de Alexander) para corregirlo y avisarle.

Uso:  python nova_hook_turno.py pre   |   python nova_hook_turno.py stop
Siempre: si algo falla, no bloquea (devuelve {}) y lo apunta en memory/registros/telemetria_hooks.jsonl.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / ".nova_turno_estado.json"
REGISTRO = Path.home() / ".gemini" / "antigravity" / "memory" / "registros" / "telemetria_hooks.jsonl"
MAX_LINEAS = 150

RE_PIDE_CODIGO = re.compile(
    r"(?i)\b(script|c[oó]digo|funci[oó]n|programa|clase|componente|endpoint|algoritmo|regex|consulta sql|query)\b"
    r"|\b(escr[ií]be(me)?|hazme|crea(me)?|genera(me)?|programa(me)?|implementa)\b.{0,60}\b(python|javascript|typescript|"
    r"js|ts|react|html|css|sql|bash|powershell|java|kotlin|swift|dart|go|rust|php)\b")
RE_AUTORIZA = re.compile(r"(?i)escr[ií]be(lo|melo)\s+t[uú]|hazlo\s+t[uú]|p[eé]ga(lo|melo)\s+(aqu[ií]|en el chat)|en el chat")

RECORDATORIO = (
    "REGLA DE NOVA (ley 14, la vigila un hook): Alexander pide codigo. Hasta 150 lineas en 1-2 archivos: escribelo TU con "
    "edit_file/write_file (no en el chat). Una web o pieza mas grande: escribe secciones.json MASTICADO (un encargo preciso "
    "por seccion) y lanza `<PYTHON> <NOVA_HOME>\\antigravity\\scripts\\nova_secciones.py --carpeta <ruta>` (Qwen en local). "
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
    """(id del ultimo mensaje de Alexander, texto de las respuestas del modelo desde entonces)."""
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


# ---------------------------------------------------------------- adjuntos (09/11, Claude, a pedido de Luaz)
# Antigravity guarda lo que Alexander pega en brain/<conv>/.user_uploaded/ y nova_puente_capturas.py (cada 2 s) lo
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
    """Nombres de los archivos que Alexander pego en este turno (carpeta .user_uploaded + 'media' del transcript;
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
                         creationflags=0x08000000)  # CREATE_NO_WINDOW
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
    partes = ["REGLA DE NOVA (adjuntos, la vigila un hook): Alexander ha pegado un adjunto y YA esta leido EN LOCAL "
              "(0 tokens de nube). Su contenido esta AQUI ABAJO. Trabaja SOLO con este texto: NO abras el original, NO "
              "intentes extraerlo con Python/PowerShell ni pidas permisos para hacerlo, y no busques el .md (Antigravity "
              "bloquea esa carpeta)."]
    for n, md in listos.items():
        try:
            texto = md.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            texto = f"(no se pudo leer {md.name}: {e})"
        if len(texto) > MAX_CHARS_ADJUNTO:
            texto = texto[:MAX_CHARS_ADJUNTO] + "\n[... recortado: es largo. Responde con esto y dile a Alexander que hay mas.]"
        partes.append(f"\n===== ADJUNTO {n} =====\n{texto.strip()}\n===== FIN {n} =====")
    if faltan:
        partes.append("Aun procesandose en local: " + ", ".join(faltan) + ". Dile a Alexander que lo repita en unos "
                      "segundos; no lo analices tu.")
    partes.append("Si este texto no basta para responder, dile a Alexander que falta y por que.")
    return "\n".join(partes)


# ---------------------------------------------------------------- interruptor de MCP (09/11, Claude, a pedido de Luaz)
# Playwright (~5.100 tokens) y Postgres (~5.000) viajan en CADA mensaje si estan encendidos. Van apagados y se
# encienden aqui solo si Luaz pide algo que los necesita; session_guard.ps1 los apaga al cerrar Antigravity.
NOVA_MCP = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_mcp.py"
PIDE_MCP = {  # 09/11 tarde: playwright va FIJO encendido (carga bajo demanda, no cuesta tokens); solo postgres
    "postgres": re.compile(r"(?i)\b(postgres(ql)?|supabase|base(s)? de datos|bbdd|sql|psql)\b"),
}
PIDE_BRAVE = re.compile(r"(?i)\b(en )?(mi |el )?brave\b|\bmi (navegador|sesi[oó]n)\b")


def interruptor_mcp(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    pedido = str(datos.get("lastUserInput") or "")
    pedido = RE_ADJUNTO_LOCAL.sub("", pedido)  # que el nombre de un adjunto no encienda nada
    avisos = []
    if PIDE_BRAVE.search(pedido):
        avisos.append("Para navegar en el Brave de Alexander (con sus sesiones) usa el puente de Brave "
                      "(http://127.0.0.1:5005: /status, /snapshot, /screenshot, POST /execute), NO Playwright.")
    for nombre, patron in PIDE_MCP.items():
        if patron.search(pedido):
            import subprocess
            try:
                # timeout 35 s: la recarga en caliente (RefreshMcpServers) reinicia los MCP y tarda ~10 s
                r = subprocess.run([sys.executable, str(NOVA_MCP), "activar", nombre], capture_output=True, timeout=35,
                                   creationflags=0x08000000)
                salida = r.stdout.decode("utf-8", "replace").strip()
            except Exception as e:
                salida = f"error: {e}"
            apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": f"mcp_{nombre}",
                     "resultado": salida[:120]})
            if "recargado en caliente" in salida:
                avisos.append(f"Se ha ENCENDIDO el MCP {nombre} ({salida}). Si sus herramientas aun no te aparecen en esta "
                              "llamada, apareceran en la siguiente; si tampoco, dile a Alexander que repita el pedido y PARA "
                              "(no investigues). Nunca pidas contraseñas en el chat. Se apaga solo al cerrar Antigravity.")
            elif "ya estaba" not in salida:
                # 09/11 P4: sin recarga en caliente Nova creia que las herramientas llegarian y se puso a investigar
                # (list_resources, leer archivos, docker ps -> abrio Docker; ~95k tokens) y acabo pidiendo la contraseña.
                avisos.append(f"Se ha ACTIVADO el MCP {nombre} en la configuracion, pero sus herramientas NO estaran hasta "
                              "reabrir Antigravity. Dile a Alexander SOLO esto, en una linea: 'He activado " + nombre +
                              "; cierra y abre Antigravity y repite el pedido.' y PARA. No investigues (nada de docker, "
                              "puertos, archivos del MCP ni list_resources) y NUNCA pidas contraseñas en el chat.")
    return ("REGLA DE NOVA (MCP bajo demanda, la vigila un hook): " + " ".join(avisos)) if avisos else ""


# ---------------------------------------------------------------- pase de pago en Brave (09/11, Claude, a pedido de Luaz)
# La extension v4 bloquea botones de pago/compra. Solo se desbloquea UN pago (10 min) si Alexander lo escribe/dice.
# lastUserInput es el mensaje real de Alexander (una web o un adjunto no pueden escribirlo). La clave solo la tienen
# este hook y el puente; nova_hook.py impide que Nova la lea o llame a /pase_pago.
# Solo primera persona y afirmativo: "autorizo el pago", "te doy permiso para comprar", "tienes mi permiso para pagar".
# NO: "no autorizo el pago", "¿autorizaste el pago?", "la autorizacion del pago fallo", "nunca te permito comprar".
RE_AUTORIZA_PAGO = re.compile(r"(?i)(?<![\w¿?])(autorizo|te autorizo|te doy permiso|tienes (mi )?permiso|te permito)\b"
                              r"[^.?!\n]{0,40}?\b(pag(o|os|ar|a|ues)|compr(a|as|ar|e)|suscri\w*)\b")
RE_NIEGA_PAGO = re.compile(r"(?i)\b(no|nunca|jam[aá]s|ni)\s+(te\s+)?(autorizo|doy|tienes|permito)\b")
CLAVE_PASE = AQUI / ".pase_pago.clave"


def autoriza_pago(pedido: str) -> bool:
    """True solo si Alexander autoriza en afirmativo (la frase que lo dice no es pregunta ni negacion)."""
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
        return ("REGLA DE NOVA (pagos): Alexander quiere autorizar un pago, pero el puente de Brave no respondio (¿Brave cerrado "
                "o la extension sin conectar?). Diselo; no intentes pagar.")
    return ("REGLA DE NOVA (pagos, la vigila un hook): Alexander ha AUTORIZADO UN SOLO PAGO en Brave durante 10 minutos. "
            "Antes de pulsar el boton final dile en una frase que vas a pagar (que, cuanto, donde). Tras ese pago el "
            "permiso se gasta solo. Los numeros de tarjeta y contraseñas NO los escribes nunca: los pone Alexander o el "
            "autocompletado de Brave.")


# ---------------------------------------------------------------- guardian de tokens en el chat (Ley 16, 09/11 Claude)
# Flujo de Alexander: al pasar de 100k -> copia del chat al .txt de memory\chat_logs (con la fecha del chat) y aviso
# "escribe /compact" (hasta 5 compactaciones); con 5 hechas -> "salta de ventana" (el puente queda listo y en la
# ventana nueva basta con "seguimos"). El guardian de memoria (nova_buffer_guardian.py) hace la copia y el aviso por
# voz; este hook pone el aviso DENTRO del chat (antes solo salia si Nova usaba una herramienta, y como un clic).
TOPE_BUFER = 100_000
RECORDAR_CADA = 50_000  # si Alexander no compacta, se vuelve a avisar cada +50k
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


def aviso_bufer(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:  # una vez por mensaje de Alexander
        return ""
    transcript = str(datos.get("transcriptPath") or "")
    if not transcript or not Path(transcript).exists():
        return ""
    contexto, hechas = medir_bufer(transcript)
    if contexto < TOPE_BUFER:
        return ""
    conv = str(datos.get("conversationId", ""))
    estado = leer_estado()
    clave = f"bufer:{conv}"
    previo = estado.get(clave) or {}
    if previo.get("hechas") == hechas and contexto - previo.get("tokens", 0) < RECORDAR_CADA:
        return ""  # ya avisado en este ciclo
    estado[clave] = {"hechas": hechas, "tokens": contexto}
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    # Antes de cada aviso: copia del chat al .txt (el guardian escribe chat_<fecha>_inicio-<HHmm>_conv-<id>.txt)
    import subprocess
    try:
        subprocess.run([sys.executable, str(GUARDIAN), "--silent"], capture_output=True, timeout=25, creationflags=0x08000000)
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
        linea = (f"[BUFER EN {k}k | Chat respaldado | Compactaciones {hechas}/5] Escribe /compact para resetear a ~17k "
                 "tokens (la conversacion queda guardada).")
        extra = f"Quedan {5 - hechas} compactaciones antes de tener que saltar de ventana."
    return (f"AVISO DE BUFER (Ley 16, lo vigila un hook): el contexto va por {k}k tokens (tope 100k). La copia del chat "
            f"esta en {donde}. {extra} Responde a Alexander con normalidad y TERMINA tu respuesta con esta linea, tal "
            f"cual: {linea}")


# ---------------------------------------------------------------- aprendizaje automatico SIN ruido (Ley 3, 09/11 Claude)
# Antes dependia de que Nova se acordara (skill con trigger model_decision): desde el 08/11 no apunto nada.
# Solo cuando hay SEÑAL (Alexander corrige o el turno anterior tuvo 2+ comandos fallidos) se le pide UNA linea.
RE_CORRIGE = re.compile(
    r"(?i)\b(te equivocaste|te has equivocado|est[aá] mal|lo hiciste mal|eso no (es|era)|no era eso|no es as[ií]|"
    r"otra vez (lo mismo|igual|mal)|sigue (igual|sin|fallando)|no funciona|no sirve|fallaste|no (me )?(hiciste|haces|hace) caso|"
    r"te dije que|ya te dije|error tuyo|mal hecho|corr[ií]gelo|no hagas eso|por qu[eé] hiciste)\b")
INBOX = r"<NOVA_HOME>\antigravity\memory\inbox_lecciones.md"


def fallos_turno_anterior(transcript: str) -> int:
    """Comandos fallidos entre el penultimo y el ultimo mensaje de Alexander."""
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


def aviso_leccion(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    pedido = RE_ADJUNTO_LOCAL.sub("", str(datos.get("lastUserInput") or ""))
    transcript = str(datos.get("transcriptPath") or "")
    corrige = bool(RE_CORRIGE.search(pedido))
    fallos = fallos_turno_anterior(transcript) if transcript and Path(transcript).exists() else 0
    if not corrige and fallos < 2:
        return ""
    motivo = "Alexander te esta corrigiendo" if corrige else f"en tu turno anterior fallaron {fallos} comandos"
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
            "`- [AAAA-MM-DD] [dominio] situacion -> hacer en su lugar` y termina con '(leccion apuntada)'. "
            "Si NO hay nada que aprender, termina tu respuesta con '(sin leccion)'. Un hook comprueba que hiciste una de las dos.")


INBOX_REAL = Path.home() / ".gemini" / "antigravity" / "memory" / "inbox_lecciones.md"
RE_SIN_LECCION = re.compile(r"(?i)\(\s*sin lecci[oó]n\s*\)")


def firma_inbox() -> list:
    try:
        st = INBOX_REAL.stat()
        return [st.st_size, st.st_mtime_ns]
    except OSError:
        return [0, 0]


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
            "`- [AAAA-MM-DD] [dominio] situacion -> hacer en su lugar`, y responde solo '(leccion apuntada)'. "
            "Si no hay nada que aprender, responde solo '(sin leccion)'.")}
    else:
        estado.pop(clave, None)
        decision = "leccion_en_bruto"
        salida = {}
        bruto = re.sub(r"\s+", " ", str(pend.get("pedido") or "")).strip()[:200]
        try:
            with INBOX_REAL.open("a", encoding="utf-8") as f:
                f.write(f"- [{time.strftime('%Y-%m-%d')}] [revisar] {pend.get('motivo')}: \"{bruto}\" -> "
                        "PENDIENTE: Nova no apunto la leccion; revisar en el informe semanal\n")
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


# 09/11 tarde (Claude, a pedido de Luaz): nova_hook.py BLOQUEA webs de >150 lineas escritas desde la nube salvo que
# Alexander lo autorice en SU mensaje ("escribelo tu", "hazlo tu"). Este hook ve el mensaje; nova_hook.py no. Se apunta
# aqui (por conversacion, se renueva con cada mensaje de Alexander) y nova_hook.py lo lee.
AUTORIZA_CODIGO = AQUI / ".autoriza_codigo.json"
RE_AUTORIZA_WEB = re.compile(r"(?i)\b(escr[ií]be(lo|la|melo|mela)|hazlo|hazla|hazmela|h[aá]zmelo)\s+t[uú]\b|\b(tienes\s+permiso|luz\s+verde|haz\s+los\s+cambios|s[uú]belo|ed[ií]talo|haz\s+(el\s+)?(commit|push)|sube\s+a\s+github)\b")
# 09/11 (regla de Luaz): por defecto webs minimalistas con la biblioteca (0 nube); si da una WEB DE REFERENCIA, la nube
# puede escribirla ("no queda de otra"): un enlace + una palabra de referencia en SU mensaje.
RE_REFERENCIA_WEB = re.compile(r"(?i)https?://\S+|www\.\S+")
RE_PALABRA_REFERENCIA = re.compile(r"(?i)\b(referencia|parecid[ao]|como (esta|esa|la de)|igual que|estilo de|inspir[aá]te|"
                                   r"inspirad[ao]|basad[ao] en|tipo esta|al estilo)\b")


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
    try:
        AUTORIZA_CODIGO.write_text(json.dumps(dict(list(estado.items())[-100:])), encoding="utf-8")
    except OSError:
        pass


DOCTOR_ESTADO = Path.home() / ".gemini" / "antigravity" / "memory" / "doctor_estado.json"
DOCTOR_PS = r"<NOVA_HOME>\antigravity\scripts\nova_doctor.ps1"


def aviso_doctor(datos: dict) -> str:
    """11/11 (Claude): si el Nova Doctor de ESTE equipo encontro fallos (Python de Nova, hooks, Ollama, voz, aduana...),
    se lo cuenta a Nova UNA vez por conversacion para que avise a Alexander. Nova no repara nada a mano."""
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
            "Alexander en UNA linea. NO intentes arreglarlo tu (nada de pip, copiar de Drive ni editar scripts): si quiere, "
            f"vuelve a pasar el Doctor con: powershell -ExecutionPolicy Bypass -File \"{DOCTOR_PS}\" y le das su ultima linea. "
            "Si sigue fallando, es cosa de Claude.")


def pre(datos: dict) -> dict:
    pedido = str(datos.get("lastUserInput") or "")
    apuntar_autorizacion(datos)
    pasos = []
    aviso_d = aviso_doctor(datos)
    if aviso_d:
        pasos.append({"ephemeralMessage": aviso_d})
    aviso_l = aviso_leccion(datos)
    if aviso_l:
        pasos.append({"ephemeralMessage": aviso_l})
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
    if RE_PIDE_CODIGO.search(pedido) and not RE_AUTORIZA.search(pedido):
        apuntar({"evento": "PreInvocation", "conv": str(datos.get("conversationId", ""))[:8], "decision": "recordatorio_codigo"})
        pasos.append({"ephemeralMessage": RECORDATORIO})
    return {"injectSteps": pasos} if pasos else {}


def stop(datos: dict) -> dict:
    transcript = datos.get("transcriptPath") or ""
    if not transcript or not Path(transcript).exists():
        return {}
    conv = str(datos.get("conversationId", ""))
    ultimo_id, texto = respuestas_del_turno(transcript)
    n = lineas_de_codigo(texto)
    pedido = str(datos.get("lastUserInput") or "")
    if n <= MAX_LINEAS or RE_AUTORIZA.search(pedido):
        return revisar_leccion(datos, texto)
    estado = leer_estado()
    clave = f"{conv}:{ultimo_id}"
    if estado.get(clave):  # una sola correccion por mensaje de Alexander (nunca un bucle)
        return {}
    estado[clave] = True
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-200:])), encoding="utf-8")
    except OSError:
        pass
    apuntar({"evento": "Stop", "conv": conv[:8], "lineas_codigo_chat": n, "decision": "continue"})
    return {"decision": "continue", "reason": (
        f"[HOOK NOVA] Has escrito unas {n} lineas de codigo en el chat desde la nube: eso incumple la ley 14 (el codigo va "
        "en archivos, y mas de 150 lineas las pica Qwen por secciones). Ahora, en un mensaje corto: 1) dile a Alexander que te has saltado la regla, "
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
