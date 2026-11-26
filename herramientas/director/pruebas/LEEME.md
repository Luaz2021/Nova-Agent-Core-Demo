# Pruebas del director sin gastar cupo

`agy_falso.py` imita a la CLI agy (planos, obra, inspeccion, arreglo...). Desde una carpeta vacia:

Windows (PowerShell):
```powershell
$env:DIRECTOR_AGY = "$env:USERPROFILE\.gemini\antigravity\herramientas\director\pruebas\agy_falso.py"
$env:DIRECTOR_SIN_ESCANERES = "1"
& $env:NOVA_PYTHON "$env:USERPROFILE\.gemini\antigravity\herramientas\director\nova_director.py" todo "<carpeta vacia>" --idea "$env:USERPROFILE\.gemini\antigravity\herramientas\director\pruebas\idea.md"
```

macOS / Linux (bash o zsh):
```bash
export DIRECTOR_AGY="$HOME/.gemini/antigravity/herramientas/director/pruebas/agy_falso.py"
export DIRECTOR_SIN_ESCANERES=1
"$HOME/.gemini/nova_env/bin/python" "$HOME/.gemini/antigravity/herramientas/director/nova_director.py" todo "<carpeta vacia>" --idea "$HOME/.gemini/antigravity/herramientas/director/pruebas/idea.md"
```

Variantes (misma variable en las dos shells): `SIM_V4=1` (preguntas -> respuestas.md -> continuar -> pausa de diseno:
crear estudio.txt -> continuar), `AGY_F2_NUNCA=1` (escalera hasta parar), `DIRECTOR_TELEMETRIA=<jsonl con un freno del
conv "conv-179">` (pausa por freno del hook en vez de escalar). Quitar las variables al acabar.
Ojo: el director apunta sus fallos en `memory/registros/director_errores.jsonl`; para no ensuciar tu registro real,
prueba con otra carpeta de usuario (variable USERPROFILE en Windows o HOME en macOS/Linux).
