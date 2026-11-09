"""
Genera manifest_master.json (lo que lee "Nova, busca actualizaciones" en el equipo de cada usuario).
Solo lo usa el autor antes de publicar un parche:

    python herramientas_autor/generar_manifest.py --version 3.1

Reglas:
  - Cada archivo va con su SHA-256 tal como lo sirve GitHub (saltos de linea LF), asi el actualizador verifica
    la descarga y solo baja lo que cambio.
  - Compatibilidad con el actualizador de Nova v2.x: GEMINI.md (Rule), AYUDA.md (Config), scripts de primer nivel
    (Script), plantillas de memoria (Template) y una entrada por skill (Skill) van con el formato antiguo. Todo lo
    demas va como "File" (el actualizador viejo lo ignora; el nuevo lo trae).
  - perfil_usuario.json NUNCA va en el manifiesto (el actualizador v2.3 lo sobrescribia).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXCLUIR_PARTES = {"__pycache__", ".git", "medios_cache", "node_modules", ".DS_Store"}
EXCLUIR_NOMBRES = {"perfil_usuario.json", "memoria_disenos.json"}
EXCLUIR_EXT = {".pyc"}
PRESERVAR = {"nova_core/nova_hooks_config.json"}  # el usuario puede cambiarlo (modo registro/bloqueo)


def sha_github(p: Path) -> tuple[str, int]:
    datos = p.read_bytes()
    if b"\0" not in datos[:8000]:  # texto: GitHub lo guarda con LF (.gitattributes)
        datos = datos.replace(b"\r\n", b"\n")
    return hashlib.sha256(datos).hexdigest().upper(), len(datos)


def archivos(carpeta: Path):
    for p in sorted(carpeta.rglob("*")):
        rel = p.relative_to(RAIZ)
        if not p.is_file() or set(rel.parts) & EXCLUIR_PARTES or p.name in EXCLUIR_NOMBRES or p.suffix in EXCLUIR_EXT:
            continue
        yield p, rel.as_posix()


def componente(tipo: str, nombre: str, rel: str, destino: str, p: Path, **extra) -> dict:
    sha, tam = sha_github(p)
    ident = f"{tipo.lower()}_" + "".join(c if c.isalnum() else "_" for c in rel.lower())
    c = {"Id": ident, "Name": nombre, "Type": tipo, "RelativePath": rel, "TargetRelative": destino, "SizeBytes": tam,
         "SHA256": sha}
    c.update(extra)
    if rel in PRESERVAR:
        c["Preserve"] = True
    return c


def generar(version: str) -> dict:
    comps = [componente("Rule", "GEMINI.md", "GEMINI.md", "config/GEMINI.md", RAIZ / "GEMINI.md"),
             componente("Config", "AYUDA.md", "AYUDA.md", "config/AYUDA.md", RAIZ / "AYUDA.md")]
    for p, rel in archivos(RAIZ / "scripts"):
        sub = rel[len("scripts/"):]
        tipo = "Script" if "/" not in sub else "File"
        comps.append(componente(tipo, p.name, rel, f"antigravity/scripts/{sub}", p))
    for p, rel in archivos(RAIZ / "memory_templates"):
        comps.append(componente("Template", p.name, rel, f"antigravity/memory/{p.name}", p))
    for p, rel in archivos(RAIZ / "nova_core"):
        comps.append(componente("File", p.name, rel, rel, p))
    for carpeta in ("herramientas", "clonador"):
        for p, rel in archivos(RAIZ / carpeta):
            comps.append(componente("File", p.name, rel, f"antigravity/{rel}", p))
    for p, rel in archivos(RAIZ / "almacen"):
        comps.append(componente("File", p.name, rel, f"antigravity/{rel}", p))
    for carpeta in sorted(d for d in (RAIZ / "skills").iterdir() if d.is_dir()):
        skill_md = carpeta / "SKILL.md"
        for p, rel in archivos(carpeta):
            sub = rel[len(f"skills/{carpeta.name}/"):]
            if p == skill_md:
                sha, _ = sha_github(p)
                total = sum(sha_github(x)[1] for x, _ in archivos(carpeta))
                comps.append({"Id": f"skill_{carpeta.name.replace('-', '_')}", "Name": carpeta.name, "Type": "Skill",
                              "RelativePath": f"skills/{carpeta.name}", "TargetRelative": f"config/skills/{carpeta.name}",
                              "SizeBytes": total, "SHA256": sha, "SkillSHA256": sha})
            else:
                comps.append(componente("File", p.name, rel, f"config/skills/{carpeta.name}/{sub}", p))
    return {"Version": version, "Engine": "NovaManifestGuardian v3", "GeneratedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "TotalComponents": len(comps), "Components": comps}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="p. ej. 3.0, 3.1...")
    args = ap.parse_args()
    m = generar(args.version)
    (RAIZ / "manifest_master.json").write_text(json.dumps(m, indent=4, ensure_ascii=False) + "\n", encoding="utf-8",
                                               newline="\n")
    tipos: dict = {}
    for c in m["Components"]:
        tipos[c["Type"]] = tipos.get(c["Type"], 0) + 1
    print(f"manifest_master.json v{args.version}: {m['TotalComponents']} componentes {tipos}")


if __name__ == "__main__":
    main()
