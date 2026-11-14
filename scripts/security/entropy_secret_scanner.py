"""
Scanner de Secretos por Entropia de Shannon y Patrones Heuristicos.
Detecta claves de alta entropia, tokens criptograficos, archivos .env
y credenciales expuestas en staging de Git o carpetas locales.

Soporta .guardianignore en la raiz de cada repositorio.
Regla de entropia: bloquea solo ante asignaciones a variables sospechosas;
si no, genera avisos informativos sin bloquear el commit.
Coste: 0 tokens (Python estandar, sin dependencias externas).
"""

from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Extensiones y carpetas ignoradas por defecto
IGNORED_PATTERNS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    ".DS_Store", "Thumbs.db", ".png", ".jpg", ".jpeg", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".pdf"
}

# Regex de tokens conocidos que SIEMPRE bloquean el commit
KNOWN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI API Key", re.compile(r"sk-[a-zA-Z0-9_-]{20,}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[a-zA-Z0-9]{36,}")),
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Stripe API Key", re.compile(r"sk_(live|test)_[0-9a-zA-Z]{24,}")),
    ("Google Cloud API Key", re.compile(r"AIza[0-9A-Za-z-_]{35}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}")),
    ("Private Key RSA/EC/OPENSSH", re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----")),
    ("Database URL with Password", re.compile(r"(postgres|mysql|mongodb)://[^:]+:([^@]+)@")),
]

# Deteccion de asignaciones a variables / claves sospechosas
ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    (?:
        (?:^|[\s,;(])
        (?P<var>[a-zA-Z_][a-zA-Z0-9_\-\.]*)
        (?:\s*:\s*[^=,;]+)?
        \s*(?::=|=)\s*
    |
        (?:^|[\s,{])
        ["']?(?P<dict_var>[a-zA-Z_][a-zA-Z0-9_\-\.]*)["']?
        \s*:\s*
    )
    """
)

SUSPICIOUS_VAR_PATTERN = re.compile(
    r"(?i)(?:^|[^a-zA-Z0-9])(?:password|passwd|\bpass\b|_pass\b|\bpass_|_pass_|secret|token|api_?key|apikey|auth(?:entication|orization)?|cred(?:ential)?s?|private_?key|privkey|access_?key|client_?secret)(?:$|[^a-zA-Z0-9])"
)

def find_repo_root(start_path: Path | None = None) -> Path:
    """Encuentra la raiz del repositorio Git o la carpeta con .guardianignore."""
    target = (start_path or Path.cwd()).resolve()
    if target.is_file():
        target = target.parent

    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(target)
        )
        p = Path(res.stdout.strip())
        if p.exists():
            return p.resolve()
    except Exception:
        pass

    for parent in [target] + list(target.parents):
        if (parent / ".guardianignore").exists() or (parent / ".git").exists():
            return parent.resolve()
    return target

def load_guardianignore(repo_root: Path) -> list[tuple[bool, re.Pattern[str]]]:
    """Carga y compila las reglas de .guardianignore al estilo .gitignore."""
    ignore_file = repo_root / ".guardianignore"
    if not ignore_file.is_file():
        return []

    rules: list[tuple[bool, re.Pattern[str]]] = []
    try:
        with open(ignore_file, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                is_negated = line.startswith("!")
                if is_negated:
                    line = line[1:].strip()
                if not line:
                    continue

                is_dir_only = line.endswith("/")
                clean = line.rstrip("/")
                is_anchored = clean.startswith("/") or "/" in clean
                if clean.startswith("/"):
                    clean = clean[1:]

                res: list[str] = []
                i = 0
                n = len(clean)
                while i < n:
                    c = clean[i]
                    if c == "*":
                        if i + 1 < n and clean[i + 1] == "*":
                            i += 2
                            if i < n and clean[i] == "/":
                                i += 1
                                res.append("(?:.*/)?")
                            else:
                                res.append(".*")
                            continue
                        else:
                            res.append("[^/]*")
                    elif c == "?":
                        res.append("[^/]")
                    elif c in r"\.+^$()[]{}|":
                        res.append("\\" + c)
                    else:
                        res.append(c)
                    i += 1

                core = "".join(res)
                if is_anchored:
                    regex_str = f"^{core}(?:/.*)?$" if is_dir_only else f"^{core}$"
                else:
                    regex_str = f"(?:^|/){core}(?:/.*)?$" if is_dir_only else f"(?:^|/){core}$"

                try:
                    rules.append((is_negated, re.compile(regex_str, re.IGNORECASE)))
                except re.error:
                    continue
    except Exception:
        pass

    return rules

def is_ignored_path(path: Path, repo_root: Path, guardian_rules: list[tuple[bool, re.Pattern[str]]]) -> bool:
    """Comprueba si la ruta pertenece a carpetas/tipos excluidos o .guardianignore."""
    for part in path.parts:
        if part in IGNORED_PATTERNS:
            return True
    if path.suffix.lower() in IGNORED_PATTERNS:
        return True

    if guardian_rules:
        try:
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        except Exception:
            rel = path.as_posix()

        ignored = False
        for is_negated, rx in guardian_rules:
            if rx.search(rel):
                ignored = not is_negated
        if ignored:
            return True

    return False

def shannon_entropy(data: str) -> float:
    """Calcula la entropia de Shannon en bits por caracter."""
    if not data:
        return 0.0
    length = len(data)
    counts = Counter(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())

def mask_secret(secret: str) -> str:
    """Oculta el secreto para mostrarlo en reportes seguros."""
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-4:]}"

def line_assigns_suspicious_var(line: str) -> bool:
    """Detecta si la linea asigna un valor a una variable sospechosa."""
    for m in ASSIGNMENT_PATTERN.finditer(line):
        var_name = m.group("var") or m.group("dict_var")
        if var_name and SUSPICIOUS_VAR_PATTERN.search(var_name):
            return True
    return False

def is_known_non_secret(token: str) -> bool:
    """Filtra falsos positivos obvios: URLs, regexes, paquetes npm, assets, etc."""
    # URLs y protocolos
    if token.startswith(("http://", "https://", "ftp://", "ws://", "wss://")):
        return True
    # Paquetes npm / dependencias scoped
    if token.startswith("@") and "/" in token:
        return True
    # Rutas de assets o archivos con extension comun
    if re.search(r"\.(png|jpe?g|gif|webp|svg|ico|woff2?|ttf|eot|mp4|webm|mp3|css|scss|json|md|html|tsx?|jsx?|py)$", token, re.IGNORECASE):
        return True
    # Clases Tailwind con calc o corchetes
    if any(k in token for k in ("calc(", "min-h-[", "max-w-[", "grid-cols-[", "bg-[", "text-[")):
        return True
    # Expresiones regulares comunes
    if any(k in token for k in ("(?:", "(?i", "[0-9", "[a-z", "[A-Z", "\\d", "\\w", "\\s", "^", "$")) and len(token) > 10:
        return True
    # Nombres de modelos IA comunes
    if "/" in token and any(m in token.lower() for m in ("internvl", "qwen", "llama", "mistral", "claude", "gemini", "deepseek", "phi-", "bert", "gpt")):
        return True
    # Format strings tipo Python/C
    if re.search(r"\{[a-zA-Z0-9_():]+\}", token):
        return True
    return False

def evaluate_token_entropy(token: str, line_context: str) -> tuple[bool, bool, float]:
    """
    Evalua una cadena por entropia.
    Retorna (is_secret, is_blocking, entropy).
    """
    ent = shannon_entropy(token)
    length = len(token)

    # UUID v4 estandar o rutas del sistema
    if re.match(r"^[0-9a-fA-F-]{36}$", token):
        return False, False, ent
    if "\\" in token:
        return False, False, ent
    if is_known_non_secret(token):
        return False, False, ent

    assigns_suspicious = line_assigns_suspicious_var(line_context)

    if assigns_suspicious:
        # En variables sospechosas (password, secret, token, api_key), umbral sensible y BLOQUEA
        if length >= 12 and ent >= 3.0:
            return True, True, ent
    else:
        # En variables normales o sin variable: solo AVISA sin bloquear
        if 14 <= length < 20 and ent >= 3.6:
            return True, False, ent
        elif length >= 20 and ent >= 4.0:
            return True, False, ent

    return False, False, ent

def scan_line(line: str, line_no: int, file_path: Path) -> list[dict[str, str | int | float | bool]]:
    """Inspecciona una linea en busca de patrones conocidos o alta entropia."""
    findings: list[dict[str, str | int | float | bool]] = []

    # 1. Comprobacion de patrones conocidos (SIEMPRE BLOQUEAN)
    for name, pattern in KNOWN_PATTERNS:
        match = pattern.search(line)
        if match:
            val = match.group(0)
            findings.append({
                "file": str(file_path),
                "line": line_no,
                "type": f"PATRON: {name}",
                "entropy": round(shannon_entropy(val), 2),
                "preview": mask_secret(val),
                "severity": "CRITICA",
                "blocking": True
            })

    # 2. Comprobacion de cadenas por entropia de Shannon
    tokens = re.findall(r"['\"]([^'\"\s]{14,128})['\"]", line)
    for token in tokens:
        # Ignorar si ya fue capturado como patron conocido
        if any(f["preview"].startswith(token[:4]) for f in findings):
            continue

        is_secret, is_blocking, entropy = evaluate_token_entropy(token, line)
        if is_secret:
            findings.append({
                "file": str(file_path),
                "line": line_no,
                "type": "ALTA ENTROPIA (Variable sospechosa)" if is_blocking else "ALTA ENTROPIA (Aviso - sin variable sospechosa)",
                "entropy": round(entropy, 2),
                "preview": mask_secret(token),
                "severity": "CRITICA" if is_blocking else "AVISO",
                "blocking": is_blocking
            })

    return findings

def scan_file(file_path: Path, repo_root: Path, guardian_rules: list[tuple[bool, re.Pattern[str]]]) -> list[dict[str, str | int | float | bool]]:
    """Escanea un archivo individual."""
    if is_ignored_path(file_path, repo_root, guardian_rules) or not file_path.is_file():
        return []

    # Bloqueo directo si el nombre del archivo es un .env en staging o .pem
    if file_path.name in {".env", ".env.local", ".env.production", ".env.stage"} or file_path.name.endswith(".pem"):
        return [{
            "file": str(file_path),
            "line": 1,
            "type": "ARCHIVO PROHIBIDO (.env / .pem)",
            "entropy": 0.0,
            "preview": file_path.name,
            "severity": "CRITICA",
            "blocking": True
        }]

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return []

    findings: list[dict[str, str | int | float | bool]] = []
    for idx, line in enumerate(lines, 1):
        line_clean = line.strip()
        if not line_clean or line_clean.startswith(("#", "//", "/*", "*")):
            continue
        findings.extend(scan_line(line_clean, idx, file_path))
    return findings

def get_git_staged_files(repo_root: Path) -> list[Path]:
    """Obtiene los archivos en staging listos para commit en Git."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(repo_root)
        )
        return [repo_root / p.strip() for p in res.stdout.splitlines() if p.strip()]
    except Exception:
        return []

def main() -> int:
    parser = argparse.ArgumentParser(description="Escaneo de secretos por entropia y patrones.")
    parser.add_argument("--staged", action="store_true", help="Escanear solo archivos en staging de Git")
    parser.add_argument("--path", type=str, default=".", help="Ruta de archivo o directorio a escanear")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(args.path) if not args.staged else Path.cwd())
    guardian_rules = load_guardianignore(repo_root)

    files_to_scan: list[Path] = []
    if args.staged:
        files_to_scan = get_git_staged_files(repo_root)
        if not files_to_scan:
            print("[ENTROPY SCANNER] Cero archivos en staging. Todo limpio.")
            return 0
    else:
        target = Path(args.path)
        if target.is_file():
            files_to_scan = [target]
        elif target.is_dir():
            files_to_scan = [
                p for p in target.rglob("*")
                if p.is_file() and not is_ignored_path(p, repo_root, guardian_rules)
            ]

    all_findings: list[dict[str, str | int | float | bool]] = []
    for f in files_to_scan:
        all_findings.extend(scan_file(f, repo_root, guardian_rules))

    blocking_findings = [f for f in all_findings if f.get("blocking", True)]
    warning_findings = [f for f in all_findings if not f.get("blocking", True)]

    # Si hay hallazgos criticos bloqueantes, detener con error 1
    if blocking_findings:
        print("=" * 70)
        print(" [BLOQUEO DE SEGURIDAD] DETECTADOS SECRETOS O ARCHIVOS SENSIBLES")
        print("=" * 70)
        for item in blocking_findings:
            print(f" -> [{item['severity']}] {item['type']}")
            print(f"    Archivo: {item['file']}:{item['line']}")
            print(f"    Entropia: {item['entropy']} bits | Valor: {item['preview']}")
            print("-" * 70)
        if warning_findings:
            print(f"(Adicionalmente se detectaron {len(warning_findings)} avisos informativos)")
        print(f"Total hallazgos criticos bloqueantes: {len(blocking_findings)}")
        print("ACCION REQUERIDA: Elimina o mueve estas credenciales a variables de entorno antes de confirmar.")
        return 1

    # Si solo hay avisos de alta entropia sin asignacion a variable sospechosa, mostrar advertencia y permitir commit (0)
    if warning_findings:
        print("=" * 70)
        print(" [AVISO DE SEGURIDAD] DETECTADA ALTA ENTROPIA (NO BLOQUEANTE)")
        print("=" * 70)
        for item in warning_findings:
            print(f" -> [{item['severity']}] {item['type']}")
            print(f"    Archivo: {item['file']}:{item['line']}")
            print(f"    Entropia: {item['entropy']} bits | Valor: {item['preview']}")
            print("-" * 70)
        print(f"[ENTROPY SCANNER] OK: {len(files_to_scan)} archivos auditados sin secretos bloqueantes ({len(warning_findings)} avisos informativos).")
        return 0

    print(f"[ENTROPY SCANNER] OK: {len(files_to_scan)} archivos auditados sin secretos ni claves sospechosas.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
