# Servilleta de Fallos Tecnicos & Runbook Maestro (Napkin Template)
# Formato: [Contexto] -> [Causa Raiz] -> [Hacer en su lugar]
# ==============================================================================

## 1. Bases de Datos & Backend (PostgreSQL, Supabase, Concurrencia)

1. **Degradacion de Latencia por Politicas RLS con Subconsultas No Optimizadas**
   - **Contexto:** Tablas con mas de 50.000 filas en PostgreSQL/Supabase donde una consulta basica pasa de 2ms a 10s.
   - **Causa Raiz:** Escribir politicas RLS con funciones volatiles directas o subconsultas no indexadas (ej. `user_id = auth.uid()`), obligando al planificador a evaluar fila por fila en escaneo secuencial.
   - **Hacer en su lugar:** (1) Indexar todas las columnas del filtro (`CREATE INDEX`), (2) envolver en `(SELECT auth.uid()) = user_id` para forzar `initPlan` que se evalua una unica vez por consulta, y (3) encapsular comprobaciones de membresia en funciones `SECURITY DEFINER` con `SET search_path = ''`.

2. **Doble Reserva y Race Conditions en Transacciones de Citas o Dinero (Cal.com / E-Commerce)**
   - **Contexto:** Dos usuarios intentan reservar el mismo slot de tiempo o comprar el ultimo stock simultaneamente.
   - **Causa Raiz:** Comprobar disponibilidad con un `SELECT` simple y luego hacer un `INSERT`/`UPDATE` sin bloqueo. Entre el select y el insert ocurre una condicion de carrera.
   - **Hacer en su lugar:** Usar transacciones atomicas con bloqueo pesimista `SELECT ... FOR UPDATE` o restricciones de exclusion nativas en Postgres (`EXCLUDE USING gist`) para que el motor SQL rechace matematicamente solapamientos a nivel de storage.

3. **Agotamiento del Pool de Conexiones en Arquitecturas Serverless (Supavisor / PgBouncer)**
   - **Contexto:** Lambdas o Server Actions en Next.js saturan `max_connections` y devuelven 503.
   - **Causa Raiz:** Conectarse directamente a Postgres o configurar el pooler en modo sesion.
   - **Hacer en su lugar:** Configurar el pooler en modo transaccion (`pool_mode = transaction`) y garantizar la inyeccion de claims de JWT usando `SET LOCAL` o transacciones explicitas para no perder el contexto de usuario.

---

## 2. Frontend, UI & Estado React (Zustand, React 19, Waterfalls)

1. **Fugas de Memoria en Estado Global fuera de Componentes (Zustand / Event Listeners)**
   - **Contexto:** Servicios en background o utilitarios que se suscriben al store de estado.
   - **Causa Raiz:** Ejecutar `store.subscribe(...)` sin capturar y disparar la funcion de desuscripcion en el ciclo de destruccion o desmontaje.
   - **Hacer en su lugar:** Siempre almacenar la funcion de retorno (`const unsub = store.subscribe(...)`) y ejecutar `unsub()` en hooks de limpieza (`useEffect` return) o al desmontar el servicio.

2. **Cascadas de Peticiones Asincronas (Waterfalls)**
   - **Contexto:** Una pantalla tarda segundos en cargar porque espera el endpoint A para luego pedir el B y luego el C.
   - **Causa Raiz:** Encadenar `await` secuenciales en Server Components o cliente para datos que no dependen entre si.
   - **Hacer en su lugar:** Ejecutar en paralelo con `Promise.all([fetchA(), fetchB(), fetchC()])` o reestructurar hacia Server Actions con streaming y Suspense.

---

## 3. Video Programatico & Redes Sociales (TikTok, Reels, Shorts)

1. **Desincronizacion Audio-Visual por Asumir Duraciones a Ojo**
   - **Contexto:** La animacion termina antes de que la voz en off termine de hablar, o los subtitulos se solapan con la siguiente escena.
   - **Causa Raiz:** Programar duraciones en segundos en el codigo visual antes de tener el audio locutado.
   - **Hacer en su lugar:** **Principio Audio-First**. Generar el audio primero con timestamps por palabra (`word-level timestamps`) y vincular la timeline visual (`seek(t)`) estrictamente a los tiempos del locutor.

2. **Subtitulos Cortados o Tapados por Botones de la App (Safe Zones)**
   - **Contexto:** El texto del video queda oculto detras del nombre de usuario, la descripcion o los botones de Like y Compartir.
   - **Causa Raiz:** Centrar el texto en coordenadas absolutas sin respetar los margenes de la interfaz de la red social.
   - **Hacer en su lugar:** Respetar la caja segura vertical 9:16: dejar libres `108px` arriba, `320px` abajo y `120px` a la derecha. Renderizar subtitulos siempre como elementos en el DOM para validar sus limites con `getBoundingClientRect()`.

---

## 4. Entorno, Infraestructura & Comandos CLI

1. **Comandos Node/Python con Comillas Escapadas Complejas en Windows PowerShell**
   - **Contexto:** Comandos inline con JSON que fallan por parsing de comillas en terminal.
   - **Causa Raiz:** Diferencias en el lexer de PowerShell frente a Bash en comillas dobles anidadas.
   - **Hacer en su lugar:** Escribir un micro-script temporal `.js` o `.py` y ejecutarlo directamente con `node script.js` o `python script.py`.

2. **Exposicion Accidental de la `service_role_key` en Compilacion Frontend**
   - **Contexto:** Claves maestras de administracion visibles en el bundle `.next/static` o `dist`.
   - **Causa Raiz:** Usar prefijos publicos (`NEXT_PUBLIC_` o `EXPO_PUBLIC_`) o importar modulos de administracion del servidor en componentes cliente.
   - **Hacer en su lugar:** Crear clientes aislados (`supabaseAdmin`) exclusivamente en rutas de backend/Server Actions, y agregar escaneo CI pre-build para bloquear cadenas `eyJ...` con rol de superusuario.
