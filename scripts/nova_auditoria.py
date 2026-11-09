"""
NOVA AUDITORIA - auditoria de seguridad de SOLO LECTURA, con pruebas (0 tokens de nube)

    python nova_auditoria.py <carpeta del proyecto> [--salida informe.md]

Por que: las auditorias de Nova decian "todo listo, 0 vulnerabilidades" porque el proyecto compilaba; Claude
encontro ~20 problemas en el mismo codigo. "Compila" no es "auditado". Este script mira el codigo de verdad y cada
hallazgo sale con archivo:linea y la linea como prueba. Nova parte de este informe, lo revisa y lo amplia; no
puede decir "0 hallazgos" sin haberlo pasado.

Capas (las 5 de index-security-deploy):
  1. Entradas e inyecciones   (SQL con datos de la peticion, eval, innerHTML sin escapar, exec con shell...)
  2. Autenticacion y secretos (claves en el codigo, JWT sin caducidad, contrasenas en claro, .env en git)
  3. Autorizacion             (service_role en el cliente; tablas sin RLS si el proyecto usa Supabase)
  4. Cabeceras y CORS         (CORS abierto, Express sin helmet, cookies sin flags)
  5. Logica y abuso           (login sin limite de intentos, DEBUG activo, TLS sin verificar)
  + Dependencias (npm audit / pip-audit). Lo que no se pudo revisar se dice: no cuenta como limpio.
No toca nada del proyecto: solo lee y escribe el informe en <carpeta>/nova_auditoria/.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

IGNORAR = {"node_modules", ".git", "dist", "build", ".next", "__pycache__", ".venv", "venv", "vendor", "coverage",
           "nova_tareas", "nova_auditoria", ".nova_respaldo"}
CODIGO = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".php", ".java", ".kt", ".cs", ".go", ".rb", ".vue", ".svelte"}
WEB = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".html"}
EXT = CODIGO | {".sql", ".html", ".env", ".json", ".yml", ".yaml", ".toml"}

SQL = r"(?i)\b(select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from)\b"
DATO_USUARIO = r"(req|request|params|body|query|input)\b"

# (capa, severidad, que, patron, arreglo, extensiones o None = todas)
REGLAS = [
    (1, "ALTA", "SQL con datos de la peticion (inyeccion)",
     SQL + r"[^\n;]{0,160}(\$\{[^}]*" + DATO_USUARIO + r"|[\"'`]\s*\+\s*" + DATO_USUARIO + r"|%s[\"']\s*%|\.format\()",
     "consultas parametrizadas (?, $1, :nombre) o el ORM", CODIGO),
    (1, "MEDIA", "SQL armado con variables (revisar de donde vienen)",
     SQL + r"[^\n;]{0,160}(\$\{|[\"'`]\s*\+\s*\w)",
     "si la variable sale del usuario, parametrizar; si son constantes (columnas, '?,?'), dejarlo anotado", CODIGO),
    (1, "ALTA", "eval / new Function", r"\beval\s*\(|new\s+Function\s*\(", "quitar eval: parsear o mapear", CODIGO | {".html"}),
    (1, "MEDIA", "HTML sin escapar (XSS)",
     r"(?i)^(?!.*(esc\w*\(|sanitiz|dompurify|escape)).*(\.innerHTML\s*\+?=\s*[^;'\"]*(\$\{|\+\s*\w)|dangerouslySetInnerHTML|v-html=|\|\s*safe\b)",
     "textContent, escapar (escHtml) o sanitizar (DOMPurify)", WEB),
    (1, "ALTA", "comando de sistema con shell", r"shell\s*=\s*True|\bexec\s*\(\s*`|\bos\.system\(",
     "subprocess / execFile con lista de argumentos y sin shell", CODIGO),
    (1, "ALTA", "deserializacion insegura", r"pickle\.loads?\(|yaml\.load\((?![^)]*SafeLoader)|unserialize\(",
     "formatos seguros (json) o loaders seguros", CODIGO),
    (2, "ALTA", "secreto escrito en el codigo",
     r"sk-(?:or-|proj-|ant-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|"
     r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----",
     "mover a .env (fuera de git) y CAMBIAR la clave: ya esta expuesta", None),
    (2, "ALTA", "contrasena o clave asignada en el codigo",
     r"(?i)\b(password|passwd|pwd|secret|api_?key|token)\b\s*[:=]\s*['\"][^'\"\s]{6,}['\"]",
     "leer de variables de entorno", CODIGO),
    (2, "MEDIA", "JWT sin caducidad", r"jwt\.sign\((?![^)]*expiresIn)[^)]*\)", "anadir expiresIn", CODIGO),
    (2, "MEDIA", "hash debil para contrasenas", r"(?i)\b(md5|sha1)\s*\(", "bcrypt / argon2", CODIGO),
    (3, "ALTA", "service_role de Supabase en el cliente", r"(?i)service_role",
     "solo en el servidor; en el cliente la anon key + RLS", {".jsx", ".tsx", ".vue", ".svelte", ".html"}),
    (4, "MEDIA", "CORS abierto a cualquiera",
     r"origin\s*:\s*(['\"]\*['\"]|true)\b|Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*", "lista de origenes permitidos", CODIGO),
    (4, "MEDIA", "cookie sin httpOnly", r"res\.cookie\((?![^)]*httpOnly)[^)]*\)", "httpOnly, secure y sameSite", CODIGO),
    (5, "MEDIA", "modo DEBUG activo", r"(?i)\bDEBUG\s*=\s*True\b|app\.run\([^)]*debug\s*=\s*True", "DEBUG solo en local", CODIGO),
    (5, "MEDIA", "verificacion TLS desactivada", r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED",
     "no desactivar la verificacion de certificados", CODIGO),
]
REVISADO: list[str] = []  # lo que se ejecuto de verdad (para que "sin hallazgos" no sea ambiguo)
NOMBRES_CAPA = {0: "Dependencias", 1: "Entradas e inyecciones", 2: "Autenticacion y secretos", 3: "Autorizacion",
                4: "Cabeceras y CORS", 5: "Logica y abuso"}


def archivos(carpeta: Path):
    for p in carpeta.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXT and not (set(p.relative_to(carpeta).parts) & IGNORAR):
            if p.stat().st_size < 1_500_000:
                yield p


def tapar(linea: str) -> str:
    return re.sub(r"(sk-|AIza|gh[pousr]_|AKIA)[A-Za-z0-9_-]{6,}", r"\1****", linea.strip())[:160]


def buscar_patrones(carpeta: Path) -> list[dict]:
    reglas = [(c, s, q, re.compile(p), a, e) for c, s, q, p, a, e in REGLAS]
    hallazgos = []
    for p in archivos(carpeta):
        try:
            lineas = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for n, linea in enumerate(lineas, 1):
            if linea.strip().startswith(("#", "//", "*", "--")):
                continue
            for capa, sev, que, r, arreglo, exts in reglas:
                if exts and p.suffix.lower() not in exts:
                    continue
                if r.search(linea):
                    hallazgos.append({"capa": capa, "sev": sev, "que": que, "donde": f"{p.relative_to(carpeta)}:{n}",
                                      "prueba": tapar(linea), "arreglo": arreglo})
                    if sev == "ALTA" and "SQL" in que:
                        break  # la misma linea no sale dos veces (ALTA y "revisar")
    return hallazgos


def revisar_estructura(carpeta: Path) -> list[dict]:
    """Lo que no es una linea concreta: .env en git, librerias de seguridad que faltan, tablas sin RLS."""
    h = []
    gi_ruta = carpeta / ".gitignore"
    gi = gi_ruta.read_text(encoding="utf-8", errors="ignore") if gi_ruta.exists() else ""
    if [e for e in carpeta.glob(".env*") if not e.name.endswith((".example", ".sample"))] and ".env" not in gi:
        h.append({"capa": 2, "sev": "ALTA", "que": ".env sin estar en .gitignore", "donde": ".gitignore",
                  "prueba": "hay archivos .env y .gitignore no los excluye", "arreglo": "anadir .env* a .gitignore"})
    if (carpeta / ".git").exists() and shutil.which("git"):
        r = subprocess.run(["git", "ls-files", ".env", ".env.*", "*/.env"], cwd=carpeta, capture_output=True, text=True)
        for f in r.stdout.split():
            if not f.endswith((".example", ".sample")):
                h.append({"capa": 2, "sev": "ALTA", "que": ".env versionado en git", "donde": f,
                          "prueba": f"git ls-files lo lista: {f}", "arreglo": "git rm --cached + cambiar las claves"})
    for pkg in [p for p in carpeta.rglob("package.json") if not (set(p.relative_to(carpeta).parts) & IGNORAR)]:
        try:
            deps = json.loads(pkg.read_text(encoding="utf-8", errors="ignore") or "{}")
        except ValueError:
            continue
        todas = {**deps.get("dependencies", {}), **deps.get("devDependencies", {})}
        raiz = pkg.parent
        codigo = " ".join(p.read_text(encoding="utf-8", errors="ignore") for p in archivos(raiz) if p.suffix in (".js", ".ts", ".mjs", ".cjs"))
        donde = str(pkg.relative_to(carpeta))
        if "express" in todas and "helmet" not in todas and "helmet" not in codigo:
            h.append({"capa": 4, "sev": "MEDIA", "que": "Express sin helmet (cabeceras/CSP)", "donde": donde,
                      "prueba": "express en dependencias, helmet no", "arreglo": "app.use(helmet()) con CSP"})
        if re.search(r"(?i)['\"]/[\w/-]*(login|signin|auth)", codigo) and not any(
            k in todas for k in ("express-rate-limit", "rate-limiter-flexible", "@upstash/ratelimit")
        ) and not re.search(r"(?i)rate.?limit|intentos", codigo):
            h.append({"capa": 5, "sev": "MEDIA", "que": "login sin limite de intentos", "donde": donde,
                      "prueba": "hay rutas de login y ningun limitador de intentos", "arreglo": "express-rate-limit en auth"})
    # RLS solo tiene sentido con Supabase (con un servidor propio la autorizacion va en el codigo)
    usa_supabase = any(
        "supabase" in p.read_text(encoding="utf-8", errors="ignore").lower()
        for p in carpeta.rglob("package.json") if not (set(p.relative_to(carpeta).parts) & IGNORAR)
    )
    for sql in (carpeta.rglob("*.sql") if usa_supabase else []):
        if set(sql.relative_to(carpeta).parts) & IGNORAR:
            continue
        t = sql.read_text(encoding="utf-8", errors="ignore")
        for tabla in re.findall(r"(?i)create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)", t):
            nombre = tabla.strip('"').split(".")[-1]
            if not re.search(rf"(?i)alter\s+table\s+[\w.\"]*{re.escape(nombre)}\"?\s+enable\s+row\s+level\s+security", t):
                h.append({"capa": 3, "sev": "ALTA", "que": "tabla sin RLS (Supabase)", "donde": str(sql.relative_to(carpeta)),
                          "prueba": f"create table {nombre} sin enable row level security", "arreglo": "ENABLE RLS + politicas por usuario"})
    return h


def dependencias(carpeta: Path) -> tuple[list[dict], list[str]]:
    h, notas = [], []
    for pkg in [p for p in carpeta.rglob("package.json") if not (set(p.relative_to(carpeta).parts) & IGNORAR)]:
        raiz, donde = pkg.parent, str(pkg.relative_to(carpeta))
        if not shutil.which("npm"):
            notas.append(f"{donde}: npm no instalado, dependencias SIN revisar")
            continue
        if not ((raiz / "package-lock.json").exists() or (raiz / "node_modules").exists()):
            notas.append(f"{donde}: sin package-lock.json ni node_modules, npm audit no puede revisar (npm install)")
            continue
        r = subprocess.run("npm audit --json", cwd=raiz, capture_output=True, text=True, shell=True, timeout=180,
                           encoding="utf-8", errors="replace")
        try:
            datos = json.loads(r.stdout or "{}")
            cuenta = (datos.get("metadata") or {}).get("vulnerabilities") or {}
            REVISADO.append(f"{donde}: npm audit ejecutado (criticas {cuenta.get('critical', 0)}, altas {cuenta.get('high', 0)}, "
                            f"moderadas {cuenta.get('moderate', 0)}, bajas {cuenta.get('low', 0)})")
            for nombre, v in (datos.get("vulnerabilities") or {}).items():
                if v.get("severity") in ("high", "critical"):
                    h.append({"capa": 0, "sev": "CRITICA" if v["severity"] == "critical" else "ALTA",
                              "que": f"dependencia vulnerable: {nombre}", "donde": donde,
                              "prueba": f"npm audit: {v['severity']} ({v.get('range', '')})", "arreglo": "npm audit fix / actualizar"})
        except ValueError:
            notas.append(f"{donde}: npm audit no devolvio JSON valido")
    for req in [p for p in carpeta.rglob("requirements.txt") if not (set(p.relative_to(carpeta).parts) & IGNORAR)]:
        donde = str(req.relative_to(carpeta))
        if not shutil.which("pip-audit"):
            notas.append(f"{donde}: pip-audit no instalado (pip install pip-audit), dependencias de Python SIN revisar")
            continue
        r = subprocess.run(["pip-audit", "-r", str(req), "-f", "json"], capture_output=True, text=True, timeout=300)
        REVISADO.append(f"{donde}: pip-audit ejecutado")
        try:
            for d in json.loads(r.stdout or "{}").get("dependencies", []):
                for v in d.get("vulns", []):
                    h.append({"capa": 0, "sev": "ALTA", "que": f"dependencia vulnerable: {d['name']} {d.get('version', '')}",
                              "donde": donde, "prueba": v.get("id", ""),
                              "arreglo": f"actualizar a {', '.join(v.get('fix_versions', [])) or 'version corregida'}"})
        except ValueError:
            notas.append(f"{donde}: pip-audit no devolvio JSON valido")
    return h, notas


def main() -> int:
    ap = argparse.ArgumentParser(description="Auditoria de seguridad de solo lectura con pruebas")
    ap.add_argument("carpeta")
    ap.add_argument("--salida", default="")
    args = ap.parse_args()
    carpeta = Path(args.carpeta).resolve()
    if not carpeta.is_dir():
        print(f"[AUDITORIA] No existe {carpeta}")
        return 2
    revisados = sum(1 for _ in archivos(carpeta))
    hallazgos = buscar_patrones(carpeta) + revisar_estructura(carpeta)
    deps, notas = dependencias(carpeta)
    hallazgos += deps
    orden = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2}
    hallazgos.sort(key=lambda x: (orden.get(x["sev"], 3), x["capa"], x["donde"]))
    altos = sum(h["sev"] in ("CRITICA", "ALTA") for h in hallazgos)
    L = [f"# Auditoria de seguridad (automatica) · {carpeta.name} · {datetime.now():%Y-%m-%d %H:%M}", "",
         f"Archivos revisados: {revisados} · Hallazgos: {len(hallazgos)} ({altos} altos/criticos)", ""]
    L += ["## Que se reviso", f"- Codigo: {revisados} archivos con {len(REGLAS)} reglas en 5 capas",
          *[f"- {r}" for r in REVISADO], ""]
    if notas:
        L += ["## Lo que NO se pudo revisar (no cuenta como limpio)", *[f"- {n}" for n in notas], ""]
    L += ["## Hallazgos", "", "| # | Sev | Capa | Que | Donde | Prueba | Arreglo |", "|---|---|---|---|---|---|---|"]
    for i, h in enumerate(hallazgos, 1):
        prueba = h["prueba"].replace("|", "\\|")
        L.append(f"| {i} | {h['sev']} | {NOMBRES_CAPA[h['capa']]} | {h['que']} | `{h['donde']}` | `{prueba}` | {h['arreglo']} |")
    L += ["", "Esto es la base automatica. La revision de Nova parte de aqui (logica de negocio, IDOR, flujos) y cada "
          "hallazgo nuevo tambien va con archivo:linea y su prueba. Un patron puede ser falso positivo: se confirma o "
          "descarta LEYENDO esa linea, nunca sin mirarla."]
    salida = Path(args.salida) if args.salida else carpeta / "nova_auditoria" / f"auditoria_{datetime.now():%Y%m%d_%H%M}.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[AUDITORIA] {revisados} archivos · {len(hallazgos)} hallazgos ({altos} altos/criticos) · "
          f"sin revisar: {len(notas)} · informe: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
