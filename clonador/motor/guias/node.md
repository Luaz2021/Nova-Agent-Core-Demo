# GUÍA DE VERSIÓN · Node.js (LTS en producción: 24 · 26 pasa a LTS en octubre de 2026)

Node trae de serie lo que antes eran librerías. Antes de instalar un paquete, mira si ya viene dentro.

## 1. Lo que ya NO hace falta instalar
| Paquete antiguo (NO) | Node actual (SÍ) |
|---|---|
| `node-fetch`, `axios` para lo básico | `fetch` global |
| `ws` (cliente) | `WebSocket` global |
| `nodemon` | `node --watch app.js` |
| `dotenv` | `node --env-file=.env app.js` o `process.loadEnvFile()` |
| `jest` / `mocha` para tests simples | `node --test` + `node:test` y `node:assert` |
| `ts-node` / compilar para ejecutar TS | `node app.ts` (borra los tipos y ejecuta; sin enums ni sintaxis solo de TS) |
| `uuid` | `crypto.randomUUID()` |
| `rimraf`, `mkdirp` | `fs.rm(p, { recursive: true })`, `fs.mkdir(p, { recursive: true })` |
| `glob` | `fs.glob()` |
| `moment` / `date-fns` (fechas) | `Temporal` (por defecto en Node 26) o `Intl` |
| `chalk` (colores) | `util.styleText("green", "ok")` |
| `better-sqlite3` para cosas pequeñas | `node:sqlite` (`DatabaseSync`) |

## 2. Módulos: ESM por defecto
```js
// package.json → "type": "module"
import { readFile } from "node:fs/promises";     // prefijo node: siempre
import path from "node:path";
const ruta = path.join(import.meta.dirname, "datos.json");   // en vez de __dirname
const datos = JSON.parse(await readFile(ruta, "utf8"));     // await en el nivel superior
import config from "./config.json" with { type: "json" };   // importar JSON
```
- `require()` ya puede cargar módulos ESM (sin bandera): mezclar es posible, pero en código nuevo usa `import`.
- Nada de callbacks: `fs/promises`, `timers/promises` (`await setTimeout(1000)`), `stream/promises` (`pipeline`).

## 3. Servidor y peticiones
```js
const r = await fetch("https://api.ejemplo.com/datos", { signal: AbortSignal.timeout(5000) });
if (!r.ok) throw new Error(`HTTP ${r.status}`);
const json = await r.json();

import { createServer } from "node:http";
createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const patron = new URLPattern({ pathname: "/usuarios/:id" });   // URLPattern global (Node 24+)
  const m = patron.exec(url);
  res.writeHead(200, { "content-type": "application/json" }).end(JSON.stringify({ id: m?.pathname.groups.id }));
}).listen(3000);
```
En proyectos reales: Express 5 (ya maneja `async` y errores de promesas), Fastify o Hono.

## 4. Tests, permisos y utilidades
```js
import { test, describe } from "node:test";
import assert from "node:assert/strict";
describe("suma", () => { test("2+2", () => assert.equal(2 + 2, 4)); });
// node --test   ·   node --test --watch   ·   node --test --experimental-test-coverage
```
- `node --permission --allow-fs-read=./datos app.js`: limita qué puede tocar el programa.
- `util.parseArgs()` para leer argumentos de consola.
- `structuredClone(obj)` para copias profundas.
- Arrays modernos: `toSorted()`, `toReversed()`, `with()`, `findLast()`, `Object.groupBy()`, `Array.fromAsync()`, `Promise.withResolvers()`, `Set` con `union()`/`intersection()`.

## 5. Errores típicos de un modelo con Node viejo
1. `require` + `module.exports` en proyectos nuevos.
2. Instalar `node-fetch`, `dotenv`, `nodemon`, `uuid`.
3. `__dirname` dentro de ESM (no existe) → `import.meta.dirname`.
4. Callbacks y `util.promisify` en vez de las APIs de promesas.
5. `fs.existsSync` + `mkdirSync` → `mkdir(p, { recursive: true })`.
6. Express 4 con `try/catch` en cada ruta (Express 5 ya lo gestiona).
7. Usar una versión impar (25) en producción: solo las pares LTS.
