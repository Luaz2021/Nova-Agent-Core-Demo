"""
Nova Agent - Actualizador Oficial Anti-Roturas (Multiplataforma)
================================================================
Creado por Saul Alexander Martinez Rivas (@Luaz2021)

Actualiza las skills, reglas y motor oficial de Nova Agent desde GitHub
preservando al 100% las notas, tareas y datos privados del usuario.

Uso:
  python actualizar_nova.py --check   (Solo comprobar si hay novedades)
  python actualizar_nova.py           (Actualizar de forma segura con backup previo)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import sys
import urllib.request

REPO_RAW_URL = "https://raw.githubusercontent.com/Luaz2021/Nova-Agent-Core-Demo/main"
MANIFEST_NAME = "manifest_master.json"


def get_user_gemini_paths():
    user_home = os.path.expanduser("~")
    gemini_dir = os.path.join(user_home, ".gemini")
    return {
        "gemini_dir": gemini_dir,
        "config_dir": os.path.join(gemini_dir, "config"),
        "skills_dir": os.path.join(gemini_dir, "config", "skills"),
        "antigravity_dir": os.path.join(gemini_dir, "antigravity"),
        "memory_dir": os.path.join(gemini_dir, "antigravity", "memory"),
        "scripts_dir": os.path.join(gemini_dir, "antigravity", "scripts"),
        "backups_dir": os.path.join(gemini_dir, "antigravity", "backups"),
        "manifest_path": os.path.join(gemini_dir, "antigravity", MANIFEST_NAME),
    }


def fetch_remote_json(endpoint: str) -> dict | None:
    url = f"{REPO_RAW_URL}/{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Nova-Agent-Updater"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return None


def fetch_remote_text(endpoint: str) -> str | None:
    url = f"{REPO_RAW_URL}/{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Nova-Agent-Updater"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8")
    except Exception:
        return None
    return None


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def create_safety_backup(paths: dict) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_target = os.path.join(paths["backups_dir"], f"backup_previo_{timestamp}")
    os.makedirs(backup_target, exist_ok=True)

    # 1. Copiar memoria si existe
    if os.path.exists(paths["memory_dir"]):
        shutil.copytree(paths["memory_dir"], os.path.join(backup_target, "memory"), dirs_exist_ok=True)

    # 2. Copiar reglas activas
    for f in ["GEMINI.md", "AYUDA.md"]:
        src = os.path.join(paths["config_dir"], f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_target, f))

    return backup_target


def check_updates():
    paths = get_user_gemini_paths()
    remote_manifest = fetch_remote_json(MANIFEST_NAME)

    if not remote_manifest:
        print("[AVISO] No se pudo conectar con GitHub para buscar actualizaciones (revisa tu conexion).")
        return False, None

    local_manifest = None
    if os.path.exists(paths["manifest_path"]):
        try:
            with open(paths["manifest_path"], "r", encoding="utf-8") as f:
                local_manifest = json.load(f)
        except Exception:
            local_manifest = None

    remote_ver = remote_manifest.get("Version", "2.0")
    local_ver = local_manifest.get("Version", "1.0") if local_manifest else "1.0"
    remote_total = remote_manifest.get("TotalComponents", 0)
    local_total = local_manifest.get("TotalComponents", 0) if local_manifest else 0

    has_updates = (remote_ver != local_ver) or (remote_total > local_total)
    return has_updates, {
        "local_ver": local_ver,
        "remote_ver": remote_ver,
        "local_total": local_total,
        "remote_total": remote_total,
        "remote_manifest": remote_manifest,
    }


def apply_update():
    paths = get_user_gemini_paths()
    has_updates, info = check_updates()

    if not info:
        print("[ERROR] Imposible obtener informacion de version.")
        return

    if not has_updates and "--force" not in sys.argv:
        print(f"[OK] Ya tienes la version mas reciente de Nova Agent (v{info['local_ver']} con {info['local_total']} componentes).")
        print("No hay cambios pendientes de actualizar.")
        return

    print("----------------------------------------------------------------------")
    print(f"[ACTUALIZADOR] Nueva version disponible: v{info['remote_ver']} (Remoto: {info['remote_total']} comps | Local: {info['local_total']} comps)")
    print("----------------------------------------------------------------------")

    # 1. Crear backup preventivo
    backup_path = create_safety_backup(paths)
    print(f"[OK] Copia de seguridad preventiva creada en: {os.path.basename(backup_path)}")

    remote_manifest = info["remote_manifest"]
    components = remote_manifest.get("Components", [])
    updated_count = 0
    new_skills = []

    # 2. Descargar o actualizar componentes
    for comp in components:
        ctype = comp.get("Type")
        rel_path = comp.get("RelativePath")
        comp_id = comp.get("Id", "")

        # A) Reglas y Documentacion
        if ctype in {"Rule", "Config"}:
            content = fetch_remote_text(rel_path)
            if content:
                dest = os.path.join(paths["config_dir"], os.path.basename(rel_path))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
                updated_count += 1

        # B) Skills (solo actualizar o anadir nuevas)
        elif ctype == "Skill":
            skill_name = comp.get("Name")
            skill_dest_dir = os.path.join(paths["skills_dir"], skill_name)
            skill_file = os.path.join(skill_dest_dir, "SKILL.md")
            
            is_new = not os.path.exists(skill_file)
            content = fetch_remote_text(f"skills/{skill_name}/SKILL.md")
            if content:
                os.makedirs(skill_dest_dir, exist_ok=True)
                with open(skill_file, "w", encoding="utf-8") as f:
                    f.write(content)
                updated_count += 1
                if is_new:
                    new_skills.append(skill_name)

        # C) Scripts
        elif ctype == "Script":
            script_name = comp.get("Name")
            content = fetch_remote_text(f"scripts/{script_name}")
            if content:
                dest = os.path.join(paths["scripts_dir"], script_name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
                updated_count += 1

        # D) Templates de Memoria Oficial (SE GUARDAN CON PREFIJO OFICIAL PARA NO PISAR AL USUARIO)
        elif ctype == "Template":
            tpl_name = comp.get("Name")
            content = fetch_remote_text(f"memory_templates/{tpl_name}")
            if content:
                # Guardar siempre la version oficial de Saul
                clean_name = tpl_name.replace(".template", "_oficial")
                dest = os.path.join(paths["memory_dir"], clean_name)
                os.makedirs(paths["memory_dir"], exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
                updated_count += 1

    # 3. Guardar el nuevo manifiesto local
    with open(paths["manifest_path"], "w", encoding="utf-8") as f:
        json.dump(remote_manifest, f, indent=4, ensure_ascii=False)

    print(f"[OK] Actualizacion a v{info['remote_ver']} completada con exito ({updated_count} archivos actualizados).")
    if new_skills:
        print(f"[INFO] Nuevas skills agregadas ({len(new_skills)}): {', '.join(new_skills[:6])}")
    print("[SEGURIDAD] Tus notas privadas (tasks.md, napkin.md y perfil_usuario.json) se mantuvieron intactas al 100%.")


if __name__ == "__main__":
    if "--check" in sys.argv:
        has_up, info = check_updates()
        if info:
            if has_up:
                print(f"[NOVEDAD] Hay una nueva version disponible: v{info['remote_ver']} (Tu version actual: v{info['local_ver']}).")
            else:
                print(f"[AL_DIA] Tienes la version mas reciente (v{info['local_ver']}).")
    else:
        apply_update()
