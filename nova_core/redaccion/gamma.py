"""Presentaciones con GAMMA desde el borrador ya revisado: exportar --formatos gamma (12/11/2026, Claude).

Por que: cuando el enunciado pide una PRESENTACION, un Word no vale. El texto pasa antes por la revision final
(tildes, cifras, humano, ortografia, logica) y a Gamma se le manda con textMode "preserve": maqueta, pero NO
reescribe lo que ya esta revisado.

Clave: variable GAMMA_API_KEY o "gamma_api_key" en el cofre (G:\\Mi unidad\\Antigravity\\vault\\secrets.json).
Nunca se imprime ni se escribe en ningun archivo.
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://public-api.gamma.app/v1.0/generations"
COFRE = Path(r"G:\Mi unidad\Antigravity\vault\secrets.json")
INSTRUCCIONES = (
    "Presentación en español de España, con tildes. Una diapositiva por cada bloque 'Diapositiva N'. "
    "Mantén el texto tal cual (ya está revisado). Diseño limpio y profesional, azul marino, sin emojis."
)


def clave() -> str:
    if valor := os.environ.get("GAMMA_API_KEY"):
        return valor
    for linea in _leer(
        COFRE.with_name("google_cloud.env")
    ).splitlines():  # GAMMA_API_KEY=... (lo carga nova_vault_sync)
        nombre, _, valor = linea.partition("=")
        if nombre.strip() == "GAMMA_API_KEY" and valor.strip():
            return valor.strip()
    try:
        return json.loads(_leer(COFRE) or "{}").get("gamma_api_key", "")
    except ValueError:
        return ""


def _leer(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def texto_presentacion(guion: dict, secciones: list[dict]) -> str:
    partes = [
        f"Diapositiva 1: {guion.get('titulo', '')}\n{guion.get('subtitulo', '')}\n"
        + " · ".join(
            str(guion[k]) for k in ("autor", "modulo", "fecha") if guion.get(k)
        )
    ]
    for n, s in enumerate(secciones, start=2):
        partes.append(f"Diapositiva {n}: {s['titulo']}\n{s['cuerpo']}")
    return "\n\n---\n\n".join(partes)


def _pedir(url: str, api_key: str, datos: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(datos).encode("utf-8") if datos else None,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def generar(
    guion: dict, secciones: list[dict], carpeta: Path, nombre: str
) -> list[Path]:
    api_key = clave()
    if not api_key:
        raise SystemExit(
            '[error] Falta la clave de Gamma: añade "gamma_api_key" al cofre (vault\\secrets.json) '
            "o la variable GAMMA_API_KEY. Pídesela a Alexander; no la escribas en ningún script."
        )
    peticion = {
        "inputText": texto_presentacion(guion, secciones),
        "textMode": "preserve",
        "format": "presentation",
        "numCards": len(secciones) + 1,
        "cardSplit": "inputTextBreaks",
        "additionalInstructions": INSTRUCCIONES,
        "exportAs": "pptx",
    }
    try:
        respuesta = _pedir(API, api_key, peticion)
    except urllib.error.HTTPError as e:
        raise SystemExit(
            f"[error] Gamma respondió {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
        ) from None
    gen_id = respuesta.get("generationId") or respuesta.get("id")
    print(
        f"[*] Gamma está maquetando ({len(secciones) + 1} diapositivas)...", flush=True
    )
    for _ in range(60):  # hasta 5 minutos
        time.sleep(5)
        estado = _pedir(f"{API}/{gen_id}", api_key)
        if estado.get("status") == "completed":
            hechos = []
            enlace = carpeta / f"{nombre}_gamma.txt"
            enlace.write_text(estado.get("gammaUrl", ""), encoding="utf-8")
            hechos.append(enlace)
            if url := estado.get("exportUrl"):
                pptx = carpeta / f"{nombre}.pptx"
                urllib.request.urlretrieve(url, pptx)
                hechos.append(pptx)
            print(f"[ok] Presentación en Gamma: {estado.get('gammaUrl')}")
            return hechos
        if estado.get("status") == "failed":
            raise SystemExit(
                f"[error] Gamma no pudo generarla: {estado.get('error', estado)}"
            )
    raise SystemExit("[error] Gamma tardó más de 5 minutos; mira tu cuenta de Gamma.")
