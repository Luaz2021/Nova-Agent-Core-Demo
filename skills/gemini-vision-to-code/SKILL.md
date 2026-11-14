---
name: gemini-vision-to-code
description: "Convierte capturas, bocetos o diseños de Figma en codigo frontend limpio y responsivo (React, Tailwind, HTML/CSS)."
trigger: model_decision
---

# Screenshot to Code (Visual-to-Code Converter)

Esta habilidad aprovecha la visión multimodal nativa de Gemini para transformar cualquier captura de pantalla o imagen de una página web en código frontend idéntico, estructurado y listo para producción.

---

## 1. Cuándo se Activa Esta Habilidad

El agente activará esta habilidad cuando:
- El usuario adjunte una imagen o captura de pantalla y diga: *"Recrea esta web"*, *"Pasa esto a código"*, *"Hazme este componente igual a la foto"*, *"Copia este diseño"*.
- Se proporcione una URL de una imagen con una interfaz de usuario.

---

## 2. Metodología de Recreación Visual (4 Fases)

### Fase 1: Descomposición Anatómica de la Imagen
Antes de escribir una sola línea de código, el agente desglosa visualmente la captura:
1. **Layout y Cuadrícula:**
   - Detectar la estructura general: flexbox vs grid, columnas, alineación (izquierda, centro, split).
   - Identificar anchos máximos (`max-w-7xl`, `max-w-5xl`) y márgenes laterales.
2. **Paleta Cromática Exacta:**
   - Color de fondo exacto (`bg-slate-900`, `bg-[#0a0a0c]`, etc.).
   - Colores de texto primario, secundario y atenuado (muted).
   - Color de acento/marca (botones primarios, enlaces activos, badges).
   - Bordes sutiles y sombras (`border-slate-800`, `shadow-xl`).
3. **Escala Tipográfica y Pesos:**
   - Detección de títulos grandes (`font-bold text-4xl`), subtítulos y etiquetas.
4. **Componentización:**
   - Descomponer la pantalla en componentes reutilizables (Navbar, Hero, FeatureCard, PricingTable, Footer) en lugar de un único archivo monolítico.

### Fase 2: Reglas de Fidelidad Visual
- **Iconos:** Mapear los iconos de la imagen a la librería de iconos del proyecto (por defecto **Lucide React** o Heroicons). Si un icono no existe idéntico, usar el equivalente semántico más cercano.
- **Imágenes / Avatares:** Si la captura contiene fotografías o avatares, utilizar placeholders limpios de Unsplash (`https://images.unsplash.com/...`) con el `aspect-ratio`, `object-fit: cover` y `rounded-*` acordes a la captura.
- **Responsividad:** Asegurar que el diseño no solo se vea idéntico en escritorio sino que sea mobile-first (`flex-col md:flex-row`).

### Fase 3: Integración de Estándares de Calidad
- Integrar automáticamente las pautas de `web-design-guidelines`:
  - `focus-visible:ring-2` en botones e inputs.
  - Cero `outline: none` sin reemplazo.
  - Iconos decorativos con `aria-hidden="true"`.
  - Botones de acción semánticos `<button>` y enlaces `<Link>` / `<a>`.

### Fase 4: Entrega del Código
- Generar el código limpio en el framework preferido del usuario (por defecto **React + Tailwind CSS + TypeScript**).
- Entregar componentes modulares listos para copiar o guardar en el proyecto.

