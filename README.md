# 🌌 NOVA AGENT: The Google-Native Autonomous Engineering Engine
### Agente Autónomo de Ingeniería de Software, Copiloto Técnico Senior & Motor de Eficiencia de Tokens para Google Antigravity 2.0

[![License: MIT + Attribution](https://img.shields.io/badge/License-MIT%20%2B%20Attribution-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-success.svg)](#-instalación-en-1-clic-auto-instalador-de-antigravity-incluido)
[![Native Runtime](https://img.shields.io/badge/Native%20Runtime-Google%20Antigravity%202.0-orange.svg)](https://antigravity.google)
[![Ecosystem](https://img.shields.io/badge/Ideology-100%25%20Google%20Ecosystem-4285F4.svg)](#-la-ideología-100-ecosistema-google)
[![Skills](https://img.shields.io/badge/Skills-145%20Optimizadas%20Gemini-purple.svg)](#-catálogo-detallado-de-skills-por-especialidad)
[![Integrity Shield](https://img.shields.io/badge/Integrity-SHA--256%20Signed%20Manifest-brightgreen.svg)](#-capa-de-integridad-criptográfica-y-anti-plagio)
[![1-Shot Protocol](https://img.shields.io/badge/Protocol-1--Shot%20Consolidado-red.svg)](#️-arquitectura-del-sistema-la-pirámide-de-escalado-de-5-capas)

**Nova Agent** no es un prompt leak ni una extensión visual de editor: es un **Agente Autónomo de Ingeniería de Software de Código Abierto**, dotado de cerebro agéntico, memoria persistente local, disciplina de trinchera y un árbol de 145 habilidades especializadas diseñado y acoplado nativamente para **Google Antigravity 2.0** y los modelos **Google Gemini**.

Diseñado, entrenado y probado a fuego durante más de un mes de pruebas de estrés continuas por **Saúl Alexander Martínez Rivas** ([@Luaz2021](https://github.com/Luaz2021)), Nova Agent erradica los tres vicios crónicos de los asistentes de IA convencionales:
1. **Cero servilismo ni relleno conversacional:** Respuestas directas de arquitecta senior, código limpio bajo filosofía **KISS estricto** (*Keep It Simple, Stupid*) con *early returns*.
2. **Cero derroche de cuota de tokens:** Arquitectura optimizada para reducir el peso de arranque en un **38%**, ejecutar tareas multi-archivo en modo **`1-Shot` consolidado** y enrutar tareas ligeras hacia modelos gratuitos a 0 EUR.
3. **Cero experimentos en caliente:** Prohibido romper tu rama activa. Todo cambio o refactor se valida primero mediante pruebas unitarias aisladas (`phantom_test`) antes de tocar código de producción.

---


## 🎯 La Ideología: 100% Ecosistema Google

Mientras la inmensa mayoría de la comunidad open source compite por hacer wrappers y extensiones para Claude Code o Cursor, **Nova Agent fue concebido desde el primer día para exprimir al máximo el poder del ecosistema de Google**:

1. **Alineación con Google DeepMind:** Diseñado para correr de forma nativa en **Google Antigravity 2.0**, aprovechando su runtime por eventos, su sandbox seguro de herramientas y el CLI (`agy`).
2. **Explotación de la Ventana de Contexto de Gemini:** Las 145 skills están optimizadas para la capacidad de absorción masiva de **Google Gemini** (1M a 2M tokens), permitiendo analizar repositorios completos de golpe sin alucinaciones.
3. **Multimodalidad Nativa:** Inspección de capturas visuales de UI, análisis de vídeo técnico y procesamiento multimodal directo con Google Cloud.
4. **Costo Óptimo 1-Shot:** Pensado para operar el 90% del tiempo sobre **Gemini 3.8 Flash** a máxima velocidad y mínimo coste, escalando a **Argon** solo cuando se requiere cirugía sistémica.

---

## ⚡ Distinción Fundamental: Google Antigravity 2.0 vs. Antigravity IDE

Para entender la arquitectura de Nova Agent, es crítico separar el **runtime agéntico** de la **interfaz gráfica**:

| Concepto | Qué es realmente | Rol en el Ecosistema |
| :--- | :--- | :--- |
| **Google Antigravity 2.0** | **El Motor Agéntico y Plataforma de Ejecución de Google DeepMind.** Provee el runtime agéntico, el CLI (`agy`), el sandbox de permisos de herramientas, la invocación concurrente de subagentes, la memoria de sesión y la reactividad por eventos. | **El hábitat real de Nova Agent.** Nova vive, orquesta y ejecuta dentro de este runtime subyacente. Puede operar tanto en local como por terminal CLI (`agy`) desatendida. |
| **Antigravity IDE** | **La Interfaz Visual de Usuario (GUI / Editor gráfico).** Es la capa de visualización basada en Electron que sirve como cliente visual para interactuar con el motor. | Solo el visor. Nova Agent **no es una extensión gráfica de IDE**; el IDE es únicamente la ventana donde visualizas las acciones del agente. |

---

## 🏗️ Arquitectura del Sistema (La Pirámide de Escalado de 5 Capas)

Nova v3.0 trabaja con una regla de oro: **lo pesado se hace en tu equipo a 0 tokens y la nube solo dirige y repara**. Todo el flujo pasa por las **reglas automáticas (hooks)**, que vigila el sistema y no el modelo.

```mermaid
flowchart TD
    User([👨‍💻 Tú, en Google Antigravity 2.0]) -->|Mensaje| Pre[🛡️ Hook de turno<br>autorizaciones · lección pendiente · aviso de búfer]
    Pre --> Flash[⚡ Capa 1: Gemini Flash<br>Arquitecto de contratos y cirujano de guardia]
    Flash -->|Cada herramienta| Guard{🛡️ Hook guardián<br>carpetas protegidas · claves · rama principal<br>webs +150 líneas · freno de gasto}
    Guard -->|Bloqueado o pregunta| User
    Guard -->|Permitido| Dispatcher{¿Qué hay que hacer?}

    Dispatcher -->|Web de un negocio| Biblio[🏪 Biblioteca de webs<br>nova_tarea.py --categoria auto]
    Dispatcher -->|Web de referencia| Clon[🔍 Clonador<br>mide estructura · cambia textos y marcas]
    Dispatcher -->|Otra web o app| Secciones[🧩 Qwen por secciones<br>nova_secciones.py + revisión InternVL]
    Clon --> Capa0
    Secciones --> Capa0
    Dispatcher -->|Documento PDF / Word| Redactor[📄 Redactor local<br>redactor.py · resumir.py]
    Dispatcher -->|Código grande / textos en lote| Obrero[🔧 Obrero local<br>nova_local_worker.py]
    Biblio --> Capa0
    Redactor --> Capa0
    Obrero --> Capa0[💻 Capa 0: Ollama en tu equipo<br>Qwen 3.5 pica · InternVL 3.5 mira<br>0 tokens de nube]

    Dispatcher -->|Hasta 150 líneas, arreglos, lo delicado| Flash
    Dispatcher -->|Web de referencia o 'escríbelo tú'| Flash
    Capa0 -->|Falla 3 veces| Freno[⛔ Freno en seco<br>te avisa y pide permiso<br>nunca sigue en la nube a escondidas]
    Flash -->|Análisis en frío| Pro[🧠 Capa 2: Gemini Pro<br>subagente bajo demanda]
    Pro -->|Arquitectura sistémica| Argon[🏛️ Capa 3: Gemini Argon<br>artillería pesada 4.0x]
    Argon -->|3 fallos combinados| Claude[⚖️ Capa 4: Claude<br>tribunal supremo · servilleta de rescate]

    Flash --> Stop[🛡️ Hook de cierre<br>código pegado en el chat · lección apuntada]
    Stop --> Memoria[(🧠 Memoria local<br>tareas · servilleta · lecciones · puente de ventana)]
```

| Capa | Motor | Rol principal | Coste |
| :--- | :--- | :--- | :--- |
| **🛡️ Hooks** | **`nova_core/nova_hook.py` + `nova_hook_turno.py`** | Vigilan cada mensaje y cada herramienta: bloquean o preguntan ante lo peligroso, frenan el gasto cada 300k tokens reales y obligan a apuntar lo aprendido. | **0 tokens (corren en local)** |
| **Capa 0** | **Ollama: Qwen 3.5 (9B/4B) + InternVL 3.5 (visión)** | El que pica: webs de negocio desde la biblioteca, documentos, código grande y autocontenido, textos en lote y todo lo privado. Si falla 3 veces, **freno en seco**: te avisa y no sigue en la nube sin tu permiso. | **0 tokens de nube (0,00 €)** |
| **Capa 1** | **Gemini Flash** | El que dirige: entiende el pedido, prepara el contrato para la Capa 0, escribe hasta 150 líneas (arreglos, integraciones, lo delicado) y repara lo que salga mal. | **Factor 1.0x** |
| **Capa 2** | **Gemini Pro (subagente)** | Análisis en frío y asíncrono cuando Flash necesita una segunda opinión. | **Bajo demanda** |
| **Capa 3** | **Gemini Argon** | Rediseños de arquitectura, incompatibilidades profundas y auditorías forenses. | **Factor 4.0x, solo bajo demanda** |
| **Capa 4** | **Claude (Sonnet / Opus)** | Tribunal supremo tras 3 fallos combinados: deja una servilleta de rescate en `memory/ultimo_contexto_puente.md`. | **Uso quirúrgico** |

> **Escuadrón Cloud Free (opcional):** con tus claves gratuitas, `free_ai_router.py` manda consultas rápidas a Codestral, OpenRouter o Groq (Whisper) sin gastar cuota de Antigravity.

---

## 📑 Índice de Contenidos
1. [La Ideología: 100% Ecosistema Google](#-la-ideología-100-ecosistema-google)
2. [Google Antigravity 2.0 vs. Antigravity IDE](#-distinción-fundamental-google-antigravity-20-vs-antigravity-ide)
3. [Novedades de Ingeniería v3.0](#-novedades-de-ingeniería-v30)
4. [Novedades de Ingeniería v2.3](#-novedades-de-ingeniería-v23)
5. [Instalación en 1 Clic (Windows, macOS y Linux)](#-instalación-en-1-clic-auto-instalador-de-antigravity-incluido)
6. [¿Ya tienes Nova? Actualiza a v3.0 sin perder nada](#-ya-tienes-nova-actualiza-a-v30-sin-perder-nada)
7. [Router Multi-Modelo y Herramientas a 0 Tokens](#-router-multi-modelo-y-herramientas-a-0-tokens)
8. [Catálogo Detallado de Skills por Especialidad](#-catálogo-detallado-de-skills-por-especialidad)
9. [Atribuciones y Agradecimientos Open Source](#-atribuciones-y-agradecimientos-open-source-cero-cajas-negras)
10. [Capa de Integridad Criptográfica y Anti-Plagio](#-capa-de-integridad-criptográfica-y-anti-plagio)
11. [Llamada a Colaboradores: Proyecto Nova GUI](#-llamada-a-colaboradores-proyecto-nova-gui-open-source)
12. [Créditos, Licencia y Autoría](#-créditos--autoría)

---

## 🔥 Novedades de Ingeniería v3.0

Esta versión acerca la Nova pública a la Nova completa del autor: **reglas que vigila el sistema (no el modelo)**, **webs y documentos hechos en local a 0 tokens**, la **IA local de nueva generación** y un **actualizador por parches** que nunca toca lo tuyo. Funciona igual en **Windows, macOS y Linux**.

| Mejora de Arquitectura | Qué problema resuelve | Impacto Técnico Real |
| :--- | :--- | :--- |
| **1. Reglas automáticas con hooks (`nova_core/nova_hook.py`, `nova_hook_turno.py`)** | Las leyes de `GEMINI.md` son texto y el modelo a veces se las salta. Ahora Antigravity consulta a Nova **antes de cada herramienta**: bloquea escribir en carpetas protegidas o `.env`, pregunta ante comandos destructivos o ediciones en la rama principal, impide leer claves o archivos gigantes y frena webs de +150 líneas escritas desde la nube. | Las reglas se cumplen siempre. Un hook roto nunca bloquea a Nova (falla en abierto y lo apunta). |
| **2. Freno de gasto con tokens reales** | Una sesión larga podía quemar millones de tokens sin avisar. El freno cuenta los tokens **reales** (la caché de Gemini al 10 %) y pregunta cada 300k; también avisa a los 100k de contexto para compactar y guarda copia del chat. | Control del gasto sin sorpresas. |
| **3. Auto-aprendizaje vigilado** | Cuando corriges a Nova o fallan varios comandos seguidos, el hook le pide **una lección** en `memory/inbox_lecciones.md`; si no la apunta, insiste una vez y luego la guarda para revisar. | Nova no repite el mismo error. |
| **4. Biblioteca de webs local (`almacen/biblioteca_web/`)** | Webs de negocio **minimalistas y con identidad propia** según el tipo de negocio: 15 categorías, 36 estilos inspirados en principios de webs reales (nunca marcas), fotos con licencia libre, efectos de scroll y 3D (Three.js) que se apagan en el móvil y con "reducir movimiento". | Una web completa en local **sin gastar tokens de nube**. Con una web de referencia, la nube puede escribirla. |
| **5. Redactor de documentos (`nova_core/redactor.py`)** | PDF y Word con portada (u opción `sin_portada`), tablas con negrita y anchos de columna correctos, usando la IA local. Más `resumir.py` y `conversor.py` para leer documentos largos sin subirlos enteros. | Documentos profesionales a 0 tokens. |
| **6. IA local de nueva generación (`scripts/nova_instalar_ia_local.py`)** | **Qwen 3.5** (9B o 4B) para código y textos + **InternVL 3.5** para visión, según tu equipo. Si falta Ollama, Nova lo instala (winget, Homebrew o el instalador oficial de Linux). Un único catálogo: `scripts/nova_modelos.json`. | Di *"Nova, instala la IA local"* y listo. |
| **7. Actualizador por parches con firma SHA-256 (`scripts/actualizar_nova.py`)** | Compara **archivo por archivo**, verifica cada descarga, hace copia de seguridad antes de cambiar nada y **nunca toca** tus notas, tu perfil ni tus claves. Compatible con las instalaciones v2.x. | Parches seguros cada pocos meses con un *"Nova, busca actualizaciones"*. |
| **8. Multiplataforma de verdad** | Avisos de escritorio, voz, batería, anti-suspensión y portapapeles nativos en Windows, macOS y Linux; el nombre del usuario se lee de su perfil. | La misma Nova en los tres sistemas. |
| **9. Pipeline de webs completo (`scripts/nova_tarea.py`)** | Un solo comando para la Capa 0: Qwen pica por secciones (`nova_secciones.py`), el linter (`nova_core/orquestador.py`) y Playwright + InternVL revisan escritorio y móvil (`nova_pipeline_local.py`), y Nova solo arregla lo que falla. Con una web de referencia usa el **clonador** (`clonador/`), que mide estructura y ritmo y cambia textos, marcas y fotos por los tuyos. | Webs revisadas antes de entregarlas, sin reescribirlas desde la nube. |
| **10. Herramientas internas (`herramientas/`)** | Trello, Gmail, Groq (Whisper + Llama gratis), YouTube, escudo de datos para la nube gratis, escáner de repos de terceros, pruebas fantasma en rama temporal, radar de webs del sector, vídeo (narración, intro, hoja de fotogramas auditada por InternVL, destilador de reels) y voz manos libres. | Lo que Nova ya sabe hacer sin escribir scripts nuevos. |
| **11. 20 skills nuevas (145 en total)** | Móvil nativo (Android, iOS, Flutter, React Native, seguridad MASVS), presentaciones (HTML, suizo/editorial, PPTX nativo, PowerPoint), Web3 (Foundry, tokenización y MiCA), vídeo Canvas 2.5D y los **8 índices de 1 salto** que hacen que Nova lea solo lo que necesita. | Más dominios con el mismo gasto de tokens. |
| **12. Informe de aprendizaje con privacidad (`/enviar-informe`)** | Si quieres ayudar a mejorar Nova, prepara un informe con **solo** las lecciones, las entradas nuevas de tu servilleta y el **tipo** de errores. Nada de tu equipo, proyectos, rutas, correos ni claves. Tú lo revisas y decides si se envía. | Mejora colectiva sin robar información. |

---

## 🔥 Novedades de Ingeniería v2.3

Esta versión introduce el **Motor de Vídeo Programático Dual**, el **Enrutador Híbrido Automático de IA Local (Capa 0 vs Cloud Fallback)** y la suite de plantillas de estudio 3D en WebGL:

| Mejora de Arquitectura | Qué problema resuelve | Impacto Técnico Real |
| :--- | :--- | :--- |
| **1. Enrutador Híbrido Automático (`scripts/nova_video_router.py`)** | Detecta automáticamente si el cliente tiene Ollama levantado con modelos compatibles (Qwen2.5-Coder / nova-dsl). Si lo tiene, corre a **0 tokens cloud**. Si no (laptops sin GPU o clientes sin Ollama), activa **Fallback transparente a Gemini Cloud 1-Shot** sin romper nada. | **-84% tokens de nube** en equipos con GPU; 100% de compatibilidad garantizada en equipos modestos. |
| **2. Motor Dual HyperFrames: 3D Studio vs B-Roll Editorial** | Separa el vídeo procedural en código 3D (Three.js WebGL con avatares procedurales, cámara 9:16 calibrada y lip-sync a 30Hz) del montaje editorial de producto/lifestyle (fotos reales, IA generativa web y código GSAP a pelo). | Rigor técnico para debates y código en 3D; máxima flexibilidad visual para e-commerce y gastronomía. |
| **3. Contrato de Prompt en 3 Capas (Token Shield)** | Elimina el derroche de reenviar esquemas completos de 3.000 tokens en cada llamada. Capa Fija en Modelfile/System, Capa Semi-Fija en `scene-schema.json` y Capa Variable de mínimo brief en cada prompt. | Conserva la atención de modelos 7B locales y reduce drásticamente tokens de entrada en la nube. |
| **4. Validador Sub-10ms Safe Zones (`fast_check.py`)** | Valida el discriminador de tema (`theme`), lista blanca de widgets y márgenes de Safe Zone de Instagram Reels (Y: 240..1520px) antes de enviar a renderizar. | Cero fallos estructurales de decodificación y cero elementos tapados por la interfaz de Instagram/TikTok. |
| **5. Suite de Plantillas 3D Studio (`skills/hyperframes-director/templates/3d_studio/`)** | Plantillas listas para producción: motor Three.js desacoplado (`runtime_studio.js`), escenario HTML con subtítulos karaoke, generador de esquema y renderizador headless Chromium a FFmpeg (CRF 18 + EBU R128). | Puesta en marcha de vídeos verticales 9:16 en minutos sin dependencias complejas de React ni Remotion. |
| **6. Gimnasio de Razonamiento & Antipatrones (`gimnasio.template.md`)** | 20 preguntas senior de debate arquitectónico y 10 antipatrones forenses de la industria desinfectados de datos personales. | Calibra decisiones complejas antes de picar código; evita sobre-ingeniería. |
| **7. Auto-Aprendizaje de Trinchera (`learnings.template.md`)** | Registra cuando una corrección o atajo define la forma óptima ("Forma B de Saúl") frente a la genérica ("Forma A"). | Cero divagaciones repetitivas en prompts posteriores. |

---

## 🛠️ Router Multi-Modelo y Herramientas a 0 Tokens

Nova Agent incluye una suite de utilidades CLI nativas en `scripts/` y `scripts/scrapers/` que operan bajo el **Principio API/CLI First (Ley 17)**:

```text
Nova CLI Tools
├── nova_video_router.py  -> Enrutador híbrido de vídeo 3D (Capa 0 Ollama vs Capa 1 Cloud Fallback)
├── free_ai_router.py     -> Enruta consultas a Codestral o OpenRouter Free Tier (0€)
├── youtube_api_client.py -> Consultas a YouTube Data API v3 en <150ms a 0 tokens
├── nova_tarea.py         -> Comando único de webs: biblioteca, referencia (clonador) o Qwen por secciones + revisión
├── nova_instalar_ia_local.py -> Instala Ollama + Qwen 3.5 + InternVL 3.5 según tu equipo
├── nova_claves.py        -> Asistente de claves gratis (se guardan solo en tu equipo)
├── nova_revisor.py       -> Informe semanal local: qué hizo Nova, cuánto gastó y dónde falló
├── actualizar_nova.py    -> Parches oficiales con firma SHA-256 y copia de seguridad
└── enviar_feedback.py    -> Conexión directa y sanitizada con el creador vía GitHub Issues
```

### Herramientas internas (`~/.gemini/antigravity/herramientas/`, índice en `herramientas/LEEME.md`)
```text
herramientas/
├── trello/trello.py            -> Tableros, listas y tarjetas (claves en tu secrets.env, nunca impresas)
├── nube/                       -> Groq (Whisper + Llama gratis), Gmail, YouTube y escudo de datos para IA gratis en la nube
├── seguridad/                  -> Escáner de repos de terceros al clonarlos (git_clone_sentinel + nova_repo_scanner)
├── pruebas/phantom_test.ps1    -> Prueba código en una rama temporal y la descarta si falla
├── radar_web.py                -> Mide 3-5 webs reales del sector (estructura y ritmo, sin copiar textos ni fotos)
├── video/                      -> Narración, intro de 10 s, hoja de fotogramas auditada por InternVL, destilador de reels
└── voz/nova_voz.py             -> Manos libres: di "Nova" y dicta (Windows; el modelo Vosk se descarga aparte)

clonador/                       -> Motor que rehace una web de REFERENCIA en local (se cambian textos, marcas y fotos)
```

### Ejemplos de uso directo desde terminal:
```bash
# Diagnosticar si tu máquina soporta IA local a 0 tokens para vídeo o requiere fallback cloud:
python scripts/nova_video_router.py --check

# Generar escena de vídeo programático con detección automática de hardware:
python scripts/nova_video_router.py --prompt "Mito vs Realidad de Nova Core" --out escena1.json

# Consultar duda de código a Codestral (Mistral AI)
python scripts/scrapers/free_ai_router.py code "¿Cómo implementar un Early Return en Spring Boot?"

# Consultar modelo gratuito de OpenRouter
python scripts/scrapers/free_ai_router.py ask "Explica el algoritmo de consenso Raft en 3 puntos"

# Buscar vídeos en YouTube a 0 tokens de navegador
python scripts/scrapers/youtube_api_client.py search "Arquitectura Limpia Hexagonal" 3

# Montar una web de negocio desde la biblioteca local (0 tokens de nube)
python ~/.gemini/antigravity/almacen/biblioteca_web/montar.py --datos mi_web/datos.json --categoria auto --out mi_web/index.html

# Ver qué IA local te toca y qué tienes instalado
python ~/.gemini/antigravity/scripts/nova_instalar_ia_local.py --estado
```

---

## ⚡ Instalación en 1 Clic (Auto-Instalador de Antigravity Incluido)

> [!TIP]
> **¿No tienes Google Antigravity instalado?** Al ejecutar el instalador en Windows, comprobará tu sistema y **te preguntará si deseas que descargue e instale Google Antigravity oficial automáticamente** antes de enlazar las 145 skills.

> [!NOTE]
> **Requisitos:** Python 3.10 o superior y git (en Windows, si falta Python, el instalador te ofrece instalarlo con winget). La IA local es opcional y el instalador solo la ofrece si tu equipo tiene RAM y disco suficientes.

### 🪟 En Windows (PowerShell o Doble Clic)
**Opción A (1 sola línea en PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Luaz2021/Nova-Agent-Core-Demo/main/instalar_nova.bat -OutFile $env:TEMP\instalar_nova.bat; & $env:TEMP\instalar_nova.bat
```

**Opción B (Desde repositorio clonado o ZIP):**
Clona el repositorio o descarga el ZIP y haz doble clic sobre `instalar_nova.bat`.

### 🍎 En macOS (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/Luaz2021/Nova-Agent-Core-Demo/main/instalar_nova.sh | bash
```

### 🐧 En Linux (Bash)
```bash
curl -fsSL https://raw.githubusercontent.com/Luaz2021/Nova-Agent-Core-Demo/main/instalar_nova.sh | bash
```

El instalador es interactivo: te pregunta tu nombre y tu perfil, analiza tu equipo, te ofrece la IA local, registra las reglas automáticas (hooks) y, si quieres, te deja configurar tus claves gratuitas (como un inicio de sesión, sin mostrarlas en pantalla y solo en tu equipo).

---

## 🔄 ¿Ya tienes Nova? Actualiza a v3.0 sin perder nada

No hace falta reinstalar. En el chat de Antigravity escribe:

> **"Nova, busca actualizaciones"**

- La **primera vez** desde la v2.x, Nova actualiza su propio actualizador. Dilo **una segunda vez** para que traiga el resto (reglas automáticas, biblioteca de webs, redactor, IA local nueva).
- Antes de cambiar nada guarda una copia en `~/.gemini/antigravity/backups/`.
- **Nunca toca** `memory/` (tareas, servilleta, lecciones), tu `perfil_usuario.json`, tus claves ni tu configuración del IDE.
- Cuando termine, **cierra y abre Antigravity** para activar las reglas automáticas.
- Para pasar a los modelos nuevos: *"Nova, instala la IA local"* (y opcionalmente borra los viejos `qwen2.5-coder` con `nova_instalar_ia_local.py --limpiar-obsoletos`).

---

## 🧰 Catálogo Detallado de Skills por Especialidad

Nova Agent incorpora **145 skills de ingeniería de software** optimizadas para Google Gemini. Cada módulo cuenta con su especificación formal en `SKILL.md`:

### 1. 🎯 Planificación, Estructuración & Dirección Agéntica
*Módulos dedicados a la preventa técnica, descomposición de historias de usuario, mitigación de sesgos y bucles autónomos.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gemini-superpowers-engine`** | **Motor de Planificación Metódica y Grill-Me Técnico.** Bloquea la escritura de código previa; somete ideas a cuestionarios de 3 a 5 preguntas quirúrgicas sobre MVP, dependencias y criterios de aceptación antes de generar tareas `[MB] T-xx`. | *"Nuevo proyecto: [idea]"*, planificación de Sprints o módulos. |
| **`autonomous-loops`** | **Arquitectura de Bucles Autónomos y Pipelines Multi-Agente.** Orquesta ciclos continuos de ejecución orientados a objetivos con puertas de parada medibles y verificación continua. | Modo autónomo (*"te lo dejo en tus manos"*), refactors masivos. |
| **`council`** | **Consejo Arquitectónico de 4 Voces.** Simula desacuerdo estructurado para resolver dilemas de diseño técnico, trade-offs complejos y decisiones go/no-go. | Dudas de arquitectura, selección de stack o dilemas estructurales. |
| **`council-multi-model`** | **Arbitraje Externo Multi-Modelo.** Crítica cruzada sobre borradores de decisión mediante modelos externos para eliminar sesgos de proveedor. | Validaciones críticas de arquitectura previa confirmación del usuario. |
| **`agentic-engineering`** | **Ingeniería Agéntica Eval-First.** Metodología de descomposición modular de tareas, diseño de pruebas previas y enrutamiento por presupuesto. | Tareas de alta complejidad con múltiples componentes interconectados. |
| **`architecture-decision-records`** | **Registro de Decisiones Arquitectónicas (ADRs).** Redacción estandarizada de documentos numerados en `docs/adr/` con contexto, consecuencias y alternativas. | Creación o cambios mayores en la arquitectura de un software. |
| **`gemini-system-architect`** | **Arquitectura Modular y Multirepo (DDD & C4 Model).** Mapeo de límites de contexto (*Bounded Contexts*), costuras de aislamiento (*Seam Mapping*) y radio de impacto. | Diseño estructural de sistemas distribuidos, microservicios o monorepos. |

### 2. 🧪 Testing Riguroso, TDD & Depuración Sistemática
*El laboratorio hostil de Nova: cero cambios sin pruebas que los respalden.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gemini-tdd-enforcer`** | **Desarrollo Guiado por Pruebas (Ciclo Rojo-Verde-Refactor).** Aplica estrictamente el patrón AAA (Arrange-Act-Assert). Prohíbe código de producción sin un test unitario previo en rojo. | Creación de lógica de negocio, servicios y endpoints. |
| **`gemini-chaos-qa`** | **Tester Destructivo (Chaos Monkey).** Diseña escenarios de estrés extremo: desbordamientos numéricos, inyecciones, cadenas malformadas, concurrencia y nulos. | Pre-lanzamiento, pruebas de estrés y validación de endpoints. |
| **`gemini-systematic-debugger`** | **Depuración Científica Basada en Causa Raíz.** Aísla fallos mediante lectura forense de logs, formulación de hipótesis y diseño de pruebas mínimas reproducibles. | Errores en tiempo de ejecución, bugs intermitentes o fallos de compilación. |
| **`gemini-safe-refactor`** | **Refactorización Segura Read-Only.** Diagnóstico previo y plan de contingencia antes de alterar código existente (principio de Chesterton). | Migraciones internas, limpieza de deuda técnica y reestructuraciones. |
| **`production-audit`** | **Auditoría Pre-Lanzamiento y Post-Merge.** Checklist implacable de sanidad: variables de entorno, scripts de build, certificados y salud de endpoints. | Puesta en producción y auditorías post-despliegue. |
| **`benchmark-optimization-loop`** | **Bucle de Optimización Basado en Métricas Reales.** Establece líneas base, formula hipótesis atómicas de rendimiento y valida mejoras con benchmarks. | Cuellos de botella en backend, latencias altas o consumo excesivo de memoria. |
| **`react-testing`** | **Testing de Interfaces React.** Aserciones con Testing Library, Vitest/Jest, intercepción de red con MSW y tests de accesibilidad con `axe-core`. | Pruebas de componentes visuales, formularios y flujos web. |

### 3. 🏗️ Arquitectura Backend, Bases de Datos & APIs
*Estándares de alto rendimiento, cero consultas N+1 y concurrencia blindada.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gemini-clean-architecture`** | **Arquitectura Limpia & Hexagonal.** Desacoplamiento estricto en 4 capas: Domain, Service, Repository y Controller en Java, Kotlin, Node o Go. | Desarrollo de servidores, microservicios y APIs core. |
| **`gemini-database-mastery`** | **Estándares SQL de Alto Rendimiento (Postgres/MySQL/Supabase).** Erradicación de N+1, diseño de índices B-Tree/GIN, aislamiento ACID y consultas eficientes. | Modelado relacional, consultas complejas y optimización de bases de datos. |
| **`database-migrations`** | **Migraciones Zero-Downtime.** Patrón Expand-Contract, creación de índices concurrentes (`CONCURRENTLY`) y backfills seguros sin bloqueo de tablas. | Alteración de esquemas en bases de datos productivas. |
| **`api-design`** | **Diseño de APIs RESTful Empresariales.** Nombres de recursos canónicos, idempotencia, códigos HTTP estrictos, paginación por cursor y rate limiting. | Definición de contratos de API e interfaces públicas. |
| **`fastapi-patterns`** | **Buenas Prácticas en Python FastAPI.** Inyección de dependencias, tipado con Pydantic v2, routers asíncronos y testing estructurado con `pytest-asyncio`. | Microservicios y servicios de backend en Python. |
| **`backend-patterns`** | **Patrones de Servidor Node.js y Express.** Middleware pipelines, manejo centralizado de excepciones y validación de esquemas en tiempo de ejecución. | Aplicaciones de backend en Node.js, Express o Next.js API Routes. |
| **`docker-patterns`** | **Contenedorización Segura.** Multi-stage builds, usuarios no-root, optimización de capas de caché y orquestación con Docker Compose. | Despliegue en contenedores, entornos reproducibles y dev-containers. |

### 4. 🛡️ Ciberseguridad Defensiva, DevSecOps & Bastionado
*Protección militar de credenciales, modelado de amenazas y protección OWASP.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gemini-security-bastion`** | **Auditor White-Hat de Repositorios Propios.** Escaneo de secretos expuestos, validación de CORS, puertos abiertos, bypass de autenticación y cabeceras Helmet. | Triaje de seguridad, auditorías técnicas de repositorios. |
| **`gemini-git-guardian`** | **Guardian Pre-Commit & Fuga de Datos.** Bloquea commits con claves API expuestas, archivos `.env`, tokens privados o comandos destructivos `DELETE` sin `WHERE`. | Flujos de control de versiones y pre-commits. |
| **`gemini-supabase-security`** | **Bastionado de Supabase y BaaS.** Reglas de Row Level Security (RLS) atómicas, políticas de Storage Buckets y aislamiento absoluto de `service_role`. | Aplicaciones conectadas a Supabase o PostgreSQL en la nube. |
| **`gemini-stride-security`** | **Modelado de Amenazas STRIDE & RBAC.** Análisis de Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service y Elevation of Privilege. | Diseño de autenticación, control de accesos y pasarelas de pago. |
| **`gemini-military-cybersec`** | **Ciberseguridad Defensiva y Criptografía Fuerte.** Implementación de AES-256-GCM, PBKDF2/Argon2, defensas OWASP Top 10 y bastionado de servidores. | Cifrado de datos sensibles, manejo de credenciales y firmas digitales. |
| **`gemini-owasp-sentinel`** | **Centinela de Vulnerabilidades Web.** Mitigación activa de XSS, CSRF, SSRF, inyecciones SQL y deserializaciones inseguras. | Revisión de código en formularios, parsers y endpoints públicos. |
| **`agent-security-hardening`** | **Bastionado de Runtimes de Agentes IA.** Sandboxing de herramientas, prevención de ejecución de comandos maliciosos y aislamiento de memoria. | Ejecución de scripts automáticos e integraciones agénticas. |

### 5. 🎨 Frontend Anti-Slop, Design Systems & Accesibilidad
*Interfaces de autor inspiradas en 247 sitios Awwwards, tipografía modular y accesibilidad universal.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gemini-ui-artisan`** | **Dirección de Arte Frontend Anti-Slop.** Rechaza interfaces genéricas de IA. Diseña micro-bordes refinados, paletas monocromáticas sutiles y tipografía con carácter. | Creación de landings, dashboards y componentes visuales. |
| **`build-awwwards-quality-sites`** | **Desarrollo Web Nivel Awwwards.** Heroes con jerarquía visual distintiva, transiciones orgánicas, coreografías GSAP y detalles de interacción de alta costura. | Sitios web promocionales, portfolios y marcas premium. |
| **`gemini-brand-tokens`** | **Catálogo de 156 Marcas Líderes (`DESIGN.md`).** Tokens de diseño extraídos de Stripe, Linear, Apple, Airbnb, Vercel, Supabase y Raycast listos para usar. | Diseño de interfaces corporativas y estandarización visual. |
| **`brand-to-design-md`** | **Extractor de Identidad desde URLs Públicas.** Compila cualquier sitio web en un archivo `DESIGN.md` estructurado y genera una demo HTML reproducible. | Clonado de identidad corporativa y benchmarking visual. |
| **`design-doctrine`** | **Los 5 Dogmas de Diseño UI.** Cero emojis en interfaces profesionales, tokens por intención semántica, los 8 estados de componentes y foco único por pantalla. | Auditoría y diseño de sistemas de componentes. |
| **`frontend-a11y`** | **Accesibilidad Universal Web (WCAG AAA).** HTML semántico, atributos ARIA nativos, navegación completa por teclado, roles y compatibilidad con lectores de pantalla. | Maquetación web accesible y cumplimiento normativo. |
| **`gemini-webperf`** | **Optimización Extrema de Core Web Vitals.** LCP < 2.5s, INP < 200ms, CLS < 0.1, presupuestos de JS < 100 KB gzippeado y eliminación de waterfalls. | Optimización de rendimiento web y auditorías de Lighthouse. |
| **`react-performance`** | **+70 Reglas de Rendimiento en React & Next.js.** Prevención de re-renders innecesarios, límites Server/Client Actions y optimización de contextos. | Apps de alto tráfico en React 18/19 y Next.js. |

### 6. 🎬 Coreografía GSAP, Motion Web & 3D Interactivo
*Animaciones a 60fps con cálculo en hardware y soporte de accesibilidad.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gsap-core`** | **API Base Oficial de GreenSock.** Manipulación de tweens (`to`, `from`, `fromTo`), easing avanzado, stagger y soporte nativo para `prefers-reduced-motion`. | Animaciones básicas y transiciones de estado. |
| **`gsap-timeline`** | **Secuenciación y Timelines Maestros.** Parámetros de posición relativos, anidamiento de escenas y control granular de reproducción (`play`, `reverse`, `seek`). | Coreografías visuales de múltiples elementos coordinados. |
| **`gsap-scrolltrigger`** | **Scroll Dinámico y Pinning.** Animaciones vinculadas al scroll del usuario, secciones fijadas (*pinning*), scrub interactivo y efectos parallax. | Páginas de producto interactivas y narrativa por scroll. |
| **`gsap-react`** | **Integración Oficial con React / Next.js.** Manejo seguro del hook `useGSAP`, referencias DOM, contextos de animación y limpieza garantizada al desmontar. | Animaciones en componentes funcionales de React. |
| **`gsap-plugins`** | **Plugins Oficiales de GSAP.** ScrollSmoother, Flip (cambios de layout fluidos), Draggable, SplitText y CustomEase. | Efectos avanzados de layout y textos cinemáticos. |
| **`cinematic-gsap-lenis-motion-system`** | **Sistema Cinemático de Scroll Suave.** Integración de Lenis Scroll con ScrollTrigger para experiencias fluidas de alta gama sin tirones. | Landings experienciales y webs interactivas premium. |
| **`threejs-web-experience`** | **Escenas 3D en el Navegador con Three.js.** Carga de modelos GLTF/GLB, iluminación cinemática, shaders personalizados y cámaras interactivas. | Visualizadores 3D de producto y fondos interactivos. |
| **`web-motion-auditor`** | **Auditor de Rendimiento de Animaciones.** Detección de *Layout Thrashing*, forzado de transformaciones GPU (`transform`, `opacity`) y verificación a 60fps. | QA de animaciones y optimización de cuadros por segundo. |

### 7. 📹 Vídeo Programático & Estrategia Social 2026
*Producción audiovisual en código, renderizado ultraligero Audio-First y orquestación de contenidos de alto impacto.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`canvas-video-engine`** | **Vídeo programático sin npm.** Canvas 2.5D + WebCodecs, shaders y audio en Python con NumPy y FFmpeg, y control de calidad local con InternVL. | Vídeos verticales y explicativos generados en local. |
| **`hyperframes-director`** | **Motor Dual de Vídeo Programático.** Motor A (3D Procedural en Three.js con avatares procedurales y lip-sync 30Hz) y Motor B (2D Editorial/B-Roll con GSAP). Enrutador híbrido Capa 0 Ollama a 0 tokens vs Capa 1 Cloud 1-Shot Fallback y Safe Zones 9:16. | Reels técnicos, podcasts 3D con avatares, demos de producto y explainers visuales de alta retención. |
| **`video-script-storyteller`** | **Guiones de Alta Retención en 2 Columnas.** Estructura visual vs audio, ganchos de 3 segundos (*scroll stoppers*), ritmo de atención y llamadas a la acción sincronizadas. | Redacción y planificación de guiones para YouTube Shorts, Reels y TikTok. |
| **`ffmpeg-toolkit`** | **Procesamiento Audiovisual CLI Multiplataforma.** Corte sin recodificar (`-c copy`), compresión optimizada para WhatsApp/Web, normalización EBU R128 (-14 LUFS) y masterizado CRF 18. | Ensamble de vídeo, optimización de peso y extracción de pistas de audio. |
| **`remotion-video-agent`** | **Vídeo Programático en React con Remotion.** Creación de vídeos MP4 en código puro: motion graphics, renders escalables y subtitulado dinámico. | Generación de reels complejos, demos de producto en vídeo y explainers React. |
| **`gemini-video-intelligence`** | **Análisis Multimodal de Vídeo.** Extracción de fotogramas clave, OCR de pantallas y resumen estructurado de vídeos locales y de YouTube. | Procesamiento de conferencias, clases y vídeos técnicos. |
| **`procedural-film`** | **Cine Procedural y Pixel Art a 60 FPS.** Generación de visuales en tiempo real mediante HTML5 Canvas 2D y Web Audio API a cero assets externos. | Fondos cinemáticos, intros visuales y arte generativo en código puro. |
| **`ig-hook-extractor`** | **Ingeniería Inversa de Ganchos Virales.** Análisis de fórmulas canónicas de retención (<125 caracteres) para Instagram Reels y TikTok. | Redacción de guiones de vídeo y copies de impacto. |
| **`ig-carousel-planner`** | **Planificador de Carruseles de Alto Valor.** Estructuración narrativa de hasta 10 diapositivas para maximizar guardados y compartidos. | Contenido educativo y divulgación técnica en redes. |
| **`ig-content-planner`** | **Estrategia Semanal de Contenido Social.** Matrices de distribución por formatos (Reels, Carruseles, Stories) alineadas con objetivos comerciales. | Planes de publicación y calendarios editoriales. |
| **`ig-humanizer`** | **Filtro Anti-IA para Redes Sociales.** Elimina clichés robotizados de marketing y aporta cadencia natural humana a descripciones y guiones. | Revisión de textos y copys antes de publicar. |

### 8. 💼 Finanzas SaaS, Legal Mercantil & Operaciones COO
*Métricas financieras, contratos comerciales blindados y procedimientos operativos estándar.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`saas-finance-metrics`** | **Economía Unitaria y Métricas Financieras SaaS.** Cálculo riguroso de LTV, CAC, Churn rate, Payback period, MRR/ARR Waterfall y la Regla del 40. | Modelado de suscripciones, viabilidad de producto y reporting a inversores. |
| **`commercial-legal-counsel`** | **Auditoría y Redacción de Contratos Mercantiles.** Master Services Agreements (MSA), SLAs, NDAs, leasing de software, propiedad intelectual condicionada y cláusulas trampa. | Contratos de desarrollo de software, acuerdos con clientes y licencias. |
| **`business-operations-coo`** | **Operaciones Ejecutivas y Coordinación de Equipos.** Procedimientos Operativos Estándar (SOPs) en 3 pasos, matrices RACI y diseño de OKRs trimestrales. | Organización de flujos de trabajo, delegación y escalado operativo. |

### 9. 🌐 Redes Cisco, Robótica & Hardware IoT
*Infraestructura de telecomunicaciones y firmware en C++ para microcontroladores.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`cisco-network-architect`** | **Ingeniería de Redes Cisco (CCNA / CCNP).** Cálculo de VLSM en subredes, configuración de VLANs (802.1Q), enrutamiento dinámico OSPF/BGP, ACLs, NAT y STP. | Diseño de topologías de red y configuración en Cisco Packet Tracer. |
| **`embedded-robotics-maker`** | **Firmware y Robótica (Arduino & ESP32).** Programación no bloqueante con `millis()`, control PWM de motores (Puente H), sensores I2C/SPI y telemetría MQTT. | Proyectos IoT, domótica, robótica y firmware embebido. |

### 10. 🧠 Optimización de Tokens, Gimnasio & Auto-Aprendizaje
*El sistema nervioso que hace a Nova inteligente entre sesiones sin inflar tu factura.*

| Skill / Plantilla | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`gemini-continuous-learner`** | **Bucle de Auto-Aprendizaje Persistente.** Registra patrones de trabajo y correcciones del desarrollador (`learnings.template.md`) comparando la Forma genérica A (rechazada) vs la Forma B de Saúl (adoptada). | Cada vez que el usuario corrige o refina una directiva. |
| **`gemini-runbook-napkin`** | **La Servilleta de Lecciones Aprendidas (`napkin.template.md`).** Almacén de micro-recetas técnicas en formato `[Problema] -> [Causa] -> [Do instead]` actualizado con 12 auditorías open-source (Supabase, Cal.com, Vite). | Registro y consulta de errores comunes resueltos. |
| **`gimnasio.template.md`** | **Gimnasio de Razonamiento y Antipatrones.** 20 preguntas senior de debate arquitectónico y 10 antipatrones forenses de la industria para calibrar decisiones antes de codificar. | Planificación de nuevos sistemas y prevención de sobre-ingeniería. |
| **`gemini-prompt-distiller`** | **Destilador de Contexto y Poda de Tokens.** Filtra el ruido conversacional y reduce el prompt unificando referencias sin perder directrices técnicas. | Consultas de contexto denso y preparación de prompts. |
| **`gemini-concise-clean-code`** | **Código Ultra-Conciso (KISS & YAGNI).** Genera soluciones en el menor número de líneas legibles, con early returns y cero sobre-ingeniería. | Generación y refactorización de código en cualquier lenguaje. |
| **`cursorrules-advisor`** | **Catálogo de +250 Reglas Especializadas.** Adapta reglas `.cursorrules` y `.mdc` para Expo, React Native, Supabase, Spring Boot y Next.js. | Creación y auditoría de reglas locales por proyecto. |
| **`gemini-humanizer-prose`** | **Humanizador de Textos y Documentación.** Elimina giros artificiales de IA en READMEs, correos académicos, manuales y artículos técnicos. | Redacción de entregables, emails y documentación formal. |

---

### 11. 📱 Desarrollo Móvil Nativo & Multiplataforma
*Apps de verdad para Android e iOS, con la seguridad móvil de serie.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`android-core`** | **Android nativo.** Kotlin 2.0+, Jetpack Compose, Coroutines/Flow, KSP, flujo unidireccional, Material 3 y R8. | Apps Android nativas. |
| **`ios-apple-core`** | **iOS nativo.** Swift 6, SwiftUI, `@Observable`, Swift Concurrency, SwiftData y SPM. | Apps iPhone, iPad y Mac. |
| **`flutter-dart-core`** | **Flutter & Dart 2026.** Dart 3 (records, pattern matching), Impeller, Riverpod/BLoC y arquitectura limpia. | Apps multiplataforma con Flutter. |
| **`react-native-expo`** | **React Native & Expo.** Expo Router, New Architecture (Fabric/TurboModules), NativeWind v4, Zustand, TanStack Query y Reanimated 3. | Apps multiplataforma con JavaScript/TypeScript. |
| **`mobile-security-masvs`** | **Seguridad móvil OWASP MASVS v2.** Keystore/Keychain, SSL pinning, biometría, ofuscación y anti-tampering. | Cualquier app que maneje datos de usuarios. |

### 12. 🎤 Presentaciones & Diapositivas
*Decks que no parecen hechos por una IA.*

| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`frontend-slides`** | **Deck web en un solo HTML.** Escenario 16:9 rígido, tipografías con carácter y micro-interacciones, sin dependencias. | Presentaciones para proyectar o compartir por enlace. |
| **`guizang-ppt`** | **Diseño editorial de diapositivas.** Estilo suizo y revista editorial: retícula estricta, líneas finas y contraste tipográfico. | Decks de marca, portfolio o investigación. |
| **`ppt-master`** | **PPTX nativo.** Formas vectoriales, tablas editables, plantillas institucionales y control de colisiones. | Cuando hace falta un PowerPoint editable. |
| **`mcp-server-ppt`** | **Control de PowerPoint en Windows (COM).** Crear, editar en vivo y exportar diapositivas a PNG/PDF. | Automatizar PowerPoint ya instalado. |

### 13. ⛓️ Web3, Smart Contracts & Fintech
| Skill | Especificación Técnica | Cuándo se Activa |
| :--- | :--- | :--- |
| **`blockchain-security-foundry`** | **Smart contracts con Foundry.** Forge, Anvil y Cast, pruebas de invariantes y auditoría con estándares Cyfrin. | Desarrollo y auditoría de contratos. |
| **`fintech-web3-business`** | **Negocio Web3.** Tokenización de activos reales (RWA), tokenomics sostenibles y cumplimiento europeo MiCA. | Modelos de negocio y viabilidad de proyectos cripto. |

### 14. 🧭 Índices de 1 Salto (el mapa que ahorra tokens)
*Nova lee primero el índice del tema y solo después las skills que necesita: nunca carga las 145 de golpe.*

| Índice | Qué cubre |
| :--- | :--- |
| **`index-ui-frontend`** | Webs y UI: anti-clichés, 6 arquetipos de negocio, flujo con la biblioteca local, motion y canvas. |
| **`index-backend-db`** | Arquitectura limpia, FastAPI, Node, PostgreSQL/Supabase RLS, migraciones, Docker y redes. |
| **`index-mobile-dev`** | Android, iOS, React Native, Flutter y seguridad MASVS. |
| **`index-motion-3d`** | GSAP, ScrollTrigger, Lenis, micro-interacciones y Three.js. |
| **`index-ai-multimedia`** | IA local, enrutado multi-agente, vídeo en código, FFmpeg, transcripción y scrapers 0-token. |
| **`index-brand-growth`** | Marca, Instagram 2026, textos humanos y legal (RGPD). |
| **`index-security-deploy`** | Auditoría web, OWASP/STRIDE, TDD, Chaos QA y despliegue a 0 €. |
| **`index-nova-core`** | La propia Nova: memoria, servilleta, lecciones, modelos y cómo crear skills. |

---

## 🤝 Atribuciones y Agradecimientos Open Source (Cero Cajas Negras)

Nova Agent es un proyecto de código abierto construido con orgullo sobre los hombros de gigantes. Creemos en la transparencia total, sin plumas decorativas ni cajas negras:

| Creador / Proyecto Original | Repositorio / Enlace | Contribución al Ecosistema de Nova Agent |
| :--- | :--- | :--- |
| **Google DeepMind & Gemini Team** | [antigravity.google](https://antigravity.google) | **Plataforma y Motor:** Por crear **Google Antigravity 2.0**, el entorno agéntico multimodal sobre el que corre Nova, y la familia de modelos Gemini. |
| **Jesse Vincent (Obra)** | [`obra/superpowers`](https://github.com/obra/superpowers) | **Filosofía Agéntica:** Por sentar las bases de la ingeniería agéntica moderna (*Systematic Debugging*, *TDD Enforcer* estricto y desacoplamiento de subagentes). |
| **Julius Brussee** | [`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman) | **Eficiencia Extrema:** Por la premisa de comunicación ultraconcisa para la preservación de ventanas de contexto y reducción de latencia. |
| **Blader** | [`blader/humanizer`](https://github.com/blader) | **Cultura Anti-IA:** Por los principios editoriales para erradicar el lenguaje robótico y la arquitectura de servilleta de lecciones (*napkin*). |
| **Meng To & DesignCode Team** | [designcode.io](https://designcode.io) | **Frontend de Autor:** Por inspirar las técnicas avanzadas de maquetación visual, diseño de interacción Awwwards y shaders en Three.js. |
| **GreenSock (GSAP)** | [greensock.com/gsap](https://greensock.com/gsap) | **Animación Web Profesional:** Por el estándar de la industria en micro-movimiento a 60fps en el que se basa nuestra suite oficial GSAP. |
| **Remotion Team** | [`remotion-dev/remotion`](https://github.com/remotion-dev/remotion) | **Vídeo en Código:** Por revolucionar la generación programática de vídeo utilizando React y CSS nativo. |
| **Sameness Design** | [`sameness-design/brand.md`](https://github.com/sameness-design) | **Identidad de Marca Ejecutable:** Por el estándar abierto `brand.md` para empaquetar sistemas de diseño legibles por agentes de IA. |
| **Vercel Labs & Comunidad skills.sh** | [skills.sh](https://skills.sh) / [vercel.com](https://vercel.com) | **Web Interface Guidelines:** Por los estándares de diseño de componentes, micro-interacciones, accesibilidad y Core Web Vitals. |
| **OWASP Foundation** | [owasp.org](https://owasp.org) | **Seguridad Global:** Por los estándares internacionales de mitigación de vulnerabilidades web (OWASP Top 10) aplicados en nuestros centinelas. |
| **Comunidad Awesome Cursorrules** | [`PatrickJS/awesome-cursorrules`](https://github.com/PatrickJS/awesome-cursorrules) | **Ecosistema de Reglas:** Por recopilar y refinar las mejores directrices de desarrollo para frameworks contemporáneos. |
| **Cisco Networking Academy** | [netacad.com](https://www.netacad.com) | **Arquitectura de Redes:** Por los estándares de diseño jerárquico de redes, direccionamiento VLSM y protocolos de enrutamiento. |

---

## 🔒 Capa de Integridad Criptográfica y Anti-Plagio

Nova Agent es un proyecto **Open Source bajo Licencia MIT con Cláusula de Atribución Obligatoria**:
- **No es un simple prompt:** Detrás de este motor hay más de un mes de ingeniería de contexto, diseño de skills, scripts de automatización y millones de tokens invertidos en pruebas de estrés reales.
- **Firma Criptográfica SHA-256:** Cada archivo y skill está indexado con su hash SHA-256 en [manifest_master.json](manifest_master.json). El script `nova_manifest_guardian.ps1` audita la integridad del árbol para detectar manipulaciones no autorizadas o alteraciones de procedencia.
- **Cláusula de Atribución Ética:** Cualquier fork, derivado o proyecto comercial que utilice el núcleo de Nova Agent está obligado legalmente por el archivo [NOTICE](NOTICE) a mantener visible la autoría original de **Saúl Alexander Martínez Rivas (@Luaz2021)** y el enlace a este repositorio.

---

## 🚀 Llamada a Colaboradores: Proyecto Nova GUI (Open Source)

Buscamos desarrolladores senior y entusiastas del ecosistema Google para llevar a Nova Agent al siguiente nivel:

- 🎨 **Nova GUI Nativa (Desktop / Web):** Diseñar una interfaz gráfica dedicada e interactiva (preferentemente construida en **Flutter / Dart** para mantener la coherencia con el stack de Google, o en Next.js / Tauri) que se comunique con el runtime de Antigravity 2.0 y el CLI `agy`.
- 🔌 **Adaptadores Multi-Plataforma:** Mejorar los instaladores y conectores para macOS, distribuciones Linux y entornos Docker.
- 📦 **Nuevas Skills Acopladas a Gemini:** Aportar módulos de ingeniería que aprovechen la multimodalidad y la ventana de contexto de Google DeepMind.

Si quieres colaborar, revisa las directrices de contribución en [CONTRIBUTING.md](CONTRIBUTING.md) o abre un Issue directamente en el repositorio.

---

## 👤 Créditos & Autoría

- **Arquitecto y Creador:** **Saúl Alexander Martínez Rivas** ([@Luaz2021](https://github.com/Luaz2021))
- **Licencia:** MIT License + Mandatory Attribution - Código libre para toda la comunidad de desarrolladores y estudiantes.
- **Repositorio Oficial:** [https://github.com/Luaz2021/Nova-Agent-Core-Demo](https://github.com/Luaz2021/Nova-Agent-Core-Demo)
