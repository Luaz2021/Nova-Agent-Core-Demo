---
name: nova-community-feedback
description: "Canal directo de comunicacion con Saul Martinez (Luaz2021/Nova_Agent_Github). Permite al usuario enviar mensajes directos, sugerencias o fixes al creador con 1 solo comando o de viva voz en el chat."
---

# Nova Community Feedback

Permite a cualquier usuario de Nova comunicarse directamente con el creador (Saul Martinez):

## 1. Comandos Disponibles en Chat
Cuando el usuario diga:
- *"Nova, envia mensaje al creador: [texto]"* o *"Enviar mensaje a Saul: [texto]"*:
  Nova toma el texto, lo sanitiza (cero IPs ni rutas privadas) y ejecuta:
  `python scripts/enviar_feedback.py mensaje "<texto>"`
  Abre la ventana oficial en GitHub con el mensaje listo para enviar con 1 clic.
- *"Nova, quiero proponer una idea"* o *"Sugerir nueva skill"*:
  Nova ejecuta: `python scripts/enviar_feedback.py idea`
- *"Nova, quiero compartir un fix"* o *"Reportar error esquivado"*:
  Nova ejecuta: `python scripts/enviar_feedback.py fix`

## 2. Para Saul Martinez (Como Leer y Responderles):
- Ver mensajes nuevos desde tu terminal:
  `gh issue list --repo Luaz2021/Nova_Agent_Github`
- Responderle al usuario:
  `gh issue comment <numero> --body "Hola [usuario], he leido tu mensaje. [tu respuesta]"`
- Cerrar el hilo:
  `gh issue close <numero> --comment "Mensaje atendido. Gracias!"`
