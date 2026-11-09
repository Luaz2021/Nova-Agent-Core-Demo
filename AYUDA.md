# Guia Rapida de Comandos y Atajos · NOVA Copilot Engine
*Arquitectura creada por Saul Alexander Martinez Rivas (@Luaz2021) · Lectura estatica a 0 tokens de generacion*

```text
==========================================================================
   NOVA COPILOT ENGINE - BIENVENIDA Y MAPA DE COMANDOS (145 SKILLS)
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
| `/creador [mensaje]` o *"mandale un mensaje al creador: ..."* | Pasa el texto por `enviar_feedback.py` (borra rutas privadas, correos y claves) y abre el formulario del buzon oficial en GitHub (`Luaz2021/Nova-Agent-Core-Demo`, etiqueta `buzon-creador`); tu decides si lo envias. |
| `/reportar-fallo` o *"reportar error al creador"* | Empaqueta el fallo resuelto bajo formato Servilleta (`[SO] -> [Error] -> [Fix]`) sin datos privados y abre el formulario con etiquetas `fix-esquivado` y `napkin`. |
| `/compartir-skill [nombre]` | Empaqueta un `SKILL.md` creado o mejorado por el usuario y lo propone al Core oficial con etiqueta `skill-comunitaria` para revision y creditos de autor. |
| `/enviar-informe` | Prepara un informe SOLO con las lecciones de autoaprendizaje, las entradas nuevas de tu servilleta y el tipo de errores de Nova (nada de tu equipo, proyectos, rutas ni claves). Lo revisas y decides si lo envias. |
| *"Nova, instala la IA local"* | Instala Ollama si falta y descarga qwen3.5 + InternVL3.5 segun tu equipo (0 tokens de nube despues). |
| *"Nova, configura mis claves"* | Te indica el comando `nova_claves.py` para poner tus claves gratis en tu equipo (nunca en el chat). |
| `/actualizar-nova` o *"Nova, busca actualizaciones"* / *"Nova, ¿hay actualizaciones?"* | Ejecuta `actualizar_nova.py` con backup preventivo, compara archivo por archivo (SHA-256), descarga solo lo que cambio y el Napkin oficial de Saul (`napkin_oficial.md`) sin tocar tus notas personales ni tareas. |
| *(Exclusivo Saul)* `revisa el buzon de la comunidad` | Escanea los issues recibidos (`buzon-creador`, `napkin`, `skill-comunitaria`, `informe-uso`), aplica el filtro forense de 4 puntos (KISS, Seguridad, SO, Originalidad) y presenta el resumen listo para aprobar. |

---

## 4. Motores Especializados (Activacion Automatica por Contexto)
- **Web, UI & Animaciones:** Estilo Stripe/Linear/Awwwards (`gemini-ui-artisan`), coreografias GSAP (`gsap-*`), 3D (`threejs-web-experience`) y Core Web Vitals (`gemini-webperf`).
- **Branding & Manuales VI:** Creacion de marca (`brand-design`, manual HTML de 21 capitulos), `brand.md` y catalogo de 156 marcas globales (`gemini-brand-tokens`).
- **Instagram & Video en Codigo:** Suite Instagram 2026 (`ig-content-planner`, `ig-hook-extractor`, `ig-carousel-planner`, `ig-caption-writer`, `ig-humanizer`) y video en React (`remotion-video-agent`).
- **Backend, BaaS & Seguridad:** Arquitectura limpia (`gemini-clean-architecture`), PostgreSQL/Supabase con RLS (`gemini-supabase-security`) y auditoria STRIDE/OWASP (`gemini-security-bastion`).
- **Redes & Hardware:** Topologias Cisco CCNA/Packet Tracer (`cisco-network-architect`) y robotica Arduino/ESP32 (`embedded-robotics-maker`).
