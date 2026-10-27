---
name: gemini-vision-to-code
trigger: model_decision
description: "Convierte capturas de pantalla, bocetos de diseÃ±o, imÃ¡genes de Figma o fotos de interfaces web en cÃ³digo frontend limpio, moderno y responsivo (React, Tailwind CSS, Next.js o HTML/CSS) recreando con mÃ¡xima fidelidad la estructura, colores, espaciados y tipografÃ­as."
---

# Screenshot to Code (Visual-to-Code Converter)

Esta habilidad aprovecha la visiÃ³n multimodal nativa de Gemini para transformar cualquier captura de pantalla o imagen de una pÃ¡gina web en cÃ³digo frontend idÃ©ntico, estructurado y listo para producciÃ³n.

---

## 1. CuÃ¡ndo se Activa Esta Habilidad

El agente activarÃ¡ esta habilidad cuando:
- El usuario adjunte una imagen o captura de pantalla y diga: *"Recrea esta web"*, *"Pasa esto a cÃ³digo"*, *"Hazme este componente igual a la foto"*, *"Copia este diseÃ±o"*.
- Se proporcione una URL de una imagen con una interfaz de usuario.

---

## 2. MetodologÃ­a de RecreaciÃ³n Visual (4 Fases)

### Fase 1: DescomposiciÃ³n AnatÃ³mica de la Imagen
Antes de escribir una sola lÃ­nea de cÃ³digo, el agente desglosa visualmente la captura:
1. **Layout y CuadrÃ­cula:**
   - Detectar la estructura general: flexbox vs grid, columnas, alineaciÃ³n (izquierda, centro, split).
   - Identificar anchos mÃ¡ximos (`max-w-7xl`, `max-w-5xl`) y mÃ¡rgenes laterales.
2. **Paleta CromÃ¡tica Exacta:**
   - Color de fondo exacto (`bg-slate-900`, `bg-[#0a0a0c]`, etc.).
   - Colores de texto primario, secundario y atenuado (muted).
   - Color de acento/marca (botones primarios, enlaces activos, badges).
   - Bordes sutiles y sombras (`border-slate-800`, `shadow-xl`).
3. **Escala TipogrÃ¡fica y Pesos:**
   - DetecciÃ³n de tÃ­tulos grandes (`font-bold text-4xl`), subtÃ­tulos y etiquetas.
4. **ComponentizaciÃ³n:**
   - Descomponer la pantalla en componentes reutilizables (Navbar, Hero, FeatureCard, PricingTable, Footer) en lugar de un Ãºnico archivo monolÃ­tico.

### Fase 2: Reglas de Fidelidad Visual
- **Iconos:** Mapear los iconos de la imagen a la librerÃ­a de iconos del proyecto (por defecto **Lucide React** o Heroicons). Si un icono no existe idÃ©ntico, usar el equivalente semÃ¡ntico mÃ¡s cercano.
- **ImÃ¡genes / Avatares:** Si la captura contiene fotografÃ­as o avatares, utilizar placeholders limpios de Unsplash (`https://images.unsplash.com/...`) con el `aspect-ratio`, `object-fit: cover` y `rounded-*` acordes a la captura.
- **Responsividad:** Asegurar que el diseÃ±o no solo se vea idÃ©ntico en escritorio sino que sea mobile-first (`flex-col md:flex-row`).

### Fase 3: IntegraciÃ³n de EstÃ¡ndares de Calidad
- Integrar automÃ¡ticamente las pautas de `web-design-guidelines`:
  - `focus-visible:ring-2` en botones e inputs.
  - Cero `outline: none` sin reemplazo.
  - Iconos decorativos con `aria-hidden="true"`.
  - Botones de acciÃ³n semÃ¡nticos `<button>` y enlaces `<Link>` / `<a>`.

### Fase 4: Entrega del CÃ³digo
- Generar el cÃ³digo limpio en el framework preferido del usuario (por defecto **React + Tailwind CSS + TypeScript**).
- Entregar componentes modulares listos para copiar o guardar en el proyecto.

