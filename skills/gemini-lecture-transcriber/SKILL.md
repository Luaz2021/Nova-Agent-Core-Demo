---
name: gemini-lecture-transcriber
description: "Transcriptor y resumidor de clases, videos de YouTube y grabaciones a texto plano y esquemas de estudio en Drive."
trigger: model_decision
---

# Lecture & Video Transcriber (Extractor de Clases y Grabaciones)

Esta habilidad permite transcribir enlaces de grabaciones de clase, vÃ­deos de YouTube o contenido multimedia a texto plano y procesarlo de inmediato con el **Tutor AcadÃ©mico** para generar apuntes completos y esquemas para tus exÃ¡menes.

---

## 1. CuÃ¡ndo se Activa

El agente activarÃ¡ esta habilidad cuando el usuario:
- Proporcione un enlace a un vÃ­deo o grabaciÃ³n y diga: *"Transcribe esta clase"*, *"Saca los apuntes de este video"*, *"ResÃºmeme esta grabaciÃ³n de YouTube/Instagram"*, *"Me perdÃ­ esta clase, ponte al dÃ­a con este link"*.

---

## 2. Flujo Automatizado de Procesamiento

1. **ExtracciÃ³n en Texto Plano:**
   - El agente ejecuta el script local en Python:
     `python "G:\Mi unidad\Antigravity\skills\lecture-transcriber\scripts\transcribe.py" "<URL>"`
   - Guarda la transcripciÃ³n limpia en:
     `G:\Mi unidad\Antigravity\transcripts\<nombre-clase>.txt`
2. **GeneraciÃ³n de Apuntes (Por el Tutor AcadÃ©mico):**
   - Una vez obtenido el texto plano, el agente no se limita a copiarlo:
     - **Resumen Ejecutivo:** Los 3 conceptos fundamentales explicados en la clase.
     - **Apuntes Estructurados:** Desglose temÃ¡tico con fÃ³rmulas, definiciones y ejemplos dados por el profesor.
     - **BaterÃ­a de Preguntas de Examen:** 3 a 5 preguntas clave que podrÃ­an caer en la evaluaciÃ³n sobre esa clase.

---

## 3. Si la GrabaciÃ³n es Privada (En el Campus Virtual)

Si la grabaciÃ³n estÃ¡ dentro del campus virtual de tu universidad (Blackboard, Teams, Zoom, Moodle) con contraseÃ±a:
- Solo descarga el archivo de audio/vÃ­deo a tu PC o pÃ¡sale el archivo `.mp4`/`.m4a`/`.mp3` directamente al agente.
- O abre la grabaciÃ³n en el navegador: con la skill `playwright-cli`, el agente puede inspeccionar la pÃ¡gina activa y capturar el flujo de audio/subtÃ­tulos.

