"""
CARGA · lee los DATOS de la biblioteca desde sus carpetas (idea del autor: "categorias y una
biblioteca general; el .py solo es el motor"). Ver LEEME.md.

  general/paletas.json              paletas propias de Nova
  general/estilos/<estilo>.json     un archivo por estilo (galeria, fuerza, retiro...)
  categorias/<cat>/_categoria.json  secciones (recetas), rotulos, sector y si la foto vende (_fotografica)
  categorias/<cat>/<tipo>.json      identidad de cada tipo de negocio: fotos, busquedas, paletas, detectar

Devuelve lo mismo que devolvian los antiguos identidad.json, esqueletos.json y recetas.json (si las carpetas no
existen, los lee de esos archivos), asi el motor no cambia. Para anadir un tipo o un estilo NO hace falta tocar codigo:
basta con un archivo .json nuevo en su carpeta.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GENERAL, CATEGORIAS = AQUI / "general", AQUI / "categorias"


def _leer(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _ordenar(nombres: list[str], orden: list[str]) -> list[str]:
    """Primero en el orden guardado (_orden/_tipos: decide en los empates); los nuevos, al final por nombre."""
    return [n for n in orden if n in nombres] + sorted(n for n in nombres if n not in orden)


def _categorias() -> list[Path]:
    if not CATEGORIAS.is_dir():
        return []
    meta = _leer(CATEGORIAS / "_meta.json") if (CATEGORIAS / "_meta.json").exists() else {}
    nombres = [d.name for d in CATEGORIAS.iterdir() if d.is_dir()]
    return [CATEGORIAS / n for n in _ordenar(nombres, meta.get("_orden") or [])]


@lru_cache(maxsize=1)
def recetas() -> dict:
    if not _categorias():
        return _leer(AQUI / "recetas.json")
    meta = _leer(CATEGORIAS / "_meta.json") if (CATEGORIAS / "_meta.json").exists() else {}
    out = {k: v for k, v in meta.items() if k != "_orden"}
    for d in _categorias():
        info = _leer(d / "_categoria.json")
        out[d.name] = {k: v for k, v in info.items() if k not in ("_fotografica", "_tipos")}
    return out


@lru_cache(maxsize=1)
def esqueletos() -> dict:
    carpeta = GENERAL / "estilos"
    if not carpeta.is_dir():
        return _leer(AQUI / "esqueletos.json")
    meta = _leer(carpeta / "_meta.json") if (carpeta / "_meta.json").exists() else {}
    out = {k: v for k, v in meta.items() if k != "_orden"}
    nombres = [p.stem for p in carpeta.glob("*.json") if not p.name.startswith("_")]
    for n in _ordenar(nombres, meta.get("_orden") or []):
        out[n] = _leer(carpeta / f"{n}.json")
    return out


@lru_cache(maxsize=1)
def identidad() -> dict:
    if not _categorias():
        return _leer(AQUI / "identidad.json")
    out = {"paletas_extra": _leer(GENERAL / "paletas.json").get("paletas", [])}
    for d in _categorias():
        info = _leer(d / "_categoria.json")
        cat = {"_fotografica": True} if info.get("_fotografica") else {}
        nombres = [p.stem for p in d.glob("*.json") if not p.name.startswith("_")]
        for n in _ordenar(nombres, info.get("_tipos") or []):
            cat[n] = _leer(d / f"{n}.json")
        if len(cat) > (1 if "_fotografica" in cat else 0):
            out[d.name] = cat
    return out
