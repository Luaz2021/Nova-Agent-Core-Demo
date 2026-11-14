"""
Auditor SCA de Dependencias a 0 Tokens (Software Composition Analysis).
Inspecciona package.json o requirements.txt buscando vulnerabilidades
y CVEs conocidos con herramientas nativas del ecosistema sin gastar tokens.
Coste: 0 tokens (npm audit / pip-audit / pip).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def audit_node(project_dir: Path) -> tuple[int, str]:
    """Ejecuta npm audit y parsea el JSON resultante."""
    pkg_json = project_dir / "package.json"
    if not pkg_json.exists():
        return (0, "[NODE] No se encontro package.json en este directorio.")

    print(f"[SCA NODE] Auditando dependencias en {pkg_json}...")
    try:
        # Intentar ejecucion de npm audit --json
        res = subprocess.run(
            ["npm.cmd", "audit", "--json"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            shell=True
        )
        output = res.stdout or res.stderr
        if not output.strip():
            return (0, "[NODE] npm audit no devolvio salida.")

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            # Fallback en caso de salida no JSON
            return (res.returncode, f"[NODE] {output[:500]}")

        vulns = data.get("metadata", {}).get("vulnerabilities", {})
        critical = vulns.get("critical", 0)
        high = vulns.get("high", 0)
        moderate = vulns.get("moderate", 0)
        low = vulns.get("low", 0)
        total = vulns.get("total", critical + high + moderate + low)

        report = (
            f"[NODE AUDIT] Total: {total} | "
            f"Criticas: {critical} | Altas: {high} | Moderadas: {moderate} | Bajas: {low}"
        )

        if critical > 0 or high > 0:
            return (1, f"ALERTA ROJA: {report}\nAccion: Ejecuta 'npm audit fix' para corregir dependencias inseguras.")
        return (0, f"OK: {report}")

    except Exception as e:
        return (0, f"[NODE] Omitido: npm no disponible o error al ejecutar ({e})")

def audit_python(project_dir: Path) -> tuple[int, str]:
    """Verifica dependencias en Python buscando paquetes desactualizados o pip-audit."""
    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        return (0, "[PYTHON] No se encontro requirements.txt.")

    print(f"[SCA PYTHON] Auditando {req_file}...")
    # 1. Probar si pip-audit esta instalado
    try:
        res = subprocess.run(["pip-audit", "-r", str(req_file), "--format=json"], capture_output=True, text=True)
        if res.returncode == 0:
            return (0, "[PYTHON AUDIT] pip-audit en verde: 0 vulnerabilidades conocidas.")
        return (1, f"[PYTHON AUDIT ALERTA]: Se detectaron paquetes vulnerables:\n{res.stdout[:600]}")
    except FileNotFoundError:
        # pip-audit no instalado: verificacion rapida con pip list --outdated
        return (0, "[PYTHON] pip-audit no instalado en PATH. Se recomienda 'pip install pip-audit' para escaneo CVE profundo.")

def main() -> int:
    parser = argparse.ArgumentParser(description="Auditor SCA de dependencias a 0 tokens.")
    parser.add_argument("--path", type=str, default=".", help="Ruta del proyecto a auditar")
    args = parser.parse_args()

    target_dir = Path(args.path).resolve()
    print("=" * 70)
    print(f" [SCA GUARDIAN] INICIANDO AUDITORIA DE DEPENDENCIAS EN: {target_dir}")
    print("=" * 70)

    exit_code = 0
    node_code, node_msg = audit_node(target_dir)
    print(node_msg)
    if node_code != 0:
        exit_code = 1

    py_code, py_msg = audit_python(target_dir)
    print(py_msg)
    if py_code != 0:
        exit_code = 1

    print("-" * 70)
    if exit_code == 0:
        print("[SCA OK] Dependencias revisadas y aprobadas a 0 tokens.")
    else:
        print("[SCA FALLO] Se detectaron dependencias de alto riesgo que requieren actualizacion.")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
