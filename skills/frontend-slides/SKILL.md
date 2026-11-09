---
name: frontend-slides
description: "Generacion de presentaciones web en un solo archivo HTML sin dependencias (Single-File Deck). Escenario rigido 16:9 (1920x1080), estetica Anti-AI-Slop, tipografias con caracter y micro-interacciones CSS."
metadata:
  version: "1.0.0"
  source: "https://github.com/zarazhangrui/frontend-slides"
  author: "Zara Zhang / Adaptado a Nova"
---

# Frontend Slides · Zero-Dependency HTML Decks

Doctrina para generar presentaciones interactivas en la web, autónomas y sin empaquetadores ni frameworks (`npm`, `webpack` o `vite`).

## 1. Principios Anti-AI-Slop

1. **Cero Clichés de IA:**
   - Prohibidos los gradientes morados sobre fondo blanco.
   - Prohibidas las tipografías genéricas sin carácter (`Inter`, `Arial`, `Roboto` por defecto). Usar combinaciones tipográficas de impacto (`Space Grotesk`, `Playfair Display`, `Outfit`, `Syne`).
2. **Escenario Rígido 16:9 (`1920x1080`):**
   - Cada presentación se diseña dentro de un lienzo fijo de `1920 x 1080` píxeles.
   - Se escala uniformemente al viewport del navegador mediante `transform: scale(...)` con `transform-origin: center center`.
   - Prohibido hacer "reflow" responsive que descoloque los elementos de la diapositiva en pantallas pequeñas; la diapositiva debe mantener su relación de aspecto fija exactamente igual que en un proyector de conferencias.
3. **Visibilidad y Estados de Transición:**
   - Usar clases de visibilidad (`.active`, `.visible`) controlando `opacity` y `visibility`.
   - Prohibido alternar entre `display: none` y `display: block` directamente si hay reglas de flexbox o grid que puedan sobreescribirlas.

## 2. Casos de Uso en Nova

- Pitch decks para inversores o demos de producto en vivo.
- Generación de mockups de capturas y ventanas de software (ej. navegadores macOS/Chrome para evidenciar prompts de IA o interfaces).
- Exportación a PDF para impresión o distribución web ultraligera (< 200 KB por deck completo).
