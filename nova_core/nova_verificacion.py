r"""
NOVA · FRENO DE VERIFICACION + MODO PROFE (23/11/2026, Claude, a pedido del usuario: "para quedar bien siempre me da la
razon; le digo cosas sin sentido y me dice tienes razon y yo patino, no aprendo nada").

Medido el 23/11 en memory\chat_logs: 27 respuestas de noviembre EMPIEZAN dando la razon ("Tienes toda la razon",
"Exacto", "Diste en el clavo"...), varias sin haber comprobado nada.

Lo usa nova_hook_turno.py:
  - Stop: si la respuesta final EMPIEZA dando la razon y en el turno NO hubo ninguna llamada (no leyo, no ejecuto,
    no busco) -> 1 "continue": comprobarlo de verdad y responder en MODO PROFE.
    Tambien si el usuario pidio verificar ("¿seguro?", "/verifica") y Nova contesto sin ninguna llamada.
  - PreInvocation: si el usuario escribe "¿seguro?" / "/verifica" / "compruebalo" -> aviso de investigar ANTES.
NO frena (pasa):
  - hubo llamadas en el turno (leyo/ejecuto/busco: comprobo algo)
  - El usuario habla de lo que Nova HIZO en esta conversacion ("te dije", "no te pedi", "te pedi solo"): eso se ve
    en el propio chat, no hace falta comprobar nada fuera
  - El usuario da una preferencia o una decision ("prefiero", "me gusta", "quiero que", "hazlo asi"): no hay nada
    que verificar
Una vez por mensaje del usuario (nunca un bucle). Telemetria: verificacion_continue / verificacion_ok_*.
"""

import json
import re
from pathlib import Path

# La respuesta EMPIEZA dando la razon (primeros ~160 caracteres, sin la linea del bufer)
RE_DA_RAZON = re.compile(
    r"(?i)^[\s*_>¡!\"'“«]*(s[ií],?\s+)?(tienes\s+(toda\s+la\s+|mucha\s+|toda\s+)?raz[oó]n|llevas\s+raz[oó]n|exact(o|amente)|"
    r"correct(o|ísimo|isimo)|efectivamente|en\s+efecto|as[ií]\s+es|diste\s+en\s+el\s+clavo|has\s+dado\s+en\s+el\s+clavo|"
    r"buen[ao]\s+(observaci[oó]n|punto|apunte|ojo)|totalmente\s+de\s+acuerdo|de\s+acuerdo\s+contigo|bien\s+visto|"
    r"muy\s+bien\s+visto|cierto)\b"
)
# el usuario habla de lo que Nova hizo en el chat (se comprueba leyendo la conversacion, no hace falta herramienta)
RE_SOBRE_EL_CHAT = re.compile(
    r"(?i)\b(te\s+dije|ya\s+te\s+dije|te\s+ped[ií]|no\s+te\s+ped[ií]|no\s+te\s+he\s+pedido|solo\s+te\s+ped[ií]|"
    r"te\s+he\s+dicho|no\s+te\s+dije|me\s+dijiste|dijiste\s+que|antes\s+dijiste|no\s+me\s+hiciste\s+caso)\b"
)
# Preferencias o decisiones del usuario: no hay verdad que comprobar
RE_PREFERENCIA = re.compile(
    r"(?i)\b(prefiero|me\s+gusta(n|r[ií]a)?|no\s+me\s+gusta|quiero\s+que|quisiera|hazlo\s+as[ií]|d[eé]jalo\s+as[ií]|"
    r"mejor\s+(hazlo|ponlo|d[eé]jalo|qu[ií]talo|usa|pon)|me\s+quedo\s+con|elijo|vamos\s+con)\b"
)
# el usuario pide comprobar
RE_VERIFICA = re.compile(
    r"(?i)(¿\s*seguro\s*\??|^\s*seguro\s*\?|est[aá]s\s+segur[ao]|/verifica\b|verif[ií]ca(lo|la|me)?\b|"
    r"compr[uú]eba(lo|la)?\b|contr[aá]sta(lo|la)?\b|invest[ií]ga(lo)?\s+antes|no\s+me\s+des\s+la\s+raz[oó]n)"
)
RE_SOLO_BUFER = re.compile(r"(?is)^\s*\[(BUFER EN|COMPACTACION AUTOMATICA|LIMITE DE SESION)[^\]]*\][^\n]*\n*")

MODO_PROFE = (
    "MODO PROFE (el usuario quiere APRENDER, no que le des la razon): empieza con ✅ 'Tenias razon' o ❌ 'No exactamente' "
    "(o 🟡 'En parte') segun lo que COMPROBASTE; luego el POR QUE en 2-3 lineas, sin rollo; y al final 'Para "
    "comprobarlo tu:' con el comando, el archivo o la busqueda exacta. Si se equivoca, diselo claro y con respeto."
)
MSG_CONTINUE = (
    "[HOOK NOVA · VERIFICACION] Le has dado la razon al usuario (\"{frase}\") SIN comprobar nada en este turno. "
    "No respondas de memoria para quedar bien. Ahora, sin repetir lo anterior: 1) compruebalo DE VERDAD con tus "
    "herramientas (lee el archivo o el codigo, ejecutalo, o busca la fuente oficial / documentacion); 2) responde en "
    + MODO_PROFE
)
MSG_SIN_VERIFICAR = (
    "[HOOK NOVA · VERIFICA] el usuario te pidio que lo COMPROBARAS y has contestado sin usar ninguna herramienta. "
    "Ahora: investiga de verdad (lee, ejecuta o busca la fuente) y responde en " + MODO_PROFE
)
MSG_PRE_VERIFICA = (
    "[HOOK NOVA · VERIFICA] el usuario pide que lo compruebes: investiga ANTES de responder (lee el archivo, ejecuta, "
    "o busca la fuente oficial). Nada de memoria ni de darle la razon por quedar bien. Responde en " + MODO_PROFE
)


def _limpiar_pedido(texto: str) -> str:
    return re.sub(r"(?s)<ADDITIONAL_METADATA>.*|<USER_SETTINGS_CHANGE>.*|</?USER_REQUEST>", "", texto or "").strip()


def turnos(transcript: str):
    """Genera, por cada mensaje del usuario: {'pedido', 'llamadas', 'final', 'id'}."""
    actual = None
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                tipo = o.get("type")
                if tipo == "USER_INPUT":
                    if actual:
                        yield actual
                    actual = {"pedido": _limpiar_pedido(str(o.get("content") or "")), "llamadas": 0, "final": "",
                              "id": str(o.get("step_index", ""))}
                elif tipo == "PLANNER_RESPONSE" and actual is not None:
                    actual["llamadas"] += len(o.get("tool_calls") or [])
                    # la linea del bufer (la pide otro freno) se quita; si detras hay respuesta, esa cuenta
                    contenido = RE_SOLO_BUFER.sub("", str(o.get("content") or "")).strip()
                    if contenido:
                        actual["final"] = contenido
    except OSError:
        pass
    if actual:
        yield actual


def ultimo_turno(transcript: str) -> dict:
    t = {"pedido": "", "llamadas": 0, "final": "", "id": ""}
    for t in turnos(transcript):
        pass
    return t


def apertura(final: str) -> str:
    return RE_SOLO_BUFER.sub("", final or "").lstrip()[:160]


def decidir(turno: dict, pedido: str = "") -> tuple[str, str]:
    """('sin_comprobar'|'sin_verificar'|'', frase o motivo ok_* para la telemetria)."""
    pedido = pedido or turno.get("pedido", "")
    inicio = apertura(turno.get("final", ""))
    pide_verificar = bool(RE_VERIFICA.search(pedido))
    m = RE_DA_RAZON.search(inicio)
    if not m and not pide_verificar:
        return "", ""
    if turno.get("llamadas"):
        return "", "ok_comprobo"
    if pide_verificar:
        return "sin_verificar", inicio[:120]
    if RE_SOBRE_EL_CHAT.search(pedido):
        return "", "ok_sobre_el_chat"
    if RE_PREFERENCIA.search(pedido):
        return "", "ok_preferencia"
    return "sin_comprobar", inicio[:120]


def mensaje(tipo: str, frase: str) -> str:
    return MSG_SIN_VERIFICAR if tipo == "sin_verificar" else MSG_CONTINUE.format(frase=frase.replace('"', "'")[:100])


# ------------------------------------------------------------------------------------------------------------------
# 23/11 (Claude, regla web-001 de aprendido.jsonl, x5): REVISION VISUAL antes de dar por terminado un cambio de web.
# Si en el turno Nova escribio/edito .html/.css/.js de un proyecto (fuera de .gemini) y cierra diciendo que esta listo
# SIN haber pasado herramientas\revision_visual\revisar.py despues del ultimo cambio -> 1 "continue".
# ------------------------------------------------------------------------------------------------------------------
RE_WEB = re.compile(r"(?i)\.(html?|css|js|jsx|tsx|vue|svelte)$")
RE_ESCRIBE = re.compile(r"(?i)(write|edit|replace|create)")
RE_DICE_LISTO = re.compile(
    r"(?i)\b(listo|list[ao]s|hecho|terminad[oa]|verificad[oa]|comprobad[oa]|ya\s+est[aá]|corregid[oa]|arreglad[oa]|"
    r"solucionad[oa]|funciona|qued[oó]|ya\s+no\s+(se\s+ve|parece|sale)|all\s+\d+\s+pages\s+ok|recarga\s+con)\b")
RE_NO_REVISES = re.compile(r"(?i)\b(no\s+(lo\s+)?revises|sin\s+revis(ar|i[oó]n)|no\s+hace\s+falta\s+(revisar|mirar))\b")
CASA = str(Path.home() / ".gemini").lower()
MSG_REVISION = (
    "[HOOK NOVA · REVISION VISUAL] Has cambiado {archivos} y vas a darlo por terminado SIN MIRARLO como lo ve el usuario "
    "(error web-001, ya van 5). Medir con Playwright o que compile NO es mirar. Ahora: "
    "<PYTHON> \"<NOVA_HOME>/antigravity/herramientas/revision_visual/revisar.py\" \"{carpeta}\" "
    "(si es un mockup de movil anade --marco <selector del marco>, p. ej. .phone-frame). Si sale REVISAR, arreglalo y "
    "repite. En tu respuesta pon el VEREDICTO, los problemas que vio y la ruta del informe.md."
)


def _ruta_args(args) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return ""
    if not isinstance(args, dict):
        return ""
    for k in ("Path", "TargetFile", "AbsolutePath", "FilePath", "path", "file_path"):
        v = args.get(k)
        if v:
            return _desescapar(str(v))
    return ""


def _desescapar(v: str) -> str:
    """Antigravity guarda cada argumento como texto JSON ("\"g:\\\\Mi unidad...\""): se decodifica para comparar rutas."""
    v = v.strip()
    if v.startswith('"'):
        try:
            v = json.loads(v)
        except ValueError:
            v = v.strip('"')
    return str(v).strip().strip("'")


def _comando(args) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return args
    if not isinstance(args, dict):
        return ""
    return _desescapar(str(args.get("CommandLine") or args.get("command") or ""))


def revision_turno(transcript: str) -> dict:
    """Del ultimo mensaje del usuario al final: archivos web cambiados, si paso revisar.py despues y la respuesta final."""
    info = {"pedido": "", "web": [], "revisado": False, "final": ""}
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                if o.get("type") == "USER_INPUT":
                    info = {"pedido": _limpiar_pedido(str(o.get("content") or "")), "web": [], "revisado": False,
                            "final": ""}
                elif o.get("type") == "PLANNER_RESPONSE":
                    for tc in o.get("tool_calls") or []:
                        nombre = str(tc.get("name") or "")
                        ruta = _ruta_args(tc.get("args"))
                        if RE_ESCRIBE.search(nombre) and RE_WEB.search(ruta) and not ruta.lower().startswith(CASA):
                            info["web"].append(ruta)
                            info["revisado"] = False  # un cambio despues de revisar obliga a revisar otra vez
                        elif "revision_visual" in _comando(tc.get("args")) and "revisar.py" in _comando(tc.get("args")):
                            info["revisado"] = True
                    contenido = RE_SOLO_BUFER.sub("", str(o.get("content") or "")).strip()
                    if contenido:
                        info["final"] = contenido
    except OSError:
        pass
    return info


def carpeta_web(rutas: list[str]) -> str:
    """La carpeta del proyecto: la mas cercana (subiendo) que tenga .html."""
    p = Path(rutas[-1]).parent
    for d in (p, *p.parents[:3]):
        try:
            if any(d.glob("*.html")):
                return str(d)
        except OSError:
            break
    return str(p)


def decidir_revision(info: dict, pedido: str = "") -> tuple[str, str]:
    """('revision_visual', archivos) si hay que frenar; ('', motivo_ok) si no."""
    if not info.get("web"):
        return "", ""
    if info.get("revisado"):
        return "", "ok_revisado"
    if RE_NO_REVISES.search(pedido or info.get("pedido", "")):
        return "", "ok_no_revises"
    if not RE_DICE_LISTO.search(info.get("final", "")):
        return "", "ok_no_dice_listo"
    nombres = list(dict.fromkeys(Path(r).name for r in info["web"]))
    return "revision_visual", ", ".join(nombres[:4])


def mensaje_revision(info: dict, archivos: str) -> str:
    return MSG_REVISION.format(archivos=archivos, carpeta=carpeta_web(info["web"]))
