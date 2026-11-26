"""
NOVA - instala codebase-memory-mcp (radiografia de proyectos) en ESTE equipo. Windows, macOS y Linux.
Creado por Saul Alexander Martinez Rivas (@Luaz2021) con Claude (v3.3).

Baja de GitHub la version fijada (v0.12.1, DeusData, licencia MIT), comprueba su SHA-256 contra las sumas publicadas
por el proyecto (copiadas aqui: si la descarga no coincide, NO se instala) y deja el programa en bin/.
Despues apaga el visor web y el vigilante de archivos (si no, queda un proceso vivo al cerrar Antigravity).

Uso:  <PYTHON> "<NOVA_HOME>/antigravity/herramientas/codebase_memory/instalar.py"
      (lo pide Nova la primera vez que dices "revisa el proyecto <ruta>"; ocupa ~50 MB de descarga)
"""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "v0.12.1"
BASE = f"https://github.com/DeusData/codebase-memory-mcp/releases/download/{VERSION}/"
# Sumas SHA-256 publicadas en checksums.txt de la release (comprobadas el 26/11/2026)
PAQUETES = {
    ("windows", "amd64"): ("codebase-memory-mcp-windows-amd64.zip",
                           "4e4e0f16b45233af5c757a1fcbe3c3b16e9056375b1fbe2ce020b6de75dedcc0"),
    ("windows", "arm64"): ("codebase-memory-mcp-windows-arm64.zip",
                           "934ab6bd67a76c6ebd9e110d87b7090ffd629919bedaeddabe5a19175038b063"),
    ("darwin", "amd64"): ("codebase-memory-mcp-darwin-amd64.tar.gz",
                          "ca6e64397a8ae80cec898a8205a6aa16750ac798acc05a0c3ed983837944a581"),
    ("darwin", "arm64"): ("codebase-memory-mcp-darwin-arm64.tar.gz",
                          "9bfcbe38414b47969a3e1d1c1999f5357409387c86fa3d24221b5458267660d2"),
    # Linux: la version "portable" (estatica) funciona en cualquier distribucion
    ("linux", "amd64"): ("codebase-memory-mcp-linux-amd64-portable.tar.gz",
                         "8c3d0341064301e78ecc84cf7348d4e2c6562a0f57448243ea560aaa34de36c1"),
    ("linux", "arm64"): ("codebase-memory-mcp-linux-arm64-portable.tar.gz",
                         "ed0f1f548cd79b121c401c2e9f7841c189a001af26d3768368088c24f6a53533"),
}
AQUI = Path(__file__).resolve().parent
BIN = AQUI / "bin"
CACHE = AQUI / ".cache"
NOMBRE_EXE = "codebase-memory-mcp" + (".exe" if os.name == "nt" else "")
EXE = BIN / NOMBRE_EXE
SIN_VENTANA = 0x08000000 if os.name == "nt" else 0


def plataforma() -> tuple[str, str]:
    so = {"Windows": "windows", "Darwin": "darwin", "Linux": "linux"}.get(platform.system(), "")
    maq = platform.machine().lower()
    arq = "arm64" if maq in ("arm64", "aarch64") else "amd64" if maq in ("x86_64", "amd64") else maq
    return so, arq


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def extraer_binario(paquete: Path, destino: Path) -> Path:
    """Saca SOLO el programa (y LICENSE) del paquete, sin confiar en las rutas de dentro (nada de ../)."""
    destino.mkdir(parents=True, exist_ok=True)
    encontrado = None
    if paquete.suffix == ".zip":
        with zipfile.ZipFile(paquete) as z:
            for info in z.infolist():
                nombre = Path(info.filename).name
                if nombre in (NOMBRE_EXE, "LICENSE") and not info.is_dir():
                    (destino / nombre).write_bytes(z.read(info))
                    encontrado = encontrado or (destino / NOMBRE_EXE if nombre == NOMBRE_EXE else None)
    else:
        with tarfile.open(paquete, "r:gz") as t:
            for m in t.getmembers():
                nombre = Path(m.name).name
                if m.isfile() and nombre in (NOMBRE_EXE, "LICENSE"):
                    f = t.extractfile(m)
                    if f:
                        (destino / nombre).write_bytes(f.read())
                        if nombre == NOMBRE_EXE:
                            encontrado = destino / NOMBRE_EXE
    if not encontrado or not encontrado.exists():
        raise RuntimeError("no esta el programa dentro del paquete (el antivirus lo pudo apartar)")
    return encontrado


def configurar() -> None:
    """Visor web y vigilante de archivos apagados (indices en .cache, uno por equipo)."""
    env = dict(os.environ, CBM_CACHE_DIR=str(CACHE))
    for clave in ("ui_enabled", "auto_watch", "watcher_enabled"):
        subprocess.run([str(EXE), "config", "set", clave, "false"], capture_output=True, env=env,
                       creationflags=SIN_VENTANA)


def main() -> int:
    so, arq = plataforma()
    if (so, arq) not in PAQUETES:
        print(f"[codebase] Tu sistema ({platform.system()} {platform.machine()}) no tiene version oficial. "
              "Nova sigue funcionando sin la radiografia.")
        return 1
    nombre, suma = PAQUETES[(so, arq)]
    if EXE.exists() and "--forzar" not in sys.argv:
        print(f"[codebase] Ya esta instalado: {EXE} (reinstalar: --forzar)")
        configurar()
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="nova_codebase_"))
    try:
        paquete = tmp / nombre
        print(f"[codebase] Bajando {nombre} ({VERSION})...")
        with urllib.request.urlopen(BASE + nombre, timeout=120) as r, paquete.open("wb") as f:
            shutil.copyfileobj(r, f)
        h = sha256(paquete)
        if h != suma:
            print(f"[codebase] FALLO: la suma SHA-256 NO coincide ({h}). No se instala.")
            return 1
        nuevo = extraer_binario(paquete, tmp / "x")
        BIN.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nuevo, EXE)
        if (tmp / "x" / "LICENSE").exists():
            shutil.copy2(tmp / "x" / "LICENSE", BIN / "LICENSE")
        if os.name != "nt":
            EXE.chmod(0o755)
            if so == "darwin":  # sin la marca de cuarentena (por si el sistema la puso)
                subprocess.run(["xattr", "-d", "com.apple.quarantine", str(EXE)], capture_output=True)
        configurar()
        v = subprocess.run([str(EXE), "--version"], capture_output=True, text=True,
                           creationflags=SIN_VENTANA).stdout.strip()
        print(f"[codebase] Instalado OK ({v or VERSION}) en {BIN} (suma verificada). "
              "Enciendelo con: nova_mcp.py activar codebase")
        return 0
    except Exception as e:
        print(f"[codebase] FALLO: {e}")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
