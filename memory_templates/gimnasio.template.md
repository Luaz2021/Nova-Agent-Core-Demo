# Gimnasio de Razonamiento, Debate y Antipatrones de la Industria
# Estandar de Calibracion Arquitectonica para Nova Agent
# ==============================================================================

## Parte 1: 20 Preguntas de Alto Nivel para Calibrar Razonamiento y Debate

### Bloque A: Arquitectura & Decisiones de Escala
1. **Monolito Modular vs Microservicios:** ¿En que metrica exacta de negocio o equipo deja de ser rentable un monolito y se justifica pagar la complejidad de red y serializacion de los microservicios?
2. **Serverless Cold Starts:** ¿Cuando una funcion serverless pasa de ahorrar dinero a ser un cuello de botella inaceptable en latencia frente a un contenedor basico persistente?
3. **Sincronia vs Asincronia:** Si un usuario hace clic en 'Confirmar Reserva o Pago', ¿que partes del flujo deben ser estrictamente sincronas y cuales deben delegarse a una cola en segundo plano?
4. **Estrategia Offline-First en Movil:** ¿Como sincronizas datos cuando el usuario recupera internet tras 2 dias sin pisar los cambios concurrentes de otros usuarios?

### Bloque B: Concurrencia, Estado & Bases de Datos
5. **El Problema del Doble Gasto:** Dos usuarios intentan reservar el mismo recurso o pagar el ultimo item al mismo milisegundo. ¿Bloqueo optimista, bloqueo pesimista o atomicidad a nivel de motor SQL?
6. **Normalizacion vs Rendimiento:** ¿Cuando es legitimo desnormalizar una tabla relacional y aceptar el riesgo de inconsistencia para bajar de 150ms a 10ms de consulta?
7. **Soft Deletes vs Hard Deletes:** ¿Por que llenar tablas con banderas `is_deleted = true` puede degradar el rendimiento de los indices B-Tree a largo plazo y como se mitiga con indices parciales?
8. **Indices en Base de Datos:** Si anadir indices acelera las lecturas, ¿cual es el costo oculto en escrituras, fragmentacion y memoria que nadie calcula en produccion?

### Bloque C: Frontend, Rendimiento & Movil
9. **El Costo Real de un Re-render:** ¿Por que memoizar prematuramente con `useMemo` y `useCallback` puede hacer que tu aplicacion sea mas lenta en lugar de mas rapida?
10. **Puente Nativo en Aplicaciones Hibridas:** ¿Que operaciones deben quedarse en el hilo de JavaScript y cuales deben enviarse obligatoriamente al motor nativo para no congelar la UI a 60 FPS?
11. **Gestion de Estado Global:** ¿En que punto Redux o Context pasan de ser utiles a convertirse en una trampa de dependencias circulares y renderizado fantasma?
12. **Precarga y Waterfalls:** Si una pantalla necesita datos de 3 endpoints diferentes, ¿como eliminas la cascada de peticiones sin sobrecargar la memoria del cliente movil?

### Bloque D: Seguridad & Blindaje Real
13. **El Mito de la Seguridad en el Frontend:** Si validas exhaustivamente un formulario en React, ¿por que no has protegido absolutamente nada del sistema si el endpoint carece de validacion defensiva?
14. **JWT vs Sesiones con Cookies HTTP-Only:** ¿Por que guardar tokens de autenticacion en `localStorage` es un regalo para cualquier ataque XSS y como se mitiga con cookies seguras?
15. **Aislamiento Zero-Trust en BaaS:** ¿Como auditas que una politica Row Level Security (RLS) en Postgres sea hermetica y no permita filtracion por inyeccion de cabeceras?
16. **Manejo de Secretos:** ¿Cual es la diferencia critica entre una variable expuesta en compilacion (`NEXT_PUBLIC_` o `EXPO_PUBLIC_`) y una variable de entorno de servidor?

### Bloque E: Filosofia de Ingenieria & Trinchera (KISS vs Deuda)
17. **La Valla de Chesterton:** Si ves una funcion de 80 lineas que parece redundante o fea, ¿por que borrarla o reescribirla a ciegas sin documentar primero su proposito original es el error mas costoso?
18. **Deuda Tecnica Consciente:** ¿Cuando es estrategico tomar deuda tecnica para validar un MVP y cuando se convierte en un riesgo que destruira el producto?
19. **Sobre-Ingenieria Temprana:** ¿Como distingues una abstraccion limpia de un laberinto innecesario de 5 capas de interfaces que nadie pidio?
20. **Automatizaciones vs Codigo Simple:** ¿Por que montar un scraper complejo con navegador headless suele ser una mala decision si existe un endpoint JSON interno o un comando CLI nativo?

---

## Parte 2: Los 10 Antipatrones Forenses de la Industria

1. **El Bucle Infinito del useEffect (React):**
   - *Fallo:* Peticiones HTTP infinitas, navegador congelado y cuotas de API agotadas.
   - *Causa Raiz:* Instanciacion de objetos/arrays literales dentro del array de dependencias.
   - *Solucion:* Derivar estado durante el render o usar cache con deduplicacion (TanStack Query / SWR).

2. **El Problema N+1 en ORMs (Prisma, TypeORM, Hibernate):**
   - *Fallo:* Tiempos de respuesta que escalan de 50ms a 15 segundos al aumentar los registros.
   - *Causa Raiz:* Lazy loading no intencionado que dispara 1 consulta adicional por cada fila iterada.
   - *Solucion:* Eager loading explicito (`include`/`join`) o consultas SQL directas con agregacion JSON.

3. **La Trampa de los Tokens en LocalStorage:**
   - *Fallo:* Robo de credenciales y secuestro de sesion mediante scripts maliciosos de terceros.
   - *Causa Raiz:* Almacenar tokens JWT en almacenamiento local accesible desde JavaScript.
   - *Solucion:* Cookies `httpOnly`, `SameSite=Strict` y `Secure`.

4. **El Desastre del Delete sin Where (y Soft Deletes sin Indices Parciales):**
   - *Fallo:* Borrado accidental de datos o degradacion masiva de lecturas por millones de filas marcadas como borradas.
   - *Solucion:* Transacciones seguras con limite, auditoria y `CREATE INDEX idx_active ON tabla(id) WHERE is_deleted = false`.

5. **Exposicion de Claves Maestras (`service_role_key`):**
   - *Fallo:* Bypass completo de politicas RLS; usuarios anonimos vacian la base de datos.
   - *Solucion:* Validacion de prefijos de variables de entorno y escaneo automatico en CI pre-build.

6. **Desincronizacion en Video Programatico:**
   - *Fallo:* El video avanza mas rapido o mas lento que la voz en off.
   - *Solucion:* Principio Audio-First: extraer timestamps por palabra de la locucion antes de animar.

7. **Bloqueo de Hilo Principal por Serializacion Masiva:**
   - *Fallo:* La aplicacion no responde mientras parsea JSON gigantes de 50 MB.
   - *Solucion:* Streams reactivos y procesamiento en trozos (*chunking*).

8. **Inyeccion de Dependencias Circular:**
   - *Fallo:* Modulos que se llaman mutuamente provocando `undefined` al inicio o fugas de memoria.
   - *Solucion:* Inversion de dependencias y desacoplamiento mediante eventos o interfaces intermedias.

9. **Sobre-Ingenieria de Microservicios para Trafico Bajo:**
   - *Fallo:* 10 repositorios para un proyecto con 500 visitas al dia, pagando costos de latencia y mantenimiento inasumibles.
   - *Solucion:* Monolito modular limpio con arquitectura por capas (KISS estricto).

10. **Parches a Ciegas sin Test Reproducible:**
    - *Fallo:* El programador cambia 3 lineas al azar "a ver si compila", introduciendo 2 bugs nuevos.
    - *Solucion:* Ciclo Rojo-Verde-Refactor: aislar el fallo con un test que falle primero, resolverlo y verificar en verde.
