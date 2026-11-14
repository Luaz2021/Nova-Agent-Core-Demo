---
name: gemini-lecture-transcriber
description: "Transcriptor y resumidor de clases, videos de YouTube y grabaciones a texto plano y esquemas de estudio en Drive."
trigger: model_decision
---

# Lecture & Video Transcriber (Extractor de Clases y Grabaciones)

Esta habilidad permite transcribir enlaces de grabaciones de clase, vídeos de YouTube o contenido multimedia a texto plano y procesarlo de inmediato con el **Tutor Académico** para generar apuntes completos y esquemas para tus exámenes.

---

## 1. Cuándo se Activa

El agente activará esta habilidad cuando el usuario:
- Proporcione un enlace a un vídeo o grabación y diga: *"Transcribe esta clase"*, *"Saca los apuntes de este video"*, *"Resúmeme esta grabación de YouTube/Instagram"*, *"Me perdí esta clase, ponte al día con este link"*.

---

## 2. Flujo Automatizado de Procesamiento

1. **Extracción en Texto Plano:**
   - El agente ejecuta el script local en Python:
     `python "<NOVA_HOME>\antigravity\almacen\skills\gemini-lecture-transcriber\scripts\transcribe.py" "<URL>"`
   - Guarda la transcripción limpia en:
     `G:\Mi unidad\Antigravity\transcripts\<nombre-clase>.txt`
2. **Generación de Apuntes (Por el Tutor Académico):**
   - Una vez obtenido el texto plano, el agente no se limita a copiarlo:
     - **Resumen Ejecutivo:** Los 3 conceptos fundamentales explicados en la clase.
     - **Apuntes Estructurados:** Desglose temático con fórmulas, definiciones y ejemplos dados por el profesor.
     - **Batería de Preguntas de Examen:** 3 a 5 preguntas clave que podrían caer en la evaluación sobre esa clase.

---

## 3. Si la Grabación es Privada (En el Campus Virtual)

Si la grabación está dentro del campus virtual de tu universidad (Blackboard, Teams, Zoom, Moodle) con contraseña:
- Solo descarga el archivo de audio/vídeo a tu PC o pásale el archivo `.mp4`/`.m4a`/`.mp3` directamente al agente.
- O abre la grabación en el navegador: con la skill `playwright-cli`, el agente puede inspeccionar la página activa y capturar el flujo de audio/subtítulos.

