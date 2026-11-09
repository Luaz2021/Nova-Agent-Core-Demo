# Biblioteca de webs de Nova

Nova hace webs de negocios **minimalistas y con identidad propia**, sin escribir código y sin gastar tokens de nube.
Esta carpeta tiene dos partes: **los datos** (que puedes tocar sin saber programar) y **el motor** (los `.py`).

## Cómo está organizada

```
biblioteca_web/
├── general/
│   ├── paletas.json             colores propios de Nova (fondo, texto, botones…)
│   └── estilos/<estilo>.json    un archivo por estilo: galeria, tostador, fuerza, retiro, oscuro-tech…
├── categorias/<categoria>/
│   ├── _categoria.json          qué secciones lleva la web (recetas), rótulos y si "la foto vende"
│   └── <tipo>.json              cada tipo de negocio: cafeteria.json, gimnasio.json, clinica.json…
├── plantilla_datos*.json        la ficha que rellena Nova con los datos REALES del negocio
└── *.py                         el motor (no hace falta tocarlo)
```

## Cómo elige Nova el diseño (todo automático)

1. Mira **de qué va el negocio** (`negocio.tipo` en la ficha) → categoría y tipo.
2. **Fotos**: primero las de la biblioteca que casan con el tema; si no llegan, busca en internet
   fotografías con licencia libre (y pone el crédito). Nunca fotos que no casen.
3. **Estilo**: solo entre los estilos hechos para ese tipo (`"tipos"` del estilo). Alterna y no repite el anterior.
4. **Colores**: una de las 3 paletas del estilo, sin repetir las últimas de la misma categoría.
5. **Efectos**: los del estilo (scroll bonito, 3D…). En el móvil y con "reducir movimiento" todo sale quieto.
6. Si el cliente **pide** colores o estilo (`"estilo"` en la ficha), mandan los suyos.

## Recetas rápidas (sin programar)

**Añadir un tipo de negocio** (p. ej. heladería): copia `categorias/hosteleria/cafeteria.json` como
`heladeria.json` y cambia:
- `"detectar"`: palabras que lo reconocen (`"helad|gelat"`).
- `"fotos"`: palabras en inglés de las fotos que valen (`"ice cream|gelato"`).
- `"buscar"`: búsquedas en internet (`["gelato shop", "ice cream cone"]`).
- `"paletas"`: ids de paletas de `general/paletas.json`.

**Añadir un estilo nuevo** (p. ej. a partir de una web de referencia): copia un archivo de `general/estilos/`, ponle
otro nombre y cambia:
- `"tipos"`: para qué negocios vale (`["cafeteria", "panaderia"]`).
- `"tipografia"`: letra de Google Fonts.
- `"rasgos"`: `escala` (pequena, media, grande, enorme), `mayus` (true/false), `tracking` (espaciado), `radius` (esquinas).
- `"variantes"`: cómo es la portada (`foto`, `partido`, `tipografico`) y los destacados (`tarjetas`, `lista`, `zigzag`, `bento`).
- `"efecto"` / `"cierre"` / `"decoradores"`: efectos de scroll (`pasos`, `horizontal`, `apiladas` / `zoom`, `mascara` / `titular`, `magnetico`).
- `"tres_d"`: `{"protagonista": "liquido" | "formas" | "particulas3d", "ligero": "profundidad"}` o `{}` para nada.
- `"paletas"`: 3 ids de paleta.

**Cambiar colores**: edita la paleta en `general/paletas.json` (fondo `bg`, texto `ink`, botones `accent`).

Regla de oro: **se copian principios de diseño de las webs de referencia, nunca marcas, logos ni textos.**
Un 3D a medida (configuradores, escenas propias) no sale de aquí: se hace con Claude.

## Probar

```
python montar.py --datos <carpeta>/datos.json --categoria auto --out index.html
```
(Nova lo lanza sola, en local y a 0 tokens de nube.)
