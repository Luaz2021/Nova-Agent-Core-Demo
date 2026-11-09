---
name: ios-apple-core
description: "Estandar de Ingenieria Apple/iOS Nativo: Swift 6, SwiftUI, Framework Observation (@Observable), Swift Concurrency, SwiftData y SPM."
---

# iOS Apple Core · Senior Architecture & Engineering Standards

## 1. Arquitectura & Framework Observation (Swift 6)
- **Estado Moderno con `@Observable`:**
  - Prohibido el uso de `ObservableObject`, `@Published` y `@StateObject` en codigo nuevo (patron legacy de iOS 13-16).
  - Usar la macro `@Observable` de Swift 5.9+ / Swift 6. En la vista SwiftUI, inyectar el estado con `@State var viewModel = ...` o `@Bindable` para bindings bidireccionales.
- **Estructura Limpia MVVM / TCA:**
  - `Views/`: SwiftUI declarativo puro, sin logica de negocio ni llamadas a red en closures.
  - `ViewModels/`: Clases decoradas con `@Observable` y aisladas con `@MainActor`.
  - `Services/`: Actores independientes para llamadas HTTP o sincronizacion background.
  - `Repositories/`: Abstraccion de persistencia (SwiftData / CoreData / Keychain).

## 2. Swift Concurrency Estricta (Data-Race Free)
- **Eliminacion de `DispatchQueue`:**
  - Prohibido usar `DispatchQueue.main.async` o `DispatchQueue.global().async`.
  - Migracion al modelo estructurado con `async/await`, `Task { ... }`, y `withTaskGroup`.
- **Aislamiento de Hilos (Actors & MainActor):**
  - Todo ViewModel o servicio que interactue con SwiftUI debe llevar `@MainActor`.
  - Todo estado mutable compartido entre multiples tareas debe encapsularse en un `actor` para garantizar seguridad contra condiciones de carrera en tiempo de compilacion (Swift 6 strict concurrency).

## 3. Navegacion & UI Moderna en SwiftUI
- **Navegacion Declarativa:**
  - Prohibido usar `NavigationView` (deprecado).
  - Usar `NavigationStack(path: $path)` con tipos `Hashable` y modificadores `.navigationDestination(for: Destination.self)`.
- **Feedback Haptico & Accesibilidad:**
  - Integrar haptica nativa con `UIImpactFeedbackGenerator` o `.sensoryFeedback()` de SwiftUI.
  - Soportar Dynamic Type en textos y etiquetas accesibles (`.accessibilityLabel`, `.accessibilityHint`).

## 4. Persistencia Local & Gestor de Paquetes
- **Persistencia con SwiftData:**
  - Modelado con `@Model` y consultas reactivas con `@Query(sort: ...)`.
  - Operaciones masivas o sincronizacion en segundo plano utilizando `ModelContext` instanciado contra el `ModelContainer` compartido.
- **Gestor de Dependencias:**
  - **Swift Package Manager (SPM) exclusivo:** Cero dependencias en CocoaPods o Carthage. Toda libreria debe integrarse mediante `Package.swift` o dependencias nativas de Xcode.
