import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
LOTE: pasa webs por la cadena oficial (analizar -> crear -> verificar) y deja un resumen.

  python lote.py                  (lee lote.txt: una URL por línea; las líneas con # se ignoran)
  python lote.py reintentar       (lee reintentar.txt)
  python lote.py https://web.com  (UNA web; para una sola es mejor clonar.py, que enseña cada paso en directo)

Sin Qwen (como clonar.py):  analizar --sin-ojos -> crear -> verificar --intentos=0, todas las secciones
Cada paso recibe la carpeta de SU web (no depende de ultimo_analisis.txt, que cualquier análisis pisa).
Resultado: workspace/resumen_<lote>.md (se actualiza después de cada web) y resumen_<lote>.json.
Si una web bloquea o falla, se apunta y se sigue con la siguiente.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
SALIDA = Path(__file__).resolve().parent.parent / "workspace"
SOLO, INTENTOS = 0, 0          # sin Qwen: todas las secciones medidas, sin reparaciones (las hace Claude)


def correr(args, limite):
    t = time.time()
    try:
        p = subprocess.run([sys.executable, "-u"] + args, cwd=BASE, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=limite)
        return p.returncode, p.stdout + p.stderr, round(time.time() - t)
    except subprocess.TimeoutExpired:
        return -9, "tiempo agotado", round(time.time() - t)


def error_real(salida):
    """La línea que explica el fallo (la del error, no la última que imprimió)."""
    lineas = [l.strip() for l in salida.strip().splitlines() if l.strip()]
    for l in reversed(lineas):
        if re.search(r"Error|Exception|NO SE PUDO|Traceback", l):
            return l[:110]
    return lineas[-1][:110] if lineas else ""


NOMBRE = "lote"


def resumen(filas):
    ok = [f for f in filas if f.get("estado") == "ok"]
    cubre = [f for f in ok if f["parecido"] >= 50]
    modo = (f"modo rápido: análisis sin ojos, {SOLO} secciones verificadas" if SOLO
            else "cadena completa: análisis con ojos, todas las secciones verificadas")
    L = ["# Resumen del lote rápido" if SOLO else "# Resumen de la cadena completa", "",
         f"_{time.strftime('%Y-%m-%d %H:%M')} · {modo}, {INTENTOS} intento(s) de Qwen por sección_", "",
         f"**Webs procesadas:** {len(filas)} · **terminadas:** {len(ok)} · **cubiertas ≥ 50 % de parecido:** {len(cubre)}/{len(filas)}"
         + (f" · **parecido medio:** {round(sum(f['parecido'] for f in ok) / len(ok))}%" if ok else ""), "",
         "| # | Web | Tipo | Parecido | Lista | Aprobadas | Tiempo | Notas |", "|---|---|---|---|---|---|---|---|"]
    for i, f in enumerate(filas, 1):
        if f.get("estado") == "ok":
            L.append(f"| {i} | {f['web']} | {f['tipo']} | {f['parecido']}% | {f['lista']}% | {f['aprobadas']} | {f['tiempo'] // 60} min | {f.get('nota', '')} |")
        else:
            L.append(f"| {i} | {f['web']} | — | — | — | — | {f.get('tiempo', 0) // 60} min | ⚠ {f.get('nota', f.get('estado'))} |")
    (SALIDA / f"resumen_{NOMBRE}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (SALIDA / f"resumen_{NOMBRE}.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")


def carpeta_de(salida):
    """La carpeta que imprime analizar.py al acabar ("Listo en N s -> <carpeta>"); si no, el puntero global."""
    m = re.findall(r"Listo en \d+ s -> (.+)", salida)
    return Path(m[-1].strip()) if m else Path((SALIDA / "ultimo_analisis.txt").read_text(encoding="utf-8").strip())


def main():
    global NOMBRE, SOLO, INTENTOS
    arg = sys.argv[1] if len(sys.argv) > 1 else "lote"
    una = arg.startswith("http")
    if una:                                      # una sola web: la cadena completa, sin recortes
        NOMBRE, SOLO, INTENTOS, urls = "cadena", 0, 0, [arg]
    else:
        NOMBRE = arg.replace(".txt", "")
        urls = [l.strip() for l in (BASE / f"{NOMBRE}.txt").read_text(encoding="utf-8").splitlines() if l.strip().startswith("http")]
    filas = []
    print(f"{'CADENA COMPLETA' if una else 'LOTE RÁPIDO'} · {len(urls)} web(s)", flush=True)
    for i, url in enumerate(urls, 1):
        web = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")[:45]
        print(f"\n[{i}/{len(urls)}] {web}", flush=True)
        f = {"web": web, "url": url}
        c, salida, t1 = correr(["analizar.py", url, "--sin-ojos"], 2400 if una else 1200)
        f["tiempo"] = t1
        if c != 0:
            f["estado"] = "bloqueada" if c == 2 else "falló el análisis"
            m = re.search(r"NO SE PUDO ANALIZAR ESTA WEB\s+(.*)", salida)
            f["nota"] = (m.group(1).strip()[:110] if m else error_real(salida))
            filas.append(f)
            resumen(filas)
            print(f"   ⚠ {f['estado']}: {f['nota']}", flush=True)
            continue
        carpeta = carpeta_de(salida)
        f["carpeta"] = str(carpeta)
        try:
            datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8"))
            f["tipo"] = datos["clasificacion"]["tipo"]
            f["secciones"] = len(datos["secciones"])
            escenas = sum(1 for s in datos["secciones"] if s.get("escena"))
        except Exception:
            f["tipo"], escenas = "?", 0
        c, salida, t2 = correr(["crear.py", str(carpeta)], 900)
        f["tiempo"] += t2
        if c != 0:
            f["estado"], f["nota"] = "falló crear", error_real(salida)
            filas.append(f)
            resumen(filas)
            continue
        c, salida, t3 = correr(["verificar.py", str(carpeta), f"--solo={SOLO}", f"--intentos={INTENTOS}"], 7200 if una else 2400)
        f["tiempo"] += t3
        m = re.search(r"Parecido medio (\d+)% · lista media (\d+)% · aprobadas (\d+)/(\d+)", salida)
        if not m:
            f["estado"], f["nota"] = "falló verificar", error_real(salida)
        else:
            f.update(estado="ok", parecido=int(m.group(1)), lista=int(m.group(2)), aprobadas=f"{m.group(3)}/{m.group(4)}",
                     nota=(f"{escenas} escena(s) 3D/vídeo · " if escenas else "") + f"{f.get('secciones', '?')} secciones en total")
        filas.append(f)
        resumen(filas)
        print(f"   -> {f.get('parecido', '—')}% parecido · lista {f.get('lista', '—')}% · {f['tiempo'] // 60} min", flush=True)
    print(f"\nTerminado. Resumen: {SALIDA / ('resumen_' + NOMBRE + '.md')}", flush=True)


if __name__ == "__main__":
    main()

