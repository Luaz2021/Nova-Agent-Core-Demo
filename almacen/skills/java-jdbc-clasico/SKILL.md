---
name: java-jdbc-clasico
description: "JDBC clasico (sin Spring): conexion con DriverManager, PreparedStatement, ResultSet, try-with-resources, controller/DAO, transacciones y errores tipicos con MySQL. Usar en practicas de clase con base de datos (Swing o consola)."
---

# JDBC clasico (MySQL / MariaDB / SQL Server)

## 0. Antes de tocar nada
- Mira como lo hace YA el proyecto (y el profe): una clase de conexion, controller o DAO. Sigue ese patron; no metas
  Spring, JPA ni pools si no los usa. Practicas (`practica_*`, `entregable_*`): explica y propone; el usuario escribe.
- El driver tiene que estar en el proyecto (Maven: `com.mysql:mysql-connector-j`; si no, el .jar en el Build Path).
  "No suitable driver found" = falta el driver o la URL esta mal.

## 1. Conexion
```java
public final class Conexion {
    private static final String URL = "jdbc:mysql://localhost:3306/mi_bd";
    private static final String USER = "root";
    private static final String PASSWORD = "";
    private static Connection conexion;
    private Conexion() {}
    public static Connection conectar() throws SQLException {
        if (conexion == null || conexion.isClosed()) {
            conexion = DriverManager.getConnection(URL, USER, PASSWORD);
        }
        return conexion;
    }
}
```
- **Dos estilos validos; NO mezclarlos**:
  - Conexion compartida (como arriba): la conexion NO va dentro del `try (...)` (se cerraria para todos); solo
    `PreparedStatement` y `ResultSet`.
  - Conexion por operacion: `try (Connection c = DriverManager.getConnection(...); PreparedStatement ps = ...)`.
- Contrasenas: en practicas locales van en la clase; nunca subir claves reales a GitHub.

## 2. Consultas: siempre PreparedStatement
```java
String sql = "SELECT id, nombre FROM usuarios WHERE rol = ?";
try (PreparedStatement ps = Conexion.conectar().prepareStatement(sql)) {
    ps.setString(1, rol);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            filas.add(new Object[] { rs.getInt("id"), rs.getString("nombre") });
        }
    }
}
```
- Nunca concatenar lo que escribe el usuario en el SQL (inyeccion SQL). Los `?` empiezan en 1.
- `executeQuery()` para SELECT; `executeUpdate()` para INSERT/UPDATE/DELETE (devuelve filas afectadas: `> 0` = ok).
- Id generado: `prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)` y `ps.getGeneratedKeys()`.
- UPDATE y DELETE siempre con `WHERE` (el hook frena SQL sin WHERE).

## 3. Donde va el SQL
- En el **controller** (estilo de clase) o en un **DAO** (`UsuarioDAO.insertar/listar/...`). La vista nunca importa
  `java.sql`; el controller/DAO nunca importa `javax.swing`.
- Devolver datos simples a la vista: `List<Object[]>` para una JTable, `boolean` para "se guardo", un objeto modelo
  (`Usuario`) si el proyecto los usa. Las excepciones SQL se registran (`e.printStackTrace()` o log) y se devuelve un
  valor que la vista pueda mostrar.

## 4. Transacciones (varias operaciones que van juntas)
```java
Connection c = Conexion.conectar();
c.setAutoCommit(false);
try { /* ps1.executeUpdate(); ps2.executeUpdate(); */ c.commit(); }
catch (SQLException e) { c.rollback(); throw e; }
finally { c.setAutoCommit(true); }
```

## 5. Errores tipicos
- `Communications link failure`: MySQL apagado (XAMPP/servicio) o puerto distinto.
- `Access denied for user`: usuario/contrasena.
- `Unknown database` / `Table doesn't exist`: nombre de BD o tabla (mayusculas en Linux).
- `Column 'x' not found`: el alias del SELECT no coincide con `rs.getX("x")`.
- `Operation not allowed after ResultSet closed`: se cerro la conexion compartida dentro de un try-with-resources.
- La tabla sale vacia sin error: el filtro (`WHERE rol = 'alumno'`) no coincide con lo que hay en la BD (mayusculas,
  espacios). Probar la consulta en el cliente de MySQL primero.

## Definicion de hecho
- La consulta funciona en el cliente de BD, el metodo devuelve lo esperado, recursos cerrados, sin SQL concatenado y
  el cambio es el minimo pedido.
