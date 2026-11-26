# API X-Ray

Escáner portable de APIs REST / JSON y generador visual de modelo relacional SQL tipo DBeaver. Funciona en **Windows, macOS y Linux** usando únicamente la librería estándar de Python 3.10+ (sin `pip install`).

## Arranque rápido

En Windows (entorno Nova):

```powershell
<PYTHON> "api_xray.py"
```

En macOS / Linux (o Python estándar):

```bash
python3 api_xray.py
```

Opciones útiles:

- Abrir escaneando directo una API: `python3 api_xray.py --url https://dummyjson.com/products`
- Solo consola (sin navegador): `python3 api_xray.py --cli https://dummyjson.com/products --all --sql sqlite`

## Las 4 secciones de la interfaz

1. **Radiografía & Backend:** código HTTP, latencia, métodos permitidos (`OPTIONS`/`HEAD`), cabeceras CORS, paginación y rutas relacionadas.
2. **Datos:** vista Tabla tipo DBeaver (con selector de tabla principal/hijas, búsqueda, ordenación y detalle de fila) + vista Árbol JSON plegable.
3. **Modelo BD & Diagrama:** lienzo ER interactivo con nodos arrastrables, zoom, relaciones `1:1` / `1:N` y generador `CREATE TABLE` para SQLite, MySQL y PostgreSQL.
4. **Diagnóstico & Exportar:** alertas de campos nulos, textos largos o tipos mezclados, y descarga directa a `.sqlite`, `.sql`, `.md` y `.json`.
