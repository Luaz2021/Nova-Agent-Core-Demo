---
name: gemini-reverse-engineering
description: "Ingenieria inversa de binarios, APKs, scripts JS ofuscados y protocolos de red (Ghidra, Radare2, Frida)."
---

# 🧬 Reverse Engineering Mastery

Esta habilidad guía al agente en tareas de ingeniería inversa, auditoría binaria y desofuscación profunda.

## 1. Desofuscación de Frontend & APIs Ocultas
- Analizar bundles minificados de Webpack/Vite/Rollup.
- Localizar endpoints internos, tokens hardcodeados y lógicas criptográficas en JavaScript cliente (`AST parsing`).
- Reconstrucción de flujos de autenticación y firmado de peticiones (HMAC, JWT).

## 2. Binarios y Ejecutables (ELF / PE / Mach-O)
- Análisis estático con herramientas CLI (`strings`, `objdump`, `nm`, `readelf`).
- Identificación de funciones criptográficas y rutinas de empaquetado (UPX, VMProtect).
- Protocolos de parcheo y bypass de protecciones lógicas.

## 3. Análisis de APKs (Android)
- Descompilación con `jadx` / `apktool`.
- Inspección de certificados, Network Security Config (SSL Pinning) y hooks con Frida.
