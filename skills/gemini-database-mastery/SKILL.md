---
name: gemini-database-mastery
trigger: model_decision
description: "EstÃ¡ndares de alto rendimiento para bases de datos relacionales y SQL (PostgreSQL, MySQL, SQLite, Neon, Supabase). Exige eliminaciÃ³n del problema N+1, indexaciÃ³n inteligente (B-Tree/GIN), transacciones seguras ACID y migraciones sin tiempo de inactividad (Zero-Downtime)."
---

# Database & SQL Engineering Best Practices

Esta habilidad asegura que cualquier esquema, migraciÃ³n o consulta a base de datos sea eficiente, segura y no genere caÃ­das en producciÃ³n.

---

## 1. DetecciÃ³n y ErradicaciÃ³n del Problema N+1
- **Prohibido:** Ejecutar consultas en bucles (`for`/`map`) para obtener relaciones secundarias.
- **Obligatorio:** 
  - En SQL puro: Usar `JOIN` explÃ­cito o agregaciÃ³n `JSON_AGG()`.
  - En ORMs (Prisma, Drizzle, TypeORM, Hibernate, SQLAlchemy): Usar `include`, `with` o prefetching masivo en una Ãºnica consulta indexada.

---

## 2. IndexaciÃ³n Inteligente (Query Performance)
- **Columnas de filtrado frecuente (`WHERE`, `ORDER BY`, `JOIN`):** Exigir Ã­ndice B-Tree.
- **BÃºsquedas de texto o JSON (`jsonb`):** Usar Ã­ndices GIN o expresiones generadas.
- **PrevenciÃ³n de Full Table Scans:** Prohibido hacer `SELECT *` en tablas de producciÃ³n; seleccionar solo las columnas requeridas.
- **PaginaciÃ³n eficiente:** Preferir paginaciÃ³n por cursor/keyset (`WHERE id > :last_id LIMIT 20`) sobre paginaciones profundas (`OFFSET 100000`).

---

## 3. Migraciones Seguras (Zero-Downtime Migrations)
1. **Columnas NOT NULL:** Nunca aÃ±adir `NOT NULL` directo en tablas con datos existentes. 
   - *Procedimiento seguro:* AÃ±adir columna como nullable $\rightarrow$ popular datos con script de backfill $\rightarrow$ aplicar restricciÃ³n `NOT NULL`.
2. **EliminaciÃ³n de Columnas (`DROP COLUMN`):** No borrar directamente columnas activas para no romper instancias concurrentes; aplicar deprecaciÃ³n en cÃ³digo primero.
3. **CreaciÃ³n de Ãndices:** En bases de datos en producciÃ³n, usar `CREATE INDEX CONCURRENTLY` (PostgreSQL) para evitar bloqueos de tabla.

---

## 4. Integridad y Transacciones
- Todas las operaciones multi-tabla dependientes (ej. cobro + creaciÃ³n de orden) deben estar envueltas en **transacciones atÃ³micas** (`BEGIN ... COMMIT`) con manejo de rollback en caso de fallo.

