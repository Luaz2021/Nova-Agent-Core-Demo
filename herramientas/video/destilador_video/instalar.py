"""
NOVA - entorno del DESTILADOR DE VIDEO (Windows, macOS y Linux). v3.3, con Claude.
Creado por Saul Alexander Martinez Rivas (@Luaz2021).

Crea ~/nova_destilador/env (Python 3.12 con uv, fuera de la carpeta de Nova) con faster-whisper, FFmpeg portable,
numpy, yt-dlp y psutil. Con GPU NVIDIA (Windows/Linux) anade las librerias CUDA de pip (sin instalar CUDA).
En Mac va por CPU (Apple Silicon es rapido igualmente para clases cortas).

Uso (una vez por equipo, con OK del usuario; ~1 GB sin GPU, ~3 GB con GPU NVIDIA):
  <PYTHON> "<NOVA_HOME>/antigravity/herramientas/video/destilador_video/instalar.py"
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path.home() / "nova_destilador"
ENV = BASE / "env"
PY = ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PAQUETES = ["faster-whisper==1.2.1", "imageio-ffmpeg", "numpy<3", "yt-dlp", "psutil"]
CUDA = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*"]


def uv() -> str | None:
    cand = [shutil.which("uv"), str(Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")),
            str(Path.home() / ".cargo" / "bin" / "uv")]
    return next((c for c in cand if c and Path(c).exists()), None)


def main() -> int:
    u = uv()
    if not u:
        print("[destilador] Falta uv. Ejecuta el Doctor de Nova (nova_doctor.py --reparar) o instala uv "
              "(https://docs.astral.sh/uv/) y repite.")
        return 1
    BASE.mkdir(parents=True, exist_ok=True)
    if not PY.exists():
        subprocess.run([u, "venv", str(ENV), "--python", "3.12", "-q"], check=True)
    paquetes = list(PAQUETES)
    nvidia = shutil.which("nvidia-smi") and platform.system() in ("Windows", "Linux") \
        and platform.machine().lower() in ("amd64", "x86_64")
    if nvidia:
        paquetes += CUDA
    print(f"[destilador] Instalando {len(paquetes)} paquetes ({'con GPU NVIDIA' if nvidia else 'CPU'})...")
    subprocess.run([u, "pip", "install", "--python", str(PY), "-q", *paquetes], check=True)
    r = subprocess.run([str(PY), "-c", "import faster_whisper, imageio_ffmpeg, numpy, psutil; "
                        "print('destilador: entorno OK', faster_whisper.__version__)"], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-400:])
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        print(f"[destilador] FALLO: {e}")
        sys.exit(1)
