---
name: gemini-skill-architect
trigger: model_decision
description: "Meta-habilidad oficial de creaciÃ³n y evoluciÃ³n de habilidades (skill-creator de Anthropic adaptada a Gemini/Antigravity). DiseÃ±a, redacta y empaqueta nuevas skills con frontmatter YAML estÃ¡ndar, pautas de activaciÃ³n y progressive disclosure. Requiere SIEMPRE avisar y pedir confirmaciÃ³n al usuario antes de crear una skill."
---

# Skill Creator (Antigravity & Gemini Skills Architect)

Esta meta-habilidad permite al asistente detectar cuÃ¡ndo un flujo de trabajo, procedimiento recurrente o conjunto de reglas especializadas merece convertirse en una **nueva habilidad permanente** para el sistema.

---

## 1. REGLA INQUEBRANTABLE: Transparencia y Consentimiento del Usuario

El asistente **NUNCA** crearÃ¡ una skill de forma silenciosa u oculta. 
Antes de escribir cualquier archivo en `G:\Mi unidad\Antigravity\skills/`:

1. **Avisar al usuario explÃ­citamente:**
   - Explicar quÃ© patrÃ³n recurrente se ha detectado.
   - Proponer el nombre de la nueva skill (ej. `database-migrator`, `tdd-enforcer`).
   - Resumir en 2 viÃ±etas quÃ© reglas o automatizaciones contendrÃ¡.
2. **Solicitar confirmaciÃ³n:** Esperar a que el usuario diga *"sÃ­, crÃ©ala"* o dÃ© el visto bueno antes de proceder.

---

## 2. AnatomÃ­a Obligatoria de una Skill para Gemini / Antigravity

Cada nueva skill se almacena en `G:\Mi unidad\Antigravity\skills/<nombre-skill>/` y debe contener:

### A. Frontmatter YAML Estricto en `SKILL.md`:
```markdown
---
name: gemini-skill-architect
trigger: model_decision
description: "DescripciÃ³n precisa de quÃ© hace la habilidad y CUÃNDO debe activarse. Incluir palabras clave y frases que el usuario suele decir para activarla sin sobre-activaciones accidentales."
---
```

### B. Carga Progresiva (Progressive Disclosure):
- El archivo `SKILL.md` principal debe ser conciso y operativo (< 500 lÃ­neas).
- Si la skill requiere tablas de datos gigantescas, documentaciÃ³n de terceros o scripts auxiliares, se deben colocar en subcarpetas:
  - `references/`: GuÃ­as de consulta profunda que el modelo solo lee cuando sea estrictamente necesario.
  - `scripts/`: Herramientas ejecutables (Node, Python, Bash/PowerShell).

---

## 3. Protocolo de CreaciÃ³n

1. **Identificar la Necesidad:**
   - Â¿El usuario pide un procedimiento especializado que se va a repetir a menudo?
   - Â¿Hay un manual de buenas prÃ¡cticas que el usuario siempre exige en sus proyectos?
2. **Estructurar la LÃ³gica:**
   - Desglosar la habilidad en directrices accionables, ejemplos de "Antes vs DespuÃ©s", y comandos claros.
3. **Escritura y SincronizaciÃ³n:**
   - Escribir `SKILL.md` en `G:\Mi unidad\Antigravity\skills/<nombre-skill>/SKILL.md`.
   - Sincronizar la copia local en `~/.gemini/antigravity/skills/<nombre-skill>/`.
4. **VerificaciÃ³n:** Confirmar al usuario que la skill ya estÃ¡ disponible para ambas mÃ¡quinas (PC y Laptop).

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

