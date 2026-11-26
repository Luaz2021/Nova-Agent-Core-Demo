# CARRIL BACKEND / BASE DE DATOS (kit corto: léelo entero, ~1,5k tokens)

Activo cuando el usuario trae SQL, una BD, DAO/repositorios, JDBC/JPA, una API o un CRUD. Resume las skills de
`index-backend-db`: si necesitas más detalle, abre SOLO la del apartado "Profundizar" que toque.

## 1. Antes de tocar nada (radiografía rápida, 1-3 llamadas)
- Mira la estructura: `pom.xml` / `build.gradle` / `requirements.txt` / `package.json`, versión de Java/Python, qué BD (MySQL, PostgreSQL, SQLite, Oracle) y cómo conecta.
- Si te piden "mira este script/proyecto": responde primero QUÉ HACE, luego RIESGOS y luego MEJORAS por orden de impacto. No reescribas el archivo entero: cambios por fragmentos (`edit_file` <= 35 %).

## 1b. Proyecto grande, rama o legacy: RADIOGRAFÍA primero, no leas archivo por archivo
- El usuario trae un proyecto/rama/código viejo ("desglósalo", "cómo está montado", "¿se puede refactorizar/trocear?"): lanza
  `<PYTHON> "<NOVA_HOME>/antigravity/herramientas/codebase_memory/radiografia.py" analizar "<carpeta>"`
  (local, 1-3 min; no hace falta encender el MCP ni reabrir Antigravity). Lee SOLO el `RADIOGRAFIA.md` que deja en
  `documentos_generados/radiografias/`: piezas, mapa de dependencias, ciclos, puntos frágiles, funciones monstruo,
  duplicados, código muerto y plan para trocear. Donde ponga `[NOVA: explícalo…]` explica TÚ qué hace la pieza con su
  ficha (archivos, funciones, comentarios), sin abrir el código. Resúmeselo al usuario y pregunta por dónde empezar.
  (`--explicar` = que lo haga Qwen local: lento, solo si el usuario lo pide.)
- ANTES de cambiar una función que otros usan: `radiografia.py impacto <proyecto> <funcion>` (quién la llama y riesgo).
  Así sabes el trozo exacto que tocar: `edit_file` sobre esa función, nunca reescribir el archivo.
- Después de editar (con git): `radiografia.py cambios <proyecto>`. Mapa visual: `radiografia.py mapa` (127.0.0.1:9749,
  se cierra solo; `mapa --cerrar`). Copias viejas dentro del proyecto: `--excluir backup,archivo`.
- Con el MCP `codebase` encendido: `index_repository` -> `get_architecture` / `trace_path` / `search_graph` /
  `get_code_snippet` (150-400 tokens por consulta). Lee archivos enteros solo para EDITARLOS.

## 2. Arquitectura (la de clase, sin inventos)
- Capas: `modelo/entidad` -> `DAO/Repository` (SOLO SQL) -> `Service` (reglas de negocio) -> `Controller/Menu` (entrada/salida). Cero SQL en el controlador o en el menú.
- Una clase de conexión (`ConexionBD`/`Database`) con los datos en `.properties` / `.env` FUERA de git. Nunca contraseñas en el código.
- Métodos cortos, early return, nombres claros. Excepción propia (`DAOException`) en vez de lanzar `SQLException` hacia arriba.

## 3. SQL y JDBC: las 8 reglas que más fallan
1. **Siempre `PreparedStatement`** con `?`. Concatenar valores en SQL = inyección SQL. Prohibido.
2. **try-with-resources** para `Connection`, `PreparedStatement` y `ResultSet` (se cierran solos).
3. **Transacción** cuando una operación toca varias tablas o varias filas que deben ir juntas: `setAutoCommit(false)` -> `commit()` / `rollback()` en el `catch`.
4. Claves foráneas con índice; `LEFT JOIN` si la relación puede ser nula; nada de N+1 (un `SELECT` por fila dentro de un bucle): usa `JOIN`.
5. Alias que no sean palabras reservadas (`mod`, `order`, `user` rompen en MySQL).
6. Fechas: `java.time` (`LocalDate`, `LocalDateTime`); zona horaria explícita si hay hora de negocio.
7. Valida en el back aunque ya valide el front (mismas reglas en los dos).
8. Cambios de esquema en producción: expand-contract (añadir columna nullable -> rellenar -> cambiar lecturas -> borrar después).

## 4. Python / Node (si el backend no es Java)
- Python: `sqlite3`/driver con parámetros (`?` o `%s`), nunca f-strings en SQL; `with` para la conexión; FastAPI con Pydantic v2.
- Entorno: proyecto en una carpeta sincronizada (Google Drive, OneDrive, iCloud) -> `uv run --with-requirements requirements.txt <comando>` (NUNCA un `.venv` dentro de Drive: tarda minutos). Fuera de Drive, su `.venv`. Nunca pip en `NOVA_PYTHON`.
- Claves de firma (JWT, sesiones): de una variable de entorno y, si falta, ERROR al arrancar. Nunca un valor por defecto en el código (`os.environ.get("X", "dev-secret")` = cualquiera falsifica tokens). Dinero: `Decimal` y guardado como texto/entero de céntimos, nunca REAL/float.
- Node: consultas parametrizadas (`$1`), librerías declaradas en `package.json` antes de usarlas.

## 5. Definición de hecho (el verificador)
- Compila / arranca: Java `mvn -q compile` (o `javac`); Python `<PYTHON> -m py_compile <archivo>`.
- Cada operación tocada probada con un caso correcto y uno de error (dato inválido, id que no existe).
- Si hay tests: `mvn test` / `<PYTHON> -m pytest` (o `-m unittest`).
- Busca inyección antes de entregar: ninguna consulta con `+` o f-string metiendo valores.

## 6. Escalar (pirámide)
- Diseño de un esquema grande, migración de datos o un fallo que se repite dos veces -> consulta al asesor (o ventana Carbon/Neon si el usuario lo pide).

## Profundizar (solo si hace falta, 1 skill)
`almacen/skills/gemini-clean-architecture/SKILL.md` · `gemini-database-mastery` · `database-migrations` · `api-design` · `backend-patterns` · `fastapi-patterns` · `gemini-supabase-security`

<!-- ERRORES_YA_COMETIDOS:INICIO -->
## Errores que ya cometiste (no los repitas)
_Lo genera `nova_aprendido.py kits` desde `memory/aprendido.jsonl` (tus propios errores): no lo edites a mano. Aun no hay ninguno._
<!-- ERRORES_YA_COMETIDOS:FIN -->
