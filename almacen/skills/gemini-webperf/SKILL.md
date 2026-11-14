---
name: gemini-webperf
description: "Optimizacion de Core Web Vitals (LCP <2.5s, INP <200ms, CLS <0.1), presupuestos de JS (<100KB) y cero waterfalls."
trigger: model_decision
---

# Web Performance & Core Web Vitals Standards

Esta habilidad aplica los estandares de rendimiento web promovidos por Addy Osmani y el equipo de Google Chrome. Establece que el rendimiento no es un añadido final, sino un requisito arquitectonico obligatorio en cada linea de frontend.

---

## 1. Presupuestos de Rendimiento y Core Web Vitals

Toda interfaz web entregada debe cumplir los siguientes umbrales tecnicos:

1. **Largest Contentful Paint (LCP) < 2.5 segundos:**
   - Priorizar la carga del elemento principal visible en el viewport inicial.
   - Pre-cargar fuentes criticas (`rel="preload"`) y usar `fetchpriority="high"` en la imagen del hero si aplica.
2. **Interaction to Next Paint (INP) < 200 milisegundos:**
   - Evitar tareas largas en el hilo principal (Long Tasks > 50ms).
   - Desacoplar calculos pesados del hilo de eventos y diferir ejecuciones no esenciales con `requestIdleCallback` o transiciones concurrentes.
3. **Cumulative Layout Shift (CLS) < 0.1:**
   - Reservar dimensiones explicitas (`width` y `height` o `aspect-ratio`) para imagenes, videos, modales y banners.
   - Prohibido insertar contenido dinamico sobre texto ya renderizado que empuje los elementos visuales hacia abajo.

---

## 2. Presupuesto de Bundle y Cero Waterfalls

1. **Presupuesto de JavaScript Inicial:**
   - Mantener el payload critico de JavaScript por debajo de 100 KB gzippeado en el primer render.
   - Utilizar importaciones dinamicas (`next/dynamic` o `React.lazy`) para componentes pesados no visibles en el primer pantallazo (modales, calendarios, graficos o reproductores).
2. **Eliminacion de Peticiones en Cascada (Waterfalls):**
   - En componentes de servidor y capas de carga de datos, disparar las consultas independientes en paralelo (`Promise.all`) en vez de esperas secuenciales `await` consecutivas.
   ```typescript
   // Incorrecto: Cascada de peticiones secuenciales
   const user = await getUser(id);
   const bookings = await getBookings(id);

   // Correcto: Carga concurrente en paralelo
   const [user, bookings] = await Promise.all([
     getUser(id),
     getBookings(id)
   ]);
   ```

---

## 3. Optimizacion de Multimedia y Recursos

- **Formatos Modernos:** Servir siempre imagenes en formato WebP o AVIF con compresion automatica.
- **Carga Perezosa Inteligente:** Aplicar `loading="lazy"` a todos los elementos fuera de la pantalla inicial, manteniendo `loading="eager"` exclusivamente para el recurso LCP.
- **Fuentes Tipograficas:** Limitar la carga a un maximo de 2 pesos de fuente necesarios (`font-display: swap`) y auto-alojarlas para evitar llamadas a dominios de terceros bloqueantes.

---

## 4. La Valla de Chesterton en Refactorizaciones

Antes de simplificar, eliminar o alterar codigo existente bajo el argumento de optimizar:
- Es obligatorio entender, verificar y documentar por que el codigo original fue colocado de esa forma.
- Si no se puede explicar la razon de una comprobacion o estado previo, no se debe tocar sin antes validarlo con un test unitario o una prueba fantasma.
