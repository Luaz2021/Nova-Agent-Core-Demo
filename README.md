# 🌌 NOVA Agent Core (Community Demo)
### Copiloto Técnico Senior & Arquitecta de Software Multiplataforma

![License](https://img.shields.io/badge/License-MIT-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-success)
![Engine](https://img.shields.io/badge/Native%20Engine-Google%20Antigravity%202.0-orange)
![Skills](https://img.shields.io/badge/Skills-115%20Verificadas-purple)
![Zero-Tokens](https://img.shields.io/badge/Instalacion-0%20Tokens-brightgreen)

**Nova** no es un plugin genérico ni una simple extensión de editor: es un **sistema de copiloto técnico autónomo diseñado nativa y exclusivamente para el motor de Google Antigravity 2.0**. 

Orquestada por el modelo **Gemini**, Nova toma el control del entorno de ejecución, gestiona terminales, compila proyectos, audita bases de datos, inspecciona navegadores y coordina subagentes especializados en segundo plano. Cero formalismos de secretaria sumisa: actitud de colega veterano, nivel de arquitecta senior y filosofía **KISS estricto** (Keep It Simple, Stupid).

Esta versión (**Community Edition**) es 100% libre, local, no requiere privilegios de administrador (`sudo`) y no contiene credenciales ni datos privados.

---

## ⚡ Instalación en 1 Clic (Zero-Tokens)

El instalador detecta automáticamente si tienes **Google Antigravity** en tu máquina. Si no está instalado, se encarga de descargarlo e instalarlo de manera oficial y automática antes de enlazar las 115 habilidades y reglas del agente.

### 🪟 En Windows (Doble Clic)
Haz doble clic en el archivo:
```text
instalar_nova.bat
```
*(O desde PowerShell: `powershell -ExecutionPolicy Bypass -File .\adapters\windows\install.ps1`)*

### 🍎 En macOS (Terminal)
```bash
sh ./instalar_nova.sh
```

### 🐧 En Linux (Bash)
```bash
sh ./instalar_nova.sh
```

---

## 🚀 ¿Qué es capaz de hacer Nova? (Músculos Técnicos)

Nova opera con una matriz de **115 habilidades especializadas** divididas por dominios de ingeniería real:

### 1. ☕ Backend de Alto Rendimiento & Bases de Datos
- **Arquitectura Limpia & Modular:** Desacoplamiento estricto por capas (Domain, Service, Repository, Controller) en Java 21, Spring Boot y FastAPI.
- **SQL & Bases de Datos ACID:** Eliminación del problema N+1, indexación inteligente (B-Tree/GIN), transacciones seguras y migraciones sin caída de servicio (Zero-Downtime) para PostgreSQL, MySQL, SQLite y Supabase.
- **Seguridad BaaS & Supabase RLS:** Bastionado zero-trust con políticas atómicas de Row Level Security (RLS) y aislamiento absoluto de llaves `service_role`.

### 2. 🌐 Frontend Anti-Slop, GSAP & Calidad Awwwards
- **Diseño Anti-Slop:** Cero componentes genéricos de IA. Interfaces con personalidad basadas en los manuales de diseño de marcas líderes mundiales (Stripe, Linear, Vercel, Apple, Supabase).
- **Coreografía Cinemática con GSAP & Lenis:** Scroll animado fluido, micro-interacciones a 60 FPS, timelines complejos y respeto por la directiva `prefers-reduced-motion`.
- **Rendimiento Web Real (Core Web Vitals):** Presupuestos de bundle estrictos (<100 KB gzip inicial), optimización de cascadas de peticiones (waterfalls) y eliminación de saltos de diseño (CLS).

### 3. 🛡️ Ciberseguridad Ofensiva Ética & Guardianes de Git
- **Auditoría Local (White-Hat):** Detección automática de API keys expuestas (Stripe, AWS, Gemini), puertos abiertos olvidados y validación de cabeceras HTTP seguras.
- **Git Guardian Activo:** Bloquea antes de hacer commit o push cualquier intento de subir archivos `.env` o sentencias SQL destructivas (`DELETE` sin `WHERE`).
- **Chaos QA:** Tester adversarial que busca activamente romper tu código con casos límite (edge cases), desbordamientos y condiciones de carrera antes de que llegue a producción.

### 4. 🧠 Calibrador Psicológico de Usuario (`user-intent-reader`)
- Nova analiza tu lenguaje de forma invisible y adapta su nivel pedagógico sin molestarte con preguntas:
  - **Perfil Estudiante / Principiante:** Modo mentor explicativo con analogías sencillas y paso a paso.
  - **Perfil Desarrollador / Pragmático:** Modo directo al grano, código limpio con early returns y comandos listos.
  - **Perfil Arquitecto / Senior:** Modo de trinchera, discusión de trade-offs, patrones de resiliencia y cero rodeos.

### 5. 🎙️ Protocolo de Voz Dual (Modo Cocina / Manos Libres)
- **Audio Ejecutivo (15-20 segundos):** Si la interacción es por voz o estás cocinando/lejos del teclado, Nova te resume la respuesta en 2 frases concisas por los altavoces mediante síntesis de Edge-TTS y reproductores nativos (`winmm` en Windows, `afplay` en Mac, `mpv/aplay` en Linux).
- **Detalle Técnico en Pantalla:** Toda la estructura, código completo, diagramas Mermaid y tablas quedan plasmados en el chat.

### 6. 🌙 Nova Awake Sentinel (Windows)
- Evita que tu PC se suspenda durante compilaciones largas, entrenamientos o descargas usando llamadas nativas `SetThreadExecutionState` (sin pulsar teclas falsas ni generar ruido), cuidando la batería al suspenderse limpiamente si baja del 10%.

---

## 💬 Comunicación Directa con el Creador

Nova cuenta con un canal integrado para conectar a la comunidad directamente con el autor del proyecto:

En cualquier momento puedes decirle a Nova en el chat:
> *"Nova, envía mensaje al creador: [tu duda o sugerencia]"*

Nova abrirá automáticamente una plantilla segura en GitHub Issues con tu mensaje redactado, **sanitizando de forma automática cualquier ruta privada, IP local o contraseña** para que nunca expongas tus datos personales.

---

## 🔒 Privacidad, Telemetría Ética y Manifiesto SHA-256

- **100% Local:** Tus proyectos, notas y código se quedan en tu máquina.
- **Telemetría Ética (Opt-In):** Una vez al mes, solo si lo autorizaste durante la instalación, Nova genera un resumen técnico anónimo (skills más usadas y patrones de error resueltos) para incorporar mejoras comunitarias.
- **Actualizaciones Cero-Conflictos:** Cuando Saúl Martínez publica una actualización oficial, el sincronizador valida los componentes mediante hashes criptográficos **SHA-256** (`manifest_master.json`), integrando las nuevas skills **sin tocar ni sobreescribir jamás tus archivos personales o notas locales**.

---

## 🏆 Créditos & Autoría

- **Creador y Arquitecto:** Alexander Martinez ([@Luaz2021](https://github.com/Luaz2021)) · Torrevieja, España
- **Motor de Inteligencia:** Google Gemini sobre Antigravity 2.0
- **Licencia:** MIT (Open Source de distribución comunitaria)
