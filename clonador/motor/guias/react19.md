# GUÍA DE VERSIÓN · React 19 (actual: 19.2) + Next.js

Escribe React 19. Lo que aprendiste es React 17/18: varias APIs ya no existen y hay formas nuevas de hacer formularios y datos.

## 1. Lo que ya NO se usa
| Antiguo (NO) | React 19 (SÍ) |
|---|---|
| `ReactDOM.render(<App/>, el)` | `createRoot(el).render(<App/>)` |
| `ReactDOM.hydrate` | `hydrateRoot(el, <App/>)` |
| `forwardRef((props, ref) => ...)` | `function Input({ ref, ...props })` (ref es una prop normal) |
| `<Contexto.Provider value={v}>` | `<Contexto value={v}>` |
| `propTypes`, `defaultProps` en funciones | TypeScript y valores por defecto: `function B({ talla = "m" })` |
| refs de texto `ref="input"` | `useRef` o ref como función |
| `useFormState` (react-dom) | `useActionState` (react) |
| `create-react-app` (abandonado) | Vite (`npm create vite@latest`) o un framework (Next.js) |
| `useMemo`/`useCallback` en todas partes | El React Compiler memoriza solo; úsalos solo si hace falta de verdad |
| `react-helmet` para el `<title>` | `<title>` y `<meta>` dentro del componente |

## 2. Formularios y Actions
```jsx
import { useActionState, useOptimistic } from "react";
import { useFormStatus } from "react-dom";

async function guardar(estadoPrevio, formData) {
  const nombre = formData.get("nombre");
  if (!nombre) return { error: "Falta el nombre" };
  await api.guardar(nombre);
  return { ok: true };
}

function Boton() { const { pending } = useFormStatus(); return <button disabled={pending}>{pending ? "Guardando…" : "Guardar"}</button>; }

export function Formulario() {
  const [estado, accion, pendiente] = useActionState(guardar, {});
  return (
    <form action={accion}>          {/* action recibe una función, no una URL */}
      <input name="nombre" />
      {estado.error && <p role="alert">{estado.error}</p>}
      <Boton />
    </form>
  );
}
```
`useOptimistic(lista, (actual, nuevo) => [...actual, nuevo])` muestra el cambio al instante mientras se guarda.

## 3. `use()`, Suspense y lo nuevo de 19.2
```jsx
import { use, Suspense, Activity, useEffectEvent } from "react";
function Comentarios({ promesa }) { const datos = use(promesa); return datos.map(c => <p key={c.id}>{c.texto}</p>); }
// <Suspense fallback={<Cargando/>}><Comentarios promesa={cargar()} /></Suspense>
// use() también lee contexto dentro de un if: if (x) { const tema = use(TemaContexto); }

<Activity mode={visible ? "visible" : "hidden"}><Pestana /></Activity>   // oculta sin perder el estado

const alConectar = useEffectEvent(() => avisar(tema));   // lee el valor actual sin re-ejecutar el efecto
useEffect(() => { const c = conectar(sala); c.on("ok", alConectar); return () => c.close(); }, [sala]);
```
Las refs como función pueden devolver una limpieza: `ref={(el) => { observar(el); return () => dejar(el); }}`.

## 4. Next.js actual (App Router)
- Carpeta `app/`: `app/page.tsx`, `app/layout.tsx`, `app/blog/[slug]/page.tsx`. El antiguo `pages/` y `getServerSideProps`/`getStaticProps` son lo viejo.
- Los componentes son de **servidor** por defecto: pueden ser `async` y leer la base de datos directamente. Para estado o eventos, la primera línea del archivo es `"use client"`.
- Server Actions: una función con `"use server"` que se pasa a `<form action={...}>`.
- `params` y `searchParams` son promesas: `const { slug } = await params;`.
- Datos: `fetch` en el componente de servidor; la caché se activa a propósito con `"use cache"` (no se cachea todo por defecto).
- Turbopack es el empaquetador por defecto. En Next 16 el archivo `middleware.ts` pasa a llamarse `proxy.ts`.
- Imágenes con `next/image`, enlaces con `next/link` (sin `<a>` dentro).

```tsx
// app/productos/[id]/page.tsx  (servidor)
export default async function Pagina({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = await db.producto.find(id);
  return <main><title>{p.nombre}</title><h1>{p.nombre}</h1><BotonComprar id={id} /></main>;
}
```

## 5. Errores típicos de un modelo con React viejo
1. `ReactDOM.render` o `create-react-app`.
2. `forwardRef` y `Contexto.Provider` innecesarios.
3. `useEffect` + `useState` + `fetch` para cargar datos en Next → componente de servidor `async`.
4. `"use client"` en todos los archivos.
5. `pages/` y `getServerSideProps` en proyectos nuevos.
6. Olvidar `await params`.
7. Llenar el código de `useMemo`/`useCallback` "por si acaso".
