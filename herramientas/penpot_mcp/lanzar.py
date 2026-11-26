"""
NOVA - lanzador del MCP "penpot" (Windows, macOS y Linux). v3.3, con Claude.
Creado por Saul Alexander Martinez Rivas (@Luaz2021).

Lo ejecuta Antigravity al encender el MCP (entrada que crea scripts/nova_mcp.py: "activar penpot"):
  1) asegura el servidor: si nada escucha en el puerto 4401, instala @penpot/mcp (version fija) en ~/nova_penpot_mcp
     (cada equipo el suyo; la 1a vez tarda 1-2 min), da a pnpm 12 los permisos de esbuild y sharp y lo arranca oculto
     (MCP 4401, plugin 4400: Penpot -> Plugins -> http://localhost:4400/manifest.json).
  2) conecta Antigravity por stdio con mcp-remote.
stdout = SOLO JSON-RPC (lo de mcp-remote): todo lo demas va a ~/nova_penpot_mcp/servidor.log.
Lo apaga nova_mcp.py ("apagar penpot" y al cerrar Antigravity). Necesita Node.js (npm/npx).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

VERSION = "2.19.1"  # la web de Penpot va por 2.19.x (2.15.4 daba "Version mismatch")
REMOTO = "mcp-remote@0.16.7"
BASE = Path.home() / "nova_penpot_mcp"  # no LOCALAPPDATA: las apps MSIX de Windows lo redirigen y pnpm se pierde
PK = BASE / "node_modules" / "@penpot" / "mcp"
LOG = BASE / "servidor.log"
CANDADO = BASE / ".candado"
WIN = os.name == "nt"
SIN_VENTANA = 0x08000000 if WIN else 0


def log(texto: str) -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {texto}\n")


def escucha(puerto: int = 4401) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def programa(nombre: str) -> str | None:
    return shutil.which(nombre + (".cmd" if WIN else "")) or shutil.which(nombre)


def coger_candado(espera_s: int = 360) -> bool:
    """Si Antigravity lanza el MCP dos veces a la vez, solo uno instala/arranca."""
    fin = time.time() + espera_s
    while time.time() < fin:
        try:
            fd = os.open(CANDADO, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:  # candado de un lanzador que murio hace mas de 10 min
                if time.time() - CANDADO.stat().st_mtime > 600:
                    CANDADO.unlink()
                    continue
            except OSError:
                pass
            if escucha():
                return False
            time.sleep(2)
    return False


def permisos_pnpm() -> None:
    """pnpm 12 bloquea esbuild/sharp (ERR_PNPM_IGNORED_BUILDS) hasta que se les da permiso en pnpm-workspace.yaml."""
    yaml = PK / "pnpm-workspace.yaml"
    if not yaml.exists():
        return
    t = yaml.read_text(encoding="utf-8")
    t2 = re.sub(r"(esbuild|sharp):\s*set this to true or false", r"\1: true", t)
    if not re.search(r"(?m)^allowBuilds:", t2):
        t2 = "allowBuilds:\n  esbuild: true\n  sharp: true\n\n" + t2
    else:
        for dep in ("esbuild", "sharp"):
            if not re.search(rf"(?m)^\s+{dep}:", t2):
                t2 = re.sub(r"(?m)^allowBuilds:\s*$", f"allowBuilds:\n  {dep}: true", t2)
    if t2 != t:
        yaml.write_text(t2, encoding="utf-8")
        log("permisos pnpm: esbuild y sharp = true")


def asegurar_servidor(espera_max: int = 240) -> bool:
    if escucha():
        return True
    BASE.mkdir(parents=True, exist_ok=True)
    tengo = coger_candado()
    try:
        if escucha():
            return True
        npm, node = programa("npm"), shutil.which("node")
        if not npm or not node:
            log("FALLO: falta Node.js (npm/node). Instalalo desde nodejs.org y reabre Antigravity")
            return False
        try:
            ver = json.loads((PK / "package.json").read_text(encoding="utf-8")).get("version")
        except (OSError, ValueError):
            ver = None
        if ver != VERSION:
            log(f"instalando @penpot/mcp@{VERSION} (antes: {ver})")
            with LOG.open("a", encoding="utf-8") as f:
                subprocess.run([npm, "install", "--prefix", str(BASE), f"@penpot/mcp@{VERSION}", "--no-audit",
                                "--no-fund"], stdout=f, stderr=f, creationflags=SIN_VENTANA)
        permisos_pnpm()
        arranque = PK / "bin" / "mcp-local.js"
        if not arranque.exists():
            log("FALLO: no se instalo @penpot/mcp (mira arriba el error de npm)")
            return False
        log("arrancando servidor")
        f = LOG.open("a", encoding="utf-8")
        extra = ({"creationflags": SIN_VENTANA | 0x00000008 | 0x00000200} if WIN  # oculto y desligado
                 else {"start_new_session": True})
        subprocess.Popen([node, str(arranque)], cwd=PK, stdin=subprocess.DEVNULL, stdout=f, stderr=f, **extra)
        t0 = time.time()
        while time.time() - t0 < espera_max:
            if escucha():
                return True
            time.sleep(2)
        log(f"FALLO: el servidor no abrio el puerto 4401 en {espera_max} s")
        return False
    finally:
        if tengo:
            try:
                CANDADO.unlink()
            except OSError:
                pass


def main() -> int:
    try:
        asegurar_servidor()
    except Exception as e:  # nunca escribir en stdout: romperia el JSON-RPC
        log(f"FALLO asegurando el servidor: {e}")
    npx = programa("npx")
    if not npx:
        log("FALLO: falta npx (Node.js)")
        return 1
    args = [npx, "-y", REMOTO, "http://localhost:4401/mcp", "--allow-http"]
    if WIN:
        return subprocess.call(args)
    os.execv(npx, args)  # macOS/Linux: mcp-remote ocupa este proceso (stdio directo con Antigravity)
    return 0


if __name__ == "__main__":
    sys.exit(main())
