---
name: android-views-xml
description: "Android clasico con Views: Activities, layouts XML (ConstraintLayout/LinearLayout), ViewBinding o findViewById, listeners, Intents, RecyclerView y SQLite/Room basico. La de las PRACTICAS de clase del usuario. Usar cuando el proyecto tiene res/layout/*.xml."
---

# Android con Views y XML (practicas de clase)

## 0. Antes de tocar nada (obligatorio)
- **Mira que usa YA el proyecto** (`app/build.gradle.kts`, `MainActivity`, `res/layout`) y sigue ESE estilo: lenguaje (Java o
  Kotlin), `findViewById` o ViewBinding, LinearLayout o ConstraintLayout. **No migres a Compose**, no metas Hilt, ViewModel,
  Flow ni arquitectura limpia si el proyecto no los usa. Para Compose existe `android-compose`, solo si ya es Compose.
- **Si la carpeta es `practica_*` o `entregable_*`**: explica y propone; el usuario escribe (lo vigila un hook). Con su
  permiso ("hazlo tu"): solo el trozo necesario con `edit_file`, nunca reescribir el XML entero.
- **Proyecto en una carpeta sincronizada (Google Drive, OneDrive, iCloud, Dropbox)**: el build va FUERA de esa carpeta
  (`layout.buildDirectory` a `~/.android-builds/<proyecto>` en `build.gradle.kts`). Errores con `desktop.ini`, `.DS_Store`
  o "Failed to create parent directory" = eso, no el codigo.

## 1. Estructura KISS de una app pequena
```
app/src/main/
  java/<paquete>/        MainActivity + otras Activities; si crece: ui/ (pantallas), data/ (BD, modelos), util/
  res/layout/            activity_main.xml, item_*.xml (filas de listas)
  res/values/            strings.xml (TODOS los textos), colors.xml, themes.xml, dimens.xml
  AndroidManifest.xml    cada Activity nueva se declara aqui
```
- Una Activity = una pantalla = un layout. La logica que no es de pantalla (calculos, BD) en una clase aparte
  (p. ej. `CalculadoraLogica`), sin `View` ni `Context` dentro: asi se prueba sola.

## 2. Layouts XML
- **Ids** con prefijo de tipo y camelCase: `btnSumar`, `txtResultado`, `etNombre` (EditText), `rvLista`. El id del
  XML es el que se usa en el codigo: si cambia en uno, cambia en el otro.
- **ConstraintLayout**: cada vista necesita al menos una restriccion horizontal y una vertical (si no, salta a 0,0 y el
  editor marca error rojo). Ancho "lo que quede" = `android:layout_width="0dp"` + start/end restringidos.
- **LinearLayout** para filas/columnas simples (botones de calculadora: filas horizontales con `layout_weight="1"` y
  `layout_width="0dp"`). No anidar mas de 2-3 niveles.
- **Una linea separadora** = `<View android:layout_height="1dp" android:background="..."/>`.
- Textos en `strings.xml` (`@string/...`), medidas en `dp`, letras en `sp`. Colores en `colors.xml`.
- El editor de diseno: el desplegable de dispositivo en `Custom` con ancho minimo = la vista "se aplasta"; elegir un
  movil (Medium Phone). No es un error del codigo.

## 3. Codigo de la Activity
- `setContentView(R.layout.activity_main)` y luego enlazar vistas: `findViewById<Button>(R.id.btnSumar)` (Kotlin) /
  `Button btnSumar = findViewById(R.id.btnSumar);` (Java), o ViewBinding si el proyecto ya lo tiene activado.
- Listeners: `btn.setOnClickListener { ... }` (Kotlin) / `btn.setOnClickListener(v -> ...)` (Java). Varios botones con
  la misma accion: un solo metodo que recibe el texto o el id, no 20 copias.
- Leer un numero de un EditText: comprobar vacio y capturar `NumberFormatException`; dividir por cero -> mensaje, no crash.
- Estado al girar la pantalla: `onSaveInstanceState` para lo poco que haga falta (p. ej. el texto del resultado).
- La plantilla nueva trae `enableEdgeToEdge()` + listener de insets sobre `R.id.main`: no borrarlo; si se cambia el id
  del layout raiz, cambiarlo tambien ahi.

## 4. Navegar y pasar datos
- `startActivity(Intent(this, OtraActivity::class.java).putExtra("clave", valor))`; en la otra: `intent.getStringExtra`.
- Las claves de extras en constantes (`companion object { const val EXTRA_ID = "id" }`), no escritas a mano dos veces.

## 5. Listas (RecyclerView)
- Layout de fila `item_x.xml` + `Adapter` con `ViewHolder` + `LayoutManager` (`LinearLayoutManager`). Cambiar datos ->
  `notifyItemInserted/Changed/Removed` (o `notifyDataSetChanged` si la practica es basica).

## 6. Datos
- Poco y sencillo: `SharedPreferences`. Tablas: `SQLiteOpenHelper` (lo habitual en clase) o Room si el proyecto ya lo
  usa. Nunca consultas de BD ni red en el hilo principal en apps reales (ANR); en practicas basicas avisar si se hace.
- Consultas con parametros (`?`), nunca concatenando lo que escribe el usuario.

## 7. Errores tipicos (ya vistos)
- `R` en rojo / "Unresolved reference": error en algun XML (mira el XML que tocaste) o Sync de Gradle pendiente.
- La app se cierra al abrir: `findViewById` devuelve null (id que no existe en ESE layout) o Activity sin declarar en el
  Manifest. Mirar Logcat, la primera linea `Caused by`.
- Build roto en Drive: ver punto 0.

## Definicion de hecho
- Compila (`gradlew assembleDebug` o Run), la pantalla se ve bien en un movil normal y en horizontal, sin textos sueltos
  fuera de `strings.xml`, y el cambio es el minimo pedido.
