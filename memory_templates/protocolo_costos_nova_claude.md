# Protocolo Oficial de Eficiencia y Costos v3.0 (Consenso Nova Argon + Claude)
*Fecha de aprobacion: 2026-10-28 | Estado: ACTIVO*

## 1. Formula Oficial de Costo Ponderado
Cada llamada API `k` dentro de una tarea se contabiliza individualmente:
- **Pesos internos por tipo de token:**
  - `Input_Nuevo`: `1.0x`
  - `Cache_Read`: `0.1x` (se **SUMA** `cache_read_tokens` de todas las llamadas `k=1..N` de la tarea, nunca se usa `max()`).
  - `Output` (incluyendo razonamiento): `6.0x`
- **Factor por Nivel de Modelo (`model_tier`):**
  - `flash` ($0.50 / $0.05 / $3.00): Multiplicador `1.0x`
  - `pro` / `argon` ($2.00 / $0.20 / $12.00): Multiplicador `4.0x`

$$\text{Costo}(N, P_0) = \text{Factor}_{\text{modelo}} \times \sum_{k=1}^{N} \left( \text{in}_k \times 1.0 + \text{cache}_k \times 0.1 + \text{out}_k \times 6.0 \right)$$

---

## 2. Invariante de Cola Dinamica y Costo por Llamada de Herramienta
En Antigravity IDE, los ultimos **~2.052 tokens** de cada request corresponden al sufijo dinamico efimero y no entran en el Prefix Cache:
$$\text{cache\_read\_tokens}_k \approx \text{TotalPrompt}_{k-1} - 2.052$$
$$\text{input\_tokens}_k \approx 2.052 + \Delta_k$$

Por tanto, cada llamada adicional a una herramienta cuesta un fijo de `2.052 + 0.1 * P_0` puntos antes de generar codigo:
1. **Regla 1-Shot Consolidado:** Cuando una tarea requiera crear o modificar `>= 2` archivos y ejecutar pruebas (`unittest` estandar), debe ejecutarse en **un unico paso consolidado** (o llamadas a herramientas en paralelo en el mismo turno) para mantener `N <= 2..3` llamadas API.
2. **Prohibido cambiar de modelo en caliente:** Cambiar entre Flash y Argon en una ventana con historial acumulado invalida el 100% del KV-cache (`cache_read_tokens = 0`). Si se requiere escalar de modelo y la ventana supera los 30k tokens, abrir ventana nueva primero.

---

## 3. Punto Optimo de Salto de Ventana
Abrir ventana nueva tiene un costo inicial de prefill (`cache = 0` en la Llamada 1) igual a `0.9 * P_init`.
Mantenerse en la ventana actual con historial `H` paga `0.1 * H` extra por cada llamada futura `K`:
$$H_{\text{optimo}} > \frac{9 \times P_{\text{init}}}{K}$$
- Con `P_init` en ~29k: saltar entre **100k y 120k tokens** en fronteras de tarea.
- Con `P_init` podado a ~12,3k: saltar a partir de **60k tokens** en fronteras de tarea.

---

## 4. Estado del Patron Jefe-Obrero (Qwen 2.5 Coder 7B Local)
- **Estado actual:** **CONGELADO** para tareas pequenas y medianas (1 a 3 archivos, `< 1.500` tokens de output). Nova Cloud en Modo 2 Consolidado (`1-Shot`) es mas barata y fiable.
- **Condiciones estrictas para reapertura futura:**
  1. Prefijo fijo global podado a `<= 12.500` tokens.
  2. Invocacion exclusivamente mediante el CLI fijo `nova_local_worker.py` en maximo **2 llamadas API** (`Brief` -> `Reporte`).
  3. Tareas con volumen de salida `> 1.500` tokens de codigo repetitivo o lectura/resumen masivo de repositorios locales.
  4. **Puerta de Calidad:** Qwen debe pasar a la primera los tests escritos por la nube en al menos **4 de cada 5 corridas (>= 80% first-pass rate)**.

---

## 5. Nota Critica para el Instalador de Nova Community Edition
- Antigravity IDE inyecta automaticamente en `<user_rules>` los archivos `~/.gemini/config/GEMINI.md` y `~/.gemini/GEMINI.md`, pero **NO inyecta `~/.gemini/antigravity/GEMINI.md`**.
- Todo instalador (Windows/macOS/Linux) debe escribir la regla maestra unicamente en `~/.gemini/config/GEMINI.md` y eliminar `~/.gemini/GEMINI.md` para evitar duplicacion de tokens.
