r"""
NOVA · APRENDIDO (23/11/2026, Claude, con el usuario: "que lo que aprende lo lea antes de picar codigo").

UNA entrada y UN dataset:
  - Entrada: memory\inbox_lecciones.md (quejas del usuario, lecciones de Nova y correcciones de Claude, una linea:
    `- [AAAA-MM-DD] [tema] (de: usuario|nova|claude) cuando ... -> hacer en su lugar`).
  - Dataset: memory\aprendido.jsonl (una regla por error; si se repite, sube 'veces'). Lo actualiza el /destilar
    (Claude) entrada a entrada, nunca reescribiendolo entero.
  - Lo que LEE Nova: el bloque "Errores que ya cometiste" de cada kit de carril (y de index-nova-core para el tema
    nova). Lo escribe este script: `kits`. No se edita a mano.

Uso:
  <PYTHON> nova_aprendido.py kits                  # regenera los bloques de los kits
  <PYTHON> nova_aprendido.py buscar web css        # reglas de un tema que contengan una palabra
  <PYTHON> nova_aprendido.py estado                # resumen + inbox pendiente + candidatas a freno
"""

import json
import re
import sys
from pathlib import Path

GEMINI = Path.home() / ".gemini"
MEMORIA = GEMINI / "antigravity" / "memory"
DATASET = MEMORIA / "aprendido.jsonl"
INBOX = MEMORIA / "inbox_lecciones.md"
CARRILES = GEMINI / "antigravity" / "herramientas" / "carriles"
TEMAS = ("web", "backend", "consola", "redaccion", "investigacion", "video", "rea", "nova")
KIT = {t: CARRILES / f"carril_{t}.md" for t in TEMAS if t != "nova"}
KIT["nova"] = GEMINI / "config" / "skills" / "index-nova-core" / "SKILL.md"
INICIO, FIN = "<!-- ERRORES_YA_COMETIDOS:INICIO -->", "<!-- ERRORES_YA_COMETIDOS:FIN -->"
MAX_EN_KIT = 8
AVISO_INBOX = 15  # a partir de aqui toca /destilar
CAMPOS = ("id", "tema", "origen", "cuando", "error", "regla", "comprobacion", "veces", "fechas", "prioridad", "estado")
PESO = {"alta": 0, "media": 1, "baja": 2}


def cargar() -> list[dict]:
    reglas = []
    for n, linea in enumerate(DATASET.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        r = json.loads(linea)
        falta = [c for c in CAMPOS if c not in r]
        if falta or r["tema"] not in TEMAS:
            raise ValueError(f"aprendido.jsonl linea {n}: campos {falta} o tema '{r.get('tema')}' no valido")
        reglas.append(r)
    return reglas


def orden(r: dict) -> tuple:
    return (PESO.get(r["prioridad"], 1), -int(r["veces"]), "".join(sorted(r["fechas"])[-1:]) and
            -int(sorted(r["fechas"])[-1].replace("-", "")))


def bloque(tema: str, reglas: list[dict]) -> str:
    activas = sorted((r for r in reglas if r["tema"] == tema and r["estado"] == "activa"), key=orden)
    en_codigo = [r for r in reglas if r["tema"] == tema and r["estado"] == "en_codigo"]
    lineas = [INICIO, "## Errores que ya cometiste (no los repitas)",
              f"_Lo genera `nova_aprendido.py kits` desde `memory\\aprendido.jsonl`: no lo edites a mano._"]
    for r in activas[:MAX_EN_KIT]:
        lineas.append(f"- **Cuando {r['cuando']}:** {r['regla']}. Comprueba: {r['comprobacion']}. "
                      f"_(x{r['veces']}, {r['id']})_")
    if not activas:
        lineas.append("- (sin errores apuntados todavia en este tema)")
    if en_codigo:
        lineas.append("- Ya te frena el hook (no hace falta recordarlo): " +
                      "; ".join(f"{r['id']} {r['cuando']}" for r in en_codigo[:4]) + ".")
    resto = len(activas) - MAX_EN_KIT
    if resto > 0:
        lineas.append(f"- Hay {resto} mas: `<PYTHON> <NOVA_HOME>/nova_core/nova_aprendido.py buscar "
                      f"{tema} <palabra>`.")
    lineas.append(FIN)
    return "\n".join(lineas)


def kits() -> None:
    reglas = cargar()
    for tema, ruta in KIT.items():
        if not ruta.exists():
            print(f"  (sin kit para {tema}: {ruta.name})")
            continue
        texto = ruta.read_text(encoding="utf-8")
        nuevo = bloque(tema, reglas)
        if INICIO in texto and FIN in texto:
            texto = re.sub(re.escape(INICIO) + r".*?" + re.escape(FIN), lambda _m: nuevo, texto, flags=re.S)
        else:
            texto = texto.rstrip() + "\n\n" + nuevo + "\n"
        ruta.write_text(texto, encoding="utf-8", newline="")
        n = sum(1 for r in reglas if r["tema"] == tema and r["estado"] == "activa")
        print(f"  {ruta.name:24} {min(n, MAX_EN_KIT)}/{n} reglas activas | {len(texto.splitlines())} lineas")


def pendientes_inbox() -> int:
    try:
        return sum(1 for l in INBOX.read_text(encoding="utf-8").splitlines() if l.startswith("- ["))
    except OSError:
        return 0


def buscar(tema: str, palabra: str = "") -> None:
    for r in sorted(cargar(), key=orden):
        if (tema in ("", "todo", r["tema"])) and palabra.lower() in json.dumps(r, ensure_ascii=False).lower():
            print(f"[{r['id']}] ({r['estado']}, x{r['veces']}) cuando {r['cuando']}\n   -> {r['regla']}\n"
                  f"   comprueba: {r['comprobacion']}")


def estado() -> None:
    reglas = cargar()
    from collections import Counter
    print(f"{len(reglas)} reglas | por tema: {dict(Counter(r['tema'] for r in reglas))}")
    print(f"en codigo (las impone un hook): {sum(r['estado'] == 'en_codigo' for r in reglas)}")
    cand = [r["id"] for r in reglas if r["estado"] == "activa" and int(r["veces"]) >= 3]
    print(f"candidatas a freno de codigo (activas con 3+ veces): {cand or 'ninguna'}")
    n = pendientes_inbox()
    print(f"inbox sin destilar: {n} lecciones" + (" -> TOCA /destilar" if n >= AVISO_INBOX else ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:] or ["estado"]
    if a[0] == "kits":
        kits()
    elif a[0] == "buscar":
        buscar(a[1] if len(a) > 1 else "", " ".join(a[2:]))
    else:
        estado()
