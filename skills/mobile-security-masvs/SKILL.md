---
name: mobile-security-masvs
description: "Estandar Ciberseguridad Movil OWASP MASVS v2: Keystore/Keychain, SSL Pinning, Zero-Trust, Biometria, R8/Ofuscacion y Anti-Tampering."
---

# Mobile Security MASVS · OWASP Standards & Zero-Trust Defense

## 1. Almacenamiento Seguro (MASVS-STORAGE)
- **Prohibicion de Texto Plano:**
  - Prohibido almacenar JWTs, llaves de API, datos personales sensibles o credenciales en `SharedPreferences`, `UserDefaults` o `AsyncStorage` sin cifrar.
- **Implementacion por Plataforma:**
  - **Android:** `EncryptedSharedPreferences` respaldado por `AndroidKeyStore` con cifrado AES-256-GCM.
  - **iOS:** `Keychain Services` con politicas de accesibilidad estrictas (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`).
  - **React Native:** `expo-secure-store` o `react-native-keychain`.
  - **Flutter:** `flutter_secure_storage`.
- **Cero Secretos en Binario:**
  - Prohibido hardcodear llaves maestras, secretos de pago (Stripe secret key) o `service_role_key` de Supabase en el codigo de la app. Los clientes moviles se consideran entornos comprometidos por diseno.

## 2. Seguridad en Comunicaciones & Red (MASVS-NETWORK)
- **Cierre de Conexiones Inseguras:**
  - Android: `network_security_config.xml` con `cleartextTrafficPermitted="false"`.
  - iOS: `App Transport Security (ATS)` estricto en `Info.plist` (prohibido `NSAllowsArbitraryLoads = true`).
- **SSL Certificate Pinning (Para APIs Criticas):**
  - Implementar pinning de clave publica (SPKI hash) en clientes HTTP (OkHttp `CertificatePinner`, TrustKit en iOS o interceptores en Dio/Ktor) para mitigar ataques Man-in-the-Middle (MitM) con proxies locales.
  - Mantener siempre al menos una clave de respaldo (backup pin) para evitar caidas ante rotacion de certificados del servidor.

## 3. Autenticacion & Criptografia (MASVS-AUTH & CRYPTO)
- **Biometria Segura:**
  - Integrar mediante `BiometricPrompt` nativo (Android) y `LocalAuthentication` (iOS).
  - Exigir siempre verificacion criptografica: la clave en Keystore/Keychain debe desbloquearse unicamente tras autenticacion biometrica positiva (`setUserAuthenticationRequired(true)`).
- **Ciclo de Vida de Tokens:**
  - Access tokens con expiracion corta (15 a 60 minutos) y Refresh tokens con rotacion obligatoria almacenados en hardware seguro.

## 4. Resiliencia & Proteccion de Codigo (MASVS-CODE & RESILIENCE)
- **Ofuscacion & Minificacion (Android):**
  - Activar R8 en modo release con ofuscacion de clases y metodos para dificultar la ingenieria inversa con herramientas como JADX o Apktool.
- **Proteccion contra Entornos Alterados:**
  - En apps financieras o criticas, detectar manipulacion basica: ejecucion en emuladores publicos, presencia de binarios `su` / Magisk (Android) o carpetas de jailbreak (`/Applications/Cydia.app` en iOS).
- **Desactivacion de Modo Debug:**
  - Asegurar `android:debuggable="false"` en manifiestos de produccion y stripping completo de simbolos de depuracion en binarios iOS.
