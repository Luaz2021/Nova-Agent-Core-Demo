# Guia Rapida de Comandos y Atajos · NOVA Copilot Engine
*Arquitectura creada por Saul Alexander Martinez Rivas (@Luaz2021) · Lectura estatica a 0 tokens de generacion*

```text
==========================================================================
   NOVA COPILOT ENGINE - BIENVENIDA Y MAPA DE COMANDOS (119 SKILLS)
   Creado por Saul Alexander Martinez Rivas (@Luaz2021)
==========================================================================
¡Hola! Soy Nova, tu copiloto tecnica y arquitecta de trinchera en Antigravity.
Reglas base: Cero servilismo, codigo limpio (KISS), cero experimentos en vivo
sobre tu rama activa y permiso primero antes de tocar tu terminal.
==========================================================================
```

---

## 1. Atajos de Sesion y Memoria Persistente
| Atajo / Frase en el Chat | Accion Automatica de Nova |
| :--- | :--- |
| `hola` / `continuamos` / `seguimos` | Lee el puente de sesion y `tasks.md` y retoma exactamente en la ultima frase respondiendo en 2-3 lineas ejecutivas. |
| `/ayuda` o `ayuda` | Muestra este archivo estatico completo sin gastar tokens de salida (`6.0x`) redactando desde cero. |
| /keys o configurar llaves | Despliega la guia paso a paso para activar el Router Multi-Modelo y herramientas a 0 EUR. |
| `buenos dias` / `que tenemos pendiente` | Entrega el resumen ejecutivo matutino de proyectos activos y tareas abiertas. |

---

## 2. Atajos de Ingenieria, Proyectos y Auditoria
| Atajo / Frase en el Chat | Flujo que Activa |
| :--- | :--- |
| `Nuevo proyecto: [idea]` / `Planifiquemos el Sprint [X]` | Bloquea escritura de codigo, lanza de 3 a 5 preguntas quirurgicas (*Grill-Me*) y arma el tablero en `memory\tasks.md`. |
| `Nova analiza este proyecto: [ruta]` | Triaje Read-Only en 60s y entrega del **Reporte Tanque de 7 Puntos** (Stack, UI Anti-Slop, a11y, SEO, Legal/RGPD, Ciberseguridad y Deploy 0 EUR). |
| `te lo dejo en tus manos` | Activa el modo autonomo: ejecucion `1-Shot` consolidada, `unittest` en verde, Chaos QA y reporte final. |

---

## 3. Linea Directa con el Creador (Saul Alexander Martinez Rivas)
| Atajo Comunitario / Frase | Que hace Nova por detras (Sanitizado y Seguro) |
| :--- | :--- |
| `/creador [mensaje]` o *"mandale un mensaje al creador: ..."* | Pasa el texto por `feedback_sanitizer.py` (borra rutas privadas o claves) y lo envia al buzon oficial en GitHub (`Luaz2021/Nova-Agent-Core-Demo`, etiqueta `buzon-creador`) via `gh issue create` o enlace directo en 1 clic. |
| `/reportar-fallo` o *"reportar error al creador"* | Empaqueta el fallo resuelto bajo formato Servilleta (`[SO] -> [Error] -> [Fix]`) sin datos privados y lo envia con etiqueta `napkin-crowd`. |
| `/compartir-skill [nombre]` | Empaqueta un `SKILL.md` creado o mejorado por el usuario y lo propone al Core oficial con etiqueta `skill-comunitaria` para revision y creditos de autor. |
| `/actualizar-nova` | Compara el `manifest_master.json` local contra el repositorio oficial de Saul en GitHub y descarga mejoras sin tocar la memoria privada del usuario. |
| *(Exclusivo Saul)* `revisa el buzon de la comunidad` | Escanea los issues recibidos (`buzon-creador`, `napkin-crowd`, `skill-comunitaria`), aplica el filtro forense de 4 puntos (KISS, Seguridad, SO, Originalidad) y presenta el resumen listo para aprobar. |

---

## 4. Motores Especializados (Activacion Automatica por Contexto)
- **Web, UI & Animaciones:** Estilo Stripe/Linear/Awwwards (`gemini-ui-artisan`), coreografias GSAP (`gsap-*`), 3D (`threejs-web-experience`) y Core Web Vitals (`gemini-webperf`).
- **Branding & Manuales VI:** Creacion de marca (`brand-design`, manual HTML de 21 capitulos), `brand.md` y catalogo de 156 marcas globales (`gemini-brand-tokens`).
- **Instagram & Video en Codigo:** Suite Instagram 2026 (`ig-content-planner`, `ig-hook-extractor`, `ig-carousel-planner`, `ig-caption-writer`, `ig-humanizer`) y video en React (`remotion-video-agent`).
- **Backend, BaaS & Seguridad:** Arquitectura limpia (`gemini-clean-architecture`), PostgreSQL/Supabase con RLS (`gemini-supabase-security`) y auditoria STRIDE/OWASP (`gemini-security-bastion`).
- **Redes & Hardware:** Topologias Cisco CCNA/Packet Tracer (`cisco-network-architect`) y robotica Arduino/ESP32 (`embedded-robotics-maker`).
