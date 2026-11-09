"""
NOVA HOOK DE TURNO (Antigravity: PreInvocation + Stop). Complementa a nova_hook.py (PreToolUse), que solo ve herramientas.

  - PreInvocation (antes de cada llamada al modelo, mensaje efimero que no se acumula en el historial):
      * apunta si el usuario autoriza escribir una web desde la nube ("escribelo tu" o una web de referencia);
        nova_hook.py lo lee para no bloquearla.
      * APRENDIZAJE (Ley 3): si el usuario corrige a Nova o el turno anterior tuvo 2+ comandos fallidos, pide UNA
        leccion en memory/inbox_lecciones.md (o "(sin leccion)").
      * BUFER (Ley 16): al pasar de 100k tokens de contexto, copia el chat a memory/chat_logs y pide "/compact".
      * si el usuario pide codigo: recuerda la regla de las 150 lineas.
  - Stop (al terminar el turno):
      * si la respuesta trae mas de MAX_LINEAS lineas de codigo en el chat y el usuario no dijo "escribelo tu",
        obliga a Nova a seguir UNA vez (por mensaje) para corregirlo y avisar.
      * si se pidio leccion y no la apunto: insiste una vez; a la segunda, el hook la apunta en bruto para revisar.

Uso:  python nova_hook_turno.py pre   |   python nova_hook_turno.py stop
Siempre: si algo falla, no bloquea (devuelve {}) y lo apunta en memory/registros/telemetria_hooks.jsonl.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / ".nova_turno_estado.json"
ANTIGRAVITY = Path.home() / ".gemini" / "antigravity"
REGISTRO = ANTIGRAVITY / "memory" / "registros" / "telemetria_hooks.jsonl"
PERFIL = ANTIGRAVITY / "memory" / "perfil_usuario.json"
MAX_LINEAS = 150
WINDOWS = os.name == "nt"
_SIN_VENTANA = 0x08000000 if WINDOWS else 0  # CREATE_NO_WINDOW


def _nombre_usuario() -> str:
    try:
        nombre = str(json.loads(PERFIL.read_text(encoding="utf-8-sig")).get("nombre", "")).strip()
    except (OSError, ValueError, AttributeError):
        nombre = ""
    return nombre or "el usuario"


USUARIO = _nombre_usuario()
PY = f'& "{sys.executable}"' if WINDOWS else f'"{sys.executable}"'
MONTAR = ANTIGRAVITY / "almacen" / "biblioteca_web" / "montar.py"
OBRERO = ANTIGRAVITY / "scripts" / "nova_local_worker.py"

RE_PIDE_CODIGO = re.compile(
    r"(?i)\b(script|c[oó]digo|funci[oó]n|programa|clase|componente|endpoint|algoritmo|regex|consulta sql|query)\b"
    r"|\b(escr[ií]be(me)?|hazme|crea(me)?|genera(me)?|programa(me)?|implementa)\b.{0,60}\b(python|javascript|typescript|"
    r"js|ts|react|html|css|sql|bash|powershell|java|kotlin|swift|dart|go|rust|php|web|p[aá]gina)\b")
RE_AUTORIZA = re.compile(r"(?i)escr[ií]be(lo|melo)\s+t[uú]|hazlo\s+t[uú]|p[eé]ga(lo|melo)\s+(aqu[ií]|en el chat)|en el chat")
RE_ADJUNTO_LOCAL = re.compile(r"\[adjunto local:\s*([^\]\r\n]+?)\s*\]")

RECORDATORIO = (
    f"REGLA DE NOVA (ley 14, la vigila un hook): {USUARIO} pide codigo. Hasta {MAX_LINEAS} lineas en 1-2 archivos: "
    "escribelo TU con edit_file/write_file (no en el chat). Una WEB de negocio: rellena datos.json y lanza la biblioteca "
    f"local (0 tokens): {PY} \"{MONTAR}\" --datos \"<carpeta>/datos.json\" --categoria auto --out \"<carpeta>/index.html\". "
    f"Otra pieza grande: el obrero local {PY} \"{OBRERO}\" --task \"<encargo>\". "
    "Si dice 'escribelo tu' o da una web de referencia, lo escribes."
)


def apuntar(d: dict) -> None:
    try:
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), **d}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def leer_estado() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_estado(estado: dict, maximo: int = 300) -> None:
    try:
        ESTADO.write_text(json.dumps(dict(list(estado.items())[-maximo:])), encoding="utf-8")
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


# ---------------------------------------------------------------- guardian de tokens en el chat (Ley 16)
# Al pasar de 100k -> copia del chat a memory/chat_logs y aviso "escribe /compact" (hasta 5 compactaciones);
# con 5 hechas -> "salta de ventana" (el puente queda listo y en la ventana nueva basta con "seguimos").
TOPE_BUFER = 100_000
RECORDAR_CADA = 50_000  # si no se compacta, se vuelve a avisar cada +50k
GUARDIAN = ANTIGRAVITY / "scripts" / "nova_buffer_guardian.py"
CHAT_LOGS = ANTIGRAVITY / "memory" / "chat_logs"


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
    if int(datos.get("invocationNum") or 0) != 0:  # una vez por mensaje del usuario
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
    guardar_estado(estado)
    if GUARDIAN.exists():  # copia del chat al .txt (chat_<AAAA-MM>_<conv>.txt)
        try:
            subprocess.run([sys.executable, str(GUARDIAN), "--silent"], capture_output=True, timeout=25,
                           creationflags=_SIN_VENTANA)
        except Exception:
            pass
    copia = next(iter(sorted(CHAT_LOGS.glob(f"chat_*_{conv[:8]}.txt"))), None) if conv else None
    donde = f"memory/chat_logs/{copia.name}" if copia else "memory/chat_logs/"
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
            f"esta en {donde}. {extra} Responde a {USUARIO} con normalidad y TERMINA tu respuesta con esta linea, tal "
            f"cual: {linea}")


# ---------------------------------------------------------------- aprendizaje automatico SIN ruido (Ley 3)
# Solo cuando hay SENAL (el usuario corrige o el turno anterior tuvo 2+ comandos fallidos) se pide UNA linea.
RE_CORRIGE = re.compile(
    r"(?i)\b(te equivocaste|te has equivocado|est[aá] mal|lo hiciste mal|eso no (es|era)|no era eso|no es as[ií]|"
    r"otra vez (lo mismo|igual|mal)|sigue (igual|sin|fallando)|no funciona|no sirve|fallaste|no (me )?(hiciste|haces|hace) caso|"
    r"te dije que|ya te dije|error tuyo|mal hecho|corr[ií]gelo|no hagas eso|por qu[eé] hiciste)\b")
INBOX_REAL = ANTIGRAVITY / "memory" / "inbox_lecciones.md"
INBOX = str(INBOX_REAL)
RE_SIN_LECCION = re.compile(r"(?i)\(\s*sin lecci[oó]n\s*\)")
COMO_ANADIR = ("con run_command (PowerShell: Add-Content -Encoding utf8 -Path \"<inbox>\" -Value \"<linea>\")" if WINDOWS
               else "con run_command (printf '%s\\n' \"<linea>\" >> \"<inbox>\")")


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


def firma_inbox() -> list:
    try:
        st = INBOX_REAL.stat()
        return [st.st_size, st.st_mtime_ns]
    except OSError:
        return [0, 0]


def aviso_leccion(datos: dict) -> str:
    if int(datos.get("invocationNum") or 0) != 0:
        return ""
    pedido = RE_ADJUNTO_LOCAL.sub("", str(datos.get("lastUserInput") or ""))
    transcript = str(datos.get("transcriptPath") or "")
    corrige = bool(RE_CORRIGE.search(pedido))
    fallos = fallos_turno_anterior(transcript) if transcript and Path(transcript).exists() else 0
    if not corrige and fallos < 2:
        return ""
    motivo = f"{USUARIO} te esta corrigiendo" if corrige else f"en tu turno anterior fallaron {fallos} comandos"
    conv = str(datos.get("conversationId", ""))
    apuntar({"evento": "PreInvocation", "conv": conv[:8], "decision": "pedir_leccion", "corrige": corrige, "fallos": fallos})
    estado = leer_estado()
    estado[f"leccion:{conv}"] = {"firma": firma_inbox(), "motivo": motivo, "pedido": pedido[:300], "insistido": False}
    guardar_estado(estado)
    return (f"APRENDIZAJE (Ley 3, lo vigila un hook): {motivo}. Primero resuelve lo que pide. Al final, SOLO si aprendiste "
            f"algo nuevo y reutilizable (no si fue un fallo de red o un servicio caido), anade UNA linea al final de {INBOX} "
            f"{COMO_ANADIR} con este formato exacto: "
            "`- [AAAA-MM-DD] [dominio] situacion -> hacer en su lugar` y termina con '(leccion apuntada)'. "
            "Si NO hay nada que aprender, termina tu respuesta con '(sin leccion)'. Un hook comprueba que hiciste una de las dos.")


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
    salida: dict = {}
    if hecho:
        estado.pop(clave, None)
        decision = "leccion_ok"
    elif not pend.get("insistido"):
        pend["insistido"] = True
        estado[clave] = pend
        decision = "leccion_continue"
        salida = {"decision": "continue", "reason": (
            "[HOOK NOVA] Te pidieron apuntar una leccion (Ley 3) y el inbox no ha cambiado. Ahora, sin repetir el trabajo: "
            f"si aprendiste algo, anade UNA linea a {INBOX} {COMO_ANADIR}, formato "
            "`- [AAAA-MM-DD] [dominio] situacion -> hacer en su lugar`, y responde solo '(leccion apuntada)'. "
            "Si no hay nada que aprender, responde solo '(sin leccion)'.")}
    else:
        estado.pop(clave, None)
        decision = "leccion_en_bruto"
        bruto = re.sub(r"\s+", " ", str(pend.get("pedido") or "")).strip()[:200]
        try:
            INBOX_REAL.parent.mkdir(parents=True, exist_ok=True)
            with INBOX_REAL.open("a", encoding="utf-8") as f:
                f.write(f"- [{time.strftime('%Y-%m-%d')}] [revisar] {pend.get('motivo')}: \"{bruto}\" -> "
                        "PENDIENTE: Nova no apunto la leccion; revisar en el informe semanal\n")
        except OSError as e:
            decision = f"leccion_en_bruto_error: {e}"
    guardar_estado(estado)
    apuntar({"evento": "Stop", "conv": conv[:8], "decision": decision})
    return salida


# ---------------------------------------------------------------- autorizacion de webs desde la nube
# nova_hook.py BLOQUEA webs de >150 lineas escritas desde la nube salvo que el usuario lo autorice en SU mensaje
# ("escribelo tu", "hazlo tu") o de una WEB DE REFERENCIA (enlace + palabra de referencia). Este hook ve el mensaje;
# nova_hook.py no. Se apunta aqui (por conversacion, se renueva con cada mensaje) y nova_hook.py lo lee.
AUTORIZA_CODIGO = AQUI / ".autoriza_codigo.json"
RE_AUTORIZA_WEB = re.compile(r"(?i)\b(escr[ií]be(lo|la|melo|mela)|hazlo|hazla|hazmela|h[aá]zmelo)\s+t[uú]\b")
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


def pre(datos: dict) -> dict:
    pedido = str(datos.get("lastUserInput") or "")
    apuntar_autorizacion(datos)
    pasos = []
    for aviso in (aviso_leccion(datos), aviso_bufer(datos)):
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
    if estado.get(clave):  # una sola correccion por mensaje del usuario (nunca un bucle)
        return {}
    estado[clave] = True
    guardar_estado(estado, 200)
    apuntar({"evento": "Stop", "conv": conv[:8], "lineas_codigo_chat": n, "decision": "continue"})
    return {"decision": "continue", "reason": (
        f"[HOOK NOVA] Has escrito unas {n} lineas de codigo en el chat desde la nube: eso incumple la ley 14 (el codigo va "
        f"en archivos, y lo grande lo hace la Capa 0 local). Ahora, en un mensaje corto: 1) dile a {USUARIO} que te has "
        "saltado la regla, 2) ofrecele hacerlo en local (biblioteca de webs con montar.py o el obrero "
        "nova_local_worker.py; pregunta la carpeta si no la sabes). NO vuelvas a pegar el codigo.")}


def main() -> None:
    t0 = time.time()
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        datos = json.loads(sys.stdin.buffer.read().decode("utf-8-sig", errors="replace") or "{}")
        salida = pre(datos) if modo == "pre" else stop(datos) if modo == "stop" else {}
    except Exception as ex:  # un hook roto nunca deja a Nova sin trabajar
        apuntar({"evento": modo, "error_hook": f"{ex.__class__.__name__}: {ex}", "ms": round((time.time() - t0) * 1000)})
        salida = {}
    # ASCII puro: la consola de Windows usa cp1252 y un caracter raro rompia la salida
    sys.stdout.write(json.dumps(salida, ensure_ascii=True))


if __name__ == "__main__":
    main()
