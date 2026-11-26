"""Mapa de diferencias original vs clon de una seccion: original | clon | diferencias en rojo. Uso: diferencias.py <web> <n> <pc|movil> <salida>"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

web, n, vista, salida = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
img = web / "construccion" / "img"
a = Image.open(img / f"orig_{n}_{vista}.png").convert("RGB")
b = Image.open(img / f"gen_{n}_{vista}.png").convert("RGB")
w, h = a.width, max(a.height, b.height)
A = Image.new("RGB", (w, h), "white"); A.paste(a, (0, 0))
B = Image.new("RGB", (w, h), "white"); B.paste(b.resize((w, int(b.height * w / b.width))), (0, 0))
da = np.abs(np.asarray(A, dtype=int) - np.asarray(B, dtype=int)).sum(axis=2)
mask = da > 60
D = np.asarray(A).copy() // 3 + 170
D[mask] = [230, 0, 0]
print(f"alto orig {a.height} clon {b.height} · pixeles distintos {mask.mean() * 100:.1f} %")
filas = mask.mean(axis=1)
bandas, dentro = [], None
for y, v in enumerate(filas):
    if v > 0.02 and dentro is None: dentro = y
    if v <= 0.02 and dentro is not None:
        if y - dentro > 3: bandas.append((dentro, y))
        dentro = None
print("bandas con diferencias (y0-y1):", bandas[:15])
esc = 760 / w if vista == "pc" else 1
tira = Image.new("RGB", (w * 3 + 24, h), (255, 0, 255))
tira.paste(A, (0, 0)); tira.paste(B, (w + 12, 0)); tira.paste(Image.fromarray(D.astype("uint8")), (2 * w + 24, 0))
tira.resize((int(tira.width * esc), int(tira.height * esc))).save(salida)
