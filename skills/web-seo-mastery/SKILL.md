---
name: web-seo-mastery
description: "Optimizador de SEO tecnico: metadatos Title/Description, Open Graph, jerarquia H1-H6, sitemap.xml y Schema JSON-LD."
trigger: model_decision
---

# Web SEO Mastery & Semantic Architecture (El Motor de Posicionamiento)

Esta habilidad asegura que cualquier sitio web o aplicación esté optimizado técnica y semánticamente para indexar en los primeros lugares de Google y en motores de respuesta de IA (ChatGPT, Gemini, Perplexity), auditando la estructura del DOM y generando los artefactos técnicos necesarios.

---

## 1. Cuándo se Activa
Se activa automáticamente cuando el usuario dice:
- *"Optimiza el SEO de esta página"*, *"Revisa las palabras clave o metadatos"*, *"Genera el sitemap o robots.txt"*, *"Revisa si el DOM está bien estructurado para Google"*, *"Crea el Schema JSON-LD para este negocio/producto"*, *"Audita si esta web posiciona bien"*.

---

## 2. Los 4 Pilares del SEO Técnico Moderno

### Pilar 1: Metadatos y Social Cards (Open Graph / Twitter)
En cada página (`<head>` en HTML o `metadata` en Next.js):
1. **Title Tag:** Entre 50 y 60 caracteres. Fórmula: `[Palabra Clave Principal] | [Nombre de Marca]` (ej. `Alquiler Dúplex Miraflores | Bolívar 1209`).
2. **Meta Description:** Entre 130 y 155 caracteres con gancho persuasivo y llamada a la acción (CTA).
3. **Canonical Tag:** `<link rel="canonical" href="https://dominio.com/pagina" />` para evitar duplicados.
4. **Open Graph & Twitter Cards:** `og:title`, `og:description`, `og:image` (1200x630px) para que al compartir por WhatsApp o Instagram se vea una miniatura profesional.

### Pilar 2: Jerarquía Semántica del DOM (Lectura Humana y de Bots)
- **Regla del H1 Único:** Exactamente un solo `<h1>` por página con la entidad o propuesta de valor principal.
- **Anidación lógica:** Nunca saltar de `<h2>` a `<h4>` sin pasar por `<h3>`.
- **Atributos ALT en imágenes:** Descriptivos y contextuales para SEO de imágenes y accesibilidad.
- **URLs amigables:** Sin IDs raros (`/servicios/manicura-rusa` en lugar de `/service?id=823`).

### Pilar 3: Datos Estructurados (Schema Markup JSON-LD)
Google premia las webs que le explican su contenido mediante esquemas JSON-LD embebidos en el `<head>`.
* **Para Negocios Locales (Salón Nails, Depa Airbnb):**
  - Esquema `LocalBusiness` / `LodgingBusiness`: Dirección, teléfono, horarios, coordenadas, rango de precios.
* **Para Artículos / Blog:**
  - Esquema `Article` con autor, fecha de publicación y breadcrumbs.
* **Para FAQs (Preguntas Frecuentes):**
  - Esquema `FAQPage` para que Google muestre las preguntas desplegables directamente en la página de resultados de búsqueda.

### Pilar 4: Artefactos de Indexación (Sitemap y Robots)
1. **`robots.txt`:** Define qué rutas rastrear y enlaza el sitemap:
   ```txt
   User-agent: *
   Allow: /
   Disallow: /admin/
   Disallow: /api/
   Sitemap: https://tudominio.com/sitemap.xml
   ```
2. **`sitemap.xml`:** Mapa limpio de URLs canónicas con fechas `<lastmod>` precisas y protocolo W3C.

---

## 3. Checklist de Auditoría SEO en 60 Segundos

1. `[ ]` ¿Hay exactamente un solo `<h1>` en la página principal?
2. `[ ]` ¿El `title` tiene menos de 60 caracteres y la `description` menos de 160?
3. `[ ]` ¿Tiene implementada la imagen Open Graph para redes sociales (`og:image`)?
4. `[ ]` ¿Existe un bloque `JSON-LD` con el Schema del negocio o servicio?
5. `[ ]` ¿Están presentes `sitemap.xml` y `robots.txt`?
