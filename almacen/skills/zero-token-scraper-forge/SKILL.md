---
name: zero-token-scraper-forge
description: "Crea micro-scripts reutilizables en Python/PowerShell (scripts/scrapers/) para extraccion web a 0 tokens de LLM."
---

# Zero-Token Scraper Forge

## Propósito
Evitar levantar navegadores completos (Playwright, Brave) o gastar tokens de IA para tareas repetitivas de extracción de datos web o monitoreo de sitios.

## Principio API/CLI First
- **Regla Suprema:** Antes de raspar HTML o simular clicks en navegador, verificar si el servicio ofrece:
  1. API oficial gratuita (ej. YouTube Data API v3, GitHub API, OpenWeather).
  2. Endpoints JSON internos (Network tab XHR/Fetch).
  3. Herramientas CLI nativas (`yt-dlp`, `curl`, `gh`).

## Flujo de Trabajo
1. **Inspección Inicial (Fase Única):**
   - Identificar el endpoint REST subyacente o el selector CSS exacto.
2. **Forjado del Micro-Script:**
   - Crear un script Python ultraligero (`requests` o `httpx`) en `scripts/scrapers/<servicio>.py`.
3. **Ejecución a Cero Tokens:**
   - Consultas posteriores ejecutan directamente el script local devolviendo el resultado en JSON/texto en milisegundos sin coste de LLM.
