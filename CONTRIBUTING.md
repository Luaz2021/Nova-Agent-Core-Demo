# Guía de Contribución a Nova Agent

¡Gracias por tu interés en colaborar con **Nova Agent**! Este es un proyecto de código abierto construido con orgullo por y para la comunidad de desarrolladores enfocados en el ecosistema de **Google Gemini** y **Google Antigravity 2.0**.

---

## 🏛️ Filosofía de Ingeniería de Nova Agent

Toda contribución al núcleo o al árbol de skills debe respetar los tres principios sagrados:

1. **KISS Estricto (Keep It Simple, Stupid) & YAGNI:**
   - Código corto, legible a la primera, con *early returns*.
   - Prohibida la sobre-ingeniería innecesaria, los patrones abstractos vacíos o el relleno conversacional.
2. **100% Acoplado a las Fortalezas de Google Gemini:**
   - Skills diseñadas para aprovechar ventanas de contexto masivas (1M+ tokens) sin degradación.
   - Respeto del presupuesto de tokens: frontmatter YAML conciso, cero explicaciones redundantes.
3. **Cero Experimentos en Caliente:**
   - Los cambios deben validarse en ramas aisladas o sandboxes antes de tocar la rama principal.

---

## 🚀 Proyectos Prioritarios en Busca de Colaboradores

Buscamos activamente colaboradores para los siguientes frentes:

### 1. Proyecto Nova GUI (Frontend Dedicado)
- **Objetivo:** Crear una interfaz gráfica de usuario moderna, ligera y responsiva para interactuar con Nova Agent.
- **Stack Preferido:** 
  - **Flutter / Dart** (para mantener la alineación nativa con el stack de Google y compilación multiplataforma en Windows, Linux, macOS y Android).
  - Alternativamente: **Next.js / Tailwind** o **Tauri**.
- **Cómo conectarse:** Nova Agent expone comandos CLI vía `agy` y scripts de automatización local en `scripts/`.

### 2. Nuevas Skills Especializadas
- Creación de módulos `SKILL.md` con frontmatter YAML optimizado.
- Deben incluir directrices técnicas claras, condiciones de activación y ejemplos de código reales.

### 3. Adaptadores Multiplataforma
- Pruebas y mejoras en los instaladores `instalar_nova.sh` para distribuciones Linux (Ubuntu, Debian, Fedora, Arch) y macOS (Apple Silicon / Intel).

---

## 🛠️ Flujo de Trabajo para Contribuir

1. **Haz un Fork** del repositorio: [https://github.com/Luaz2021/Nova-Agent-Core-Demo](https://github.com/Luaz2021/Nova-Agent-Core-Demo).
2. **Crea una rama descriptiva** para tu feature:
   ```bash
   git checkout -b feature/nueva-skill-o-modulo
   ```
3. **Realiza tus cambios** manteniendo el estilo y documentación limpia (cero emojis en código fuente interno).
4. **Comprueba la integridad:**
   - Si añades o modificas componentes del núcleo, actualiza o valida el archivo `manifest_master.json`.
5. **Abre un Pull Request** explicando claramente:
   - Qué problema resuelve.
   - Qué pruebas realizaste.
   - Qué impacto tiene en el consumo de tokens.

---

## 📜 Licencia y Atribución

Al contribuir a Nova Agent, aceptas que tus contribuciones se distribuyan bajo la **Licencia MIT con Cláusula de Atribución**. Respetamos y acreditamos públicamente a cada colaborador en la lista oficial de agradecimientos.
