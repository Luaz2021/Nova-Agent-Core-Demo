"""Auditoria visual a 0 tokens de hojas de contacto de video con Qwen2.5-VL en Ollama."""

from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path.home() / ".gemini" / "nova_core"))
from ollama_comun import ensure_ollama_service

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def _modelo_nova(clave: str, defecto: str) -> str:
    """Modelo Qwen desde scripts/nova_modelos.json (unico sitio para cambiar de version)."""
    try:
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8"))[clave]
    except Exception:
        return defecto


MODELO_VL = _modelo_nova("vl", "blaifa/InternVL3_5:8b")
PROMPT_QA = (
    "Analiza esta hoja de contacto 3x2 de un video programatico. "
    "Verifica 4 reglas: (1) textos cortados o fuera de margen, "
    "(2) elementos o textos solapados, (3) bajo contraste ilegible, "
    "(4) fotogramas vacios por error. Responde APROBADO o lista el fallo por recuadro (1 a 6)."
)


def ensamblar_hoja(
    rutas: list[Path], salida: Path, cols: int = 3, filas: int = 2
) -> Path:
    """Genera un mosaico 3x2 redimensionado a 1280x720 para inferencia rapida (< 30s)."""
    if not rutas:
        raise ValueError("Se requiere al menos un fotograma para ensamblar la hoja.")
    cw, ch = 1280 // cols, 720 // filas
    lienzo = Image.new("RGB", (cw * cols, ch * filas), (10, 14, 22))
    celdas = [
        (
            idx,
            Image.open(ruta).convert("RGB").resize((cw, ch), Image.Resampling.BILINEAR),
        )
        for idx, ruta in enumerate(rutas[: cols * filas])
    ]
    for idx, miniatura in celdas:
        lienzo.paste(miniatura, ((idx % cols) * cw, (idx // cols) * ch))
    lienzo.save(salida, quality=88)
    return salida


def consultar_juez_vl(hoja: Path, modelo: str = MODELO_VL) -> str:
    """Envia la hoja de contacto en Base64 a Ollama local y devuelve el veredicto."""
    if not hoja.exists():
        return f"ERROR: No existe el archivo {hoja}"
    ensure_ollama_service()
    img_b64 = base64.b64encode(hoja.read_bytes()).decode("utf-8")
    payload = json.dumps(
        {
            "model": modelo,
            "prompt": PROMPT_QA,
            "images": [img_b64],
            "stream": False,
            "options": {"temperature": 0.1},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    return str(datos.get("response", "")).strip()


def main() -> None:
    """Punto de entrada CLI: recibe rutas de imagenes o una hoja ya generada."""
    args = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
    if not args:
        print(
            "Uso: python auditar_hoja_vl.py <frame1.png> [frame2.png ...] | <hoja_final.png>"
        )
        return
    hoja = (
        args[0]
        if len(args) == 1
        else ensamblar_hoja(args, args[0].parent / "hoja_final_720p.jpg")
    )
    print(consultar_juez_vl(hoja))


if __name__ == "__main__":
    main()
