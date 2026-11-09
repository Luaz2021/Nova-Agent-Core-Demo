r"""
Nova Repo Sentinel - Escaner Estatico Zero-Tokens
Ubicacion: <GoogleDrive>\Antigravity\scripts\nova_repo_scanner.py
Escaneo ultrarrapido de repositorios y skills recien clonados (<400ms a 0 tokens).
Detecta inyecciones de prompt, hooks maliciosos (postinstall) y payloads ofuscados.
"""

import os
import sys
import re

PATTERNS = [
    # 1. Prompt Injections & Jailbreaks en texto plano (.md, .txt, .rules)
    (re.compile(r"(?i)(ignore\s+(all\s+)?previous\s+instructions|system\s+override|disregard\s+all\s+prior|DAN\s+mode|act\s+as\s+unrestricted)", re.I), "PROMPT_INJECTION"),
    (re.compile(r"(?i)(curl|wget|fetch|powershell|Invoke-WebRequest).*(exfil|pastebin|ngrok|webhook\.site|discord\.com/api/webhooks)", re.I), "DATA_EXFILTRATION_CALL"),
    
    # 2. Cargas Ofuscadas y Ejecucion Dinamica
    (re.compile(r"(?i)(from_base64|base64_decode|b64decode|atob)\s*\(", re.I), "BASE64_EXEC_ATTEMPT"),
    (re.compile(r"(eval\s*\(|exec\s*\(|Function\s*\(\s*['\"`]return|Invoke-Expression|iex\s+)", re.I), "DYNAMIC_CODE_EXECUTION"),
    
    # 3. Robo de credenciales locales
    (re.compile(r"(?i)(\.ssh/id_rsa|\.aws/credentials|\.vault|\.env\.local)", re.I), "CREDENTIAL_HARVESTING_REFERENCE"),
]

SUSPICIOUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".vbs", ".ps1", ".scr", ".pif"}

def scan_directory(target_path):
    if not os.path.exists(target_path):
        print(f"[ERROR] Ruta no encontrada: {target_path}")
        return 1

    findings = []
    scanned_files = 0

    print(f"\n[NOVA SENTINEL] Escaneando repositorio en: {target_path}")

    for root, dirs, files in os.walk(target_path):
        # Ignorar .git y node_modules para velocidad pura
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "vendor", ".venv", "__pycache__"}]
        
        for fname in files:
            scanned_files += 1
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()

            # A. Detectar binarios o scripts ejecutables en repositorios que deberian ser de docs/librerias
            if ext in SUSPICIOUS_EXTENSIONS and "node_modules" not in fpath:
                rel = os.path.relpath(fpath, target_path)
                findings.append((rel, 0, "SUSPICIOUS_EXECUTABLE", f"Binario o script ejecutable detectado: {fname}"))

            # B. Analisis de package.json contra hooks sucios
            if fname == "package.json":
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if re.search(r'"(preinstall|postinstall)"\s*:\s*"[^"]*(curl|wget|bash|sh|node\s+-e|powershell)', content, re.I):
                            rel = os.path.relpath(fpath, target_path)
                            findings.append((rel, 1, "MALICIOUS_PACKAGE_HOOK", "Hook preinstall/postinstall sospechoso en package.json"))
                except Exception:
                    pass

            # C. Escaneo de contenido de texto plano
            if ext in {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".rules", ".mdc"}:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if len(line) > 2000:
                                # Lineas gigantes ofuscadas
                                rel = os.path.relpath(fpath, target_path)
                                findings.append((rel, idx, "SUSPICIOUS_LONG_LINE", "Linea sospechosamente larga (>2000 caracteres), posible payload ofuscado"))
                                break
                            for pattern, tag in PATTERNS:
                                if pattern.search(line):
                                    rel = os.path.relpath(fpath, target_path)
                                    findings.append((rel, idx, tag, line.strip()[:100]))
                except Exception:
                    pass

    print(f"[NOVA SENTINEL] Archivos analizados: {scanned_files}")
    if not findings:
        print("[SENTINEL OK] Repositorio limpio. Cero inyecciones o malware detectado a Nivel 0.\n")
        return 0
    else:
        print(f"\n[ALERTA DE SEGURIDAD] Se detectaron {len(findings)} hallazgos criticos:")
        for rel, line_num, tag, sample in findings:
            print(f"  - [{tag}] {rel} (linea {line_num}): {sample}")
        print("\n[RECOMENDACION] No abras este proyecto ni ejecutes scripts sin revision manual.\n")
        return 2

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python nova_repo_scanner.py <ruta_del_repo>")
        sys.exit(1)
    target = sys.argv[1]
    sys.exit(scan_directory(target))
