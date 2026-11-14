---
name: gemini-cloud-sync
description: "Motor de sincronizacion PC y Laptop: enlaza skills de Drive, memoria persistente, manifiesto SHA-256 y Git Guardian."
trigger: model_decision
---

# Cloud Sync Engine (Un Solo Clic: "Sincroniza")

Esta habilidad automatiza por completo la puesta a punto de tu entorno. Cuando estés en tu laptop (o en cualquier máquina nueva con Google Drive instalado) y digas **"sincroniza"**, el agente ejecutará todo el protocolo sin que tengas que acordarte de comandos ni rutas.

---

## 1. Cuándo se Activa

El agente activará este procedimiento cuando el usuario diga:
- *"sincroniza"*
- *"sincroniza todo"*
- *"sincronizar laptop"*
- *"actualiza con la nube"*

---

## 2. Procedimiento de Ejecución Automática

Al recibir la orden, el agente ejecuta en orden:

### Paso 1: Sincronizar Skills Locales
1. Busca la carpeta de Google Drive: `G:\Mi unidad\Antigravity\skills`.
2. Asegura que la carpeta local del sistema (`~/.gemini/antigravity/skills`) apunte a la nube o tenga todas las skills copiadas al día.

### Paso 1.1: Sincronizar Entornos y Lenguajes (Nova Environment Sentinel)
1. Ejecuta automáticamente:
```powershell
powershell -ExecutionPolicy Bypass -File "G:\Mi unidad\Antigravity\sync_dev_environments.ps1"
```
2. Audita si Node.js LTS, OpenJDK 21, Git, GitHub CLI, Python y Docker están instalados. Si falta alguno en la laptop o PC nueva, lo descarga e instala silenciosamente vía `winget`.
3. Configura `JAVA_HOME` apuntando al JDK 21.

### Paso 2: Configurar Git Guardian Global para IntelliJ, VS Code y Android Studio
Ejecuta automáticamente en PowerShell:
```powershell
git config --global core.hooksPath "G:/Mi unidad/Antigravity/skills/git-guardian-sentinel/scripts"
```
Esto deja la laptop blindada contra fugas de API keys o sentencias SQL suicidas en todos los IDEs.

### Paso 3: Asegurar Dependencias de Estudio y Transcripción
Verifica e instala en la laptop las librerías necesarias para transcribir clases:
```powershell
pip install --upgrade yt-dlp youtube-transcript-api
```

### Paso 4: Conectar Memoria y Ecosistema Multi-Agente
- Carga el enrutador multi-agente (`multiagent-router`).
- Conecta la memoria persistente de proyectos en `G:\Mi unidad\Antigravity\memory`.
- Conecta la carpeta de transcripciones en `G:\Mi unidad\Antigravity\transcripts`.

### Paso 5: Confirmación al Usuario
El agente responderá con un mensaje breve y conciso:
> *"✅ Sistema 100% sincronizado con tu nube: 21 skills activas, transcriptor de clases listo, ecosistema multi-agente operativo y Git Guardian protegiendo tus IDEs."*

