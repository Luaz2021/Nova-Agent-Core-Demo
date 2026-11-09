---
name: android-core
description: "Estandar de Ingenieria Android Nativo: Kotlin 2.0+, Jetpack Compose, Coroutines/Flow, KSP, UDF, Material 3, R8 y JetBrains Agent Skills."
---

# Android Core · Senior Architecture & Engineering Standards

## 1. Arquitectura & Flujo de Datos (UDF + Clean Architecture)
- **Flujo Unidireccional Estricto (UDF):** El `ViewModel` expone un unico `StateFlow<UiState>` inmutable hacia la UI. La UI solo emite eventos `(UiEvent)` hacia el `ViewModel`.
- **Division de Capas:**
  - `ui/`: Composables puros desacoplados, estados inmutables y preview providers.
  - `domain/`: Casos de uso (`*UseCase.kt`) con una sola responsabilidad publica (`operator fun invoke()`), libres de dependencias de Android framework.
  - `data/`: Repositorios (`*RepositoryImpl.kt`), DataSources (Network con Retrofit/Ktor, Local con Room/DataStore) y Mappers bidireccionales.
- **Inyeccion de Dependencias:** Usar Hilt (`@HiltViewModel`, `@Inject`) o Koin moderno (`koinViewModel()`). Prohibido instanciar dependencias o repositorios a mano en actividades o vistas.

## 2. Jetpack Compose & Rendimiento Visual
- **Disciplina de Recomposicion:**
  - Toda coleccion en clases de estado debe ser inmutable (`kotlinx.collections.immutable`): usar `ImmutableList<T>` o `PersistentList<T>` para evitar recomposiciones fantasmas. Prohibido `List<T>` mutable o estandar en estados de Compose.
  - Anotar modelos de datos estables externos con `@Stable` o `@Immutable`.
  - Usar `remember` para calculos costosos y `derivedStateOf` para transformaciones de estado que cambien con alta frecuencia (ej. scroll offset).
- **Consumo Seguro de Flujos en UI:**
  - Recolectar estados siempre con `val state by viewModel.uiState.collectAsStateWithLifecycle()`. Prohibido `collectAsState()` simple porque sigue consumiendo recursos con la app en segundo plano.
- **Side-Effects Controlados:**
  - Eventos de navegacion o snacks unicos: manejar con `LaunchedEffect` escuchando un canal de eventos (`Channel<UiEffect>`).
  - Limpieza de recursos con `DisposableEffect`. Prohibido ejecutar llamadas de red o persistencia directamente en el cuerpo del Composable.

## 3. Kotlin 2.0+, Coroutines & Concurrencia
- **Estructura de Dispatchers:**
  - Inyectar siempre `CoroutineDispatcher` (no hardcodear `Dispatchers.IO`).
  - `Dispatchers.Main.immediate` para actualizaciones rapidas de UI.
  - `Dispatchers.Default` para calculos pesados, parsing JSON o filtrado de listas.
  - `Dispatchers.IO` para base de datos y llamadas HTTP.
- **Manejo de Estados vs Eventos:**
  - Estados: `MutableStateFlow` inicializado con valor por defecto.
  - Eventos de un solo uso: `Channel<Effect>(Channel.BUFFERED).receiveAsFlow()`.

## 4. Gradle, KSP & Rendimiento de Compilacion
- **Prohibido `kapt`:** Toda generacion de codigo debe correr sobre **KSP** (Kotlin Symbol Processing) para reducir tiempos de build en un 50-70%.
- **Optimizaciones en `gradle.properties`:**
  - `org.gradle.caching=true`
  - `org.gradle.parallel=true`
  - `org.gradle.configuration-cache=true`
- **Compilacion R8 en Release:** Habilitar `isMinifyEnabled = true` e `isShrinkResources = true`. Probar siempre release builds con ProGuard rules especificas para evitar crash por reflexion en librerias como Moshi o KotlinX Serialization.
