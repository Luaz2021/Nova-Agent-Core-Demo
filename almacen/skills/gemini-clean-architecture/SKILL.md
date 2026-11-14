---
name: gemini-clean-architecture
description: "Reglas de arquitectura limpia (Domain, Service, Repository, Controller), KISS y patrones backend en Java/Kotlin/Node."
trigger: model_decision
---

# Clean Architecture & Design Patterns Enforcement

## 1. Reglas Inquebrantables de Capas
- **Capa Domain / Core:** Cero dependencias externas (nada de Spring, nada de frameworks web, solo lógica de negocio pura).
- **Capa Service:** Orquestación de casos de uso. Prohibido meter consultas SQL directas o lógica HTTP aquí.
- **Capa Persistence / Repository:** Única capa con permiso para interactuar con bases de datos o mapeadores ORM.

## 2. Patrones Obligatorios según el Contexto
- Si manejas creación de objetos complejos con muchos parámetros opcionales $\rightarrow$ **Builder Pattern**.
- Si desacoplas la lógica de creación de objetos de su implementación concreta $\rightarrow$ **Factory Method / Strategy Pattern**.
- Si controlas peticiones repetidas o estados globales seguros $\rightarrow$ **Singleton controlado por Inyección de Dependencias**.

## 3. Formato de Respuesta del Agente
Antes de escribir código, el agente debe desglosar en 3 líneas qué patrón va a utilizar y por qué respeta la inversión de dependencias (SOLID).
