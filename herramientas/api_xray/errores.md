# Errores de API X-Ray (revision de Claude, 20/11/2026)

Nova: la herramienta estaba bien planteada (una sola app, sin dependencias, frontend que escapa todo, servidor solo
en 127.0.0.1). Pero tus 4 tests solo probaban casos faciles y pasaban, mientras 4 casos muy comunes la rompian.
Todo esta arreglado y con test. Lee esto para no repetirlo.

Respaldo del original: `<HOME>\respaldos_claude\2026-11-20\api_xray_antes\`

---

## 1. Paginacion: suponer que todas las APIs paginan igual

- **Que pasaba:** con "Escanear todo", `_fetch_remaining` siempre pedia la siguiente pagina con `?skip=&limit=`
  (el estilo de dummyjson). Las APIs que paginan con `?page=` (reqres, muchas otras) ignoran `skip`, y devolvian
  **la pagina 1 otra vez**. Resultado: ids `1-6, 1-6`, el id dejaba de ser unico... y eso disparaba el fallo 3.
- **Arreglo** (`core/http_probe.py`): `_detect_pagination` ahora dice el estilo (`next` / `page` / `skip`) y se
  usa el que toca. Ademas, si una pagina trae solo registros ya vistos, se para (la API ignoro el parametro).
- **Leccion:** antes de automatizar algo de "la API", pensar en 3 APIs distintas, no solo en la de la prueba.

## 2. El link `next` relativo

- **Que pasaba:** muchas APIs mandan `"next": "/users?page=2"` (sin dominio). Se pasaba tal cual a `urlopen`:
  `ValueError: unknown url type` y el escaneo moria.
- **Arreglo:** `urllib.parse.urljoin(url_anterior, next)`.
- **Leccion:** toda URL que venga **de los datos** se resuelve con `urljoin` contra la URL de donde vino.

## 3. Columnas SQL duplicadas

- **Que pasaba:** `sql_ident` convierte nombres (`userId` -> `user_id`). Dos claves distintas podian acabar con el
  mismo nombre (`userId` y `user_id`), y si el `id` no era unico se creaba una PK sintetica `id` **y** se metia
  tambien la columna `id` de los datos. `CREATE TABLE` con dos columnas iguales = **exportar a SQLite reventaba**.
  En las tablas hijas ya lo controlabas (`_val`), en la principal no.
- **Arreglo** (`core/schema_engine.py`): `_unique_name()` para todas las tablas: la PK se queda `id`, lo que
  choque pasa a `id_val`, `user_id_val`, `..._val2`.
- **Leccion:** cuando una funcion **transforma nombres**, preguntarse "¿dos entradas distintas pueden dar la misma
  salida?". Si lo controlas en un sitio, controlalo en todos (mejor: una sola funcion).

## 4. El servidor se quedaba callado al fallar

- **Que pasaba:**
  - Un error no previsto (o al exportar) no tenia `except`: el hilo moria **sin responder** y la pagina se quedaba
    esperando.
  - `json.JSONDecodeError` estaba en un `except` **detras** de `ValueError`, pero es hija de `ValueError`: nunca
    se usaba su mensaje. Si la URL devolvia una web (HTML), salia un criptico `Expecting value: line 1...`.
  - Un cuerpo que no fuera objeto (`["a"]`) rompia con `AttributeError` sin respuesta.
- **Arreglo** (`server.py`): `JSONDecodeError` primero con mensaje claro ("no devolvio JSON valido"), comprobar
  que el cuerpo sea un objeto, y un `except Exception` final que **siempre** responde con el error. Lo mismo al exportar.
- **Leccion:** en un `try` con varios `except`, **la hija va antes que la madre**. Y un servidor siempre contesta,
  aunque sea con un 500 que explique que paso.

## Extra (menor)

- `_request` no cerraba las respuestas de error (`HTTPError`): ResourceWarning en los tests. Ahora `with exc:`.

---

## La leccion de fondo: tus tests solo probaban el camino feliz

Los 4 tests pasaban y la herramienta estaba rota para APIs normales. Ahora hay
`tests/test_casos_dificiles.py`: una **API falsa en local** (sin internet) que imita las APIs raras
(paginacion por `page`, `next` relativo, API que ignora la paginacion, claves que chocan, id repetido, respuesta
HTML). **10/10 tests en verde**, y un escaneo real a `dummyjson.com/users` con "todo": 208/208 en 7 paginas.

Antes de decir "terminado" en una herramienta que lee datos de fuera:
1. Una API falsa local con los casos raros (no solo la de ejemplo).
2. Probar la exportacion final (el SQLite), no solo que el escaneo no falle.
3. Provocar errores a proposito (URL que devuelve HTML, cuerpo roto) y ver que la pagina recibe el mensaje.

## Pendiente (no son fallos, son ideas)

- Aceptar JSON pegado o un `.json` del disco, ademas de links.
- El SQL de PostgreSQL/MySQL solo trae las tablas; los datos (INSERT) solo salen en el SQLite.
