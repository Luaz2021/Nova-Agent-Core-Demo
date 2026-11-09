# clones_web — motor de clonación de webs

Organizado el 2026-11-08. Esta carpeta es la copia de trabajo buena (no la de `.gemini/antigravity/motor_clones`).

| Carpeta | Qué es |
|---|---|
| `motor/` | El motor. Cadena oficial: `1_ANALIZAR` → `2_CREAR` → `3_VERIFICAR` (o `CLONAR.bat` para todo). Pendientes en `motor/PENDIENTES_MOTOR.md`. |
| `herramientas/` | Utilidades fuera del motor (`exportar_react.py`: clon → `datos_web.ts` para React). |
| `workspace/` | Salida de cada web clonada (`workspace/<web>/`). No va a git (pesa ~335 MB). |
| `autopsias_dataset/` | Fallos de Qwen recogidos para entrenar. Lo usa `motor/autopsia_collector.py`. |
| `archivo/` | Copias viejas y scripts sueltos. No se usan. Lista de lo movido en `archivo/MOVIMIENTOS_2026-11-08.txt`. |

## Modelos (Ollama)
Se leen de `~/.gemini/antigravity/scripts/nova_modelos.json` (claves `coder` y `vl`).
Por defecto: `qwen3.5:9b` (código) y `blaifa/InternVL3_5:8b` (ojos).

## Medir el motor sin IA
`python motor/verificar.py workspace/<web> --intentos=0`
