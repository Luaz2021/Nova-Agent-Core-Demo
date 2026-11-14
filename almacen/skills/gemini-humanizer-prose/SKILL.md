---
name: gemini-humanizer-prose
description: "Humanizador avanzado de textos: elimina huellas de IA, sesgos estadisticos (perplejidad y burstiness uniforme), clichés de Wikipedia AI Cleanup y prepara textos para evadir detectores (GPTZero, Turnitin)."
trigger: model_decision
---

# Humanizer Prose: Motor de Des-robotización y Evasión Forense (2026)

Esta habilidad transforma textos generados por LLMs en prosa que replica la huella estilométrica y estadística de la escritura humana experta. Grounded en más de 50 investigaciones peer-reviewed (NeurIPS, ICML, EMNLP, EACL 2024-2026), el catálogo de *Wikipedia: Signs of AI writing* y los motores de evasión estocástica.

---

## 1. Arquitectura de 3 Capas Jerárquicas

1. **Capa 1: Reglas de la Casa (House Rules - La ley del usuario):**
   - Tu voz y estilo mandan por encima de cualquier regla externa. Si hay conflicto, esta capa siempre gana.
   - Puntuación sobria: comillas rectas (`"`), cero em dashes decorativos (`—`), sin negritas innecesarias en listas.
2. **Capa 2: Las 9 Palancas de Humanización (Prescriptive Engine):**
   - Reglas activas de reescritura que atacan la estructura sintáctica y la cadencia antes de entregar el texto.
3. **Capa 3: Auditoría y Verificación Local a 0 Tokens:**
   - Todo texto reescrito en tareas de alta exigencia puede verificarse con el script local:
     `python <NOVA_HOME>\antigravity\scripts\humanize_check.py borrador.md`

---

## 2. Las 9 Palancas Científicas de Humanización

### Palanca 1: Burstiness Agresivo (Variabilidad de Longitud de Oraciones)
- **El defecto de la IA:** Escribe con ritmo de metrónomo (~15 a 20 palabras por oración; desviación estándar $\sigma < 6$).
- **La regla humana:** En textos mayores a 80 palabras:
  - La oración más larga debe superar a la más corta por **al menos 20 palabras** ($max - min \ge 20$).
  - Menos del 45% de las oraciones pueden estar en la banda "peligrosa" de 10 a 20 palabras.
  - Alternar: una frase corta y contundente (4-7 palabras). Luego una frase compleja con subordinadas o incisos (25-35 palabras). Luego una pregunta o fragmento.

### Palanca 2: Perplejidad Léxica & Frecuencia Inversa
- Sustituir elecciones predecibles y de baja perplejidad por vocabulario exacto y de dominio:
  - En vez de *"abordar los desafíos"* -> *"destrabar el cuello de botella"*.
  - En vez de *"implementar una estrategia robusta"* -> *"cerrar el acuerdo comercial"*.

### Palanca 3: Baneo Estricto del Catálogo de Slop (Wikipedia AI Cleanup)
Prohibido usar los términos comodín que delatan el pre-entrenamiento de OpenAI/Anthropic/Google:
- **Inglés:** *delve, tapestry, testament, underscore, leverage, utilize, robust, comprehensive, streamline, foster, facilitate, pivotal, nuanced, notable, enduring, in the realm of, multifaceted, a plethora of, vibrant, seamless, beacon*.
- **Español:** *en conclusión, en el vertiginoso mundo, un tapiz de, sirve como testimonio, es crucial destacar, es importante señalar, vale la pena mencionar, desempeña un papel fundamental, robusto, aprovechar al máximo, fomentar, facilitar, hito transformador, huella indeleble*.

### Palanca 4: Copulativas Simples vs Verbos Inflados
- Usar **es, son, tiene, cuenta con** en lugar de inflaciones metafóricas:
  - ❌ *"Nuestra plataforma se erige como un testimonio de innovación."*
  - ✅ *"Procesamos 4,000 operaciones por segundo con dos caídas al trimestre."*

### Palanca 5: Destrucción del Paralelismo Negativo ("Not X, but Y")
- La IA abusa de la antítesis simétrica para sonar profunda.
- ❌ *"Esto no es solo una herramienta, es un movimiento hacia el futuro."*
- ❌ *"No se trata de ganar dinero, se trata de cambiar vidas."*
- ✅ Declarar directamente lo que la cosa **ES**, sin el andamio negativo: *"El software procesa pedidos en tiempo real."*

### Palanca 6: Cero Conclusiones Huecas y Falsa Trascendencia
- Baneo total de frases de cierre tipo: *"En conclusión...", "A medida que avanzamos hacia...", "Deja que eso cale (Let that sink in)"*, o resúmenes que repiten lo ya dicho.
- **Regla de cierre humano:** El texto termina en el último hecho concreto o en la siguiente acción a tomar.

### Palanca 7: Disfluencia y Asimetría Controlada
- Los humanos no escriben listas perfectas de tres adjetivos aliterados (*"rápido, escalable y seguro"*).
- Romper tríadas forzadas: usar un solo adjetivo preciso. Permitir repeticiones naturales cuando clarifican en lugar de forzar sinónimos exóticos.

### Palanca 8: Puntuación Limpia y Tipografía
- **Em dashes (—):** Máximo una por cada 300 palabras. En textos cortos (< 300 palabras), cero.
- **Comillas:** Usar comillas rectas simples o dobles (`"`, `'`), nunca tipográficas curvadas (`“`, `”`).
- **Encabezados:** Formato oración (Sentence case), cero emojis decorativos en títulos de documentación seria.

### Palanca 9: Purga de Artefactos y Metadatos Criptográficos
- Eliminar caracteres invisibles de ancho cero (`\u200B`, `\u200C`, `\u200D`, `\uFEFF`) que algunos generadores inyectan como marcas de agua.
- Limpiar restos de chat (`oaicite`, `contentReference`, tracking UTMs).

---

## 3. Protocolo de Ejecución de Dos Profundidades

### Modo A: Pase Quirúrgico (Short Pass - DMs, correos, PRs, captions)
- Aplicar de inmediato las Palancas 3 (Vocabulario), 4 (Verbos simples), 5 (Cero paralelismo) y 8 (Puntuación).
- Salida limpia en un solo paso, sin preámbulos tipo *"Aquí tienes el texto humanizado:"*.

### Modo B: Pase Profundo (Heavy Pass - Papers, artículos, READMEs, ensayos)
1. **Pase 1 (Limpieza de slop):** Extracción de palabras prohibidas y reestructuración de antítesis.
2. **Pase 2 (Inyección de Burstiness):** Medición de longitudes de oración; romper párrafos uniformes forzando oraciones ultra-cortas y oraciones compuestas.
3. **Pase 3 (Especificidad empírica):** Sustituir cualquier adjetivo abstracto por números, nombres de herramientas, metodologías o métricas reales.
4. **Verificación:** Pasar el borrador por `scripts\humanize_check.py` asegurando un Score de Riesgo de IA < 20%.

---

## 4. Ley Inviolable de Preservación Técnica
Al humanizar código, documentación o finanzas:
- **Números exactos, precios, fórmulas, variables, rutas de archivo y lógica de código son 100% sagrados.** La humanización opera sobre el estilo y la sintaxis de la prosa, jamás sobre la verdad de los datos.
