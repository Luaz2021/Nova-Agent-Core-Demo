"""
Nova Buffer & Token Guardian v2.1 (Community Edition - 100% Local)
==================================================================
- Monitorea en tiempo real el peso en tokens de la sesion activa.
- Guarda el dialogo limpio en texto plano en ~/.gemini/antigravity/memory/chat_logs/.
- Mantiene actualizado 'ultimo_contexto_puente.md' en local para traspaso instantaneo al abrir ventana nueva.
- Dispara alerta al superar 100k tokens.
"""

import os
import socket
import sys
import json
import time
import glob
import subprocess
from datetime import datetime

def get_memory_dir():
    """Carpeta de memoria 100% local para Community Edition (Sin sincronizacion Cloud)."""
    local_fallback = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "memory"))
    os.makedirs(local_fallback, exist_ok=True)
    return local_fallback

BRAIN_DIR = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "brain"))
MEMORY_DIR = get_memory_dir()
CHAT_LOGS_DIR = os.path.join(MEMORY_DIR, "chat_logs")
BRIDGE_FILE = os.path.join(MEMORY_DIR, "ultimo_contexto_puente.md")
STATE_FILE = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "buffer_guardian_state.json"))

TOKEN_THRESHOLD = 100000  # 100k tokens: Punto dulce antes de consumo alto de bateria
TOKEN_STEP = 25000        # Re-alertar cada 25k adicionales (125k, 150k, 175k, etc.)
RETENTION_DAYS = 90       # 3 meses de retencion para logs crudos

LAST_MTIME_MAP = {}
CACHED_RESULTS = {}

os.makedirs(CHAT_LOGS_DIR, exist_ok=True)


def purge_old_logs():
    """Elimina logs de chat de mas de 90 dias."""
    cutoff = time.time() - (RETENTION_DAYS * 86400)
    for filepath in glob.glob(os.path.join(CHAT_LOGS_DIR, "chat_*.txt")):
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
        except Exception:
            pass


def get_latest_transcript():
    """Encuentra el transcript.jsonl de la conversacion activa mas reciente."""
    pattern = os.path.join(BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl")
    files = glob.glob(pattern)
    if not files:
        return None, None
    latest = max(files, key=os.path.getmtime)
    conv_id = latest.split(os.sep)[-4]
    return conv_id, latest


def parse_and_sync_transcript(conv_id, transcript_path):
    """Extrae el texto plano limpio, archivos tocados y calcula la carga actual de tokens."""
    global LAST_MTIME_MAP, CACHED_RESULTS

    try:
        current_mtime = os.path.getmtime(transcript_path)
        if transcript_path in LAST_MTIME_MAP and LAST_MTIME_MAP[transcript_path] == current_mtime:
            if conv_id in CACHED_RESULTS:
                return CACHED_RESULTS[conv_id]
    except Exception:
        current_mtime = 0

    dialogues = []
    touched_files = set()
    current_tokens = 0
    user_msg_count = 0
    last_user_goal = ""
    last_nova_action = ""

    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                step_type = obj.get("type", "")
                created = obj.get("created_at", "")[:19].replace("T", " ")

                # Extraer herramientas y archivos tocados
                tool_calls = obj.get("tool_calls", [])
                if tool_calls:
                    for call in tool_calls:
                        args = call.get("args") or call.get("arguments") or {}
                        if isinstance(args, dict):
                            for key in ["Path", "path", "file_path", "filePath"]:
                                if key in args and isinstance(args[key], str):
                                    touched_files.add(os.path.basename(args[key]))

                if step_type == "USER_INPUT":
                    content = obj.get("content", "").strip()
                    if "<USER_REQUEST>" in content:
                        content = content.split("<USER_REQUEST>")[-1].split("</USER_REQUEST>")[0].strip()
                    if content:
                        user_msg_count += 1
                        last_user_goal = content[:200]
                        dialogues.append(f"[{created}] ALEXANDER: {content}")

                elif step_type == "PLANNER_RESPONSE":
                    inp = obj.get("input_tokens", 0) or 0
                    cache = obj.get("cache_read_tokens", 0) or 0
                    if (inp + cache) > 0:
                        current_tokens = inp + cache

                    content = obj.get("content", "").strip()
                    if content:
                        last_nova_action = content[:200]
                        dialogues.append(f"[{created}] NOVA: {content}")
    except Exception:
        return 0, 0

    if not dialogues:
        return current_tokens, user_msg_count

    # Guardar en cache de ejecucion
    LAST_MTIME_MAP[transcript_path] = current_mtime
    CACHED_RESULTS[conv_id] = (current_tokens, user_msg_count)

    # 1. Guardar log completo en texto plano (retencion 3 meses)
    date_str = datetime.now().strftime("%Y-%m")
    log_file = os.path.join(CHAT_LOGS_DIR, f"chat_{date_str}_{conv_id[:8]}.txt")
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"# Historial de Conversacion ({conv_id})\n")
            f.write(f"# Carga actual: {current_tokens:,} tokens | Mensajes: {user_msg_count}\n")
            f.write(f"# Archivos tocados: {', '.join(sorted(touched_files)) if touched_files else 'Ninguno'}\n")
            f.write("=" * 70 + "\n\n")
            f.write("\n\n".join(dialogues))
    except Exception:
        pass

    # 2. Actualizar archivo puente ultraligero (SOLO si Nova ya emitio al menos 1 respuesta real en esta ventana,
    #    evitando sobrescribir el puente de la ventana anterior durante el turno inicial de traspaso "continuamos"/"seguimos")
    if last_nova_action.strip():
        recent = dialogues[-10:]
        files_str = ", ".join(sorted(touched_files)) if touched_files else "N/A"
        is_ready_to_switch = "LISTO_PARA_SALTAR" if current_tokens >= TOKEN_THRESHOLD else "EN_CURSO"
        try:
            current_machine = os.environ.get("COMPUTERNAME") or socket.gethostname() or "DESCONOCIDO"
            with open(BRIDGE_FILE, "w", encoding="utf-8") as f:
                f.write("# Puente de Contexto Inmediato (Traspaso entre Ventanas)\n")
                f.write(f"- ESTADO: {is_ready_to_switch}\n")
                f.write(f"- EQUIPO_ORIGEN: {current_machine}\n")
                f.write(f"- ACTUALIZADO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Chat: `{conv_id[:8]}`)\n")
                f.write(f"- CARGA_TOKENS: {current_tokens:,} tokens ({user_msg_count} mensajes)\n")
                f.write(f"- ARCHIVOS_TOCADOS: [{files_str}]\n")
                f.write(f"- ULTIMA_ORDEN_ALEXANDER: {last_user_goal}\n")
                f.write(f"- ULTIMO_PASO_NOVA: {last_nova_action}\n")
                f.write(f"- RUTA_LOG_HISTORICO: {log_file}\n\n")
                f.write("## Ultimas lineas habladas (Retomar desde aqui):\n\n")
                for entry in recent:
                    if len(entry) > 600:
                        entry = entry[:600] + " ... [ver log completo]"
                    f.write(f"- {entry}\n\n")
        except Exception:
            pass

    return current_tokens, user_msg_count


def trigger_alert(current_tokens):
    """Dispara alerta sonora, notificacion toast no bloqueante y aviso de voz."""
    k_tokens = int(current_tokens / 1000)
    print(f"[ALERTA BUFFER] Sesion en {current_tokens:,} tokens ({k_tokens}k). Puente persistido en local.")

    # 1. Chime acustico doble + Beep nativo del sistema
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        winsound.Beep(880, 180)
        winsound.Beep(1175, 240)
    except Exception:
        pass

    # 2. Notificacion Toast de Windows 11 (usando AUMID registrado de Antigravity + NotifyIcon fallback)
    try:
        msg_body = f"Sesion en {current_tokens:,} tokens ({k_tokens}k). Puente guardado en local. Abre ventana nueva para ahorrar tokens."
        ps_toast = f"""
        try {{
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName('text')
            $textNodes.Item(0).AppendChild($template.CreateTextNode('Nova Token Guardian ({k_tokens}k tokens)')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{msg_body}')) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Google.AntigravityIDE').Show($toast)
        }} catch {{
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $n = New-Object System.Windows.Forms.NotifyIcon
            $n.Icon = [System.Drawing.SystemIcons]::Warning
            $n.Visible = $true
            $n.ShowBalloonTip(7000, 'Nova Token Guardian ({k_tokens}k tokens)', '{msg_body}', [System.Windows.Forms.ToolTipIcon]::Warning)
            Start-Sleep -Seconds 7
            $n.Dispose()
        }}
        """
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_toast],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
    except Exception:
        pass

    # 3. Aviso por voz asincrono (SAPI)
    try:
        voice_text = f"Alexander, la sesion supero los {k_tokens} mil tokens. El puente esta guardado en local para saltar cuando quieras."
        ps_voice = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Volume = 100; try {{ $s.SelectVoice('Microsoft Helena Desktop') }} catch {{}}; $s.Speak('{voice_text}')"
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_voice],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
    except Exception:
        pass


def check_once(silent=False):
    purge_old_logs()
    conv_id, transcript = get_latest_transcript()
    if not transcript:
        return
    tokens, msgs = parse_and_sync_transcript(conv_id, transcript)
    print(f"[Nova Buffer Guardian] Conversacion: {conv_id[:8]} | Carga actual: {tokens:,} tokens | Mensajes: {msgs}")

    # Cargar estado
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    last_alert_tokens = state.get(conv_id, 0)

    # Deteccion de compactacion de contexto: si los tokens cayeron mas de 15k, resetear umbral
    if tokens < (last_alert_tokens - 15000):
        last_alert_tokens = 0
        state[conv_id] = 0

    should_alert = False
    if not silent and tokens >= TOKEN_THRESHOLD:
        if last_alert_tokens == 0:
            should_alert = True
        elif (tokens - last_alert_tokens) >= TOKEN_STEP:
            should_alert = True

    if should_alert:
        state[conv_id] = tokens
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass
        trigger_alert(tokens)


def sync_all_historical_chats():
    """Extrae todos los chats historicos de brain/* a chat_logs/ y genera un indice maestro."""
    pattern = os.path.join(BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl")
    files = sorted(glob.glob(pattern), key=os.path.getmtime)
    summary_entries = []
    total_conv = 0
    total_msgs = 0

    for t_path in files:
        conv_id = t_path.split(os.sep)[-4]
        tokens, msgs = parse_and_sync_transcript(conv_id, t_path)
        if msgs == 0:
            continue
        total_conv += 1
        total_msgs += msgs
        mtime_str = datetime.fromtimestamp(os.path.getmtime(t_path)).strftime("%Y-%m-%d %H:%M")

        topics = []
        try:
            with open(t_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"USER_INPUT"' in line:
                        obj = json.loads(line)
                        c = obj.get("content", "").strip()
                        if "<USER_REQUEST>" in c:
                            c = c.split("<USER_REQUEST>")[-1].split("</USER_REQUEST>")[0].strip()
                        c = " ".join(c.split())
                        if c and len(c) > 2:
                            topics.append(c[:140] + ("..." if len(c) > 140 else ""))
                        if len(topics) >= 3:
                            break
        except Exception:
            pass

        topic_str = " | ".join(topics) if topics else "Sin texto de usuario"
        summary_entries.append({
            "conv_id": conv_id,
            "date": mtime_str,
            "msgs": msgs,
            "tokens": tokens,
            "topics": topic_str
        })

    summary_file = os.path.join(MEMORY_DIR, "resumen_historico_chats.md")
    try:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# Archivo Historico Consolidado de Conversaciones (Antigravity Brain)\n")
            f.write(f"*Sincronizado automaticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            f.write(f"*Total conversaciones respaldadas: **{total_conv}** | Mensajes totales: **{total_msgs}**\n\n")
            f.write("> Todos los dialogos completos en texto plano estan guardados en `memory\\chat_logs\\`.\n\n")
            f.write("| Fecha Ult. Act. | ID Chat | Msgs | Pico Tokens | Temas Tratados / Primeros Prompts |\n")
            f.write("| :--- | :--- | :---: | :---: | :--- |\n")
            for item in reversed(summary_entries):
                f.write(f"| {item['date']} | `{item['conv_id'][:8]}` | {item['msgs']} | {item['tokens']:,} | {item['topics']} |\n")
    except Exception as e:
        print(f"Error escribiendo resumen: {e}")

    print(f"[Nova Buffer Guardian] Historico completo respaldado: {total_conv} chats ({total_msgs} mensajes) -> {summary_file}")


if __name__ == "__main__":
    if "--sync-all" in sys.argv:
        sync_all_historical_chats()
    elif "--daemon" in sys.argv:
        while True:
            try:
                check_once(silent=False)
            except Exception:
                pass
            time.sleep(15)
    else:
        check_once(silent="--silent" in sys.argv)
