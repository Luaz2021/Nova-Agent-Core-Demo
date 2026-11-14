---
name: gemini-brand-tokens
description: "Catalogo de Design Systems de 156 marcas lideres (Stripe, Linear, Apple, Airbnb, Vercel, Supabase) via DESIGN.md."
trigger: model_decision
---

# Awesome Design-MD (Brand Design Systems & Tokens)

Esta habilidad proporciona una biblioteca curada de más de 60 sistemas de diseño completos basados en el estándar `DESIGN.md` (popularizado por Google Stitch y VoltAgent). Permite aplicar la estética visual, paletas de colores precisas (hexadecimales), escalas tipográficas y estilos de componentes inspirados en las marcas tecnológicas y de consumo más admiradas del mundo.

---

## 1. Cuándo Invocar Esta Habilidad

El agente activará esta habilidad cuando:
- El usuario diga: *"Haz que se vea como Stripe"*, *"Usa el estilo de Linear"*, *"Quiero una estética minimalista tipo Apple o Raycast"*, *"Aplica el diseño de Supabase / Vercel"*.
- El usuario pida recomendaciones de paletas de colores, tipografías o tokens visuales para su aplicación.
- Se solicite crear o inyectar un archivo `DESIGN.md` en la raíz de un proyecto para definir su diseño.

---

## 2. Marcas y Presets Disponibles

La biblioteca de presets se encuentra almacenada en:
- `presets/<marca>/DESIGN.md` dentro de esta skill.

### Categorías Principales:
- **Developer Tools & Tech:** `stripe`, `linear.app`, `vercel`, `supabase`, `raycast`, `cursor`, `warp`, `posthog`, `resend`, `hashicorp`.
- **Minimalistas & Productividad:** `apple`, `notion`, `framer`, `cal`, `superhuman`, `figma`.
- **Fintech & Crypto:** `revolut`, `wise`, `mercury`, `coinbase`, `binance`, `kraken`.
- **AI & Modern Labs:** `claude`, `elevenlabs`, `cohere`, `replicate`, `runwayml`, `ollama`.
- **Consumer & Lifestyle:** `nike`, `spotify`, `airbnb`, `tesla`, `playstation`, `starbucks`.

---

## 3. Cómo Aplicar un Estilo a un Proyecto

1. **Lectura del Preset:**  
   El agente lee el archivo correspondiente en `presets/<marca>/DESIGN.md` para extraer los tokens:
   - Paleta cromática (colores primarios, fondos `canvas`, bordes `hairline`, estados interactivos).
   - Tipografía (familias de fuentes recomendadas, tamaños `display`, pesos, letter-spacing).
   - Componentes clave (radio de bordes de botones, sombras, espaciados).
2. **Generación o Copia de `DESIGN.md`:**  
   Si el usuario quiere conservar el diseño en su repositorio, el agente copiará o generará `DESIGN.md` en la raíz del proyecto activo para que sea la guía permanente de estilo.
3. **Construcción en Tailwind / CSS:**  
   Al redactar componentes (React, Vue, HTML, etc.), el agente mapeará directamente los tokens del `DESIGN.md` a clases de Tailwind o variables CSS (CSS Variables) para lograr el look & feel idéntico al de la marca seleccionada.


## 156-Brand DESIGN.md Library

This skill includes full, verified `DESIGN.md` guidelines for 150+ world-leading brands located in `design-md-library/`:
`1password, acer, adobe, adp, affirm, airbnb, airtable, amazon, amd, anthropic, apple, arm, asana, asus, atlassian, autodesk, behance, bestbuy, bloomberg, booking, box, brex, canva, cisco, clickup, cloudflare, coinbase, confluent, costco, coursera` ... and 126 more!

To apply any brand aesthetic (e.g. Stripe, Airbnb, Apple, Linear, Coinbase, Vercel, Supabase), read its file from `design-md-library/<brand>.md` and apply its colors, typography, border radius, and layout rules.
