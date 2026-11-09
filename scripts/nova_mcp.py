r"""
NOVA · INTERRUPTOR DE MCP (09/11/2026, Claude, a pedido de el autor)
=================================================================
Los MCP cuestan tokens en CADA mensaje aunque no se usen (sus herramientas viajan siempre):
  playwright ~5.100 · postgres ~5.000 · sequential-thinking ~600 (este queda apagado siempre).
Por eso van APAGADOS y se encienden solo cuando el autor pide algo que los necesita:
  - nova_core\nova_hook_turno.py (PreInvocation) detecta el pedido y llama a "activar".
  - session_guard.ps1 llama a "apagar" al cerrarse Antigravity (vuelven a estar apagados la proxima vez).

(09/11 tarde: ver nota en INTERRUPTORES: con Antigravity 2.29 ya no cuestan tokens; Playwright va fijo encendido.)

Uso:
  python nova_mcp.py estado
  python nova_mcp.py activar postgres
  python nova_mcp.py apagar [postgres]

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
# encendido ~19,1k vs apagado ~19,0k de contexto. Playwright queda FIJO encendido (decision de el autor; sin espera de 8 s).
# Solo postgres sigue con interruptor (no tiene conexion configurada).
INTERRUPTORES = ("postgres",)  # los que se pueden encender/apagar; el resto no se toca
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


def estado() -> dict[str, bool]:
    return {k: not v.get("disabled", False) for k, v in leer().get("mcpServers", {}).items()}


def cambiar(nombres: list[str], encender: bool) -> list[str]:
    cfg = leer()
    servidores = cfg.get("mcpServers", {})
    cambiados = []
    for n in nombres:
        if n in servidores and n in INTERRUPTORES and bool(servidores[n].get("disabled", False)) == encender:
            servidores[n]["disabled"] = not encender
            cambiados.append(n)
    if cambiados:
        guardar(cfg)
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
                             creationflags=0x08000000).stdout
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
        return "Antigravity cerrado: vale al abrirlo"
    if _llamar("RefreshMcpServers", ls) is None:
        return "no se pudo recargar en caliente: vale al reabrir Antigravity"
    return "recargado en caliente (RefreshMcpServers ok)"


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
    cambiados = cambiar(nombres, encender=(orden == "activar"))
    nota = recargar() if cambiados else "ya estaba asi"
    log(f"{orden} {nombres} -> cambiados={cambiados} · {nota}")
    print(f"{orden}: {', '.join(nombres)} · {nota}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
