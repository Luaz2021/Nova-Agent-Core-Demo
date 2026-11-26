# Carriles por tema (20/11/2026, Claude)

**Para qué:** que Nova (Hydrogen) use las skills correctas SOLA, sin que el usuario le diga cuáles. El código decide, Nova ejecuta.

**Cómo funciona**
1. `nova_core/nova_hook_turno.py` (cada mensaje del usuario) llama a `nova_core/nova_carriles.py`: detecta el tema por las palabras del mensaje (o un atajo `/backend`, `/consola`, `/web`, `/video`, `/investiga`, `/redacta`, `/rea`) y le dice a Nova que lea el **kit** de ese tema.
2. El kit es una ficha corta (1-1,5k tokens) con lo esencial de las skills del tema y su "Definición de hecho" (el verificador). Queda en la conversación (caché): no se relee.
3. `nova_core/nova_hook.py`: si el carril es obligatorio y Nova va a escribir un archivo de ese tema sin haber leído el kit, la frena UNA vez. La segunda pasa (nunca un bucle).

**Archivos**
- `carriles.json`: palabras, atajos, kit, si es obligatorio y qué extensiones vigila. **Aquí se ajusta** (también desde `/destilar`).
- `carril_*.md`: los kits. Si una lección de `inbox_lecciones.md` es de un tema, `/destilar` la fusiona en su kit (máx. ~60 líneas por kit).
- Estado por conversación: `nova_core/.nova_carriles.json` (no hace falta tocarlo).

**Añadir un carril**: nueva entrada en `carriles.json` + su `carril_<nombre>.md`. Probar con un mensaje real.
