"""
Vigia Lint de Nova-Core (Watchdog en tiempo real a 0 tokens, MODO SOLO REVISION).

Observa las carpetas configuradas en `vigia_config.json`, ejecuta automaticamente
`orquestador.revisar(archivo, autofix=False)` al guardar (sin mutar el archivo
mientras `edit_file` trabaja) y actualiza `ultimo_lint.md` con la lista acumulada
de archivos con avisos pendientes (un archivo solo sale cuando queda limpio).

Uso:
    python vigia_lint.py [directorio1 directorio2 ...]
"""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import orquestador as o

CONFIG_VIGIA = Path(__file__).resolve().parent / "vigia_config.json"
DEBOUNCE_SEG = 0.4


def cargar_config_vigia() -> tuple[list[Path], set[str]]:
    """Lee las carpetas y la lista de exclusion desde vigia_config.json."""
    excluidos = {d.lower() for d in o.IGNORAR_DIRS}
    candidatas: list[Path] = []
    if CONFIG_VIGIA.exists():
        try:
            datos = json.loads(CONFIG_VIGIA.read_text(encoding="utf-8"))
            candidatas = [Path(p) for p in datos.get("carpetas", [])]
            excluidos |= {d.lower() for d in datos.get("excluir_directorios", [])}
        except ValueError:
            candidatas = [Path.cwd()]
    if len(sys.argv) > 1:
        candidatas = [Path(p) for p in sys.argv[1:]]
    elif not candidatas:
        candidatas = [Path.cwd()]
    carpetas = [c.resolve() for c in candidatas if c.exists() and c.is_dir()]
    return carpetas, excluidos


def os_fsdecode(ruta: bytes | str) -> str:
    return ruta.decode("utf-8", errors="replace") if isinstance(ruta, bytes) else ruta


class ManejadorVigia(FileSystemEventHandler):
    """Ejecuta orquestador.revisar(..., autofix=False) sin modificar el archivo en disco."""

    def __init__(self, excluidos: set[str]) -> None:
        super().__init__()
        self._excluidos = excluidos
        self._ultimo_evento: dict[str, float] = {}

    def _procesar(self, ruta_str: str) -> None:
        ruta = Path(ruta_str).resolve()
        if not ruta.is_file() or ruta.suffix.lower() not in o.EXT_SOPORTADAS:
            return
        partes_lower = {p.lower() for p in ruta.parts}
        if partes_lower & self._excluidos or ruta.name in {
            "ultimo_lint.md",
            ".estado_lint.json",
            "vigia_config.json",
        }:
            return
        try:
            if time.time() - ruta.stat().st_mtime > 10.0:
                return
        except OSError:
            return
        clave = str(ruta)
        ahora = time.monotonic()
        if ahora - self._ultimo_evento.get(clave, 0.0) < DEBOUNCE_SEG:
            return
        self._ultimo_evento[clave] = ahora
        o.revisar(clave, autofix=False)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._procesar(os_fsdecode(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._procesar(os_fsdecode(event.src_path))


def main() -> None:
    lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_sock.bind(("127.0.0.1", 59841))
    except OSError:
        sys.exit(0)

    carpetas, excluidos = cargar_config_vigia()
    if not carpetas:
        sys.exit(0)
    manejador = ManejadorVigia(excluidos)
    observador = Observer()
    for carpeta in carpetas:
        observador.schedule(manejador, str(carpeta), recursive=True)
    observador.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observador.stop()
    observador.join()


if __name__ == "__main__":
    main()
