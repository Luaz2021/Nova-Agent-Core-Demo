---
name: gemini-cloud-sync
trigger: model_decision
description: "Motor de sincronizaciÃ³n automÃ¡tica entre PC y Laptop. Se activa cuando el usuario dice 'sincroniza', 'sincroniza todo', 'sincronizar laptop' o 'actualiza desde la nube'. Enlaza las skills de Google Drive, activa el ecosistema multi-agente, la memoria persistente y configura el Git Guardian global en la mÃ¡quina."
---

# Cloud Sync Engine (Un Solo Clic: "Sincroniza")

Esta habilidad automatiza por completo la puesta a punto de tu entorno. Cuando estÃ©s en tu laptop (o en cualquier mÃ¡quina nueva con Google Drive instalado) y digas **"sincroniza"**, el agente ejecutarÃ¡ todo el protocolo sin que tengas que acordarte de comandos ni rutas.

---

## 1. CuÃ¡ndo se Activa

El agente activarÃ¡ este procedimiento cuando el usuario diga:
- *"sincroniza"*
- *"sincroniza todo"*
- *"sincronizar laptop"*
- *"actualiza con la nube"*

---

## 2. Procedimiento de EjecuciÃ³n AutomÃ¡tica

Al recibir la orden, el agente ejecuta en orden:

### Paso 1: Sincronizar Skills Locales
1. Busca la carpeta de Google Drive: `G:\Mi unidad\Antigravity\skills`.
2. Asegura que la carpeta local del sistema (`~/.gemini/antigravity/skills`) apunte a la nube o tenga todas las skills copiadas al dÃ­a.

### Paso 1.1: Sincronizar Entornos y Lenguajes (Nova Environment Sentinel)
1. Ejecuta automÃ¡ticamente:
```powershell
powershell -ExecutionPolicy Bypass -File "G:\Mi unidad\Antigravity\sync_dev_environments.ps1"
```
2. Audita si Node.js LTS, OpenJDK 21, Git, GitHub CLI, Python y Docker estÃ¡n instalados. Si falta alguno en la laptop o PC nueva, lo descarga e instala silenciosamente vÃ­a `winget`.
3. Configura `JAVA_HOME` apuntando al JDK 21.

### Paso 2: Configurar Git Guardian Global para IntelliJ, VS Code y Android Studio
Ejecuta automÃ¡ticamente en PowerShell:
```powershell
git config --global core.hooksPath "G:/Mi unidad/Antigravity/skills/git-guardian-sentinel/scripts"
```
Esto deja la laptop blindada contra fugas de API keys o sentencias SQL suicidas en todos los IDEs.

### Paso 3: Asegurar Dependencias de Estudio y TranscripciÃ³n
Verifica e instala en la laptop las librerÃ­as necesarias para transcribir clases:
```powershell
pip install --upgrade yt-dlp youtube-transcript-api
```

### Paso 4: Conectar Memoria y Ecosistema Multi-Agente
- Carga el enrutador multi-agente (`multiagent-router`).
- Conecta la memoria persistente de proyectos en `G:\Mi unidad\Antigravity\memory`.
- Conecta la carpeta de transcripciones en `G:\Mi unidad\Antigravity\transcripts`.

### Paso 5: ConfirmaciÃ³n al Usuario
El agente responderÃ¡ con un mensaje breve y conciso:
> *"âœ… Sistema 100% sincronizado con tu nube: 21 skills activas, transcriptor de clases listo, ecosistema multi-agente operativo y Git Guardian protegiendo tus IDEs."*

