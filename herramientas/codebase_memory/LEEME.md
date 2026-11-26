# codebase-memory-mcp (MCP "codebase") · radiografía de proyectos

Funciona en **Windows, macOS (Intel y Apple Silicon) y Linux (x64 y ARM)**.

Radiografía de proyectos de código: indexa clases, métodos y quién llama a quién (Java, Python y ~160 lenguajes más) y Nova pregunta al índice en vez de leer archivo por archivo (150-400 tokens por consulta).

- **Programa:** codebase-memory-mcp v0.12.1 (DeusData, licencia MIT, `bin/LICENSE`). **No viene en el repo**: se instala una vez por equipo con
  `<PYTHON> "<NOVA_HOME>/antigravity/herramientas/codebase_memory/instalar.py"`
  (baja ~50 MB de GitHub, elige la versión de tu sistema y comprueba su suma SHA-256: si no coincide, no instala).
- **Índices:** `.cache/` (uno por equipo). No escribe nada dentro de tus proyectos.
- **Encendido:** el MCP va APAGADO. `nova_hook_turno.py` lo enciende (`scripts/nova_mcp.py activar codebase`, que crea la entrada en tu `mcp_config.json` si no existe) cuando pides "revisa el proyecto", "quién llama a...", "arquitectura", "refactoriza"..., y se apaga al cerrar Antigravity. Si el programa no está instalado, no se enciende y Nova te da el comando de arriba.
- **Cómo lo usa Nova:** kit `herramientas/carriles/carril_backend.md`, apartado 1b.
- **Antivirus:** el proyecto avisa de un falso positivo en Windows Defender (`Trojan:Script/Wacatac.B!ml`). Nunca añadas exclusiones a ciegas: si lo aparta, el instalador lo dice y Nova sigue sin la radiografía.
- **RADIOGRAFÍA: `radiografia.py`** usa el mismo programa en modo CLI (sin encender el MCP ni reabrir Antigravity):
  - `analizar <carpeta> [--explicar] [--excluir a,b] [--profundidad N] [--nombre X]` → `documentos_generados/radiografias/<fecha>_<nombre>/RADIOGRAFIA.md` + `datos.json`. Agrupa los archivos en piezas (carpetas; quita `src/main/java`), dependencias entre piezas (llamadas + imports), ciclos (Tarjan), cohesión e inestabilidad (Ce/(Ca+Ce)) y un veredicto por pieza (INDEPENDIENTE / BASE / ACOPLADA / NUDO / AISLADA). Además: funciones más llamadas desde otros archivos (frágiles), complejidad cognitiva, duplicados (≥ 85 %) y código muerto. `--explicar` = Qwen local, 1-2 frases por pieza.
  - `impacto <proyecto> <funcion>` (quién depende de esa función, con riesgo) · `cambios <proyecto>` (impacto de lo que hay sin commit en git) · `proyectos`.
  - `mapa` = visor web en http://127.0.0.1:9749; se cierra solo a los 60 min (`--minutos N`); `mapa --cerrar` lo para.
  - Los proyectos del índice se llaman `rx_<nombre>`.
