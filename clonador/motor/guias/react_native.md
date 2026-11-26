# GUÍA DE VERSIÓN · React Native (actual: 0.85) + Expo (SDK 56)

Escribe React Native moderno: con Expo, la Nueva Arquitectura y React 19. Lo que aprendiste suele ser RN de 2021-2023.

## 1. Crear el proyecto
```bash
npx create-expo-app@latest MiApp      # forma recomendada (la doc oficial de RN aconseja un framework: Expo)
npx expo start                         # se prueba en el móvil con Expo Go o con una development build
```
- NO uses `npx react-native init` (retirado). Sin Expo: `npx @react-native-community/cli init`.
- **Nueva Arquitectura** (Fabric + TurboModules, sin "puente") activada por defecto: las librerías deben ser compatibles. Motor JS: Hermes.
- React 19.2 dentro: todo lo de la guía de React 19 vale aquí (ref como prop, `use()`, Actions…).

## 2. Navegación: Expo Router (por carpetas, como Next)
```
app/
  _layout.tsx        // pila o pestañas principal
  index.tsx          // pantalla "/"
  (tabs)/_layout.tsx // grupo de pestañas
  producto/[id].tsx  // pantalla con parámetro
```
```tsx
// app/_layout.tsx
import { Stack } from "expo-router";
export default function Layout() { return <Stack screenOptions={{ headerShown: false }} />; }

// app/index.tsx
import { Link } from "expo-router";
export default function Inicio() { return <Link href="/producto/42">Ver producto</Link>; }

// app/producto/[id].tsx
import { useLocalSearchParams, router } from "expo-router";
export default function Producto() { const { id } = useLocalSearchParams<{ id: string }>(); /* router.back() */ }
```
React Navigation sigue existiendo por debajo, pero en proyectos nuevos se usa Expo Router y no `NavigationContainer` + `createStackNavigator` a mano.

## 3. Componentes y librerías actuales
| Antiguo (NO) | Actual (SÍ) |
|---|---|
| `AsyncStorage` de `react-native` | `@react-native-async-storage/async-storage` o `expo-sqlite` / `expo-secure-store` |
| `SafeAreaView` de `react-native` | `react-native-safe-area-context` (`SafeAreaView`, `useSafeAreaInsets`) |
| `<Image>` para todo | `expo-image` (caché, transiciones, placeholder) |
| `ListView`, `ScrollView` con `.map` largo | `FlatList` / `FlashList` |
| `Animated` para gestos complejos | `react-native-reanimated` 4 + `react-native-gesture-handler` |
| Pedir permisos con librerías sueltas | Módulos de Expo: `expo-camera`, `expo-location`, `expo-notifications` |
| `react-native link` | Autolinking (no se hace nada) / config plugins de Expo |
| Variables de entorno con librerías | `EXPO_PUBLIC_API_URL` en `.env` |

## 4. Estilos
```tsx
import { StyleSheet, View, Text, Pressable } from "react-native";
const s = StyleSheet.create({
  tarjeta: { padding: 16, gap: 12, borderRadius: 16, backgroundColor: "#14141F", boxShadow: "0 4px 12px rgba(0,0,0,0.25)" },
  titulo: { fontSize: 20, fontWeight: "600", color: "#fff" },
});
<Pressable style={({ pressed }) => [s.tarjeta, pressed && { opacity: 0.7 }]} onPress={abrir}>…</Pressable>
```
- `gap`, `rowGap`, `columnGap` funcionan en flex.
- Con la Nueva Arquitectura se puede usar `boxShadow` y `filter` como en CSS.
- Usa `Pressable`, no `TouchableOpacity` (sigue existiendo pero es lo antiguo).
- Si el proyecto usa Tailwind: NativeWind (`className="p-4 rounded-2xl"`).

## 5. Errores típicos de un modelo con RN viejo
1. `react-native init` o configurar Android/iOS a mano cuando Expo lo hace.
2. Importar `AsyncStorage` o `SafeAreaView` desde `react-native`.
3. `NavigationContainer` + stack manual en vez de Expo Router.
4. Componentes de clase y `componentDidMount`.
5. Librerías nativas que no soportan la Nueva Arquitectura.
6. `TouchableOpacity` por todas partes en vez de `Pressable`.
