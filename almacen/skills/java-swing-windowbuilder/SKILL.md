---
name: java-swing-windowbuilder
description: "Java Swing con Eclipse WindowBuilder: editar ventanas (JFrame/JPanel) sin romper la vista Design, MVC sencillo (vista / controller / conexion), JTable con DefaultTableModel. Usar con proyectos Swing de Eclipse (practicas de clase)."
---

# Java Swing + WindowBuilder

Fuentes: ayuda oficial de WindowBuilder (FAQ, edicion bidireccional, preferencias de parsing) en help.eclipse.org y
el jar de WindowBuilder 1.25 (etiquetas de ocultar codigo). Lo de las secciones 3-4 se comprobo en un proyecto
real de practicas de clase (24/11/2026).

## 0. Antes de tocar nada
- Si es una practica (`practica_*`, `practicas_*`, `entregable_*`): explica y propone; el usuario escribe (hook). Con
  "hazlo tu": solo el trozo necesario, con `edit_file`.
- Nivel del curso: el codigo que genera WindowBuilder es largo y "antiguo" (clases anonimas, `setBounds`). Es lo
  normal: NO lo reescribas a lambdas, streams ni layouts nuevos si no te lo piden.

## 1. Lo que WindowBuilder entiende (no romper la vista Design)
- Los componentes se crean en el **constructor** o en un metodo llamado desde el (`initialize()`, `createComponents()`).
  Las piezas nuevas van AHI, con el mismo estilo que las que ya existen.
- Un componente que se usa en otros metodos tiene que ser **campo** de la clase (en WindowBuilder: "Convert local to
  field"). Si es variable local del constructor, `cargarTabla()` no lo ve.
- Editar a mano esta permitido: WindowBuilder vuelve a leer el codigo (edicion bidireccional) y respeta el formato.

## 2. Lo que rompe la vista Design ("parse error" o la ventana sale vacia)
- Construir la interfaz con datos de ejecucion: bucles con limites de fuera, `if` que solo se saben al ejecutar,
  componentes creados segun lo que devuelve la BD.
- Dos variables (campos o locales) apuntando al mismo componente.
- Reutilizar el MISMO objeto `GridBagConstraints` para varios componentes.
- Construir la UI con metodos auxiliares que reciben parametros.
- Logica larga dentro del constructor/`initialize()`.
**Arreglo**: la logica va en metodos aparte (`cargarTabla()`, `guardar()`...) llamados desde los listeners o desde un
constructor secundario. Si hace falta dejar codigo dinamico dentro, se esconde al parser con sus etiquetas:
```java
//$hide>>$
for (String nombre : nombres) { combo.addItem(nombre); }   // el parser no lo ve
//$hide<<$
panel.setBorder(miBordeRaro()); //$hide$   (una sola linea)
```
(Son las etiquetas por defecto de WindowBuilder 1.25; se pueden cambiar en Window > Preferences > WindowBuilder >
Code Parsing: si el proyecto usa otras, usar esas.)
- Componente propio en la paleta: clase publica que hereda de `JComponent`/`JPanel` con constructor publico SIN
  argumentos; lo que solo debe pasar al ejecutar, dentro de `if (!java.beans.Beans.isDesignTime()) { ... }`.

## 3. MVC sencillo (lo que espera el profe y es KISS)
```
src/main/java/
  db/          Conexion.java        -> abre la conexion (una sola clase)
  controller/  XController.java     -> SQL y logica; devuelve datos (List<Object[]>, boolean...). NO importa javax.swing
  view/        ventana_x.java       -> WindowBuilder; lee campos, llama al controller, pinta. NO importa java.sql
```
- En los listeners solo una llamada: `btnGuardar.addActionListener(e -> guardar());` (o la anonima que genera WB).
- La validacion para mostrar mensajes (`JOptionPane`) en la vista; la regla de negocio en el controller.

## 4. JTable (lo que mas se lia)
- La tabla va DENTRO de un `JScrollPane` con `scroll.setViewportView(tabla)`. **`setColumnHeaderView(tabla)` es un
  error** (mete la tabla en la cabecera y no se ven filas): pasa al soltarla en el borde de arriba del scroll.
- Modelo: `DefaultTableModel` con columnas y `isCellEditable` a `false` si es solo lectura.
- Cargar: 
```java
private void cargarTabla() {
    DefaultTableModel modelo = (DefaultTableModel) tabla.getModel();
    modelo.setRowCount(0);                                  // vaciar: si no, se duplican filas
    controller.listar(id).forEach(modelo::addRow);          // el controller devuelve List<Object[]>
}
```
- Columna ID oculta: `tabla.removeColumn(tabla.getColumnModel().getColumn(0));` y leer con
  `tabla.getModel().getValueAt(fila, 0)` (el MODELO cuenta todas las columnas; `tabla.getValueAt` solo las visibles).
- Fila seleccionada: `tabla.getSelectionModel().addListSelectionListener(e -> { if (!e.getValueIsAdjusting()) ... })`
  (funciona con raton y teclado; `mouseClicked` no ve las flechas).

## 5. Errores tipicos
- "Parsing error" / Design vacio: mirar `<workspace>/.metadata/.log`, Project > Clean, y quitar del constructor lo del
  punto 2. No hay pestana Design: el archivo esta abierto con el Java Editor; reabrir con "WindowBuilder Editor".
- La ventana no aparece: falta `setVisible(true)` o no se lanza con `EventQueue.invokeLater(...)`.
- Componentes descolocados al cambiar de tamano: `setLayout(null)` (absoluto). Para practicas vale; si piden que se
  adapte: BorderLayout + paneles, o GridBagLayout.

## Definicion de hecho
- Compila, la pestana Design sigue abriendo, la ventana funciona (cargar, seleccionar, guardar) y el cambio es el
  minimo pedido, en el estilo del proyecto.
