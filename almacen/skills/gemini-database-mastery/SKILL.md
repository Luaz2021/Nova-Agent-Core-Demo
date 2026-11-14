---
name: gemini-database-mastery
description: "Estandares SQL de alto rendimiento (Postgres, MySQL, Supabase): cero N+1, indices B-Tree/GIN, ACID y zero-downtime."
trigger: model_decision
---

# Database & SQL Engineering Best Practices

Esta habilidad asegura que cualquier esquema, migración o consulta a base de datos sea eficiente, segura y no genere caídas en producción.

---

## 1. Detección y Erradicación del Problema N+1
- **Prohibido:** Ejecutar consultas en bucles (`for`/`map`) para obtener relaciones secundarias.
- **Obligatorio:** 
  - En SQL puro: Usar `JOIN` explícito o agregación `JSON_AGG()`.
  - En ORMs (Prisma, Drizzle, TypeORM, Hibernate, SQLAlchemy): Usar `include`, `with` o prefetching masivo en una única consulta indexada.

---

## 2. Indexación Inteligente (Query Performance)
- **Columnas de filtrado frecuente (`WHERE`, `ORDER BY`, `JOIN`):** Exigir índice B-Tree.
- **Búsquedas de texto o JSON (`jsonb`):** Usar índices GIN o expresiones generadas.
- **Prevención de Full Table Scans:** Prohibido hacer `SELECT *` en tablas de producción; seleccionar solo las columnas requeridas.
- **Paginación eficiente:** Preferir paginación por cursor/keyset (`WHERE id > :last_id LIMIT 20`) sobre paginaciones profundas (`OFFSET 100000`).

---

## 3. Migraciones Seguras (Zero-Downtime Migrations)
1. **Columnas NOT NULL:** Nunca añadir `NOT NULL` directo en tablas con datos existentes. 
   - *Procedimiento seguro:* Añadir columna como nullable $\rightarrow$ popular datos con script de backfill $\rightarrow$ aplicar restricción `NOT NULL`.
2. **Eliminación de Columnas (`DROP COLUMN`):** No borrar directamente columnas activas para no romper instancias concurrentes; aplicar deprecación en código primero.
3. **Creación de Índices:** En bases de datos en producción, usar `CREATE INDEX CONCURRENTLY` (PostgreSQL) para evitar bloqueos de tabla.

---

## 4. Integridad y Transacciones
- Todas las operaciones multi-tabla dependientes (ej. cobro + creación de orden) deben estar envueltas en **transacciones atómicas** (`BEGIN ... COMMIT`) con manejo de rollback en caso de fallo.

