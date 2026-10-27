---
name: nova-awake-sentinel
description: "Guardian anti-suspension inteligente y nativo para Windows. Mantiene la CPU y pantalla encendidas durante tareas activas usando SetThreadExecutionState (sin pulsar teclas falsas), monitorea el nivel de bateria (Safe Checkpoint al 10%) y restaura la politica normal de bloqueo de Windows tras 5 minutos de inactividad."
---

# Nova Awake Sentinel

Protege la ejecucion de tareas largas en segundo plano evitando que Windows se suspenda o bloquee mientras el agente procesa codigo.

## 1. Caracteristicas
- **API Nativa:** Usa `kernel32.dll -> SetThreadExecutionState`. Cero interferencia de raton o teclado.
- **Monitoreo de Bateria:** Consulta `GetSystemPowerStatus`. Si la laptop esta a bateria y cae a <= 10% (o entra en modo ahorro), aplica un checkpoint seguro y libera la suspension para evitar apagones forzados.
- **Temporizador de Gracia (5 minutos):** Al terminar la tarea de Nova, mantiene el equipo despierto 300 segundos adicionales. Si no entran mas tareas, restaura la suspension automatica original de Windows.

## 2. Invocacion Rapida
- Activar flag de tarea: `python scripts/nova_awake_sentinel.py flag-on`
- Desactivar flag: `python scripts/nova_awake_sentinel.py flag-off`
- Demonio en segundo plano: `wscript scripts/start_awake_sentinel.vbs`
