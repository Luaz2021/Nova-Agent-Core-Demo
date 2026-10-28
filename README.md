# 🌌 NOVA Agent Core v2.0 (Community Edition)
### Copiloto Técnico Senior, Arquitecta de Software & Motor de Eficiencia de Tokens para Google Antigravity

![License](https://img.shields.io/badge/License-MIT-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-success)
![Engine](https://img.shields.io/badge/Native%20Engine-Google%20Antigravity%202.0-orange)
![Skills](https://img.shields.io/badge/Skills-119%20Optimizadas-purple)
![Token-Savings](https://img.shields.io/badge/Cold--Start%20Savings--38%25%20Tokens-brightgreen)

**Nova** no es un prompt suelto ni una extensión genérica: es una **arquitectura completa de copiloto técnico, memoria persistente local y disciplina de ingeniería** construida nativa y exclusivamente para **Google Antigravity 2.0** y **Google Gemini**.

Creada y probada en trinchera por **Saúl Alexander Martínez Rivas** ([@Luaz2021](https://github.com/Luaz2021)), Nova elimina los tres problemas clásicos de los asistentes de IA:
1. **Cero servilismo ni relleno conversacional:** Respuestas directas de arquitecta senior, código limpio bajo filosofía **KISS estricto** (*Keep It Simple, Stupid*) con *early returns*.
2. **Cero derroche de cuota de tokens:** Arquitectura optimizada matemáticamente para reducir el peso de arranque en un **38%**, ejecutar tareas multi-archivo en modo **`1-Shot` consolidado** y evitar respuestas estáticas costosas.
3. **Cero experimentos en vivo:** Prohibido romper tu rama activa. Todo cambio o refactor se valida primero mediante pruebas unitarias aisladas antes de tocar producción.

---

## 📑 Índice de Contenidos
1. [Novedades de Ingeniería v2.0 (Optimizador de Tokens & Hardware)](#-novedades-de-ingeniería-v20-optimizador-de-tokens--hardware)
2. [Instalación en 1 Clic (Windows, macOS y Linux)](#-instalación-en-1-clic-auto-instalador-de-antigravity-incluido)
3. [Arquitectura de Permisos y Seguridad de Doble Capa](#-arquitectura-de-permisos-y-seguridad-de-doble-capa)
4. [Guía de Atajos Rápidos y Línea Directa con el Creador](#-guía-de-atajos-rápidos-y-línea-directa-con-el-creador)
5. [Catálogo de 119 Skills por Dominio](#-catálogo-de-119-skills-integradas)
6. [Créditos y Licencia](#-créditos--autoría)

---

## 🔥 Novedades de Ingeniería v2.0 (Optimizador de Tokens & Hardware)

Esta versión incorpora las optimizaciones del **Protocolo de Eficiencia de Costos v3.0**:

| Mejora de Arquitectura | Qué problema resuelve | Ahorro / Impacto Real |
| :--- | :--- | :--- |
| **1. Frontmatter YAML Quirúrgico en las 119 Skills** | El IDE inyecta el nombre y `description` de todas las skills en cada ventana. Redujimos los encabezados YAML de `47.647` a `19.922` caracteres manteniendo el **100% del contenido interno** de cada `SKILL.md`. | **~7.000 tokens fijos menos** en cada ventana nueva. |
| **2. Inyección Única de Reglas (`config/GEMINI.md`)** | Evita la doble inyección de reglas globales eliminando duplicados legacy en `~/.gemini/GEMINI.md`. | **~3.200 tokens menos** en el primer turno. |
| **3. Regla de Ejecución `1-Shot` Consolidada (Ley 18)** | Cada llamada extra a herramientas paga un sufijo dinámico no cacheado (~2.052 tokens). Nova agrupa la creación de archivos y ejecución de `unittest` en **un único paso consolidado** (`2-3` llamadas API en vez de `9`). | **Hasta -60% de costo** en tareas de código. |
| **4. Bienvenida a `0 Tokens` (`AYUDA.md`)** | Los tokens de salida (`output_tokens`) cuestan **`6.0x`**. En lugar de que la IA redacte su manual de bienvenida cada vez que alguien instala Nova, el instalador lo imprime en consola a **0 tokens** y el primer saludo en el chat ocupa solo **2-3 líneas** (~50 tokens). | **Ahorro de ~1.000 tokens de salida (`6.0x`)** en el primer arranque. |
| **5. Escáner de Hardware a `0 Tokens` e IA Local Adaptativa** | El instalador analiza tu CPU, RAM, GPU/VRAM y disco libre antes de sugerir IA local (`Ollama`):<br>• **Equipo Básico (`< 12 GB RAM`):** **Bloquea automáticamente la IA local** para proteger tu RAM y batería, activando el Modo `1-Shot` Cloud.<br>• **Gama Media (`12-15 GB RAM`):** Ofrece opcionalmente `qwen2.5-coder:3b`.<br>• **Equipo Potente (`>= 16 GB RAM` + GPU dedicada / Apple Silicon):** Configura `qwen2.5-coder:7b` exclusivamente para tareas masivas (`> 1.500` tokens repetitivos). | Cero bloqueos en laptops básicas y aprovechamiento real de GPU en equipos potentes. |
| **6. Guardián Local de 100k Tokens (`nova_buffer_guardian.py` v2.1)** | Monitorea en segundo plano el peso de la sesión en `~/.gemini/antigravity/memory`, protege el archivo puente contra condiciones de carrera y te avisa al llegar a `100k-120k` tokens para saltar a una ventana limpia sin perder el hilo. | Sesiones largas sin degradación de cuota ni pérdida de contexto. |

---

## ⚡ Instalación en 1 Clic (Auto-Instalador de Antigravity Incluido)

> [!TIP]
> **¿No tienes Google Antigravity instalado?** Al ejecutar el instalador en Windows, comprobará tu sistema y **te preguntará si deseas que descargue e instale Google Antigravity oficial automáticamente** antes de enlazar las 119 skills.

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

### ✅ Qué hace el instalador paso a paso (a 0 Tokens)
1. **Onboarding rápido:** Te pregunta tu nombre, tu perfil técnico (Estudiante, Frontend, Backend, Fullstack o Emprendedor No-Dev) y tu preferencia de telemetría ética anónima (*Opt-In*).
2. **Escáner de Hardware:** Evalúa tu RAM, GPU y disco libre, recomendando (o descartando en equipos básicos) el obrero de IA local y guardando la ficha en `~/.gemini/antigravity/memory/perfil_usuario.json`.
3. **Enlace instantáneo:** Conecta las **119 skills** mediante enlaces simbólicos/junctions e instala `GEMINI.md` y `AYUDA.md` en `~/.gemini/config/`.
4. **Primer mensaje corto en tu portapapeles:** Imprime la guía de atajos en tu consola y deja copiado en tu portapapeles (`Ctrl + V` / `Cmd + V`) un saludo de 1 línea para verificar tu entorno en menos de 50 tokens:
   ```text
   Hola Nova, verifica mi perfil_usuario.json y confirmame en 2 o 3 lineas que todo esta listo.
   ```

---

## 🛡️ Arquitectura de Permisos y Seguridad de Doble Capa

Nova está diseñada bajo el principio de **Transparencia y Mínimo Privilegio**:

1. **Capa 1: Permisos del IDE (`config.json` Opt-In durante la instalación):**
   - A diferencia de otros scripts que desactivan el sandbox de terminal o fuerzan la auto-ejecución de comandos (`TURBO / EAGER`) en silencio, **el instalador de Nova mantiene intacto el sandbox de tu terminal**.
   - Durante la instalación te pregunta si deseas habilitar únicamente `nonWorkspaceFileAccessPolicy: ALLOW` para que Nova pueda leer sus propias **119 skills** y su carpeta de memoria local (`~/.gemini/antigravity/memory`) sin interrumpirte con popups de lectura en cada turno.
2. **Capa 2: Ley Sagrada #1 (*Permiso Primero en el Chat*):**
   - Aunque Nova pueda leer su memoria local fluidamente, la **Ley 1 de `GEMINI.md`** le prohíbe ejecutar comandos en terminal, levantar procesos o modificar archivos de tu proyecto sin tu orden explícita en el chat (*"ejecuta tal"*, *"tienes permiso"* o *"te lo dejo en tus manos"*).
3. **Git Guardian y Integridad SHA-256:**
   - Todos los componentes del núcleo están firmados en `manifest_master.json` con hashes **SHA-256**, y la skill `gemini-git-guardian` previene commits accidentales de archivos `.env` o claves privadas.

---

## 💬 Guía de Atajos Rápidos y Línea Directa con el Creador

En cualquier momento dentro del chat de Antigravity puedes escribir estos comandos cortos (también disponibles en tu archivo local `~/.gemini/config/AYUDA.md`):

### ⚡ Atajos de Sesión y Desarrollo
| Atajo / Frase en el Chat | Acción de Nova |
| :--- | :--- |
| `hola` / `continuamos` / `seguimos` | Lee tu puente local (`ultimo_contexto_puente.md`) y `tasks.md` y retoma la sesión en 2-3 líneas ejecutivas sin mochila de tokens. |
| `/ayuda` o `ayuda` | Muestra el archivo estático `AYUDA.md` con todos tus comandos sin gastar tokens de generación (`6.0x`). |
| `Nuevo proyecto: [idea]` | Bloquea la escritura de código, te hace de 3 a 5 preguntas quirúrgicas (*Grill-Me*) y organiza el sprint en `tasks.md`. |
| `Nova analiza este proyecto: [ruta]` | Auditoría *Read-Only* en 60s con el **Reporte Tanque de 7 Puntos** (Stack, UX/UI Anti-Slop, Accesibilidad a11y, SEO, Legal/RGPD, Ciberseguridad y Deploy a 0 €). |
| `te lo dejo en tus manos` | Activa el modo autónomo: creación/edición `1-Shot` consolidada + batería de tests unitarios (`unittest`) en verde + Chaos QA. |

### 📬 Línea Directa con el Creador (Saúl Alexander Martínez Rivas)
¿Encontraste un caso curioso, tienes una duda arquitectónica o creaste una skill nueva que quieres aportar al proyecto? Habla directamente con Saúl desde el chat:

| Comando en el Chat | Qué hace Nova por detrás (100% Sanitizado) |
| :--- | :--- |
| **`/creador [tu mensaje]`** *(o "Nova, envía mensaje al creador: ...")* | Pasa tu mensaje por `enviar_feedback.py` (que **borra automáticamente rutas de usuario, IPs locales y tokens**) y abre la ventana oficial en GitHub Issues con la etiqueta `buzon-creador` lista para enviar en 1 clic. |
| **`/reportar-fallo`** | Empaqueta un bug resuelto bajo formato Servilleta (`[SO] -> [Error] -> [Solución]`) con la etiqueta `napkin-crowd` para mejorar el Core comunitario. |
| **`/compartir-skill [nombre]`** | Propone una skill creada o mejorada por ti (`skill-comunitaria`) para que Saúl la audite y la incorpore al repositorio oficial con créditos a tu usuario de GitHub. |
| **`/actualizar-nova`** | Coteja tu `manifest_master.json` contra el repositorio oficial de Saúl y descarga mejoras sin tocar ni borrar jamás tus notas o memorias locales. |

---

## 🎯 Catálogo de 119 Skills Integradas

Nova activa automáticamente el módulo exacto según el tema del que le hables (sin cargar las 119 skills de golpe en memoria):

- **☕ Backend, Arquitectura Limpia & Bases de Datos:** `gemini-clean-architecture` (DDD, capas estrictas en Java/Spring/Python/Node), `gemini-database-mastery` (SQL ACID, cero N+1, índices B-Tree/GIN), `database-migrations` (Zero-Downtime), `gemini-supabase-security` (políticas RLS atómicas y aislamiento de `service_role`), `api-design`, `fastapi-patterns`, `backend-patterns` y `cursorrules-advisor` (+250 reglas de frameworks).
- **🎨 Frontend Anti-Slop, UI/UX & Calidad Awwwards:** `gemini-ui-artisan`, `build-awwwards-quality-sites`, `design-doctrine` (los 5 dogmas y 8 estados interactivos), `ux-writing` (microcopy humano), `design-critique` (revisión hostil en tabla), `visual-hierarchy`, `frontend-a11y`, `gemini-webperf` (Core Web Vitals: LCP <2.5s, INP <200ms, CLS <0.1), `web-seo-mastery` y `web-legal-compliance` (RGPD / LSSI / CCPA / Ley 29733).
- **🎬 Motion Design, Suite Oficial GSAP & 3D:** Suite completa `gsap-*` (`gsap-core`, `gsap-timeline`, `gsap-scrolltrigger`, `gsap-react`, `gsap-plugins`, `gsap-performance`, `gsap-utils`, `gsap-frameworks`), `cinematic-gsap-lenis-motion-system`, `motion-design` (LottieFiles / 12 principios de Disney en UI), `threejs-web-experience`, `procedural-film` y `web-motion-auditor`.
- **✒️ Branding, Identidad Visual & 156 Marcas Mundiales:** `brand-design` (director VI conversacional con manual HTML de 21 capítulos), `brand-md`, `brand-to-design-md`, `gemini-brand-tokens` (catálogo de 156 marcas: Stripe, Linear, Apple, Airbnb, Vercel, Supabase, etc.), `color-palette-builder`, `typography-system`, `icon-system`, `logo-brief-writer` y `brand-naming`.
- **📱 Suite Instagram 2026 & Video en Código:** `ig-content-planner`, `ig-hook-extractor`, `ig-carousel-planner`, `ig-caption-writer`, `ig-hashtag-strategist`, `ig-humanizer`, `ig-audience-insights`, `ig-profile-optimizer`, `ig-repurposer`, `remotion-video-agent` y `gemini-video-intelligence`.
- **🛡️ Ciberseguridad, Testing & Redes/Robótica:** `gemini-security-bastion`, `gemini-stride-security`, `gemini-owasp-sentinel`, `gemini-military-cybersec`, `gemini-git-guardian`, `gemini-chaos-qa`, `gemini-tdd-enforcer`, `ai-deploy-advisor` (despliegue a 0 €), `cisco-network-architect` (CCNA / VLSM / OSPF / Packet Tracer) y `embedded-robotics-maker` (Arduino / ESP32 / MQTT / `millis()`).

---

## 🏆 Créditos & Autoría

- **Creador y Arquitecto Principal:** **Saúl Alexander Martínez Rivas** ([@Luaz2021](https://github.com/Luaz2021)) · Torrevieja, España.
- **Motor Nativo:** Google Gemini sobre **Google Antigravity 2.0**.
- **Licencia:** Distribuido bajo licencia **MIT**. Libre para usar, estudiar y construir sobre él manteniendo la atribución al autor original.
