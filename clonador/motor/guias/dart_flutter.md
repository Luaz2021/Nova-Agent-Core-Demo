# GUÍA DE VERSIÓN · Dart 3 (actual: 3.12) + Flutter (actual: 3.44)

Escribe Dart 3 y Flutter actual. Lo que aprendiste suele ser Dart 2 y Flutter 2-3.10: falta mucha sintaxis nueva y varias APIs se renombraron.

## 1. Dart 3: sintaxis que debes usar
```dart
// Records (varios valores sin crear clase)
(String, int) persona() => ('Ana', 30);
final (nombre, edad) = persona();
({double lat, double lng}) punto = (lat: 40.4, lng: -3.7);

// Patterns + switch como expresión
String describir(Object o) => switch (o) {
  int n when n < 0 => 'negativo',
  int() => 'entero',
  String s => 'texto de ${s.length}',
  [var a, var b] => 'lista de dos: $a, $b',
  {'tipo': 'user', 'id': int id} => 'usuario $id',
  _ => 'otra cosa',
};
if (json case {'nombre': String n, 'edad': int e}) { print('$n $e'); }

// sealed: el compilador comprueba que cubres todos los casos
sealed class Estado {}
class Cargando extends Estado {}
class Listo extends Estado { final List<String> datos; Listo(this.datos); }
class Fallo extends Estado { final String error; Fallo(this.error); }
Widget pintar(Estado e) => switch (e) { Cargando() => const CircularProgressIndicator(), Listo(:final datos) => Lista(datos), Fallo(:final error) => Text(error) };

// Modificadores de clase: final, base, interface, sealed, mixin class
// Elementos null-aware en colecciones (3.8)
final lista = [?posibleNulo, 'fijo'];
// Dot shorthands (3.10): se omite el tipo cuando se sabe
Column(mainAxisAlignment: .center, crossAxisAlignment: .start, children: [...]);
```
- Null safety obligatorio: `String?`, `!`, `late`, `required`. Ya no existe código sin null safety.
- Dart 3.12 trae constructores primarios en modo experimental: no los uses si no se pide.

## 2. Flutter: APIs renombradas o retiradas
| Antiguo (NO) | Actual (SÍ) |
|---|---|
| `color.withOpacity(0.5)` | `color.withValues(alpha: 0.5)` |
| `WillPopScope(onWillPop: ...)` | `PopScope(canPop: false, onPopInvokedWithResult: (didPop, r) {...})` |
| `MaterialStateProperty`, `MaterialState` | `WidgetStateProperty`, `WidgetState` |
| `textScaleFactor` | `textScaler: TextScaler.linear(1.2)` |
| `ThemeData(primarySwatch: ...)` | `ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: ...))` (Material 3 por defecto) |
| `RaisedButton`, `FlatButton`, `OutlineButton` | `ElevatedButton`, `TextButton`, `OutlinedButton`, `FilledButton` |
| `Scaffold.of(context).showSnackBar` | `ScaffoldMessenger.of(context).showSnackBar` |
| `BottomNavigationBar` (M2) | `NavigationBar` (M3) |
| `ButtonBar` | `OverflowBar` |
| `Color.value`, `.red`, `.green` | `.toARGB32()`, `.r`, `.g`, `.b` |

## 3. Widgets y patrones actuales
```dart
MaterialApp.router(
  theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFF26B21))),
  routerConfig: router,                 // go_router para navegación con rutas
);

// Espaciado: en Row/Column ya existe spacing (Flutter 3.27+)
Column(spacing: 12, children: [Text('A'), Text('B')]);

// Botones M3
FilledButton(onPressed: comprar, child: const Text('Comprar'));
FilledButton.tonal(onPressed: () {}, child: const Text('Más'));
```
- Usa `const` en todos los widgets que no cambien.
- Estado: `setState` en lo pequeño; en apps: Riverpod (con `@riverpod`), Bloc o `ChangeNotifier` + `ListenableBuilder`.
- Peticiones: paquete `http` o `dio`; JSON con `json_serializable` o con patterns (sección 1).
- Impeller es el motor de dibujo por defecto (iOS y Android 10+).
- Material y Cupertino se están separando del núcleo en paquetes propios: revisa los `import` si el proyecto ya los usa por separado.
- En iOS, Swift Package Manager sustituye a CocoaPods.

## 4. Errores típicos de un modelo con Flutter viejo
1. `withOpacity`, `WillPopScope`, `MaterialStateProperty`, `textScaleFactor`.
2. `RaisedButton`/`FlatButton` (eliminados).
3. `primarySwatch` y Material 2 en vez de `ColorScheme.fromSeed`.
4. Cadenas de `if/else` e `is` donde va un `switch` con patrones.
5. Clases enteras para devolver dos valores → records.
6. `SizedBox(height: 12)` entre cada hijo → `spacing:`.
7. Código sin null safety.
