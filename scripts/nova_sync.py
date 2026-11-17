"""
Nova Sync v1 (version publica, v3.2) - Nova en varios equipos con Google Drive para escritorio
================================================================================================
Creado por Saul Alexander Martinez Rivas (@Luaz2021)

La carpeta de Google Drive manda. Cada equipo trabaja en su ~/.gemini y usa dos puentes:
  bajar   "Nova, sincroniza"         Drive -> este equipo. NUNCA escribe en Drive.
  subir   "Nova, sube los cambios"   este equipo -> Drive. Es lo UNICO que escribe en Drive.
  espejo  "Nova, deja este equipo igual que Drive"  resetea este equipo a Drive (copia antes lo distinto).

Asistente guiado (una vez por equipo):
  configurar   detecta Google Drive para escritorio (si falta, da el enlace oficial), encuentra "Mi unidad",
               crea la carpeta Nova_Sync (con permiso: --si) y hace la primera pasada:
               carpeta vacia -> este es el primer equipo (sube) | con datos -> equipo nuevo (espejo).
  estado       como esta (configurado, ultima pasada, pendientes)
  desconectar  este equipo deja de sincronizar (no borra nada)

BLINDAJE
  - Solo "subir" puede escribir, mover o borrar en Drive (escribir_nube() lo comprueba SIEMPRE).
  - Comparacion en 3 vias con la "base" (como estaba todo en la ultima pasada de ESTE equipo).
  - Bajar: si un archivo cambio en los dos lados gana Drive y lo local se guarda al lado (*.local-<fecha>.*).
    Lo creado aqui y no subido no se toca: queda "pendiente de subir".
  - Subir: si Drive tiene una version mas nueva (de otro equipo), NO la pisa: queda "bloqueado" hasta bajar.
  - Primera vez (sin base) nunca borra. Mas de 25 borrados en una pasada -> no borra ninguno (salvo --forzar).
  - Carpeta que falta o esta vacia en un lado (Drive a medio montar) -> esa carpeta no se toca.
  - Lo borrado en Drive va a Nova_Sync/_papelera/<fecha>; lo de este equipo a ~/.gemini/antigravity/backups/sync/.
  - Una sola pasada a la vez (candado). Nunca viajan: claves (secrets.env, *.clave, .env), hooks.json, nova_env,
    perfil_usuario.json (hardware de cada equipo), estados de los vigilantes, caches.

Uso:  python nova_sync.py configurar [--si] [--carpeta RUTA] [--nombre Nova_Sync]
      python nova_sync.py bajar | subir | espejo [--simular] [--forzar]
      python nova_sync.py estado | desconectar
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import socket
import string
import subprocess
import sys
import time
from pathlib import Path

GEMINI = Path.home() / ".gemini"
AG = GEMINI / "antigravity"
CONFIG = GEMINI / "config" / "nova_sync.json"          # de cada equipo (no viaja)
BASE = AG / "sync_base_nova.json"                       # de cada equipo (no viaja)
ESTADO = AG / "memory" / "sync_status.json"             # excluido del sync
CANDADO = AG / ".nova_sync.lock"
BACKUPS = AG / "backups" / "sync"
ENLACE_DRIVE = "https://www.google.com/drive/download/"
MAX_BORRADOS = 25
WIN, MAC = os.name == "nt", sys.platform == "darwin"

# (carpeta local relativa a ~/.gemini, nombre en Drive). Los archivos sueltos van con arbol=False.
MAPEO = [
    ("config/GEMINI.md", "reglas/GEMINI.md", False),
    ("config/AYUDA.md", "reglas/AYUDA.md", False),
    ("config/skills", "skills_indices", True),
    ("antigravity/almacen", "almacen", True),
    ("antigravity/scripts", "scripts", True),
    ("antigravity/herramientas", "herramientas", True),
    ("antigravity/clonador", "clonador", True),
    ("antigravity/memory", "memory", True),
    ("antigravity/documentos_generados", "documentos_generados", True),
    ("antigravity/proyectos", "proyectos", True),
    ("antigravity/scratch", "scratch", True),
    ("nova_core", "nova_core", True),
]
EXCLUIR = re.compile(
    r"(?i)(^|/)(__pycache__|node_modules|\.git|\.venv|venv|\.next|\.cache|\.ruff_cache|\.pytest_cache|\.mypy_cache"
    r"|salida_docs|\.nova_respaldo|medios_cache|chat_logs_tmp)(/|$)"
    r"|\.pyc$|\.pid$|\.lock$|\.nova_tmp$|\.local-\d{8}-\d{4}|\.conflicto-|(^|/)~\$|(^|/)(desktop\.ini|thumbs\.db|\.ds_store)$"
    r"|(^|/)(secrets?\.env|\.env(\.[\w.-]+)?|[^/]*\.clave|hooks\.json(\..*)?|config\.json|mcp_config\.json)$"
    r"|(^|/)(perfil_usuario\.json|doctor_estado\.json|sync_status[^/]*\.json|equipos\.json)$"
    r"|(^|/)\.(nova_hooks_estado|nova_turno_estado|estado_lint|nova_modo|autoriza_codigo)[^/]*\.json$"
)
INBOX = "memory/inbox_lecciones.md"
LOGS_MEZCLA = re.compile(r"(?i)^memory/registros/[^/]+\.(log|jsonl)$")


class Blindaje(Exception):
    pass


# ------------------------------------------------------------------ utilidades
def ahora() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def leer_json(p: Path, defecto):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return defecto


def escribir_json(p: Path, datos) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def firma(p: Path, cache: dict | None) -> dict | None:
    try:
        st = p.stat()
    except OSError:
        return None
    if cache and cache.get("s") == st.st_size and cache.get("t") == st.st_mtime_ns and cache.get("h"):
        return {"h": cache["h"], "s": st.st_size, "t": st.st_mtime_ns}
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return {"h": h.hexdigest(), "s": st.st_size, "t": st.st_mtime_ns}


def listar(raiz: Path) -> dict[str, str]:
    """{clave_minusculas: ruta_relativa_con_/} de los archivos de un arbol, sin excluidos."""
    out = {}
    if not raiz.is_dir():
        return out
    for dirpath, dirs, files in os.walk(raiz):
        rel_dir = Path(dirpath).relative_to(raiz).as_posix()
        dirs[:] = [d for d in dirs if not EXCLUIR.search(f"{rel_dir}/{d}/".lstrip("./"))]
        for f in files:
            rel = f"{rel_dir}/{f}".lstrip("./") if rel_dir != "." else f
            if not EXCLUIR.search(rel):
                out[rel.lower()] = rel
    return out


class Candado:
    def __enter__(self):
        CANDADO.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(180):  # hasta 15 min en cola
            try:
                fd = os.open(CANDADO, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {ahora()}".encode())
                os.close(fd)
                return self
            except FileExistsError:
                if time.time() - CANDADO.stat().st_mtime > 900:  # candado abandonado
                    CANDADO.unlink(missing_ok=True)
                    continue
                time.sleep(5)
        raise SystemExit("[SYNC] Otra sincronizacion lleva mas de 15 min. Esta no se ejecuta.")

    def __exit__(self, *a):
        CANDADO.unlink(missing_ok=True)


# ------------------------------------------------------------------ Google Drive para escritorio
def drive_instalado() -> bool:
    if WIN:
        pf = [os.environ.get("PROGRAMFILES", r"C:\Program Files"), os.environ.get("PROGRAMFILES(X86)", "")]
        return any(b and Path(b, "Google", "Drive File Stream").is_dir() for b in pf)
    if MAC:
        return Path("/Applications/Google Drive.app").exists()
    return False


def _etiqueta_volumen(letra: str) -> str:
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(261)
        ctypes.windll.kernel32.GetVolumeInformationW(f"{letra}:\\", buf, 261, None, None, None, None, 0)
        return buf.value
    except Exception:
        return ""


NO_SON_MI_UNIDAD = {".shortcut-targets-by-id", "shared drives", "unidades compartidas", "other computers",
                    "otros ordenadores", "otros equipos", ".tmp.drivedownload", ".tmp.driveupload", "$recycle.bin",
                    "system volume information"}


def buscar_mi_unidad() -> list[Path]:
    """Carpetas 'Mi unidad'/'My Drive' (cualquier idioma) de Google Drive para escritorio montado en este equipo."""
    raices: list[Path] = []
    if WIN:
        for letra in string.ascii_uppercase[3:]:
            r = Path(f"{letra}:\\")
            try:
                if r.exists() and ("google drive" in _etiqueta_volumen(letra).lower() or (r / "My Drive").is_dir()
                                    or (r / "Mi unidad").is_dir()):
                    raices.append(r)
            except OSError:
                pass
    elif MAC:
        cs = Path.home() / "Library" / "CloudStorage"
        if cs.is_dir():
            raices += [d for d in cs.iterdir() if d.name.startswith("GoogleDrive")]
        if Path("/Volumes/GoogleDrive").is_dir():
            raices.append(Path("/Volumes/GoogleDrive"))
    encontradas = []
    for r in raices:
        try:
            for d in r.iterdir():
                if d.is_dir() and d.name.lower() not in NO_SON_MI_UNIDAD:
                    encontradas.append(d)
                    break
        except OSError:
            pass
    return encontradas


# ------------------------------------------------------------------ motor
class Motor:
    def __init__(self, modo: str, nube: Path, simular=False, forzar=False):
        self.modo, self.nube, self.simular, self.forzar = modo, nube, simular, forzar
        self.base = leer_json(BASE, {}).get("archivos", {})
        self.primera = not BASE.exists()
        self.fecha = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        self.c = {k: 0 for k in ("al_dia", "subidos", "bajados", "borrados", "mezclados", "gana_nube",
                                 "pend_subir", "pend_bajar", "bloqueados", "errores")}
        self.listas = {"bloqueados": [], "copias_locales": [], "errores": [], "pend_subir": [], "omitidas": []}

    # --- el blindaje: TODA escritura en Drive pasa por aqui
    def escribir_nube(self, destino: Path) -> None:
        if self.modo != "subir":
            raise Blindaje(f"modo {self.modo} NO puede escribir en Drive ({destino})")
        if self.nube not in destino.parents and destino != self.nube:
            raise Blindaje(f"escritura fuera de la carpeta de Nova Sync ({destino})")

    def copiar(self, origen: Path, destino: Path) -> bool:
        if self.nube in destino.parents:
            self.escribir_nube(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_name(destino.name + ".nova_tmp")
        esperado = firma(origen, None)["h"]
        for _ in range(3):
            try:
                shutil.copy2(origen, tmp)
                if firma(tmp, None)["h"] == esperado:
                    os.replace(tmp, destino)
                    return True
            except OSError:
                time.sleep(0.6)
        tmp.unlink(missing_ok=True)
        return False

    def apartar(self, p: Path, clave: str) -> None:
        """Mueve a la papelera (nunca borra de verdad)."""
        if self.nube in p.parents:
            self.escribir_nube(p)
            dest = self.nube / "_papelera" / self.fecha / clave
        else:
            dest = BACKUPS / "borrados" / self.fecha / clave
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))

    def inventario(self) -> dict[str, tuple[Path, Path]]:
        claves: dict[str, tuple[Path, Path]] = {}
        for local, nube, arbol in MAPEO:
            lp, cp = GEMINI / local, self.nube / nube
            if not arbol:
                # archivo suelto (reglas): si falta en un lado no se quita del otro (solo se copia lo que existe)
                if cp.exists() or (self.modo == "subir" and lp.exists()) or lp.exists() and cp.exists():
                    claves[nube.lower()] = (lp, cp)
                continue
            con_base = any(k.startswith(nube.lower() + "/") for k in self.base)
            vacia_nube = not cp.is_dir() or not any(cp.iterdir())
            vacia_local = not lp.is_dir() or not any(lp.iterdir())
            # FRENO: Drive a medio montar o carpeta borrada entera -> esa carpeta no se toca
            if (self.modo in ("bajar", "espejo") and vacia_nube and (con_base or self.modo == "espejo")) or \
               (self.modo == "subir" and vacia_local and con_base):
                if not (vacia_nube and vacia_local):
                    self.listas["omitidas"].append(nube)
                continue
            for rel in list(listar(lp).values()) + list(listar(cp).values()):
                claves[f"{nube}/{rel}".lower()] = (lp / rel, cp / rel)
        for k in list(self.base):
            if k not in claves:
                arbol = next(((l, n) for l, n, a in MAPEO if a and k.startswith(n.lower() + "/")), None)
                if arbol and arbol[1] not in self.listas["omitidas"]:
                    rel = self.base[k]["clave"][len(arbol[1]) + 1:]
                    claves[k] = (GEMINI / arbol[0] / rel, self.nube / arbol[1] / rel)
        return claves

    def decidir(self, k: str, L: dict | None, C: dict | None) -> str:
        b = self.base.get(k)
        clave = (b or {}).get("clave", k)
        if self.modo == "espejo":
            return "BAJAR" if C else "QUITAR_LOCAL"
        if not b:
            if L and not C:
                op = "SUBIR"
            elif C and not L:
                op = "BAJAR"
            else:
                op = ("SUBIR" if L["t"] >= C["t"] else "BAJAR") if self.primera else "CONFLICTO"
        else:
            cl = (L or {}).get("h") != b["h"]
            cn = (C or {}).get("h") != b["h"]
            if cl and not cn:
                op = "SUBIR" if L else "BORRAR_NUBE"
            elif cn and not cl:
                op = "BAJAR" if C else "BORRAR_LOCAL"
            elif not L:
                op = "BAJAR"
            elif not C:
                op = "SUBIR"
            else:
                op = "CONFLICTO"
        if op == "CONFLICTO" and (clave.lower() == INBOX or LOGS_MEZCLA.match(clave)):
            op = "MEZCLAR"
        if self.modo == "bajar":
            if op == "CONFLICTO":
                return "GANA_NUBE"
            if op in ("SUBIR", "BORRAR_NUBE", "MEZCLAR"):
                return "PEND_SUBIR"
        if self.modo == "subir":
            if op == "CONFLICTO":
                return "BLOQUEADO"
            if op in ("BAJAR", "BORRAR_LOCAL"):
                return "PEND_BAJAR"
        return op

    def ejecutar(self) -> dict:
        claves = self.inventario()
        nueva_base: dict = {}
        acciones = []
        for k, (lp, cp) in sorted(claves.items()):
            b = self.base.get(k)
            L = firma(lp, b and {"h": b["h"], "s": b.get("ls"), "t": b.get("lt")})
            C = firma(cp, b and {"h": b["h"], "s": b.get("cs"), "t": b.get("ct")})
            clave = (b or {}).get("clave") or self._clave_real(k, lp)
            if L and C and L["h"] == C["h"]:
                nueva_base[k] = {"clave": clave, "h": L["h"], "ls": L["s"], "lt": L["t"], "cs": C["s"], "ct": C["t"]}
                self.c["al_dia"] += 1
                continue
            if not L and not C:
                continue
            op = self.decidir(k, L, C)
            if op in ("PEND_SUBIR", "PEND_BAJAR", "BLOQUEADO"):
                self.c[{"PEND_SUBIR": "pend_subir", "PEND_BAJAR": "pend_bajar", "BLOQUEADO": "bloqueados"}[op]] += 1
                if op == "BLOQUEADO":
                    self.listas["bloqueados"].append(clave)
                if op == "PEND_SUBIR":
                    self.listas["pend_subir"].append(clave)
                if b:
                    nueva_base[k] = b
                continue
            acciones.append((k, clave, lp, cp, op, L, C))

        borrados = [a for a in acciones if a[4] in ("BORRAR_NUBE", "BORRAR_LOCAL")]
        frenar_borrados = len(borrados) > MAX_BORRADOS and not self.forzar
        if frenar_borrados:
            print(f"  [FRENO] Se querian borrar {len(borrados)} archivos (limite {MAX_BORRADOS}). No se borra ninguno. "
                  "Revisa que Drive este completo (o usa --forzar si de verdad lo borraste tu).")
            for a in borrados:
                if self.base.get(a[0]):
                    nueva_base[a[0]] = self.base[a[0]]
            acciones = [a for a in acciones if a not in borrados]
        if self.primera:  # primera pasada: nunca borra
            acciones = [a for a in acciones if a[4] not in ("BORRAR_NUBE", "BORRAR_LOCAL")]

        informe_espejo = []
        for k, clave, lp, cp, op, L, C in acciones:
            print(f"  [{op}] {clave}")
            if self.simular:
                continue
            ok = True
            try:
                if op == "SUBIR":
                    ok = self.copiar(lp, cp); self.c["subidos"] += ok
                elif op == "BAJAR":
                    if self.modo == "espejo" and L:
                        dest = BACKUPS / "espejo" / self.fecha / clave
                        ok = self.copiar(lp, dest); informe_espejo.append(f"PISADO   {clave}")
                    elif self.modo == "espejo":
                        informe_espejo.append(f"BAJADO   {clave}")
                    ok = ok and self.copiar(cp, lp); self.c["bajados"] += ok
                elif op == "QUITAR_LOCAL":  # espejo: no existe en Drive -> se aparta (nunca se borra)
                    dest = BACKUPS / "espejo" / self.fecha / clave
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(lp), str(dest))
                    informe_espejo.append(f"QUITADO  {clave}"); self.c["borrados"] += 1
                elif op == "BORRAR_NUBE":
                    self.apartar(cp, clave); self.c["borrados"] += 1
                elif op == "BORRAR_LOCAL":
                    self.apartar(lp, clave); self.c["borrados"] += 1
                elif op == "GANA_NUBE":
                    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
                    lado = lp.with_name(f"{lp.stem}.local-{stamp}{lp.suffix}")
                    ok = self.copiar(lp, lado) and self.copiar(cp, lp)
                    if ok:
                        self.listas["copias_locales"].append(str(lado.relative_to(GEMINI)))
                    self.c["gana_nube"] += ok
                elif op == "MEZCLAR":
                    self.mezclar(lp, cp); self.c["mezclados"] += 1
                elif op == "CONFLICTO":  # solo en subir con primera=False no llega aqui; por seguridad
                    ok = False
            except Blindaje:
                raise
            except OSError as e:
                ok = False
                self.listas["errores"].append(f"{clave}: {e}")
            if not ok:
                self.c["errores"] += 1
                if self.base.get(k):
                    nueva_base[k] = self.base[k]
                continue
            if op in ("BORRAR_NUBE", "BORRAR_LOCAL", "QUITAR_LOCAL"):
                continue
            L2, C2 = firma(lp, None), firma(cp, None)
            if L2 and C2:
                nueva_base[k] = {"clave": clave, "h": L2["h"], "ls": L2["s"], "lt": L2["t"], "cs": C2["s"], "ct": C2["t"]}

        # lo que esta pasada no reviso (carpetas omitidas) conserva su base
        for k, v in self.base.items():
            if k not in nueva_base and k not in claves:
                nueva_base[k] = v
        if informe_espejo and not self.simular:
            d = BACKUPS / "espejo" / self.fecha
            d.mkdir(parents=True, exist_ok=True)
            (d / "INFORME.txt").write_text(
                f"ESPEJO {ahora()} en {socket.gethostname()}: este equipo quedo IGUAL que Drive.\n"
                "PISADO = tu version local esta en esta carpeta | QUITADO = no existia en Drive (tambien aqui) | "
                "BAJADO = faltaba en este equipo\n\n" + "\n".join(informe_espejo) + "\n", encoding="utf-8")
        if not self.simular:
            escribir_json(BASE, {"version": 1, "equipo": socket.gethostname(), "fecha": ahora(), "archivos": nueva_base})
        return self.resumen(frenar_borrados)

    def _clave_real(self, k: str, lp: Path) -> str:
        for local, nube, arbol in MAPEO:
            if not arbol and k == nube.lower():
                return nube
            if arbol and k.startswith(nube.lower() + "/"):
                try:
                    return f"{nube}/{lp.relative_to(GEMINI / local).as_posix()}"
                except ValueError:
                    return k
        return k

    def mezclar(self, lp: Path, cp: Path) -> None:
        """Lineas de Drive + las locales que Drive no tiene (no se pierde ninguna leccion ni linea de log)."""
        self.escribir_nube(cp)  # solo en subir (en bajar MEZCLAR queda pendiente de subir)
        nube = cp.read_text(encoding="utf-8", errors="replace").splitlines()
        vistas = set(nube)
        extra = [l for l in lp.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip() and l not in vistas]
        texto = "\n".join(nube + extra) + "\n"
        tmp = cp.with_name(cp.name + ".nova_tmp")
        tmp.write_text(texto, encoding="utf-8")
        os.replace(tmp, cp)
        lp.write_text(texto, encoding="utf-8")

    def resumen(self, frenado: bool) -> dict:
        c = self.c
        estado = ("ALERTA_REVISAR" if c["errores"] or frenado or self.listas["omitidas"] else
                  "BLOQUEADOS" if c["bloqueados"] else "CONFLICTOS" if c["gana_nube"] else "OK")
        r = {"Estado": estado, "Modo": self.modo, "Motor": "nova_sync.py v1", "Timestamp": ahora(),
             "Maquina": socket.gethostname(), "Simulacion": self.simular, "PrimeraVez": self.primera,
             "AlDia": c["al_dia"], "Subidos": c["subidos"], "Bajados": c["bajados"] + c["gana_nube"],
             "Mezclados": c["mezclados"], "Borrados": c["borrados"], "PendientesSubir": c["pend_subir"],
             "PendientesBajar": c["pend_bajar"], "Bloqueados": self.listas["bloqueados"],
             "CopiasLocalesGuardadas": self.listas["copias_locales"], "Errores": self.listas["errores"],
             "CarpetasOmitidas": self.listas["omitidas"], "BorradosFrenados": frenado}
        if not self.simular:
            escribir_json(ESTADO, r)
        return r


# ------------------------------------------------------------------ comandos
def linea(r: dict) -> str:
    t = (f"SYNC {r['Modo']}{' (simulacion)' if r['Simulacion'] else ''}: {r['Estado']} | {r['AlDia']} al dia, "
         f"{r['Subidos']} subidos, {r['Bajados']} bajados, {r['Borrados']} apartados, {r['PendientesSubir']} pendientes de subir")
    if r["Bloqueados"]:
        t += f" | BLOQUEADOS (Drive tiene una version mas nueva: di 'sincroniza' y vuelve a subir): {', '.join(r['Bloqueados'][:5])}"
    if r["CopiasLocalesGuardadas"]:
        t += f" | gano Drive, tu version quedo en: {', '.join(r['CopiasLocalesGuardadas'][:3])}"
    if r["CarpetasOmitidas"]:
        t += f" | no tocadas (faltan o vacias en un lado): {', '.join(r['CarpetasOmitidas'])}"
    if r["Errores"]:
        t += f" | errores: {'; '.join(r['Errores'][:3])}"
    return t


def cargar_config() -> dict | None:
    cfg = leer_json(CONFIG, None)
    if not cfg or not cfg.get("carpeta"):
        return None
    return cfg


def sincronizar(modo: str, simular=False, forzar=False) -> int:
    cfg = cargar_config()
    if not cfg:
        print("[SYNC] Este equipo no tiene Nova Sync configurado. Di 'Nova, configura el sync'.")
        return 2
    nube = Path(cfg["carpeta"])
    if not nube.is_dir():
        print(f"[SYNC] No encuentro la carpeta de Drive ({nube}). Abre Google Drive para escritorio, espera a que "
              "monte la unidad y repite. Este equipo sigue funcionando en local.")
        return 2
    try:
        with Candado():
            r = Motor(modo, nube, simular, forzar).ejecutar()
    except Blindaje as e:
        print(f"[BLINDAJE] {e}. No se hizo nada mas.")
        return 3
    print(linea(r))
    return 0 if r["Estado"] in ("OK", "CONFLICTOS") else 1


def configurar(args: list[str]) -> int:
    print("== Nova Sync: configuracion guiada ==")
    manual = args[args.index("--carpeta") + 1] if "--carpeta" in args else None
    nombre = args[args.index("--nombre") + 1] if "--nombre" in args else "Nova_Sync"
    if not re.fullmatch(r"[\w .-]{1,60}", nombre):
        print("[SYNC] Nombre de carpeta no valido (letras, numeros, espacio, punto, guion).")
        return 2
    if sys.platform.startswith("linux") and not manual:
        print("[SYNC] Google no tiene Drive para escritorio en Linux. Opciones: montar tu Drive con rclone "
              "(https://rclone.org/drive/) y luego: nova_sync.py configurar --carpeta <ruta a Mi unidad montada>.")
        return 2
    if manual:
        mi_unidad = Path(manual).expanduser()
        if not mi_unidad.is_dir():
            print(f"[SYNC] No existe {mi_unidad}.")
            return 2
    else:
        if not drive_instalado() and not buscar_mi_unidad():
            print("[PASO 1/3] Falta Google Drive para escritorio.\n"
                  f"   1. Descargalo de la pagina oficial: {ENLACE_DRIVE}\n"
                  "   2. Instalalo e inicia sesion con tu cuenta de Google.\n"
                  "   3. Espera a que aparezca 'Google Drive' (en Windows una unidad tipo G:, en Mac en el Finder).\n"
                  "   4. Vuelve a decir: 'Nova, configura el sync'.")
            return 2
        unidades = buscar_mi_unidad()
        if not unidades:
            print("[PASO 1/3] Google Drive esta instalado pero no veo la unidad montada. Abre Google Drive para "
                  "escritorio, inicia sesion y espera 1 minuto. Si usas otra ruta: configurar --carpeta <ruta a Mi unidad>.")
            return 2
        if len(unidades) > 1:
            print("[PASO 1/3] Hay varias cuentas de Drive: " + " | ".join(str(u) for u in unidades) +
                  ". Elige una con: configurar --carpeta <ruta>.")
            return 2
        mi_unidad = unidades[0]
    print(f"[PASO 1/3] OK: Google Drive en {mi_unidad}")
    carpeta = mi_unidad / nombre
    existe = carpeta.is_dir()
    if not existe:
        if "--si" not in args:
            print(f"[PASO 2/3] Voy a crear la carpeta '{nombre}' en tu Drive ({carpeta}). "
                  "Si estas de acuerdo, repite con --si ('Nova, si, crea la carpeta').")
            return 4
        carpeta.mkdir(parents=False)
        (carpeta / "LEEME_NOVA_SYNC.txt").write_text(
            "Carpeta de Nova Sync. La gestiona Nova: no muevas ni edites aqui a mano.\n"
            "Cada equipo: 'Nova, sincroniza' (baja) y 'Nova, sube los cambios' (sube).\n", encoding="utf-8")
        print(f"[PASO 2/3] OK: carpeta creada en tu Drive: {carpeta}")
    else:
        print(f"[PASO 2/3] OK: la carpeta '{nombre}' ya existe en tu Drive (otro equipo ya la usa).")
    con_datos = existe and any(p.name not in ("LEEME_NOVA_SYNC.txt", "_papelera") for p in carpeta.iterdir())
    escribir_json(CONFIG, {"carpeta": str(carpeta), "equipo": socket.gethostname(), "configurado": ahora(),
                           "nota": "Archivo de ESTE equipo: no viaja."})
    if con_datos:
        print("[PASO 3/3] La carpeta ya tiene la Nova de otro equipo: dejo ESTE equipo igual que Drive (espejo; "
              "lo distinto se guarda antes en ~/.gemini/antigravity/backups/sync/espejo/).")
        return sincronizar("espejo")
    print("[PASO 3/3] Primer equipo: subo tu Nova a Drive.")
    return sincronizar("subir")


def estado() -> int:
    cfg = cargar_config()
    if not cfg:
        print("[SYNC] No configurado en este equipo. Di 'Nova, configura el sync'.")
        return 2
    r = leer_json(ESTADO, {})
    print(f"[SYNC] Carpeta: {cfg['carpeta']} ({'accesible' if Path(cfg['carpeta']).is_dir() else 'NO accesible ahora'})")
    print("[SYNC] Ultima pasada: " + (linea(r) + f" ({r.get('Timestamp')})" if r else "ninguna"))
    return 0


def desconectar() -> int:
    if CONFIG.exists():
        CONFIG.rename(CONFIG.with_name("nova_sync.desconectado.json"))
    print("[SYNC] Este equipo deja de sincronizar. No se borro nada (ni aqui ni en Drive).")
    return 0


def main() -> int:
    if sys.stdout:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    a = sys.argv[1:]
    cmd = a[0].lower() if a else "estado"
    if cmd in ("bajar", "sincroniza", "sincronizar"):
        return sincronizar("bajar", "--simular" in a)
    if cmd in ("subir", "sube"):
        return sincronizar("subir", "--simular" in a, "--forzar" in a)
    if cmd == "espejo":
        return sincronizar("espejo", "--simular" in a)
    if cmd == "configurar":
        return configurar(a[1:])
    if cmd == "desconectar":
        return desconectar()
    return estado()


if __name__ == "__main__":
    sys.exit(main())
