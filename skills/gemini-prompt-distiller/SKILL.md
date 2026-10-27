---
name: gemini-prompt-distiller
trigger: always_on
description: "Optimizador integral de tokens y destilador de contexto (inspirado en Headroom y Claude Token Optimizer). Filtra ruido conversacional en prompts, aplica carga progresiva de documentaciÃ³n (.geminiignore / context routing) y evita respuestas infladas, ahorrando hasta un 90% de tokens de inicio y respuesta."
---

# Token Optimizer & Context Distiller

Esta habilidad fusiona dos dimensiones del ahorro de tokens:
1. **OptimizaciÃ³n en Tiempo de Inicio (Repo & Context Optimization - CTO):** Evita que archivos gigantes de documentaciÃ³n, logs o historiales pasados se carguen de golpe al iniciar la sesiÃ³n.
2. **DestilaciÃ³n en Tiempo de EjecuciÃ³n (Prompt Distiller - Headroom):** Filtra anÃ©cdotas y divagaciones en los mensajes del usuario para responder con mÃ¡xima precisiÃ³n tÃ©cnica y mÃ­nima verbosidad.

---

## 1. OptimizaciÃ³n del Espacio de Trabajo (Carga Progresiva)

Al abrir o trabajar en cualquier repositorio:
- **Regla del 90% (Lean Startup):** El archivo principal de reglas (`GEMINI.md`) debe mantenerse ligero (< 1,000 tokens) con solo comandos esenciales y arquitectura general.
- **DivisiÃ³n en Referencias Bajo Demanda:** Las guÃ­as extensas de arquitectura, API o esquemas de base de datos se colocan en archivos secundarios (ej. `docs/api.md`, `docs/database.md`) y el agente **solo las lee cuando el usuario pregunta especÃ­ficamente por ellas**.
- **Ignorar Basura de Contexto:** Asegurar la exclusiÃ³n de carpetas pesadas en el escaneo inicial (`node_modules/`, `dist/`, `.git/`, logs, coverage, archivos de build).

---

## 2. DestilaciÃ³n de Solicitudes (Zero-Noise Filtering)

Cuando el usuario envÃ­e mensajes extensos o conversacionales:
1. **Extraer el Core TÃ©cnico:** Identificar el entregable real (bug a solucionar, endpoint a crear, script a redactar).
2. **Identificar Restricciones Obligatorias:** LibrerÃ­as exigidas, rutas especÃ­ficas o tipos de datos requeridos.
3. **Descartar Relleno:** Ignorar anÃ©cdotas personales, quejas del cliente o justificaciones previas que no alteran el cÃ³digo.

---

## 3. Salida Ultra-Eficiente del Agente (Verbosity Steering)

- **Cero Ceremonia:** No decir *"Entiendo perfectamente tu situaciÃ³n..."* ni repetir el prompt.
- **CÃ³digo y Diffs Concisos:** Mostrar Ãºnicamente las lÃ­neas modificadas con 1 o 2 lÃ­neas de contexto, nunca el archivo de 500 lÃ­neas entero si solo cambiÃ³ un `if`.
- **AcciÃ³n Inmediata:** Si el usuario pide un cambio, aplicar la herramienta o el cÃ³digo directamente.

