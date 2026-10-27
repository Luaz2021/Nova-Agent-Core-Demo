---
trigger: model_decision
description: "Aplica estas reglas estrictas de arquitectura limpia, separaciÃ³n de capas (Domain, Service, Repository, Controller) y patrones de diseÃ±o siempre que se cree o refactorice cÃ³digo backend."
---

# Clean Architecture & Design Patterns Enforcement

## 1. Reglas Inquebrantables de Capas
- **Capa Domain / Core:** Cero dependencias externas (nada de Spring, nada de frameworks web, solo lÃ³gica de negocio pura).
- **Capa Service:** OrquestaciÃ³n de casos de uso. Prohibido meter consultas SQL directas o lÃ³gica HTTP aquÃ­.
- **Capa Persistence / Repository:** Ãšnica capa con permiso para interactuar con bases de datos o mapeadores ORM.

## 2. Patrones Obligatorios segÃºn el Contexto
- Si manejas creaciÃ³n de objetos complejos con muchos parÃ¡metros opcionales $\rightarrow$ **Builder Pattern**.
- Si desacoplas la lÃ³gica de creaciÃ³n de objetos de su implementaciÃ³n concreta $\rightarrow$ **Factory Method / Strategy Pattern**.
- Si controlas peticiones repetidas o estados globales seguros $\rightarrow$ **Singleton controlado por InyecciÃ³n de Dependencias**.

## 3. Formato de Respuesta del Agente
Antes de escribir cÃ³digo, el agente debe desglosar en 3 lÃ­neas quÃ© patrÃ³n va a utilizar y por quÃ© respeta la inversiÃ³n de dependencias (SOLID).

