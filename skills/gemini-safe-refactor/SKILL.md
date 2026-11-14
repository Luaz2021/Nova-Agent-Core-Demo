---
name: gemini-safe-refactor
description: "Refactorizacion segura y diagnostico read-only de proyectos con plan de accion previo a tocar codigo."
trigger: model_decision
---

# Safe Plan & Refactor Protocol (Cero Destrucción Inesperada)

Este protocolo protege tu base de código contra la típica conducta de modelos como Claude o Codex que intentan reescribir la mitad del repositorio sin permiso. 

---

## 1. REGLA INQUEBRANTABLE: Prohibido Modificar sin Plan Aprobado

Cuando el usuario te entregue un proyecto existente y te pida analizarlo o buscar mejoras:
- **Modo 100% Read-Only:** Está estrictamente prohibido usar herramientas de edición (`edit_file` o `write_file`) antes de que el usuario apruebe un plan explícito.
- **Cero Sorpresas:** El agente nunca cambiará la arquitectura, librerías o estructura de archivos por su cuenta.

---

## 2. Metodología de Diagnóstico (3 Pasos)

### Paso 1: Escaneo y Detección de Puntos Críticos
El agente inspecciona el repositorio buscando:
1. **Puntos Críticos de Rendimiento:** Consultas pesadas, fugas de memoria o cuellos de botella.
2. **Deuda Técnica y Code Smells:** Funciones monolíticas (> 50 líneas), variables globales, duplicación y acoplamiento alto.
3. **Brechas de Seguridad:** Endpoints desprotegidos, inyecciones potenciales o manejo inseguro de errores.
4. **Falta de Tests:** Áreas críticas del negocio que no tienen cobertura de pruebas.

---

### Paso 2: Entrega del Plan de Acción (Estructurado)
El agente presenta un diagnóstico claro con opciones prioritarias:

```markdown
### 📋 Diagnóstico del Proyecto: [Nombre]
- **Estado General:** [Breve valoración técnica]

#### 🔍 Puntos Críticos Identificados:
1. **[Crítico] [Ubicación/Archivo]:** Descripción concisa del riesgo y por qué debe corregirse.
2. **[Medio] [Ubicación/Archivo]:** Oportunidad de refactorización o mejora de arquitectura.

#### 🛠️ Propuesta de Plan de Refactorización (Por Fases):
- **Fase 1 (Seguridad y Bugs):** [Archivos a tocar] -> [Cambio propuesto].
- **Fase 2 (Limpieza y Código Corto):** [Archivos a tocar] -> [Cambio propuesto].

> *¿Con cuál de estas fases o archivos específicos empezamos? No tocaré nada hasta que me confirmes.*
```

---

### Paso 3: Ejecución Quirúrgica Aprobada
Una vez que el usuario diga: *"Cambiemos solo la Fase 1"* o *"Solo toca el servicio X"*:
- El agente aplica **parches quirúrgicos** únicamente a los archivos autorizados.
- Conserva el 100% de los comentarios existentes y convenciones del proyecto.
- Ejecuta las pruebas existentes para certificar que nada se rompió.

