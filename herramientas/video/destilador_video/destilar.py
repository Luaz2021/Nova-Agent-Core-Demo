"""
DESTILADOR DE VIDEO de Nova (Claude, 23/11/2026). Todo en LOCAL: Whisper oye, InternVL ve, Qwen redacta.

Modos:
  clase       grabacion de clase (Teams, pantalla compartida): transcripcion con minutos, capturas cuando
              cambia la pantalla o el profe dice "fijaos / este codigo / el error...", InternVL lee esas
              capturas (codigo, diapositiva, consola) y Qwen saca el resumen + lista "a verificar".
  referencia  reel / TikTok / video de referencia: cortes de plano, que se ve y se dice en cada plano,
              gancho de los 3 primeros segundos, ritmo, textos en pantalla y leccion para nuestros videos.

Uso (con el Python de su entorno, NO el de Nova):
  <PYTHON> destilar.py <video o URL> --modo clase   (salta solo a su entorno: ~/nova_destilador/env)
  opciones: --out DIR  --modelo small|medium|large-v3-turbo  --sin-vista  --sin-resumen  --cpu
            --desde MM:SS --hasta MM:SS (solo un trozo)

Salida (carpeta): transcripcion.txt, capturas\\*.jpg, vista.md, resumen.md, datos.json
Nada sale a internet salvo la descarga de la URL (yt-dlp). La investigacion la hace Nova despues con
la lista "A verificar" del resumen (solo terminos, nunca la grabacion).
"""

import os
import subprocess
import sys

# Nova lo lanza con $env:NOVA_PYTHON: si no estamos en el entorno del destilador, saltamos a el.
_ENV = os.path.join(os.path.expanduser("~"), "nova_destilador", "env")  # v3.3: Windows, macOS y Linux
_ENV_PY = os.path.join(_ENV, "Scripts", "python.exe") if os.name == "nt" else os.path.join(_ENV, "bin", "python")
if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(_ENV_PY)):
    if not os.path.exists(_ENV_PY):
        print("FALTA el entorno del destilador en este equipo. Ejecuta (una vez, ~3 GB con GPU NVIDIA):\n  \""
              + sys.executable + "\" \"" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "instalar.py") + "\"")
        sys.exit(2)
    _entorno = dict(os.environ)
    if sys.platform.startswith("linux"):  # v3.3: las librerias CUDA de los paquetes nvidia-* (antes de arrancar)
        import glob as _glob
        _libs = _glob.glob(os.path.join(_ENV, "lib", "python3*", "site-packages", "nvidia", "*", "lib"))
        if _libs:
            _entorno["LD_LIBRARY_PATH"] = os.pathsep.join(_libs + [_entorno.get("LD_LIBRARY_PATH", "")])
    sys.exit(subprocess.call([_ENV_PY, "-I", os.path.abspath(__file__)] + sys.argv[1:], env=_entorno))

import argparse  # noqa: E402
import base64
import gc
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np

# --- CUDA de los paquetes nvidia-* del entorno (sin instalar CUDA en Windows) ---
_SP = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
for _d in (glob.glob(str(_SP / "*" / "bin")) if os.name == "nt" else []):  # en Linux: LD_LIBRARY_PATH (arriba)
    os.add_dll_directory(_d)
    os.environ["PATH"] = _d + os.pathsep + os.environ["PATH"]

import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
NOVA_HOME = Path.home() / ".gemini"
SALIDA_DEFECTO = NOVA_HOME / "antigravity" / "documentos_generados" / "destilados"

# Frases del profe que suelen significar "mira la pantalla"
PISTAS = re.compile(
    r"\b(f[ií]jate|fijaos|mirad|mira |veis|ves aqu[ií]|aqu[ií] (tenemos|tengo|est[aá]|veis|vemos)|"
    r"este c[oó]digo|en (la )?pantalla|como (se )?ve|el error|la consola|ejecut|compil|"
    r"esta l[ií]nea|este m[eé]todo|esta clase|el diagrama|esta diapositiva)",
    re.IGNORECASE,
)

CONFIG = {
    # muestras por segundo, umbral de cambio (0-255), separacion minima (s), recorte (izq, arr, der, abajo)
    "clase": dict(fps=0.5, umbral=5.0, umbral_px=0.015, hueco=8.0, recorte=(0.05, 0.08, 0.25, 0.10), max_base=6, max_min=0.8, tope=40),
    "referencia": dict(fps=4.0, umbral=22.0, hueco=0.4, recorte=(0, 0, 0, 0), max_base=16, max_min=0, tope=16),
}


COLA = Path.home() / "nova_destilador" / "en_marcha.json"
PLAN = {}  # lo rellena perfil_y_plan() en main()


# ---------------------------------------------------------------- equipo y cola
def _ram_gb():
    """(total, libre) en GB: API de Windows; en macOS/Linux con psutil (va en el entorno del destilador)."""
    if os.name != "nt":
        try:
            import psutil

            m = psutil.virtual_memory()
            return round(m.total / 2**30, 1), round(m.available / 2**30, 1)
        except Exception:
            return 8.0, 4.0  # sin datos: plan prudente
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MS()
    m.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return round(m.ullTotalPhys / 2**30, 1), round(m.ullAvailPhys / 2**30, 1)


def _gpu():
    """(nombre, total_gb, libre_gb) de la 1a GPU NVIDIA, o None."""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
        nombre, total, libre = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
        return nombre, round(float(total) / 1024, 1), round(float(libre) / 1024, 1)
    except Exception:
        return None


def liberar_ollama():
    """Descarga los modelos de Ollama que esten ocupando la GPU (otra tarea de Nova, p. ej.)."""
    try:
        for m in ollama("/api/ps", None, timeout=10).get("models", []):
            descargar_modelo(m["name"])
    except Exception:
        pass


def perfil_y_plan(a):
    """Mira GPU y RAM y reparte el trabajo. Los modelos van UNO DETRAS DE OTRO, asi que manda la GPU TOTAL."""
    ram_t, ram_l = _ram_gb()
    g = _gpu()
    sim = os.environ.get("DESTILADOR_SIMULAR")  # pruebas: "vram=8,ram=6" hace como si el equipo fuera asi
    if sim:
        s = dict(x.split("=") for x in sim.split(","))
        if "vram" in s:
            g = (f"SIMULADA ({g[0] if g else 'sin GPU'})", float(s["vram"]), float(s["vram"])) if float(s["vram"]) else None
        if "ram" in s:
            ram_l = float(s["ram"])
    p = dict(ram_total=ram_t, ram_libre=ram_l, gpu=g[0] if g else None,
             vram_total=g[1] if g else 0, vram_libre=g[2] if g else 0, cpu_hilos=os.cpu_count() or 4)
    vt = p["vram_total"]
    plan = dict(dispositivo="cuda" if vt >= 3 and not a.cpu else "cpu")
    if plan["dispositivo"] == "cuda":
        plan["whisper"] = "large-v3-turbo" if vt >= 11 else ("medium" if vt >= 6 else "small")
    else:
        plan["whisper"] = "small" if ram_l >= 4 else "base"
    if a.modo == "referencia" and plan["whisper"] in ("medium", "large-v3-turbo"):
        plan["whisper"] = "small"  # reels: poca voz, prima la rapidez
    if a.modelo:
        plan["whisper"] = a.modelo
    # Ver (InternVL ~6 GB) y redactar (Qwen ~6,5 GB): con menos de 7 GB van muy lentos -> menos capturas/contexto
    plan["vista"] = not a.sin_vista and (vt >= 6 or ram_l >= 10)
    plan["factor_capturas"] = 1.0 if vt >= 10 else (0.7 if vt >= 7 else 0.4)
    plan["ancho_captura"] = 1280 if vt >= 7 else 960
    plan["ctx_qwen"] = 16384 if vt >= 10 else (12288 if vt >= 7 else 8192)
    plan["tramo_s"] = 600 if plan["ctx_qwen"] >= 12288 else 420
    if ram_l < 4:
        plan["aviso"] = f"poca RAM libre ({ram_l} GB): cierra programas o ira lento"
    return p, plan


def _vivo(pid):
    if os.name != "nt":  # v3.3: macOS/Linux
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, ValueError):
            return False
    import ctypes
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(codigo))
    ctypes.windll.kernel32.CloseHandle(h)
    return codigo.value == 259  # STILL_ACTIVE


def esperar_turno(nombre, max_min=180):
    """Un destilado cada vez en el equipo: si hay otro en marcha, este espera (no se pelean por la GPU)."""
    COLA.parent.mkdir(parents=True, exist_ok=True)
    avisado = False
    fin = time.time() + max_min * 60
    while time.time() < fin:
        try:
            fd = os.open(str(COLA), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "video": nombre, "desde": f"{datetime.now():%H:%M:%S}"}).encode())
            os.close(fd)
            return
        except FileExistsError:
            try:
                otro = json.loads(COLA.read_text(encoding="utf-8"))
            except Exception:
                otro = {}
            if not otro.get("pid") or not _vivo(otro["pid"]):
                COLA.unlink(missing_ok=True)  # quedo de un destilado que murio
                continue
            if not avisado:
                log(f"EN COLA: ya se esta destilando '{otro.get('video')}' (desde {otro.get('desde')}). Espero mi turno...")
                avisado = True
            time.sleep(10)
    raise SystemExit("Llevo demasiado en cola: revisa si el otro destilado se colgo.")


def soltar_turno():
    try:
        if json.loads(COLA.read_text(encoding="utf-8")).get("pid") == os.getpid():
            COLA.unlink()
    except Exception:
        pass


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def mmss(t):
    t = int(max(t, 0))
    return f"{t // 3600:d}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def a_segundos(s):
    if s is None:
        return None
    partes = [float(p) for p in str(s).split(":")]
    seg = 0.0
    for p in partes:
        seg = seg * 60 + p
    return seg


def modelo_nova(clave, defecto):
    try:
        f = NOVA_HOME / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(f.read_text(encoding="utf-8")).get(clave) or defecto
    except Exception:
        return defecto


# ---------------------------------------------------------------- video
def bajar_si_url(entrada, carpeta):
    if not re.match(r"https?://", entrada):
        return Path(entrada)
    log("Descargando con yt-dlp...")
    destino = carpeta / "video.%(ext)s"
    cmd = [sys.executable, "-m", "yt_dlp", "--no-playlist", "-f", "b/best", "--ffmpeg-location", FFMPEG,
           "-o", str(destino), entrada]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    vids = [p for p in carpeta.glob("video.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not vids:
        raise RuntimeError("yt-dlp no pudo bajar el video: " + (r.stderr or r.stdout)[-300:])
    return vids[0]


def duracion(video):
    r = subprocess.run([FFMPEG, "-i", str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def recortar(video, desde, hasta, carpeta):
    """Corta un trozo sin recodificar (para pruebas o para destilar solo una parte)."""
    out = carpeta / "trozo.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    if desde:
        cmd += ["-ss", str(desde)]
    cmd += ["-i", str(video)]
    if hasta:
        cmd += ["-t", str(hasta - (desde or 0))]
    cmd += ["-c", "copy", str(out)]
    subprocess.run(cmd, check=True)
    return out


def distinta(a, b, c):
    """25/11 (Claude, laptop): dos diapositivas con el MISMO fondo y distinto codigo/texto apenas mueven la media
    (medido: 3,4 con umbral 5) pero cambian con fuerza un 3 % de los pixeles. Cuenta como pantalla nueva si mas de
    c['umbral_px'] de los pixeles cambia mas de 40 niveles (un raton o un cursor son <0,2 %)."""
    lim = c.get("umbral_px")
    return bool(lim) and float((np.abs(a - b) > 40).mean()) > lim


def escenas(video, modo, dur):
    """Cambios de pantalla: muestras pequenas en gris por tuberia (rapido, sin IA)."""
    c = CONFIG[modo]
    w, h = 192, 108
    cmd = [FFMPEG, "-loglevel", "error", "-i", str(video), "-vf",
           f"fps={c['fps']},scale={w}:{h},format=gray", "-f", "rawvideo", "-"]
    datos = subprocess.run(cmd, capture_output=True).stdout
    n = len(datos) // (w * h)
    if n == 0:
        return [0.0], []
    fr = np.frombuffer(datos[: n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.int16)
    l, a, d, b = c["recorte"]
    fr = fr[:, int(a * h): h - int(b * h), int(l * w): w - int(d * w)]
    cortes, fuerza = [0.0], [999.0]
    ref = fr[0]
    for i in range(1, n):
        diff = float(np.abs(fr[i] - ref).mean())
        t = i / c["fps"]
        if diff > c["umbral"] or distinta(fr[i], ref, c):
            # en clase exigimos que la pantalla nueva aguante (evita ratones y ventanas de paso)
            estable = modo == "referencia" or i + 1 >= n or float(np.abs(fr[i + 1] - fr[i]).mean()) < c["umbral"]
            if estable and t - cortes[-1] >= c["hueco"]:
                cortes.append(round(t, 2))
                fuerza.append(diff)
            ref = fr[i]
    return cortes, fuerza


def miniatura(img):
    """Gris 192x108 de una captura (para no mirar dos veces la misma pantalla)."""
    datos = subprocess.run([FFMPEG, "-loglevel", "error", "-i", str(img), "-vf", "scale=192:108,format=gray",
                            "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(datos[: 192 * 108], dtype=np.uint8).reshape(108, 192).astype(np.int16)


def captura(video, t, destino, ancho=1280):
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
           "-vf", f"scale={ancho}:-2", "-q:v", "3", str(destino)]
    subprocess.run(cmd, check=True)
    return destino


# ---------------------------------------------------------------- audio
def transcribir(video, modelo, idioma, cpu):
    from faster_whisper import WhisperModel

    # audio decodificado por FFmpeg (16 kHz mono float32): evita PyAV, que rompe con algunas versiones
    crudo = subprocess.run([FFMPEG, "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(crudo, dtype=np.float32)
    if audio.size == 0:
        return [], idioma or "?", "sin audio"
    intentos = [("cpu", "int8")] if cpu else [("cuda", "int8_float16"), ("cpu", "int8")]
    hilos = max(2, (os.cpu_count() or 4) - 2)  # deja 2 hilos libres para que el equipo no se congele
    for dispositivo, tipo in intentos:
        try:
            nombre_m = modelo if dispositivo == "cuda" else (modelo if modelo in ("tiny", "base", "small") else "small")
            m = WhisperModel(nombre_m, device=dispositivo, compute_type=tipo, cpu_threads=hilos)
            segs, info = m.transcribe(audio, language=idioma, vad_filter=True, beam_size=5,
                                      condition_on_previous_text=False)
            lista = [dict(ini=round(s.start, 2), fin=round(s.end, 2), texto=s.text.strip()) for s in segs]
            del m
            gc.collect()
            return lista, info.language, dispositivo
        except Exception as e:  # sin GPU / sin DLL -> CPU
            log(f"Whisper en {dispositivo} fallo ({str(e)[:90]}); probando otra via...")
    raise RuntimeError("Whisper no pudo transcribir")


# ---------------------------------------------------------------- ollama
def ollama(ruta, cuerpo, timeout=600):
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    req = urllib.request.Request(f"{OLLAMA}{ruta}", data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def descargar_modelo(modelo):
    try:
        ollama("/api/generate", {"model": modelo, "keep_alive": 0}, timeout=60)
    except Exception:
        pass


PROMPT_VISTA = {
    "clase": ("Fotograma de una clase online (pantalla compartida). Describe SOLO el contenido principal: "
              "diapositiva, codigo, consola, IDE o diagrama. Si hay codigo, copialo EXACTO en un bloque ```. "
              "Si hay un error en consola, copialo. Ignora barra de tareas, pestanas del navegador, hora, tiempo, "
              "y NO escribas nombres de personas. En espanol, maximo 150 palabras."),
    "referencia": ("Fotograma de un video corto (reel/TikTok). Describe en espanol, maximo 70 palabras: encuadre y "
                   "plano (primer plano, general, cenital...), que aparece, texto en pantalla (copialo exacto), "
                   "colores/estilo y si hay persona hablando a camara. No inventes nada que no se vea."),
}


def mirar(img, modo, modelo):
    b64 = base64.b64encode(Path(img).read_bytes()).decode()
    r = ollama("/api/generate", {"model": modelo, "prompt": PROMPT_VISTA[modo], "images": [b64], "stream": False,
                                 "keep_alive": "2m", "options": {"temperature": 0.1, "num_ctx": 4096}})
    return (r.get("response") or "").strip()


def redactar(prompt, modelo, ctx=None):
    ctx = ctx or PLAN.get("ctx_qwen", 16384)
    r = ollama("/api/chat", {"model": modelo, "stream": False, "think": False, "keep_alive": "2m",
                             "messages": [{"role": "user", "content": prompt}],
                             "options": {"temperature": 0.2, "num_ctx": ctx}}, timeout=1200)
    texto = (r.get("message") or {}).get("content", "").strip()
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.S).strip()


# ---------------------------------------------------------------- pasos
def elegir_momentos(cortes, fuerza, segs, modo, dur):
    c = CONFIG[modo]
    momentos = [(t, "cambio de pantalla" if t > 0 else "inicio", f) for t, f in zip(cortes, fuerza)]
    if modo == "clase":
        for s in segs:
            if PISTAS.search(s["texto"]):
                t = (s["ini"] + s["fin"]) / 2
                if all(abs(t - m[0]) > 20 for m in momentos):
                    momentos.append((t, "el profe senala algo", 5.0))
    tope = min(c["tope"], int(c["max_base"] + c["max_min"] * dur / 60))
    tope = max(4, int(tope * PLAN.get("factor_capturas", 1.0)))  # menos GPU -> menos capturas a InternVL
    if len(momentos) > tope:  # nos quedamos con los cambios mas fuertes, repartidos
        momentos = sorted(momentos, key=lambda m: -m[2])[:tope]
    return sorted(momentos)


def texto_tramo(segs, ini, fin):
    return " ".join(f"[{mmss(s['ini'])}] {s['texto']}" for s in segs if ini <= s["ini"] < fin)


def resumen_clase(segs, vista, dur, modelo, titulo):
    tramo = PLAN.get("tramo_s", 600)
    bloque = tramo if dur > tramo * 1.5 else dur + 1  # tramos de 7-10 min en clases largas (segun GPU)
    notas = []
    t = 0.0
    while t < dur:
        fin = t + bloque
        oido = texto_tramo(segs, t, fin)
        visto = "\n".join(f"[{mmss(v['t'])}] {v['descripcion']}" for v in vista if t <= v["t"] < fin)
        if oido.strip() or visto.strip():
            p = (f"Clase: {titulo}. Tramo {mmss(t)}-{mmss(min(fin, dur))}.\n\n"
                 f"LO QUE SE DICE (transcripcion automatica, puede tener errores de palabras tecnicas):\n{oido}\n\n"
                 f"LO QUE SE VE EN PANTALLA (descripcion automatica de capturas):\n{visto or '(sin capturas)'}\n\n"
                 "Haz notas de estudio en espanol de este tramo: cada idea con su minuto [mm:ss]. Cruza lo que se dice "
                 "con lo que se ve: si el profe dice 'este bucle' y en pantalla hay codigo, pon el codigo. Corrige "
                 "terminos tecnicos mal transcritos (Java, Kotlin, thread, ArrayList...) solo si es evidente. "
                 "NO inventes nada que no este arriba. Ignora saludos, problemas de audio y charla administrativa.")
            notas.append(redactar(p, modelo))
        t = fin
    juntas = "\n\n---\n\n".join(notas)
    final = (f"Clase: {titulo} ({mmss(dur)}). Notas por tramos:\n\n{juntas}\n\n"
             "Escribe el RESUMEN FINAL en Markdown, en espanol, conciso, con estas secciones exactas:\n"
             "## En una frase\n## Resumen (5-10 vinetas con [mm:ss])\n## Conceptos clave (termino: explicacion corta)\n"
             "## Codigo y ejemplos vistos (bloques ``` con su minuto; omite la seccion si no hubo codigo)\n"
             "## Tareas, fechas o avisos del profe (omite si no hay)\n"
             "## A verificar (dudas, cosas incompletas o que pueden estar mal, y 2-5 busquedas cortas para "
             "investigar, como terminos de busqueda)\n"
             "Reglas: nada inventado. No anadas nombres de clases, metodos, paquetes o librerias que no aparezcan "
             "en las notas (lo que tu sepas de mas va SOLO como busqueda en 'A verificar'). Si algo no quedo claro, "
             "va a 'A verificar'.")
    return redactar(final, modelo)


def resumen_referencia(segs, vista, cortes, dur, modelo, titulo):
    cpm = round(len(cortes) / dur * 60, 1) if dur else 0
    oido = texto_tramo(segs, 0, dur + 1) or "(sin voz)"
    visto = "\n".join(f"[{v['t']:.1f}s] {v['descripcion']}" for v in vista)
    p = (f"Video de referencia: {titulo}. Duracion {dur:.1f}s, {len(cortes)} planos, {cpm} cortes/min, "
         f"plano medio {dur / max(len(cortes), 1):.1f}s. Cortes en segundos: {cortes[:40]}\n\n"
         f"VOZ:\n{oido}\n\nPLANOS (lo que se ve):\n{visto}\n\n"
         "Analiza en Markdown y en espanol, con estas secciones exactas:\n"
         "## Gancho (0-3 s: que se ve y que se dice, por que engancha)\n## Estructura (planos agrupados por partes)\n"
         "## Ritmo y montaje (cortes, duracion de planos, movimientos)\n## Textos en pantalla\n"
         "## Estilo visual\n## Leccion para nuestros videos (3-5 vinetas replicables)\n"
         "Reglas: solo lo que esta en los datos; si algo no se puede saber, dilo.")
    return redactar(p, modelo)


# ---------------------------------------------------------------- main
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Destilador de video local (clase / referencia)")
    ap.add_argument("entrada")
    ap.add_argument("--modo", choices=["clase", "referencia"], default="clase")
    ap.add_argument("--out")
    ap.add_argument("--modelo", default=None, help="Whisper: small | medium | large-v3-turbo")
    ap.add_argument("--idioma", default=None)
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    ap.add_argument("--sin-vista", action="store_true")
    ap.add_argument("--sin-resumen", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    tiempos = {}
    base = a.entrada.split("?")[0].rstrip("/")
    nombre = re.sub(r"[^\w-]+", "_", base.split("/")[-1] if re.match(r"https?://", base) else Path(base).stem)[:50]
    nombre = nombre or "video"
    import atexit

    esperar_turno(nombre)  # un destilado cada vez en este equipo
    atexit.register(soltar_turno)
    perfil, plan = perfil_y_plan(a)
    PLAN.update(plan)
    gpu_txt = (f"{perfil['gpu']} {perfil['vram_total']} GB (libre {perfil['vram_libre']})" if perfil["gpu"]
               else "sin GPU NVIDIA")
    log(f"Equipo: {gpu_txt} | RAM {perfil['ram_total']} GB (libre {perfil['ram_libre']}) -> Whisper {plan['whisper']} "
        f"en {plan['dispositivo']}, capturas x{plan['factor_capturas']}, contexto Qwen {plan['ctx_qwen']}")
    if plan.get("aviso"):
        log("AVISO: " + plan["aviso"])

    out = Path(a.out) if a.out else SALIDA_DEFECTO / f"{datetime.now():%Y%m%d_%H%M}_{nombre}"
    (out / "capturas").mkdir(parents=True, exist_ok=True)

    video = bajar_si_url(a.entrada, out)
    if a.desde or a.hasta:
        video = recortar(video, a_segundos(a.desde), a_segundos(a.hasta), out)
    dur = duracion(video)
    log(f"Video: {nombre} | {mmss(dur)} | modo {a.modo} | salida {out}")

    # 1. Oir (antes se descargan de la GPU los modelos de Ollama que haya dejado otra tarea)
    if plan["dispositivo"] == "cuda":
        liberar_ollama()
    t = time.time()
    modelo_w = plan["whisper"]
    idioma = a.idioma or ("es" if a.modo == "clase" else None)
    segs, lengua, disp = transcribir(video, modelo_w, idioma, plan["dispositivo"] == "cpu")
    tiempos["transcribir"] = round(time.time() - t, 1)
    (out / "transcripcion.txt").write_text(
        "\n".join(f"[{mmss(s['ini'])}] {s['texto']}" for s in segs), encoding="utf-8")
    log(f"1/4 Transcrito: {len(segs)} frases, {sum(len(s['texto'].split()) for s in segs)} palabras "
        f"({disp}, {modelo_w}, {tiempos['transcribir']} s)")

    # 2. Momentos a mirar
    t = time.time()
    cortes, fuerza = escenas(video, a.modo, dur)
    momentos = elegir_momentos(cortes, fuerza, segs, a.modo, dur)
    tiempos["escenas"] = round(time.time() - t, 1)
    log(f"2/4 Cambios de pantalla: {len(cortes)} | momentos a mirar: {len(momentos)} ({tiempos['escenas']} s)")

    # 3. Ver
    t = time.time()
    vista = []
    modelo_vl = modelo_nova("vl", "blaifa/InternVL3_5:8b")
    previa = None  # (miniatura, minuto) de la ultima captura mirada: si la pantalla es igual no se repite
    for i, (tm, motivo, _) in enumerate(momentos, 1):
        img = captura(video, tm, out / "capturas" / f"{i:03d}_{mmss(tm).replace(':', '-')}.jpg",
                      ancho=plan["ancho_captura"])
        desc = ""
        mini = miniatura(img)
        if (previa is not None and float(np.abs(mini - previa[0]).mean()) < CONFIG[a.modo]["umbral"] * 0.6
                and not distinta(mini, previa[0], CONFIG[a.modo])):
            img.unlink(missing_ok=True)
            continue  # misma pantalla que la anterior: ni captura ni InternVL
        previa = (mini, tm)
        if plan["vista"]:
            try:
                desc = mirar(img, a.modo, modelo_vl)
            except Exception as e:
                desc = f"(InternVL no respondio: {str(e)[:80]})"
        vista.append(dict(t=round(tm, 2), motivo=motivo, captura=img.name, descripcion=desc))
    descargar_modelo(modelo_vl)  # libera la GPU para Qwen (clave en 8 GB)
    tiempos["ver"] = round(time.time() - t, 1)
    with open(out / "vista.md", "w", encoding="utf-8") as f:
        for v in vista:
            f.write(f"### [{mmss(v['t'])}] {v['motivo']}\n![]({'capturas/' + v['captura']})\n\n{v['descripcion']}\n\n")
    log(f"3/4 Capturas vistas: {len(vista)} ({tiempos['ver']} s)")

    # 4. Redactar
    resumen = ""
    if not a.sin_resumen:
        t = time.time()
        modelo_q = modelo_nova("coder", "qwen3.5:9b")
        titulo = nombre if re.match(r"https?://", a.entrada) else Path(a.entrada).stem[:80]
        if a.modo == "clase":
            resumen = resumen_clase(segs, vista, dur, modelo_q, titulo)
        else:
            resumen = resumen_referencia(segs, vista, cortes, dur, modelo_q, titulo)
        descargar_modelo(modelo_q)
        tiempos["resumir"] = round(time.time() - t, 1)
        cab = (f"# {titulo}\n\n> Destilado en local el {datetime.now():%d/%m/%Y %H:%M} | {mmss(dur)} | modo {a.modo} | "
               f"Whisper {modelo_w} ({disp}) | {len(vista)} capturas. Transcripcion: transcripcion.txt, "
               f"capturas: vista.md\n\n")
        (out / "resumen.md").write_text(cab + resumen + "\n", encoding="utf-8")
        log(f"4/4 Resumen listo ({tiempos['resumir']} s)")

    tiempos["total"] = round(time.time() - t0, 1)
    datos = dict(entrada=a.entrada, modo=a.modo, duracion_s=round(dur, 1), idioma=lengua, whisper=modelo_w,
                 dispositivo=disp, equipo=perfil, plan=plan, cortes=cortes,
                 momentos=[dict(t=v["t"], motivo=v["motivo"]) for v in vista], tiempos=tiempos)
    (out / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    for tmp in ("trozo.mp4",):
        (out / tmp).unlink(missing_ok=True)
    log(f"OK en {tiempos['total']} s -> {out}")
    print(json.dumps({"ok": True, "carpeta": str(out), "tiempos": tiempos}, ensure_ascii=False))


if __name__ == "__main__":
    main()
