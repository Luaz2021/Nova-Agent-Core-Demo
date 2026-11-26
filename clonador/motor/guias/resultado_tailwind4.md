# Prueba de la guía «tailwind4»

_2026-11-01 22:34 · qwen2.5-coder:7b · temperatura 0_

| | Sin guía | Con guía |
|---|---|---|
| Errores de versión antigua (total) | **3** | **0** |
| Usos de sintaxis nueva (total) | 0 | 16 |

## Por tarea

### 1. Página HTML completa con Tailwind CSS 4 cargado por CDN en el navegador, con dos colores propios de marca (#F26B21 'marca' y #1D1D1F 'tinta') y la fuente 'Inter' configurados para usarlos como clases.
- **sin guía:** errores: ninguno · nuevo: ninguno
- **con guía:** errores: ninguno · nuevo: @theme ×1, CDN de v4 ×1

### 2. Tarjeta de producto con Tailwind CSS 4: imagen arriba con esquinas pequeñas redondeadas, sombra suave, borde gris claro, título, precio y botón con fondo negro al 80 % de opacidad.
- **sin guía:** errores: ninguno · nuevo: ninguno
- **con guía:** errores: ninguno · nuevo: ninguno

### 3. Hero con Tailwind CSS 4: fondo con degradado de izquierda a derecha de violeta a cian, título grande y un botón que al pasar el ratón muestra un anillo (ring) de 3 px.
- **sin guía:** errores: *-opacity-N (eliminado en v4) ×1, bg-gradient-to-* (ahora bg-linear-to-*) ×1 · nuevo: ninguno
- **con guía:** errores: ninguno · nuevo: @theme ×1, CDN de v4 ×1, bg-linear-to-* ×1, container queries ×1, outline-hidden ×1, ring-3 ×1

### 4. Rejilla de 3 tarjetas con Tailwind CSS 4 que se adapta al ancho del CONTENEDOR (no de la pantalla): 1 columna si el contenedor es estrecho, 3 si es ancho.
- **sin guía:** errores: ninguno · nuevo: ninguno
- **con guía:** errores: ninguno · nuevo: @theme ×1, CDN de v4 ×1, container queries ×1

### 5. Barra de navegación con Tailwind CSS 4: fija arriba, fondo blanco translúcido con desenfoque, un input de búsqueda sin contorno al enfocarlo y un texto que se corta con puntos suspensivos.
- **sin guía:** errores: ninguno · nuevo: ninguno
- **con guía:** errores: ninguno · nuevo: @theme ×1, CDN de v4 ×1

### 6. Modal con Tailwind CSS 4: fondo oscuro semitransparente encima de la página, caja centrada con esquinas redondeadas, y una clase marcada como !important para forzar el z-index.
- **sin guía:** errores: *-opacity-N (eliminado en v4) ×1 · nuevo: ninguno
- **con guía:** errores: ninguno · nuevo: @theme ×1, CDN de v4 ×1, ! al final ×1
