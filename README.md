# 🌌 NOVA - Copiloto Técnico y Arquitecta de Software (Community Edition)

![License](https://img.shields.io/badge/License-MIT-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-success)
![Zero-Tokens](https://img.shields.io/badge/Instalacion-0%20Tokens-brightgreen)
![Skills](https://img.shields.io/badge/Skills-113%20Verificadas-purple)

**Nova** es una copiloto técnica, arquitecta de software y socia de trinchera para programadores, diseñada originalmente para operar como asistente integral en Antigravity IDE y VS Code.

Esta versión (**Community Edition**) es 100% autónoma, opera de forma local en tu máquina, no requiere permisos de administrador (`sudo`) y no contiene credenciales ni datos privados.

---

## ⚡ Instalación en 1 Línea (Zero-Tokens)

El instalador detecta automáticamente tu sistema operativo, crea los enlaces simbólicos de las 113 skills hacia `~/.gemini/antigravity/skills` y configura las reglas maestras `GEMINI.md` a coste cero tokens.

### 🪟 En Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File .\adapters\windows\install.ps1
```

### 🍎 En macOS (Terminal)
```bash
sh ./adapters/macos/install.sh
```

### 🐧 En Linux (Bash)
```bash
sh ./adapters/linux/install.sh
```

---

## 🧠 Características Principales

1. **113 Habilidades Especializadas (`skills/`):**
   - Backend & Arquitectura: Java 21, Spring Boot, FastAPI, PostgreSQL, Supabase RLS y Arquitectura Limpia.
   - Frontend & UI: Diseños estilo Stripe/Linear, GSAP, animaciones cinemáticas y sistema anti-slop.
   - Calibrador Psicológico (`user-intent-reader`): Detecta tu nivel automáticamente (Principiante / Desarrollador / Senior) y adapta sus explicaciones a tu ritmo sin forzar cuestionarios.
2. **Cero `sudo` / Cero Permisos de Root:**
   - En macOS y Linux opera estrictamente en tu espacio de usuario (`~/.gemini`). Imposible que rompa librerías del sistema operativo.
3. **Memoria Persistente Local:**
   - Incluye plantillas limpias para Kanban (`tasks.md`) y Runbook de errores (`napkin.md`) para que Nova recuerde tus decisiones entre sesiones.
4. **Voz Dual y Manos Libres:**
   - Resúmenes ejecutivos de 15 segundos por los altavoces mediante Edge-TTS y reproductores nativos (`winmm` en Windows, `afplay` en Mac, `mpv/aplay` en Linux).

---

## 🔒 Política de Seguridad y Privacidad

- Este repositorio es **Open Source de solo lectura** bajo licencia MIT.
- No se aceptan Pull Requests externos para garantizar la integridad y estabilidad del manifiesto criptográfico de hashes (SHA-256).

### 🛡️ Telemetría Ética y Actualizaciones Respetuosas
Nova incluye un sistema opcional y transparente de mejora continua:
1. **Resumen Mensual Anónimo (Opt-In):** Una vez al mes, si el usuario lo autoriza durante la instalación, Nova genera un resumen ligero de manifiesto (skills optimizadas y errores solucionados) sin rutas locales, código privado ni claves.
2. **Actualizaciones sin pisar tu trabajo:** Cuando Saúl Martínez publica mejoras en el repositorio oficial, Nova te avisa y te pregunta si deseas actualizar. Si aceptas, el sincronizador inteligente coteja los hashes SHA-256, **mantiene intactos tus archivos personales, notas y configuraciones locales**, y solo incorpora las nuevas skills oficiales.

---

## 🏆 Créditos
- **Creador & Arquitecto:** Alexander Martinez ([@Luaz2021](https://github.com/Luaz2021))
- **Copiloto & Estructura:** Agent-Nova-Gemini
