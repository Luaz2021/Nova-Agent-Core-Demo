---
name: gemini-humanizer-prose
trigger: model_decision
description: "Humanizador de redacciÃ³n y eliminaciÃ³n de patrones artificiales de IA (blader/humanizer). Basado en los criterios editoriales de Wikipedia contra textos de IA. Elimina fÃ³rmulas robÃ³ticas (no es solo X sino Y, trÃ­adas forzadas, cierres melodramÃ¡ticos, palabras comodÃ­n como crucial/fundamental/tapiz) para que la documentaciÃ³n, correos, READMEs y commits suenen como escritos por un humano real."
---

# Humanizer: Elimina Patrones Artificiales de IA

Esta habilidad limpia textos, documentaciÃ³n, emails, PRs y READMEs de los clichÃ©s, tics de lenguaje y estructuras sintÃ¡cticas que delatan a los modelos de lenguaje (basada en la guÃ­a oficial de Wikipedia sobre *Signs of AI Writing*).

---

## 1. CuÃ¡ndo se Activa

El agente activarÃ¡ esta habilidad cuando:
- El usuario pida: *"Humaniza este texto"*, *"Haz que esto no parezca escrito por una IA"*, *"Reescribe este README/correo para que suene natural"*, *"Quita los clichÃ©s de ChatGPT/Gemini"*.
- Al redactar descripciones de Pull Requests, mensajes de commit o documentaciÃ³n pÃºblica que deba sonar natural y autÃ©ntica.

---

## 2. Los Patrones de IA a Erradicar (AI Tells)

### A. Estructuras de Puesta en Escena (Staging)
1. **La fÃ³rmula "No solo X, sino Y" ("Not only X, but Y"):**
   - âŒ *AI:* "Esto no es solo una base de datos, es el corazÃ³n de tu negocio."
   - âœ… *Humano:* "Esta base de datos almacena los pedidos de los clientes."
2. **Cierres melodramÃ¡ticos de una sola lÃ­nea:**
   - âŒ *AI:* "Y esa es la verdadera victoria." / "Deja que eso cale." / "En un mundo cada vez mÃ¡s digital..."
   - âœ… *Humano:* Cortar la frase por completo. El hecho habla por sÃ­ mismo.
3. **TrÃ­adas forzadas (Rhythm by rule):**
   - âŒ *AI:* "Una soluciÃ³n rÃ¡pida, escalable y eficiente." (Siempre listas de 3 adjetivos).
   - âœ… *Humano:* Usar solo el adjetivo que realmente aporta informaciÃ³n relevante.

### B. Palabras ComodÃ­n Infladas (Stock Words)
- Eliminar palabras como: *crucial, fundamental, imprescindible, un tapiz de..., en conclusiÃ³n, es importante destacar que, sin lugar a dudas, pionero, transformador*.
- Sustituir afirmaciones infladas por hechos verificables concretos.

### C. Formato RobÃ³tico
- Evitar poner en negrita cada una de las palabras iniciales de una lista sin motivo.
- Variar la longitud de las oraciones: la escritura humana combina frases muy cortas con explicaciones mÃ¡s largas; la IA tiende a hacer todos los pÃ¡rrafos de longitud idÃ©ntica.

---

## 3. Modo de Trabajo

1. **Preservar el Hecho TÃ©cnico al 100%:** Nombres de variables, rutas, comandos, fechas, nÃºmeros y cÃ³digo no se tocan.
2. **Reescritura Natural:** Se reescribe la idea con tono directo, profesional y sobrio, eliminando cualquier rastro de lenguaje de ventas o entusiasmo falso.

