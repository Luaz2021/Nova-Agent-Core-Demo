---
name: gemini-git-guardian
description: "Guardian Git y Pre-Commit Hooks: bloquea commits con API keys expuestas, archivos .env o SQL DELETE sin WHERE."
trigger: model_decision
---

# Git Guardian Sentinel (Protección Pre-Commit & Pre-Push)

Esta habilidad actúa como un **guardián local de Git** para que, sin importar desde dónde programes (VS Code, IntelliJ IDEA, Android Studio o la consola), **sea físicamente imposible hacer un commit o un push que contenga API keys expuestas o consultas SQL suicidas**.

---

## 1. Qué Amenazas Bloquea Físicamente

1. **Secretos por Entropía de Shannon (Matemática Pura H >= 4.2 bits):**
   - No depende de prefijos fijos: calcula la aleatoriedad matemática de las cadenas de caracteres. Caza contraseñas de BD, secretos de JWT, tokens criptográficos y hashes privados aunque tengan nombres arbitrarios.
   - Patrones conocidos de rescate: OpenAI (`sk-...`), Stripe (`sk_live_...`), AWS (`AKIA...`), GitHub (`ghp_...`), URLs con credenciales embebidas y llaves privadas RSA/OpenSSH.
2. **Archivos `.env` en Staging:**
   - Si alguien intenta hacer commit de un archivo `.env` o `.env.local` por descuido, el hook aborta la operación de inmediato.
3. **El clásico "DELETE FROM tabla;" sin WHERE (Error Fatal de BD):**
   - Detecta si un desarrollador puso un punto y coma `;` justo después del nombre de la tabla (ej. `DELETE FROM usuarios; WHERE id = 1`), lo que vaciaría la base de datos entera al ejecutar la migración o el script.

---

## 2. Cómo Instalar el Guardián en Cualquier Repositorio

Para activar el escudo en tu proyecto actual (sirve para VS Code, IntelliJ, Android Studio, etc.):

Solo tienes que pedirle al agente:
> *"Instala el Git Guardian en este proyecto"*

El agente ejecuta el instalador físico universal:
```bash
python "<NOVA_HOME>\antigravity\scripts\security\install_git_guard.py"
```

Para auditar staging o repositorios sin commitear a 0 tokens:
```bash
python "<NOVA_HOME>\antigravity\scripts\security\entropy_secret_scanner.py" --staged
```

A partir de ese segundo:
- Si tú o cualquier miembro del equipo intenta commitear una clave secreta o un `DELETE` suicida desde **IntelliJ, Android Studio o VS Code**:
- Git **abortará el commit al instante** mostrando una alerta roja en la consola y no dejará avanzar hasta que se retire el fallo.

---

## 3. Plantilla de GitHub Actions para el Equipo (Pull Requests)

Para protegerte como jefe de proyecto cuando otros desarrolladores hagan Push o creen una Pull Request a tu repositorio:

El agente puede generar un workflow de GitHub Actions en `.github/workflows/guardian-ci.yml`:
- Escanea automáticamente cada PR entrante.
- Bloquea el botón de "Merge" si la rama de algún compañero expuso claves o consultas destructivas.

