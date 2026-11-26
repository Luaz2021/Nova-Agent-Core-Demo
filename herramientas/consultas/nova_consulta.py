"""Consultas de ventana de la PIRAMIDE de Nova (20/11/2026, Claude; idea del usuario).

Hydrogen (la ventana base; Flash hasta el 24/11, se retira el 30/11) nunca cambia de modelo, asi conserva su cache. Cuando algo no sale ni con el asesor, Nova
escribe UNA consulta corta (texto plano) y el usuario abre una ventana nueva con un modelo pesado que solo lee esa
consulta y los archivos que nombra, responde en respuesta.md y se cierra. "Los pesados entran, resuelven y se van."

Escalera:  carbon -> neon -> opus -> claude   (24/11: Argon se retira el 30/11 -> Carbon; "argon" se acepta como alias)   (atajo: --nivel <x> salta directo; lo decide el usuario)

  nueva   --titulo "..." --pregunta "..." [--intentado "..."] [--archivos a,b] [--nivel carbon|neon|opus|claude]
          [--tipo plan]   (ORQUESTADOR CASERO: el pesado escribe PLAN.md con pasos para Hydrogen, en vez de respuesta.md)
  estado                      consultas abiertas y su siguiente nivel
  cerrar  <id> --resultado resuelto|no_resuelto [--nota "..."]   (no_resuelto -> propone el siguiente nivel)

Datos: memory\\consultas\\<id>\\consulta.md + respuesta.md, y memory\\consultas\\estado.json (viaja con la memoria).
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

DIR = Path.home() / ".gemini" / "antigravity" / "memory" / "consultas"
ESTADO = DIR / "estado.json"
INBOX = Path.home() / ".gemini" / "antigravity" / "memory" / "inbox_lecciones.md"
ESCALERA = ["carbon", "neon", "opus", "claude"]
MODELO = {
    "carbon": "Gemini 4 Carbon (High)",
    "neon": "Gemini 4 Neon (High o Extra)",
    "opus": "Claude Opus 5.5 (UNA sola consulta: gasta x10 en el cupo de Claude)",
    "claude": "Claude Code, fuera de Antigravity (pasale la carpeta de la consulta)",
}


def leer() -> dict:
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"consultas": {}}


def guardar(e: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", t.lower())[:40].strip("_") or "consulta"


def siguiente(niveles_fallidos: list[str]) -> str | None:
    for n in ESCALERA:
        if n not in niveles_fallidos:
            return n
    return None


def nueva(a) -> None:
    e = leer()
    tema = slug(a.titulo)
    fallidos = [n for c in e["consultas"].values() if c["tema"] == tema and c["resultado"] == "no_resuelto"
                for n in [{"argon": "carbon"}.get(c["nivel"], c["nivel"])]]
    a.nivel = "carbon" if a.nivel == "argon" else a.nivel  # 24/11: Argon se retira el 30/11
    nivel = a.nivel or siguiente(fallidos)
    if not nivel:
        print("ESCALERA AGOTADA: Carbon, Neon, Opus y Claude ya lo intentaron. Dile al usuario que hay que replantearlo.")
        return
    if nivel in fallidos and not a.nivel:
        nivel = siguiente(fallidos)
    cid = f"{time.strftime('%Y%m%d-%H%M%S')}_{tema}"
    carpeta = DIR / cid
    carpeta.mkdir(parents=True, exist_ok=True)
    archivos = [x.strip() for x in (a.archivos or "").split(",") if x.strip()]
    previas = [c for c in e["consultas"].values() if c["tema"] == tema]
    if a.tipo == "plan":  # ORQUESTADOR CASERO: el pesado planifica en texto plano, Hydrogen ejecuta en su ventana
        salida, tarea = carpeta / "PLAN.md", (
            f"- Escribe el plan en `{carpeta / 'PLAN.md'}`: pasos NUMERADOS y pequenos que un modelo rapido (Hydrogen) pueda "
            "ejecutar uno a uno, cada uno con: archivos que toca, que hacer y como comprobarlo (comando o test). Al final, "
            "riesgos y 'Definicion de hecho'. Maximo 80 lineas.\n"
            "- Si Hydrogen se atasca, escribira ESTADO.md en esta carpeta y te lo traeran para revisar SOLO eso.\n")
    else:
        salida, tarea = carpeta / "respuesta.md", (
            f"- Escribe tu respuesta en `{carpeta / 'respuesta.md'}` (maximo 40 lineas): decision o arreglo concreto, "
            "por que, riesgo principal y como comprobarlo. Si propones cambios de codigo, como diff o fragmentos cortos.\n")
    (carpeta / "consulta.md").write_text(
        f"# CONSULTA DE VENTANA ({'PLAN' if a.tipo == 'plan' else 'DUDA'}) · {a.titulo}\n\n"
        f"*Nivel: **{nivel}** ({MODELO[nivel]}) · creada {time.strftime('%Y-%m-%d %H:%M')} por Nova (Hydrogen)*\n\n"
        "## Para el modelo que responde (LEE ESTO PRIMERO)\n"
        "- Eres un consultor de paso: lee SOLO esta consulta y los archivos de abajo. No abras la conversacion de Nova.\n"
        + tarea +
        "- NO modifiques ningun otro archivo ni ejecutes nada que cambie el proyecto. Cuando acabes, dilo en una linea.\n\n"
        f"## Pregunta\n{a.pregunta}\n\n"
        f"## Lo que ya se intento\n{a.intentado or '(nada indicado)'}\n\n"
        "## Archivos a mirar\n" + ("\n".join(f"- `{x}`" for x in archivos) or "- (ninguno)") + "\n\n"
        "## Consultas anteriores de este tema\n"
        + ("\n".join(f"- {c['nivel']}: {c['resultado']} {c.get('nota', '')}" for c in previas) or "- (ninguna)") + "\n",
        encoding="utf-8")
    e["consultas"][cid] = {"tema": tema, "titulo": a.titulo, "nivel": nivel, "resultado": "abierta",
                           "creada": time.strftime("%Y-%m-%d %H:%M")}
    guardar(e)
    print(f"CONSULTA CREADA: {carpeta / 'consulta.md'}")
    print(f"Dile al usuario, tal cual: \"Abre una ventana nueva con {MODELO[nivel]} y escribe: "
          f"responde la consulta {carpeta / 'consulta.md'}\". Cuando vuelva, lee {salida}.")


def estado(_a) -> None:
    e = leer()
    abiertas = {k: v for k, v in e["consultas"].items() if v["resultado"] == "abierta"}
    if not abiertas:
        print("Sin consultas abiertas.")
    for k, v in abiertas.items():
        resp = DIR / k / "respuesta.md"
        print(f"- {k} | nivel {v['nivel']} | {'RESPONDIDA' if resp.exists() else 'esperando respuesta'} | {v['titulo']}")


def cerrar(a) -> None:
    e = leer()
    c = e["consultas"].get(a.id)
    if not c:
        print(f"No existe la consulta {a.id}. Usa: estado")
        sys.exit(1)
    c["resultado"], c["nota"], c["cerrada"] = a.resultado, a.nota or "", time.strftime("%Y-%m-%d %H:%M")
    guardar(e)
    with open(INBOX, "a", encoding="utf-8") as f:  # aprendizaje: que nivel hizo falta para que tipo de problema
        f.write(f"- [{time.strftime('%Y-%m-%d')}] [nova] (de: nova) piramide: {c['titulo']} -> {c['nivel']}: "
                f"{a.resultado}{' (' + a.nota + ')' if a.nota else ''}\n")  # 26/11: temas fijos de nova_aprendido
    if a.resultado == "resuelto":
        print(f"Cerrada: resuelto en {c['nivel']}. Leccion apuntada.")
        return
    fallidos = [v["nivel"] for v in e["consultas"].values() if v["tema"] == c["tema"] and v["resultado"] == "no_resuelto"]
    sig = siguiente(fallidos)
    print(f"Cerrada: {c['nivel']} no lo resolvio. " + (
        f"Siguiente nivel: {sig} ({MODELO[sig]}). Crea la consulta con: nova_consulta.py nueva --titulo \"{c['titulo']}\" ..."
        if sig else "Escalera agotada: hay que replantearlo con el usuario."))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="orden", required=True)
    n = s.add_parser("nueva")
    n.add_argument("--titulo", required=True)
    n.add_argument("--pregunta", required=True)
    n.add_argument("--intentado")
    n.add_argument("--archivos")
    n.add_argument("--nivel", choices=ESCALERA + ["argon"])  # 24/11: argon = alias de carbon
    n.add_argument("--tipo", choices=["duda", "plan"], default="duda",
                   help="plan = orquestador casero: el pesado escribe PLAN.md y Hydrogen lo ejecuta")
    n.set_defaults(f=nueva)
    s.add_parser("estado").set_defaults(f=estado)
    c = s.add_parser("cerrar")
    c.add_argument("id")
    c.add_argument("--resultado", required=True, choices=["resuelto", "no_resuelto"])
    c.add_argument("--nota")
    c.set_defaults(f=cerrar)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
