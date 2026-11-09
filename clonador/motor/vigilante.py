import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
VIGILANTE — deja que Claude lance los scripts mientras tú no estás.

Se queda esperando y cada 5 segundos mira si hay una orden en  workspace/orden.txt
Órdenes permitidas (una por archivo, nada más se ejecuta). Cadena oficial: analizar -> crear -> verificar
    cadena https://web.com          -> python lote.py URL           (las tres seguidas, completas)
    analizar https://web.com [--sin-dinamico]  -> python analizar.py URL  (paso 1)
    crear [web]                     -> python crear.py            (paso 2: base del clon, sin IA)
    verificar [web] [--solo=10] [--umbral=90] [--lista=90]  -> python verificar.py (paso 3: Qwen repara)
    vestir                          -> python construir.py --vestir
    lote [nombre]                   -> python lote.py nombre      (muchas webs, modo rápido)
    construir_legado [--umbral=75]  -> python construir.py --legacy   (cadena antigua retirada: Qwen desde cero)
    crear_cero nara                 -> python crear_cero.py nara  (web desde cero, prueba_creacion/nara)
([web] = carpeta dentro de workspace/, p. ej. apple_com_es_mac; sin ella, el último análisis. La lista está en
ordenes.py y se recarga sola.)
Mientras trabaja escribe workspace/estado_vigilante.txt y el registro completo en workspace/registro_vigilante.txt.
Para pararlo: cierra la ventana.
"""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.dont_write_bytecode = True
CARPETA = BASE.parent / "workspace"
ORDEN = CARPETA / "orden.txt"
ESTADO = CARPETA / "estado_vigilante.txt"
REGISTRO = CARPETA / "registro_vigilante.txt"


def estado(txt):
    ESTADO.write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} · {txt}\n", encoding="utf-8")
    print(f"[{time.strftime('%H:%M:%S')}] {txt}", flush=True)


def traducir(linea):
    """Las órdenes permitidas viven en ordenes.py y se recargan cada vez (así se pueden añadir sin reiniciar)."""
    import importlib
    import ordenes
    importlib.reload(ordenes)
    return ordenes.traducir(linea)


def mantener_despierto():
    """Mientras el vigilante esté abierto, Windows no suspende el PC ni apaga la pantalla
    (lo mismo que hace un reproductor de vídeo). No cambia ninguna configuración: al cerrar la ventana, todo vuelve a lo normal."""
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        return True
    except Exception:
        return False


def main():
    CARPETA.mkdir(exist_ok=True)
    if mantener_despierto():
        print("PC despierto mientras esta ventana siga abierta (sin suspensión ni pantalla apagada).", flush=True)
    estado("esperando órdenes (deja esta ventana abierta)")
    while True:
        if ORDEN.exists():
            linea = ORDEN.read_text(encoding="utf-8").strip()
            ORDEN.unlink()
            cmd = traducir(linea)
            if not cmd:
                estado(f"orden rechazada: {linea[:80]!r}")
            else:
                estado(f"ejecutando: {linea}")
                with REGISTRO.open("a", encoding="utf-8") as reg:
                    reg.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} · {linea} =====\n")
                    reg.flush()
                    proc = subprocess.Popen(cmd, cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, encoding="utf-8", errors="replace")
                    for l in proc.stdout:
                        print(l, end="", flush=True)
                        reg.write(l)
                        reg.flush()
                    proc.wait()
                estado(f"terminado ({'bien' if proc.returncode == 0 else 'código ' + str(proc.returncode)}): {linea} · esperando órdenes")
        time.sleep(5)


if __name__ == "__main__":
    main()
