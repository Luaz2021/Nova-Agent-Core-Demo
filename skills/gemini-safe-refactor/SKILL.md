---
name: gemini-safe-refactor
description: "Refactorizacion segura y diagnostico read-only de proyectos con plan de accion previo a tocar codigo."
trigger: model_decision
---

# Safe Plan & Refactor Protocol (Cero DestrucciÃ³n Inesperada)

Este protocolo protege tu base de cÃ³digo contra la tÃ­pica conducta de modelos como Claude o Codex que intentan reescribir la mitad del repositorio sin permiso. 

---

## 1. REGLA INQUEBRANTABLE: Prohibido Modificar sin Plan Aprobado

Cuando el usuario te entregue un proyecto existente y te pida analizarlo o buscar mejoras:
- **Modo 100% Read-Only:** EstÃ¡ estrictamente prohibido usar herramientas de ediciÃ³n (`edit_file` o `write_file`) antes de que el usuario apruebe un plan explÃ­cito.
- **Cero Sorpresas:** El agente nunca cambiarÃ¡ la arquitectura, librerÃ­as o estructura de archivos por su cuenta.

---

## 2. MetodologÃ­a de DiagnÃ³stico (3 Pasos)

### Paso 1: Escaneo y DetecciÃ³n de Puntos CrÃ­ticos
El agente inspecciona el repositorio buscando:
1. **Puntos CrÃ­ticos de Rendimiento:** Consultas pesadas, fugas de memoria o cuellos de botella.
2. **Deuda TÃ©cnica y Code Smells:** Funciones monolÃ­ticas (> 50 lÃ­neas), variables globales, duplicaciÃ³n y acoplamiento alto.
3. **Brechas de Seguridad:** Endpoints desprotegidos, inyecciones potenciales o manejo inseguro de errores.
4. **Falta de Tests:** Ãreas crÃ­ticas del negocio que no tienen cobertura de pruebas.

---

### Paso 2: Entrega del Plan de AcciÃ³n (Estructurado)
El agente presenta un diagnÃ³stico claro con opciones prioritarias:

```markdown
### ðŸ“‹ DiagnÃ³stico del Proyecto: [Nombre]
- **Estado General:** [Breve valoraciÃ³n tÃ©cnica]

#### ðŸ” Puntos CrÃ­ticos Identificados:
1. **[CrÃ­tico] [UbicaciÃ³n/Archivo]:** DescripciÃ³n concisa del riesgo y por quÃ© debe corregirse.
2. **[Medio] [UbicaciÃ³n/Archivo]:** Oportunidad de refactorizaciÃ³n o mejora de arquitectura.

#### ðŸ› ï¸ Propuesta de Plan de RefactorizaciÃ³n (Por Fases):
- **Fase 1 (Seguridad y Bugs):** [Archivos a tocar] -> [Cambio propuesto].
- **Fase 2 (Limpieza y CÃ³digo Corto):** [Archivos a tocar] -> [Cambio propuesto].

> *Â¿Con cuÃ¡l de estas fases o archivos especÃ­ficos empezamos? No tocarÃ© nada hasta que me confirmes.*
```

---

### Paso 3: EjecuciÃ³n QuirÃºrgica Aprobada
Una vez que el usuario diga: *"Cambiemos solo la Fase 1"* o *"Solo toca el servicio X"*:
- El agente aplica **parches quirÃºrgicos** Ãºnicamente a los archivos autorizados.
- Conserva el 100% de los comentarios existentes y convenciones del proyecto.
- Ejecuta las pruebas existentes para certificar que nada se rompiÃ³.

