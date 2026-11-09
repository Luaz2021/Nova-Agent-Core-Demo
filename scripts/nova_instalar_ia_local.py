"""
Nova - Instalador de la IA local (Capa 0: Ollama + Qwen + InternVL) para Windows, macOS y Linux
==============================================================================================
Lo usan los instaladores de Nova y tambien Nova cuando el usuario dice "Nova, instala la IA local".

    python nova_instalar_ia_local.py --estado                 (que hay instalado y que toca a este equipo)
    python nova_instalar_ia_local.py [--perfil OPTIMO_GPU|GAMA_MEDIA] [--si]
        1. Si no hay Ollama, lo instala (pregunta antes salvo --si):
             Windows: winget install Ollama.Ollama   (si no hay winget: abre https://ollama.com/download)
             macOS:   brew install ollama            (si no hay Homebrew: abre https://ollama.com/download)
             Linux:   instalador oficial https://ollama.com/install.sh (pide la contrasena de sudo)
        2. Arranca el servicio y descarga los 2 modelos del perfil (coder + vision) de scripts/nova_modelos.json.
        3. Apunta lo instalado en memory/perfil_usuario.json (ia_local) para que todos los scripts usen esos modelos.
    python nova_instalar_ia_local.py --limpiar-obsoletos       (borra modelos viejos de Nova, p. ej. qwen2.5-coder)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ANTIGRAVITY = Path.home() / ".gemini" / "antigravity"
PERFIL = ANTIGRAVITY / "memory" / "perfil_usuario.json"
CATALOGO = next((p for p in (AQUI / "nova_modelos.json", ANTIGRAVITY / "scripts" / "nova_modelos.json") if p.exists()),
                AQUI / "nova_modelos.json")
URL_OLLAMA = "http://127.0.0.1:11434/"


def leer_json(p: Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def preguntar(texto: str, defecto: bool, auto: bool) -> bool:
    if auto:
        return True
    if not sys.stdin or not sys.stdin.isatty():
        return defecto
    r = input(f"{texto} (s/n) [{'s' if defecto else 'n'}]: ").strip().lower()
    return defecto if not r else r.startswith("s") or r.startswith("y")


def ruta_ollama() -> str | None:
    cmd = shutil.which("ollama")
    if cmd:
        return cmd
    for c in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
              "/Applications/Ollama.app/Contents/Resources/ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"):
        if os.path.exists(c):
            return c
    return None


def ollama_vivo() -> bool:
    try:
        with urllib.request.urlopen(URL_OLLAMA, timeout=2) as r:
            return b"Ollama is running" in r.read()
    except OSError:
        return False


def arrancar_ollama(cmd: str) -> bool:
    if ollama_vivo():
        return True
    try:
        subprocess.Popen([cmd, "serve"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x08000000 if sys.platform == "win32" else 0)
    except OSError:
        return False
    for _ in range(30):
        time.sleep(0.5)
        if ollama_vivo():
            return True
    return False


def instalar_ollama(auto: bool) -> str | None:
    """Instala Ollama con el metodo oficial de cada sistema. Devuelve la ruta o None."""
    print("[IA LOCAL] Ollama no esta instalado (es el motor que corre los modelos en tu equipo, gratis y sin nube).")
    if not preguntar("Quieres que lo instale ahora?", True, auto):
        print("[IA LOCAL] Sin Ollama. Puedes instalarlo cuando quieras desde https://ollama.com/download")
        return None
    try:
        if sys.platform == "win32":
            if shutil.which("winget"):
                subprocess.run(["winget", "install", "-e", "--id", "Ollama.Ollama",
                                "--accept-source-agreements", "--accept-package-agreements"], check=False)
            else:
                print("[IA LOCAL] No hay winget: abro la descarga oficial. Instala OllamaSetup.exe y vuelve a lanzarme.")
                webbrowser.open("https://ollama.com/download/windows")
        elif sys.platform == "darwin":
            if shutil.which("brew"):
                subprocess.run(["brew", "install", "ollama"], check=False)
            else:
                print("[IA LOCAL] No hay Homebrew: abro la descarga oficial. Arrastra Ollama a Aplicaciones, abrelo y vuelve a lanzarme.")
                webbrowser.open("https://ollama.com/download/mac")
        else:
            if not shutil.which("curl"):
                print("[IA LOCAL] Falta curl. Instala curl o sigue https://ollama.com/download/linux")
                return None
            print("[IA LOCAL] Lanzo el instalador oficial de Ollama (te pedira tu contrasena de sudo)...")
            subprocess.run(["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], check=False)
    except OSError as e:
        print(f"[IA LOCAL] No se pudo lanzar el instalador: {e}")
    return ruta_ollama()


def descargar(cmd: str, modelo: str) -> bool:
    print(f"[IA LOCAL] Descargando {modelo} (puede tardar; se puede cortar y reanudar)...")
    return subprocess.run([cmd, "pull", modelo], check=False).returncode == 0


def modelos_instalados(cmd: str) -> list[str]:
    try:
        out = subprocess.run([cmd, "list"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [l.split()[0] for l in out.splitlines()[1:] if l.strip()]


def guardar_perfil(perfil_hw: str, coder: str, vl: str, instalada: bool) -> None:
    datos = leer_json(PERFIL)
    ia = datos.get("ia_local") if isinstance(datos.get("ia_local"), dict) else {}
    ia.update({"instalada": instalada, "modelo": coder if instalada else "ninguno", "modelo_vl": vl if instalada else "ninguno",
               "perfil": perfil_hw, "regla_activacion": ia.get("regla_activacion", "solo_tareas_masivas_mayor_1500_tokens")})
    datos["ia_local"] = ia
    try:
        PERFIL.parent.mkdir(parents=True, exist_ok=True)
        PERFIL.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        print(f"[IA LOCAL] No pude guardar el perfil: {e}")


def perfil_por_defecto() -> str:
    tier = str((leer_json(PERFIL).get("hardware") or {}).get("tier", ""))
    return tier if tier in ("OPTIMO_GPU", "GAMA_MEDIA") else "OPTIMO_GPU"


def main() -> int:
    ap = argparse.ArgumentParser(description="Instala Ollama y los modelos locales de Nova")
    ap.add_argument("--perfil", choices=["OPTIMO_GPU", "GAMA_MEDIA"], help="Por defecto, el del escaner del instalador")
    ap.add_argument("--si", action="store_true", help="No preguntar (acepta instalar Ollama y descargar)")
    ap.add_argument("--estado", action="store_true")
    ap.add_argument("--limpiar-obsoletos", action="store_true")
    ap.add_argument("--solo-ollama", action="store_true", help="Instala/arranca Ollama sin descargar modelos")
    args = ap.parse_args()

    catalogo = leer_json(CATALOGO)
    perfil_hw = args.perfil or perfil_por_defecto()
    elegido = (catalogo.get("perfiles") or {}).get(perfil_hw) or {}
    coder = elegido.get("coder") or catalogo.get("coder") or "qwen3.5:9b"
    vl = elegido.get("vl") or catalogo.get("vl") or "blaifa/InternVL3_5:8b"
    cmd = ruta_ollama()

    if args.estado:
        print(json.dumps({"sistema": sys.platform, "ollama": cmd or "no instalado", "servicio_activo": ollama_vivo(),
                          "perfil": perfil_hw, "modelos_que_tocan": [coder, vl],
                          "instalados": modelos_instalados(cmd) if cmd and ollama_vivo() else [],
                          "perfil_usuario": leer_json(PERFIL).get("ia_local")}, indent=2, ensure_ascii=False))
        return 0

    if not cmd:
        cmd = instalar_ollama(args.si)
        if not cmd:
            guardar_perfil(perfil_hw, coder, vl, False)
            return 1
    if not arrancar_ollama(cmd):
        print("[IA LOCAL] Ollama esta instalado pero no arranca. Abrelo una vez a mano (o reinicia) y repite.")
        return 1
    print(f"[IA LOCAL] Ollama activo ({cmd}).")

    if args.limpiar_obsoletos:
        instalados = set(modelos_instalados(cmd))
        for viejo in catalogo.get("modelos_obsoletos", []):
            if viejo in instalados and preguntar(f"Borrar el modelo viejo {viejo}?", True, args.si):
                subprocess.run([cmd, "rm", viejo], check=False)
        return 0
    if args.solo_ollama:
        return 0

    peso = elegido.get("descarga_gb")
    print(f"[IA LOCAL] Perfil {perfil_hw}: {coder} (codigo y textos) + {vl} (vision)" + (f", ~{peso} GB." if peso else "."))
    if not preguntar("Descargo los dos modelos ahora?", True, args.si):
        guardar_perfil(perfil_hw, coder, vl, False)
        return 0
    instalados = set(modelos_instalados(cmd))
    ok = all(m in instalados or descargar(cmd, m) for m in (coder, vl))
    guardar_perfil(perfil_hw, coder, vl, ok)
    print("[IA LOCAL] Listo: Nova usara estos modelos en local (0 tokens de nube)." if ok else
          "[IA LOCAL] Alguna descarga fallo. Repite el comando: Ollama reanuda donde lo dejo.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
