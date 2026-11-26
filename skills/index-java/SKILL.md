---
name: index-java
description: "Indice Macro Java (DAM): Java consola, Swing con Eclipse WindowBuilder, JDBC clasico con MySQL, Spring Boot y estructura de proyectos KISS. Leer antes de crear o modificar codigo Java."
---

# Index 09 · Java (1-Hop Router)

## 1. Reglas operativas
- **Practicas** (`practica_*`, `practicas_*`, `entregable_*`): explica y propone, el usuario escribe (lo frena un hook).
  Con "hazlo tu": solo el trozo necesario con `edit_file`.
- **Nivel del curso y estilo del proyecto**: si el proyecto usa clases anonimas, bucles clasicos o `setBounds`, se
  sigue asi. Nada de streams, records, Spring o "modernizar" si no lo usa o no lo pide el usuario (esto manda sobre
  REGLAS_KISS en proyectos de clase).
- **Estructura**: la del proyecto; si es nuevo, la plantilla mas pequena de `estructura-proyectos`.
- **Arreglar**: localizar -> contrato de lo que no cambia -> cambio minimo -> verificar (ver `estructura-proyectos`).

## 2. Mapa de salto al almacen (`<NOVA_HOME>/antigravity/almacen/skills/<nombre>\SKILL.md`)
- **Ventanas Swing / WindowBuilder / JTable**: `java-swing-windowbuilder`
- **Base de datos con JDBC (MySQL, PreparedStatement, controller/DAO)**: `java-jdbc-clasico`
- **Estructura del proyecto, AGENTS.md, arreglar sin romper**: `estructura-proyectos`
- **Spring Boot 3** (solo si el proyecto es Spring): `spring-boot-scaffolding` (crear), `spring-layered-architecture`
  (capas), `spring-rest-api-conventions` (API REST), `spring-data-jpa` (entidades y repositorios). En ingles,
  copiadas del repo MIT rrezartprebreza/spring-boot-skills (ver su FUENTE.md).
- **Consola / ejercicios con Scanner**: kit del carril consola (`herramientas/carriles/carril_consola.md`).

## Trampas ya vistas
- JTable sin filas: tabla en `setColumnHeaderView` en vez de `setViewportView`.
- Columna oculta: leer con `tabla.getModel().getValueAt`, no `tabla.getValueAt`.
- Conexion compartida dentro de `try (...)`: se cierra para todos ("ResultSet closed").
- Tabla vacia sin error: el `WHERE` no coincide con los datos reales (mayusculas, espacios).

## Definicion de hecho
- Compila, se probo lo que se cambio (y la pestana Design de WindowBuilder sigue abriendo), cambio minimo.
