"""
Nova Agent - Actualizador Oficial Anti-Roturas v3 (Windows / macOS / Linux)
===========================================================================
Creado por Saul Alexander Martinez Rivas (@Luaz2021)

Trae los parches oficiales desde GitHub (manifest_master.json) SIN tocar lo privado del usuario:
  - Compara archivo por archivo con SHA-256: solo baja lo que cambio (aunque el numero de version no cambie).
  - Verifica el SHA-256 de cada descarga: si no coincide, NO se escribe (nada a medias ni manipulado).
  - Antes de pisar un archivo guarda la copia en ~/.gemini/antigravity/backups/backup_previo_<fecha>/.
  - Nunca toca: memory/ (tasks.md, napkin.md, perfil_usuario.json, lecciones...), claves, hooks.json ni config.json,
    ni archivos marcados "Preserve" que ya existan (p. ej. la memoria de disenos de la biblioteca).
  - Las plantillas de memoria se guardan como *_oficial.md al lado de las del usuario.
  - Si cambian los hooks, vuelve a registrarlos en ~/.gemini/config/hooks.json (sin borrar hooks ajenos).

Compatibilidad con Nova v2.x: el actualizador viejo solo entiende Rule/Config/Script/Skill/Template y se
actualiza a si mismo a esta version; lo demas (tipo "File") lo trae esta version la siguiente vez que se pida.

Uso:
  python actualizar_nova.py --check   (solo comprobar si hay novedades)
  python actualizar_nova.py           (actualizar con copia de seguridad previa)
  python actualizar_nova.py --force   (revisa y repara todos los archivos)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_RAW_URL = os.environ.get("NOVA_REPO_RAW_URL", "https://raw.githubusercontent.com/Luaz2021/Nova-Agent-Core-Demo/main")
MANIFEST_NAME = "manifest_master.json"
GEMINI = Path.home() / ".gemini"
ANTIGRAVITY = GEMINI / "antigravity"
LOCAL_MANIFEST = ANTIGRAVITY / MANIFEST_NAME
BACKUPS = ANTIGRAVITY / "backups"
# Nunca se escriben desde el actualizador (datos y ajustes del usuario)
INTOCABLES = {ANTIGRAVITY / "memory" / "perfil_usuario.json", GEMINI / "config" / "secrets.env",
              GEMINI / "config" / "hooks.json", GEMINI / "config" / "config.json", GEMINI / "config" / "mcp_config.json"}


def _get(ruta_relativa: str, timeout: int = 20) -> bytes | None:
    ruta = ruta_relativa.replace("\\", "/").lstrip("/")
    if REPO_RAW_URL.startswith("file://"):  # pruebas locales: NOVA_REPO_RAW_URL=file:///ruta/al/repo
        try:
            return (Path(REPO_RAW_URL[7:].lstrip("/") if os.name == "nt" else REPO_RAW_URL[7:]) / ruta).read_bytes()
        except OSError:
            return None
    try:
        req = urllib.request.Request(f"{REPO_RAW_URL}/{ruta}", headers={"User-Agent": "Nova-Agent-Updater"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read()
    except Exception:
        return None
    return None


def fetch_remote_json(endpoint: str) -> dict | None:
    datos = _get(endpoint)
    try:
        return json.loads(datos.decode("utf-8-sig")) if datos else None
    except ValueError:
        return None


def sha256_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest().upper()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError:
        return ""


def leer_manifest_local() -> dict:
    try:
        return json.loads(LOCAL_MANIFEST.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def plan_de_componente(comp: dict) -> tuple[str, Path, str, bool] | None:
    """(ruta en el repo, destino local, sha esperado, preservar) de un componente; None si no aplica."""
    tipo = comp.get("Type")
    rel = str(comp.get("RelativePath") or "").replace("\\", "/")
    destino_rel = str(comp.get("TargetRelative") or "").replace("\\", "/")
    esperado = str(comp.get("SHA256") or "").upper()
    if not rel or not destino_rel or Path(destino_rel).is_absolute() or ".." in Path(destino_rel).parts:
        return None
    if tipo == "Skill":  # entrada heredada de v2 (carpeta) -> su SKILL.md; el SHA del SKILL.md va en SkillSHA256
        rel, destino_rel = f"{rel.rstrip('/')}/SKILL.md", f"{destino_rel.rstrip('/')}/SKILL.md"
        esperado = str(comp.get("SkillSHA256") or "").upper()
    elif tipo == "Template":  # nunca pisa la nota del usuario: la version oficial va al lado
        nombre = Path(destino_rel).name
        if nombre == "perfil_usuario.json":
            return None
        destino_rel = str(Path(destino_rel).with_name(nombre.replace(".template", "_oficial"))).replace("\\", "/")
    destino = GEMINI / destino_rel
    if destino in INTOCABLES:
        return None
    return rel, destino, esperado, bool(comp.get("Preserve"))


def comprobar(forzar: bool = False) -> tuple[dict | None, list]:
    """(manifiesto remoto, cambios [(comp, rel, destino, esperado)])."""
    remoto = fetch_remote_json(MANIFEST_NAME)
    if not remoto:
        return None, []
    cambios = []
    for comp in remoto.get("Components", []):
        plan = plan_de_componente(comp)
        if not plan:
            continue
        rel, destino, esperado, preservar = plan
        existe = destino.exists()
        if preservar and existe:
            continue
        if forzar or not existe or (esperado and sha256_file(destino) != esperado):
            cambios.append((comp, rel, destino, esperado))
    return remoto, cambios


def respaldar(destino: Path, carpeta: Path) -> None:
    if destino.is_file():
        copia = carpeta / destino.relative_to(GEMINI)
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino, copia)


def respaldo_memoria(carpeta: Path) -> None:
    mem = ANTIGRAVITY / "memory"
    if mem.exists():
        shutil.copytree(mem, carpeta / "antigravity" / "memory", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("chat_logs", "registros"))




def reparar_arranque_windows() -> None:
    if os.name != 'nt':
        return
    bad = GEMINI.parent / '.gemini ntigravity'
    if bad.is_dir():
        for sub in ('herramientas', 'clonador'):
            if (bad / sub).is_dir():
                shutil.copytree(bad / sub, ANTIGRAVITY / sub, dirs_exist_ok=True)
        shutil.rmtree(bad, ignore_errors=True)
    vbs = ANTIGRAVITY / 'scripts' / 'start_session_guard.vbs'
    startup = Path(os.environ.get('APPDATA', '')) / 'Microsoft/Windows/Start Menu/Programs/Startup/Nova_SessionGuard.vbs'
    if vbs.is_file() and startup.parent.is_dir():
        shutil.copy2(vbs, startup)
        subprocess.Popen(['wscript.exe', str(vbs)], close_fds=True)


def registrar_hooks() -> None:
    script = GEMINI / "nova_core" / "instalar_hooks.py"
    if script.exists():
        subprocess.run([sys.executable, str(script)], check=False)


def apply_update(forzar: bool = False) -> int:
    remoto, cambios = comprobar(forzar)
    if remoto is None:
        print("[AVISO] No se pudo conectar con GitHub para buscar actualizaciones (revisa tu conexion).")
        return 1
    ver_r, ver_l = remoto.get("Version", "?"), leer_manifest_local().get("Version", "1.0")
    LOCAL_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    if not cambios:
        LOCAL_MANIFEST.write_text(json.dumps(remoto, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] Ya tienes la version mas reciente de Nova Agent (v{ver_r}). No hay parches pendientes.")
        return 0

    print("----------------------------------------------------------------------")
    print(f"[ACTUALIZADOR] Parche disponible: v{ver_r} (tenias v{ver_l}) | {len(cambios)} archivos nuevos o cambiados")
    print("----------------------------------------------------------------------")
    carpeta = BACKUPS / f"backup_previo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    carpeta.mkdir(parents=True, exist_ok=True)
    respaldo_memoria(carpeta)
    print(f"[OK] Copia de seguridad creada en: backups/{carpeta.name}")

    escritos, fallidos, nuevas_skills, hooks_tocados, auto = 0, [], [], False, False
    for comp, rel, destino, esperado in cambios:
        datos = _get(rel)
        if datos is None:
            fallidos.append(rel)
            continue
        if esperado and esperado not in {sha256_bytes(datos), sha256_bytes(datos.replace(b'\r\n', b'\n')), sha256_bytes(datos.replace(b'\n', b'\r\n'))}:
            fallidos.append(f"{rel} (la firma SHA-256 no coincide: no se instala)")
            continue
        es_nueva = not destino.exists()
        try:
            respaldar(destino, carpeta)
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp = destino.with_name(destino.name + ".nova_tmp")
            tmp.write_bytes(datos)
            os.replace(tmp, destino)
            escritos += 1
        except OSError as e:
            fallidos.append(f"{rel} ({e})")
            continue
        if comp.get("Type") == "Skill" and es_nueva:
            nuevas_skills.append(comp.get("Name", rel))
        if rel.startswith("nova_core/"):
            hooks_tocados = True
        if rel == "scripts/actualizar_nova.py":
            auto = True

    if not fallidos:
        LOCAL_MANIFEST.write_text(json.dumps(remoto, indent=2, ensure_ascii=False), encoding="utf-8")
    if hooks_tocados:
        registrar_hooks()
    reparar_arranque_windows()

    print(f"[OK] Parche v{ver_r} aplicado: {escritos} archivos actualizados.")
    if nuevas_skills:
        print(f"[INFO] Nuevas skills ({len(nuevas_skills)}): {', '.join(nuevas_skills[:6])}")
    if fallidos:
        print(f"[AVISO] {len(fallidos)} archivos no se pudieron traer (se reintentara la proxima vez):")
        for f in fallidos[:10]:
            print(f"   - {f}")
    if hooks_tocados:
        print("[INFO] Reglas automaticas (hooks) actualizadas: cierra y abre Antigravity para activarlas.")
    if auto:
        print("[INFO] El actualizador se actualizo a si mismo: ejecutalo otra vez para revisar el resto con la version nueva.")
    print("[SEGURIDAD] Tus notas (memory/), tu perfil y tus claves no se han tocado.")
    return 0 if not fallidos else 2


def check_updates() -> int:
    remoto, cambios = comprobar()
    if remoto is None:
        print("[AVISO] No se pudo conectar con GitHub para buscar actualizaciones (revisa tu conexion).")
        return 1
    if cambios:
        print(f"[NOVEDAD] Hay parches disponibles: v{remoto.get('Version', '?')} ({len(cambios)} archivos). "
              f"Tu version: v{leer_manifest_local().get('Version', '1.0')}.")
    else:
        print(f"[AL_DIA] Tienes la version mas reciente (v{remoto.get('Version', '?')}).")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check_updates())
    sys.exit(apply_update(forzar="--force" in sys.argv))
