# CARRIL INVESTIGACIÓN (kit corto: léelo entero, ~0,8k tokens)

Activo cuando el usuario pide investigar, comparar opciones, buscar fuentes, un estado del arte o datos de mercado.

## Método
1. Convierte el pedido en 3-6 PREGUNTAS concretas y di cuáles vas a responder.
2. Fuentes primero oficiales y primarias (documentación, organismos, artículos, repos), después prensa o blogs.
3. **Cada dato lleva su fuente (URL) y su fecha.** Una cifra importante, contrastada con 2 fuentes.
4. Separa siempre: HECHO (con fuente) · ESTIMACIÓN (de quién) · OPINIÓN · NO ENCONTRADO. Nunca rellenes un hueco inventando: escribe "no encontrado".
5. API/CLI antes que navegador (`search_web`, APIs, `yt-dlp`, `curl`); scrapers 0-token si hay que repetir.

## Entrega
- Respuesta corta arriba (5-8 líneas), luego tabla comparativa si hay opciones, y al final la lista de fuentes.
- Si va a un documento: `redactar.py` (carril REDACCIÓN) con las cifras en `"datos"`.

## Definición de hecho (el verificador)
- Ninguna cifra sin fuente; cada pregunta marcada como respondida, a medias o sin respuesta.

## Escalar
- Síntesis larga o decisión cara (qué tecnología elegir, qué comprar) -> consulta de ventana a Neon con las preguntas y tus fuentes.

<!-- ERRORES_YA_COMETIDOS:INICIO -->
## Errores que ya cometiste (no los repitas)
_Lo genera `nova_aprendido.py kits` desde `memory/aprendido.jsonl` (tus propios errores): no lo edites a mano. Aun no hay ninguno._
<!-- ERRORES_YA_COMETIDOS:FIN -->
