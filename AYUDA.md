# Guia Rapida de Comandos y Atajos · NOVA Copilot Engine
*Arquitectura creada por Saul Alexander Martinez Rivas (@Luaz2021) · Lectura estatica a 0 tokens de generacion*

```text
==========================================================================
   NOVA COPILOT ENGINE - BIENVENIDA Y MAPA DE COMANDOS (125 SKILLS)
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
| `Nova, configura el sync` | **Nova Sync (varios equipos):** te guia paso a paso. Si no tienes Google Drive para escritorio te da el enlace oficial; luego crea la carpeta `Nova_Sync` en tu Drive (te pide permiso) y hace la primera pasada. En el 2o equipo deja tu Nova igual que la del 1o. Windows y Mac (Linux: con rclone). |
| `Nova, sincroniza` | **Baja** de Drive lo nuevo. Nunca escribe en Drive. Si un archivo cambio en los dos equipos gana Drive y el tuyo queda al lado como `*.local-*`. En Windows corre solo al abrir Antigravity. |
| `Nova, sube los cambios` | **Sube** a Drive lo que cambiaste aqui (lo UNICO que escribe en Drive). Si otro equipo subio algo mas nuevo, ese archivo queda bloqueado hasta que sincronices. En Windows corre solo al cerrar Antigravity. |
| `Nova, deja este equipo igual que Drive` | **Espejo:** guarda una copia de lo distinto y deja este equipo identico a Drive (para un equipo desordenado). |
| `Nova` (en voz alta, Windows) | **Nova Voz Live:** dices "Nova" y hablas normal; te pregunta lo que falte y le pasa el encargo a Nova en Antigravity. Te avisa hablando al terminar y te pregunta los permisos por voz. Necesita `GEMINI_API_KEY` (gratis en AI Studio). El **monito flotante** va fuera de Antigravity: arrastralo donde quieras; clic derecho para apagar la voz. Se esconde con juegos a pantalla completa. |
| `Nova, instala tu voz` | **Pack de voz (opcional):** Ayla (voz de Nova) y Marina (guardian y videos), generadas en tu equipo. Windows/Linux con GPU NVIDIA o Mac con chip Apple. Escribe en el chat *acepto la licencia de las voces* (`LICENCIA_VOCES.md`: solo para uso dentro de Nova) y Nova la instala. A mano en Windows: `powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.gemini\antigravity\herramientas\voz_clon\instalar.ps1"`; Mac/Linux: `sh ~/.gemini/antigravity/herramientas/voz_clon/instalar.sh` (y escribes ACEPTO). |
| `Nova, revisate` | **Nova Doctor:** revisa y repara la instalacion (carpetas, skills, reglas automaticas, librerias, navegador). |
| `/destilar` | Con Claude o Argon: pasa el inbox de lecciones y `mis_quejas.md` a las secciones Trampas / Definicion de hecho de cada indice y vacia el inbox. |
| `/keys` o `configurar llaves` | Despliega la guia paso a paso para activar el Router Multi-Modelo y herramientas a 0 EUR. |
| `buenos dias` / `que tenemos pendiente` | Entrega el resumen ejecutivo matutino de proyectos activos y tareas abiertas. |

---

## 2. Atajos de Ingenieria, Proyectos y Auditoria
| Atajo / Frase en el Chat | Flujo que Activa |
| :--- | :--- |
| `Nuevo proyecto: [idea]` / `Planifiquemos el Sprint [X]` | Bloquea escritura de codigo, lanza de 3 a 5 preguntas quirurgicas (*Grill-Me*) y arma el tablero en `memory\tasks.md`. |
| `Nova analiza este proyecto: [ruta]` | Triaje Read-Only en 60s y entrega del **Reporte Tanque de 7 Puntos** (Stack, UI Anti-Slop, a11y, SEO, Legal/RGPD, Ciberseguridad y Deploy 0 EUR). |
| `te lo dejo en tus manos` | Activa el modo autonomo: ejecucion `1-Shot` consolidada, `unittest` en verde, Chaos QA y reporte final. |
| `/director hazme una app de [idea]` (v3.3) | NOVA DIRECTOR: planos -> obra por fases -> inspeccion, sin ventanas y con tope de gasto. Pausa y te pregunta si falta algo. Necesita la CLI `agy`. |
| `hazlo tu` / `te doy permiso` (v3.3) | Modo ENCARGO (trabaja sola en su zona) / permiso para tocar lo protegido en ESTE mensaje (con copia). Los hooks, reglas y el Doctor nunca. |
| `¿seguro?` / `/verifica` (v3.3) | Nova lo comprueba antes de responder y contesta en modo profe (OK / NO / En parte + como comprobarlo tu). |
| `desglosa este proyecto [ruta]` (v3.3) | Radiografia del proyecto (piezas, dependencias, ciclos, codigo muerto). La 1a vez Nova te ofrece instalar el programa. |
| `/backend` `/web` `/consola` `/video` `/redacta` `/investiga` (v3.3) | Fuerza el carril de ese tema: Nova lee su kit corto antes de escribir. |

---

## 3. Linea Directa con el Creador (Saul Alexander Martinez Rivas)
| Atajo Comunitario / Frase | Que hace Nova por detras (Sanitizado y Seguro) |
| :--- | :--- |
| `/creador [mensaje]` o *"mandale un mensaje al creador: ..."* | Pasa el texto por `scripts/enviar_feedback.py` (borra rutas privadas, IPs y claves) y lo envia al buzon oficial en GitHub (`Luaz2021/Nova-Agent-Core-Demo`, etiqueta `buzon-creador`) via `gh issue create` o enlace directo en 1 clic. |
| `/reportar-fallo` o *"reportar error al creador"* | Empaqueta el fallo resuelto bajo formato Servilleta (`[SO] -> [Error] -> [Fix]`) sin datos privados y lo envia con etiqueta `napkin-crowd`. |
| `/compartir-skill [nombre]` | Empaqueta un `SKILL.md` creado o mejorado por el usuario y lo propone al Core oficial con etiqueta `skill-comunitaria` para revision y creditos de autor. |
| `/enviar-informe` | Prepara el informe de aprendizaje (SOLO lecciones, servilleta nueva y TIPO de errores; sin rutas, correos ni claves) en `memory/informe_para_enviar.md`. Lo revisas, borras lo que quieras y, si dices que si, abre el formulario de GitHub (etiqueta `informe-uso`). Si aceptaste al instalar, Nova te lo propone una vez al mes. |
| `/actualizar-nova` o *"Nova, busca actualizaciones"* / *"Nova, ¿hay actualizaciones?"* | Ejecuta `actualizar_nova.py` con backup preventivo, descarga skills/scripts nuevos y el Napkin oficial de Saul (`napkin_oficial.md`) sin tocar tus notas personales ni tareas. |
| *(Exclusivo Saul)* `revisa el buzon de la comunidad` | Escanea los issues recibidos (`buzon-creador`, `napkin-crowd`, `skill-comunitaria`), aplica el filtro forense de 4 puntos (KISS, Seguridad, SO, Originalidad) y presenta el resumen listo para aprobar. |

---

## 4. Motores Especializados (Activacion Automatica por Contexto)
- **Web, UI & Animaciones:** Estilo Stripe/Linear/Awwwards (`gemini-ui-artisan`), coreografias GSAP (`gsap-*`), 3D (`threejs-web-experience`) y Core Web Vitals (`gemini-webperf`).
- **Branding & Manuales VI:** Creacion de marca (`brand-design`, manual HTML de 21 capitulos), `brand.md` y catalogo de 156 marcas globales (`gemini-brand-tokens`).
- **Instagram & Video en Codigo:** Suite Instagram 2026 (`ig-content-planner`, `ig-hook-extractor`, `ig-carousel-planner`, `ig-caption-writer`, `ig-humanizer`) y video en React (`remotion-video-agent`).
- **Backend, BaaS & Seguridad:** Arquitectura limpia (`gemini-clean-architecture`), PostgreSQL/Supabase con RLS (`gemini-supabase-security`) y auditoria STRIDE/OWASP (`gemini-security-bastion`).
- **Redes & Hardware:** Topologias Cisco CCNA/Packet Tracer (`cisco-network-architect`) y robotica Arduino/ESP32 (`embedded-robotics-maker`).
