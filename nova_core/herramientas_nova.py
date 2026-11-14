"""
Puente directo del Orquestador Nova-Core para el Chat de Antigravity (Sin API externa).

Recibe el archivo o los archivos que Alexander pasa por el chat, ejecuta las
herramientas locales (leer_fragmento, editar_archivo, crear_archivo, revisar, deshacer)
y controla el limite de 3 vueltas por archivo en local (0 tokens).

Uso directo desde el chat de Nova:
    python herramientas_nova.py revisar archivo1.py [archivo2.ts carpeta/ ...]
    python herramientas_nova.py fragmento archivo.py 1 80
    python herramientas_nova.py editar cambio.json
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

import orquestador as o

# Regla corta de referencia (el detalle completo vive en REGLAS_KISS_2026.md)
REGLA_KISS = (
    "KISS = el cambio minimo que resuelve la tarea, con sintaxis moderna del lenguaje. "
    "Nunca reescribas archivos: usa editar_archivo con fragmentos exactos. "
    "Versiones: Python 3.14, JS ES2025 (Node 24), TS 5.9, React 19, Java 21, C# 14, PHP 8.5, Dart 3.13. "
    "Si el linter avisa de sintaxis antigua, corrigelo; no inventes APIs que no existan en esas versiones."
)


class ControlVueltas:
    """Cuenta las vueltas modelo <-> linter por archivo para no entrar en bucle."""

    def __init__(self, maximo: int = o.MAX_VUELTAS):
        self.maximo = maximo
        self.vueltas = Counter()
        self.agotado = False

    def registrar(self, archivo: str, limpio: bool) -> None:
        if limpio:
            self.vueltas[archivo] = 0
            return
        self.vueltas[archivo] += 1
        if self.vueltas[archivo] >= self.maximo:
            self.agotado = True


def ejecutar(nombre: str, entrada: dict, control: ControlVueltas | None = None) -> str:
    """Ejecuta una accion sobre el archivo o los archivos pasados por el chat y devuelve texto limpio."""
    try:
        if nombre == "leer_fragmento":
            r = o.leer_fragmento(**entrada)
            return r["fragmento"] + f"\n(total {r['total_lineas']} lineas)"
        if nombre == "revisar":
            archivos = entrada.get("archivos") or [entrada["archivo"]]
            r = (
                o.revisar(archivos[0])
                if len(archivos) == 1 and Path(archivos[0]).is_file()
                else o.revisar_lote(archivos)
            )
            return o.avisos_para_modelo(r)
        if nombre == "editar_archivo":
            r = o.editar_archivo(**entrada)
        elif nombre == "crear_archivo":
            r = o.crear_archivo(**entrada)
        elif nombre == "deshacer":
            r = o.deshacer(entrada["archivo"])
            return (
                f"Restaurado: {r.get('restaurado_desde')}"
                if r.get("ok")
                else f"ERROR: {r.get('error')}"
            )
        else:
            return f"ERROR: accion desconocida {nombre}"
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"

    texto = o.avisos_para_modelo(r)
    if control and r.get("ok"):
        control.registrar(entrada["archivo"], r.get("limpio", True))
        if control.agotado:
            texto += f"\nSE ALCANZO EL MAXIMO DE {control.maximo} VUELTAS. Para y explica al usuario que falta."
    return texto


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    orden = sys.argv[1]
    if orden == "revisar":
        print(ejecutar("revisar", {"archivos": sys.argv[2:]}))
    elif orden == "fragmento":
        desde = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        hasta = int(sys.argv[4]) if len(sys.argv) > 4 else None
        print(
            ejecutar(
                "leer_fragmento",
                {"archivo": sys.argv[2], "desde": desde, "hasta": hasta},
            )
        )
    elif orden == "editar":
        datos = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print(ejecutar("editar_archivo", datos))
    elif orden == "deshacer":
        print(ejecutar("deshacer", {"archivo": sys.argv[2]}))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
