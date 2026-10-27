---
name: gemini-git-guardian
trigger: model_decision
description: "GuardiÃ¡n de Git, Pre-Commit Hooks y CI/CD Sentinel. Protege tus repositorios desde VS Code, IntelliJ, Android Studio o terminal. Bloquea automÃ¡ticamente commits o pushes con API keys expuestas (Stripe, OpenAI, AWS), archivos .env sin ignorar, o consultas SQL destructivas tipo DELETE FROM tabla; sin WHERE que borren la base de datos."
---

# Git Guardian Sentinel (ProtecciÃ³n Pre-Commit & Pre-Push)

Esta habilidad actÃºa como un **guardiÃ¡n local de Git** para que, sin importar desde dÃ³nde programes (VS Code, IntelliJ IDEA, Android Studio o la consola), **sea fÃ­sicamente imposible hacer un commit o un push que contenga API keys expuestas o consultas SQL suicidas**.

---

## 1. QuÃ© Amenazas Bloquea FÃ­sicamente

1. **Secretos y API Keys Expuestas:**
   - Detecta patrones de tokens de OpenAI (`sk-...`), Stripe (`sk_live_...`), AWS (`AKIA...`), GitHub tokens (`ghp_...`), URLs con credenciales y llaves privadas RSA.
2. **Archivos `.env` en Staging:**
   - Si alguien intenta hacer commit de un archivo `.env` o `.env.local` por descuido, el hook aborta la operaciÃ³n de inmediato.
3. **El clÃ¡sico "DELETE FROM tabla;" sin WHERE (Error Fatal de BD):**
   - Detecta si un desarrollador puso un punto y coma `;` justo despuÃ©s del nombre de la tabla (ej. `DELETE FROM usuarios; WHERE id = 1`), lo que vaciarÃ­a la base de datos entera al ejecutar la migraciÃ³n o el script.

---

## 2. CÃ³mo Instalar el GuardiÃ¡n en Cualquier Repositorio

Para activar el escudo en tu proyecto actual (sirve para VS Code, IntelliJ, Android Studio, etc.):

Solo tienes que pedirle al agente:
> *"Instala el Git Guardian en este proyecto"*

El agente copiarÃ¡ el script de seguridad en `.git/hooks/pre-commit`:
```bash
# Copia automÃ¡tica del hook
cp "<skill>/scripts/pre-commit-hook.sh" ".git/hooks/pre-commit"
chmod +x ".git/hooks/pre-commit"
```

A partir de ese segundo:
- Si tÃº o cualquier miembro del equipo intenta commitear una clave secreta o un `DELETE` suicida desde **IntelliJ, Android Studio o VS Code**:
- Git **abortarÃ¡ el commit al instante** mostrando una alerta roja en la consola y no dejarÃ¡ avanzar hasta que se retire el fallo.

---

## 3. Plantilla de GitHub Actions para el Equipo (Pull Requests)

Para protegerte como jefe de proyecto cuando otros desarrolladores hagan Push o creen una Pull Request a tu repositorio:

El agente puede generar un workflow de GitHub Actions en `.github/workflows/guardian-ci.yml`:
- Escanea automÃ¡ticamente cada PR entrante.
- Bloquea el botÃ³n de "Merge" si la rama de algÃºn compaÃ±ero expuso claves o consultas destructivas.

