---
name: index-mobile-dev
description: "Indice Macro Mobile: Android con XML y Views (practicas de clase) o con Compose, skills oficiales de Google (CLI, tests, seguridad, ANR, AGP 9), iOS (Swift/SwiftUI), React Native (Expo) y Flutter (Dart)."
---

# Index 07 · Mobile Development & Multiplatform (1-Hop Router)

## 0. Android: primero mira que usa el proyecto (24/11)
- **Tiene `res/layout/*.xml` y Activities** (las practicas de clase): `android-views-xml`. Respeta ese estilo: NO migrar a
  Compose ni meter Hilt/ViewModel/Flow/arquitectura limpia si el proyecto no los usa. Lo de abajo sobre Compose y
  UDF NO aplica.
- **Ya es Compose**: `android-compose`.
- **Practica** (`practica_*`, `entregable_*`): explica y propone; el usuario escribe (lo frena un hook). Con "hazlo tu":
  solo el trozo necesario con `edit_file`.
- **Proyecto en una carpeta sincronizada (Drive, OneDrive, iCloud)**: build fuera de ella (ver `android-views-xml`).
- Estructura y arreglar sin romper: `estructura-proyectos`.

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **Salto Obligatorio al Almacen:** Al crear o modificar una app movil, abrir obligatoriamente el `SKILL.md` de la plataforma activa en el apartado 2 (Android: `android-views-xml` o `android-compose` segun el punto 0; `ios-apple-core`, `react-native-expo` o `flutter-dart-core`) antes de armar el contrato para `qwen3.5:9b`. Reparar siempre por lineas (`edit_file <= 35%`), nunca reemplazando el archivo entero.
- **Arquitectura Limpia & Flujo Unidireccional (UDF) (proyectos que ya la usan o apps nuevas grandes; no en practicas con XML):** En cualquier plataforma movil, el estado fluye hacia abajo (State) y los eventos fluyen hacia arriba (Events). Separar estrictamente `UI/Presentation` -> `Domain (UseCases/State)` -> `Data (Repository/DataSource)`. Prohibido incrustar logica de persistencia o llamadas HTTP dentro de componentes visuales.
- **Por plataforma (solo proyectos que ya lo usan o apps nuevas; el detalle esta en su skill del apartado 2):**
  - Android Compose: `StateFlow` + `collectAsStateWithLifecycle()`, Hilt/Koin, KSP (no `kapt`), Material 3, R8 en release.
  - iOS (Swift 6): `async/await` + `@MainActor`, `@Observable`, MVVM o TCA, SwiftData. React Native: Expo Router,
    New Architecture, TanStack Query + Zustand. Flutter: Riverpod/BLoC, null-safety y records de Dart 3.
- **Seguridad movil (MASVS):** cero secretos en el cliente (`strings.xml`, `Info.plist`, env); almacenamiento seguro
  (Keystore / Keychain / secure-store); HTTPS estricto (+ pinning en APIs sensibles); R8 / symbols stripping en release.

## Trampas de Nova (errores reales ya cometidos)
- Expo en Windows: probar `npx expo start --lan` antes del tunel; `@expo/ngrok` como devDependency (nunca global) y `npx expo login` o authtoken para `--tunnel`.
- Si "no levanta" en el movil, mirar primero la URL exacta de la captura (subdominio o IP tecleados mal es lo mas frecuente).
- Versiones: comprobar las del proyecto (Expo SDK, Kotlin, Swift, Flutter) antes de usar APIs nuevas (Ley 12).

## Definicion de hecho
- Build o analisis en verde (`gradlew assembleDebug`, `npx expo-doctor` / arranque, `flutter analyze`) y probado en emulador o dispositivo.

## 2. Mapa de Salto al Almacen (`<NOVA_HOME>/antigravity/almacen/` + la ruta `skills/...` de cada entrada; copia local, nunca leer de la carpeta de Drive)
Abrir con `read_file` en paralelo al iniciar o auditar desarrollo movil:
- **Android con XML y Views (practicas):** `skills/android-views-xml/SKILL.md`
- **Android con Compose:** `skills/android-compose/SKILL.md`
- **Oficiales de Google (en ingles, Apache-2.0, ver FUENTE.md; leer solo la que toque):**
  - comando `android` (crear/ejecutar, emuladores, inspeccionar UI): `skills/android-cli/SKILL.md`
  - montar tests unitarios/UI: `skills/android-testing-setup/SKILL.md`
  - la app se congela (ANR): `skills/android-anr-audit/SKILL.md`
  - seguridad de Intents / permisos: `skills/android-intent-security/SKILL.md`, `skills/android-permissions-security/SKILL.md`
  - subir Android Gradle Plugin a 9 (solo si se pide): `skills/android-agp-9-upgrade/SKILL.md`
  - edge-to-edge (solo Compose): `skills/android-edge-to-edge/SKILL.md`
  - migrar XML a Compose (SOLO si el usuario lo pide): `skills/android-migrar-xml-a-compose/SKILL.md`
- **Apple & iOS Nativo:** `skills/ios-apple-core/SKILL.md`
- **Cross-Platform React Native:** `skills/react-native-expo/SKILL.md`
- **Cross-Platform Flutter:** `skills/flutter-dart-core/SKILL.md`
- **Seguridad & Auditoria Movil:** `skills/mobile-security-masvs/SKILL.md`
