"""
Orquestador de edicion + linter para Nova (Nova-Core Local - Entrada directa por Chat/CLI).

Principio: Nova controla como se escribe en disco, no el modelo.
- El modelo NO reescribe archivos: edita por reemplazo (texto_viejo -> texto_nuevo).
- Despues de cada edicion o al recibir archivos por el chat se pasa la escalera offline (gratis, sin tokens):
    1. formateador  2. linter con autofix  3. avisos que quedan
  Solo lo que queda en el paso 3 vuelve a Nova en el chat.
- Freno: si un cambio toca mas del LIMITE_CAMBIO del archivo, se rechaza (o pide permiso).
- Cada edicion guarda respaldo en .nova_respaldo/ y se puede deshacer.
- El autofix del linter tambien tiene freno: si toca mas del LIMITE_CAMBIO se deshace, y en carpetas
  protegidas (clones_web, motor_clones o con un archivo .nova_protegido) nunca reescribe, solo informa.
- En el commit (hook, `revisar-staged`) solo mira: lineas cambiadas de lo preparado, bloquea solo errores
  reales (sintaxis, nombres sin definir, no compila); estilo y codigo fosil son avisos. No formatea ni hace git add.

Soporte completo multi-lenguaje:
- Python 3.14 (ruff format + ruff check UP,FURB,SIM,RET)
- JS/TS/React/CSS/JSON (biome check --write)
- Dart 3.13 (dart format + dart fix + dart analyze --format=machine)
- PHP 8.5 (php -l + mago/phpstan si existen)
- Java 21 (javac --release 21 -Xlint:all -proc:none)
- C# 14 (dotnet format --verify-no-changes)

Uso directo con los archivos pasados por el chat (uno o varios archivos/carpetas):
    python orquestador.py revisar archivo1.py [archivo2.ts carpeta/ ...]
    python orquestador.py fragmento archivo.py 10 40
    python orquestador.py editar cambio.json      # {"archivo","texto_viejo","texto_nuevo"}
    python orquestador.py deshacer archivo.py
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LIMITE_CAMBIO = 0.35  # fraccion maxima de lineas que puede tocar una edicion
MIN_LINEAS_FRENO = 20  # en archivos mas cortos el freno no aplica
MAX_VUELTAS = 3  # vueltas modelo <-> linter antes de parar
CARPETA_RESPALDO = ".nova_respaldo"

# Anti-fosil + KISS estructural (SIM y RET fuerzan early return y aplanan condicionales)
PY_OBJETIVO = "py314"
RUFF_CONFIG = Path(__file__).resolve().parent / "pyproject.toml"
RUFF_ANTIFOSIL = [
    "--config",
    str(RUFF_CONFIG),
    "--extend-select",
    "UP,FURB,SIM,RET,TID251",
    "--target-version",
    PY_OBJETIVO,
]
BIOME_CONFIG = Path(__file__).resolve().parent / "biome.json"
SG_CONFIG = Path(__file__).resolve().parent / "sgconfig.yml"
DART_OPCIONES = Path(__file__).resolve().parent / "analysis_options.yaml"

EXT_PYTHON = {".py", ".pyi"}
EXT_BIOME = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".jsonc", ".css"}
EXT_SG = {".py", ".ts", ".tsx"}
EXT_DART = {".dart"}
EXT_PHP = {".php"}
EXT_JAVA = {".java"}
EXT_CSHARP = {".cs"}
EXT_SOPORTADAS = EXT_PYTHON | EXT_BIOME | EXT_DART | EXT_PHP | EXT_JAVA | EXT_CSHARP
IGNORAR_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".dart_tool",
    ".nova_respaldo",
    "vendor",
    ".ruff_cache",
    ".system_generated",
    "salida_docs",
    "clones_web",
    "motor_clones",
}


# ---------- Utilidades ----------


def _ejecutar(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        creationflags=flags,
    )


def _leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write(texto)


def _respaldar(ruta: Path) -> None:
    carpeta = ruta.parent / CARPETA_RESPALDO
    carpeta.mkdir(exist_ok=True)
    shutil.copy2(
        ruta,
        carpeta
        / f"{ruta.name}.{time.strftime('%Y%m%d-%H%M%S')}.{time.time_ns() % 10**6}",
    )


def fraccion_cambiada(antes: str, despues: str) -> float:
    a, d = antes.splitlines(), despues.splitlines()
    iguales = sum(
        b.size
        for b in difflib.SequenceMatcher(
            None, a, d, autojunk=False
        ).get_matching_blocks()
    )
    return 1 - iguales / max(len(a), 1)


def expandir_archivos(rutas: list[str]) -> list[Path]:
    """Recibe uno o varios archivos o carpetas pasados por el chat y devuelve la lista de archivos soportados."""
    salida: list[Path] = []
    for item in rutas:
        p = Path(item).resolve()
        if p.is_dir():
            for sub in sorted(p.rglob("*")):
                if (
                    sub.is_file()
                    and sub.suffix.lower() in EXT_SOPORTADAS
                    and not (set(sub.parts) & IGNORAR_DIRS)
                ):
                    salida.append(sub)
        elif p.is_file():
            salida.append(p)
    return salida


# ---------- Herramientas de edicion ----------


def leer_fragmento(archivo: str, desde: int = 1, hasta: int | None = None) -> dict:
    """Devuelve solo las lineas pedidas, numeradas (para no mandar el archivo entero)."""
    lineas = _leer(Path(archivo)).splitlines()
    hasta = min(hasta or len(lineas), len(lineas))
    desde = max(1, desde)
    texto = "\n".join(f"{n:>5}| {lineas[n - 1]}" for n in range(desde, hasta + 1))
    return {"ok": True, "total_lineas": len(lineas), "fragmento": texto}


def crear_archivo(archivo: str, contenido: str) -> dict:
    """Escritura completa: SOLO para archivos que no existen."""
    ruta = Path(archivo)
    if ruta.exists():
        return {
            "ok": False,
            "error": "El archivo ya existe. Usa editar_archivo con texto_viejo/texto_nuevo.",
        }
    _escribir(ruta, contenido)
    return {"ok": True, "creado": str(ruta), **revisar(archivo)}


def editar_archivo(
    archivo: str, texto_viejo: str, texto_nuevo: str, permitir_grande: bool = False
) -> dict:
    """Edicion por reemplazo: texto_viejo debe aparecer exactamente una vez."""
    ruta = Path(archivo)
    if not ruta.exists():
        return {
            "ok": False,
            "error": "El archivo no existe. Para uno nuevo usa crear_archivo.",
        }
    if not texto_viejo:
        return {
            "ok": False,
            "error": "texto_viejo vacio: indica el texto exacto a reemplazar.",
        }

    antes = _leer(ruta)
    veces = antes.count(texto_viejo)
    if veces == 0:
        return {
            "ok": False,
            "error": "texto_viejo no aparece en el archivo. Copialo exacto (espacios incluidos); "
            "usa leer_fragmento para verlo.",
        }
    if veces > 1:
        return {
            "ok": False,
            "error": f"texto_viejo aparece {veces} veces. Anade lineas de alrededor para que sea unico.",
        }

    despues = antes.replace(texto_viejo, texto_nuevo, 1)
    n_lineas = antes.count("\n") + 1
    fraccion = fraccion_cambiada(antes, despues)
    if (
        not permitir_grande
        and n_lineas >= MIN_LINEAS_FRENO
        and fraccion > LIMITE_CAMBIO
    ):
        return {
            "ok": False,
            "necesita_permiso": True,
            "error": f"El cambio toca el {fraccion:.0%} del archivo (limite {LIMITE_CAMBIO:.0%}). "
            "Haz cambios mas pequenos o pide permiso al usuario.",
        }

    _respaldar(ruta)
    _escribir(ruta, despues)
    return {"ok": True, "cambiado": f"{fraccion:.0%}", **revisar(archivo)}


def deshacer(archivo: str) -> dict:
    ruta = Path(archivo)
    carpeta = ruta.parent / CARPETA_RESPALDO
    copias = (
        sorted(carpeta.glob(f"{ruta.name}.*"), key=lambda p: p.stat().st_mtime)
        if carpeta.exists()
        else []
    )
    if not copias:
        return {"ok": False, "error": "No hay respaldos de este archivo."}
    shutil.copy2(copias[-1], ruta)
    copias[-1].unlink()
    return {"ok": True, "restaurado_desde": copias[-1].name}


# ---------- Escalera de linter (offline) ----------


def _buscar_biome(desde: Path) -> list[str] | None:
    for carpeta in [desde, *desde.parents]:
        for nombre in ("biome.cmd", "biome"):
            local = carpeta / "node_modules" / ".bin" / nombre
            if local.exists():
                return [str(local)]
    if shutil.which("biome"):
        return [shutil.which("biome")]
    if shutil.which("npx"):
        return [shutil.which("npx"), "--yes", "@biomejs/biome"]
    return None


def _herramienta(nombre: str, *conocidas: Path) -> str | None:
    """Busca en el PATH y, si no esta, en las rutas donde esta instalado en este PC."""
    return shutil.which(nombre) or next((str(p) for p in conocidas if p.exists()), None)


_LOCAL = Path(os.environ.get("LOCALAPPDATA", ""))
RUTAS_PHP = (
    _LOCAL
    / "Microsoft/WinGet/Packages/PHP.PHP.8.5_Microsoft.Winget.Source_8wekyb3d8bbwe/php.exe",
    Path(r"C:\laragon\bin\php\php-8.3.33-Win32-vs16-x64\php.exe"),
)
RUTAS_DART = (Path(r"C:\src\flutter\bin\cache\dart-sdk\bin\dart.exe"),)


def _ruff() -> list[str] | None:
    if shutil.which("ruff"):
        return [shutil.which("ruff")]
    try:
        import ruff  # noqa: F401

        exe = Path(sys.executable)
        py_cli = (
            str(exe.with_name("python.exe"))
            if exe.name.lower() == "pythonw.exe"
            else str(exe)
        )
        return [py_cli, "-m", "ruff"]
    except ImportError:
        return None


def _sg() -> str | None:
    for cmd in ("sg", "ast-grep"):
        hallado = shutil.which(cmd)
        if hallado:
            return hallado
    for carpeta in (
        Path(sys.executable).parent,
        Path(sys.executable).parent / "Scripts",
    ):
        for nombre in ("sg.exe", "ast-grep.exe", "sg", "ast-grep"):
            cand = carpeta / nombre
            if cand.exists():
                return str(cand)
    return None


def _revisar_sg(ruta: Path, autofix: bool = True) -> tuple[str, list[dict]]:
    if ruta.suffix.lower() not in EXT_SG:
        return "", []
    sg_bin = _sg()
    if not sg_bin or not SG_CONFIG.exists():
        return "ast-grep (sg): no instalado, paso omitido", []
    es_app_nextjs = "app" in {p.lower() for p in ruta.parts} and ruta.name.lower() in {
        "page.tsx",
        "layout.tsx",
        "route.ts",
        "page.ts",
        "layout.ts",
    }
    cwd, nombre = ruta.parent, ruta.name
    if autofix:
        _ejecutar([sg_bin, "scan", "-c", str(SG_CONFIG), "--update-all", nombre], cwd)
    r = _ejecutar([sg_bin, "scan", "-c", str(SG_CONFIG), "--json", nombre], cwd)
    try:
        hallazgos = json.loads(r.stdout or "[]")
    except ValueError:
        hallazgos = []
    avisos = [
        {
            "linea": int(h.get("range", {}).get("start", {}).get("line", 0)) + 1,
            "codigo": h.get("ruleId", "ast-grep"),
            "mensaje": h.get("message", "").strip(),
        }
        for h in hallazgos
        if not h.get("ruleId", "").startswith("nextjs15-sync-params") or es_app_nextjs
    ]
    modo = "autofix + scan" if autofix else "scan sin fix"
    return f"ast-grep ({modo}): ok", avisos


def _revisar_python(ruta: Path, autofix: bool = True) -> tuple[list[str], list[dict]]:
    ruff = _ruff()
    if not ruff:
        return ["ruff no instalado (pip install ruff)"], []
    cwd, nombre = ruta.parent, ruta.name
    pasos = []
    paso_sg, avisos_sg = _revisar_sg(ruta, autofix=autofix)
    if paso_sg:
        pasos.append(paso_sg)
    if autofix:
        r = _ejecutar([*ruff, "format", nombre], cwd)
        pasos.append(
            "formato: "
            + ("ok" if r.returncode == 0 else "error de sintaxis, no se pudo formatear")
        )
        _ejecutar([*ruff, "check", *RUFF_ANTIFOSIL, "--fix", "--quiet", nombre], cwd)
        pasos.append("autofix: ok")
    else:
        pasos.append("ruff (solo revision): ok")
    r = _ejecutar(
        [*ruff, "check", *RUFF_ANTIFOSIL, "--output-format=json", nombre], cwd
    )
    avisos = [
        {
            "linea": a["location"]["row"],
            "codigo": a.get("code") or "sintaxis",
            "mensaje": a["message"],
        }
        for a in json.loads(r.stdout or "[]")
    ]
    return pasos, [*avisos_sg, *avisos]


RE_GITHUB = re.compile(
    r"::(?:error|warning|notice) title=([^,]*),file=[^,]*,line=(\d+)[^:]*::(.*)"
)


def _revisar_biome(
    ruta: Path, autofix: bool = True, buscar_desde: Path | None = None
) -> tuple[list[str], list[dict]]:
    # buscar_desde: en el commit se revisa una copia temporal; biome se busca junto al archivo de verdad
    biome = _buscar_biome(buscar_desde or ruta.parent)
    if not biome:
        return ["biome no disponible (instala Node o npm i -D @biomejs/biome)"], []
    cwd, nombre = ruta.parent, ruta.name
    config = [f"--config-path={BIOME_CONFIG}"] if BIOME_CONFIG.exists() else []
    pasos = []
    paso_sg, avisos_sg = _revisar_sg(ruta, autofix=autofix)
    if paso_sg:
        pasos.append(paso_sg)
    if autofix:
        r = _ejecutar([*biome, "check", *config, "--write", nombre], cwd)
        pasos.append(
            "formato + autofix: ok"
            if r.returncode in (0, 1)
            else f"biome fallo: {r.stderr.strip()[:200]}"
        )
    else:
        pasos.append("biome (solo revision): ok")
    r = _ejecutar([*biome, "check", *config, "--reporter=github", nombre], cwd)
    avisos = [
        {"linea": int(m.group(2)), "codigo": m.group(1), "mensaje": m.group(3).strip()}
        for m in RE_GITHUB.finditer(r.stdout)
    ]
    return pasos, [*avisos_sg, *avisos]


def _revisar_dart(ruta: Path) -> tuple[list[str], list[dict]]:
    dart = _herramienta("dart", *RUTAS_DART)
    if not dart:
        return ["dart no disponible"], []
    pasos = []
    propio = any(
        (c / "analysis_options.yaml").exists()
        for c in [ruta.parent, *ruta.parent.parents]
    )
    with tempfile.TemporaryDirectory(prefix="nova_dart_") as tmp:
        if propio or not DART_OPCIONES.exists():
            cwd, nombre = ruta.parent, ruta.name  # el proyecto manda con sus reglas
        else:
            # archivo suelto: se revisa una copia junto a las reglas anti-fosil y se trae el arreglo
            cwd, nombre = Path(tmp), ruta.name
            shutil.copy2(DART_OPCIONES, cwd / "analysis_options.yaml")
            shutil.copy2(ruta, cwd / nombre)
        r = _ejecutar([dart, "format", nombre], cwd)
        pasos.append("dart format: " + ("ok" if r.returncode == 0 else "fallo formato"))
        _ejecutar([dart, "fix", "--apply", "."], cwd)
        pasos.append(
            "dart fix: ok" + ("" if propio else " (reglas anti-fosil de nova_core)")
        )
        r = _ejecutar([dart, "analyze", "--format=machine", nombre], cwd)
        if cwd != ruta.parent:
            shutil.copy2(cwd / nombre, ruta)
    avisos = []
    for line in (r.stdout + "\n" + r.stderr).splitlines():
        parts = line.split("|")
        if len(parts) >= 8:
            avisos.append(
                {
                    "linea": int(parts[4]) if parts[4].isdigit() else 1,
                    "codigo": parts[2],
                    "mensaje": "|".join(parts[7:]).strip(),
                    "severidad": "error" if parts[0].upper() == "ERROR" else "aviso",
                }
            )
    return pasos, avisos


def _revisar_php(ruta: Path) -> tuple[list[str], list[dict]]:
    php = _herramienta("php", *RUTAS_PHP)
    if not php:
        return ["php no disponible"], []
    cwd, nombre = ruta.parent, ruta.name
    pasos = []
    avisos = []
    r = _ejecutar([php, "-l", nombre], cwd)
    if r.returncode != 0:
        out = (r.stdout + " " + r.stderr).strip()
        m = re.search(r"on line (\d+)", out)
        linea = int(m.group(1)) if m else 1
        avisos.append(
            {"linea": linea, "codigo": "php-syntax", "mensaje": out, "severidad": "error"}
        )
        return ["php -l: error de sintaxis"], avisos
    pasos.append("php -l: ok")
    phpstan = shutil.which("phpstan")
    if phpstan:
        r2 = _ejecutar(
            [phpstan, "analyse", "--error-format=json", "--no-progress", nombre], cwd
        )
        try:
            data = json.loads(r2.stdout or "{}")
            for f_data in data.get("files", {}).values():
                for msg in f_data.get("messages", []):
                    avisos.append(
                        {
                            "linea": msg.get("line", 1),
                            "codigo": "phpstan",
                            "mensaje": msg.get("message", ""),
                        }
                    )
            pasos.append("phpstan: ok")
        except ValueError:
            avisos.append(
                {
                    "linea": 1,
                    "codigo": "phpstan",
                    "mensaje": "salida JSON invalida de phpstan",
                }
            )
    return pasos, avisos


def _revisar_java(ruta: Path) -> tuple[list[str], list[dict]]:
    javac = shutil.which("javac")
    if not javac:
        return ["javac no disponible en PATH"], []
    cwd, nombre = ruta.parent, ruta.name
    # los .class van a una carpeta temporal para no ensuciar el proyecto
    with tempfile.TemporaryDirectory(prefix="nova_javac_") as clases:
        r = _ejecutar(
            [
                javac,
                "--release",
                "21",
                "-Xlint:all",
                "-proc:none",
                "-encoding",
                "UTF-8",
                "-sourcepath",
                str(cwd),
                "-d",
                clases,
                nombre,
            ],
            cwd,
        )
    avisos = []
    re_javac = re.compile(
        r"^.*?:(\d+):\s*(error|warning):\s*(?:\[([^\]]+)\]\s*)?(.*)$"
    )
    for line in (r.stderr + "\n" + r.stdout).splitlines():
        m = re_javac.match(line.strip())
        if m:
            avisos.append(
                {
                    "linea": int(m.group(1)),
                    "codigo": m.group(3) or "javac21",
                    "mensaje": m.group(4).strip(),
                    "severidad": "error" if m.group(2) == "error" else "aviso",
                }
            )
    return ["javac 21 -Xlint:all: ok" if not avisos else "javac 21: con avisos"], avisos


def _revisar_csharp(ruta: Path) -> tuple[list[str], list[dict]]:
    dotnet = shutil.which("dotnet")
    if not dotnet:
        return ["dotnet no disponible en PATH"], []
    # dotnet format necesita un proyecto: se busca el .csproj mas cercano hacia arriba
    proyecto = next(
        (p for c in [ruta.parent, *ruta.parent.parents] for p in c.glob("*.csproj")),
        None,
    )
    if not proyecto:
        return ["dotnet format: sin .csproj cerca, no se pudo revisar"], []
    cwd, nombre = proyecto.parent, str(ruta.relative_to(proyecto.parent))
    _ejecutar(
        [dotnet, "format", str(proyecto), "--include", nombre], cwd
    )  # aplica lo que puede arreglar
    r = _ejecutar(
        [
            dotnet,
            "format",
            str(proyecto),
            "--include",
            nombre,
            "--verify-no-changes",
            "--severity",
            "info",
        ],
        cwd,
    )
    avisos = []
    re_cs = re.compile(r"^.*?\((\d+),\d+\):\s*(error|warning)\s+([A-Z0-9]+):\s*(.*)$")
    for line in (r.stdout + "\n" + r.stderr).splitlines():
        m = re_cs.match(line.strip())
        if m:
            avisos.append(
                {
                    "linea": int(m.group(1)),
                    "codigo": m.group(3),
                    "mensaje": m.group(4).strip(),
                    "severidad": "error" if m.group(2) == "error" else "aviso",
                }
            )
    return [
        "dotnet format: ok" if r.returncode == 0 else "dotnet format: revisado"
    ], avisos


# Carpetas donde el linter NUNCA reescribe (solo informa): el motor del clonador ya se rompió una vez así.
# Más carpetas: un archivo vacío .nova_protegido en la raíz de cualquier proyecto.
PROTEGIDAS = {"clones_web", "motor_clones"}
MARCA_PROTEGIDO = ".nova_protegido"


def es_protegido(ruta: Path) -> bool:
    ruta = ruta.resolve()
    return bool(set(ruta.parts) & PROTEGIDAS) or any(
        (c / MARCA_PROTEGIDO).exists() for c in ruta.parents
    )


# Lo que BLOQUEA (rompe el programa). Todo lo demás —estilo, código fósil, sugerencias— es aviso.
#  ruff: E9xx sintaxis/IO, F63x comparaciones rotas, F7xx break/return fuera de sitio, F82x nombres sin definir
RE_RUFF_ERROR = re.compile(r"^(E9\d\d|F63\d|F7\d\d|F82\d)$")
BIOME_ERROR = (
    "noUndeclaredVariables",
    "noConstAssign",
    "noInvalidUseBeforeDeclaration",
    "noUnreachableSuper",
    "noSelfAssign",
)


def severidad(aviso: dict, ext: str) -> str:
    """'error' (bloquea un commit) o 'aviso' (se enseña y se deja pasar)."""
    if aviso.get("severidad"):
        return aviso["severidad"]
    codigo = str(aviso.get("codigo") or "")
    if codigo in ("sintaxis", "php-syntax"):
        return "error"
    if ext in EXT_PYTHON:
        return "error" if RE_RUFF_ERROR.match(codigo) else "aviso"
    if ext in EXT_BIOME:
        return "error" if codigo.startswith("parse") or codigo.endswith(BIOME_ERROR) else "aviso"
    return "aviso"


def revisar(archivo: str, autofix: bool = True) -> dict:
    """Escalera offline sobre UN archivo. Devuelve solo lo que el modelo tiene que arreglar.

    El autofix tiene freno: en carpetas protegidas no se aplica, y si el formateo + arreglos tocan más del
    LIMITE_CAMBIO de un archivo (reescribir un archivo antiguo entero), se deshace y solo se informa."""
    ruta = Path(archivo).resolve()
    ext = ruta.suffix.lower()
    notas = []
    if autofix and es_protegido(ruta):
        autofix = False
        notas.append("carpeta protegida: solo revision, sin autofix")
    antes_bytes = ruta.read_bytes() if autofix and ruta.is_file() else None  # bytes: se restaura EXACTO (CRLF incluido)
    antes = antes_bytes.decode("utf-8", errors="replace") if antes_bytes is not None else None
    pasos, avisos = _escalera(ruta, ext, autofix)
    if pasos is None:
        return {
            "archivo": str(ruta),
            "linter": "sin linter para este tipo de archivo",
            "avisos": [],
            "limpio": True,
        }
    if antes is not None:
        despues = _leer(ruta)
        fraccion = fraccion_cambiada(antes, despues)
        if antes.count("\n") + 1 >= MIN_LINEAS_FRENO and fraccion > LIMITE_CAMBIO:
            ruta.write_bytes(antes_bytes)  # se deja como estaba, byte a byte
            pasos, avisos = _escalera(ruta, ext, False)
            notas.append(
                f"autofix DESHECHO: tocaba el {fraccion:.0%} del archivo (limite {LIMITE_CAMBIO:.0%}); "
                "arreglalo por partes con editar_archivo"
            )
        elif despues != antes:
            _respaldar_bytes(ruta, antes_bytes)  # el autofix cambió algo: se puede deshacer
    for a in avisos:
        a["severidad"] = severidad(a, ext)
    resultado_rev = {
        "archivo": str(ruta),
        "linter": [*notas, *pasos],
        "avisos": avisos,
        "limpio": not avisos,
    }
    _guardar_ultimo_lint(resultado_rev)
    return resultado_rev


def _respaldar_bytes(ruta: Path, datos: bytes) -> None:
    carpeta = ruta.parent / CARPETA_RESPALDO
    carpeta.mkdir(exist_ok=True)
    (carpeta / f"{ruta.name}.{time.strftime('%Y%m%d-%H%M%S')}.{time.time_ns() % 10**6}").write_bytes(datos)


def _escalera(ruta: Path, ext: str, autofix: bool) -> tuple[list[str] | None, list[dict]]:
    """Linter de cada lenguaje. dart y dotnet format siempre corrigen: sin autofix, no se ejecutan sus arreglos."""
    if ext in EXT_PYTHON:
        return _revisar_python(ruta, autofix=autofix)
    if ext in EXT_BIOME:
        return _revisar_biome(ruta, autofix=autofix)
    if ext in EXT_DART:
        return _revisar_dart(ruta) if autofix else _analizar_dart(ruta)
    if ext in EXT_PHP:
        return _revisar_php(ruta)
    if ext in EXT_JAVA:
        return _revisar_java(ruta)
    if ext in EXT_CSHARP:
        return _revisar_csharp(ruta) if autofix else (["dotnet format: omitido (sin autofix)"], [])
    return None, []


def _analizar_dart(ruta: Path) -> tuple[list[str], list[dict]]:
    """dart analyze sin format ni fix: no toca el archivo."""
    dart = _herramienta("dart", *RUTAS_DART)
    if not dart:
        return ["dart no disponible"], []
    r = _ejecutar([dart, "analyze", "--format=machine", ruta.name], ruta.parent)
    avisos = []
    for line in (r.stdout + "\n" + r.stderr).splitlines():
        parts = line.split("|")
        if len(parts) >= 8:
            avisos.append(
                {
                    "linea": int(parts[4]) if parts[4].isdigit() else 1,
                    "codigo": parts[2],
                    "mensaje": "|".join(parts[7:]).strip(),
                    "severidad": "error" if parts[0].upper() == "ERROR" else "aviso",
                }
            )
    return ["dart analyze (solo revision): ok"], avisos


ESTADO_LINT_JSON = Path(__file__).resolve().parent / ".estado_lint.json"


def _cargar_mapa_lint() -> dict[str, dict]:
    if not ESTADO_LINT_JSON.exists():
        return {}
    try:
        datos = json.loads(_leer(ESTADO_LINT_JSON))
        return {
            k: v
            for k, v in datos.items()
            if Path(k).exists() and not (set(Path(k).parts) & IGNORAR_DIRS)
        }
    except ValueError:
        return {}


def _guardar_ultimo_lint(res: dict) -> None:
    mapa = _cargar_mapa_lint()
    archivo = str(Path(res.get("archivo", "")).resolve())
    if res.get("limpio", True):
        mapa.pop(archivo, None)
    else:
        mapa[archivo] = {
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pasos": res.get("linter", []),
            "avisos": res.get("avisos", []),
        }
    _escribir(ESTADO_LINT_JSON, json.dumps(mapa, ensure_ascii=False, indent=1))

    estado_global = (
        "LIMPIO" if not mapa else f"CON_AVISOS ({len(mapa)} archivos pendientes)"
    )
    lineas = [
        "# Ultimo Lint (Nova-Core Vigia - Estado por Archivo)",
        f"- **Actualizado:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Estado Global:** `{estado_global}`",
        f"- **Ultimo archivo revisado:** `{archivo}` (`{'LIMPIO' if res.get('limpio', True) else 'CON_AVISOS'}`)",
        "",
    ]
    if not mapa:
        lineas.extend(
            ["## Archivos con Avisos Pendientes", "Ninguno. Todo limpio.", ""]
        )
    else:
        lineas.append("## Archivos con Avisos Pendientes")
        for ruta_pend, info in mapa.items():
            lineas.append(f"### `{ruta_pend}` ({info.get('fecha', '')})")
            for a in info.get("avisos", [])[:20]:
                lineas.append(f"- linea {a['linea']}: [{a['codigo']}] {a['mensaje']}")
            lineas.append("")

    contenido = "\n".join(lineas)
    for destino in (
        Path(__file__).resolve().parent / "ultimo_lint.md",
        Path.home() / ".gemini" / "antigravity" / "memory" / "registros" / "ultimo_lint.md",
    ):
        if destino.parent.exists():
            _escribir(destino, contenido)


def revisar_lote(rutas: list[str], autofix: bool = True) -> dict:
    """Revisa uno o varios archivos o carpetas pasados por el chat en una sola llamada."""
    archivos = expandir_archivos(rutas)
    if not archivos:
        return {
            "ok": False,
            "error": "No se encontraron archivos soportados en las rutas indicadas.",
            "resultados": [],
        }
    resultados = [revisar(str(a), autofix=autofix) for a in archivos]
    limpios = sum(1 for r in resultados if r["limpio"])
    return {
        "ok": True,
        "total_archivos": len(resultados),
        "limpios": limpios,
        "con_avisos": len(resultados) - limpios,
        "resultados": resultados,
    }


def avisos_para_modelo(resultado: dict) -> str:
    """Texto corto para devolver a Nova en el chat."""
    if not resultado.get("ok", True):
        return "ERROR: " + resultado["error"]
    if "resultados" in resultado:
        partes = []
        for r in resultado["resultados"]:
            nombre = Path(r["archivo"]).name
            if r["limpio"]:
                partes.append(
                    f"[OK] {nombre}: limpio ({', '.join(r['linter']) if isinstance(r['linter'], list) else r['linter']})"
                )
            else:
                lineas = [
                    f"  linea {a['linea']}: [{a['codigo']}] {a['mensaje']}"
                    for a in r["avisos"][:20]
                ]
                partes.append(f"[AVISOS] {nombre}:\n" + "\n".join(lineas))
        return "\n".join(partes)
    avisos = resultado.get("avisos", [])
    if not avisos:
        return "OK. Archivo limpio."
    lineas = [
        f"linea {a['linea']}: [{a['codigo']}] {a['mensaje']}" for a in avisos[:20]
    ]
    extra = f"\n(+{len(avisos) - 20} avisos mas)" if len(avisos) > 20 else ""
    return (
        "Editado, pero quedan avisos. Corrigelos con ediciones pequenas:\n"
        + "\n".join(lineas)
        + extra
    )


# ---------- Aduana del commit (hook pre-commit) ----------
#
# En el commit SOLO SE MIRA, no se toca nada:
#  - se revisa lo que entra en el commit: la versión preparada (git show :archivo), no la del disco;
#  - solo cuentan las líneas añadidas o cambiadas en este commit (lo antiguo no bloquea);
#  - bloquea solo lo que rompe (sintaxis, nombres sin definir, no compila); estilo y código fósil = aviso;
#  - no formatea ni hace git add (antes se colaban en el commit cambios que no estaban preparados).
# Para formatear / modernizar: `orquestador.py revisar archivo` (con el freno del 35 %).

RE_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _git(args: list[str], cwd: Path) -> str:
    return _ejecutar(["git", *args], cwd).stdout


def _lineas_cambiadas(raiz: Path, archivo: str) -> set[int]:
    """Números de línea (en la versión preparada) añadidos o cambiados en este commit."""
    lineas: set[int] = set()
    for linea in _git(["diff", "--cached", "-U0", "--no-color", "--", archivo], raiz).splitlines():
        m = RE_HUNK.match(linea)
        if m:
            inicio, cuantas = int(m.group(1)), int(m.group(2) or 1)
            lineas.update(range(inicio, inicio + cuantas))
    return lineas


def _revisar_preparado(raiz: Path, archivo: str) -> tuple[list[str], list[dict]]:
    """Linter de la versión PREPARADA del archivo, sin escribir nada en el proyecto."""
    real = raiz / archivo
    ext = real.suffix.lower()
    if ext in EXT_PYTHON | EXT_BIOME | EXT_PHP:
        contenido = _ejecutar(["git", "show", f":{archivo}"], raiz).stdout
        with tempfile.TemporaryDirectory(prefix="nova_commit_") as tmp:
            copia = Path(tmp) / real.name
            _escribir(copia, contenido)
            if ext in EXT_PYTHON:
                return _revisar_python(copia, autofix=False)
            if ext in EXT_BIOME:
                return _revisar_biome(copia, autofix=False, buscar_desde=real.parent)
            return _revisar_php(copia)
    # java / dart / c#: necesitan el proyecto alrededor; se revisa el archivo del disco sin tocarlo
    pasos, avisos = _escalera(real, ext, autofix=False)
    if _git(["diff", "--name-only", "--", archivo], raiz).strip():
        pasos = [*(pasos or []), "ojo: el archivo tiene cambios sin preparar; se reviso la version del disco"]
    return pasos or [], avisos


def revisar_commit() -> int:
    raiz = Path(_git(["rev-parse", "--show-toplevel"], Path.cwd()).strip() or Path.cwd())
    preparados = [
        f.strip()
        for f in _git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], raiz).splitlines()
        if f.strip() and Path(f.strip()).suffix.lower() in EXT_SOPORTADAS
    ]
    if not preparados:
        print("[OK] Sin archivos de codigo en el commit.")
        return 0
    errores, avisos, antiguos = [], [], 0
    for archivo in preparados:
        cambiadas = _lineas_cambiadas(raiz, archivo)
        if not cambiadas:
            continue
        _, encontrados = _revisar_preparado(raiz, archivo)
        ext = Path(archivo).suffix.lower()
        for a in encontrados:
            if a["linea"] not in cambiadas:
                antiguos += 1
                continue
            a["severidad"] = severidad(a, ext)
            (errores if a["severidad"] == "error" else avisos).append((archivo, a))

    def lista(cosas):
        return "\n".join(f"  {f}:{a['linea']} [{a['codigo']}] {a['mensaje']}" for f, a in cosas[:30])

    print(f"[NOVA LINT] {len(preparados)} archivos de codigo en el commit: "
          f"{len(errores)} errores, {len(avisos)} avisos en las lineas cambiadas"
          + (f" ({antiguos} avisos de codigo antiguo ignorados)" if antiguos else ""))
    if avisos:
        print("Avisos (no bloquean; arreglalos cuando puedas):\n" + lista(avisos))
    if errores:
        print("ERRORES (bloquean el commit):\n" + lista(errores))
        return 1
    return 0


# ---------- CLI ----------


def main():
    if len(sys.argv) < 2 or (sys.argv[1] != "revisar-staged" and len(sys.argv) < 3):
        print(__doc__)
        sys.exit(2)
    orden = sys.argv[1]
    if orden == "revisar":
        rutas = sys.argv[2:]
        res = (
            revisar(rutas[0])
            if len(rutas) == 1 and Path(rutas[0]).is_file()
            else revisar_lote(rutas)
        )
    elif orden == "revisar-sin-fix":
        rutas = sys.argv[2:]
        res = (
            revisar(rutas[0], autofix=False)
            if len(rutas) == 1 and Path(rutas[0]).is_file()
            else revisar_lote(rutas, autofix=False)
        )
    elif orden == "revisar-texto":
        rutas = sys.argv[2:]
        res = (
            revisar(rutas[0])
            if len(rutas) == 1 and Path(rutas[0]).is_file()
            else revisar_lote(rutas)
        )
        print(avisos_para_modelo(res))
        return
    elif orden == "revisar-staged":
        sys.exit(revisar_commit())  # hook pre-commit: solo mira (ver «Aduana del commit»)
    elif orden == "fragmento":
        archivo = sys.argv[2]
        desde = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        hasta = int(sys.argv[4]) if len(sys.argv) > 4 else None
        res = leer_fragmento(archivo, desde, hasta)
    elif orden == "editar":
        archivo = sys.argv[2]
        res = editar_archivo(**json.loads(Path(archivo).read_text(encoding="utf-8")))
    elif orden == "deshacer":
        archivo = sys.argv[2]
        res = deshacer(archivo)
    else:
        print(__doc__)
        sys.exit(2)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
