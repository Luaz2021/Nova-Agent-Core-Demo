---
name: gemini-omniroute-manager
description: "Estrategia de optimización de costos y gestión de maratones de código con OmniRoute. Agota primero las cuotas y pools de tokens gratuitos (Groq, Mistral, Google AI Studio, Cloudflare) antes de consumir cuotas de pago de Claude Sonnet o Gemini Pro."
---

# ⚡ OmniRoute Token Optimizer & Marathon Protocol

Protocolo de gestión de costos para sesiones largas de programación (8 a 12 horas).

## 1. La Regla de Oro: "Primero lo Gratis, Reserva lo de Pago"
Cuando Alexander diga:
- *"Nova, estaré 12 horas programando, activa OmniRoute"*
- *"Modo maratón de código"*
- *"Gasta lo gratis primero"*

El agente activa la estrategia de cascada (*Ladder Fallback*):

### Fase 1: Pool Gratuito (0€ / 0 Tokens de Pago)
1. Enrutar consultas de chat, formateo, pruebas unitarias y búsquedas a proveedores con capas gratuitas generosas:
   - **Groq / Cerebras**: Inferencia ultra rápida de Llama 3.3 / Qwen (cuota gratuita diaria).
   - **Google AI Studio (Gemini Flash Free)**: 15 peticiones por minuto gratuitas.
   - **Cloudflare Workers AI**: Modelos open source sin coste.

### Fase 2: Cuota Base de Antigravity (Gemini 3.8 Flash Low)
- Si los pools externos gratuitos se saturan por rate limit temporal, pasar a la ventana de 5 horas de **Gemini 3.8 Flash**.

### Fase 3: Artillería Pesada Reservada (Claude Sonnet 5.5 / Opus / Argon)
- **Bloqueado para tareas triviales**.
- Solo se activa cuando Alexander pida explícitamente:
  - Diseño de arquitectura de microservicios compleja.
  - Refactorización de código crítico de producción.
  - Resolución de bugs imposibles que requieran razonamiento profundo.
