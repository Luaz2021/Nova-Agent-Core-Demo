# CARRIL PROYECTO GRANDE (kit corto: léelo entero) · 26/11/2026

Activo cuando el usuario pide algo GRANDE: una app completa, un full stack, un sistema con varios módulos, "de cero",
front + back. Para algo así **por defecto NO lo construyes tú a mano**: lo hace el DIRECTOR (Neon especifica y planea,
Hydrogen construye por fases con caché, la máquina comprueba, Neon inspecciona la seguridad). Probado el 26/11: más
barato que el Orchestrator de Antigravity y con inspección de seguridad.

`<DIR>` = `<PYTHON> "<NOVA_HOME>/antigravity/herramientas/director/nova_director.py"`

## Cuándo SÍ y cuándo NO
- SÍ: app/sistema completo, full stack, 3+ módulos o pantallas, API + front, proyecto "de cero".
- NO: 1-2 archivos o un cambio en algo hecho (lo haces tú) · web de NEGOCIO (estudio web) · copiar una web (clonador) ·
  **prácticas de clase NUNCA** (las hace el usuario) · si el usuario dice "hazlo tú".

## Pasos (en este orden)
1. **Carpeta y enunciado.** Proyecto en `antigravity/proyectos/<nombre>` (o la carpeta que diga el usuario). Escribe
   `TAREA.md` con SUS palabras + lo que sepas (para quién, pantallas, datos, tecnología si la dijo). No inventes requisitos:
   lo que falte lo preguntará el director.
2. **Avísale en UNA línea y lánzalo**: "Esto va por el director: especifica, construye por fases y revisa la seguridad
   (~5-6 % del cupo de 5 h). ¿Dale?" Si en su mensaje ya dijo "hazlo", "dale", "lánzalo" o "encárgate", no preguntes.
   `<DIR> lanzar "<carpeta>" --idea "<carpeta>\TAREA.md"`  (añade `--inspeccion ligera` si dice que no hace falta tanta revisión)
3. **Después de lanzar: NADA.** No esperes, no mires su estado, no abras sus archivos (gastarías por nada). Dile:
   "Lanzado; Marina te avisa cuando acabe o si necesita que decidas algo."
4. **Un mensaje que empieza por `[director]` lo escribe el DIRECTOR, no el usuario** (llega solo al chat cuando se pausa,
   termina o se para). Haz lo que dice: `resumen` y háblale al usuario (las preguntas, el vale o cómo fue). Igual
   **cuando pregunte "¿cómo fue?"** o te diga que sonó Marina: `<DIR> resumen` (sin carpeta = el último). Explícaselo
   corto: qué se hizo, si pasa las pruebas, lo crítico en palabras sencillas, lo que tiene que decidir él y el gasto.
   No releas el código.
5. **Si el resumen dice EN PAUSA:**
   - *Preguntas*: házselas al usuario tal cual, escribe sus respuestas numeradas en `<carpeta>/.director/respuestas.md`
     y `<DIR> lanzar "<carpeta>" --continuar`.
   - *Fase de diseño u otra con herramienta*: haz lo que dice `instrucciones_nova` con esa herramienta (normalmente el
     estudio web: ficha -> validar -> **vale del usuario**) y después `<DIR> lanzar "<carpeta>" --continuar`.
   - *"El hook frenó algo que la fase necesita"*: explícale al usuario QUÉ se frenó y POR QUÉ en palabras sencillas.
     Si dice que sí (su "dale, sigue"), añade la regla que indica `PAUSA.md` a `<carpeta>/.director/permisos.json`
     (solo vale para ese proyecto; nunca claves, cofre ni zona blindada) y `--continuar`. Si dice que no, pregúntale
     qué prefiere.
6. **Hallazgos que "contradicen el enunciado"**: no los arregles tú; explícale el riesgo y que decida él.

## Errores que no debes cometer
- Construir tú un proyecto grande "porque es rápido": salen 15 archivos sin revisar (prueba B del 26/11: clave fija).
- Lanzar dos directores en el mismo proyecto (el director lo impide y te lo dirá).
- Decir "listo" antes del aviso: el director tarda 15-40 min.
