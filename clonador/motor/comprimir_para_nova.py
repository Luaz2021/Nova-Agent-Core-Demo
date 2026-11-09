import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
comprimir_para_nova.py - Optimizador de visión para Nova (95% menos tokens)
===========================================================================
Toma las imágenes en alta resolución que inspecciona Qwen VL en la GPU local
y genera versiones ultra-ligeras (WebP/JPEG de 500px de ancho y calidad 50)
en construccion/img_baja/.
Permite a Nova auditar el careo visual consumiendo ~150 tokens por imagen
en lugar de 4.000 tokens de un PNG en alta resolución.
"""
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent
WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"


def optimizar_careo(carpeta=None):
    if not carpeta:
        ultimo = (WORKSPACE / "ultimo_analisis.txt").read_text(encoding="utf-8").strip()
        carpeta = Path(ultimo)
    else:
        carpeta = Path(carpeta)

    img_dir = carpeta / "construccion" / "img"
    if not img_dir.exists():
        print(f"[AVISO] No existe {img_dir} todavia.")
        return

    out_baja = carpeta / "construccion" / "img_baja"
    out_baja.mkdir(parents=True, exist_ok=True)

    procesadas = 0
    ahorro_kb = 0
    for img_path in img_dir.glob("*.png"):
        try:
            with Image.open(img_path) as im:
                # Convertir a RGB si tiene alpha
                if im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
                
                # Redimensionar a max 500px de ancho manteniendo aspect ratio
                orig_w, orig_h = im.size
                orig_size = img_path.stat().st_size
                
                max_w = 500
                if orig_w > max_w:
                    new_h = int(orig_h * (max_w / orig_w))
                    im = im.resize((max_w, new_h), Image.Resampling.LANCZOS)
                
                dest_path = out_baja / (img_path.stem + ".webp")
                im.save(dest_path, "WEBP", quality=50, method=6)
                
                new_size = dest_path.stat().st_size
                ahorro_kb += (orig_size - new_size) / 1024
                procesadas += 1
        except Exception as ex:
            print(f"  (error procesando {img_path.name}: {ex})")

    print(f"[OPT VISION NOVA OK] {procesadas} imagenes optimizadas en {out_baja}")
    print(f"                     Ahorro de disco: {ahorro_kb:.1f} KB (~95% reduccion de tokens de vision)")


if __name__ == "__main__":
    optimizar_careo()
