# CARRIL CONSOLA (kit corto: léelo entero, ~1k tokens)

Activo cuando el usuario trabaja un programa de consola/terminal (menús, `Scanner`, `input()`, ejercicios de clase en
Java, Kotlin o Python). Si además hay BD, va junto al carril BACKEND.

## 1. Estructura
- `Main` mínimo (crea objetos y lanza el menú) -> `Menu`/`Vista` (bucle, opciones, lee y muestra) -> `Service` (lógica) -> `DAO`/datos (archivo o BD).
- El menú NO tiene lógica de negocio ni SQL: solo pide datos, llama al service y muestra el resultado.
- Si viene de un ENUNCIADO: haz una lista de requisitos y comprueba al final que están TODOS (opción por opción).

## 2. Entrada de datos (lo que más falla)
- Un único `Scanner` para todo el programa (no uno por método) y no cerrarlo hasta salir.
- Java: tras `nextInt()` hay que limpiar con `nextLine()`; mejor leer siempre `nextLine()` y convertir con `Integer.parseInt` dentro de `try/catch (NumberFormatException)`.
- Repite la pregunta hasta que el dato sea válido (bucle), con un mensaje claro de qué se esperaba.
- Kotlin: `readLine()?.trim()?.toIntOrNull()`; Python: `try: int(input(...)) except ValueError`.
- Menú con opción de salir y `default`/`else` para opciones que no existen.

## 3. Salida
- Mensajes claros y en español, sin trazas de excepción para el usuario (la traza al log o a `System.err`).
- Listados alineados (`printf` / f-strings) y un mensaje si la lista está vacía.
- Consola de Windows con tildes: `chcp 65001` o `System.setOut(new PrintStream(System.out, true, "UTF-8"))`.

## 4. Definición de hecho (el verificador)
- Compila y se ejecuta: Java `javac`/`mvn -q compile` + ejecutar; Python `<PYTHON> <script>`.
- Prueba cada opción del menú con un dato bueno, uno malo (letra donde va número, vacío) y la opción de salir.
- Si hay tests, pásalos. Si no hay y es un ejercicio, enseña la ejecución real.

## 5. Escalar
- Si el mismo fallo sale dos veces, consulta al asesor antes de seguir probando a ciegas.

## Profundizar (solo si hace falta)
`almacen/skills/gemini-clean-architecture/SKILL.md` · `gemini-systematic-debugger` · `gemini-tdd-enforcer`
Índice del dominio (1 salto): `config/skills/index-java/SKILL.md` (Java de clase); con BD, también `index-backend-db`.

<!-- ERRORES_YA_COMETIDOS:INICIO -->
## Errores que ya cometiste (no los repitas)
_Lo genera `nova_aprendido.py kits` desde `memory/aprendido.jsonl` (tus propios errores): no lo edites a mano. Aun no hay ninguno._
<!-- ERRORES_YA_COMETIDOS:FIN -->
