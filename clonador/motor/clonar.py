import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
CLONAR · el flujo entero en un solo paso, sin IA (sin Qwen) y en local

  python clonar.py https://web.com          (o sin URL: lee url.txt)
  python clonar.py https://web.com --paginas=3     (además, hasta 2 subpáginas del menú)

  1. analizar   mide la web (PC + iPhone 14 Pro), fotos de referencia, interacciones (sin "ojos")
  2. crear      clon fiel -> Tailwind, interacciones (clon-interacciones.js) y datos para React (react/datos_web.ts)
  3. verificar  nota de cada sección contra la original, versión final con medios libres y prueba de interacciones
                (sin reparaciones de Qwen: lo que quede por debajo del 90 % lo arregla Claude con código)

Cada paso recibe la carpeta de SU web (no depende de ultimo_analisis.txt). Al final, un resumen con las rutas.
"""
import re
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def paso(nombre, args, limite):
    """Ejecuta un paso enseñando su salida en directo; devuelve (código, salida completa)."""
    print(f"\n{'=' * 62}\n  {nombre}\n{'=' * 62}", flush=True)
    t, salida = time.time(), []
    p = subprocess.Popen([sys.executable, "-u"] + args, cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace",
                         env={**__import__("os").environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    try:
        for linea in p.stdout:
            salida.append(linea)
            print(linea, end="", flush=True)
        p.wait(timeout=limite)
    except subprocess.TimeoutExpired:
        p.kill()
        return -9, "".join(salida) + "\ntiempo agotado"
    print(f"  ({nombre.split(' ')[0]}: {round(time.time() - t)} s)", flush=True)
    return p.returncode, "".join(salida)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    extra = [a for a in sys.argv[1:] if a.startswith("--paginas")]
    url = args[0] if args else (BASE / "url.txt").read_text(encoding="utf-8").strip().splitlines()[0].strip()
    t0 = time.time()

    analizar_cmd = ["analizar.py", url]
    if "--sin-ojos" in sys.argv:
        analizar_cmd.append("--sin-ojos")
    analizar_cmd += extra
    c, salida = paso("1/3 ANALIZAR (medir la original)", analizar_cmd, 2400)
    m = re.findall(r"Listo en \d+ s -> (.+)", salida)
    if c != 0 or not m:
        print(f"\n✖ No se pudo analizar {url}. Mira el aviso de arriba (webs que bloquean robots, páginas vacías...).")
        sys.exit(1)
    carpeta = Path(m[-1].strip())

    c, salida = paso("2/3 CREAR (clon, interacciones y datos para React)", ["crear.py", str(carpeta)], 1200)
    if c != 0:
        print("\n✖ Falló el paso de crear: mira el error de arriba.")
        sys.exit(1)

    c, salida = paso("3/3 VERIFICAR (nota de cada sección, sin Qwen)", ["verificar.py", str(carpeta), "--intentos=0"], 3600)
    nota = re.findall(r"Parecido medio (\d+)% · lista media (\d+)% · aprobadas (\d+)/(\d+)", salida)
    inter = re.findall(r"interacciones: (\d+) de (\d+) correctas", salida)
    bajas = re.findall(r"sección (\d+) \(\d+/\d+\).*?\n\s+parecido (\d+)%", salida)

    out = carpeta / "construccion"
    print(f"\n{'=' * 62}\n  RESUMEN · {url} · {round((time.time() - t0) / 60, 1)} min\n{'=' * 62}")
    if nota:
        p, li, ap, tot = nota[-1]
        print(f"  Parecido medio {p} % · lista {li} % · aprobadas {ap} de {tot}")
    if inter:
        print(f"  Interacciones: {inter[-1][0]} de {inter[-1][1]} correctas")
    flojas = [f"{n} ({v} %)" for n, v in bajas if int(v) < 90]
    if flojas:
        print(f"  Por debajo del 90 %: secciones {', '.join(flojas)} -> para Claude (pendientes_nova.md)")
    for nombre, ruta in (("Clon (base)", out / "index.html"), ("Versión final (medios libres)", out / "index_final.html"),
                         ("Careo original/clon", out / "revision.html"), ("Datos para React", carpeta / "react" / "datos_web.ts"),
                         ("Interacciones", out / "interacciones_prueba.md")):
        if ruta.exists():
            print(f"  {nombre:30s} {ruta}")
    (BASE.parent / "workspace" / "ultimo_analisis.txt").write_text(str(carpeta), encoding="utf-8")


if __name__ == "__main__":
    main()
