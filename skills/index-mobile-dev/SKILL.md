---
name: index-mobile-dev
description: "Indice Macro Mobile: Android nativo (Kotlin/Compose), iOS (Swift/SwiftUI), React Native (Expo) y Flutter (Dart), arquitectura limpia y seguridad OWASP MASVS."
---

# Index 07 · Mobile Development & Multiplatform (1-Hop Router)

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **Salto Obligatorio al Almacen:** Al crear o modificar una app movil, abrir obligatoriamente el `SKILL.md` de la plataforma activa en el apartado 2 (`android-core`, `ios-apple-core`, `react-native-expo` o `flutter-dart-core`) + `mobile-security-masvs\SKILL.md` antes de armar el contrato para `qwen3.5:9b`. Reparar siempre por lineas (`edit_file <= 35%`), nunca reemplazando el archivo entero.
- **Arquitectura Limpia & Flujo Unidireccional (UDF):** En cualquier plataforma movil, el estado fluye hacia abajo (State) y los eventos fluyen hacia arriba (Events). Separar estrictamente `UI/Presentation` -> `Domain (UseCases/State)` -> `Data (Repository/DataSource)`. Prohibido incrustar logica de persistencia o llamadas HTTP dentro de componentes visuales.
  - Gestion reactiva de estado con `StateFlow` y recoleccion en Compose mediante `collectAsStateWithLifecycle()`.
  - Inyeccion de dependencias con Hilt o Koin moderno.
  - Optimizacion Gradle obligatoria: `KSP` activo (prohibido `kapt`), convention plugins y configuration cache habilitada.
  - Diseno Material 3 estricto, manejo adaptativo para tablets/plegables y optimizacion R8/ProGuard en release.
  - Concurrencia moderna estricta: `async/await`, `actor`, aislamiento con `@MainActor` en capas de UI (prohibido `DispatchQueue.main.async` legacy).
  - Estado moderno con el framework `Observation` (`@Observable`), reemplazando `ObservableObject` y `@Published`.
  - Arquitectura MVVM desacoplada o The Composable Architecture (TCA) para flujos complejos.
  - Persistencia local con SwiftData o CoreData utilizando contextos secundarios asincronos.
  - Enrutamiento basado en archivos con Expo Router y soporte de Deep Linking universal.
  - New Architecture activada: motor Hermes, TurboModules nativos y renderer Fabric.
  - Estado servidor con TanStack Query v5 y estado global liviano con Zustand.
  - Estilos mediante NativeWind v4 (Tailwind nativo) y animaciones fluidas a 60/120 fps en el hilo UI con `react-native-reanimated` v3.
  - Motor grafico Impeller habilitado por defecto (eliminacion de shader compilation jank).
  - Manejo de estado declarativo con Riverpod (usando generacion de codigo `@riverpod`) o BLoC para sistemas empresariales.
  - Null-safety estricto, pattern matching y records de Dart 3.
  - **Cero secretos en el cliente:** Prohibido almacenar API keys privadas, llaves maestras o service role keys en codigo fuente, `strings.xml`, `Info.plist` o variables de entorno cliente.
  - **Almacenamiento seguro:** Android `EncryptedSharedPreferences` / `AndroidKeyStore`, iOS `Keychain Services`, React Native `expo-secure-store`, Flutter `flutter_secure_storage`.
  - **Comunicaciones cifradas:** HTTPS estricto con Network Security Config (Android), App Transport Security (iOS) y SSL Pinning para APIs sensibles.
  - **Proteccion de binarios:** Ofuscacion y minificacion activa con R8 (Android) y symbols stripping en produccion.

## Trampas de Flash (errores reales ya cometidos)
- Expo en Windows: probar `npx expo start --lan` antes del tunel; `@expo/ngrok` como devDependency (nunca global) y `npx expo login` o authtoken para `--tunnel`.
- Si "no levanta" en el movil, mirar primero la URL exacta de la captura (subdominio o IP tecleados mal es lo mas frecuente).
- Versiones: comprobar las del proyecto (Expo SDK, Kotlin, Swift, Flutter) antes de usar APIs nuevas (Ley 12).

## Definicion de hecho
- Build o analisis en verde (`gradlew assembleDebug`, `npx expo-doctor` / arranque, `flutter analyze`) y probado en emulador o dispositivo.

## 2. Mapa de Salto a las Skills (`<NOVA_HOME>/antigravity/` + la ruta `skills/...` de cada entrada)
Abrir con `read_file` en paralelo al iniciar o auditar desarrollo movil:
- **Android Nativo & Compose:** `skills\android-core\SKILL.md`
- **Apple & iOS Nativo:** `skills\ios-apple-core\SKILL.md`
- **Cross-Platform React Native:** `skills\react-native-expo\SKILL.md`
- **Cross-Platform Flutter:** `skills\flutter-dart-core\SKILL.md`
- **Seguridad & Auditoria Movil:** `skills\mobile-security-masvs\SKILL.md`
