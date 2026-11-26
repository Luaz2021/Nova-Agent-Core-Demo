"""Junta varias imagenes en una fila (mismo alto maximo) para revisarlas de un vistazo. Uso: mosaico.py salida.png a.png b.png ..."""
import sys
from PIL import Image
ims = [Image.open(p).convert("RGB") for p in sys.argv[2:]]
alto = min(1400, max(i.height for i in ims))
ims = [i.resize((max(1, int(i.width * min(1, alto / i.height))), min(i.height, alto))) for i in ims]
L = Image.new("RGB", (sum(i.width for i in ims) + 12 * (len(ims) - 1), max(i.height for i in ims)), (255, 0, 255))
x = 0
for i in ims:
    L.paste(i, (x, 0)); x += i.width + 12
L.save(sys.argv[1])
