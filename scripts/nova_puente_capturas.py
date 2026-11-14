"""
Puente de ADJUNTOS de Nova (Capa 0 - 0 tokens de nube). v2 (08/11, Claude).

Lo que Alexander pega en el chat de Antigravity (imagenes, PDFs, Word, Excel...) llega a brain/<conv>/.user_uploaded/.
Este puente (lo lanza session_guard al arrancar, en bucle):
  1. lo MUEVE a antigravity/temporal/<AAAA-MM>/  (carpeta TEMPORAL de Nova, sincronizada con Drive con "sube los cambios")
  2. IMAGEN    -> InternVL (local) la describe        -> <archivo>.vista.md al lado
     DOCUMENTO -> destilador (conversor + resumir, Qwen local si es largo) -> <archivo>.resumen.md al lado
  3. apunta una linea en temporal/INDICE.md (fecha, archivo, tipo, resumen corto, ruta del .md)
Nova lee INDICE.md y el .md del archivo (pocos tokens), NUNCA la imagen o el documento entero desde la nube.
Los originales no se borran nunca. Si Ollama no responde, el adjunto queda "pendiente" y se reintenta solo.

    pythonw nova_puente_capturas.py --daemon          (lo hace session_guard)
    python  nova_puente_capturas.py --procesar        (procesa lo pendiente una vez)
    python  nova_puente_capturas.py --analizar --prompt "que falla en esta captura"   (pregunta a InternVL por la ultima imagen)
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

NOVA = Path.home() / ".gemini"
DIR_BRAIN = NOVA / "antigravity" / "brain"
DIR_ADJ = NOVA / "antigravity" / "temporal"  # carpeta TEMPORAL de Nova (sincronizada con Drive)
INDICE = DIR_ADJ / "INDICE.md"
PENDIENTES = DIR_ADJ / ".pendientes.json"
LOG_PUENTE = NOVA / "antigravity" / "memory" / "registros" / "puente_capturas.log"
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
IMAGENES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
DOCUMENTOS = {".pdf", ".docx", ".xlsx", ".xlsm", ".pptx", ".txt", ".md", ".csv", ".html", ".htm"}
sys.path.insert(0, str(NOVA / "nova_core"))


def modelos() -> tuple[str, str]:
    try:
        m = json.loads((NOVA / "antigravity" / "scripts" / "nova_modelos.json").read_text(encoding="utf-8"))
        return m.get("vl", "blaifa/InternVL3_5:8b"), m.get("coder", "qwen3.5:9b")
    except (OSError, ValueError):
        return "blaifa/InternVL3_5:8b", "qwen3.5:9b"


def _log(texto: str) -> None:
    try:
        with LOG_PUENTE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {texto}\n")
    except OSError:
        pass


def _leer_pendientes() -> list[str]:
    try:
        return json.loads(PENDIENTES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _guardar_pendientes(lista: list[str]) -> None:
    try:
        PENDIENTES.write_text(json.dumps(sorted(set(lista)), ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


# ------------------------------------------------------------------------------------------------ mover
def mover_adjuntos(conv_id: str | None = None) -> list[Path]:
    """De brain/<conv>/.user_uploaded a memory/adjuntos/<AAAA-MM>/ (sincronizada)."""
    destino_mes = DIR_ADJ / datetime.now().strftime("%Y-%m")
    movidos: list[Path] = []
    for c in ([DIR_BRAIN / conv_id] if conv_id else list(DIR_BRAIN.glob("*"))):
        sube = c / ".user_uploaded"
        if not sube.is_dir():
            continue
        for archivo in sube.iterdir():
            if not archivo.is_file():
                continue
            destino_mes.mkdir(parents=True, exist_ok=True)
            destino = destino_mes / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}"
            try:
                shutil.move(str(archivo), str(destino))
                movidos.append(destino)
            except OSError as e:  # Antigravity aun lo esta escribiendo: se intenta en la siguiente vuelta
                _log(f"no se pudo mover {archivo.name}: {e}")
    return movidos


# ------------------------------------------------------------------------------------------------ leer
def ver_imagen(ruta: Path, pregunta: str = "") -> str:
    """InternVL local. Lanza excepcion si Ollama no responde (el adjunto queda pendiente)."""
    vl, _ = modelos()
    texto = (pregunta or "Describe esta imagen para alguien que no puede verla: que es, que texto se lee, que elementos "
             "importantes hay y, si es una web o una app, que se ve mal (cortes, contraste, alineacion).") + \
            " Responde en espanol, en 4 a 8 lineas, sin inventar."
    cuerpo = {"model": vl, "stream": False, "keep_alive": "10m", "options": {"temperature": 0.1, "num_predict": 400},
              "messages": [{"role": "user", "content": texto, "images": [base64.b64encode(ruta.read_bytes()).decode()]}]}
    req = urllib.request.Request(OLLAMA_CHAT, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        respuesta = (json.loads(r.read()).get("message") or {}).get("content", "").strip()
    if not respuesta:
        raise RuntimeError("InternVL devolvio una respuesta vacia")
    return respuesta


def destilar_documento(ruta: Path) -> tuple[str, str]:
    """(resumen, ruta del texto completo). Corto: texto limpio directo; largo: resumen con Qwen local."""
    from conversor import convertir  # nova_core
    from resumir import resumir_local
    salida = DIR_ADJ / "_texto"
    salida.mkdir(parents=True, exist_ok=True)
    doc = convertir(ruta, salida)
    largo = len(doc.get("chunks") or []) > 1
    resumen = resumir_local(doc, 8, salida, usar_ollama=largo)
    if largo and (not resumen or resumen.startswith("Error")):
        raise RuntimeError("Qwen no pudo resumir (Ollama?)")
    completo = next(iter(sorted(salida.glob(f"{ruta.stem}*.json"))), salida)
    return resumen, str(completo)


def procesar(ruta: Path) -> bool:
    """Deja <archivo>.vista.md o <archivo>.resumen.md y una linea en INDICE.md. False = pendiente (reintentar)."""
    ext = ruta.suffix.lower()
    try:
        if ext in IMAGENES:
            texto, tipo, sufijo, extra = ver_imagen(ruta), "imagen", ".vista.md", ""
        elif ext in DOCUMENTOS:
            texto, completo = destilar_documento(ruta)
            tipo, sufijo, extra = "documento", ".resumen.md", f"\n\nTexto completo (por trozos): `{completo}`"
        else:
            texto, tipo, sufijo, extra = "(tipo no soportado: abrelo solo si Alexander lo pide)", "otro", ".nota.md", ""
    except Exception as e:
        _log(f"pendiente {ruta.name}: {type(e).__name__}: {e}")
        return False
    md = ruta.with_name(ruta.name + sufijo)
    md.write_text(f"# {ruta.name}\n\nTipo: {tipo} · leido en local (0 tokens de nube) · {datetime.now():%Y-%m-%d %H:%M}\n\n"
                  f"{texto}{extra}\n", encoding="utf-8")
    corto = " ".join(texto.split())[:180]
    nuevo = not INDICE.exists()
    with INDICE.open("a", encoding="utf-8") as f:
        if nuevo:
            f.write("# Adjuntos de Alexander (lo mas nuevo abajo)\n\nNova: lee el .md de cada adjunto, no el archivo original.\n\n"
                    "| Fecha | Archivo | Tipo | Resumen | Lectura |\n|---|---|---|---|---|\n")
        f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {ruta.name} | {tipo} | {corto.replace('|', '/')} | `{md}` |\n")
    _log(f"{tipo} procesado: {ruta.name} -> {md.name}")
    return True


def procesar_pendientes(nuevos: list[Path] | None = None) -> None:
    lista = _leer_pendientes() + [str(p) for p in (nuevos or [])]
    quedan = [r for r in dict.fromkeys(lista) if Path(r).exists() and not procesar(Path(r))]
    _guardar_pendientes(quedan)


def daemon_loop(intervalo: float = 2.0) -> None:
    DIR_ADJ.mkdir(parents=True, exist_ok=True)
    _log("puente de adjuntos v2 arrancado")
    ultimo_reintento = 0.0
    while True:
        try:
            movidos = mover_adjuntos()
            if movidos:
                _log(f"{len(movidos)} adjunto(s) movidos a {DIR_ADJ}")
                procesar_pendientes(movidos)
            elif _leer_pendientes() and time.time() - ultimo_reintento > 120:  # reintenta lo pendiente cada 2 min
                ultimo_reintento = time.time()
                procesar_pendientes()
        except Exception as e:
            _log(f"ERROR: {type(e).__name__}: {e}")
        time.sleep(intervalo)


def main() -> None:
    if sys.stdout:  # con pythonw (sin consola) no hay stdout
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Puente de adjuntos de Nova (imagenes con InternVL, documentos con el destilador)")
    ap.add_argument("--daemon", action="store_true", help="Bucle continuo (lo lanza session_guard)")
    ap.add_argument("--mover", action="store_true", help="Mover adjuntos una vez")
    ap.add_argument("--procesar", action="store_true", help="Procesar lo pendiente una vez")
    ap.add_argument("--conv-id", default=None)
    ap.add_argument("--analizar", action="store_true", help="Preguntar a InternVL por la ultima imagen de adjuntos")
    ap.add_argument("--prompt", default="", help="Pregunta concreta sobre la imagen")
    a = ap.parse_args()
    if a.daemon:
        daemon_loop()
        return
    if a.mover or a.procesar:
        movidos = mover_adjuntos(a.conv_id) if a.mover else []
        procesar_pendientes(movidos)
        print(f"[Puente] {len(movidos)} movidos; pendientes: {len(_leer_pendientes())}. Indice: {INDICE}")
    if a.analizar:
        imgs = [p for p in DIR_ADJ.rglob("*") if p.suffix.lower() in IMAGENES]
        if not imgs:
            print("[Puente] No hay imagenes en adjuntos.")
            return
        ultima = max(imgs, key=lambda p: p.stat().st_mtime)
        print(f"[InternVL] {ultima.name}\n{ver_imagen(ultima, a.prompt)}")


if __name__ == "__main__":
    main()
