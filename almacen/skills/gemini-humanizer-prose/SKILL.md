---
name: gemini-humanizer-prose
description: "Editor y humanizador de prosa v2.0 (perfiles academico/tecnico/general): elimina huellas de IA sin staccato artificial, aplica Fact-Lock, respeta voz real en espanol panhispanico y valida en local con humanize_check.py."
trigger: model_decision
---

# Humanizer Prose v2.0: Editor Anti-Slop y Preservacion de Voz

Transforma borradores de IA o pule textos dictados por humanos para que lean naturales, precisos y fieles al autor. Combina la arquitectura Fact-Lock y `voice-matching` de `blader/humanizer` v4.0 (MIT), los perfiles por dominio y patrones academicos de `kimhons/humanize` (MIT), la puntuacion por densidad y guardia anti-sobrecorreccion de `ig-humanizer` V3, el catalogo en espanol de `Humanizer-es` (MIT) y la rubrica de 50 puntos de `stop-slop` (MIT).

*(Regla de dominio: para Instagram usar `ig-humanizer`; esta skill cubre textos academicos, tecnicos, profesionales y generales.)*

---

## 1. Arquitectura de 3 Capas y Perfiles de Dominio

1. **Capa 1 — Voz del Autor (siempre manda):**
   - Si existe una muestra o perfil de voz (ej. `memory\estilo_proyecto_uem.md`), esa muestra manda sobre cualquier regla inferior.
   - **Espanol formal panhispanico (base peruana del autor):** prohibido forzar castellanismos de Espana (*vosotros*, *ordenador*, *coger*) o aplanar la sintaxis natural del autor. En trabajos en Espana, usar solo nombres oficiales de leyes/instituciones locales (BOE, CFGS, Ministerio).
2. **Capa 2 — Perfiles por Dominio (sin contradicciones):**
   - `academico` (APA 7 / UEM / tesis): registro formal y analitico, cero digresiones coloquiales ni tuteo al tribunal; **comillas tipograficas (`“ ”`, `« »`) permitidas** (Word/APA 7); pasiva refleja permitida en Metodologia; vigilancia dura de lavado de citas, relleno de manuscrito y pseudoprecision metodologica.
   - `tecnico` (READMEs, docs, informes): neutro, directo, voz activa, comillas rectas (`"`), sin adjetivos promocionales.
   - `general` (correos, Airbnb, articulos): claro, cercano segun registro, sin muletillas de chatbot ni relleno.
3. **Capa 3 — Verificacion Local a 0 Tokens:**
   - Auditar antes de entregar con:
     `<PYTHON> "<NOVA_HOME>/antigravity/scripts/humanize_check.py" --perfil academico --apa borrador.md`

---

## 2. Reglas Activas (2 Niveles: Golpe Unico vs Densidad)

### Nivel A — Patrones Fuertes (1 aparicion = corregir)
1. **Paralelismo negativo y falsos pivotes:** *"no solo X, sino tambien Y"*, *"no es X, es Y"*, *"no se trata de X, sino de Y"*, *"X en lugar de Y"* sin oposicion real. Declarar directamente lo que algo **es**.
2. **Cierres melodramaticos y fragmentos staccato:** *"En conclusion..."*, *"Deja que eso cale"*, *"Ese es el verdadero logro"*, *"El futuro parece prometedor"*, o cadenas de fragmentos dramaticos (*"Sin rodeos. Sin filtros. Solo resultados."*). Terminar en el ultimo hecho concreto.
3. **Aperturas de escenario y falsa trascendencia:** *"En el vertiginoso mundo..."*, *"En el panorama actual..."*, *"En su esencia..."*, *"La verdadera pregunta es..."*, *"A continuacion exploraremos..."*. Ir directo al argumento.
4. **Clichés puros de LLM y lengua de folleto:** *"un tapiz de"*, *"sirve como testimonio"*, *"huella indeleble"*, *"hito transformador"*, *"es crucial destacar"*, *"es importante senalar"*, *"vale la pena mencionar"*, *"cabe destacar"*, *"sin lugar a dudas"*, *"desempena un papel fundamental"*.
5. **Gerundios colgantes de relleno:** *"...mejorando el proceso, destacando la importancia y reflejando el compromiso..."*. Cortar la cola o enunciar el hecho respaldado.
6. **Restos de chat y marcas invisibles:** *"Claro!"*, *"Espero que esto te ayude"*, *"segun mi ultima actualizacion"*, caracteres Unicode de ancho cero (`\u200B`, `\u200C`, `\u200D`, `\uFEFF`), `oaicite`, `contentReference`, UTMs.
7. **Patrones academicos (obligatorios en `academico`):**
   - **Lavado de citas:** *"estudios demuestran"*, *"la literatura senala"*, *"los expertos coinciden"* sin cita `(Autor, ano)`. Exigir fuente real o marcar `[PENDIENTE: fuente]`.
   - **Relleno de manuscrito:** *"hasta donde sabemos"*, *"llena un vacio critico"*, *"representa un avance significativo"*, *"sienta las bases para"*.
   - **Pseudoprecision metodologica:** *"riguroso analisis exhaustivo"*, *"evaluacion cuidadosa"* sin describir que metodo, muestra o herramienta se uso.
   - **Evasivas de tesis:** *"podria argumentarse que"*, *"se podria sugerir que"*. Tomar postura respaldada en datos.

### Nivel B — Patrones por Densidad (actuar con >= 3 marcas en un mismo parrafo)
- **Vocabulario comun sobreusado por IA:** *robusto/a, fomentar, facilitar, potenciar, integral, holistico/a, paradigma, pionero/a, transformador/a, sinergia, en definitiva, asimismo, por otro lado, en este sentido, alberga, ostenta*. Una aparicion natural en un parrafo academico se respeta; **3 o mas en el mismo parrafo** piden reescribir el parrafo completo.
- **Verbos copulativos inflados:** reemplazar cadenas de *sirve como / actua como / cuenta con* por *es / tiene* cuando recargan el texto.
- **Regla de tres y repeticiones:** dejar una enumeracion natural de 3 elementos concretos; recortar triadas huecas (*"rapido, escalable y seguro"*) o varias triadas seguidas. Evitar repetir la misma palabra de contenido 4+ veces en el mismo parrafo (sin caer en carrusel forzado de sinonimos).
- **Rayas (`—`):** tope de 1 cada 300 palabras (o la frecuencia de la muestra del autor). Reemplazar el exceso por coma, dos puntos o parentesis, nunca por punto suelto que genere fragmentos.

### Regla Anti-Staccato (Ritmo Natural, NO Burstiness Forzado)
- **Prohibido fabricar vaiven mecanico corto/largo/corto** o inyectar fragmentos de 2-3 palabras para "engañar" a un detector: hoy es la huella numero 1 de texto pasado por humanizador.
- Corregir el ritmo **solo** cuando un parrafo suena plano (4+ frases seguidas de igual longitud y misma estructura) fundiendo o dividiendo una sola frase con naturalidad.

---

## 3. Tres Modos de Ejecucion

### Modo A — Pase Quirurgico (correos, DMs, PRs, textos cortos)
- Limpiar Nivel A y excesos obvios de Nivel B en una sola pasada, manteniendo brevedad y tono.

### Modo B — Pase Profundo (borradores redactados por IA)
1. **Marcar tells** (Nivel A + densidad Nivel B + patrones academicos).
2. **Reescribir por parrafos** preservando todos los hechos (Fact-Lock).
3. **Autoauditoria critica:** responder internamente *"Que hace que esto todavia suene a IA?"* y corregir solo lo que siga cantando.
4. **Validar en local** con `humanize_check.py` (meta: `Score < 20`) y revisar la rubrica de 50 puntos (Directitud, Ritmo, Confianza, Autenticidad, Concision >= 35/50).

### Modo C — Edicion de Texto Dictado / Luz Verde Academica (por defecto con borradores del autor)
- **Regla de oro:** el autor escribio o dicto las ideas. **NO reescribir desde cero ni sustituir su voz.**
- Permitido (Luz Verde): corregir ortografia, tildes/enes, puntuacion, concordancia, tics orales del dictado y repeticiones accidentales; senalar afirmaciones sin cita `(Autor, ano)` y verificar formato APA 7.
- **Guardia anti-sobrecorreccion:** al terminar, comprobar que (a) no se hayan introducido fragmentos staccato ni muletillas de IA, (b) no se haya perdido la cadencia personal del autor, y (c) si el parrafo ya estaba limpio, no tocarlo por inercia.

---

## 4. Fact-Lock Inviolable (Cero Alucinaciones)
- **Intocables:** cifras, porcentajes, fechas, nombres propios, citas `(Autor, ano)`, citas textuales entre comillas (`“...”`, `"..."`, `«...»`), DOIs, URLs, formulas, codigo y rutas.
- Jamas inventar fuentes, datos ni ejemplos para "dar autenticidad". Si falta un dato o una referencia, marcar `[PENDIENTE: ...]` y preguntarlo al autor.
