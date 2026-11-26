# GUÍA DE VERSIÓN · Java 21 / 25 (LTS; la última LTS es Java 25, de septiembre de 2025)

Escribe Java moderno. Lo que aprendiste suele ser Java 8-11: mucho código de relleno que ya sobra.

## 1. Datos y tipos
```java
record Punto(double x, double y) {                  // inmutable: constructor, equals, hashCode y toString incluidos
  Punto { if (x < 0) throw new IllegalArgumentException(); }   // constructor compacto con validación
}
sealed interface Forma permits Circulo, Cuadrado {}
record Circulo(double radio) implements Forma {}
record Cuadrado(double lado) implements Forma {}

var lista = new ArrayList<String>();               // var en variables locales
String json = """
    { "nombre": "Ana", "edad": 30 }
    """;                                            // text blocks
```

## 2. Pattern matching (sustituye cadenas de instanceof y casts)
```java
double area(Forma f) {
  return switch (f) {                               // switch como expresión, exhaustivo con sealed
    case Circulo(var r) -> Math.PI * r * r;         // record patterns
    case Cuadrado(var l) when l > 100 -> -1;        // guardas con when
    case Cuadrado(var l) -> l * l;
  };
}
if (obj instanceof String s && !s.isBlank()) { System.out.println(s.length()); }
String tipo = switch (dia) { case SABADO, DOMINGO -> "finde"; default -> "laborable"; };
try { ... } catch (IOException _) { ... }          // variable sin nombre con _ (Java 22+)
```

## 3. Concurrencia: hilos virtuales
```java
try (var ex = Executors.newVirtualThreadPerTaskExecutor()) {     // un hilo virtual por tarea: miles sin problema
  List<Future<String>> fs = urls.stream().map(u -> ex.submit(() -> descargar(u))).toList();
  for (var f : fs) System.out.println(f.get());
}
Thread.ofVirtual().start(() -> trabajar());
```
- Para E/S (red, base de datos) usa hilos virtuales en vez de grandes pools o código reactivo complicado.
- `ScopedValue` (final en Java 25) en vez de `ThreadLocal` para pasar contexto.

## 4. Colecciones y streams
```java
var nums = List.of(3, 1, 2);                        // inmutable (no Arrays.asList ni new ArrayList + add)
var mapa = Map.of("a", 1, "b", 2);
nums.getFirst(); nums.getLast(); nums.reversed();   // colecciones secuenciadas (21)
var pares = nums.stream().filter(n -> n % 2 == 0).toList();     // toList() directo
// Gatherers (24): operaciones intermedias propias, p. ej. ventanas
nums.stream().gather(Gatherers.windowFixed(2)).toList();
```
Cliente HTTP de serie: `HttpClient.newHttpClient().send(HttpRequest.newBuilder(URI.create(url)).build(), BodyHandlers.ofString())`.

## 5. Java 25: programas pequeños sin ceremonia
```java
// Archivo Hola.java, se ejecuta con: java Hola.java   (sin compilar aparte)
void main() {
  String nombre = IO.readln("¿Nombre? ");
  IO.println("Hola, " + nombre);
}
```
- `import module java.base;` importa todo un módulo de golpe.
- Constructores flexibles: se puede validar ANTES de `super(...)`.

## 6. Errores típicos de un modelo con Java viejo
1. Clases POJO con getters, setters, `equals` y `hashCode` a mano → `record`.
2. Cadenas `if (x instanceof A) { A a = (A) x; ... }` → patrones y `switch`.
3. `switch` con `case:` y `break` → `case ->` como expresión.
4. `Date`, `Calendar`, `SimpleDateFormat` → `java.time` (`LocalDate`, `Instant`, `DateTimeFormatter`).
5. `collect(Collectors.toList())` → `toList()`.
6. `Vector`, `Hashtable`, `StringBuffer` → `ArrayList`, `HashMap`, `StringBuilder`.
7. Pools de hilos enormes para E/S → hilos virtuales.
8. `public static void main(String[] args)` obligatorio en scripts de prueba (Java 25 ya no lo exige).
