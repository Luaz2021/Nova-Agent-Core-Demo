# GUÍA QWEN — por dónde van los tiros

Guía para trabajar con **qwen2.5-coder:7b** (Ollama, RTX de 8 GB) en webs: generar, clonar (para estudio) y corregir.
La parte A es para ti; la parte B se le pasa a Qwen como mensaje de sistema.

---

## A. Para ti: cómo se trabaja

### El reparto de papeles
| Quién | Hace | No hace |
|---|---|---|
| **analizar.py** (pasos 1-3) | Medir la web, fotos PC/tablet/móvil, hover, scroll, Qwen con ojos, informes | Escribir diseño |
| **Claude** (paso 4) | Leer los informes (texto) y 5-15 fotos, definir `diseno.json`, escribir instrucciones cortas por sección, reparar lo rojo | Escribir el código entero |
| **Qwen Coder** (paso 5) | Escribir **una sección** (~2.000 tokens) con su ficha + la instrucción de Claude | Pensar la web entera |
| **construir.py** (paso 6) | Verificar cada sección contra la original (PC y móvil), pedir a Qwen 2 correcciones, quedarse la mejor | — |

### El punto dulce de Qwen 7B (medido en las pruebas)
| | Bien | Empieza a fallar | Se rompe |
|---|---|---|---|
| Lee (entrada) | ≤ 8.000 tokens (~15 KB de HTML) | > 12.000 | contexto de 24K lleno (num_ctx) |
| Escribe (salida) | ≤ 7.000 tokens (~13 KB de HTML) | > 7.500 | se corta a los 8.192 (num_predict) |
| Instrucciones por petición | 5-8 | 15+ | 25+ |
| Tamaño de la tarea | 1 sección | página entera | — |
| Velocidad (RTX 8 GB) | 40-50 tokens/s → 2.000 tokens < 1 min · una sección de 10 KB ≈ 2-3 min | | |

Ojo con el HTML con clases de Tailwind: el tokenizador de Qwen da **~1,9 caracteres por token** (un texto normal da ~4).
Como Qwen devuelve la sección ENTERA al repararla, el límite real es la salida: secciones de más de ~13,6 KB
(verificar.py: MAX_CODIGO_QWEN) van directas a Claude. Parámetros en construir.py: NUM_PREDICT, NUM_CTX, CAR_POR_TOKEN.

1 token ≈ 3-4 caracteres. Opciones fijas: `temperature 0`, `seed 42`, `num_ctx 16384`.

### El flujo
```
1-3  1_ANALIZAR.bat   -> pruebas_Qwen/<web>/ informe_pc.md, informe_movil.md, diferencias_pc_movil.md,
                         fichas_secciones.md, capturas/ (pc, tablet, móvil, secciones, hover, scroll)
4    Claude           -> pruebas_Qwen/<web>/claude/diseno.json + claude/sec_N.md (200-400 tokens cada una)
5-6  2_CONSTRUIR.bat  -> construccion/index.html, revision.html (original | Qwen), pendientes_claude.md
7    Claude           -> repara solo las secciones de pendientes_claude.md
```

### Lo que escribe Claude en el paso 4
`claude/diseno.json` (nombres cortos; Qwen los usa como `bg-tinta`, `font-titulo`):
```json
{"colores": {"tinta": "#29353C", "fondo": "#F3FAF5", "acento": "#E8A0A0"},
 "fuentes": {"titulo": "Playfair Display", "texto": "Inter"},
 "notas": "botones píldora (rounded-full), mucho aire: py-[80px] en escritorio"}
```
`claude/sec_N.md` — corto, con clases exactas, 5-8 puntos:
```
Estructura: flex flex-col md:flex-row, imagen a la izquierda (md:w-1/2), texto a la derecha.
- Título: font-titulo text-[32px] md:text-[56px] text-tinta leading-[1.1]
- Botón: bg-tinta text-white rounded-full px-[28px] py-[14px] text-[14px] uppercase
- En móvil la imagen va arriba y ocupa w-full h-[260px] object-cover
```
Sin `claude/` Qwen trabaja solo con las fichas (sirve como prueba, pero sale peor).

### Reglas de oro (aprendidas a base de fallos)
1. **Código de ejemplo exacto > instrucciones en prosa.** "Usa `text-[44px]`" funciona; "más grande" no.
2. **Editar sobre su versión anterior** en vez de regenerar (8/12 → 10/12).
3. **Modo parche:** solo las secciones con fallos. Con la página entera delante copia el final sin cambios.
4. **Ejemplos neutros:** Qwen copia el estilo de los ejemplos (le puso el hero de Olive & June a Basecamp).
5. **La cabecera del HTML la monta el script** (fuentes, CDN, `<head>`). Qwen solo escribe `<section>`.
6. **Secciones con más de 30 textos:** partirlas en sub-bloques antes de pasárselas.
7. **Verificar todo:** si un cambio baja el parecido, se descarta. Nunca confiar a ciegas.

### Según el tipo de web (lo dice `informe_pc.md`)
- **Landing / marketing:** el caso ideal. Sección a sección.
- **Tienda:** igual que landing + componentes repetidos (tarjeta de producto ×N): Qwen escribe **la tarjeta una vez** y el script la repite con los datos.
- **Aplicación (SPA) o con iframes grandes:** solo el aspecto. Los iframes se sustituyen por una captura o un hueco; la lógica se programa aparte.
- **Con movimiento** (scroll, GSAP, AOS, carruseles): primero la versión estática; luego una pasada de movimiento, un efecto por petición ("IntersectionObserver con fundido de 0,6 s para estos elementos").

---

## B. Mensaje de sistema para Qwen (copiar tal cual)

```
Eres un desarrollador front-end. Escribes UNA sección de una página con Tailwind CSS (CDN) a partir de una FICHA con medidas reales.
La ficha manda: no inventes estilo, traduce las medidas a código.

FORMATO
- Responde solo con: <!-- SECCIÓN N --> y un único <section>...</section>. Sin <html>, <head>, <style>, <script> ni explicaciones.

TRADUCCIÓN
- Tamaños: base = móvil, md: = escritorio. "44px (móvil 28px)" -> text-[28px] md:text-[44px].
- Colores exactos con corchetes: text-[#29353C] bg-[#F3FAF5]. Pesos: font-[800].
- Fuentes: font-['Inter'] (la que diga la ficha). Mayúsculas solo si la ficha dice MAYÚS.
- Columnas: "móvil 1, tablet 2, escritorio 3" -> grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3.
- Imagen + texto en fila: flex flex-col md:flex-row. Contenedor seguro 1080p: max-w-[1400px] mx-auto px-4.
- Botones: copia fondo, color, radio (0 = sin rounded), padding y tamaño de la ficha.
- Imágenes, vídeos e iframes: NO pongas URLs. Escribe el MARCO con la proporción y el color de la ficha:
  <div class="w-full aspect-[4/3] overflow-hidden rounded-[12px] bg-[#D8C9B5]"><img alt="descripción" class="w-full h-full object-cover"></div>
  logo: <img alt="logo" class="h-[40px] w-auto object-contain"> · avatar: añade rounded-full · vídeo: <video class="w-full h-full object-cover"></video>
  (el script rellena los medios después; tú solo construyes el marco)
- Textos: literales y en el mismo orden.

PROHIBIDO
- @apply, la clase "container", clases que no sean de Tailwind, colores aproximados.
- Iconos de Font Awesome sin familia (usa fa-solid / fa-regular).
- Que algo se salga en móvil (375px): usa w-full, flex-col u overflow-x-auto.

SI TE DAN UNA LISTA DE DIFERENCIAS
- Corrige SOLO eso, cambiando lo mínimo. Conserva todo lo demás exactamente igual.
```
