---
name: flutter-dart-core
description: "Estandar Flutter & Dart 2026: Dart 3 (Records/Pattern Matching), Flutter 3.2x+, Impeller Engine, Riverpod/BLoC y Clean Architecture."
---

# Flutter & Dart Core · Senior Architecture Standards

## 1. Lenguaje Dart 3 & Tipado Estricto
- **Patrones y Records de Dart 3:**
  - Modelado de estados de UI mediante clases selladas (`sealed class UiState`) para garantizar chequeo exhaustivo en bloques `switch`.
  - Retorno de tuplas y desestructuracion limpia usando records `(int, String)`.
  - Null-safety estricto sin uso abusivo del operador de asercion `!`.
- **Estructura Modular Clean Architecture:**
  - `presentation/`: Widgets desacoplados, Controllers/Notifiers y mappers a UI.
  - `domain/`: Entidades inmutables puras y Casos de Uso (`UseCases`).
  - `data/`: Modelos con deserializacion JSON, DataSources (Dio / Http / Local DB) y Repositorios.

## 2. Motor Grafico Impeller & Performance de UI
- **Impeller como Motor de Renderizado:**
  - Habilitado por defecto en iOS y Android para eliminar la compilacion de shaders en tiempo de ejecucion (cero micro-tirones o *jank*).
- **Disciplina de Widgets:**
  - Uso estricto de constructores `const` en todo widget estatico para que Flutter reutilice el arbol de elementos en memoria.
  - Separar widgets grandes en micro-widgets atomicos con su propio `build()` para limitar el area de reconstruccion.
  - Prohibido crear metodos helpers tipo `Widget _buildItem()` que rompan el arbol de renderizado; crear clases `StatelessWidget` dedicadas.

## 3. Gestion de Estado Reactivo
- **Riverpod (Code Generation con `@riverpod`):**
  - Manejo asincrono mediante `AsyncNotifierProvider` y consumo en vista con `.when(data: ..., loading: ..., error: ...)`.
  - Inyeccion modular sin depender del `BuildContext`.
- **BLoC (Para Aplicaciones Enterprise):**
  - Separacion estricta de `Events` y `States` con `flutter_bloc`.
  - Transformacion de eventos pesados con `rxdart` (debounce en busquedas, throttle en botones de pago).

## 4. Persistencia & Seguridad Local
- **Almacenamiento Cifrado:**
  - Guardar tokens de acceso y credenciales exclusivamente con `flutter_secure_storage`.
  - Datos estructurados o cache offline mediante `drift` (SQLite con typesafety) o `isar`.
- **Comunicaciones HTTP:**
  - Cliente `dio` con interceptores para renovacion automatica de tokens y timeouts configurados.
