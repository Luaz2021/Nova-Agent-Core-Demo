r"""
NOVA · FRENO DE AUTONOMIA: sin excusas y sin pedir confirmacion (22/11/2026, Claude, a pedido del usuario: "siempre me dice hay error en esto y el otro; que
busque solucion y no excusas, gasto mas tokens hablando que trabajando").

Lo usa nova_hook_turno.py en el Stop (cuando Nova va a cerrar su turno). Mira SOLO el turno actual (desde el ultimo
mensaje del usuario) en el transcript de Antigravity y decide si la respuesta final es una EXCUSA:
  - "devuelve": le pasa el trabajo al usuario ("hazlo tu", "tendras que abrir...", "a mano", "manualmente")
  - "no_puedo": "no puedo", "no he podido", "no es posible", "no me deja"
  - "error":    "hay un error", "falla", "no funciona" sobre SU trabajo (solo cuenta si en el turno fallo algo)
NO es excusa (pasa sin frenar):
  - hubo un BLOQUEO REAL en el turno (hook o regla de Antigravity: "tool call denied") -> pedir permiso es correcto
  - la respuesta pide algo que solo el usuario da: permiso, clave/contrasena, pago, iniciar sesion, captcha, 2FA
  - El usuario quiere hacerlo EL ("lo hago yo", "explicame", "ensename", "paso a paso", practicas de clase)
  - ya lo intento: tras el primer fallo hizo 2+ llamadas mas (probo soluciones) antes de rendirse
El hook frena como mucho UNA vez por mensaje del usuario (nunca un bucle). Telemetria: autonomia_continue / autonomia_ok_*.
"""

import json
import re

RE_DEVUELVE = re.compile(
    r"(?i)\b(h[aá]zlo|[aá]brelo|[aá]brela|ed[ií]talo|p[eé]galo|c[oó]pialo|ejec[uú]talo|inst[aá]lalo|c[aá]mbialo|"
    r"arr[eé]glalo|p[oó]nlo|c[aá]mbiala|ed[ií]tala)\s+t[uú](\s+mismo)?\b"
    r"|\bt[uú]\s+mismo\b"
    r"|\btendr[aá]s\s+que\s+(abrir|ejecutar|pegar|editar|instalar|hacer|cambiar|copiar|crear|a[nñ]adir|borrar|mover|"
    r"reiniciar|configurar|escribir|descargar|arrastrar)"
    r"|\bte\s+toca(\s+a\s+ti)?\s+(abrir|editar|hacer|pegar|cambiar|ejecutar|arreglar|copiar|instalar)\b"
    r"|\bte\s+lo\s+dejo\s+a\s+ti\b"
    r"|\b(h[aá]zlo|c[aá]mbialo|ed[ií]talo|a[nñ][aá]delo|p[oó]nlo)\s+(a\s+mano|manualmente)\b"
)
# el usuario pide una ACCION (no una charla o una explicacion): solo ahi se vigila que Nova no le devuelva el trabajo
RE_PIDE_ACCION = re.compile(
    r"(?i)\b(arregl\w*|revis\w*|corrig\w*|haz|hazme|hazlo|crea\w*|cambi\w*|pon(lo|la|me)?|a[nñ]ad\w*|quit\w*|"
    r"sub\w*|instal\w*|ejecut\w*|configur\w*|mont\w*|edit\w*|program\w*|genera\w*|dise[nñ]\w*|soluciona\w*|"
    r"mira\s+(a\s*)?ver|pru[eé]ba\w*|enc[aá]rgate|sincroniza\w*|actualiza\w*|borra\w*|mueve|copia\w*)\b"
)
# Topes externos (cupo o plan de un servicio): no es excusa, es un limite real que Nova no puede saltar
RE_LIMITE_EXTERNO = re.compile(
    r"(?i)\b(out\s+of\s+calls|rate\s+limit|cupo|cuota|quota|l[ií]mite\s+(del|de\s+tu|de\s+la)\s+(plan|cuenta|api)|"
    r"plan\s+(starter|gratuito|gratis|free))\b"
)
RE_NO_PUEDO = re.compile(
    r"(?i)\b(no\s+puedo|no\s+he\s+podido|no\s+pude|no\s+es\s+posible|no\s+tengo\s+acceso|no\s+me\s+deja|"
    r"me\s+bloque[aó]|est[aá]\s+bloquead[oa]|imposible)\b"
)
RE_ERROR = re.compile(
    r"(?i)\b(hay\s+un\s+(error|fallo|problema)|da\s+(un\s+)?error|salta\s+(un\s+)?error|sale\s+(un\s+)?error|"
    r"sigue\s+fallando|fall[oó]|est[aá]\s+fallando|no\s+funciona|no\s+arranca|se\s+rompi[oó])\b"
)
# En la misma frase que la excusa: ya lo arreglo -> no es excusa
RE_ARREGLADO = re.compile(r"(?i)\b(arregl[eé]|solucion[eé]|correg[ií]|ya\s+funciona|resuelto|listo|qued[oó]\s+bien)\b")
# Cosas que de verdad solo puede dar el usuario
RE_SOLO_USUARIO = re.compile(
    r"(?i)\b(permiso|autoriza|contrase[nñ]a|clave|api\s*key|token|credencial|cofre|pago|pagar|tarjeta|"
    r"inicia(r)?\s+sesi[oó]n|login|captcha|2fa|c[oó]digo\s+de\s+verificaci[oó]n|verificaci[oó]n\s+en\s+dos|"
    r"administrador|uac|elevaci[oó]n|runas)\b"
)
# el usuario quiere hacerlo el / aprender (practicas de clase)
RE_LO_HACE_EL = re.compile(
    r"(?i)\b(lo\s+hago\s+yo|yo\s+lo\s+hago|yo\s+lo\s+pico|lo\s+pico\s+yo|d[eé]jame\s+a\s+m[ií]|expl[ií]ca(me|lo)|"
    r"ens[eé][nñ]a(me)?|gu[ií]a(me)?|paso\s+a\s+paso|c[oó]mo\s+(lo\s+)?hago|quiero\s+aprender|no\s+me\s+lo\s+hagas|"
    r"sin\s+hac[eé]rmelo|para\s+aprender|(pueda|puedo|quiero)\s+hacer(lo)?\s+yo|yo\s+sol[oa](?!\s+(ver|mir|observ))|yo\s+mism[oa])\b"
)
# 22/11 noche (el usuario: "a cada rato le tengo que decir que tiene permiso"): en un ENCARGO Nova cerraba cada paso con
# "Dime 'sigue' y en el siguiente paso...". Si el usuario ya le dio el encargo en esta conversacion, no se para a pedir
# un "sigue": el hook la hace continuar (hasta MAX_SIGUE veces por mensaje del usuario).
RE_PIDE_SIGUE = re.compile(
    r"(?i)\bdime\s+[*_`\"'“”«»\s]*(sigue|dale|contin[uú]a|adelante|ok|vale|s[ií]|listo|go)\b"
    r"|\b(cuando|si)\s+me\s+(digas|confirmes|des\s+(el\s+)?ok)\b"
    r"|\bav[ií]same\s+(y|para|cuando)\b"
    r"|¿\s*(sigo|contin[uú]o|avanzo|empiezo|lo\s+hago|quieres\s+que\s+(siga|contin[uú]e|empiece|lo\s+haga))\b"
    r"|\b(espero\s+tu\s+(ok|confirmaci[oó]n|se[nñ]al))\b"
)
RE_ENCARGO_EL = re.compile(
    r"(?i)\b(h[aá]z(lo|la|melo|mela)\s+t[uú]|enc[aá]rgate|t[uú]\s+sol[ao]|yo\s+solo\s+(ver[eé]|miro|mirar[eé])|"
    r"tienes\s+(mi\s+|todo\s+(el\s+)?)?permiso|te\s+doy\s+permiso|no\s+me\s+(andes\s+)?pid(as|es)\s+permiso|"
    r"sin\s+pedir(me)?\s+permiso|avanza\s+(todo|sola|t[uú])|haz(lo)?\s+todo|dale\s+con\s+todo|no\s+pares)\b"
)
MAX_SIGUE = 8
# Lo que de verdad le pide al usuario (para pide_confirmacion): sin "login" suelto, que suele ser una PANTALLA que diseña
RE_NECESITA_USUARIO = re.compile(
    r"(?i)\b(contrase[nñ]a|clave|api\s*key|token|credencial|cofre|pago|pagar|tarjeta|inicia(r|s)?\s+(tu\s+)?sesi[oó]n|"
    r"(tu|con\s+tu)\s+(cuenta|usuario|login)|captcha|2fa|c[oó]digo\s+de\s+verificaci[oó]n|administrador|uac)\b"
)
RE_SOLO_BUFER = re.compile(r"(?is)^\s*\[(BUFER EN|COMPACTACION AUTOMATICA|LIMITE DE SESION)")
MSG_SIGUE = (
    "[HOOK NOVA · AUTONOMIA] el usuario YA te dio el encargo y el permiso en esta conversacion: no le pidas "
    "'sigue' ni 'dale'. Continua TU SOLA ahora mismo con el siguiente paso, y despues con el siguiente, sin parar "
    "hasta terminar el encargo. Lo de su navegador y su escritorio (pestanas, clics, Brave Shields, plugins) lo haces "
    "TU con el puente de Brave y windows-mcp. Solo paras si necesitas algo que de verdad solo el puede dar (clave, "
    "login, pago): en ese caso, UNA linea diciendo que necesitas. Al terminar, un resumen corto de lo hecho."
)
RE_OFRECE_ALTERNATIVAS = re.compile(r"(?i)\b(pero|alternativa|opciones|formas\s+de|en\s+su\s+lugar|otra\s+v[ií]a)\b")


def analizar_turno(transcript: str) -> dict:
    """Del ultimo mensaje del usuario al final: llamadas, fallos, bloqueos reales y la respuesta final."""
    info = {"id": "", "llamadas": 0, "fallos": 0, "bloqueos": 0, "tras_fallo": 0, "final": ""}
    aprende = False  # en ESTA conversacion el usuario dijo que lo hace el / quiere aprender (practicas): se recuerda
    encargo = False  # en ESTA conversacion el usuario le dio el encargo ("hazlo tu", "tienes mi permiso"): se recuerda
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                tipo = o.get("type")
                if tipo == "USER_INPUT":
                    pedido = re.sub(r"(?s)<ADDITIONAL_METADATA>.*|<USER_SETTINGS_CHANGE>.*|</?USER_REQUEST>", "",
                                    str(o.get("content") or ""))
                    aprende = aprende or bool(RE_LO_HACE_EL.search(pedido))
                    encargo = encargo or bool(RE_ENCARGO_EL.search(pedido))
                    info = {"id": str(o.get("step_index", "")), "llamadas": 0, "fallos": 0, "bloqueos": 0,
                            "tras_fallo": 0, "final": "", "aprende": aprende, "encargo": encargo}
                elif tipo == "PLANNER_RESPONSE":
                    n = len(o.get("tool_calls") or [])
                    info["llamadas"] += n
                    if info["fallos"]:
                        info["tras_fallo"] += n
                    contenido = str(o.get("content") or "")
                    # 22/11: la linea del bufer (la pide otro freno) no tapa la respuesta real de Nova
                    if contenido and not (len(contenido) < 400 and RE_SOLO_BUFER.match(contenido)):
                        info["final"] = contenido
                elif tipo == "GENERIC":
                    texto = linea.lower()
                    if "denied" in texto or "deny rule" in texto:
                        info["bloqueos"] += 1
                    else:
                        m = re.search(r"exited with code (-?\d+)", linea)
                        if (m and m.group(1) != "0") or o.get("status") == "ERROR":
                            info["fallos"] += 1
    except OSError:
        pass
    return info


def _frases(texto: str) -> list[str]:
    texto = re.sub(r"```.*?```", " ", texto, flags=re.S)  # el codigo no cuenta
    return [f for f in re.split(r"(?<=[.!?¿¡])\s+|\n+", texto) if f.strip()]


def tipo_excusa(final: str) -> tuple[str, str]:
    """('devuelve'|'no_puedo'|'error'|'', frase) para la respuesta final de Nova."""
    for tipo, rx in (("devuelve", RE_DEVUELVE), ("no_puedo", RE_NO_PUEDO), ("error", RE_ERROR)):
        for frase in _frases(final):
            if rx.search(frase) and not RE_ARREGLADO.search(frase) and "?" not in frase:
                return tipo, frase.strip()[:200]
    return "", ""


def decidir(info: dict, pedido: str) -> tuple[str, str]:
    """('' si no hay que frenar | motivo para la telemetria, tipo)."""
    tipo, frase = tipo_excusa(info.get("final", ""))
    if not tipo and (info.get("encargo") or RE_ENCARGO_EL.search(pedido or "")) and not info.get("aprende"):
        for f in _frases(info.get("final", "")):
            if RE_PIDE_SIGUE.search(f):
                if info.get("bloqueos"):
                    return "", "ok_bloqueo_real"
                if RE_NECESITA_USUARIO.search(f):  # 22/11: "pantalla de Login" no es pedir que inicie sesion
                    return "", "ok_solo_usuario"
                return "pide_confirmacion", f.strip()[:200]
    if not tipo:
        return "", ""
    if info.get("bloqueos"):
        return "", "ok_bloqueo_real"
    if RE_SOLO_USUARIO.search(frase):
        return "", "ok_solo_usuario"
    if RE_LIMITE_EXTERNO.search(info.get("final", "")):
        return "", "ok_limite_externo"
    if RE_LO_HACE_EL.search(pedido or "") or info.get("aprende"):
        return "", "ok_lo_hace_el"
    if not RE_PIDE_ACCION.search(pedido or "") and not info.get("llamadas"):
        return "", "ok_charla"  # charla o explicacion sin trabajo pedido: no se vigila
    if info.get("fallos") and info.get("tras_fallo", 0) >= 2:
        return "", "ok_ya_lo_intento"
    if tipo == "error" and not info.get("fallos"):
        return "", "ok_error_ajeno"  # habla de un error del codigo del usuario, no de su trabajo
    if tipo == "no_puedo" and not info.get("fallos") and RE_OFRECE_ALTERNATIVAS.search(info.get("final", "")):
        return "", "ok_ofrece_alternativas"
    return tipo, frase


MSG_CONTINUE = (
    "[HOOK NOVA · AUTONOMIA] Vas a cerrar el turno con una excusa ({tipo}: \"{frase}\") sin haberlo intentado de "
    "verdad. El usuario quiere SOLUCIONES, no explicaciones. Ahora, sin repetir lo anterior: 1) busca la causa real "
    "(lee el error completo, el log o el archivo); 2) prueba al menos 2 soluciones distintas con tus herramientas "
    "(otra via, el Doctor si es de Nova, la skill o el kit del tema); 3) si funciona, di en 1-2 lineas que lo "
    "arreglaste y como. Solo si las 2 fallan, responde en 3 lineas: QUE FALLA, QUE PROBASTE, QUE NECESITAS de "
    "el usuario. No le pases el trabajo a el salvo que sea algo que solo el puede dar (permiso, clave, pago, login)."
)
