# Nova-Core · orquestador de edición + linter

Principio: **Nova controla cómo se escribe en disco, no el modelo.**

- `orquestador.py` — el motor (offline, sin tokens).
- `herramientas_nova.py` — las 3 herramientas para la API de Anthropic + control de vueltas + regla KISS corta.

## Qué hace

| Situación | Qué responde Nova al modelo |
|---|---|
| Quiere reescribir un archivo que ya existe | Error: usa `editar_archivo` |
| `texto_viejo` no aparece | Error: cópialo exacto, usa `leer_fragmento` |
| `texto_viejo` aparece varias veces | Error: añade líneas de alrededor |
| El cambio toca más del 35 % del archivo (≥ 20 líneas) | Rechazado, `necesita_permiso` |
| Edición correcta | Respaldo → formateador → autofix → solo los avisos que quedan |
| 3 vueltas seguidas con avisos | "Para y explica al usuario qué falta" |

Escalera por archivo (gratis): **formato → autofix → avisos al modelo**.
- Python: `ruff format`, `ruff check --fix`, `ruff check`.
- JS/TS/JSX/JSON/CSS: Biome, buscado por jerarquía: `node_modules` del proyecto → `biome` en el PATH → `npx @biomejs/biome`.

Cada edición guarda copia en `.nova_respaldo/` junto al archivo; `deshacer` vuelve a la anterior.

## Instalar

```
pip install ruff
```
Para JS basta con tener Node (usa `npx`); mejor aún `npm i -D @biomejs/biome` en el proyecto.

## Probar a mano

```
python orquestador.py revisar archivo.py
python orquestador.py fragmento archivo.py 10 40
python orquestador.py editar cambio.json
python orquestador.py deshacer archivo.py
```

## Conectarlo a Nova

```python
from herramientas_nova import HERRAMIENTAS, REGLA_KISS, ControlVueltas, ejecutar

control = ControlVueltas()          # uno por tarea
resp = cliente.messages.create(
    model="claude-haiku-5-5", max_tokens=1024,
    system=REGLA_KISS, tools=HERRAMIENTAS, messages=mensajes,
)
resultados = [
    {"type": "tool_result", "tool_use_id": b.id, "content": ejecutar(b.name, b.input, control)}
    for b in resp.content if b.type == "tool_use"
]
# añadir resp.content como assistant y resultados como user, y repetir
# hasta que no haya tool_use o control.agotado == True (entonces avisar al usuario)
```

Si el resultado trae `necesita_permiso`, Nova te pregunta y, si dices que sí, llama a
`orquestador.editar_archivo(..., permitir_grande=True)`.
