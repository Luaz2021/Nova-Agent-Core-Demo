r"""
NOVA SEGURIDAD · arnes de auditoria barato en tokens (25/11/2026, Claude, a pedido del usuario). Sin Qwen.

Primera opinion GRATIS (0 tokens): escaneres en local -> candidatos con archivo:linea y el trozo de codigo.
Despues el modelo solo VERIFICA esos candidatos (no lee el proyecto entero):

  1. Escaneres: nova_auditoria.py (siempre) + Semgrep CE, gitleaks y OSV-Scanner SI estan instalados (si no, se dice
     en el informe: lo no revisado no cuenta como limpio).
  2. PAQUETE.md compacto: candidatos por gravedad con +-3 lineas de contexto.
  3. Verificacion (Nova, en la MISMA conversacion; si es grande, Orchestrator): metodo de la skill
     security-audit-cloudflare: intentar DESMONTAR cada candidato medio/alto/critico (de donde entra el dato hasta
     donde hace dano). Sin prueba no cuenta. Resultado en VERIFICACION.md (confirmado / descartado / falta validar).
  4. Critico de OTRA familia SOLO para critico/alto o desacuerdo: consulta de ventana con Claude Sonnet 5.5 (bolsa
     aparte de la de Gemini): herramientas\consultas\nova_consulta.py --nivel opus (o Sonnet si el usuario lo elige).

Uso:  <PYTHON> nova_seguridad.py <carpeta del proyecto> [--max 40]
Salida: antigravity\documentos_generados\seguridad\<proyecto>_<fecha>\ (NUNCA escribe dentro del proyecto).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

NOVA = Path.home() / ".gemini" / "antigravity"
AUDITORIA = NOVA / "scripts" / "nova_auditoria.py"
SALIDA_BASE = NOVA / "documentos_generados" / "seguridad"
SKILL_CF = NOVA / "almacen" / "skills" / "security-audit-cloudflare"
ORDEN = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2, "BAJA": 3, "INFO": 4}


def _auditoria_base(carpeta: Path) -> list[dict]:
    spec = importlib.util.spec_from_file_location("nova_auditoria", AUDITORIA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    hallazgos = mod.buscar_patrones(carpeta) + mod.revisar_estructura(carpeta)
    deps, notas = mod.dependencias(carpeta)
    out = [{"herramienta": "nova_auditoria", "sev": h["sev"], "que": h["que"], "donde": h["donde"],
            "prueba": h.get("prueba", ""), "arreglo": h.get("arreglo", "")} for h in hallazgos + deps]
    return out, list(notas)


def _correr(cmd: list[str], timeout: int = 600, cwd: Path | None = None, env: dict | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           cwd=cwd, env=env)
        return p.returncode, p.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


# 25/11: Semgrep en Windows se rompe con espacios en las rutas ("C:\Users\Ana Maria"): "rule validation failed" si la carpeta
# temporal tiene espacios e "Invalid scanning root" si la ruta del proyecto los tiene. Arreglo probado: TEMP sin espacios
# (C:\Users\Public\...) y escanear "." desde dentro del proyecto.
import tempfile  # noqa: E402

# v3.3: en macOS/Linux la carpeta temporal del sistema no lleva espacios
TMP_SEMGREP = Path("C:/Users/Public/nova_semgrep_tmp") if os.name == "nt" else Path(tempfile.gettempdir()) / "nova_semgrep_tmp"


# v3.3: como se instala cada escaner en cada sistema (Nova lo propone; lo instala solo con OK del usuario)
_WIN, _MAC = os.name == "nt", sys.platform == "darwin"
COMO_INSTALAR = {
    "semgrep": "uv tool install semgrep" if not _MAC else "brew install semgrep (o: uv tool install semgrep)",
    "gitleaks": ("winget install --id Gitleaks.Gitleaks -e" if _WIN else "brew install gitleaks" if _MAC
                 else "descarga el binario de github.com/gitleaks/gitleaks/releases o tu gestor de paquetes"),
    "osv-scanner": ("winget install --id Google.OSVScanner -e" if _WIN else "brew install osv-scanner" if _MAC
                    else "descarga el binario de github.com/google/osv-scanner/releases o tu gestor de paquetes"),
}


def _exe(nombre: str) -> str | None:
    exe = shutil.which(nombre)
    if not exe:  # winget/uv anaden el PATH al usuario: si el proceso viene de antes, buscar en los sitios tipicos
        for d in (Path.home() / ".local" / "bin", Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links",
                  Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path.home() / "go" / "bin"):  # v3.3: Mac/Linux
            for ext in (".exe", ".cmd", ""):
                if (d / f"{nombre}{ext}").exists():
                    return str(d / f"{nombre}{ext}")
        paquetes = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
        hallado = next(iter(sorted(paquetes.glob(f"*/{nombre}.exe"))), None) if paquetes.is_dir() else None
        if hallado:
            return str(hallado)
    return exe


def _semgrep(carpeta: Path) -> tuple[list[dict], str]:
    exe = _exe("semgrep")
    if not exe:
        return [], "Semgrep CE no instalado (analisis de codigo multi-lenguaje). Instalar (con OK del usuario): " + COMO_INSTALAR["semgrep"]
    import os

    TMP_SEMGREP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(TMP_SEMGREP), TMP=str(TMP_SEMGREP), PYTHONIOENCODING="utf-8")
    rc, out = _correr([exe, "scan", "--config", "p/default", "--json", "--quiet", "--metrics", "off", "."],
                      cwd=carpeta, env=env)
    try:
        datos = json.loads(out)
    except ValueError:
        return [], f"Semgrep fallo (codigo {rc})."
    sev = {"ERROR": "ALTA", "WARNING": "MEDIA", "INFO": "BAJA"}
    return [{"herramienta": "semgrep", "sev": sev.get(r["extra"].get("severity", ""), "MEDIA"),
             "que": r["extra"].get("message", r.get("check_id", ""))[:160],
             "donde": f"{r['path']}:{r['start']['line']}", "prueba": (r["extra"].get("lines") or "")[:200],
             "arreglo": ""} for r in datos.get("results", [])], ""


def _gitleaks(carpeta: Path, tmp: Path) -> tuple[list[dict], str]:
    exe = _exe("gitleaks")
    if not exe:
        return [], "gitleaks no instalado (claves y contrasenas filtradas). Instalar (con OK del usuario): " + COMO_INSTALAR["gitleaks"]
    rep = tmp / "gitleaks.json"
    _correr([exe, "detect", "--no-git", "--redact", "-s", str(carpeta), "-r", str(rep), "-f", "json"])
    try:
        datos = json.loads(rep.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], ""
    return [{"herramienta": "gitleaks", "sev": "ALTA", "que": f"Secreto expuesto ({d.get('RuleID')})",
             "donde": f"{d.get('File')}:{d.get('StartLine')}", "prueba": "[tapado]", "arreglo":
             "Quitar del codigo, rotar la clave y cargarla desde el cofre/variables de entorno."} for d in datos], ""


def _osv(carpeta: Path) -> tuple[list[dict], str]:
    exe = _exe("osv-scanner")
    if not exe:
        return [], "OSV-Scanner no instalado (dependencias con vulnerabilidades conocidas; necesita internet). Instalar (con OK del usuario): " + COMO_INSTALAR["osv-scanner"]
    rc, out = _correr([exe, "scan", "source", "-r", "--format", "json", str(carpeta)])
    try:
        datos = json.loads(out)
    except ValueError:
        return [], f"OSV-Scanner fallo o sin dependencias que revisar (codigo {rc})."
    res = []
    for r in datos.get("results", []):
        for pk in r.get("packages", []):
            for v in pk.get("vulnerabilities", []):
                res.append({"herramienta": "osv-scanner", "sev": "ALTA",
                            "que": f"{pk['package'].get('name')} {pk['package'].get('version')}: {v.get('id')} "
                                   f"{(v.get('summary') or '')[:100]}",
                            "donde": r.get("source", {}).get("path", ""), "prueba": v.get("id", ""),
                            "arreglo": "Actualizar la dependencia a una version corregida."})
    return res, ""


def _contexto(donde: str, carpeta: Path, radio: int = 3) -> str:
    ruta, _, linea = donde.rpartition(":")
    try:
        n = int(linea)
        p = Path(ruta) if Path(ruta).is_absolute() else carpeta / ruta
        lineas = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except (ValueError, OSError):
        return ""
    ini, fin = max(0, n - 1 - radio), min(len(lineas), n + radio)
    return "\n".join(f"{i + 1:>5}{'>' if i + 1 == n else ' '} {lineas[i][:160]}" for i in range(ini, fin))


def main() -> int:
    ap = argparse.ArgumentParser(description="Arnes de auditoria de seguridad de Nova (0 tokens hasta verificar)")
    ap.add_argument("carpeta")
    ap.add_argument("--max", type=int, default=40, help="maximo de candidatos que se pasan al modelo")
    a = ap.parse_args()
    carpeta = Path(a.carpeta).resolve()
    if not carpeta.is_dir():
        print(f"[SEGURIDAD] No existe {carpeta}")
        return 2
    destino = SALIDA_BASE / f"{carpeta.name}_{datetime.now():%Y%m%d_%H%M}"
    destino.mkdir(parents=True, exist_ok=True)

    candidatos, no_revisado = _auditoria_base(carpeta)
    for fn in (_semgrep, _osv):
        r, nota = fn(carpeta)
        candidatos += r
        if nota:
            no_revisado.append(nota)
    r, nota = _gitleaks(carpeta, destino)
    candidatos += r
    if nota:
        no_revisado.append(nota)

    # sin duplicados (mismo sitio y misma idea de dos escaneres) y por gravedad
    vistos, unicos = set(), []
    for c in sorted(candidatos, key=lambda x: ORDEN.get(x["sev"], 5)):
        clave = (c["que"][:60].lower(),) if c["herramienta"] == "osv-scanner" else (c["donde"], c["que"][:40].lower())
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(c)
    for i, c in enumerate(unicos, 1):
        c["id"] = f"C{i:03d}"
    (destino / "candidatos.json").write_text(json.dumps(unicos, ensure_ascii=False, indent=1), encoding="utf-8")

    a_verificar = [c for c in unicos if ORDEN.get(c["sev"], 5) <= 2][: a.max]
    resto = len(unicos) - len(a_verificar)
    L = [f"# Paquete de auditoria · {carpeta.name} · {datetime.now():%Y-%m-%d %H:%M}", "",
         f"Candidatos: {len(unicos)} · a verificar (media o mas): {len(a_verificar)}"
         + (f" · bajos/sobrantes sin verificar: {resto}" if resto else ""), "",
         "## Como verificar (Nova)",
         f"- Metodo: `{SKILL_CF}\\SKILL.md` (modo orientacion) y su guia del tipo de proyecto.",
         "- Por cada candidato: lee SOLO ese trozo (y lo que necesites seguir), intenta DESMONTARLO: de donde entra el "
         "dato, por donde pasa, donde hace dano. Si no hay camino real, es DESCARTADO. Sin prueba no cuenta.",
         "- Escribe `VERIFICACION.md` en esta carpeta: | id | confirmado/descartado/falta validar | prueba (archivo:linea "
         "-> archivo:linea) | gravedad final | arreglo minimo |.",
         "- CRITICO o ALTO confirmado, o dudas: segunda opinion de OTRA familia (consulta de ventana a Claude, bolsa "
         "aparte). No pruebes nada contra servidores reales.", ""]
    if no_revisado:
        L += ["## Lo que NO se pudo revisar (no cuenta como limpio)", *[f"- {n}" for n in no_revisado], ""]
    L += ["## Candidatos a verificar", ""]
    for c in a_verificar:
        L += [f"### {c['id']} · {c['sev']} · {c['que']}", f"`{c['donde']}` ({c['herramienta']})"]
        ctx = _contexto(c["donde"], carpeta)
        if ctx:
            L += ["```", ctx, "```"]
        elif c.get("prueba"):
            L.append(f"Prueba: `{c['prueba'][:200]}`")
        if c.get("arreglo"):
            L.append(f"Arreglo sugerido: {c['arreglo']}")
        L.append("")
    (destino / "PAQUETE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[SEGURIDAD] {len(unicos)} candidatos ({len(a_verificar)} a verificar) · sin revisar: {len(no_revisado)} · "
          f"paquete: {destino / 'PAQUETE.md'}")
    return 0


if __name__ == "__main__":
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
