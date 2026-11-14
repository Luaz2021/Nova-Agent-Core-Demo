"""Revision de LOGICA con Qwen en local (0 tokens de nube). 12/11/2026, Claude.

Qwen lee el documento entero (y los requisitos del enunciado, si los hay) y devuelve:
- requisitos que el texto NO responde de verdad (aunque la seccion diga que los cubre)
- contradicciones entre partes del documento
- frases sin sentido o que no se entienden
Solo AVISA: un modelo local se puede equivocar, la decision es de Alexander.
"""

import json
import re

from .base import qwen

SISTEMA = (
    "Eres un profesor de FP que revisa el trabajo de un alumno antes de que lo entregue. Eres exigente pero justo. "
    "Respondes SOLO con un JSON valido, sin texto antes ni despues."
)
MAX_CARACTERES = 18000  # ~5k tokens: cabe en los 8k de contexto de Qwen con el prompt


def revisar(texto: str, requisitos: list[dict] | None = None) -> list[str]:
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.DOTALL).strip()
    if len(texto) > MAX_CARACTERES:
        texto = (
            texto[:MAX_CARACTERES] + "\n[...documento recortado para la revision...]"
        )
    obligatorios = [
        r for r in (requisitos or []) if r["clase"] not in ("entrega", "ayuda")
    ]
    lista = (
        "\n".join(f"{r['id']}: {r['texto']}" for r in obligatorios) or "(sin enunciado)"
    )
    prompt = (
        f"REQUISITOS DEL ENUNCIADO:\n{lista}\n\nDOCUMENTO DEL ALUMNO:\n{texto}\n\n"
        "Revisa el documento y responde con este JSON:\n"
        '{"no_responde": [{"id": "R3", "motivo": "..."}], '
        '"contradicciones": ["..."], "sin_sentido": ["frase exacta del documento"]}\n'
        "Reglas: en no_responde pon solo requisitos que de verdad no se contestan. En sin_sentido copia la frase "
        "tal cual aparece. Si todo esta bien, listas vacias."
    )
    try:
        salida = qwen(prompt, SISTEMA, max_tokens=900)
    except Exception as e:  # Ollama apagado: no frena la exportacion
        return [
            f"[LÓGICA] No se pudo revisar con Qwen ({e.__class__.__name__}). Ejecuta el Doctor."
        ]
    m = re.search(r"\{.*\}", salida, re.DOTALL)
    try:
        datos = json.loads(m.group(0)) if m else {}
    except ValueError:
        return ["[LÓGICA] Qwen no devolvió una revisión legible; revísalo a ojo."]
    avisos = [
        f"[LÓGICA] {r.get('id', '?')} no se responde: {r.get('motivo', '')}"
        for r in datos.get("no_responde", [])
        if isinstance(r, dict)
    ]
    avisos += [
        f"[LÓGICA] Contradicción: {c}" for c in datos.get("contradicciones", []) if c
    ]
    avisos += [
        f"[LÓGICA] No se entiende: «{f}»" for f in datos.get("sin_sentido", []) if f
    ]
    return avisos
