"""Careo para revisar a ojo: original | clon por seccion (PC arriba, movil abajo). Uso: careo.py <carpeta_web> <salida> [secciones]"""
import re, sys
from pathlib import Path
from PIL import Image, ImageDraw

web, salida = Path(sys.argv[1]), Path(sys.argv[2])
salida.mkdir(parents=True, exist_ok=True)
img = web / "construccion" / "img"
rev = (web / "construccion" / "revision.html").read_text(encoding="utf-8", errors="replace")
secs = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else sorted(
    {int(m) for m in re.findall(r"orig_(\d+)_pc", " ".join(p.name for p in img.iterdir()))})


def par(a, b, ancho):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    A = A.resize((ancho, max(1, int(A.height * ancho / A.width))))
    B = B.resize((ancho, max(1, int(B.height * ancho / B.width))))
    L = Image.new("RGB", (ancho * 2 + 12, max(A.height, B.height) + 18), (255, 0, 255))
    L.paste(A, (0, 18)); L.paste(B, (ancho + 12, 18))
    d = ImageDraw.Draw(L); d.text((4, 3), "ORIGINAL", fill="black"); d.text((ancho + 16, 3), "CLON", fill="black")
    return L


for n in secs:
    for vista, ancho in (("pc", 760), ("movil", 393)):
        a, b = img / f"orig_{n}_{vista}.png", img / f"gen_{n}_{vista}.png"
        if a.exists() and b.exists():
            par(a, b, ancho).save(salida / f"careo_{n}_{vista}.png")
print("listo", secs)
