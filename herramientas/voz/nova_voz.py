"""
NOVA VOZ v9 - manos libres (modo Alexa, bandeja y mascota 2D dentro de Antigravity) por voz para Antigravity (sin widget; base: Voice Companion v5.0)
===========================================================================================
- Modo Alexa: "Nova, <orden>" -> pitido y la orden va al chat. Solo "Nova" -> pitido y te escucha. Sin frases habladas.
- Responde HABLANDO: la orden va con la marca [voz] y Nova termina con una linea "VOZ: ..." (respuesta corta o resumen
  de lo hecho) que se lee en alto. Regla en GEMINI.md.
- "Nova, modo voz" (o "hablemos") -> pulsa Start Voice mode de Antigravity (Gemini Live: conversacion por voz oficial).
- Voz neural (Edge TTS, es-PE-CamilaNeural) con frases en cache (<15 ms). Pausas de 1.8 s al dictar.
- La orden se escribe en el chat de Antigravity por CDP (Chrome DevTools Protocol) y se guarda en
  antigravity/nova_voice_inbox.txt. Si no encuentra Antigravity, AVISA y no pega nada en otra ventana.
- Cambios v6 (08/11, Claude): fuera el widget flotante (tkinter) que daba errores; fuera el pegado a ciegas
  con Ctrl+V + Enter en la ventana activa; fuera la ruta vieja de Drive. Preparado para usar la voz clonada
  de Nova (scratch/voice_clone, pendiente de inspeccion) cuando este lista: cambiar VOICE_NAME o speak_neural.

    pythonw nova_voz.py   (sin ventana: estado en el icono de la bandeja; clic derecho = pausar / registro / salir)
Requisitos: pip install edge-tts SpeechRecognition sounddevice numpy websocket-client
"""

import sys
import os
import time
import re
import queue
import json
import urllib.request
import subprocess
import winsound
import ctypes
import asyncio
import base64
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import websocket
import edge_tts

# ==============================================================================
# 0. AUTO-GUARDIÁN DE INSTANCIA ÚNICA (MATA DUPLICADOS ANTERIORES)
# ==============================================================================
def kill_other_instances():
    my_pid = os.getpid()
    ps_cmd = f"""
    $myPid = {my_pid}
    $myParent = (Get-CimInstance Win32_Process -Filter "ProcessId = $myPid").ParentProcessId
    Get-CimInstance Win32_Process | Where-Object {{
        ($_.Name -like 'python*') -and
        ($_.ProcessId -ne $myPid) -and
        ($_.ProcessId -ne $myParent) -and
        ($_.CommandLine -match 'nova_voice_companion|nova_native_widget|nova_voz')
    }} | ForEach-Object {{
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }}
    """
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            timeout=4, creationflags=0x08000000
        )
    except Exception:
        pass

# ==============================================================================
# 1. CONFIGURACIÓN Y CACHÉ DE VOZ + ASSETS DEL ROBOT
# ==============================================================================
VOICE_NAME = "es-PE-CamilaNeural"
CACHE_DIR = os.path.expanduser(r"~\.gemini\antigravity\voice_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


CACHED_PHRASES = {
    "wake": {
        "file": os.path.join(CACHE_DIR, "wake_jefe.mp3"),
        "text": "¿Qué necesitas, Jefe?"
    },
    "confirm": {
        "file": os.path.join(CACHE_DIR, "confirm.mp3"),
        "text": "Oído cocina, ejecutando."
    },
    "retry": {
        "file": os.path.join(CACHE_DIR, "retry.mp3"),
        "text": "No te escuché bien, Jefe. Repítemelo con calma."
    }
}

winmm = ctypes.windll.winmm

def play_mp3_mci(file_path, wait=True):
    """Reproduce un archivo MP3 mediante la API nativa MCI de Windows sin lag."""
    if not os.path.exists(file_path):
        return False
    try:
        winmm.mciSendStringW('close nova_audio', None, 0, None)
        winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias nova_audio', None, 0, None)
        cmd = 'play nova_audio wait' if wait else 'play nova_audio from 0'
        winmm.mciSendStringW(cmd, None, 0, None)
        if wait:
            winmm.mciSendStringW('close nova_audio', None, 0, None)
        return True
    except Exception:
        return False

async def async_speak_neural(text, output_path):
    comm = edge_tts.Communicate(text, VOICE_NAME, rate="+4%")
    await comm.save(output_path)

def speak_neural(text, cache_key=None, wait=True):
    """Habla usando el caché instantáneo (<15ms) o sintetiza al vuelo."""
    if cache_key and cache_key in CACHED_PHRASES:
        fpath = CACHED_PHRASES[cache_key]["file"]
        if os.path.exists(fpath):
            play_mp3_mci(fpath, wait=wait)
            return

    dyn_path = os.path.join(CACHE_DIR, "dynamic_tts.mp3")
    try:
        asyncio.run(async_speak_neural(text, dyn_path))
        play_mp3_mci(dyn_path, wait=wait)
    except Exception:
        safe_text = re.sub(r'[\'\"`$]', '', text)
        cmd = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{safe_text}')"
        subprocess.run(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd], timeout=10, creationflags=0x08000000)

def ensure_cache():
    """Garantiza que los audios pre-cacheados existan en disco."""
    for key, data in CACHED_PHRASES.items():
        if not os.path.exists(data["file"]):
            try:
                asyncio.run(async_speak_neural(data["text"], data["file"]))
            except Exception:
                pass

# ==============================================================================
# 2. PUENTE SOUNDDEVICE -> SPEECH_RECOGNITION
# ==============================================================================
class QueueStream:
    def __init__(self, q):
        self.q = q
    def read(self, size):
        # 09/11 tarde (Claude): antes q.get() sin limite. Si el micro deja de mandar audio (se reabre Antigravity, cambia
        # el dispositivo...) la voz se quedaba colgada para siempre sin error ("le digo Nova y no hace caso").
        # Ahora: 3 s sin audio -> error -> el bucle lo apunta y vuelve a abrir el micro.
        try:
            return self.q.get(timeout=3)
        except queue.Empty:
            raise OSError("el micro no manda audio desde hace 3 s (se reabre)")

class SoundDeviceMicrophone(sr.AudioSource):
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2
        self.q = queue.Queue()
        self.sd_stream = None
        self.stream = QueueStream(self.q)

    def __enter__(self):
        def callback(indata, frames, time_info, status):
            self.q.put(indata.copy().tobytes())

        while not self.q.empty():  # audio viejo de la escucha anterior fuera
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

        self.sd_stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype='int16',
            blocksize=self.CHUNK,
            callback=callback
        )
        self.sd_stream.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sd_stream:
            self.sd_stream.stop()
            self.sd_stream.close()

# ==============================================================================
# 3. MOTOR FONÉTICO ESPAÑOL (WAKE-WORD "NOVA")
# ==============================================================================
def normalize_spanish_phonetics(text):
    if not text:
        return ""
    t = text.lower().strip()
    accents = {
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a',
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u'
    }
    for char, rep in accents.items():
        t = t.replace(char, rep)
    t = t.replace('v', 'b').replace('h', '').replace('qu', 'k').replace('z', 's')
    t = re.sub(r'c(?=[ei])', 's', t).replace('c', 'k').replace('ll', 'y')
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def damerau_levenshtein(s1, s2):
    d = {}
    len1, len2 = len(s1), len(s2)
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1
    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(d[(i - 1, j)] + 1, d[(i, j - 1)] + 1, d[(i - 1, j - 1)] + cost)
            if i and j and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost)
    return d[(len1 - 1, len2 - 1)]

DIRECT_MATCH_WORDS = {"noba", "nova", "noa", "noda", "nora", "novah", "nobah"}
NEGATIVE_WORDS = {"no", "ba", "bale", "bas", "bamos", "nobela", "nobiembre", "nota", "nada", "loba", "boba", "boda", "roba", "soba"}

def detect_wake_word(text):
    if not text:
        return False, ""
    original_text = text.strip()
    norm = normalize_spanish_phonetics(original_text)
    words = norm.split()
    orig_words = original_text.split()
    if not words:
        return False, ""

    salutations = {"ola", "oye", "ey", "eh", "ok", "bueno", "porfa"}

    for i in range(len(words) - 1):
        if words[i] == "no" and words[i+1] == "ba":
            cmd = " ".join(orig_words[i+2:]) if i + 2 < len(orig_words) else ""
            return True, cmd.strip()

    for i, w in enumerate(words):
        if w in DIRECT_MATCH_WORDS:
            cmd = " ".join(orig_words[i+1:]) if i + 1 < len(orig_words) else ""
            return True, cmd.strip()

    for i, w in enumerate(words):
        if w in NEGATIVE_WORDS:
            continue
        if damerau_levenshtein(w, "noba") <= 1:
            has_salutation = (i > 0 and words[i-1] in salutations)
            if has_salutation or len(words) == 1 or i == 0:
                cmd = " ".join(orig_words[i+1:]) if i + 1 < len(orig_words) else ""
                return True, cmd.strip()

    return False, ""

def play_chime_wake():
    try:
        winsound.Beep(1000, 70)
        winsound.Beep(1400, 100)
    except Exception:
        pass

def play_chime_confirm():
    try:
        winsound.Beep(1400, 70)
        winsound.Beep(1800, 100)
    except Exception:
        pass

def play_chime_error():
    estado_bandeja("error", "algo fallo: mira el registro")
    try:
        winsound.Beep(600, 140)
    except Exception:
        pass

# ==============================================================================
# 4. INYECCIÓN DIRECTA CDP EN ANTIGRAVITY (CHROME DEVTOOLS PROTOCOL)
# ==============================================================================
def _puertos_antigravity():
    """Electron apunta su puerto de depuracion en DevToolsActivePort (lectura instantanea). Plan B: preguntar a Windows."""
    puertos = []
    for d in ("Antigravity", "antigravity"):
        f = os.path.join(os.environ.get("APPDATA", ""), d, "DevToolsActivePort")
        try:
            with open(f, encoding="utf-8") as fh:
                primera = fh.readline().strip()
                if primera.isdigit():
                    puertos.append(int(primera))
        except OSError:
            pass
    if puertos:
        return list(dict.fromkeys(puertos))
    ps_cmd = ("Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -in "
              "(Get-Process Antigravity -ErrorAction SilentlyContinue).Id } | Select-Object -ExpandProperty LocalPort")
    try:
        res = subprocess.run(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                             capture_output=True, text=True, timeout=12, creationflags=0x08000000)
        return [int(x) for x in res.stdout.split() if x.strip().isdigit()]
    except Exception:
        return []


def get_antigravity_ws_url():
    """WebSocket de la ventana principal de Antigravity (titulo 'Antigravity', no las paginas data: auxiliares)."""
    for port in _puertos_antigravity():
        try:
            targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1.5).read())
        except Exception:
            continue
        pages = [t for t in targets if t.get("type") == "page" and not str(t.get("url", "")).startswith("data:")]
        pages.sort(key=lambda t: t.get("title") != "Antigravity")
        if pages:
            return pages[0]["webSocketDebuggerUrl"]
    return None


def contar_voz(js) -> int:
    return js("(document.body.innerText.match(/(^|\\n)\\s*VOZ:/g) || []).length") or 0


def esperar_respuesta_y_hablar(antes: int, limite_min: int = 20):
    """Tras enviar, espera la linea 'VOZ: ...' que Nova pone al final de su respuesta y la lee en voz alta.
    09/11 (Claude): antes miraba cada 2 s y pedia dos lecturas iguales (2-4 s de retraso extra). Ahora mira cada
    0,4 s con una sola conexion abierta y habla en cuanto la linea lleva 0,8 s sin cambiar."""
    expr = ("(() => { const m = document.body.innerText.match(/(^|\\n)\\s*VOZ:[^\\n]*/g) || [];"
            " return JSON.stringify({n: m.length, ultima: m.length ? m[m.length - 1].replace(/^\\s*VOZ:\\s*/, '').trim() : ''}); })()")
    fin = time.time() + limite_min * 60
    ultimo, desde = "", 0.0
    ws, n = None, 0
    try:
        while time.time() < fin:
            time.sleep(0.4)
            if ws is None:
                ws_url = get_antigravity_ws_url()
                if not ws_url:
                    time.sleep(1.5)
                    continue
                try:
                    ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=5)
                except Exception:
                    ws = None
                    continue
            try:
                n += 1
                ws.send(json.dumps({"id": n, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
                while True:
                    resp = json.loads(ws.recv())
                    if resp.get("id") == n:
                        break
                r = json.loads(resp.get("result", {}).get("result", {}).get("value") or "{}")
            except Exception:
                try:
                    ws.close()
                except Exception:
                    pass
                ws = None
                continue
            if r.get("n", 0) > antes and r.get("ultima"):
                if r["ultima"] != ultimo:
                    ultimo, desde = r["ultima"], time.time()
                elif time.time() - desde >= 0.8:  # la linea ya no cambia: termino de escribirla
                    log_event(f"Respuesta de Nova: '{ultimo}'")
                    estado_bandeja("hablando", ultimo[:80])
                    speak_neural(re.sub(r"[`*_#>]", "", ultimo)[:400], wait=True)
                    estado_bandeja("pausa" if _BANDEJA["pausa"] else "espera", "di 'Nova'")
                    return True
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
    log_event("Nova no dio linea VOZ: a tiempo (sin respuesta hablada)")
    estado_bandeja("espera", "di 'Nova'")
    return False


def inject_and_send(prompt_text):
    """v7 (08/11): el editor nuevo de Antigravity no se entera de execCommand; se escribe como un teclado real
    (CDP Input.insertText) y se pulsa el boton 'Send message' (solo aparece cuando hay texto)."""
    try:
        with open(os.path.expanduser(r"~\.gemini\antigravity\nova_voice_inbox.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {prompt_text}\n")
    except Exception:
        pass
    ws_url = get_antigravity_ws_url()
    if not ws_url:
        log_event("No encuentro el chat de Antigravity (CDP). La orden queda en nova_voice_inbox.txt")
        play_chime_error()
        return False
    try:
        ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=5)
        n = [0]

        def cdp(metodo, params=None):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": metodo, "params": params or {}}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == n[0]:
                    return r

        def js(expr):
            return cdp("Runtime.evaluate", {"expression": expr, "returnByValue": True}).get("result", {}).get("result", {}).get("value")

        if not js("(() => { const el = document.querySelector('[contenteditable=\"true\"]'); if (!el) return false; el.focus(); return true; })()"):
            ws.close()
            log_event("No encuentro el cuadro de mensaje de Antigravity")
            play_chime_error()
            return False
        # 08/11: sin foco real (la ventana de la voz delante) Chromium ignora el teclado -> foco emulado
        cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
        antes_voz = contar_voz(js)
        js("document.querySelector('[contenteditable=\"true\"]').focus()")
        restos = len((js("document.querySelector('[contenteditable=\"true\"]').innerText") or "").strip())
        for _ in range(restos + 2 if restos else 0):  # vaciar solo si habia algo escrito
            cdp("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8})
            cdp("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8})
        cdp("Input.insertText", {"text": "[voz] " + prompt_text})  # Nova responde con una linea VOZ: para leerla en alto
        enviado = False
        for _ in range(10):  # el boton aparece cuando el editor registra el texto
            time.sleep(0.2)
            enviado = js("(() => { const b = document.querySelector('button[aria-label=\"Send message\"]'); if (b && !b.disabled) { b.click(); return true; } return false; })()")
            if enviado:
                break
        if not enviado:  # plan B: Enter como teclado real
            cdp("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
            cdp("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
        ws.close()
        log_event(f"Orden enviada a Antigravity ({'boton' if enviado else 'Enter'}): '{prompt_text}'")
        estado_bandeja("pensando", f"Nova trabajando: {prompt_text[:60]}")
        threading.Thread(target=esperar_respuesta_y_hablar, args=(antes_voz,), daemon=True).start()
        return True
    except Exception as e:
        log_event(f"Error enviando por CDP: {e}")
        play_chime_error()
        return False


PIDE_MODO_VOZ = re.compile(r"(?i)\b(modo voz|modo de voz|hablemos|conversemos|conversaci[oó]n|voice mode)\b")


def abrir_modo_voz():
    """Pulsa 'Start Voice mode' de Antigravity (Gemini Live). Necesita el cuadro de mensaje vacio."""
    ws_url = get_antigravity_ws_url()
    if not ws_url:
        play_chime_error()
        return False
    try:
        ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=5)
        expr = ("(() => { const el = document.querySelector('[contenteditable=\"true\"]'); if (el && el.innerText.trim()) return 'OCUPADO';"
                " const b = document.querySelector('button[aria-label=\"Start Voice mode\"]'); if (!b) return 'SIN_BOTON'; b.click(); return 'OK'; })()")
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
        r = json.loads(ws.recv()).get("result", {}).get("result", {}).get("value")
        ws.close()
        log_event(f"Modo voz de Antigravity: {r}")
        if r != "OK":
            play_chime_error()
        return r == "OK"
    except Exception as e:
        log_event(f"Error abriendo el modo voz: {e}")
        play_chime_error()
        return False


def modo_voz_activo() -> bool:
    """True mientras el modo voz de Antigravity esta abierto (el boton 'Start Voice mode' desaparece)."""
    ws_url = get_antigravity_ws_url()
    if not ws_url:
        return False
    try:
        ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=4)
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": "!document.querySelector('button[aria-label=\"Start Voice mode\"]')", "returnByValue": True}}))
        r = json.loads(ws.recv()).get("result", {}).get("result", {}).get("value")
        ws.close()
        return bool(r)
    except Exception:
        return False


def esperar_fin_modo_voz():
    """Pausa la escucha de 'Nova' mientras dure el modo voz (si no, se enviaria la orden dos veces)."""
    log_event("[pausa] modo voz de Antigravity abierto: no escucho hasta que lo cierres")
    time.sleep(5)
    fin = time.time() + 60 * 60
    while time.time() < fin and modo_voz_activo():
        time.sleep(2)
    play_chime_confirm()
    log_event("[espera] modo voz cerrado: vuelvo a escuchar 'Nova'")


# ------------------------------------------------------------------------------
# MUSICA EN LOCAL (09/11, Claude, a pedido de el autor): YouTube en Brave via el puente (YOUTUBE_CONTROL de la extension).
# 0 tokens: no pasa por Nova. Si la orden no es de musica, sigue el camino normal (chat de Antigravity).
# ------------------------------------------------------------------------------
_M = r"(canci[oó]n|m[uú]sica|tema|rola|video|v[ií]deo|youtube)"
_G = r"(?:\W+\w+){0,2}\W+"  # hasta 2 palabras entre el verbo y "cancion" ("pasa a la siguiente canción")
_SOLO = r"^\W*(?:la\W+)?{}\W*$"  # la orden ES solo eso ("pausa", "siguiente")
MUSICA = [  # ojo: "pon <cancion X>" NO esta aqui: buscar una cancion lo hace Nova
    ("next",    re.compile(rf"(?i)\b(siguiente|pasa(la)?|salta(la)?|cambia(la)?|otra)\b{_G}{_M}\b|\b{_M}\W+siguiente\b|"
                           + _SOLO.format(r"(siguiente|otra|cambia(la)?|p[aá]sala)"))),
    ("que",     re.compile(r"(?i)\b(qu[eé]|cu[aá]l)\b(?:\W+\w+){0,2}\W+(suena|est[aá] sonando|canci[oó]n es|tema es)\b")),
    ("pause",   re.compile(rf"(?i)\b(pausa|pausar|pon pausa a|para|det[eé]n|quita)\W+(la\W+|el\W+|esta\W+|este\W+)?{_M}\b|"
                           + _SOLO.format(r"(pausa|p[aá]usala|para(la)?)"))),
    ("play",    re.compile(rf"(?i)\b(contin[uú]a|reanuda|dale play a|quita la pausa a)\W+(la\W+|el\W+)?{_M}\b|"
                           + _SOLO.format(r"(play|dale play|contin[uú]a|reanuda|quita la pausa)"))),
    ("vol_up",  re.compile(r"(?i)\bsube\W+(el\W+)?volumen\b|^\W*m[aá]s (alto|volumen)\W*$")),
    ("vol_down",re.compile(r"(?i)\bbaja\W+(el\W+)?volumen\b|^\W*(m[aá]s bajo|menos volumen)\W*$")),
    ("vol_set", re.compile(r"(?i)\bvolumen\b(?:\W+(?!\d)\w+){0,3}?\W+(\d{1,3})\b")),
    ("mute",    re.compile(rf"(?i)^\W*(silencia(la)?|silencio|mutea(la)?|quita el silencio)\W*$|\b(silencia|mutea)\W+(la\W+|el\W+)?{_M}\b")),
]


def _volumen_windows(accion, objetivo=None):
    """Teclas de volumen de Windows (cada pulsacion = 2 %). Sale el indicador de volumen de Windows en pantalla."""
    VK_MUTE, VK_DOWN, VK_UP = 0xAD, 0xAE, 0xAF

    def pulsar(vk, veces=1):
        for _ in range(veces):
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
            time.sleep(0.01)
    if accion == "mute":
        pulsar(VK_MUTE)
    elif accion == "vol_up":
        pulsar(VK_UP, 8)      # +16 %
    elif accion == "vol_down":
        pulsar(VK_DOWN, 8)    # -16 %
    elif accion == "vol_set":
        pulsar(VK_DOWN, 50)   # a 0 y luego subir hasta el objetivo
        pulsar(VK_UP, round(min(max(objetivo, 0), 100) / 2))


def _youtube(command, **extra):
    req = urllib.request.Request("http://127.0.0.1:5005/execute", method="POST",
                                 data=json.dumps({"action": "YOUTUBE_CONTROL", "args": {"command": command, **extra}}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


_MUSICA = {"volumen_tocado": False}


def bajar_musica():
    """Estilo Alexa (09/11, el autor: "que baje la musica, no pausar"): al oir "Nova" baja YouTube al 25 % para oir
    la orden. Devuelve el volumen anterior (o None si no suena nada)."""
    _MUSICA["volumen_tocado"] = False
    try:
        d = _youtube("status").get("data") or {}
        if d and not d.get("paused") and not d.get("muted") and d.get("volume", 0) > 8:
            _youtube("volume", volume=max(d["volume"] * 0.25, 5) / 100)
            return d["volume"]
    except Exception:
        pass
    return None


def subir_musica(volumen_antes):
    """Vuelve al volumen de antes, salvo que la orden fuera justo cambiar el volumen de la musica."""
    if volumen_antes is None or _MUSICA["volumen_tocado"]:
        return
    try:
        _youtube("volume", volume=volumen_antes / 100)
    except Exception:
        pass


def musica_local(orden: str) -> bool:
    """True si era una orden de musica (hecha aqui, sin Nova)."""
    accion = next((a for a, rx in MUSICA if rx.search(orden)), None)
    if not accion:
        return False
    # Volumen y silencio: SIN decir musica/youtube/video -> el de Windows (el PC); CON -> solo el de YouTube
    if accion in ("vol_up", "vol_down", "vol_set", "mute") and not re.search(rf"(?i)\b{_M}\b", orden):
        log_event(f"Volumen de Windows ({accion}): '{orden}'")
        objetivo = int(MUSICA[6][1].search(orden).group(1)) if accion == "vol_set" else None
        _volumen_windows(accion, objetivo)
        return True
    log_event(f"Musica local ({accion}): '{orden}'")
    if accion in ("vol_up", "vol_down", "vol_set", "mute"):
        _MUSICA["volumen_tocado"] = True  # que subir_musica no deshaga el volumen que acaba de pedir
    try:
        if accion in ("vol_up", "vol_down", "vol_set"):
            vol = (_youtube("status").get("data") or {}).get("volume", 50)
            if accion == "vol_set":
                vol = int(MUSICA[6][1].search(orden).group(1))
            else:
                vol += 15 if accion == "vol_up" else -15
            r = _youtube("volume", volume=min(max(vol, 0), 100) / 100)
        elif accion == "que":
            r = _youtube("status")
        else:
            r = _youtube(accion)
    except Exception as e:
        log_event(f"Musica local: puente de Brave sin respuesta ({e})")
        speak_neural("No llego a Brave. ¿Está abierto?")
        return True
    if not r.get("ok"):
        log_event(f"Musica local: {r.get('error')}")
        speak_neural("No encuentro YouTube sonando en Brave.")
        return True
    d = r.get("data") or {}
    if accion == "next":
        time.sleep(1.5)  # que cargue la nueva
        try:
            d = _youtube("status").get("data") or d
        except Exception:
            pass
        speak_neural(f"Ahora suena {d.get('title', 'la siguiente')}")
    elif accion == "que":
        speak_neural(f"Suena {d.get('title', 'algo')}" + (f", de {d['channel']}" if d.get("channel") else ""))
    else:
        play_chime_confirm()
    return True


def ejecutar(orden):
    """'Nova, modo voz' -> modo voz oficial; musica -> YouTube en local; cualquier otra orden -> chat de Antigravity."""
    if musica_local(orden):
        return True
    if PIDE_MODO_VOZ.search(orden):
        if abrir_modo_voz():
            esperar_fin_modo_voz()
            return True
        return False
    return inject_and_send(orden)


# ==============================================================================
# 4b. ICONO EN LA BANDEJA DE WINDOWS (estado sin ventanas: el widget flotante daba errores)
# ==============================================================================
COLORES = {"espera": (148, 163, 184), "escuchando": (34, 197, 94), "enviando": (245, 158, 11),
           "pensando": (245, 158, 11), "hablando": (59, 130, 246), "error": (239, 68, 68), "pausa": (71, 85, 105)}
_BANDEJA = {"icono": None, "pausa": False}


def _imagen(color):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=color + (255,))
    d.text((24, 18), "N", fill=(255, 255, 255, 255))
    try:
        from PIL import ImageFont
        d.rectangle((0, 0, 0, 0))
        f = ImageFont.truetype("segoeuib.ttf", 34)
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, 60, 60), fill=color + (255,))
        d.text((32, 31), "N", fill=(255, 255, 255, 255), font=f, anchor="mm")
    except Exception:
        pass
    return img


def estado_bandeja(modo, texto=""):
    mascota(modo)
    ico = _BANDEJA["icono"]
    if ico is None:
        return
    try:
        ico.icon = _imagen(COLORES.get(modo, COLORES["espera"]))
        ico.title = f"Nova Voz · {texto or modo}"[:120]
    except Exception:
        pass


def iniciar_bandeja():
    """Icono con menu: Pausar/Reanudar, Ver registro, Salir. Si pystray no esta, sigue sin icono."""
    try:
        import pystray
    except ImportError:
        log_event("pystray no instalado: sin icono de bandeja (pip install pystray)")
        return

    def pausar(icon, item):
        _BANDEJA["pausa"] = not _BANDEJA["pausa"]
        estado_bandeja("pausa" if _BANDEJA["pausa"] else "espera", "en pausa" if _BANDEJA["pausa"] else "di 'Nova'")
        log_event("Pausa ACTIVADA desde la bandeja" if _BANDEJA["pausa"] else "Pausa QUITADA desde la bandeja")

    def ver_registro(icon, item):
        subprocess.Popen(["notepad.exe", os.path.expanduser(r"~\.gemini\antigravity\memory\registros\nova_voice.log")])

    def salir(icon, item):
        log_event("Nova Voz cerrada desde la bandeja")
        try:  # session_guard.ps1 no la relanza hasta que se cierre y vuelva a abrir Antigravity
            open(VOZ_APAGADA, "w").close()
        except Exception:
            pass
        _js_seguro("window.__novaMascota && window.__novaMascota.quitar()")
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(pystray.MenuItem(lambda i: "Reanudar escucha" if _BANDEJA["pausa"] else "Pausar escucha", pausar),
                        pystray.MenuItem("Ver registro", ver_registro), pystray.MenuItem("Salir", salir))
    icono = pystray.Icon("nova_voz", _imagen(COLORES["espera"]), "Nova Voz · arrancando", menu)
    _BANDEJA["icono"] = icono
    threading.Thread(target=icono.run, daemon=True).start()


# ==============================================================================
# 4c. MASCOTA 2D DENTRO DE ANTIGRAVITY (mascota.js, inyectada por CDP: vive y muere con la ventana)
# ==============================================================================
MASCOTA_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mascota.js")
_MASCOTA = {"estado": "espera"}
VOZ_APAGADA = os.path.join(CACHE_DIR, "voz_apagada.flag")  # la crea "Salir"; session_guard.ps1 la respeta y la borra al cerrar Antigravity


def _js_seguro(expr):
    try:
        return _js_antigravity(expr)
    except Exception:
        return None


def _js_antigravity(expr, timeout=4):
    url = get_antigravity_ws_url()
    if not url:
        return None
    ws = websocket.create_connection(url, suppress_origin=True, timeout=timeout)
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
        return json.loads(ws.recv()).get("result", {}).get("result", {}).get("value")
    finally:
        ws.close()


def mascota(estado):
    """Cambia la cara de la mascota (si no esta, la crea). Nunca bloquea ni rompe la voz."""
    _MASCOTA["estado"] = estado

    def _hacer():
        try:
            if not _js_antigravity("!!window.__novaMascota"):
                with open(MASCOTA_JS, encoding="utf-8") as f:
                    _js_antigravity(f.read(), timeout=6)
            _js_antigravity(f"window.__novaMascota && window.__novaMascota.set({json.dumps(estado)})")
        except Exception:
            pass
    threading.Thread(target=_hacer, daemon=True).start()


def vigilar_mascota():
    """Si Antigravity se recarga o se abre de nuevo, la mascota vuelve a aparecer con el estado actual."""
    while True:
        time.sleep(4)
        try:
            if get_antigravity_ws_url() and not _js_antigravity("!!window.__novaMascota"):
                mascota(_MASCOTA["estado"])
        except Exception:
            pass


# ==============================================================================
# 4d. ADUANA DE ADJUNTOS (aduana.js por CDP, 09/11 Claude): lo que el autor pega/arrastra/adjunta en Antigravity no sube
#     a la nube: se guarda en temporal\, el puente lo lee EN LOCAL y en el chat queda "[adjunto local: <archivo>]".
#     El hook de turno (nova_core\nova_hook_turno.py) le pasa a Nova el texto ya leido. Shift = pasar como siempre.
# ==============================================================================
ADUANA_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aduana.js")
DIR_TEMPORAL = os.path.expanduser(r"~\.gemini\antigravity\temporal")
PUENTE_PY = os.path.expanduser(r"~\.gemini\antigravity\scripts\nova_puente_capturas.py")
_PUENTE = {"mod": None}


def _puente():
    """El modulo del puente de adjuntos (mismas funciones de lectura local que usa el daemon)."""
    if _PUENTE["mod"] is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("nova_puente_capturas", PUENTE_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PUENTE["mod"] = mod
    return _PUENTE["mod"]


def _nombre_seguro(nombre):
    base, ext = os.path.splitext(os.path.basename(nombre or "adjunto"))
    base = re.sub(r"[^\w.-]+", "_", base).strip("._-")[:60] or "adjunto"  # \w deja tildes y ñ (COTIZACIÓN)
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext)[:8].lower()
    return base + ext


def escribir_en_chat(texto):
    """Escribe texto en el cuadro de mensaje de Antigravity (como un teclado, sin enviar)."""
    url = get_antigravity_ws_url()
    if not url:
        return False
    ws = websocket.create_connection(url, suppress_origin=True, timeout=5)
    try:
        n = [0]

        def cdp(metodo, params=None):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": metodo, "params": params or {}}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == n[0]:
                    return r
        cdp("Runtime.evaluate", {"expression": "(() => { const el = document.querySelector('[contenteditable=\"true\"]'); if (el) el.focus(); })()"})
        cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
        cdp("Input.insertText", {"text": texto})
        return True
    finally:
        ws.close()


def _procesar_adjunto(ruta):
    from pathlib import Path
    t0 = time.time()
    try:
        ok = _puente().procesar(Path(ruta))
    except Exception as e:
        log_event(f"Aduana: error leyendo {os.path.basename(ruta)} en local: {e}")
        ok = False
    if not ok:  # el daemon del puente lo reintenta cada 2 min (p. ej. si Ollama aun no estaba listo)
        try:
            p = _puente()
            p._guardar_pendientes(p._leer_pendientes() + [str(ruta)])
        except Exception:
            pass
    log_event(f"Aduana: {os.path.basename(ruta)} {'leido en local' if ok else 'PENDIENTE'} en {time.time() - t0:.1f} s")
    estado_bandeja("pausa" if _BANDEJA["pausa"] else "espera", "di 'Nova'")


def recibir_adjunto(payload):
    try:
        d = json.loads(payload)
        datos = base64.b64decode(d.get("b64") or "")
        if not datos:
            log_event(f"Aduana: '{d.get('nombre')}' llego vacio")
            return
        carpeta = os.path.join(DIR_TEMPORAL, time.strftime("%Y-%m"))
        os.makedirs(carpeta, exist_ok=True)
        base = f"{time.strftime('%Y%m%d_%H%M%S')}_{_nombre_seguro(d.get('nombre'))}"
        nombre, i = base, 2
        while os.path.exists(os.path.join(carpeta, nombre)):
            raiz, ext = os.path.splitext(base)
            nombre, i = f"{raiz}_{i}{ext}", i + 1
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "wb") as f:
            f.write(datos)
        log_event(f"Aduana ({d.get('via')}): '{d.get('nombre')}' -> {nombre} ({len(datos) // 1024} KB), sin subir a la nube")
        estado_bandeja("mirando", "leyendo adjunto en local")
        escribir_en_chat(f"[adjunto local: {nombre}] ")
        _procesar_adjunto(ruta)
    except Exception as e:
        log_event(f"Aduana: error recibiendo adjunto: {e}")


def vigilar_aduana():
    """Conexion CDP fija con Antigravity: inyecta aduana.js, le da latido cada 3 s y recibe los adjuntos."""
    avisado = False
    while True:
        ws = None
        try:
            url = get_antigravity_ws_url()
            if not url:
                time.sleep(3)
                continue
            with open(ADUANA_JS, encoding="utf-8") as f:
                js = f.read()
            ws = websocket.create_connection(url, suppress_origin=True, timeout=5)
            ws.settimeout(2)
            n = [0]

            def send(metodo, params=None):
                n[0] += 1
                ws.send(json.dumps({"id": n[0], "method": metodo, "params": params or {}}))

            send("Runtime.addBinding", {"name": "novaAduana"})
            send("Runtime.enable")  # avisa si la ventana se recarga (executionContextCreated) para reinyectar
            send("Runtime.evaluate", {"expression": js})
            if not avisado:
                log_event("Aduana de adjuntos activa (Shift al pegar = pasar como siempre)")
                avisado = True
            latido = 0.0
            while True:
                if time.time() - latido > 3:
                    send("Runtime.evaluate", {"expression": "window.__novaAduanaLatido = Date.now()"})
                    latido = time.time()
                try:
                    msg = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    continue
                metodo = msg.get("method")
                if metodo == "Runtime.bindingCalled" and msg.get("params", {}).get("name") == "novaAduana":
                    threading.Thread(target=recibir_adjunto, args=(msg["params"].get("payload", ""),), daemon=True).start()
                elif metodo == "Runtime.executionContextCreated":
                    send("Runtime.evaluate", {"expression": js})
                    latido = 0.0
        except Exception:
            time.sleep(3)  # Antigravity cerrado o recargando: se reconecta solo
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass


def log_event(text):
    msg = f"[{time.strftime('%H:%M:%S')}] {text}"
    print(msg, flush=True)
    try:
        log_path = os.path.expanduser(r"~\.gemini\antigravity\memory\registros\nova_voice.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


# ==============================================================================
# 5. MOTOR DE VOZ (sin ventana)
# ==============================================================================
# 09/11 noche (Claude, a pedido de el autor): "Nova" se detecta EN LOCAL con Vosk (como Alexa: nada sale a Google hasta
# oir la palabra). Gramatica cerrada con SENUELOS para que "novela", "nueva", "novia", "nueve"... no la activen
# (probado 9/9). Si Vosk o su modelo faltan o fallan, la voz vuelve sola al modo de antes (Google).
MODELO_VOSK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelos", "vosk-model-small-es-0.42")
# 09/11 22:40: "no va ahi" la activaba (por el resultado PARCIAL). Ahora: solo el resultado FINAL y "nova" SUELTA
# (como mucho tras un saludo: "Oye Nova"); mas senuelos (no, va, ahi...). Pruebas 10/11: solo "no va" suelto con
# pausas suena igual que "Nova" (le pasaria hasta a Alexa).
GRAMATICA_VOSK = json.dumps(["nova", "novela", "nueva", "nuevo", "novia", "noventa", "nueve", "nota", "nos", "nada", "no", "va",
                             "vas", "voy", "ahi", "aqui", "alla", "noble", "bola", "boba", "lo", "la", "el", "en", "eso", "esa",
                             "tele", "[unk]"])


def es_nova_suelta(r: dict) -> bool:
    pal = [w for w in r.get("result", []) if w.get("word") != "[unk]"]
    return len(pal) == 1 and pal[0]["word"] == "nova" and pal[0].get("conf", 0) >= 0.7 and len(r.get("result", [])) <= 2
try:
    import vosk as _vosk
    VOSK_OK = os.path.isdir(MODELO_VOSK)
except ImportError:
    VOSK_OK = False


class NovaVoz:
    piso = 120.0  # suelo del umbral de energia (se recalcula al calibrar)

    def bucle_vosk(self, recognizer, mic):
        _vosk.SetLogLevel(-1)
        modelo = _vosk.Model(MODELO_VOSK)
        log_event("Palabra 'Nova' en LOCAL (Vosk): Google solo oye la orden, nunca la casa")
        fallos = 0
        while self.running:
            if _BANDEJA["pausa"]:
                time.sleep(0.5)
                continue
            rec = _vosk.KaldiRecognizer(modelo, 16000, GRAMATICA_VOSK)
            rec.SetWords(True)
            q = queue.Queue()
            oido = False
            try:
                with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype="int16", channels=1,
                                       callback=lambda d, f, t, s: q.put(bytes(d))):
                    while self.running and not _BANDEJA["pausa"]:
                        try:
                            datos = q.get(timeout=3)
                        except queue.Empty:
                            raise OSError("el micro no manda audio")
                        if rec.AcceptWaveform(datos):  # solo frases TERMINADAS (nada de adivinanzas a medias)
                            oido = es_nova_suelta(json.loads(rec.Result()))
                        if oido:
                            break
                fallos = 0
            except Exception as e:
                fallos += 1
                log_event(f"Vosk: {e} (intento {fallos})")
                if fallos >= 5:
                    raise
                time.sleep(1)
                continue
            if not oido:
                continue
            log_event("Palabra de activacion (local)")
            estado_bandeja("mirando", "te ha oido")
            volumen_antes = bajar_musica()
            play_chime_wake()
            time.sleep(0.15)
            try:
                self.escuchar_orden(recognizer, mic)
            finally:
                subir_musica(volumen_antes)
        return 0

    def __init__(self):
        self.running = True

    @staticmethod
    def calibrar(recognizer, mic, segundos):
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=segundos)
        recognizer.energy_threshold = min(max(recognizer.energy_threshold, 120), 6000)
        # 09/11 noche: el umbral dinamico bajaba hasta 0 en silencio y la voz mandaba silencio a Google sin parar
        # (1.887 veces en 3 h): ahora tiene SUELO = 80 % de lo calibrado (minimo 120)
        NovaVoz.piso = max(120.0, recognizer.energy_threshold * 0.8)
        log_event(f"Umbral calibrado: {recognizer.energy_threshold:.1f} (suelo {NovaVoz.piso:.0f})")

    def estado(self, modo, texto):
        log_event(f"[{modo}] {texto}")
        estado_bandeja(modo, texto)

    def escuchar_orden(self, recognizer, mic):
        self.estado("escuchando", "te escucho")
        recognizer.pause_threshold = 1.1  # 09/11: antes 1.8 s de silencio para dar la orden por terminada
        with mic as source:
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
                orden = recognizer.recognize_google(audio, language="es-ES")
                log_event(f"Orden reconocida: '{orden}'")
            except Exception:
                orden = ""
        if orden.strip():
            play_chime_confirm()
            ejecutar(orden)
            time.sleep(2.0)
        else:
            play_chime_error()
            time.sleep(1.0)
        self.estado("espera", "di 'Nova'")

    def bucle(self):
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.8
        recognizer.non_speaking_duration = 0.5
        mic = SoundDeviceMicrophone(sample_rate=16000, chunk_size=1024)
        log_event("Iniciando Nova Voz v9 (modo Alexa + bandeja + mascota)...")
        try:
            # 09/11 (Claude): antes se forzaba a 260 si salia >280. Con ruido real de ~2700 el umbral quedaba por
            # debajo del ruido, nunca habia "silencio" y "Nova" se perdia en trozos de 5 s. Ahora se respeta la
            # calibracion (con un tope alto) y se recalibra sola si lo oye todo como voz (ver bucle).
            self.calibrar(recognizer, mic, 1.0)
        except Exception as e:
            log_event(f"Error accediendo al micrófono: {e}")
            estado_bandeja("error", "sin microfono")
            time.sleep(30)
            return 1
        play_chime_confirm()
        self.estado("espera", "di 'Nova'")
        if VOSK_OK:
            try:
                return self.bucle_vosk(recognizer, mic)
            except Exception as e:
                log_event(f"Vosk no disponible ({type(e).__name__}: {e}): vuelvo a detectar 'Nova' con Google")
        sin_silencio = 0
        while self.running:
            if _BANDEJA["pausa"]:
                time.sleep(0.5)
                continue
            if recognizer.energy_threshold < NovaVoz.piso:
                recognizer.energy_threshold = NovaVoz.piso
            try:
                with mic as source:
                    recognizer.pause_threshold = 0.8
                    try:
                        audio = recognizer.listen(source, timeout=2.5, phrase_time_limit=5)
                    except sr.WaitTimeoutError:
                        sin_silencio = 0
                        continue
                # trozo de 5 s completo = no encontro pausa. Tres seguidos: el umbral esta bajo el ruido -> recalibrar
                if len(audio.frame_data) / (audio.sample_rate * audio.sample_width) >= 4.8:
                    sin_silencio += 1
                    if sin_silencio >= 3:
                        sin_silencio = 0
                        self.calibrar(recognizer, mic, 1.5)
                        continue
                else:
                    sin_silencio = 0
                segs = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
                try:
                    frase = recognizer.recognize_google(audio, language="es-ES")
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    log_event(f"Error reconocimiento: {e}")
                    time.sleep(0.5)
                    continue
                detectado, orden_directa = detect_wake_word(frase)
                if not detectado:
                    # PRIVACIDAD: nunca se guarda lo que se dice en la habitacion; solo que se oyo algo
                    log_event(f"Oido sin 'Nova' ({len(frase.split())} palabras, umbral {recognizer.energy_threshold:.0f})")
                    continue
                log_event(f"Palabra de activación: '{frase}'")
                if orden_directa:  # "Nova <orden>"
                    estado_bandeja("mirando", "te ha oido")
                    play_chime_confirm()  # el pitido ya es bloqueante: sin espera extra
                    ejecutar(orden_directa)
                    time.sleep(2.0)
                    continue
                estado_bandeja("mirando", "te ha oido")
                volumen_antes = bajar_musica()  # como Alexa: baja la musica mientras le hablas
                play_chime_wake()  # modo Alexa: solo un pitido y te escucha
                time.sleep(0.15)  # que el eco del pitido no entre en la orden (antes 0.4)
                try:
                    self.escuchar_orden(recognizer, mic)
                finally:
                    subir_musica(volumen_antes)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log_event(f"Excepción en bucle: {e}")
                time.sleep(1)
        return 0


if __name__ == "__main__":
    kill_other_instances()
    try:  # si la arrancan (a mano o el guardian), deja de estar "apagada"
        os.remove(VOZ_APAGADA)
    except OSError:
        pass
    iniciar_bandeja()
    threading.Thread(target=vigilar_mascota, daemon=True).start()
    threading.Thread(target=vigilar_aduana, daemon=True).start()
    sys.exit(NovaVoz().bucle())
