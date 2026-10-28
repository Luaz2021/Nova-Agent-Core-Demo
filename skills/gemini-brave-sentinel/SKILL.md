---
name: gemini-brave-sentinel
description: "Inspeccion en tiempo real del navegador Brave: pestaña activa, videos de YouTube y apuntes de Google Meet."
---

# 🦁 Brave Browser Sentinel & Meeting Assistant v3

Conecta a Nova directamente con el navegador Brave diario mediante WebSocket seguro bidireccional (`127.0.0.1:5005`).

## 1. Arquitectura Pull y Comandos Disponibles
La extension opera bajo el modelo Pull en `G:\Mi unidad\Antigravity\brave_extension_v3`:
- `SNAPSHOT`: Arbol de accesibilidad semantico con referencias numeradas (`ref`) para entender que hay en pantalla en menos de 500 tokens.
- `CLICK`: Clic con scroll centrado por `ref` o por selector CSS.
- `TYPE`: Escritura con setter nativo de prototipo compatible con React/Next.js y emision de eventos `input`, `change` y `keydown` (Enter).
- `GET_SELECTION`: Lectura instantanea del texto seleccionado por el usuario con el raton.
- `SCROLL`: Desplazamiento inteligente (`up`, `down`, `top`, `bottom`).
- `YOUTUBE_CONTROL`: Control de reproduccion (`toggle`, `play`, `pause`, `speed`, `next`).

## 2. Invocacion desde Antigravity / PowerShell
Para consultar el estado o mandar una accion a Brave:
```powershell
# Obtener estado de conexion
Invoke-RestMethod -Uri "http://127.0.0.1:5005/status" -Method Get

# Obtener snapshot de la pestaña activa
Invoke-RestMethod -Uri "http://127.0.0.1:5005/snapshot" -Method Get

# Escribir en un buscador (ref 1) y presionar Enter
$body = @{ action = "TYPE"; args = @{ ref = 1; text = "black clover"; enter = $true } } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:5005/execute" -Method Post -Body $body -ContentType "application/json"
```

## 3. Pestañas en Vivo y YouTube
- Cuando el usuario pregunte: *"¿Que video tengo abierto en Brave?"* o *"Revisa la web que estoy viendo"*:
  1. Consultar `/snapshot` o `YOUTUBE_CONTROL` en el puente local.
  2. Extraer titulo, URL activa y estado de reproduccion de YouTube.
  3. Resumir el contenido del video o el articulo que Alexander tiene en pantalla.

## 4. Asistente de Reuniones (Google Meet / Zoom Web)
- Cuando el usuario diga: *"Tengo reunion en Meet, toma apuntes de todo lo hablado"*:
  1. Consultar el snapshot de la pestaña activa de `meet.google.com`.
  2. Extraer subtitulos en vivo (Closed Captions).
  3. Generar un acta de reunion estructurada en `G:\Mi unidad\Antigravity\memory\actas_reunion.md`.
