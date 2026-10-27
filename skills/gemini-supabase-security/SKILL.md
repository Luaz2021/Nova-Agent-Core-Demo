---
name: gemini-supabase-security
trigger: model_decision
description: "Auditoria defensiva y bastionado de proyectos con Supabase y PostgreSQL. Aplica politicas estrictas de Row Level Security (RLS), prevencion de fugas en Storage Buckets, aislamiento de claves de API (anon vs service_role) y proteccion contra bypass de autenticacion."
---

# Supabase Security & RLS Defense Standards

Esta habilidad establece las reglas obligatorias de seguridad y control de acceso para cualquier proyecto construido sobre Supabase y PostgreSQL. Protege la base de datos contra accesos no autorizados, fugas de informacion y configuraciones inseguras de API.

---

## 1. Principio Zero-Trust para Row Level Security (RLS)

1. **Habilitacion Obligatoria en Cada Tabla:**
   - Toda tabla creada o modificada en el esquema `public` debe tener RLS habilitado explicitamente.
   ```sql
   ALTER TABLE public.reservas ENABLE ROW LEVEL SECURITY;
   ```
   - Ninguna tabla con datos de usuarios o negocio puede quedar sin politicas activas.
2. **Politicas Granulares por Operacion:**
   - Evitar politicas genericas `FOR ALL`. Declarar reglas atomicas independientes para `SELECT`, `INSERT`, `UPDATE` y `DELETE`.
   ```sql
   -- Lectura restringida al propio usuario o anfitrion autorizado
   CREATE POLICY "Usuarios ven sus propias reservas"
   ON public.reservas
   FOR SELECT
   USING (auth.uid() = usuario_id);

   -- Insercion verificada con uid autenticado
   CREATE POLICY "Usuarios autenticados crean reservas"
   ON public.reservas
   FOR INSERT
   WITH CHECK (auth.uid() = usuario_id);
   ```

---

## 2. Aislamiento de Credenciales y Llaves de API

1. **Anon Key vs Service Role Key:**
   - La `anon_key` (publicable) solo accede a lo que las politicas RLS permiten.
   - La `service_role_key` tiene permisos de superusuario y omite RLS por completo. Esta terminantemente prohibido incluirla en el cliente frontend o en variables con prefijos publicos (`NEXT_PUBLIC_` o `EXPO_PUBLIC_`).
   - El uso de `service_role` queda confinado a funciones de servidor seguras (Server Actions de Next.js, API routes o Edge Functions protegidas).

---

## 3. Bastionado de Storage Buckets

1. **Visibilidad de Buckets:**
   - Los buckets que contienen documentos de identidad, comprobantes de pago o fotos de registro de huespedes deben ser estrictamente privados (`public: false`).
2. **Descargas Seguras mediante URLs Firmadas:**
   - En lugar de servir archivos por URL estatica publica, generar Signed URLs temporales con expiracion corta (maximo 60 segundos) tras validar la identidad del usuario que la solicita:
   ```typescript
   const { data, error } = await supabase.storage
     .from('documentos-privados')
     .createSignedUrl('checkin/id_foto.jpg', 60);
   ```

---

## 4. Tipado Fuerte y Esquema Blindado

- **Generacion Automatizada de Tipos:**
  - Extraer los tipos TypeScript directamente de la base de datos con `supabase gen types typescript` y usarlos en cada llamada al cliente Supabase.
  - No usar `any` ni saltarse los tipos generados para consultas a tablas.
- **Proteccion contra Inyeccion SQL:**
  - Emplear siempre los constructores de consulta del SDK de Supabase (`.select()`, `.eq()`, `.filter()`).
  - Si se ejecutan funciones RPC o SQL directo, parametrizar siempre los argumentos evitando concatenaciones de cadenas.
