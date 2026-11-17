r"""
NOVA · PACK DE VOZ / CLONADOR (v3.2). Voces oficiales: Ayla (Nova) y Marina (guardian y videos).
LAS VOCES AYLA Y MARINA NO SON MIT: solo se pueden usar dentro de Nova (LICENCIA_VOCES.md).

Motor: Qwen3-TTS-12Hz-1.7B-Base (Apache 2.0), en LOCAL con la GPU, acelerado con faster-qwen3-tts (MIT, CUDA graphs):
empieza a sonar en ~0,6 s y genera mas rapido que el tiempo real (16/11; antes ~12 s y 4x mas lento).
Clona con 10-20 s de audio + su texto exacto. Nada sale del equipo.
  hablar --voz nova --texto "..."   -> lo DICE por los altavoces mientras se genera (streaming)
  servidor: POST /hablar (Nova Voz), /decir (archivo), /calentar

Entorno pesado FUERA de Drive (no viaja): %USERPROFILE%\nova_voz_clon\ (env, modelo, voces, salidas).
Montarlo (GPU NVIDIA):  Windows: instalar.ps1 · Linux: sh instalar.sh  (piden aceptar LICENCIA_VOCES.md)

  estado                                         -> entorno, GPU, modelo y voces registradas
  registrar --id ana --audio x.mp4 --texto "..." --permiso   -> crea la voz (recorta silencios, 24 kHz mono)
  decir --voz ana --texto "..." [--salida f.wav] [--mp3]      -> genera el audio con esa voz
        --voz nova  = voz oficial de Nova (ayla) · --voz videos = narradora de videos (marina)  [datos\voz_clon\roles.json]
        --estilo agresiva (ayla). Se genera el texto entero de una vez y CRUDO (sin acelerar ni filtros): aprobado por el autor.
  voces | borrar --voz ana

USO RESPONSABLE (obligatorio): solo voces de personas que han dado su permiso (--permiso). Nunca para hacerse pasar
por alguien ante terceros, ni para enganar. Cada voz guarda quien dio el permiso y cuando.
Nova lo lanza con su Python normal: el script se relanza solo con el Python del entorno de voz.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(os.environ.get("NOVA_VOZ_CLON") or Path.home() / "nova_voz_clon")
PY_ENV = BASE / "env_fq" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")  # entorno de faster-qwen3-tts
VOCES = BASE / "voces"
AQUI = Path(__file__).resolve().parent
VOCES_PACK = AQUI / "voces"  # v3.2: las oficiales llegan con Nova (y con cada parche)
LICENCIA_OK = BASE / "licencia_voces_aceptada.json"  # lo escribe el instalador tras escribir ACEPTO
OFICIALES = {"ayla", "marina"}
SALIDAS = BASE / "salidas"
HF = BASE / "hf"
MODELO_HF = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
# En Windows sin permiso de enlaces simbolicos la cache de Hugging Face falla: el modelo se baja a una carpeta normal.
MODELO = str(BASE / "modelo") if (BASE / "modelo" / "config.json").exists() else MODELO_HF
VOSK = Path.home() / ".gemini" / "antigravity" / "herramientas" / "voz" / "modelos" / "vosk-model-small-es-0.42"
SR_REF = 24000
ROLES = Path(__file__).resolve().parent / "roles.json"  # nova -> ayla, guardian y videos -> marina
# v3.2: MOTORES. NVIDIA (Windows/Linux) = faster-qwen3-tts con CUDA (streaming, ~0,6 s hasta sonar).
# Mac con chip Apple (M1, M2, M3, M4...) = mlx-audio sobre MLX (memoria unificada), mismo Qwen3-TTS 1.7B en 8 bits.
# El motor MLX es EXPERIMENTAL hasta probarlo en Macs reales: genera la frase entera y la reproduce (sin streaming).
import platform  # noqa: E402

MLX = sys.platform == "darwin" and platform.machine() == "arm64"
MODELO_MLX_HF = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
MODELO_MLX = str(BASE / "modelo_mlx") if (BASE / "modelo_mlx" / "config.json").exists() else MODELO_MLX_HF


def relanzar_si_hace_falta() -> None:
    """Nova usa su Python (sin torch): se relanza este mismo script con el Python del entorno de voz."""
    try:
        if MLX:
            import mlx_audio  # noqa: F401
        else:
            import faster_qwen3_tts  # noqa: F401
        return
    except ImportError:
        pass
    if not PY_ENV.exists():
        print(f"[VOZ] No esta montado el entorno de voz en {BASE}. Ejecuta instalar.ps1 de esta carpeta (una vez).")
        sys.exit(2)
    sys.exit(subprocess.call([str(PY_ENV), str(Path(__file__).resolve()), *sys.argv[1:]]))


def ffmpeg() -> str:
    f = shutil.which("ffmpeg")
    if not f:
        print("[VOZ] Falta ffmpeg en el PATH.")
        sys.exit(2)
    return f


def preparar_audio(origen: Path, destino: Path) -> float:
    """24 kHz mono, sin silencios al principio/final, volumen normalizado. Devuelve la duracion en segundos."""
    filtro = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
              "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse,"
              "highpass=f=60,loudnorm=I=-18:TP=-2:LRA=11")
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(origen), "-ac", "1", "-ar", str(SR_REF), "-af", filtro,
                    str(destino)], check=True)
    import soundfile as sf

    info = sf.info(str(destino))
    return info.frames / info.samplerate


def transcribir_vosk(wav24: Path) -> str:
    """Si no dan el texto: Vosk local (aproximado: revisarlo SIEMPRE, el clon depende de que sea exacto)."""
    nova_py = os.environ.get("NOVA_PYTHON")
    if not nova_py or not VOSK.exists():
        return ""
    tmp = wav24.with_name("tmp16k.wav")
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(wav24), "-ac", "1", "-ar", "16000", str(tmp)], check=True)
    codigo = (
        "import json,sys,wave\nfrom vosk import Model,KaldiRecognizer,SetLogLevel\nSetLogLevel(-1)\n"
        "w=wave.open(sys.argv[2],'rb');r=KaldiRecognizer(Model(sys.argv[1]),w.getframerate());p=[]\n"
        "while True:\n d=w.readframes(4000)\n if not d: break\n if r.AcceptWaveform(d): p.append(json.loads(r.Result())['text'])\n"
        "p.append(json.loads(r.FinalResult())['text']);print(' '.join(x for x in p if x))\n"
    )
    r = subprocess.run([nova_py, "-I", "-c", codigo, str(VOSK), str(tmp)], capture_output=True, text=True, encoding="utf-8")
    tmp.unlink(missing_ok=True)
    return r.stdout.strip()


_MODELO = None


def cargar_modelo():
    global _MODELO
    if _MODELO is None and MLX:
        os.environ.setdefault("HF_HOME", str(HF))
        from mlx_audio.tts.utils import load_model  # Qwen3-TTS 1.7B en 8 bits sobre MLX (Mac con chip Apple)

        t0 = time.time()
        _MODELO = load_model(MODELO_MLX)
        print(f"[VOZ] Modelo cargado en {time.time() - t0:.0f} s (mlx-audio, chip Apple)", flush=True)
    if _MODELO is None:
        os.environ.setdefault("HF_HOME", str(HF))
        from faster_qwen3_tts import FasterQwen3TTS  # mismo Qwen3-TTS 1.7B con CUDA graphs (16/11)

        t0 = time.time()
        _MODELO = FasterQwen3TTS.from_pretrained(MODELO)
        print(f"[VOZ] Modelo cargado en {time.time() - t0:.0f} s (faster-qwen3-tts, GPU)", flush=True)
    return _MODELO


def trocear(texto: str, maximo: int = 650) -> list[str]:
    """15/11: bloques GRANDES (<= 650 caracteres). Generar frase a frase sonaba pausado y robotico (cada trozo arranca en
    frio); el texto entero de una vez da la entonacion continua aprobada por el autor."""
    frases = [f.strip() for f in re.split(r"(?<=[.!?…;:])\s+", re.sub(r"\s+", " ", texto.strip())) if f.strip()]
    trozos, actual = [], ""
    for f in frases:
        if len(actual) + len(f) + 1 <= maximo:
            actual = f"{actual} {f}".strip()
        else:
            if actual:
                trozos.append(actual)
            while len(f) > maximo:  # frase enorme: se parte por comas
                corte = f.rfind(",", 0, maximo)
                corte = corte if corte > 40 else maximo
                trozos.append(f[: corte + 1].strip())
                f = f[corte + 1 :].strip()
            actual = f
    if actual:
        trozos.append(actual)
    return trozos


# ---------------------------------------------------------------- ordenes


def orden_estado(_a) -> int:
    print(f"[VOZ] Entorno: {BASE}")
    if MLX:
        descargado = (BASE / "modelo_mlx" / "config.json").exists()
        print(f"[VOZ] Motor: mlx-audio (Mac con chip Apple, EXPERIMENTAL) · modelo {MODELO_MLX_HF}: "
              + ("descargado" if descargado else "NO descargado (ejecuta instalar.sh)"))
        print(f"[VOZ] Licencia de las voces: {'aceptada' if LICENCIA_OK.exists() else 'NO aceptada (instalar.sh)'}")
        return orden_voces(_a)
    import torch

    print(f"[VOZ] Licencia de las voces: {'aceptada' if LICENCIA_OK.exists() else 'NO aceptada (instalador del pack)'}")
    print(f"[VOZ] PyTorch {torch.__version__} · CUDA {torch.version.cuda} · GPU: "
          + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO (ira muy lento)"))
    descargado = (BASE / "modelo" / "config.json").exists()
    print(f"[VOZ] Modelo {MODELO_HF}: {'descargado en ' + str(BASE / 'modelo') if descargado else 'NO descargado (ejecuta instalar.ps1)'}")
    return orden_voces(_a)


def orden_voces(_a) -> int:
    voces = sorted(set(VOCES.glob("*/voz.json")) | set(VOCES_PACK.glob("*/voz.json")))
    if not voces:
        print("[VOZ] No hay voces registradas.")
    for p in voces:
        m = json.loads(p.read_text(encoding="utf-8"))
        print(f"  - {m['id']}: {m.get('nombre', '')} · {m['duracion']:.1f} s · permiso: {m.get('permiso', '?')} · {m['fecha']}")
    return 0


def orden_registrar(a) -> int:
    if not a.permiso:
        print("[VOZ] FRENO: solo se clonan voces con permiso de su dueno/a. Si lo tienes, anade --permiso "
              "(y --quien \"nombre de quien lo dio\").")
        return 1
    vid = re.sub(r"[^a-z0-9_-]", "_", a.id.lower())
    origen = Path(a.audio)
    if not origen.exists():
        print(f"[VOZ] No existe el audio: {origen}")
        return 2
    carpeta = VOCES / vid
    carpeta.mkdir(parents=True, exist_ok=True)
    ref = carpeta / "referencia.wav"
    dur = preparar_audio(origen, ref)
    if dur < 5:
        print(f"[VOZ] FRENO: solo hay {dur:.1f} s de voz. Hacen falta 10-20 s.")
        return 1
    if dur > 25:
        print(f"[VOZ] Aviso: {dur:.1f} s de voz. Con 10-20 s basta; mas no mejora y puede empeorar.")
    texto = (a.texto or "").strip()
    if not texto:
        texto = transcribir_vosk(ref)
        print(f"[VOZ] Texto sacado con Vosk (REVISALO, debe ser exacto): {texto}")
        if not texto:
            print("[VOZ] FRENO: falta --texto con lo que dice el audio, palabra por palabra.")
            return 1
    meta = {"id": vid, "nombre": a.nombre or vid, "texto": texto, "duracion": dur, "idioma": a.idioma,
            "permiso": a.quien or "si (sin nombre)", "fecha": time.strftime("%Y-%m-%d %H:%M"), "origen": origen.name}
    (carpeta / "voz.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[VOZ] Voz '{vid}' registrada ({dur:.1f} s de voz). Prueba: clonador.py decir --voz {vid} --texto \"Hola\"")
    return 0


class VozNoExiste(Exception):
    pass


IDIOMAS = {"es": "Spanish", "en": "English", "fr": "French", "it": "Italian", "pt": "Portuguese", "de": "German"}


def resolver_voz(voz: str, estilo: str = "") -> tuple[dict, dict]:
    """voz puede ser un rol (nova, videos) o un id (ayla, marina). Devuelve (meta, estilo)."""
    roles = json.loads(ROLES.read_text(encoding="utf-8")) if ROLES.exists() else {}
    rol = roles.get(voz.lower()) if isinstance(roles.get(voz.lower()), dict) else {}
    nombre = re.sub(r"[^a-z0-9_-]", "_", rol.get("voz", voz).lower())
    if nombre in OFICIALES and not LICENCIA_OK.exists():
        raise VozNoExiste(f"La voz '{nombre}' solo se usa tras aceptar LICENCIA_VOCES.md (ejecuta el instalador del pack de voz).")
    carpeta = next((d / nombre for d in (VOCES, VOCES_PACK) if (d / nombre / "voz.json").exists()), VOCES / nombre)
    if not (carpeta / "voz.json").exists():
        raise VozNoExiste(f"No existe la voz '{voz}'. Roles: {', '.join(k for k in roles if not k.startswith('_'))}")
    meta = json.loads((carpeta / "voz.json").read_text(encoding="utf-8"))
    meta["_carpeta"] = str(carpeta)
    nombre_estilo = estilo or rol.get("estilo_por_defecto", "")
    est = (roles.get("estilos", {}).get(meta["id"], {}).get(nombre_estilo) or {}) if nombre_estilo else {}
    return meta, est


def generar(voz: str, texto: str, estilo: str = "", salida: str = "", mp3: bool = False) -> dict:
    """Genera el audio con la voz pedida. Devuelve {archivo, duracion, segundos, voz}. Lo usan decir, lote y servidor."""
    import numpy as np
    import soundfile as sf

    meta, est = resolver_voz(voz, estilo)
    carpeta = Path(meta["_carpeta"])
    modelo = cargar_modelo()
    ref = str(carpeta / "referencia.wav")
    trozos = trocear(texto)
    idioma = IDIOMAS.get(meta.get("idioma", "es"), "Spanish")
    t0 = time.time()
    gen = est.get("generacion", {})
    partes, sr = [], 24000
    for trozo in trozos:  # uno a uno y entero: sin acelerar ni filtros (sonido "crudo" aprobado)
        if MLX:  # mlx-audio: generate() devuelve resultados con .audio (mx.array)
            res = list(modelo.generate(text=trozo, ref_audio=ref, ref_text=meta["texto"], lang_code=meta.get("idioma", "es"),
                                       **{k: v for k, v in gen.items() if k in ("temperature", "top_p")}))
            sr = int(getattr(modelo, "sample_rate", 24000))
            partes.append(np.concatenate([np.asarray(r.audio, dtype=np.float32).reshape(-1) for r in res]))
            continue
        wavs, sr = modelo.generate_voice_clone(text=trozo, language=idioma, ref_audio=ref, ref_text=meta["texto"],
                                               max_new_tokens=4096, **gen)
        partes.append(np.asarray(wavs[0], dtype=np.float32).reshape(-1))
    pausa = np.zeros(int(sr * 0.12), dtype=np.float32)
    audio = np.concatenate([x for p in partes for x in (p, pausa)])[: -len(pausa)]
    pico = float(np.max(np.abs(audio))) or 1.0
    audio = audio / pico * 0.89
    SALIDAS.mkdir(parents=True, exist_ok=True)
    destino = Path(salida) if salida else SALIDAS / f"{meta['id']}_{time.strftime('%Y%m%d_%H%M%S')}.wav"
    destino.parent.mkdir(parents=True, exist_ok=True)
    final = destino.with_suffix(".wav")
    sf.write(str(final), audio, sr)
    if est.get("filtro"):  # p. ej. marina/locutora: sonido "de radio" aprobado por el autor
        tmp = final.with_name(final.stem + "_tmp.wav")
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(final), "-af", est["filtro"], "-ar", "44100", str(tmp)], check=True)
        tmp.replace(final)
        audio, sr = sf.read(str(final))
    if mp3:
        m = destino.with_suffix(".mp3")
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", str(final), "-b:a", "192k", str(m)], check=True)
        final = m
    return {"archivo": str(final), "duracion": round(len(audio) / sr, 2), "segundos": round(time.time() - t0, 1),
            "voz": meta["id"], "frases": len(trozos)}


# con la GPU compartida (Antigravity, navegador, Qwen) el modelo genera
# ~1,2x MAS LENTO que el tiempo real, y como sonaba a la vez que se generaba, se quedaba sin audio a mitad de frase
# (medido: 8,6 s de audio sonaron en 12,3 s, con 2 cortes). Ahora:
#  - COLCHON justo: antes de sonar se guarda la ventaja minima para no cortarse nunca: duracion_estimada * (1 - 1/r),
#    con r = lo lento que va la GPU, medido en cada frase (si la GPU va sobrada, empieza casi al instante).
#  - ALTAVOZ SIEMPRE ABIERTO: abrirlo costaba ~1 s de silencio en cada llamada de Nova Voz.
_ALTAVOZ: dict = {"flujo": None, "sonando": False}  # sonando: sale audio por el altavoz AHORA (para el monito)
# segundos de GPU por segundo de audio, POR VOZ (17/11: Marina heredaba lo aprendido con Ayla y se corto 1 s).
# Se ajusta solo con cada frase y se recuerda entre reinicios.
_LENTITUD: dict = {}
LENTITUD_INICIAL = 1.3
_LENTITUD_ARCHIVO = BASE / "lentitud_gpu.json"
try:
    _d = json.loads(_LENTITUD_ARCHIVO.read_text(encoding="utf-8"))
    _LENTITUD.update({k: min(2.0, max(0.5, float(v))) for k, v in (_d.get("voces") or {}).items()})
except Exception:
    pass
CARACTERES_POR_SEGUNDO = 16.0  # ritmo de habla de Ayla (medido 17/11)
MARGEN_S = 0.5
COLCHON_MIN_S = 0.8  # 17/11: nunca menos de 0,8 s de ventaja (con 0,3 s, una frase con voz nueva se corto)


def _altavoz():
    import sounddevice as sd
    f = _ALTAVOZ["flujo"]
    if f is None or not f.active:
        try:
            if f is not None:
                f.close()
        except Exception:
            pass
        f = sd.OutputStream(samplerate=24000, channels=1, dtype="float32", latency="high")
        f.start()
        _ALTAVOZ["flujo"] = f
    return f


def hablar_mlx(voz: str, texto: str, estilo: str = "") -> dict:
    """Mac con chip Apple: genera la frase entera con MLX y la reproduce con afplay (sin streaming)."""
    t0 = time.time()
    r = generar(voz, texto, estilo, salida=str(SALIDAS / "_hablar_mlx.wav"))
    _ALTAVOZ["sonando"] = True
    try:
        subprocess.run(["afplay", r["archivo"]], check=False)
    finally:
        _ALTAVOZ["sonando"] = False
    return {"voz": r["voz"], "primer_sonido": r["segundos"], "duracion": r["duracion"],
            "segundos": round(time.time() - t0, 1), "cortes": 0, "motor": "mlx"}


def hablar(voz: str, texto: str, estilo: str = "") -> dict:
    """16/11: lo DICE por los altavoces mientras se genera (streaming). 17/11: con colchon adaptativo para que no se
    corte y con el altavoz siempre abierto. Texto en bloques grandes (entonacion aprobada). Sin filtros (crudo)."""
    if MLX:
        return hablar_mlx(voz, texto, estilo)
    import queue
    import threading

    import numpy as np

    meta, est = resolver_voz(voz, estilo)
    carpeta = Path(meta["_carpeta"])
    modelo = cargar_modelo()
    idioma = IDIOMAS.get(meta.get("idioma", "es"), "Spanish")
    gen = est.get("generacion", {})
    t0, info = time.time(), {"primero": None, "muestras": 0, "sr": 24000, "cortes": 0}
    cola: queue.Queue = queue.Queue()

    def reproducir():
        """Hilo aparte: la GPU sigue generando mientras suena lo anterior."""
        try:
            flujo = _altavoz()
        except Exception as e:
            print(f"[VOZ] No se pudo abrir el altavoz: {e}", flush=True)
            while cola.get() is not None:
                pass
            return
        while (a := cola.get()) is not None:
            primero = info["primero"] is None
            if primero:
                info["primero"] = time.time() - t0
                _ALTAVOZ["sonando"] = True
            try:
                # True = el altavoz se quedo sin audio (corte). El 1er bloque no cuenta: venia de estar en silencio.
                if flujo.write(a.reshape(-1, 1)) and not primero:
                    info["cortes"] += 1
            except Exception:
                _ALTAVOZ["flujo"] = None  # p. ej. cambiaste de auriculares: se reabre en la siguiente
                flujo = _altavoz()
                flujo.write(a.reshape(-1, 1))
        time.sleep(max(0.0, flujo.latency))  # que suene lo ultimo antes de decir "termine"
        _ALTAVOZ["sonando"] = False

    hilo = threading.Thread(target=reproducir, daemon=True)
    hilo.start()
    try:
        for trozo in trocear(texto):
            r = _LENTITUD.get(meta["id"], LENTITUD_INICIAL)
            estimada = len(trozo) / CARACTERES_POR_SEGUNDO
            colchon = max(COLCHON_MIN_S, estimada * (1 - 1 / r) + MARGEN_S if r > 1 else 0.0)
            guardado, en_cola, sonando = [], 0.0, False
            tg0, muestras = time.time(), 0
            for chunk, sr, _ in modelo.generate_voice_clone_streaming(
                    text=trozo, language=idioma, ref_audio=str(carpeta / "referencia.wav"), ref_text=meta["texto"],
                    max_new_tokens=4096, chunk_size=8, **gen):
                info["sr"] = sr
                info.setdefault("gpu", round(time.time() - t0, 2))
                a = np.clip(np.asarray(chunk, dtype=np.float32).reshape(-1), -1.0, 1.0)
                muestras += len(a)
                if sonando:
                    cola.put(a)
                else:
                    guardado.append(a)
                    en_cola += len(a) / sr
                    if en_cola >= colchon:
                        cola.put(np.concatenate(guardado))
                        guardado, sonando = [], True
            if guardado:
                cola.put(np.concatenate(guardado))
            info["muestras"] += muestras
            dur = muestras / info["sr"]
            if dur > 1.0:  # aprender lo lenta que va la GPU con ESTA voz (media movil)
                _LENTITUD[meta["id"]] = 0.6 * _LENTITUD.get(meta["id"], LENTITUD_INICIAL) + 0.4 * ((time.time() - tg0) / dur)
                try:
                    _LENTITUD_ARCHIVO.write_text(json.dumps({"voces": {k: round(v, 3) for k, v in _LENTITUD.items()}}),
                                                 encoding="utf-8")
                except OSError:
                    pass
    finally:
        cola.put(None)
        hilo.join()
        _ALTAVOZ["sonando"] = False
    return {"voz": meta["id"], "primer_sonido": round(info["primero"] or 0, 2), "primer_trozo_gpu": info.get("gpu"),
            "duracion": round(info["muestras"] / info["sr"], 2), "segundos": round(time.time() - t0, 1),
            "cortes": info["cortes"], "lentitud_gpu": round(_LENTITUD.get(meta["id"], LENTITUD_INICIAL), 2)}


def orden_hablar(a) -> int:
    try:
        r = hablar(a.voz, a.texto, a.estilo)
    except VozNoExiste as e:
        print(f"[VOZ] {e}")
        return 2
    print(f"[VOZ] Dicho con '{r['voz']}': primer sonido a los {r['primer_sonido']} s, {r['duracion']} s de audio")
    return 0


def orden_decir(a) -> int:
    texto = Path(a.archivo).read_text(encoding="utf-8") if a.archivo else a.texto
    if not texto or not texto.strip():
        print("[VOZ] Falta --texto o --archivo.")
        return 2
    try:
        r = generar(a.voz, texto, a.estilo, a.salida, a.mp3)
    except VozNoExiste as e:
        print(f"[VOZ] {e}")
        return 2
    print(f"[VOZ] {r['archivo']}  ({r['duracion']:.1f} s de audio en {r['segundos']:.0f} s, {r['frases']} bloque(s), voz '{r['voz']}')")
    return 0


def orden_lote(a) -> int:
    """Varias frases con UNA sola carga del modelo. JSON: [{"texto": "...", "salida": "ruta.wav"}, ...]"""
    tareas = json.loads(Path(a.json).read_text(encoding="utf-8-sig"))
    for i, t in enumerate(tareas, 1):
        try:
            r = generar(t.get("voz") or a.voz, t["texto"], t.get("estilo") or a.estilo, t.get("salida", ""), a.mp3 or t.get("mp3", False))
        except VozNoExiste as e:
            print(f"[VOZ] {e}")
            return 2
        print(f"[VOZ] {i}/{len(tareas)} {r['archivo']} ({r['duracion']:.1f} s en {r['segundos']:.0f} s)", flush=True)
    return 0


def orden_servidor(a) -> int:
    """Servidor local para Nova Voz (127.0.0.1). Carga el modelo al primer pedido y lo SUELTA de la GPU tras
    --inactivo segundos sin uso (la GPU de 8 GB tambien la necesitan Qwen e InternVL de Ollama)."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    torch = None
    if not MLX:
        import torch

    candado = threading.Lock()
    ultimo = {"t": time.time()}

    def soltar():
        global _MODELO
        while True:
            time.sleep(15)
            with candado:
                if _MODELO is not None and time.time() - ultimo["t"] > a.inactivo:
                    _MODELO = None
                    import gc

                    gc.collect()
                    if torch is not None:
                        torch.cuda.empty_cache()
                    print("[VOZ] Modelo soltado de la GPU por inactividad", flush=True)

    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def _json(self, codigo, datos):
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            self._json(200, {"ok": True, "modelo_cargado": _MODELO is not None, "sonando": bool(_ALTAVOZ["sonando"])})

        def do_POST(self):
            if self.headers.get("Origin") or self.path not in ("/decir", "/hablar", "/calentar"):  # solo procesos locales
                return self._json(403, {"ok": False, "error": "no permitido"})
            if self.path == "/calentar":  # Nova Voz lo pide al oir "Nova": se carga mientras se dicta
                ultimo["t"] = time.time()
                if _MODELO is None:
                    threading.Thread(target=calentar, daemon=True).start()
                return self._json(200, {"ok": True, "cargando": _MODELO is None})
            try:
                d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
                with candado:
                    ultimo["t"] = time.time()
                    if self.path == "/hablar":  # suena aqui mismo en streaming; responde cuando termina de hablar
                        r = hablar(d.get("voz", "nova"), str(d["texto"])[:1500], d.get("estilo", ""))
                    else:
                        r = generar(d.get("voz", "nova"), str(d["texto"])[:1500], d.get("estilo", ""), d.get("salida", ""), bool(d.get("mp3")))
                    ultimo["t"] = time.time()
                self._json(200, {"ok": True, **r})
            except Exception as e:
                self._json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]})

    def calentar():
        """Carga el modelo y genera una frase corta: la primera vez se capturan los CUDA graphs (unos segundos);
        despues empieza a sonar en ~0,6 s."""
        with candado:
            ultimo["t"] = time.time()
            try:
                generar("nova", "Hola.", salida=str(BASE / "salidas" / "_calentar.wav"))
                print("[VOZ] Modelo caliente", flush=True)
            except Exception as e:
                print(f"[VOZ] No se pudo calentar: {e}", flush=True)
            ultimo["t"] = time.time()

    threading.Thread(target=soltar, daemon=True).start()
    threading.Thread(target=calentar, daemon=True).start()  # al arrancar, ya caliente
    srv = ThreadingHTTPServer(("127.0.0.1", a.puerto), Manejador)
    print(f"[VOZ] Servidor de voz en http://127.0.0.1:{a.puerto} (suelta la GPU tras {a.inactivo} s sin uso)", flush=True)
    srv.serve_forever()
    return 0


def orden_borrar(a) -> int:
    if a.voz.lower() in OFICIALES:
        print("[VOZ] Las voces oficiales de Nova no se borran desde aqui.")
        return 2
    carpeta = VOCES / re.sub(r"[^a-z0-9_-]", "_", a.voz.lower())
    if not carpeta.exists():
        print(f"[VOZ] No existe la voz '{a.voz}'.")
        return 2
    shutil.rmtree(carpeta)
    print(f"[VOZ] Voz '{a.voz}' borrada (audio de referencia y perfil).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Clonador de voz de Nova (Qwen3-TTS local)")
    sub = ap.add_subparsers(dest="orden", required=True)
    sub.add_parser("estado")
    sub.add_parser("voces")
    p = sub.add_parser("registrar")
    p.add_argument("--id", required=True)
    p.add_argument("--audio", required=True)
    p.add_argument("--texto", default="", help="lo que dice el audio, EXACTO")
    p.add_argument("--nombre", default="")
    p.add_argument("--idioma", default="es")
    p.add_argument("--permiso", action="store_true", help="la persona ha dado permiso para clonar su voz")
    p.add_argument("--quien", default="", help="quien dio el permiso")
    p = sub.add_parser("decir")
    p.add_argument("--voz", required=True)
    p.add_argument("--texto", default="")
    p.add_argument("--archivo", default="", help="txt con el texto (para textos largos)")
    p.add_argument("--salida", default="")
    p.add_argument("--mp3", action="store_true")
    p.add_argument("--estilo", default="", help="ayla: normal | agresiva · marina: locutora | crudo (datos\\voz_clon\\roles.json)")
    sub.add_parser("borrar").add_argument("--voz", required=True)
    p = sub.add_parser("lote", help='varias frases, una carga: JSON [{"texto","salida"}]')
    p.add_argument("--voz", default="nova")
    p.add_argument("--estilo", default="")
    p.add_argument("--json", required=True)
    p.add_argument("--mp3", action="store_true")
    p = sub.add_parser("servidor", help="servidor local para Nova Voz")
    p.add_argument("--puerto", type=int, default=5010)
    p.add_argument("--inactivo", type=int, default=300, help="segundos sin uso antes de soltar la GPU")
    p = sub.add_parser("hablar", help="lo dice por los altavoces mientras se genera")
    p.add_argument("--voz", default="nova")
    p.add_argument("--texto", required=True)
    p.add_argument("--estilo", default="")
    a = ap.parse_args()
    if a.orden in ("voces", "borrar"):
        return {"voces": orden_voces, "borrar": orden_borrar}[a.orden](a)
    relanzar_si_hace_falta()
    return {"estado": orden_estado, "registrar": orden_registrar, "decir": orden_decir, "lote": orden_lote,
            "hablar": orden_hablar, "servidor": orden_servidor}[a.orden](a)


if __name__ == "__main__":
    if sys.stdout is None or sys.stderr is None:  # pythonw (servidor sin ventana): sin consola, las librerias se caen al avisar
        BASE.mkdir(parents=True, exist_ok=True)
        _log = open(BASE / "servidor.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or _log
        sys.stderr = sys.stderr or _log
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
