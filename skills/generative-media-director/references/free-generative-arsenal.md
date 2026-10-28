# Arsenal de IAs Generativas Gratuitas y Tokens Libres (Flujo Hibrido)

Catalogo operacional de herramientas de IA generativa con cuotas gratuitas, renovaciones diarias o APIs abiertas sin tarjeta de credito para produccion multimedia (Video, Imagen, Voz/Audio, Musica y Guiones) acoplado a Remotion y codigo.

---

## 1. Generacion de Video (B-Roll, Motion & Animacion)

### PixVerse (pixverse.ai)
- Modelo de cuota: Recarga diaria de ~60 creditos diarios (+90 creditos de bienvenida).
- Capacidad: Text-to-Video e Image-to-Video (efectos visuales dinamicos, animacion de fotos, 4-5 segundos).
- Uso en flujo hibrido: Excelente para animar fotos fijas en bucle continuo de publicaciones diarias.
- Marca de agua: Si en tier gratuito. Se neutraliza en Remotion aplicando padding/zoom o tapando con la barra de progreso inferior.

### Kling AI (klingai.com)
- Modelo de cuota: 66 creditos diarios gratis renovables por inicio de sesion diario.
- Capacidad: Uno de los modelos mas solidos en fisica del movimiento, personajes humanos y dinamica de ropa/manos. Clips de 5 a 10 segundos.
- Uso en flujo hibrido: Convertir capturas de producto o fotos de sujetos en tomas cinematograficas antes de montarlas en Remotion.

### Hailuo AI / Minimax (hailuoai.video)
- Modelo de cuota: Generaciones gratuitas ilimitadas o cuota abierta en interfaz web.
- Capacidad: Realismo cinematografico extremo, iluminacion natural y coherencia de camara en tomas de 6 segundos.
- Uso en flujo hibrido: Generacion rapida de planos de apoyo (B-roll) para fondos de pantalla vertical 9:16.

### ByteDance Dreamina (dreamina.capcut.com)
- Modelo de cuota: 60 a 120 creditos diarios gratuitos segun region.
- Capacidad: Modelo Seedance, control de camara, imagen a video con consistencia visual.
- Uso en flujo hibrido: Creacion de escenas tematicas y tomas de accion.

### Luma Dream Machine (lumalabs.ai)
- Modelo de cuota: 30 generaciones de video gratuitas al mes.
- Capacidad: Movimientos de camara hiper-rapidos y tracking 3D de alta velocidad.
- Uso en flujo hibrido: Transiciones dramaticas y revelaciones de producto.

### Krea AI (krea.ai)
- Modelo de cuota: ~100 unidades de computo diarias gratuitas.
- Capacidad: Canvas interactivo de video y combinacion de estilos en tiempo real.

### Pika (pika.art)
- Modelo de cuota: ~80 creditos mensuales gratuitos (resolucion 480p).
- Capacidad: Efectos especiales de morphing (derretir, inflar, romper) y generacion de efectos de sonido integrados.

### Viggle AI (viggle.ai)
- Modelo de cuota: Generaciones gratuitas en Web y Discord.
- Capacidad: Transferencia de movimiento (Motion Transfer). Permite poner una persona o modelo 2D a repetir la coreografia exacta de un video de referencia.

---

## 2. Generacion de Imagenes y Texturas (APIs 100% Gratuitas y Programables)

### Pollinations.ai (image.pollinations.ai)
- Tipo: API REST 100% gratuita, sin clave de API, sin registro y sin tarjeta de credito.
- Modelos: FLUX (`flux`, `flux.1-schnell`), SDXL, Turbo.
- Endpoint directo GET:
  `https://image.pollinations.ai/prompt/{prompt_encoded}?model=flux&width=1080&height=1920&nologo=true`
- Integracion en codigo (Python / Zero Tokens):
  ```python
  import requests, urllib.parse
  prompt = urllib.parse.quote("Luxury modern apartment interior, photorealistic 8k, warm cinematic lighting")
  url = f"https://image.pollinations.ai/prompt/{prompt}?model=flux&width=1080&height=1920&nologo=true"
  img_data = requests.get(url).content
  with open("background.jpg", "wb") as f:
      f.write(img_data)
  ```
- Uso en flujo hibrido: Nova puede descargar directamente fondos e imagenes a medida en segundos durante la creacion del proyecto sin gastar cuota de ninguna API de pago.

### Cloudflare Workers AI
- Tipo: API en el Edge gratuita con cuenta Cloudflare (sin tarjeta obligatoria para tier base).
- Cuota: 10.000 Neuronas diarias gratuitas.
- Modelos: `@cf/black-forest-labs/flux-1-schnell`, `@cf/stabilityai/stable-diffusion-xl-base-1.0`.

### Hugging Face Serverless Inference API
- Tipo: Token de API gratuito personal.
- Modelos: Miles de modelos open-source (FLUX Schnell, SDXL, LoRAs de anime/arquitectura).

---

## 3. Voz y Sintesis de Audio (TTS Ultrarrealista a Coste 0)

### Edge-TTS (Microsoft Azure Neural Voices en Local)
- Tipo: Motor 100% gratuito, ilimitado, sin conexion a API keys ni consumo de saldo.
- Libreria Python: `edge-tts` (ejecutable desde terminal o script).
- Calidad: Voces neuronales oficiales de Microsoft (Alvaro, Elvira, Jorge, Christopher).
- Ventaja brutal para Remotion: Genera el archivo de audio `.mp3` y a la vez el archivo `.vtt` con los timestamps exactos de cada palabra para subtitulos sincronizados estilo karaoke.
- Comando:
  `edge-tts --voice es-ES-AlvaroNeural --text "Texto del guion" --write-media locucion.mp3 --write-subtitles subs.vtt`

### ElevenLabs (elevenlabs.io)
- Modelo de cuota: 10.000 caracteres mensuales gratuitos por cuenta.
- Calidad: Estandar de oro para clonacion de voz y entonacion emocional humana.

---

## 4. Musica y Efectos de Sonido (SFX)

### Suno (suno.com)
- Modelo de cuota: 50 creditos diarios gratuitos (hasta 10 canciones completas diarias con voces e instrumentos).
- Uso: Creacion de bases instrumentales, beats de lo-fi o trap corporativo a medida segun el ritmo del Reel.

### Udio (udio.com)
- Modelo de cuota: Cuota mensual gratuita renovable.
- Calidad: Mezcla musical y fidelidad de estudio para fondos musicales limpios.

### Freesound.org & Pixabay Audio
- APIs y catalogos abiertos con descargas directas de efectos (whoosh, pop, click de camara, campana).

---

## 5. Guiones, Ganchos y Transcripcion Ultrarrapida (APIs LLM Gratuitas)

### Groq Console (console.groq.com)
- Tipo: API gratuita sin tarjeta de credito.
- Cuota: ~14.400 peticiones diarias para modelos abiertos; velocidad de 300 a 700 tokens/segundo.
- Modelos: Llama 3.3 70B (redaccion de ganchos en menos de 125 caracteres) + Whisper large-v3 (transcripcion de audio a texto a tiempo real).

### Google AI Studio (aistudio.google.com)
- Tipo: API gratuita oficial de Google.
- Cuota: 1.500 peticiones diarias gratuitas con ventana de contexto de mas de 1 millon de tokens.
- Modelos: Gemini Flash 2.5 / 3.8.

### OpenRouter (openrouter.ai)
- Tipo: API unificada sin tarjeta.
- Modelos `:free`: Acceso a Qwen 2.5 72B, Llama 3.3 y Mistral con 50-200 peticiones/dia.

---

## 6. Matriz de Decision en Flujo Hibrido

| Elemento del Video | Herramienta Generativa | Motor de Render / Ensamblado |
| :--- | :--- | :--- |
| **Fondos e Imagenes fijas** | Pollinations.ai (FLUX) o Cloudflare | Guardado local en `assets/` |
| **Clips de movimiento (B-roll)** | PixVerse / Kling AI / Hailuo | Componente `<Video src="..." />` en Remotion |
| **Locucion / Voz en off** | Edge-TTS (Local 0€) o ElevenLabs | Pista `<Audio />` en Remotion |
| **Subtitulos animados** | Whisper (Groq) o Edge-TTS (.vtt) | Componente tipografico sincronizado por frame |
| **Tipografia, branding y marcos** | Ninguna (Codigo puro) | CSS / Tailwind / SVG nativo |
| **Transiciones y cortes** | Ninguna (Codigo puro) | Hook `useCurrentFrame()` e `interpolate()` |
| **Exportacion final** | Ninguna (Codigo puro) | `npx remotion render` con `ffmpeg` local |
