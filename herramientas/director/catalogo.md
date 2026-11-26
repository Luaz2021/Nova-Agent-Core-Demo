# CATÁLOGO DE HERRAMIENTAS DE NOVA (para el planificador; 26/11/2026)

Tarjetas cortas: QUÉ hace, CUÁNDO, qué ENTRA y qué SALE, y cómo se COMPRUEBA. El detalle de cada una está en su LEEME:
léelo solo si lo necesitas. `<PY>` = `<PYTHON>`, `<H>` = `$env:USERPROFILE\.gemini\antigravity\herramientas`.

## Rutas (elige UNA según el encargo)

| Ruta | Cuándo | Cajas, en orden |
|---|---|---|
| **sin_ui** | API, backend, CLI, scripts, BD, servicios | especificar → contrato/arquitectura → obra → pruebas → inspección |
| **con_ui** | app con pantallas (web app, panel, front + back, Android) | especificar → contrato API → back (obra) ∥ **diseño (estudio) → vale del usuario (pausa)** → pantallas (obra, con los tokens) → integración (flujos Playwright + revisar.py) → inspección |
| **web_negocio** | web/landing de un negocio (vende, informa) | NO uses el director: es el estudio web de principio a fin. Escribe 1 fase `pausa` con esa instrucción |
| **clon** | copiar una web existente | NO uses el director: clonador. 1 fase `pausa` |
| **legacy** | cambiar un proyecto que ya existe | radiografía primero (ya viene en el paquete si existe) → fases pequeñas con `impacto` antes de tocar |

Tamaño (no gastes de más): 1-2 archivos → 1 sola fase; mediano → 2-3 fases; grande → 3-5 fases. Nunca más de 6.

## Tarjetas

**obra** (Hydrogen, por defecto) · construye código de una fase · ENTRA: ficha (objetivo, archivos, criterios) ·
SALE: código + criterios en verde · Las fases seguidas comparten conversación (caché). Paralelo SOLO si no comparten
archivos y hay contrato.

**pausa** · algo que necesita al usuario o a Nova con otra herramienta interactiva (diseño, fotos, elegir). El director
para, avisa (Marina) y deja `PAUSA.md` con `instrucciones_nova`. Sigue con `nova_director.py continuar`. Sus
`criterios` comprueban que lo pedido existe (p. ej. `Test-Path estudio\estilos\00_tokens.css`).

**estudio web** (`<H>\estudio_web\estudio.py`) · diseño UX/UI con criterio: ficha (qué compra el cliente, primer
pantallazo, escala), paleta, tipografía, referencias, tokens CSS · SALE: `estudio\ficha.json`, `estudio\estilos\00_tokens.css`.
En la ruta **con_ui** el diseño son DOS fases seguidas, antes de las pantallas:
  1. `diseño` (herramienta `obra`): `<PY> "<H>\estudio_web\estudio.py" ficha "<carpeta>" "<pedido>"`, rellenar
     `estudio\ficha.json` (en una app: `que_compra` = lo que el usuario viene a HACER; `primer_pantallazo` = la pantalla
     principal; 2 referencias reales de apps parecidas; paleta sobria con contraste) y `estudio.py validar "<carpeta>"`.
     Criterios: `<PY> "<H>\estudio_web\estudio.py" validar "<carpeta>"` y `Test-Path estudio\estilos\00_tokens.css`.
  2. `vale de diseño` (herramienta `pausa`): instrucciones_nova = "enseña al usuario el resumen de validar (paleta,
     tipografía, concepto); si dice vale, crea `.director\vale_diseno.txt`; si pide cambios, corrige la ficha y valida".
     Criterio: `Test-Path .director\vale_diseno.txt`.
  Las fases de pantallas dependen de las dos y usan SOLO `var(--...)` de `00_tokens.css`.

**clonador** (`$env:USERPROFILE\clones_web\motor\clonar.py <url>`) · copia una web de referencia al 97-100 % · solo
cuando el usuario da una URL que quiere igual o "como esta".

**radiografía** (`<H>\codebase_memory\radiografia.py analizar|impacto|cambios`) · entender un proyecto existente sin
leerlo entero; `impacto <proy> <funcion>` antes de tocar algo que otros usan.

**revisión visual** (`<H>\revision_visual\revisar.py <carpeta|url> [--sin-vista]`) · capturas PC/móvil sin caché,
desbordes, imágenes rotas, errores de consola (+ InternVL) · criterio de fase de front:
`if ((<PY> "<H>\revision_visual\revisar.py" "<carpeta>" --sin-vista) -match "VEREDICTO: OK") { exit 0 } else { exit 1 }`

**flujos de usuario** (Playwright con Python: `uv run --with pytest-playwright pytest tests\e2e -q`; la 1.ª vez
`uv run --with playwright python -m playwright install chromium`) · recorrer login → pantalla principal → acción clave
como un usuario · criterio de la fase de integración en `con_ui`.

**tests / compilar** · Python `uv run --with-requirements requirements.txt python -m pytest <tests de ESA fase> -q`
(proyecto en una carpeta sincronizada: nunca `.venv` dentro) · Java `mvn -q test` · Node `npm test` · criterio de TODA fase de código.

**seguridad** (`<H>\seguridad\nova_seguridad.py <carpeta>`) · escáneres gratis (Semgrep, gitleaks, OSV); los usa la
inspección del director sola: no hace falta fase.

**Qwen local** (`<H>\..\scripts\nova_secciones.py`, `nova_tarea.py`) · trozos mecánicos (HTML repetitivo) sin gastar cupo ·
opcional dentro de una fase de obra.

**API X-Ray** (`<H>\api_xray\api_xray.py --cli <url>`) · entender una API JSON externa (tablas, ER, SQL) antes de consumirla.

## Reglas del planificador (lo que más falla en sistemas así)
1. Lo que más rompe proyectos es una **especificación floja** (~40 % de fallos medidos en sistemas multiagente): cada
   requisito con su criterio de aceptación comprobable ("CUANDO ..., EL SISTEMA DEBE ...").
2. Si falta un dato que cambia el diseño (motor de BD, quién se registra, pantallas, idioma, despliegue), **pregúntalo**
   en `preguntas` en vez de suponerlo.
3. **Un solo hilo** lleva el estado (la obra encadenada); en paralelo solo trabajo con dueño de archivos claro y contrato.
4. Lo que pueda comprobar una máquina (tests, compilar, visual), lo comprueba una máquina: ponlo en `criterios`.
