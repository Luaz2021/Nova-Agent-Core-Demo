r"""
NOVA · INTERRUPTOR DE MCP (09/11/2026, Claude, a pedido del usuario)
=================================================================
Los MCP cuestan tokens en CADA mensaje aunque no se usen (sus herramientas viajan siempre):
  playwright ~5.100 · postgres ~5.000 · sequential-thinking ~600 (este queda apagado siempre).
Por eso van APAGADOS y se encienden solo cuando el usuario pide algo que los necesita:
  - nova_core\nova_hook_turno.py (PreInvocation) detecta el pedido y llama a "activar".
  - session_guard.ps1 llama a "apagar" al cerrarse Antigravity (vuelven a estar apagados la proxima vez).

(09/11 tarde: ver nota en INTERRUPTORES: con Antigravity 2.29 ya no cuestan tokens; Playwright va fijo encendido.)

Uso:
  python nova_mcp.py estado
  python nova_mcp.py activar postgres
  python nova_mcp.py apagar [postgres]

Navegar en el Brave del usuario (con sus sesiones) NO es Playwright: eso es el puente de Brave (127.0.0.1:5005).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".gemini" / "config" / "mcp_config.json"
# 09/11 tarde: Antigravity 2.29 carga las herramientas MCP bajo demanda (antigravity\mcp\<server>\*.json + call_mcp_tool):
# encendido ~19,1k vs apagado ~19,0k de contexto. Playwright queda FIJO encendido (decision del usuario; sin espera de 8 s).
# Solo postgres sigue con interruptor (no tiene conexion configurada).
INTERRUPTORES = ("postgres", "codebase", "penpot")  # los que se pueden encender/apagar; el resto no se toca
# "penpot" = @penpot/mcp (herramientas/penpot_mcp/lanzar.py lo instala/arranca en ~/nova_penpot_mcp; 3 sistemas).
# Al apagarlo se para tambien su servidor (node, ~200 MB de RAM).
# 22/11 (Claude, N3): "codebase" = codebase-memory-mcp (radiografia de proyectos de codigo). Viaja por Drive en
# herramientas/codebase_memory/bin/ (lo instala instalar.py en cada equipo; indices en ../.cache). Si al equipo aun no le
# ha llegado (o Defender lo aparto), no se enciende; instalar.py lo instala desde GitHub con sumas verificadas.
LANZADOR_PENPOT = Path.home() / ".gemini" / "antigravity" / "herramientas" / "penpot_mcp" / "lanzar.py"
_CBM = Path.home() / ".gemini" / "antigravity" / "herramientas" / "codebase_memory"
EXE_CODEBASE = _CBM / "bin" / ("codebase-memory-mcp.exe" if os.name == "nt" else "codebase-memory-mcp")


def entrada_por_defecto(nombre: str) -> dict | None:
    """v3.3: si el usuario no tiene ese MCP en su mcp_config.json, se crea al encenderlo (3 sistemas)."""
    if nombre == "codebase" and EXE_CODEBASE.exists():
        return {"command": str(EXE_CODEBASE), "args": [], "env": {"CBM_CACHE_DIR": str(_CBM / ".cache")}}
    if nombre == "penpot" and LANZADOR_PENPOT.exists():  # necesita Node.js; lanzar.py instala y arranca el servidor
        return {"command": sys.executable, "args": [str(LANZADOR_PENPOT)]}
    return None
REGISTRO = Path.home() / ".gemini" / "antigravity" / "memory" / "registros" / "nova_mcp.log"


def log(texto: str) -> None:
    try:
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")
    except OSError:
        pass


def leer() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def guardar(cfg: dict) -> None:
    tmp = CONFIG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, CONFIG)


# 25/11 (Claude, laptop): Antigravity 2.35 ARRANCA los MCP aunque lleven "disabled": true (visto: codebase, penpot con
# su servidor + vite --watch, postgres y sequential-thinking arrancados al abrir). Apagado = SACARLO de mcpServers y
# guardarlo en "_nova_apagados" (mismo archivo, viaja igual; Antigravity ignora claves que no conoce). Encender = volver
# a meterlo. Cualquier servidor con "disabled": true que quede en mcpServers se mueve solo (normalizar).
APAGADOS = "_nova_apagados"


def normalizar(cfg: dict) -> list[str]:
    servidores = cfg.setdefault("mcpServers", {})
    apagados = cfg.setdefault(APAGADOS, {})
    movidos = [n for n, v in servidores.items() if isinstance(v, dict) and v.get("disabled")]
    for n in movidos:
        apagados[n] = servidores.pop(n)
    return movidos


def estado() -> dict[str, bool]:
    cfg = leer()
    est = {k: not v.get("disabled", False) for k, v in cfg.get("mcpServers", {}).items()}
    est.update({k: False for k in cfg.get(APAGADOS, {})})
    return est


def cambiar(nombres: list[str], encender: bool) -> list[str]:
    cfg = leer()
    movidos = normalizar(cfg)
    servidores, apagados = cfg["mcpServers"], cfg[APAGADOS]
    cambiados = []
    for n in nombres:
        if n not in INTERRUPTORES:
            continue
        if encender and n in apagados:
            entrada = apagados.pop(n)
            entrada["disabled"] = False
            servidores[n] = entrada
            cambiados.append(n)
        elif encender and n not in servidores and entrada_por_defecto(n):
            servidores[n] = entrada_por_defecto(n)
            cambiados.append(n)
        elif not encender and n in servidores:
            entrada = servidores.pop(n)
            entrada["disabled"] = True
            apagados[n] = entrada
            cambiados.append(n)
    if not apagados:
        cfg.pop(APAGADOS, None)
    if cambiados or movidos:
        guardar(cfg)
    if movidos:
        log(f"normalizar: {movidos} tenian disabled:true dentro de mcpServers -> movidos a {APAGADOS}")
    return cambiados


# ------------------------------------------------------------------ recarga en caliente (sin reiniciar Antigravity)
# 09/11 tarde (Claude): el language_server de Antigravity (solo 127.0.0.1) tiene
# exa.language_server_pb.LanguageServerService/RefreshMcpServers (Connect/JSON, cabecera x-codeium-csrf-token).
# El puerto (https_server_port 0 = al azar) y la clave salen de su linea de comandos. La clave NUNCA se imprime ni se guarda.
LS = "exa.language_server_pb.LanguageServerService"


def _language_server() -> tuple[str, list[int]] | None:
    try:  # psutil: 0,4 s (PowerShell + CIM: 5,5 s)
        import psutil
        for p in psutil.process_iter(["name"]):
            if p.info["name"] == "language_server.exe":
                c = p.cmdline()
                token = next((c[i + 1] for i, a in enumerate(c[:-1]) if a == "--csrf_token"), None)
                token = token or next((a.split("=", 1)[1] for a in c if a.startswith("--csrf_token=")), None)
                puertos = sorted({x.laddr.port for x in p.net_connections("tcp") if x.status == "LISTEN"})
                if token and puertos:
                    return token, puertos
    except Exception:
        pass
    import re
    import subprocess
    ps = ("$p = Get-CimInstance Win32_Process -Filter \"Name='language_server.exe'\" | Select-Object -First 1; "
          "if ($p) { $p.CommandLine; '#PUERTOS#'; (Get-NetTCPConnection -State Listen -OwningProcess $p.ProcessId "
          "-ErrorAction SilentlyContinue).LocalPort }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-c", ps], capture_output=True, text=True, timeout=15,
                             creationflags=0x08000000 if os.name == "nt" else 0).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    if "#PUERTOS#" not in out:
        return None
    cmd, puertos = out.split("#PUERTOS#", 1)
    m = re.search(r"--csrf_token[ =](\S+)", cmd)
    ps_ = sorted({int(x) for x in puertos.split() if x.isdigit()})
    return (m.group(1), ps_) if m and ps_ else None


def _llamar(metodo: str, ls: tuple[str, list[int]]) -> dict | None:
    import ssl
    token, puertos = ls
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # certificado propio de Antigravity, solo localhost
    for p in puertos:
        req = urllib.request.Request(f"https://127.0.0.1:{p}/{LS}/{metodo}", data=b"{}", method="POST", headers={
            "Content-Type": "application/json", "Connect-Protocol-Version": "1", "x-codeium-csrf-token": token})
        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                return json.loads(r.read() or b"{}")
        except Exception:
            continue
    return None


def recargar() -> str:
    """Pide a Antigravity que vuelva a leer mcp_config.json. Si no se puede, el cambio vale al reabrir Antigravity."""
    ls = _language_server()
    if not ls:
        # 25/11: desde 2.35 la clave va por stdin (--read_host_bridge_token_from_stdin): no hay recarga en caliente
        return "vale al abrir o reabrir Antigravity"
    if _llamar("RefreshMcpServers", ls) is None:
        return "no se pudo recargar en caliente: vale al reabrir Antigravity"
    return "recargado en caliente (RefreshMcpServers ok)"


def parar_penpot() -> int:
    """Para el servidor de Penpot (node de ~/nova_penpot_mcp y sus hijos). Devuelve cuantos procesos."""
    try:
        import psutil
    except ImportError:
        return 0
    n = 0
    for p in psutil.process_iter(["name"]):
        try:
            if "nova_penpot_mcp" in " ".join(p.cmdline()).lower():
                for h in p.children(recursive=True):
                    h.kill()
                    n += 1
                p.kill()
                n += 1
        except Exception:
            continue
    return n


# 25/11 (Claude): desde 2.35 encender un MCP = REABRIR Antigravity, y al cerrar session_guard llama "apagar" (todos):
# apagaba justo lo que Nova acababa de encender ("cierra y abre y repite el pedido" -> volvia apagado). Ahora "activar"
# apunta la hora (.gemini\nova_mcp_recien.json: raiz de .gemini, NO viaja, es de cada equipo) y el "apagar" del cierre
# (sin nombres) se SALTA lo encendido hace menos de RECIEN_MIN; ese salto se gasta (el siguiente cierre ya lo apaga).
# "apagar <nombre>" apaga siempre.
RECIEN = Path.home() / ".gemini" / "nova_mcp_recien.json"
RECIEN_MIN = 20


def _recien() -> dict[str, float]:
    try:
        return json.loads(RECIEN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar_recien(d: dict[str, float]) -> None:
    try:
        RECIEN.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a.lower() for a in sys.argv[1:]]
    orden = args[0] if args else "estado"
    nombres = [a for a in args[1:] if a in INTERRUPTORES] or (list(INTERRUPTORES) if orden == "apagar" else [])
    if orden == "estado":
        print(json.dumps(estado(), ensure_ascii=False))
        return 0
    if orden not in ("activar", "apagar") or not nombres:
        print(__doc__)
        return 2
    if orden == "activar" and "codebase" in nombres and not EXE_CODEBASE.exists():
        log("activar codebase -> NO: falta el programa en este equipo")
        print("activar: codebase · NO INSTALADO en este equipo: <PYTHON> herramientas/codebase_memory/instalar.py")
        return 0
    recien = _recien()
    respetados = []
    if orden == "activar":
        recien.update({n: time.time() for n in nombres})
        _guardar_recien(recien)
    elif len(args) == 1:  # "apagar" a secas = cierre de Antigravity
        respetados = [n for n in nombres if time.time() - recien.get(n, 0) < RECIEN_MIN * 60]
        nombres = [n for n in nombres if n not in respetados]
        _guardar_recien({})
    cambiados = cambiar(nombres, encender=(orden == "activar"))
    nota = recargar() if cambiados else "ya estaba asi"
    if respetados:
        nota += f" · se quedan ENCENDIDOS {respetados} (pedidos hace <{RECIEN_MIN} min: Nova pidio reabrir)"
    if orden == "apagar" and "penpot" in nombres:
        parados = parar_penpot()
        if parados:
            nota += f" · servidor de Penpot parado ({parados} procesos)"
    log(f"{orden} {nombres} -> cambiados={cambiados} · {nota}")
    print(f"{orden}: {', '.join(nombres)} · {nota}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
