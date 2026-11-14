---
name: react-native-expo
description: "Estandar React Native & Expo 2026: Expo Router, New Architecture (Fabric/TurboModules), NativeWind v4, Zustand, TanStack Query y Reanimated 3."
---

# React Native & Expo · Modern Architecture Standards

## 1. Routing & Arquitectura de Proyecto (Expo Router)
- **File-Based Routing Nativo:**
  - Estructurar la aplicacion bajo el directorio `app/`: `_layout.tsx`, `index.tsx`, `(tabs)/`, `(auth)/`, `[id].tsx`.
  - Tipado estricto en rutas con TypeScript habilitado en `expo-router`.
  - Soporte de Deep Linking universal configurado en `app.json` (`scheme` y `associatedDomains`).

## 2. New Architecture & Performance
- **New Architecture Habilitada:**
  - Motor de JavaScript Hermes activo por defecto.
  - Renderer Fabric (C++ sin puente serializado JSON) y TurboModules para comunicacion directa con APIs nativas.
- **Optimizacion de Listas y Renders:**
  - Prohibido `ScrollView` con listas dinamicas grandes. Usar `FlatList` optimizado con `initialNumToRender`, `maxToRenderPerBatch`, `windowSize` y `getItemLayout`, o `@shopify/flash-list` para miles de elementos.
  - Evitar funciones anonimas y objetos inline dentro de `renderItem`.

## 3. Estado Servidor vs Estado Cliente
- **Datos Asincronos & Cache de Red:**
  - `TanStack Query v5` (`@tanstack/react-query`) para todas las consultas remotas, mutaciones optimistas y gestion de cache.
- **Estado Global de la App:**
  - `Zustand` para estado cliente liviano (sesion de usuario, preferencias locales, modales globales).
  - Prohibido inflar Context API con estados de alta frecuencia que causen rerenders globales.

## 4. Estilos & Animaciones a 60/120 fps
- **Estilos con NativeWind v4:**
  - Configuracion de Tailwind CSS optimizada para movil (compilada a estilos nativos de React Native).
  - Manejo de SafeAreaView y bordes dinamicos usando `react-native-safe-area-context`.
- **Animaciones en Hilo UI:**
  - Animaciones complejas y gestos tactiles exclusivamente con `react-native-reanimated` (v3+) y `react-native-gesture-handler`.
  - Todo calculo continuo (arrastres, swipes, interpolaciones) debe ejecutarse en worklets del hilo UI, nunca en el hilo JS.

## 5. Seguridad & Almacenamiento Local
- **Persistencia Segura:**
  - Tokens de autenticacion y secretos de sesion almacenados exclusivamente en `expo-secure-store` (Keychain en iOS, Keystore en Android).
  - Prohibido almacenar tokens JWT en `AsyncStorage` plano.
- **Variables de Entorno:**
  - Prefijo `EXPO_PUBLIC_` unicamente para variables que sean 100% publicas. Prohibido exponer claves secretas de backend en el bundle de la app.
