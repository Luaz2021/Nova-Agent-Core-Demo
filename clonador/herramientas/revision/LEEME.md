# Revisión a ojo de un clon (22/11/2026, Claude)

El verificador da un número; esto es para MIRAR (la nota tapa las fotos y no ve fallos como fotos que faltan).

- `careo.py <workspace\web> <salida> [3,5,9]` -> careo_N_pc.png / careo_N_movil.png: ORIGINAL | CLON por sección.
- `diferencias.py <workspace\web> <N> <pc|movil> <salida.png>` -> original | clon | píxeles distintos en rojo,
  y las bandas (y) donde se concentran. Texto en rojo suave = fuente sustituta (normal); bloques enteros = fallo.
- `mosaico.py salida.png a.png b.png ...` -> varias fotos en fila.

Regla de oro: comparar SIEMPRE también con la web EN VIVO (navegador a 1920 px y en móvil), no solo con la
"original" que guardó el motor: esa foto también puede salir mal.
