---
name: estructura-proyectos
description: "Como estructurar un proyecto KISS segun su tipo y tamano (Java consola, Java Swing MVC, Java+JDBC, Android XML, Spring Boot, web) y como arreglar sin romper: AGENTS.md del proyecto, cambio minimo, contrato de lo que no cambia. Usar al crear un proyecto, reorganizarlo o antes de arreglar codigo existente."
---

# Estructura de proyectos (KISS, como lo hacen los profesionales)

El usuario es anti codigo espagueti y usa KISS: **la estructura justa para el tamano del proyecto**, ni mas ni menos.
Capas y modulos se anaden cuando el proyecto crece, no "por si acaso" (lo mismo recomienda la guia de arquitectura de
Android: modulos solo cuando la app crece).

## 1. Antes de crear o mover nada
- Proyecto que YA existe: **respeta su estructura**. Solo se reorganiza si el usuario lo pide.
- Practica de clase (`practica_*`, `entregable_*`): la estructura la marca el enunciado / el profe. Propon, no impongas.
- Lee el `AGENTS.md` de la raiz del proyecto si existe (punto 4).

## 2. Plantillas por tipo (empezar por la mas pequena que sirva)
**Java consola (ejercicio):** `src/Main.java` + 1-2 clases. Paquetes solo si hay mas de ~5 clases.

**Java Swing MVC (Eclipse/WindowBuilder):**
```
src/main/java/
  db/Conexion.java            conexion
  controller/XController.java SQL + logica (sin javax.swing)
  model/X.java                solo si hace falta un objeto (p. ej. Usuario)
  view/ventana_x.java         WindowBuilder (sin java.sql)
```
**Java + JDBC sin interfaz:** `db/`, `dao/` (o `controller/`), `model/`, `Main.java`.

**Android con XML:** ver `android-views-xml` (Activities en el paquete raiz; `ui/`, `data/`, `util/` solo al crecer).

**Spring Boot:** `controller/`, `service/`, `repository/`, `dto/`, `entity/` (ver `spring-layered-architecture`).
Por funcionalidad (`usuarios/`, `pedidos/` con sus capas dentro) cuando hay varias areas grandes.

**Web estatica:** `index.html`, `css/`, `js/`, `img/` (o la estructura del estudio web).

Reglas comunes: un archivo = una responsabilidad; nombres que dicen lo que hacen; sin carpetas vacias "para el
futuro"; recursos (textos, colores, config) fuera del codigo.

## 3. Arreglar sin romper (codigo existente / "legacy")
1. **Localiza** el trozo danado (lee solo lo necesario: buscar, leer rango de lineas).
2. **Contrato**: escribe en 1-3 lineas que NO debe cambiar (comportamiento, nombres publicos, ids del XML, firmas
   que usa la vista...). Si hay tests o se puede probar a mano, comprueba antes como funciona.
3. **Cambio minimo** con `edit_file` sobre ese trozo. Nunca reescribir el archivo entero para cambiar unas lineas
   (el hook lo mide). Nada de "ya que estoy, lo modernizo".
4. **Verifica**: compila / ejecuta / prueba lo del contrato. Si algo mas se rompio, se arregla ANTES de decir listo.
5. Si el arreglo bueno exige reestructurar: **pregunta** al usuario con el porque, no lo hagas por tu cuenta.

## 4. AGENTS.md del proyecto (el estandar de la industria)
Archivo corto (< 40 lineas) en la raiz del proyecto, que lee cualquier agente. Proponlo al usuario si no existe;
no lo crees sin su visto bueno en practicas. Contenido practico, no filosofia:
```markdown
# <Proyecto>
## Que es
Una linea (p. ej. "Practica DAM: gestion de notas con Swing + MySQL").
## Como se ejecuta / compila
- Eclipse: Run sobre view/login_general.java   (o: gradlew assembleDebug / mvn spring-boot:run)
- BD: MySQL local, base notas_ue (script en sql/)
## Estructura
- db/ conexion · controller/ SQL y logica · view/ ventanas WindowBuilder
## Reglas
- La vista no importa java.sql; el controller no importa javax.swing.
- Cambios minimos; no modernizar el estilo del curso.
## No tocar
- (archivos generados, plantillas del profe, etc.)
```

## Definicion de hecho
- La estructura cabe en una frase, cada archivo tiene un sitio obvio, compila, y el cambio fue el minimo.
