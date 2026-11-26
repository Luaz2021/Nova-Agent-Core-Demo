"""Simulador de la CLI agy para probar nova_director.py sin gastar cupo."""
import json
import re
import sys
import time
from pathlib import Path

args = sys.argv[1:]
prompt = args[args.index("-p") + 1]
modelo = args[args.index("--model") + 1]
conv = args[args.index("--conversation") + 1] if "--conversation" in args else f"conv-{time.time_ns()}"
rol = re.search(r"\[NOVA DIRECTOR · ([^\]]+)\]", prompt).group(1)
d = Path(".director")
cont = Path(".contador_" + re.sub(r"\W", "_", rol.split(" intento")[0]))
n = int(cont.read_text()) + 1 if cont.exists() else 1
cont.write_text(str(n))
Path(".registro_agy.txt").open("a").write(f"{time.time():.1f} {rol} | {modelo} | {conv[:12]}\n")

import os  # noqa: E402


def existe(archivo: str) -> str:
    """Criterio "el archivo existe" en la shell del sistema (v3.3: PowerShell en Windows, bash en macOS/Linux)."""
    return (f"if (Test-Path {archivo}) {{ exit 0 }} else {{ exit 1 }}" if os.name == "nt" else f"test -f {archivo}")

if rol == "PLANOS" and os.environ.get("SIM_V4"):
    paquete = Path(re.search(r"paquete (.+?\.md)", prompt).group(1)).read_text(encoding="utf-8")
    assert "CATALOGO DE HERRAMIENTAS" in paquete, "falta el catalogo"
    (d / "spec.md").write_text("# Spec\nR1 CUANDO ... EL SISTEMA DEBE ...\n", encoding="utf-8")
    if "RESPUESTAS DEL USUARIO" not in paquete:  # 1a vez: pregunta
        (d / "preguntas.json").write_text(json.dumps({"bloqueantes": ["MySQL o SQL Server?"], "supuestos": []}),
                                          encoding="utf-8")
    else:
        (d / "preguntas.json").write_text(json.dumps({"bloqueantes": [], "supuestos": ["MySQL"]}), encoding="utf-8")
        (d / "arquitectura.md").write_text("# Arquitectura\n", encoding="utf-8")
        (d / "fases.json").write_text(json.dumps({"ruta": "con_ui", "fases": [
            {"id": "F1", "titulo": "back", "objetivo": "crear a.py", "herramienta": "obra", "archivos": ["a.py"],
             "depende_de": [], "criterios": [existe("a.py")], "critica": True},
            {"id": "F2", "titulo": "diseno", "objetivo": "tokens del estudio", "herramienta": "pausa",
             "instrucciones_nova": "estudio.py ficha + validar; vale del usuario", "archivos": ["estudio.txt"],
             "depende_de": [], "criterios": [existe("estudio.txt")]},
            {"id": "F3", "titulo": "front", "objetivo": "crear c.py", "herramienta": "obra", "archivos": ["c.py"],
             "depende_de": ["F1", "F2"], "criterios": [existe("c.py")]}]}),
            encoding="utf-8")
elif rol == "PLANOS":
    (d / "arquitectura.md").write_text("# Arquitectura\n- a.py, b.py, c.py\n", encoding="utf-8")
    (d / "fases.json").write_text(json.dumps({"fases": [
        {"id": "F1", "titulo": "A", "objetivo": "crear a.py", "archivos": ["a.py"], "depende_de": [],
         "criterios": [existe("a.py")], "critica": False},
        {"id": "F2", "titulo": "B", "objetivo": "crear b.py", "archivos": ["b.py"], "depende_de": [],
         "criterios": [existe("b.py")], "critica": True},
        {"id": "F3", "titulo": "C", "objetivo": "crear c.py", "archivos": ["c.py"], "depende_de": ["F1", "F2"],
         "criterios": [existe("c.py")], "critica": False}]}), encoding="utf-8")
elif rol.startswith("OBRA F1"):
    time.sleep(2)
    Path("a.py").write_text("A = 1\n")
elif rol.startswith("OBRA F2"):
    time.sleep(2)
    if n >= 2 and not __import__("os").environ.get("AGY_F2_NUNCA"):  # el 1er intento "se le olvida": prueba el 2o intento en la misma conversacion
        Path("b.py").write_text("SECRETO = 'dev'\n")
elif rol.startswith("OBRA F3"):
    Path("c.py").write_text("from a import A\n")
elif rol.startswith("INSPECCION paso 1"):
    (d / "hallazgos.json").write_text(json.dumps({"hallazgos": [
        {"id": "H1", "gravedad": "alta", "archivo": "b.py", "linea": 1, "problema": "clave fija", "arreglo": "variable"},
        {"id": "H2", "gravedad": "critica", "archivo": "a.py", "linea": 1, "problema": "registro abierto",
         "arreglo": "cerrar", "contradice_enunciado": True}],
        "zonas_criticas": ["b.py", "no_existe.py"], "veredicto": "no apto"}), encoding="utf-8")
    (d / "INSPECCION.md").write_text("# Inspeccion\nNo apto\n", encoding="utf-8")
elif rol.startswith("INSPECCION paso 2"):
    pq = (d / "paquete_inspeccion_profunda.md").read_text(encoding="utf-8")
    assert "### b.py" in pq and "### no_existe.py" not in pq, "zonas mal"
    h = json.loads((d / "hallazgos.json").read_text(encoding="utf-8"))
    h["hallazgos"].append({"id": "H3", "gravedad": "critica", "archivo": "b.py", "linea": 1, "problema": "NaN 500",
                           "arreglo": "validar", "de": "profunda"})
    (d / "hallazgos.json").write_text(json.dumps(h), encoding="utf-8")
    with open(d / "INSPECCION.md", "a", encoding="utf-8") as f:
        f.write("\n## Revision profunda\nH3\n")
elif rol == "ARREGLO HALLAZGOS":
    Path("b.py").write_text("import os\nSECRETO = os.environ['SECRETO']\n")
elif rol == "REINSPECCION":
    (d / "hallazgos.json").write_text(json.dumps({"hallazgos": [], "veredicto": "apto"}), encoding="utf-8")
    with open(d / "INSPECCION.md", "a", encoding="utf-8") as f:
        f.write("\n## Reinspeccion\nH1 arreglado.\n")

print(json.dumps({"conversation_id": conv, "status": "ok", "response": f"{rol} hecho",
                  "usage": {"input_tokens": 3000, "cache_read_tokens": 20000 if "--conversation" in args else 0,
                            "output_tokens": 500}}))
