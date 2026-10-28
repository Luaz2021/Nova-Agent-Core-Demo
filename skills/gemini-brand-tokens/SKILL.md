---
name: gemini-brand-tokens
description: "Catalogo de Design Systems de 156 marcas lideres (Stripe, Linear, Apple, Airbnb, Vercel, Supabase) via DESIGN.md."
trigger: model_decision
---

# Awesome Design-MD (Brand Design Systems & Tokens)

Esta habilidad proporciona una biblioteca curada de mÃ¡s de 60 sistemas de diseÃ±o completos basados en el estÃ¡ndar `DESIGN.md` (popularizado por Google Stitch y VoltAgent). Permite aplicar la estÃ©tica visual, paletas de colores precisas (hexadecimales), escalas tipogrÃ¡ficas y estilos de componentes inspirados en las marcas tecnolÃ³gicas y de consumo mÃ¡s admiradas del mundo.

---

## 1. CuÃ¡ndo Invocar Esta Habilidad

El agente activarÃ¡ esta habilidad cuando:
- El usuario diga: *"Haz que se vea como Stripe"*, *"Usa el estilo de Linear"*, *"Quiero una estÃ©tica minimalista tipo Apple o Raycast"*, *"Aplica el diseÃ±o de Supabase / Vercel"*.
- El usuario pida recomendaciones de paletas de colores, tipografÃ­as o tokens visuales para su aplicaciÃ³n.
- Se solicite crear o inyectar un archivo `DESIGN.md` en la raÃ­z de un proyecto para definir su diseÃ±o.

---

## 2. Marcas y Presets Disponibles

La biblioteca de presets se encuentra almacenada en:
- `presets/<marca>/DESIGN.md` dentro de esta skill.

### CategorÃ­as Principales:
- **Developer Tools & Tech:** `stripe`, `linear.app`, `vercel`, `supabase`, `raycast`, `cursor`, `warp`, `posthog`, `resend`, `hashicorp`.
- **Minimalistas & Productividad:** `apple`, `notion`, `framer`, `cal`, `superhuman`, `figma`.
- **Fintech & Crypto:** `revolut`, `wise`, `mercury`, `coinbase`, `binance`, `kraken`.
- **AI & Modern Labs:** `claude`, `elevenlabs`, `cohere`, `replicate`, `runwayml`, `ollama`.
- **Consumer & Lifestyle:** `nike`, `spotify`, `airbnb`, `tesla`, `playstation`, `starbucks`.

---

## 3. CÃ³mo Aplicar un Estilo a un Proyecto

1. **Lectura del Preset:**  
   El agente lee el archivo correspondiente en `presets/<marca>/DESIGN.md` para extraer los tokens:
   - Paleta cromÃ¡tica (colores primarios, fondos `canvas`, bordes `hairline`, estados interactivos).
   - TipografÃ­a (familias de fuentes recomendadas, tamaÃ±os `display`, pesos, letter-spacing).
   - Componentes clave (radio de bordes de botones, sombras, espaciados).
2. **GeneraciÃ³n o Copia de `DESIGN.md`:**  
   Si el usuario quiere conservar el diseÃ±o en su repositorio, el agente copiarÃ¡ o generarÃ¡ `DESIGN.md` en la raÃ­z del proyecto activo para que sea la guÃ­a permanente de estilo.
3. **ConstrucciÃ³n en Tailwind / CSS:**  
   Al redactar componentes (React, Vue, HTML, etc.), el agente mapearÃ¡ directamente los tokens del `DESIGN.md` a clases de Tailwind o variables CSS (CSS Variables) para lograr el look & feel idÃ©ntico al de la marca seleccionada.


## 156-Brand DESIGN.md Library

This skill includes full, verified `DESIGN.md` guidelines for 150+ world-leading brands located in `design-md-library/`:
`1password, acer, adobe, adp, affirm, airbnb, airtable, amazon, amd, anthropic, apple, arm, asana, asus, atlassian, autodesk, behance, bestbuy, bloomberg, booking, box, brex, canva, cisco, clickup, cloudflare, coinbase, confluent, costco, coursera` ... and 126 more!

To apply any brand aesthetic (e.g. Stripe, Airbnb, Apple, Linear, Coinbase, Vercel, Supabase), read its file from `design-md-library/<brand>.md` and apply its colors, typography, border radius, and layout rules.
