"""
NOVA VOZ LIVE - fase 1 (17/11/2026, Claude) - la "secretaria" de voz de Nova, separada de Antigravity.
=========================================================================================================
Dos cerebros:
  - BOCA Y OIDOS: Gemini Live API (conversacion en tiempo real, < 1 s). Charla, pregunta lo que falte, resume.
  - OBRERA: Nova dentro de Antigravity. Recibe por CDP la orden ya bien redactada (puente_antigravity.py).

Flujo:
  1. Vosk local (coste cero) espera "Nova" a secas -> suena el "¿Si?" de Ayla y se abre la sesion Live.
  2. Hablas normal. Si es charla, contesta ella. Si es una tarea ("crea una web"), te pregunta lo necesario,
     te resume la orden y, con tu "si", la manda a Antigravity (herramienta enviar_a_nova).
  3. Un vigilante espera la linea "VOZ:" de Nova. Cuando llega, te avisa hablando, aunque la sesion ya
     se haya cerrado ("Nova termino: ...").
  4. La sesion se cierra sola tras INACTIVO_S sin hablar (o si dices "gracias, eso es todo"): no gasta tokens.

Monito: widget\\nova_widget.py, ventanita flotante FUERA de Antigravity (se abre y se cierra con este programa).
Voz: si esta instalado el pack de voz (Ayla, servidor en 127.0.0.1:5010, licencia aceptada) habla Ayla y el audio de
Gemini nunca suena; si no, habla la voz de Gemini. Los avisos fuera de la conversacion: Ayla o, de reserva, Edge.
Sin GEMINI_API_KEY no arranca: el guardian deja entonces la voz clasica (nova_voz.py) con el mismo monito flotante.
Altavoces: mientras Nova habla, el micro no se envia (que no se oiga a si misma). Con auriculares (--auriculares)
el micro va siempre abierto y la puedes interrumpir hablando.

    python nova_voz_live.py                 (Ayla si esta el pack de voz; si no, voz de Gemini. Altavoces)
    python nova_voz_live.py --voz gemini    (voz de Google "Kore" aunque este Ayla)
    python nova_voz_live.py --auriculares
    python nova_voz_live.py --texto "hola"  (prueba sin micro: manda un texto y escucha la respuesta)
    python nova_voz_live.py --prueba        (PRUEBA DE PUNTA A PUNTA: clave, micro, "Nova", Ayla, Gemini)

OJO: no lo arranques a la vez que nova_voz.py (los dos se pelearian por el micro y por la palabra "Nova").
Requisitos: el Python de Nova (google-genai, vosk, sounddevice, numpy, websocket-client, edge-tts; los pone el
Doctor) + GEMINI_API_KEY en las variables de Windows (gratis en https://aistudio.google.com/apikey). Solo Windows.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import glob
import json
import os
import queue
import random
import re
import socket
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.request
import winsound

import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import puente_antigravity as ag  # noqa: E402

try:  # nombre del usuario (perfil_usuario.json, lo crea el instalador)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
    from nova_comun import nombre_usuario  # noqa: E402
except Exception:  # noqa: BLE001
    def nombre_usuario(defecto: str = "") -> str:
        return defecto

# ==================================================================================================================
# CONFIGURACION
# ==================================================================================================================
MODELO = os.environ.get("NOVA_LIVE_MODELO", "gemini-3.8-live")
VOZ_GEMINI = os.environ.get("NOVA_LIVE_VOZ", "Kore")  # solo si se usa la voz de Gemini
INACTIVO_S = 20          # segundos sin hablar nadie -> se cierra la sesion (vuelve a esperar "Nova")
SILENCIO_MS = 700        # silencio que Gemini espera para dar tu frase por terminada
COLA_ALTAVOZ_S = 0.6     # tras hablar Nova, el micro sigue cerrado este rato (eco de la sala)
AYLA_INACTIVO_S = 900    # el servidor de Ayla suelta la GPU tras 15 min sin hablar (la comparte con Qwen)
AYLA_ESPERA_S = 45       # avisos fuera de conversacion: si Ayla no esta en 45 s, habla la voz de reserva
VOZ_RESERVA = True       # si Ayla falla o no esta, los avisos los dice la voz de Edge (no se queda muda)
# Permisos que exigen decir "confirmo" (no basta un "si"): borrar, publicar, tocar el sistema, ejecutar desde internet
RE_PELIGRO = re.compile(r"(?i)(\brm\b|\bdel\b|rmdir|remove-item|\bformat\b|git\s+push|--force|\bdrop\b|\bdelete\b|"
                        r"borrar|elimina|sudo|reg\s+(add|delete)|set-executionpolicy|shutdown|stop-process|taskkill|"
                        r"invoke-expression|\biex\b|curl[^|]*\|\s*(sh|bash)|npm\s+publish|vercel\s+--prod|\.ssh|"
                        r"credential|password|contrase)")
UMBRAL_VOZ = 450        # volumen minimo del micro (int16 RMS) para considerar que estas hablando (cara del monito)

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.expanduser(r"~\.gemini\antigravity")
CACHE_DIR = os.path.join(BASE, "voice_cache")
AYLA_DIR = os.path.join(CACHE_DIR, "ayla")
LOG = os.path.join(BASE, "memory", "registros", "nova_voz_live.log")
PID_VIEJO = os.path.join(CACHE_DIR, "nova_voz.pid")      # el de nova_voz.py (para no pisarnos)
PID_LIVE = os.path.join(CACHE_DIR, "nova_voz_live.pid")
VOZ_CLON_URL = "http://127.0.0.1:5010"
CLONADOR = os.path.join(BASE, "herramientas", "voz_clon", "clonador.py")
PYW_CLON = os.path.expanduser(r"~\nova_voz_clon\env_fq\Scripts\pythonw.exe")
PY_CLON = os.path.expanduser(r"~\nova_voz_clon\env_fq\Scripts\python.exe")
LOG_SERVIDOR = os.path.expanduser(r"~\nova_voz_clon\servidor.log")  # lo que dice el servidor de Ayla
VOZ_EDGE = "es-PE-CamilaNeural"
MODELO_VOSK = os.path.join(AQUI, "modelos", "vosk-model-small-es-0.42")
WIDGET = os.path.join(AQUI, "widget", "nova_widget.py")   # el monito flotante
PUERTO_WIDGET = 5011
AVISO_GASTO = os.path.join(CACHE_DIR, "aviso_gasto.json")  # lo deja el hook (nova_hook.py) en encargos por voz
VOZ_AVISOS = "marina"    # los avisos de tokens/gasto los dice Marina (pack de voz), no Ayla
VOZ_APAGADA = os.path.join(CACHE_DIR, "voz_apagada.flag")  # el guardian no relanza la voz mientras exista
FIN_TURNO = os.path.join(CACHE_DIR, "nova_turno_fin.json")  # lo escribe el hook Stop (nova_core\nova_hook_turno.py)

# Palabra de activacion: la misma logica probada de nova_voz.py v9 ("Nova" a secas + 2o paso sin gramatica)
GRAMATICA_VOSK = json.dumps(["nova", "novela", "nueva", "nuevo", "novia", "noventa", "nueve", "nota", "nos", "nada", "no",
                             "va", "vas", "voy", "ahi", "aqui", "alla", "noble", "bola", "boba", "lo", "la", "el", "en",
                             "eso", "esa", "tele", "[unk]"])
# v3.2: tambien acentos de Latinoamerica (un "Nova" colombiano lo oia como "no gana" con confianza 0.61)
RE_NOVA_LIBRE = re.compile(r"^(nova|no va|nota|noba|no ba|nueva|noa|nuba|nuva|nava|lova|bova|no vas|nobas|nos va|"
                           r"no gana|nogana|no ganas|no gá|noga|no ga|no vá|nová|no bá|novia|nueva va|la nova)$")
CONF_NOVA = 0.55  # confianza minima de Vosk para "nova" (antes 0.70; la 2a comprobacion sigue filtrando)

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

SISTEMA = """Eres Nova, la asistente de voz de <NOMBRE>. Le llamas por su nombre. Hablas espanol, cercana y con humor
ligero. Te escucha por voz, a menudo mientras cocina o hace otra cosa: responde SIEMPRE corto (1-2 frases), sin listas,
sin markdown, sin leer codigo ni enlaces en voz alta.

Tienes dos papeles:
1) CHARLA: preguntas rapidas, dudas, la hora, conversar. Respondes tu directamente.
2) PUENTE CON NOVA-OBRERA: todo lo que sea trabajo en el ordenador (crear o arreglar webs y codigo, investigar a fondo,
   archivos, documentos, buscar en internet y resumir, tareas del proyecto) lo hace Nova dentro de Antigravity.
   Tu NO lo haces ni finges hacerlo. Tu trabajo es:
   a. Entender bien el encargo. Si falta algo importante, pregunta (como mucho 2-3 preguntas cortas, de una en una).
      Si el usuario dice "tu decide" o "lo que veas", decide con sentido comun y no preguntes mas.
   b. Resumir en una frase lo que vas a mandar y preguntar "¿se lo mando?".
   c. Con su si, llamar a enviar_a_nova con una orden ESCRITA completa y clara (para leer, no para oir): que hay que
      hacer, detalles que dio el usuario, estilo, donde guardarlo si lo dijo. En espanol.
   d. Decir algo breve tipo "Hecho, ya esta en ello. Te aviso cuando termine."
   Si el usuario dice explicitamente "mandaselo tal cual" o la orden ya es clara y completa, envia sin preguntar.

Avisos: a veces recibiras mensajes que empiezan por [AVISO DEL SISTEMA]. No los dijo el usuario: es el resultado de
Nova-obrera. Cuentaselo al usuario en una o dos frases naturales.
PERMISOS: si recibes [AVISO DEL SISTEMA] PERMISO, Nova-obrera esta parada esperando que el usuario le de permiso en
Antigravity. Explicale en UNA frase sencilla que quiere hacer (en espanol, sin leer rutas enteras: solo el nombre del
archivo o la accion) y pregunta "¿Le doy permiso?". Si dice que si, llama a responder_permiso con decision "si"; si
dice que no, con "no". Si el aviso dice PELIGROSO, explica el riesgo y solo aprueba si el usuario dice la palabra
"confirmo". NUNCA respondas un permiso sin que el usuario lo haya dicho.
Si pregunta como va una tarea, usa estado_nova.
Si el usuario se despide o dice que eso es todo, despidete en 3-4 palabras y llama a terminar_conversacion.
Si solo te llama ("Nova") sin decir nada mas, contesta muy corto, por ejemplo "Dime".
"""

HERRAMIENTAS = [{"function_declarations": [
    {"name": "enviar_a_nova",
     "description": "Envia una orden de trabajo escrita a Nova (el agente que trabaja en Antigravity, en el ordenador). "
                    "Usala solo cuando el usuario haya confirmado el encargo.",
     "parameters": {"type": "OBJECT", "properties": {
         "orden": {"type": "STRING", "description": "La orden completa, clara y autosuficiente, en espanol."},
         "resumen": {"type": "STRING", "description": "Resumen de 3-6 palabras para nombrar la tarea."}},
         "required": ["orden", "resumen"]}},
    {"name": "estado_nova",
     "description": "Dice si Nova esta trabajando en algo, desde cuando, y la ultima respuesta que dio."},
    {"name": "responder_permiso",
     "description": "Responde el permiso que Nova-obrera esta esperando en Antigravity, SOLO con lo que el usuario acaba de "
                    "decir. 'si' = permitir solo esta vez; 'no' = denegar.",
     "parameters": {"type": "OBJECT", "properties": {
         "decision": {"type": "STRING", "enum": ["si", "no"], "description": "Lo que dijo el usuario."}},
         "required": ["decision"]}},
    {"name": "hora_actual",
     "description": "Devuelve la fecha y la hora exactas del ordenador del usuario (su hora local). Usala SIEMPRE que "
                    "pregunte la hora o la fecha; no la calcules ni la conviertas a otra zona."},
    {"name": "terminar_conversacion",
     "description": "Cierra la conversacion de voz cuando el usuario se despide o dice que eso es todo."},
]}]


# ==================================================================================================================
# UTILIDADES
# ==================================================================================================================
def log(texto: str):
    linea = f"[{time.strftime('%H:%M:%S')}] {texto}"
    try:
        print(linea, flush=True)
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d')}] {linea}\n")
    except OSError:
        pass


def pid_vivo(pid: int) -> bool:
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(codigo))
    ctypes.windll.kernel32.CloseHandle(h)
    return codigo.value == 259  # STILL_ACTIVE


def leer_pid(ruta) -> int:
    try:
        with open(ruta, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def clave_api() -> str | None:
    for n in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(n):
            return os.environ[n]
    try:  # la variable se guardo en Windows despues de abrir esta terminal
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            for n in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                try:
                    v = winreg.QueryValueEx(k, n)[0]
                    if v:
                        return v
                except OSError:
                    pass
    except OSError:
        pass
    try:  # v3.2: la que guarda nova_claves.py en config\secrets.env
        with open(os.path.expanduser(r"~\.gemini\config\secrets.env"), encoding="utf-8-sig") as f:
            for linea in f:
                k, _, v = linea.partition("=")
                if k.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v.strip():
                    return v.strip()
    except OSError:
        pass
    return None


def clip_ayla(grupo: str) -> str | None:
    opciones = glob.glob(os.path.join(AYLA_DIR, f"{grupo}_*.wav"))
    return random.choice(opciones) if opciones else None


def sonar_wav(ruta: str | None) -> bool:
    if ruta and os.path.exists(ruta):
        winsound.PlaySound(ruta, winsound.SND_FILENAME)
        return True
    return False


def pitido():
    winsound.Beep(880, 90)
    winsound.Beep(1320, 110)


# ==================================================================================================================
# VOZ DE NOVA: AYLA (pack de voz, licencia propia: LICENCIA_VOCES.md)
# Voz oficial = rol "nova" -> voz "ayla" (datos\voz_clon\roles.json -> %USERPROFILE%\nova_voz_clon\voces\ayla).
# Nunca suena otra voz: ni la de Gemini ni la de Edge. Si Ayla esta cargando, suena un clip de Ayla ya grabado
# y la frase espera a que este lista.
# ==================================================================================================================
def pack_voz_listo() -> bool:
    """Pack de voz instalado (motor + clonador) y licencia de las voces aceptada por el usuario."""
    return (os.path.exists(PYW_CLON) and os.path.exists(CLONADOR)
            and os.path.exists(os.path.expanduser(r"~\nova_voz_clon\licencia_voces_aceptada.json")))


class VozAyla:
    def __init__(self, activa: bool = True):
        self.activa = activa  # False = sin pack de voz: los avisos van directos a la voz de reserva
        self.ocupada = 0
        self.hasta = 0.0
        self.lock = threading.Lock()
        self.cola: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._trabajador, daemon=True).start()

    @staticmethod
    def estado_servidor(timeout=1.5) -> str:
        """'lista' (modelo cargado), 'cargando' (servidor arriba, modelo aun no) o 'apagado'."""
        try:
            with urllib.request.urlopen(VOZ_CLON_URL + "/", timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8") or "{}")
                return "lista" if d.get("modelo_cargado") else "cargando"
        except Exception:
            return "apagado"

    @staticmethod
    def lista(timeout=1.5) -> bool:
        return VozAyla.estado_servidor(timeout) == "lista"

    _arranque = threading.Lock()

    @staticmethod
    def servidor_cargando() -> bool:
        """17/11: ¿ya hay un servidor de Ayla arrancando? (cargar el modelo tarda ~2 min; dos a la vez se pisan la GPU)
        Solo cuentan procesos de Python: la propia consulta de PowerShell lleva el texto en su linea de comandos y se
        contaba a si misma -> parecia que el servidor ya cargaba y NUNCA se arrancaba (visto en otro equipo)."""
        try:
            r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?(\\.exe)?$' -and "
                                "$_.CommandLine -like '*clonador.py*servidor*' }).Count"],
                               capture_output=True, text=True, timeout=10, creationflags=0x08000000)
            return int((r.stdout or "0").strip() or 0) > 0
        except Exception:
            return False

    def arrancar(self, esperar_s=20) -> bool:
        if self.lista():
            return True
        if not (os.path.exists(PYW_CLON) and os.path.exists(CLONADOR)):
            return False
        with VozAyla._arranque:  # un solo arranque aunque lo pidan varios hilos a la vez
            estado = self.estado_servidor()
            if estado == "lista":
                return True
            if estado == "cargando":  # servidor arriba pero modelo soltado (inactividad): que lo cargue
                try:
                    urllib.request.urlopen(urllib.request.Request(VOZ_CLON_URL + "/calentar", data=b"{}",
                                                                  headers={"Content-Type": "application/json"}), timeout=5)
                except Exception:
                    pass
            elif not self.servidor_cargando():
                try:
                    # v3.2: python.exe con consola OCULTA (como cuando se lanza a mano, que carga bien) y la
                    # salida al log: antes se tiraba a DEVNULL y si fallaba no quedaba rastro.
                    exe = PY_CLON if os.path.exists(PY_CLON) else PYW_CLON
                    with open(LOG_SERVIDOR, "a", encoding="utf-8") as salida:
                        salida.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Nova Voz Live arranca el servidor\n")
                        subprocess.Popen([exe, "-u", CLONADOR, "servidor", "--inactivo", str(AYLA_INACTIVO_S)],
                                         creationflags=0x08000000, stdin=subprocess.DEVNULL, stdout=salida,
                                         stderr=subprocess.STDOUT, close_fds=True)
                    log("Cargando la voz de Ayla (tarda ~2 min la primera vez)")
                except Exception:
                    return False
        fin = time.time() + esperar_s
        while time.time() < fin:
            time.sleep(0.5)
            if self.lista():
                return True
        return False

    def calentar(self):
        def _h():
            if self.arrancar():
                try:
                    urllib.request.urlopen(urllib.request.Request(VOZ_CLON_URL + "/calentar", data=b"{}",
                                                                  headers={"Content-Type": "application/json"}), timeout=5)
                except Exception:
                    pass
        threading.Thread(target=_h, daemon=True).start()

    def hablando(self) -> bool:
        return self.ocupada > 0 or not self.cola.empty() or time.time() < self.hasta

    def _marca(self, delta):
        with self.lock:
            self.ocupada += delta
            if delta < 0:
                self.hasta = time.time() + COLA_ALTAVOZ_S

    def decir_ya(self, texto: str) -> bool:
        """Dice el texto con la voz de Ayla y espera a que termine. Bloquea. Si Ayla esta cargando: clip de Ayla
        ("un momento") y espera hasta AYLA_ESPERA_S. Nunca usa otra voz (salvo VOZ_RESERVA = True)."""
        texto = re.sub(r"[`*_#>\[\]]", "", texto).strip()
        if not texto:
            return True
        self._marca(+1)
        try:
            if not self.activa:
                return self._edge(texto) or (pitido() and False)
            if not self.lista():
                sonar_wav(clip_ayla("relleno"))  # voz de Ayla ya grabada mientras carga
            if self.arrancar(esperar_s=AYLA_ESPERA_S):
                datos = json.dumps({"voz": "nova", "texto": texto}).encode("utf-8")
                req = urllib.request.Request(VOZ_CLON_URL + "/hablar", data=datos,
                                             headers={"Content-Type": "application/json"})
                t0 = time.time()
                try:
                    with urllib.request.urlopen(req, timeout=300) as r:
                        if json.loads(r.read().decode("utf-8")).get("ok"):
                            return True
                except Exception as e:
                    log(f"Voz de Ayla fallo ({type(e).__name__})")
                    if time.time() - t0 > 4:
                        return True  # fallo a mitad: no repetir todo
            if VOZ_RESERVA:
                return self._edge(texto)
            log(f"(sin voz: Ayla no disponible) {texto}")
            pitido()
            return False
        finally:
            self._marca(-1)

    @staticmethod
    def _edge(texto: str) -> bool:
        try:
            import edge_tts
            ruta = os.path.join(CACHE_DIR, "live_tts.mp3")
            asyncio.run(edge_tts.Communicate(texto[:600], VOZ_EDGE, rate="+4%").save(ruta))
            w = ctypes.windll.winmm
            w.mciSendStringW("close nova_live", None, 0, None)
            w.mciSendStringW(f'open "{ruta}" type mpegvideo alias nova_live', None, 0, None)
            w.mciSendStringW("play nova_live wait", None, 0, None)
            w.mciSendStringW("close nova_live", None, 0, None)
            return True
        except Exception as e:
            log(f"Edge TTS fallo: {e}")
            return False

    # --- frases de la conversacion: la 1a suena en cuanto esta; las siguientes se juntan (menos cortes) ---
    def encolar(self, frase: str):
        if frase.strip():
            self.cola.put(frase.strip())

    def vaciar(self):
        try:
            while True:
                self.cola.get_nowait()
        except queue.Empty:
            pass

    def _trabajador(self):
        while True:
            frase = self.cola.get()
            self._marca(+1)  # que no parezca "callada" entre coger la frase y empezar a sonar
            try:
                partes = [frase]
                try:
                    while True:
                        partes.append(self.cola.get_nowait())
                except queue.Empty:
                    pass
                self.decir_ya(" ".join(partes))
            finally:
                self._marca(-1)


# ==================================================================================================================
# ALTAVOZ PARA LA VOZ DE GEMINI (PCM 24 kHz)
# ==================================================================================================================
class Altavoz:
    def __init__(self):
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.ultimo = 0.0
        self.stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype="int16", blocksize=1200,
                                         callback=self._cb)
        self.stream.start()

    def _cb(self, out, frames, _t, _s):
        n = frames * 2
        with self.lock:
            trozo = bytes(self.buf[:n])
            del self.buf[:n]
        if trozo:
            self.ultimo = time.time()
        out[:len(trozo)] = trozo
        if len(trozo) < n:
            out[len(trozo):] = b"\x00" * (n - len(trozo))

    def poner(self, pcm: bytes):
        with self.lock:
            self.buf += pcm

    def limpiar(self):
        with self.lock:
            self.buf.clear()

    def hablando(self) -> bool:
        with self.lock:
            if self.buf:
                return True
        return time.time() - self.ultimo < COLA_ALTAVOZ_S

    def sonando_ya(self) -> bool:
        """Sale sonido ahora mismo (sin la cola de seguridad del micro): para la cara del monito."""
        with self.lock:
            if self.buf:
                return True
        return time.time() - self.ultimo < 0.15


# ==================================================================================================================
# NOVA VOZ LIVE
# ==================================================================================================================
class NovaLive:
    def __init__(self, args):
        from google import genai
        self.args = args
        clave = clave_api()
        if not clave:
            raise SystemExit("Falta GEMINI_API_KEY (o GOOGLE_API_KEY) en las variables de Windows "
                             "(gratis en https://aistudio.google.com/apikey).")
        self.cliente = genai.Client(api_key=clave, http_options={"api_version": "v1beta"})
        self.usar_ayla = args.voz == "ayla" or (args.voz == "auto" and pack_voz_listo())
        self.ayla = VozAyla(activa=self.usar_ayla)
        self.altavoz = Altavoz()
        self.tarea: dict | None = None        # la tarea que Nova-obrera tiene entre manos
        self.ultima_respuesta = ""
        self.sesion_activa = False
        self.loop: asyncio.AbstractEventLoop | None = None
        self.avisos: asyncio.Queue | None = None
        self.mic: asyncio.Queue | None = None
        self._cara = ""
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ayla_lista = False
        self.ayla_sonando = False        # el servidor de Ayla dice que sale audio por el altavoz AHORA
        self.ultima_voz_usuario = 0.0    # ultima vez que el micro oyo voz (volumen por encima del ruido)
        self._ruido = 300.0              # nivel de ruido de fondo del micro (se ajusta solo)
        self.turno_pendiente = False     # hablaste y Gemini aun no termino de responder
        self.herramientas = 0            # herramientas en curso (enviar a Nova, hora...)
        self._fija = ("", 0.0)           # cara puesta a mano un rato (mirando al oir "Nova", error)
        self.permiso: dict | None = None  # permiso que Nova-obrera espera en Antigravity
        self._permisos_vistos: set[str] = set()
        self.despertar_con: str | None = None  # aviso que abre una conversacion sin decir "Nova" (p. ej. un permiso)
        self.ultimo_dicho = ""           # lo que dijiste en este turno (para exigir "confirmo" en lo peligroso)
        if not args.texto:
            threading.Thread(target=self._vigilar_permisos, daemon=True).start()
        if self.usar_ayla:
            threading.Thread(target=self._vigilar_ayla, daemon=True).start()
        threading.Thread(target=self._director_de_caras, daemon=True).start()

    def _vigilar_ayla(self):
        """4 veces por segundo: ¿Ayla esta cargada? ¿esta sonando? (para el monito y para no hablar con otra voz)"""
        avisado = False
        while True:
            try:
                with urllib.request.urlopen(VOZ_CLON_URL + "/", timeout=0.6) as r:
                    d = json.loads(r.read().decode("utf-8") or "{}")
            except Exception:
                d = {}
            self.ayla_lista = bool(d.get("modelo_cargado"))
            self.ayla_sonando = bool(d.get("sonando"))
            if self.ayla_lista and not avisado:
                log("Voz de Ayla lista")
            avisado = self.ayla_lista
            time.sleep(0.25)

    # ------------------------------------------------------------------ permisos de Antigravity por voz
    def _aviso_gasto(self):
        """17/11: el hook (encargos por voz) ya no para a Nova por gasto: deja aviso_gasto.json y aqui lo dice MARINA
        (voz de los avisos de tokens), sin abrir conversacion ni gastar tokens de audio."""
        try:
            m = os.path.getmtime(AVISO_GASTO)
        except OSError:
            return
        if m <= self._gasto_visto:
            return
        self._gasto_visto = m
        try:
            with open(AVISO_GASTO, encoding="utf-8") as f:
                k = int(json.load(f).get("tokens", 0)) // 1000
        except (OSError, ValueError):
            return
        quien = nombre_usuario()
        texto = f"{quien + ', e' if quien else 'E'}l encargo de Nova ya lleva {k} mil tokens. Si quieres pararlo, dímelo."
        log(f"Aviso de gasto (Marina): {k}k tokens")
        try:
            datos = json.dumps({"voz": VOZ_AVISOS, "estilo": "crudo", "texto": texto}).encode("utf-8")
            req = urllib.request.Request(VOZ_CLON_URL + "/hablar", data=datos, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=120).read()
        except Exception as e:
            log(f"No pude dar el aviso de gasto con Marina ({type(e).__name__})")

    def _vigilar_permisos(self):
        """Cada 1,5 s: ¿Nova-obrera se ha quedado esperando un permiso? Si es nuevo, te lo pregunta (abre conversacion
        sola si hace falta). Nunca responde por su cuenta: solo con lo que tu digas."""
        try:
            self._gasto_visto = os.path.getmtime(AVISO_GASTO)  # avisos viejos no se repiten al arrancar
        except OSError:
            self._gasto_visto = 0.0
        while True:
            time.sleep(1.5)
            self._aviso_gasto()
            p = ag.permiso_pendiente()
            if not p:
                self.permiso = None
                continue
            clave = p["texto"][:300]
            if clave in self._permisos_vistos:
                continue
            self._permisos_vistos.add(clave)
            p["peligroso"] = bool(RE_PELIGRO.search(p["texto"]))
            self.permiso = p
            log(f"PERMISO pedido por Nova{' (PELIGROSO)' if p['peligroso'] else ''}: {' | '.join(p['texto'].splitlines())[:300]}")
            if p["clicable"]:
                aviso = (f"PERMISO: Nova-obrera esta parada esperando permiso en Antigravity. Lo que pide: {p['texto']}"
                         + (" PELIGROSO: para aprobarlo el usuario tiene que decir 'confirmo'." if p["peligroso"] else ""))
            else:
                aviso = (f"PERMISO: Nova-obrera esta esperando algo en Antigravity que no puedo pulsar yo: {p['texto'][:300]}. "
                         "Dile al usuario que lo mire en la pantalla.")
            if self.sesion_activa and self.loop and self.avisos is not None:
                self.loop.call_soon_threadsafe(self.avisos.put_nowait, aviso)
            else:
                self.despertar_con = aviso

    def contestar_permiso(self, decision: str) -> dict:
        p = self.permiso
        if not p:
            return {"error": "Ya no hay ningun permiso pendiente (quiza lo respondio el usuario en la pantalla)."}
        si = decision == "si"
        if not self.ultimo_dicho.strip():  # v3.2: Gemini lo llamo una vez ANTES de preguntar (visto en un equipo real)
            log("Permiso: Gemini quiso responder sin que el usuario hablara -> bloqueado")
            return {"error": "El usuario todavia no ha contestado. Preguntale primero y espera a que responda."}
        dicho = unicodedata.normalize("NFKD", self.ultimo_dicho.lower()).encode("ascii", "ignore").decode()
        if si and p.get("peligroso") and "confirmo" not in dicho:
            return {"error": "Es PELIGROSO y el usuario no ha dicho 'confirmo'. Explicale el riesgo y pidele que diga 'confirmo'."}
        if not p.get("clicable"):
            return {"error": "No puedo pulsarlo yo; dile al usuario que lo mire en Antigravity."}
        ok, info = ag.responder_permiso(si)
        log(f"Permiso {'CONCEDIDO (solo esta vez)' if si else 'DENEGADO'} por voz: {ok} ({info})")
        if ok:
            self.permiso = None
            return {"resultado": "permitido solo esta vez, Nova sigue" if si else "denegado"}
        return {"error": f"No pude pulsarlo: {info}. Dile al usuario que lo haga en la pantalla."}

    # ------------------------------------------------------------------ caras del monito segun lo que pasa DE VERDAD
    def fijar_cara(self, estado: str, segundos: float):
        self._fija = (estado, time.time() + segundos)
        self.cara(estado)

    def cara_que_toca(self) -> str:
        """hablando = sale sonido de Ayla · escuchando = estas hablando tu (o te espera) ·
        pensando = terminaste de hablar y Nova piensa / consulta / prepara la voz, o Nova-obrera trabaja."""
        ahora = time.time()
        if ahora < self._fija[1]:
            return self._fija[0]
        if self.ayla_sonando or self.altavoz.sonando_ya():
            return "hablando"
        preparando_voz = self.ayla.ocupada > 0 or not self.ayla.cola.empty()
        if self.sesion_activa:
            if ahora - self.ultima_voz_usuario < 0.6:
                return "escuchando"
            if self.turno_pendiente or self.herramientas > 0 or preparando_voz:
                return "pensando"
            return "escuchando"
        if preparando_voz or (self.tarea and self.tarea["estado"] == "trabajando"):
            return "pensando"
        return "espera"

    def _director_de_caras(self):
        while True:
            try:
                self.cara(self.cara_que_toca())
            except Exception:
                pass
            time.sleep(0.15)

    # ------------------------------------------------------------------ el monito (widget flotante fuera de Antigravity)
    def abrir_widget(self):
        """Arranca widget\\nova_widget.py (si ya hay uno abierto, el nuevo se cierra solo)."""
        if self.args.sin_monito or not os.path.exists(WIDGET):
            return
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        try:
            subprocess.Popen([pyw if os.path.exists(pyw) else sys.executable, WIDGET],
                             creationflags=0x08000000 | 0x00000008, close_fds=True)
        except Exception as e:
            log(f"No pude abrir el monito: {e}")

    def cara(self, estado: str, texto: str = ""):
        """Cambia la cara del monito (solo si cambia). UDP local: instantaneo y nunca bloquea."""
        if estado == self._cara and not texto:
            return
        self._cara = estado
        try:
            self._udp.sendto(json.dumps({"estado": estado, "texto": texto}).encode("utf-8"), ("127.0.0.1", PUERTO_WIDGET))
        except OSError:
            pass

    def _repetir_cara(self):
        """Cada 3 s recuerda la cara actual al monito (por si se abrio despues o se reinicio).
        Si alguien pidio apagar la voz (clic derecho en el monito -> Apagar), se cierra todo."""
        while True:
            time.sleep(3)
            if os.path.exists(VOZ_APAGADA) and not self.args.texto:
                log("Apagada desde el monito. El guardian no la vuelve a abrir hasta reabrir Antigravity.")
                try:
                    self._udp.sendto(b'{"cmd": "salir"}', ("127.0.0.1", PUERTO_WIDGET))
                finally:
                    os._exit(0)
            if self._cara:
                try:
                    self._udp.sendto(json.dumps({"estado": self._cara}).encode("utf-8"), ("127.0.0.1", PUERTO_WIDGET))
                except OSError:
                    pass

    # ------------------------------------------------------------------ estado de "esta hablando Nova"
    def nova_habla(self) -> bool:
        return self.ayla.hablando() or self.altavoz.hablando()

    # ------------------------------------------------------------------ microfono -> cola asyncio
    def _cb_mic(self, datos, _f, _t, _s):
        # volumen de este trozo: si pasa claramente del ruido de fondo, es que estas hablando (cara "escuchando")
        try:
            muestras = np.frombuffer(bytes(datos), dtype=np.int16).astype(np.float32)
            nivel = float(np.sqrt(np.mean(muestras * muestras))) if muestras.size else 0.0
            if nivel > max(UMBRAL_VOZ, self._ruido * 3) and not self.nova_habla():
                self.ultima_voz_usuario = time.time()
            elif nivel < self._ruido * 2:
                self._ruido = 0.98 * self._ruido + 0.02 * nivel
        except Exception:
            pass
        if self.loop and self.mic is not None:
            self.loop.call_soon_threadsafe(self.mic.put_nowait, bytes(datos))

    def _casi(self, motivo: str):
        """Oyo algo parecido a 'Nova' y no lo dio por bueno (para afinar). Nunca apunta lo que se dice."""
        if time.time() - getattr(self, "_casi_t", 0) > 10:
            self._casi_t = time.time()
            log(f"Casi 'Nova': {motivo}")

    # ------------------------------------------------------------------ tareas de Nova-obrera
    def enviar_orden(self, orden: str, resumen: str) -> dict:
        if self.tarea and self.tarea["estado"] == "trabajando":
            mins = int((time.time() - self.tarea["desde"]) / 60)
            return {"error": f"Nova sigue ocupada con '{self.tarea['resumen']}' (hace {mins} min). "
                             "Dile al usuario que espere a que termine o que lo pida despues."}
        ok, info, antes = ag.enviar(orden)
        if not ok:
            log(f"No se pudo enviar a Antigravity: {info}")
            return {"error": f"No pude enviarla a Antigravity ({info}). Dile al usuario que revise que Antigravity "
                             "este abierto con el chat visible."}
        self.tarea = {"orden": orden, "resumen": resumen or orden[:40], "desde": time.time(),
                      "estado": "trabajando", "antes": antes}
        log(f"ORDEN ENVIADA ({info}): {orden}")
        threading.Thread(target=self._vigilar_tarea, args=(self.tarea,), daemon=True).start()
        return {"resultado": "enviada", "nota": "Nova ya esta trabajando. Avisaras cuando termine."}

    @staticmethod
    def _fin_por_hook(desde: float) -> dict | None:
        """Senal del hook Stop de Antigravity (nova_hook_turno.py): Nova acabo su turno despues de 'desde'."""
        try:
            with open(FIN_TURNO, encoding="utf-8") as f:
                d = json.load(f)
            if float(d.get("hora", 0)) <= desde + 1:
                return None
            # 17/11 (prueba fantasma): Nova cerro el turno con "1 task running" (descargando fotos) y habria dicho
            # "termine" a medias. Con tareas en segundo plano (fullyIdle False) y sin linea VOZ: aun NO ha terminado.
            if d.get("fullyIdle") is False and not d.get("voz"):
                return None
            return d
        except (OSError, ValueError):
            return None

    def _vigilar_tarea(self, tarea: dict):
        """Espera el fin de la tarea: 1o la senal del hook Stop (al instante); de reserva, la linea VOZ: en pantalla."""
        hook = {}

        def por_hook():
            d = self._fin_por_hook(tarea["desde"])
            if d:
                hook.update(d)
            return bool(d)

        resp = ag.esperar_respuesta(tarea["antes"], parar=por_hook)
        if hook:
            via = "hook"
            resp = hook.get("voz") or ""
            if not resp:
                resto = re.sub(r"\s+", " ", hook.get("texto", "")).strip()
                resp = (f"Terminé. {resto[:280]}" if resto else "Terminé, te lo dejé en Antigravity.")
        else:
            via = "pantalla"
        if resp:
            log(f"Fin de tarea detectado por {via}")
        if resp is None:
            tarea["estado"] = "sin respuesta"
            log(f"Nova no dio linea VOZ: para '{tarea['resumen']}'")
            self.avisar(f"Nova no ha dado respuesta sobre '{tarea['resumen']}' en 20 minutos. "
                        "Puede que este esperando un permiso en Antigravity.")
            return
        tarea["estado"] = "terminada"
        self.ultima_respuesta = resp
        log(f"NOVA TERMINO '{tarea['resumen']}': {resp}")
        self.avisar(f"Nova termino '{tarea['resumen']}'. Su respuesta: {resp}", directo=resp)

    def estado(self) -> dict:
        if not self.tarea:
            return {"estado": "libre", "ultima_respuesta": self.ultima_respuesta or "ninguna"}
        mins = round((time.time() - self.tarea["desde"]) / 60, 1)
        return {"estado": self.tarea["estado"], "tarea": self.tarea["resumen"], "minutos": mins,
                "ultima_respuesta": self.ultima_respuesta or "ninguna todavia"}

    def avisar(self, texto: str, directo: str | None = None):
        """Si hay conversacion abierta, se lo cuenta Gemini. Si no, lo dice Ayla directamente."""
        if self.sesion_activa and self.loop and self.avisos is not None:
            self.loop.call_soon_threadsafe(self.avisos.put_nowait, texto)
        else:
            sonar_wav(clip_ayla("ok")) or pitido()
            self.ayla.decir_ya(directo or texto)

    # ------------------------------------------------------------------ bucle principal: esperar "Nova"
    async def principal(self):
        import vosk
        vosk.SetLogLevel(-1)
        self.loop = asyncio.get_running_loop()
        self.mic = asyncio.Queue()
        if self.usar_ayla:
            self.ayla.calentar()
        self.abrir_widget()
        threading.Thread(target=self._repetir_cara, daemon=True).start()
        if self.args.texto:
            await self.conversar(texto_inicial=self.args.texto)
            await asyncio.sleep(1)
            while self.nova_habla():
                await asyncio.sleep(0.3)
            return
        modelo = vosk.Model(MODELO_VOSK)
        with sd.RawInputStream(samplerate=16000, blocksize=1600, dtype="int16", channels=1, callback=self._cb_mic):
            log(f"Lista. Di 'Nova' para hablar. (modelo {MODELO}, voz {'Ayla' if self.usar_ayla else 'Gemini'}, "
                f"{'auriculares' if self.args.auriculares else 'altavoces'})")
            while True:
                rec = vosk.KaldiRecognizer(modelo, 16000, GRAMATICA_VOSK)
                rec.SetWords(True)
                trozo = bytearray()
                aviso = None
                while True:
                    datos = await self.mic.get()
                    if self.despertar_con:  # p. ej. Nova pide un permiso: Nova Voz te habla sin que digas "Nova"
                        aviso, self.despertar_con = self.despertar_con, None
                        break
                    if self.nova_habla():  # su propia voz no cuenta
                        if trozo:
                            rec = vosk.KaldiRecognizer(modelo, 16000, GRAMATICA_VOSK)
                            rec.SetWords(True)
                            trozo = bytearray()
                        continue
                    trozo += datos
                    if len(trozo) > 16000 * 2 * 15:
                        del trozo[:len(trozo) - 16000 * 2 * 15]
                    if rec.AcceptWaveform(datos):
                        r = json.loads(rec.Result())
                        pal = [w for w in r.get("result", []) if w.get("word") != "[unk]"]
                        suelta = (len(pal) == 1 and pal[0]["word"] == "nova" and pal[0].get("conf", 0) >= CONF_NOVA
                                  and len(r.get("result", [])) <= 2)
                        if suelta:
                            libre = vosk.KaldiRecognizer(modelo, 16000)
                            libre.AcceptWaveform(bytes(trozo))
                            if RE_NOVA_LIBRE.match(json.loads(libre.FinalResult()).get("text", "").strip().lower()):
                                break
                            self._casi("paso 1 OK, la 2a comprobacion no lo vio claro")
                        elif any(w.get("word") == "nova" for w in pal):
                            conf = max(w.get("conf", 0) for w in pal if w.get("word") == "nova")
                            self._casi(f"confianza {conf:.2f} (minimo {CONF_NOVA:.2f}), {len(pal)} palabra(s)")
                        trozo = bytearray()
                if aviso:
                    log("Nova Voz abre conversacion por un aviso (permiso)")
                    await asyncio.to_thread(lambda: sonar_wav(clip_ayla("ok")) or pitido())
                else:
                    log("Me llamaste")
                    self.fijar_cara("mirando", 1.5)  # "¡Te oigo!"
                    if self.usar_ayla:
                        self.ayla.calentar()
                    await asyncio.to_thread(lambda: sonar_wav(clip_ayla("wake")) or pitido())
                while not self.mic.empty():  # lo que se grabo mientras sonaba el "¿Si?" no cuenta
                    self.mic.get_nowait()
                try:
                    await self.conversar(texto_inicial=f"[AVISO DEL SISTEMA] {aviso}" if aviso else None)
                except Exception as e:
                    log(f"Error en la conversacion: {type(e).__name__}: {e}")
                    self.fijar_cara("error", 4)
                    pitido()
                    await asyncio.sleep(4)
                self.turno_pendiente, self.herramientas = False, 0
                while not self.mic.empty():
                    self.mic.get_nowait()

    # ------------------------------------------------------------------ una conversacion (sesion Live)
    async def conversar(self, texto_inicial: str | None = None):
        from google.genai import types
        ahora = time.localtime()
        sistema = SISTEMA.replace("<NOMBRE>", nombre_usuario("el usuario")) + (f"\nHoy es {DIAS[ahora.tm_wday]} {time.strftime('%d/%m/%Y', ahora)}. Para la hora usa SIEMPRE "
                             "la herramienta hora_actual (nunca la calcules ni la conviertas)."
                             f"\nEstado de Nova-obrera ahora mismo: {json.dumps(self.estado(), ensure_ascii=False)}")
        if self.usar_ayla and not self.ayla_lista:
            log("Ayla aun cargando: mientras tanto contesta la voz de Gemini")
            self.ayla.calentar()
        config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": sistema,
            "tools": HERRAMIENTAS,
            "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": VOZ_GEMINI}}},
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "realtime_input_config": {"automatic_activity_detection": {"silence_duration_ms": SILENCIO_MS}},
        }
        self.avisos = asyncio.Queue()
        fin = asyncio.Event()
        # "ayla": voz de este turno. Con --voz ayla (por defecto) SIEMPRE Ayla: el audio de Gemini nunca suena
        # (derechos de voz); con --voz gemini, la voz de Gemini.
        estado = {"actividad": time.time(), "cerrar_tras_hablar": False, "frase": "", "texto_turno": "", "ayla": None}

        def ayla_turno() -> bool:
            if estado["ayla"] is None:
                estado["ayla"] = bool(self.usar_ayla and (self.ayla_lista or VozAyla.lista(0.5)))
                if self.usar_ayla and not estado["ayla"]:
                    log("Ayla aun no esta lista: este turno habla la voz de Gemini")
            return estado["ayla"]
        t_conexion = time.time()
        async with self.cliente.aio.live.connect(model=MODELO, config=config) as s:
            self.sesion_activa = True
            self.turno_pendiente = bool(texto_inicial)
            log(f"Conversacion abierta ({time.time() - t_conexion:.1f} s en conectar)")

            def hablando_ahora():
                return self.nova_habla()

            async def mandar_mic():
                silencio = b"\x00" * 3200
                while not fin.is_set():
                    datos = await self.mic.get()
                    if hablando_ahora():
                        estado["actividad"] = time.time()
                        if not self.args.auriculares:
                            datos = silencio  # que no se oiga a si misma por los altavoces
                    await s.send_realtime_input(audio=types.Blob(data=datos, mime_type="audio/pcm;rate=16000"))

            async def mandar_avisos():
                while not fin.is_set():
                    aviso = await self.avisos.get()
                    estado["actividad"] = time.time()
                    await s.send_realtime_input(text=f"[AVISO DEL SISTEMA] {aviso}")

            async def guardian():
                while not fin.is_set():
                    await asyncio.sleep(0.5)
                    if hablando_ahora():
                        estado["actividad"] = time.time()
                        continue
                    if estado["cerrar_tras_hablar"] and time.time() - estado["actividad"] > 1.0:
                        fin.set()
                    elif time.time() - estado["actividad"] > INACTIVO_S:
                        log("Silencio: cierro la conversacion")
                        fin.set()

            def soltar_frases(final=False):
                """Voz de Ayla: va diciendo frases completas segun llega la transcripcion de Gemini."""
                txt = estado["frase"]
                if final:
                    corte = len(txt)
                else:
                    m = list(re.finditer(r"[.!?…](\s|$)", txt))
                    corte = m[-1].end() if m else 0
                if corte:
                    self.ayla.encolar(txt[:corte])
                    estado["frase"] = txt[corte:]

            async def recibir():
                while not fin.is_set():
                    hubo = False
                    async for r in s.receive():
                        hubo = True
                        estado["actividad"] = time.time()
                        sc = r.server_content
                        if r.go_away is not None:
                            log("Gemini pide cerrar la sesion (limite de tiempo)")
                            fin.set()
                            return
                        if r.tool_call:
                            await atender_herramientas(r.tool_call)
                        if not sc:
                            continue
                        if sc.interrupted:
                            self.altavoz.limpiar()
                            self.ayla.vaciar()
                            estado["frase"] = ""
                            estado["ayla"] = None
                        if sc.model_turn and not ayla_turno():
                            for p in sc.model_turn.parts or []:
                                if p.inline_data and p.inline_data.data:
                                    self.altavoz.poner(p.inline_data.data)
                        if sc.input_transcription and sc.input_transcription.text:
                            self.turno_pendiente = True  # te ha oido: en cuanto calles, cara "pensando"
                            self.ultimo_dicho += " " + sc.input_transcription.text
                            log(f"Tu: {sc.input_transcription.text.strip()}")
                        if sc.output_transcription and sc.output_transcription.text:
                            estado["texto_turno"] += sc.output_transcription.text
                            if ayla_turno():
                                estado["frase"] += sc.output_transcription.text
                                soltar_frases()
                        if sc.turn_complete:
                            self.turno_pendiente = False  # respuesta completa (si Ayla aun la prepara, sigue "pensando")
                            self.ultimo_dicho = ""
                            if estado["ayla"]:
                                soltar_frases(final=True)
                            if estado["texto_turno"].strip():
                                quien = "Ayla" if self.usar_ayla else "voz Gemini"
                                log(f"Nova ({quien}): {estado['texto_turno'].strip()}")
                            estado["texto_turno"] = ""
                            estado["ayla"] = None
                    if not hubo:
                        fin.set()
                        return

            async def atender_herramientas(tool_call):
                self.herramientas += 1  # cara "pensando" mientras consulta / manda la orden
                try:
                    await _atender_herramientas(tool_call)
                finally:
                    self.herramientas = max(0, self.herramientas - 1)

            async def _atender_herramientas(tool_call):
                respuestas = []
                for fc in tool_call.function_calls or []:
                    args = dict(fc.args or {})
                    log(f"Herramienta: {fc.name} {json.dumps(args, ensure_ascii=False)[:200]}")
                    if fc.name == "enviar_a_nova":
                        res = await asyncio.to_thread(self.enviar_orden, args.get("orden", ""), args.get("resumen", ""))
                    elif fc.name == "estado_nova":
                        res = self.estado()
                    elif fc.name == "responder_permiso":
                        res = await asyncio.to_thread(self.contestar_permiso, str(args.get("decision", "")).lower())
                    elif fc.name == "hora_actual":
                        t = time.localtime()
                        res = {"hora": time.strftime("%H:%M", t), "dia": DIAS[t.tm_wday],
                               "fecha": time.strftime("%d/%m/%Y", t),
                               "nota": "Es la hora local del usuario. Dila tal cual (en formato de 12 h si suena mas natural)."}
                    elif fc.name == "terminar_conversacion":
                        estado["cerrar_tras_hablar"] = True
                        res = {"resultado": "ok, la conversacion se cerrara al terminar de hablar"}
                    else:
                        res = {"error": f"herramienta desconocida {fc.name}"}
                    respuestas.append(types.FunctionResponse(id=fc.id, name=fc.name, response=res))
                await s.send_tool_response(function_responses=respuestas)

            if texto_inicial:
                await s.send_realtime_input(text=texto_inicial)
            tareas = [asyncio.create_task(c()) for c in (recibir, mandar_avisos, guardian)]
            if not self.args.texto:  # con un aviso inicial tambien escucha tu respuesta (solo --texto no usa micro)
                tareas.append(asyncio.create_task(mandar_mic()))
            esperar_fin = asyncio.create_task(fin.wait())
            hechas, _ = await asyncio.wait(tareas + [esperar_fin], return_when=asyncio.FIRST_COMPLETED)
            fin.set()
            for t in tareas + [esperar_fin]:
                t.cancel()
            for t in hechas:
                if t is not esperar_fin and not t.cancelled() and t.exception():
                    log(f"Fallo en la conversacion: {type(t.exception()).__name__}: {t.exception()}")
        self.sesion_activa = False
        self.turno_pendiente, self.herramientas = False, 0
        # avisos que llegaron justo al cerrar: los dice Ayla
        while self.avisos and not self.avisos.empty():
            aviso = self.avisos.get_nowait()
            threading.Thread(target=self.ayla.decir_ya, args=(aviso,), daemon=True).start()
        log("Conversacion cerrada. Di 'Nova' para volver.")

# ==================================================================================================================
# PRUEBA DE PUNTA A PUNTA (v3.2): python nova_voz_live.py --prueba
# Dice paso a paso que funciona y que no: clave, otras voces, micro, palabra "Nova", servidor de Ayla, voz, Gemini.
# ==================================================================================================================
def prueba(args) -> int:
    fallos = []

    def paso(n, ok, texto, ayuda=""):
        print(f"[{'OK' if ok is True else 'AVISO' if ok is None else 'FALLA'}] {n}. {texto}", flush=True)
        if ok is False:
            fallos.append(n)
            if ayuda:
                print(f"         -> {ayuda}", flush=True)

    print("\n=== NOVA VOZ LIVE: PRUEBA DE PUNTA A PUNTA ===\n", flush=True)
    clave = clave_api()
    paso(1, bool(clave), "clave de Gemini" + (" encontrada" if clave else " NO encontrada"),
         "python nova_clave_gemini.py (en antigravity\\scripts)")
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "$p = @(Get-CimInstance Win32_Process | ? { $_.Name -match '^pythonw?(\\.exe)?$' }); "
                            "$ids = $p.ProcessId; $p | ? { $ids -notcontains $_.ParentProcessId } | % { $_.CommandLine }"],
                           capture_output=True, text=True, timeout=20, creationflags=0x08000000)
        lineas = r.stdout.splitlines()  # sin los hijos del lanzador de Python (cada programa salia x2)
    except Exception:  # noqa: BLE001
        lineas = []
    clasica = [x for x in lineas if "nova_voz.py" in x and "--solo-aduana" not in x]
    live = [x for x in lineas if "nova_voz_live.py" in x and "--prueba" not in x]
    paso(2, not clasica, "voces en marcha: Nova Voz Live x%d, voz clasica escuchando 'Nova' x%d" % (len(live), len(clasica)),
         "la voz clasica tambien escucha 'Nova' y se pelean: cierra Antigravity, reinicia el guardian "
         "(start_session_guard.vbs) y vuelve a abrirlo")
    try:
        nombre_mic = sd.query_devices(kind="input")["name"]
    except Exception as e:  # noqa: BLE001
        nombre_mic = f"ninguno ({type(e).__name__})"
    print(f"\n   Microfono predeterminado de Windows: {nombre_mic}", flush=True)
    input("   Pulsa Enter y di 'Nova' con voz normal (graba 4 s)... ")
    audio = sd.rec(64000, samplerate=16000, channels=1, dtype="int16")
    sd.wait()
    nivel = int(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    paso(3, nivel >= 150, f"micro: volumen {nivel} (menos de 150 = no te oye)",
         "Configuracion de Windows > Sonido > Entrada: elige el micro bueno y sube el volumen")
    try:
        import vosk
        vosk.SetLogLevel(-1)
        modelo = vosk.Model(MODELO_VOSK)
        rec = vosk.KaldiRecognizer(modelo, 16000, GRAMATICA_VOSK)
        rec.SetWords(True)
        rec.AcceptWaveform(audio.tobytes())
        res = json.loads(rec.FinalResult()).get("result", [])
        pal = [w for w in res if w.get("word") != "[unk]"]
        libre = vosk.KaldiRecognizer(modelo, 16000)
        libre.AcceptWaveform(audio.tobytes())
        texto_libre = json.loads(libre.FinalResult()).get("text", "").strip().lower()
        conf = max([w.get("conf", 0) for w in pal if w.get("word") == "nova"] or [0])
        oye = (len(pal) == 1 and pal[0]["word"] == "nova" and conf >= CONF_NOVA and len(res) <= 2
               and bool(RE_NOVA_LIBRE.match(texto_libre)))
        paso(4, oye, f"palabra 'Nova': oyo {[w['word'] for w in pal]} (confianza {conf:.2f}), libre: '{texto_libre}'",
             "di solo 'Nova', clara y sin nada mas, a un palmo del micro; si sigue, pasale esta linea a soporte")
    except Exception as e:  # noqa: BLE001
        paso(4, False, f"reconocedor de voz local (Vosk): {type(e).__name__}: {e}",
             "ejecuta el Doctor: falta el modelo de Vosk")
    if pack_voz_listo():
        ayla = VozAyla(activa=True)
        print("\n   Servidor de Ayla: " + ayla.estado_servidor() + " (si hay que cargarlo tarda hasta ~2 min)...", flush=True)
        lista = ayla.arrancar(esperar_s=180)
        paso(5, lista, "servidor de Ayla " + ("listo" if lista else "NO cargo en 3 min"),
             f"mira {LOG_SERVIDOR}")
        if lista:
            ok = ayla.decir_ya(f"Hola {nombre_usuario()}, soy Nova. Te oigo bien.".replace("Hola ,", "Hola,"))
            paso(6, ok, "Ayla ha hablado (deberias haberla oido)")
    else:
        paso(5, None, "sin pack de voz: hablara la voz de Gemini")
    if clave:
        async def _gemini():
            from google import genai
            cli = genai.Client(api_key=clave, http_options={"api_version": "v1beta"})
            cfg = {"response_modalities": ["AUDIO"], "output_audio_transcription": {},
                   "system_instruction": "Responde con una frase corta en espanol."}
            texto = ""
            async with cli.aio.live.connect(model=MODELO, config=cfg) as s:
                await s.send_realtime_input(text="Di solo: hola, te escucho.")
                async for r in s.receive():
                    sc = r.server_content
                    if sc and sc.output_transcription and sc.output_transcription.text:
                        texto += sc.output_transcription.text
                    if sc and sc.turn_complete:
                        break
            return texto.strip()
        try:
            t0 = time.time()
            texto = asyncio.run(asyncio.wait_for(_gemini(), 30))
            paso(7, bool(texto), f"Gemini Live contesta en {time.time() - t0:.1f} s: '{texto}'")
        except Exception as e:  # noqa: BLE001
            paso(7, False, f"Gemini Live: {type(e).__name__}: {str(e)[:200]}", "revisa la clave de Gemini")
    print("\n=== " + ("TODO OK: di 'Nova' y habla" if not fallos else f"FALLAN los pasos {fallos}") + " ===\n", flush=True)
    return 0 if not fallos else 1


def main():
    p = argparse.ArgumentParser(description="Nova Voz Live (fase 1)")
    p.add_argument("--voz", choices=["auto", "ayla", "gemini"], default="auto",
                   help="auto = Ayla si esta el pack de voz, si no la voz de Gemini")
    p.add_argument("--auriculares", action="store_true", help="micro siempre abierto: puedes interrumpirla")
    p.add_argument("--texto", help="prueba sin micro: manda este texto y escucha la respuesta")
    p.add_argument("--sin-monito", action="store_true", help="no abrir el monito flotante")
    p.add_argument("--prueba", action="store_true", help="prueba de punta a punta (no para la voz que ya funciona)")
    args = p.parse_args()
    if args.prueba:
        sys.exit(prueba(args))

    viejo = leer_pid(PID_VIEJO)
    if not args.texto and viejo and pid_vivo(viejo):
        raise SystemExit(f"nova_voz.py esta en marcha (PID {viejo}). Cierralo antes: los dos no pueden usar el micro.")
    otro = leer_pid(PID_LIVE)
    if otro and otro != os.getpid() and pid_vivo(otro):
        subprocess.run(["taskkill", "/PID", str(otro), "/T", "/F"], capture_output=True, creationflags=0x08000000)
    with open(PID_LIVE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    if not args.texto:
        try:  # si la arrancan (a mano o el guardian), deja de estar "apagada"
            os.remove(VOZ_APAGADA)
        except OSError:
            pass

    try:
        asyncio.run(NovaLive(args).principal())
    except KeyboardInterrupt:
        log("Hasta luego.")
    finally:  # el monito se va con Nova Voz Live
        try:
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'{"cmd": "salir"}', ("127.0.0.1", PUERTO_WIDGET))
        except OSError:
            pass


if __name__ == "__main__":
    main()
