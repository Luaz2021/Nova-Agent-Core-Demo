---
name: gemini-prompt-distiller
description: "Destilador de contexto y optimizador de tokens: carga progresiva de documentacion y cero respuestas infladas."
trigger: always_on
---

# Token Optimizer & Context Distiller

Esta habilidad fusiona dos dimensiones del ahorro de tokens:
1. **Optimización en Tiempo de Inicio (Repo & Context Optimization - CTO):** Evita que archivos gigantes de documentación, logs o historiales pasados se carguen de golpe al iniciar la sesión.
2. **Destilación en Tiempo de Ejecución (Prompt Distiller - Headroom):** Filtra anécdotas y divagaciones en los mensajes del usuario para responder con máxima precisión técnica y mínima verbosidad.

---

## 1. Optimización del Espacio de Trabajo (Carga Progresiva)

Al abrir o trabajar en cualquier repositorio:
- **Regla del 90% (Lean Startup):** El archivo principal de reglas (`GEMINI.md`) debe mantenerse ligero (< 1,000 tokens) con solo comandos esenciales y arquitectura general.
- **División en Referencias Bajo Demanda:** Las guías extensas de arquitectura, API o esquemas de base de datos se colocan en archivos secundarios (ej. `docs/api.md`, `docs/database.md`) y el agente **solo las lee cuando el usuario pregunta específicamente por ellas**.
- **Ignorar Basura de Contexto:** Asegurar la exclusión de carpetas pesadas en el escaneo inicial (`node_modules/`, `dist/`, `.git/`, logs, coverage, archivos de build).

---

## 2. Destilación de Solicitudes (Zero-Noise Filtering)

Cuando el usuario envíe mensajes extensos o conversacionales:
1. **Extraer el Core Técnico:** Identificar el entregable real (bug a solucionar, endpoint a crear, script a redactar).
2. **Identificar Restricciones Obligatorias:** Librerías exigidas, rutas específicas o tipos de datos requeridos.
3. **Descartar Relleno:** Ignorar anécdotas personales, quejas del cliente o justificaciones previas que no alteran el código.

---

## 3. Salida Ultra-Eficiente del Agente (Verbosity Steering)

- **Cero Ceremonia:** No decir *"Entiendo perfectamente tu situación..."* ni repetir el prompt.
- **Código y Diffs Concisos:** Mostrar únicamente las líneas modificadas con 1 o 2 líneas de contexto, nunca el archivo de 500 líneas entero si solo cambió un `if`.
- **Acción Inmediata:** Si el usuario pide un cambio, aplicar la herramienta o el código directamente.

