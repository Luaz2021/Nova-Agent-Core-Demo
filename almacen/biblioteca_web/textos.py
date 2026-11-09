"""
TEXTOS · Qwen escribe SOLO los textos que faltan en datos.json, dentro de los limites de cada hueco (0 tokens de nube)

    python textos.py datos.json [--salida datos_completos.json]

Reglas (skill ux-writing + no inventar):
- Solo huecos de texto vacios: eslogan, descripcion del negocio, descripcion de cada destacado, texto de reservar.
- Limites de largo por hueco (los bloques estan disenados para esos largos).
- PROHIBIDO meter datos: ni precios, ni cifras, ni direcciones, ni telefonos, ni premios, ni anos de historia.
  Si Qwen mete un numero o un dato que no esta en datos.json, ese texto se descarta y queda [PENDIENTE].
- Lo generado se marca en "_generado" para que el usuario sepa que textos revisar.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".gemini" / "nova_core"))

LIMITES = {"eslogan": 40, "descripcion": 170, "destacado": 120, "reservar": 140}

SISTEMA = (
    "Eres redactor web de negocios locales en espanol de Espana. Escribes con frases cortas, concretas y calidas, "
    "sin cliches de IA (nada de 'experiencia unica', 'pasion', 'descubre', 'sumergete', 'el lugar perfecto'). "
    "Nunca inventas datos: ni precios, ni numeros, ni anos, ni premios, ni direcciones, ni telefonos. "
    "Devuelves SOLO un JSON valido, sin texto alrededor."
)


def huecos(datos: dict) -> dict:
    n = datos.get("negocio") or {}
    h = {}
    if not n.get("eslogan"):
        h["eslogan"] = (f"titular de portada de 2 a 5 palabras, maximo {LIMITES['eslogan']} caracteres. NO repitas el nombre ni el "
                        "barrio: una idea propia del negocio (ej. para un cafe lento: 'El cafe, sin prisa'; para una panaderia "
                        "de masa madre: 'Pan que se toma su tiempo')")
    if not n.get("descripcion"):
        h["descripcion"] = f"1 o 2 frases (maximo {LIMITES['descripcion']} caracteres) que expliquen que es y por que venir"
    for i, x in enumerate(datos.get("destacados") or []):
        if not x.get("descripcion"):
            h[f"destacado_{i}"] = (f"1 frase (maximo {LIMITES['destacado']} caracteres) sobre '{x.get('nombre')}' "
                                   f"({x.get('etiqueta', '')}); NO empieces por su nombre, ya va en el titulo")
    if not (datos.get("_textos") or {}).get("reservar") and ((datos.get("reservas") or {}).get("valor") or n.get("telefono")):
        h["reservar"] = f"1 frase (maximo {LIMITES['reservar']} caracteres) invitando a reservar o llamar"
    return h


def contexto(datos: dict) -> str:
    n = datos.get("negocio") or {}
    partes = [f"Negocio: {n.get('nombre', '')} · {n.get('tipo', '')} · {n.get('barrio', '')} {n.get('ciudad', '')}".strip()]
    if n.get("notas"):
        partes.append(f"Notas del dueno: {n['notas']}")
    if datos.get("destacados"):
        partes.append("Destacados: " + "; ".join(f"{x.get('nombre')} ({x.get('etiqueta', '')})" for x in datos["destacados"]))
    return "\n".join(partes)


def dato_nuevo(texto: str, datos: dict) -> bool:
    """True si el texto mete numeros, precios o contactos que no estan en datos.json (posible invento)."""
    base = json.dumps(datos, ensure_ascii=False).lower()
    for m in re.finditer(r"\d[\d.,:]*|€|\$|@|https?://|www\.", texto):
        if m.group(0).lower() not in base:
            return True
    return False


def completar(datos: dict, modelo: str = "") -> tuple[dict, list[str], list[str]]:
    """(datos con textos, claves generadas, avisos)."""
    from ollama_comun import ensure_ollama_service, generar_qwen

    pedir = huecos(datos)
    if not pedir:
        return datos, [], []
    if not ensure_ollama_service():
        return datos, [], ["Ollama no responde: los textos quedan [PENDIENTE] (freno, sin nube)"]
    if not modelo:
        try:
            modelo = json.loads((Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json").read_text(encoding="utf-8"))["coder"]
        except Exception:
            modelo = "qwen3.5:9b"
    prompt = (f"{contexto(datos)}\n\nEscribe estos textos. Devuelve un JSON con exactamente estas claves:\n"
              + "\n".join(f'- "{k}": {v}' for k, v in pedir.items()))
    respuesta, cortado = generar_qwen(prompt, modelo, sistema=SISTEMA, num_predict=1200, num_ctx=8192, temperatura=0.5)
    m = re.search(r"\{.*\}", respuesta, re.S)
    try:
        nuevos = json.loads(m.group(0)) if m and not cortado else {}
    except ValueError:
        nuevos = {}
    avisos, generados = [], []
    datos = json.loads(json.dumps(datos))  # copia
    n = datos.setdefault("negocio", {})
    for clave in pedir:
        texto = str(nuevos.get(clave) or "").strip().strip('"')
        if clave.startswith("destacado_"):  # quita "Nombre: " si lo repite igualmente
            nombre = str(datos["destacados"][int(clave.split("_")[1])].get("nombre", ""))
            if nombre and texto.lower().startswith(nombre.lower()):
                texto = texto[len(nombre):].lstrip(" :,-–").strip()
                texto = texto[:1].upper() + texto[1:]
        limite = LIMITES["destacado" if clave.startswith("destacado_") else clave]
        if not texto:
            avisos.append(f"Qwen no escribio '{clave}': queda [PENDIENTE]")
            continue
        if len(texto) > limite * 1.15:
            avisos.append(f"'{clave}' demasiado largo ({len(texto)} > {limite}): queda [PENDIENTE]")
            continue
        if dato_nuevo(texto, datos):
            avisos.append(f"'{clave}' metia un dato que no esta en los datos ({texto[:60]}): descartado")
            continue
        if clave in ("eslogan", "descripcion"):
            n[clave] = texto
        elif clave == "reservar":
            datos.setdefault("_textos", {})["reservar"] = texto
        else:
            datos["destacados"][int(clave.split("_")[1])]["descripcion"] = texto
        generados.append(clave)
    datos["_generado"] = sorted(set(datos.get("_generado", []) + generados))
    return datos, generados, avisos


def main() -> int:
    ap = argparse.ArgumentParser(description="Qwen escribe los textos que faltan (sin inventar datos)")
    ap.add_argument("datos")
    ap.add_argument("--salida", default="")
    a = ap.parse_args()
    datos = json.loads(Path(a.datos).read_text(encoding="utf-8"))
    nuevos, generados, avisos = completar(datos)
    salida = Path(a.salida or Path(a.datos).with_name("datos_completos.json"))
    salida.write_text(json.dumps(nuevos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[TEXTOS] escritos por Qwen: {', '.join(generados) or 'ninguno'} -> {salida}")
    for x in avisos:
        print(f"[TEXTOS] aviso: {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
