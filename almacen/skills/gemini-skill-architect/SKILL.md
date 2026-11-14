---
name: gemini-skill-architect
description: "Diseña y empaqueta nuevas skills con frontmatter YAML estandar y progressive disclosure previa confirmacion."
trigger: model_decision
---

# Skill Creator (Antigravity & Gemini Skills Architect)

Esta meta-habilidad permite al asistente detectar cuándo un flujo de trabajo, procedimiento recurrente o conjunto de reglas especializadas merece convertirse en una **nueva habilidad permanente** para el sistema.

---

## 1. REGLA INQUEBRANTABLE: Transparencia y Consentimiento del Usuario

El asistente **NUNCA** creará una skill de forma silenciosa u oculta. 
Antes de escribir cualquier archivo en `<NOVA_HOME>ntigravitylmacen\skills\`:

1. **Avisar al usuario explícitamente:**
   - Explicar qué patrón recurrente se ha detectado.
   - Proponer el nombre de la nueva skill (ej. `database-migrator`, `tdd-enforcer`).
   - Resumir en 2 viñetas qué reglas o automatizaciones contendrá.
2. **Solicitar confirmación:** Esperar a que el usuario diga *"sí, créala"* o dé el visto bueno antes de proceder.

---

## 2. Anatomía Obligatoria de una Skill para Gemini / Antigravity

Cada nueva skill se almacena en `<NOVA_HOME>ntigravitylmacen\skills\<nombre-skill>/` y debe contener:

### A. Frontmatter YAML Estricto en `SKILL.md`:
```markdown
---
name: gemini-skill-architect
trigger: model_decision
description: "Descripción precisa de qué hace la habilidad y CUÁNDO debe activarse. Incluir palabras clave y frases que el usuario suele decir para activarla sin sobre-activaciones accidentales."
---
```

### B. Carga Progresiva (Progressive Disclosure):
- El archivo `SKILL.md` principal debe ser conciso y operativo (< 500 líneas).
- Si la skill requiere tablas de datos gigantescas, documentación de terceros o scripts auxiliares, se deben colocar en subcarpetas:
  - `references/`: Guías de consulta profunda que el modelo solo lee cuando sea estrictamente necesario.
  - `scripts/`: Herramientas ejecutables (Node, Python, Bash/PowerShell).

---

## 3. Protocolo de Creación

1. **Identificar la Necesidad:**
   - ¿El usuario pide un procedimiento especializado que se va a repetir a menudo?
   - ¿Hay un manual de buenas prácticas que el usuario siempre exige en sus proyectos?
2. **Estructurar la Lógica:**
   - Desglosar la habilidad en directrices accionables, ejemplos de "Antes vs Después", y comandos claros.
3. **Escritura y Sincronización:**
   - Escribir `SKILL.md` en `<NOVA_HOME>ntigravitylmacen\skills\<nombre-skill>/SKILL.md`.
   - Sincronizar la copia local en `~/.gemini/antigravity/skills/<nombre-skill>/`.
4. **Verificación:** Confirmar al usuario que la skill ya está disponible para ambas máquinas (PC y Laptop).

---

## 4. Interceptor API/CLI First
Queda terminantemente prohibido disenar automatizaciones basadas en navegadores (Playwright/Puppeteer/DOM) o simulacion de clics sin verificar previamente si existe:
1. API oficial gratuita o endpoint REST documentado.
2. Comandos CLI o binarios nativos del sistema operativo (`yt-dlp`, `curl`, `gh`, `winget`).
Si existe alternativa por API o CLI, la skill debe priorizarla para operar a Nivel 0 (0 tokens y minima latencia).

---

## 5. Auto-Parcheo desde Napkin
Cuando una skill existente provoque un fallo recurrente que obligue a una intervencion correctiva o rescate de Claude:
- `gemini-skill-architect` debe actualizar el `SKILL.md` de la skill afectada inyectando la regla preventiva en formato:
  `[Sintoma] -> [Causa Raiz] -> [Do Instead]`
- Registrar el incidente en `memory/napkin.md` para evitar repetir el error en sesiones posteriores.

