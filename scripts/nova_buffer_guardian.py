"""
Nova Buffer & Token Guardian v2.0 - Resilient & Multi-Alert Engine
===================================================================
- Monitorea en tiempo real el peso en tokens (input_tokens + cache_read_tokens) de la sesion activa.
- Extrae el dialogo puro en texto plano (0 basura) a Google Drive (memory/chat_logs/).
- Mantiene actualizado 'ultimo_contexto_puente.md' con los ultimos intercambios para traspaso instantaneo al abrir nueva ventana.
- Detecta automaticamente compactaciones de contexto (reseteo inteligente de umbral tras compactacion).
- Dispara triple alerta no bloqueante al superar 100k tokens (y cada +25k adicionales):
    1. Chime de sistema (winsound nativo).
    2. Notificacion Toast nativa de Windows (ToastNotificationManager).
    3. Sintesis de voz concisa asincrona.
- Optimizado con cache de mtime para reducir I/O de disco y evitar bloqueos con Google Drive File Stream.
- Purga automaticamente logs crudos de mas de 90 dias (3 meses).
"""

import contextlib
import glob
import json
import os
import socket
import subprocess
import sys
import re
import time
from datetime import datetime

# ---------- Claves fuera de los chat logs (se suben a Drive) ----------
# Si Alexander pega una clave en el chat, el log y el puente la guardan TACHADA: la clave real solo vive en el cofre
# (vault\google_cloud.env). 12/11 (Claude): + Gamma, ElevenLabs, Resend, Supabase, Stripe, Groq, HF y api_key="...".
PATRONES_CLAVE = [
    re.compile(r"sk-(?:gamma-|or-|proj-|ant-)?[A-Za-z0-9_-]{20,}"),    # Gamma / OpenAI / OpenRouter / Anthropic
    re.compile(r"\bsk_[a-f0-9]{32,}"),                                 # ElevenLabs
    re.compile(r"\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9]{16,}"),              # Resend
    re.compile(r"\bsb_(?:secret|publishable)_[A-Za-z0-9_-]{20,}"),     # Supabase (claves nuevas)
    re.compile(r"\b(?:sk|rk|pk)_live_[A-Za-z0-9]{20,}"),               # Stripe
    re.compile(r"\b(?:gsk|hf)_[A-Za-z0-9]{20,}"),                      # Groq / HuggingFace
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}"),                     # GitHub (token fino)
    re.compile(r"(?i)\b(?:api[_-]?key|apikey|secret|token)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-./+=]{24,}[\"']"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),                            # Google
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),                         # GitHub
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{20,}"),                       # Slack
    re.compile(r"AKIA[0-9A-Z]{16}"),                                  # AWS
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),                     # bot de Telegram
    re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),  # JWT / service_role
]
# VARIABLE_DE_ENTORNO=valor (OPENROUTER_API_KEY=..., DB_PASSWORD: ...) y "contraseña: ..." escrito en el chat
RE_ASIGNACION = re.compile(
    r"\b([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASS|PWD)[A-Z0-9_]*|(?i:contrase[nñ]a|password))"
    r"(\s*[:=]\s*)(['\"]?)([^\s'\"]{6,})"
)


def tachar_claves(texto: str) -> str:
    for r in PATRONES_CLAVE:
        texto = r.sub("[CLAVE TACHADA -> cofre]", texto)
    return RE_ASIGNACION.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[CLAVE TACHADA -> cofre]", texto)


def get_memory_dir():
    """Sync v4 (local primero): la memoria vive en ~/.gemini/antigravity/memory.
    Drive solo es respaldo; nova_sync_v4.ps1 la sube y la baja entre equipos."""
    local_mem = os.path.expanduser(
        os.path.join("~", ".gemini", "antigravity", "memory")
    )
    os.makedirs(local_mem, exist_ok=True)
    return local_mem


def _legacy_get_drive_memory_dir():
    """(Retirado en v4) Busqueda antigua de la memoria en Google Drive."""
    # 1. macOS (Google Drive for Desktop moderno usa CloudStorage)
    if sys.platform == "darwin":
        cloud_storage = os.path.expanduser("~/Library/CloudStorage")
        if os.path.exists(cloud_storage):
            for d in os.listdir(cloud_storage):
                if "GoogleDrive" in d:
                    for sub in [
                        "Mi unidad/Antigravity/memory",
                        "My Drive/Antigravity/memory",
                        "Antigravity/memory",
                    ]:
                        candidate = os.path.join(cloud_storage, d, sub)
                        if os.path.exists(candidate):
                            return candidate

    # 2. Linux / macOS rutas directas comunes (rclone, Google Drive CLI, sync clients)
    for linux_path in [
        os.path.expanduser("~/GoogleDrive/Antigravity/memory"),
        os.path.expanduser("~/Drive/Antigravity/memory"),
        os.path.expanduser("~/Google Drive/Antigravity/memory"),
        "/mnt/gdrive/Antigravity/memory",
    ]:
        if os.path.exists(linux_path):
            return linux_path

    # 3. Windows (busqueda dinamica por letras de unidad)
    for letter in "GDEFGHIJKLMNOPQRSTUVWXYZC":
        for sub in [
            r"Mi unidad\Antigravity\memory",
            r"My Drive\Antigravity\memory",
            r"Antigravity\memory",
        ]:
            candidate = os.path.join(f"{letter}:\\", sub)
            if os.path.exists(candidate):
                return candidate

    # Fallback local agnostico al SO
    local_fallback = os.path.expanduser(
        os.path.join("~", ".gemini", "antigravity", "memory")
    )
    os.makedirs(local_fallback, exist_ok=True)
    return local_fallback


BRAIN_DIR = os.path.expanduser(os.path.join("~", ".gemini", "antigravity", "brain"))
MEMORY_DIR = get_memory_dir()
CHAT_LOGS_DIR = os.path.join(MEMORY_DIR, "chat_logs")
BRIDGE_FILE = os.path.join(MEMORY_DIR, "ultimo_contexto_puente.md")
STATE_FILE = os.path.expanduser(
    os.path.join("~", ".gemini", "antigravity", "buffer_guardian_state.json")
)

TOKEN_THRESHOLD = 100000  # 100k tokens: Punto dulce antes de consumo alto de bateria
TOKEN_STEP = 25000  # Re-alertar cada 25k adicionales (125k, 150k, 175k, etc.)
RETENTION_DAYS = 90  # 3 meses de retencion para logs crudos

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
    pattern = os.path.join(
        BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl"
    )
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
        if (
            transcript_path in LAST_MTIME_MAP
            and LAST_MTIME_MAP[transcript_path] == current_mtime
            and conv_id in CACHED_RESULTS
        ):
            return CACHED_RESULTS[conv_id]
    except Exception:
        current_mtime = 0

    dialogues = []
    touched_files = set()  # escritos (write/edit/replace/create)
    read_files = set()  # solo leidos: van aparte para que Nova no crea que los modifico
    current_tokens = 0
    user_msg_count = 0
    checkpoints_count = 0
    last_user_goal = ""
    last_nova_action = ""
    first_created = ""

    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
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
                if not first_created and created:
                    first_created = created

                # Extraer herramientas y archivos tocados
                tool_calls = obj.get("tool_calls", [])
                if tool_calls:
                    for call in tool_calls:
                        args = call.get("args") or call.get("arguments") or {}
                        if isinstance(args, dict):
                            for key in ["Path", "path", "file_path", "filePath"]:
                                if key in args and isinstance(args[key], str):
                                    (touched_files if re.search(r"write|replace|edit|create|delete|move", str(call.get("name", "")), re.I) else read_files).add(os.path.basename(args[key]))

                if step_type == "CHECKPOINT":
                    checkpoints_count += 1
                    dialogues.append(
                        f"\n{'=' * 70}\n"
                        f">>> [COMPACTACION CICLO {checkpoints_count}/5 | Hora: {created}] (Reseteo de Buffer) <<<\n"
                        f"{'=' * 70}\n"
                    )

                elif step_type == "USER_INPUT":
                    content = obj.get("content", "").strip()
                    if "<USER_REQUEST>" in content:
                        content = (
                            content.split("<USER_REQUEST>")[-1]
                            .split("</USER_REQUEST>")[0]
                            .strip()
                        )
                    if content:
                        content = tachar_claves(content)  # la clave real solo en .env, nunca en logs/puente
                        user_msg_count += 1
                        last_user_goal = content[:200]
                        dialogues.append(f"[{created}] ALEXANDER: {content}")

                elif step_type == "PLANNER_RESPONSE":
                    inp = obj.get("input_tokens", 0) or 0
                    cache = obj.get("cache_read_tokens", 0) or 0
                    if (inp + cache) > 0:
                        current_tokens = inp + cache

                    content = tachar_claves(obj.get("content", "").strip())
                    if content:
                        last_nova_action = content[:200]
                        dialogues.append(f"[{created}] NOVA: {content}")
    except Exception:
        return 0, 0, 0

    if not dialogues:
        return current_tokens, user_msg_count, checkpoints_count

    # Guardar en cache de ejecucion
    LAST_MTIME_MAP[transcript_path] = current_mtime
    CACHED_RESULTS[conv_id] = (current_tokens, user_msg_count, checkpoints_count)

    # 1. Regla de Oro: 1 Ventana = 1 Solo Archivo de Chat Consolidado
    date_str = first_created[:10] if first_created else datetime.now().strftime("%Y-%m-%d")
    time_str = first_created[11:16].replace(":", "") if len(first_created) >= 16 else "0000"
    log_file = os.path.join(
        CHAT_LOGS_DIR, f"chat_{date_str}_inicio-{time_str}_conv-{conv_id[:8]}.txt"
    )

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("# HISTORIAL DE CHAT CONSOLIDADO (Capa 0 - Local)\n")
            f.write(f"# Conversacion ID: {conv_id}\n")
            f.write(f"# Inicio de ventana: {date_str} a las {time_str}\n")
            f.write(f"# Ciclos de compactacion realizados: {checkpoints_count} de 5\n")
            f.write(f"# Carga actual de tokens: {current_tokens:,} tokens ({user_msg_count} mensajes)\n")
            f.write(f"# Archivos tocados: {', '.join(sorted(touched_files)) if touched_files else 'Ninguno'}\n")
            f.write("=" * 70 + "\n\n")
            f.write("\n\n".join(dialogues))
    except Exception:
        pass

    # 2. Actualizar archivo puente ultraligero
    explicit_save = any(
        w in last_user_goal.lower()
        for w in ["saltar", "puente", "guarda todo", "guardar todo", "sube todo"]
    )
    if last_nova_action.strip() and (
        (user_msg_count >= 3 and current_tokens >= 25000) or explicit_save
    ):
        recent = dialogues[-6:]
        files_str = ", ".join(sorted(touched_files)) if touched_files else "N/A"
        is_ready_to_switch = (
            "LISTO_PARA_SALTAR"
            if (current_tokens >= TOKEN_THRESHOLD or explicit_save or checkpoints_count >= 5)
            else "EN_CURSO"
        )
        inherited_block = ""
        try:
            if os.path.exists(BRIDGE_FILE):
                with open(BRIDGE_FILE, encoding="utf-8", errors="replace") as bf:
                    old_bridge = bf.read()
                if (
                    f"(Chat: `{conv_id[:8]}`)" not in old_bridge
                    and "## Ultimas lineas habladas" in old_bridge
                ):
                    old_tail = old_bridge.split(
                        "## Ultimas lineas habladas (Retomar desde aqui):"
                    )[-1].strip()
                    if old_tail:
                        inherited_block = (
                            "\n## Contexto Heredado de Ventana Previa:\n"
                            + old_tail[:800]
                            + "\n"
                        )
        except Exception:
            pass
        try:
            current_machine = (
                os.environ.get("COMPUTERNAME") or socket.gethostname() or "DESCONOCIDO"
            )
            with open(BRIDGE_FILE, "w", encoding="utf-8") as f:
                f.write("# Puente de Contexto Inmediato (Traspaso entre Ventanas)\n")
                f.write(f"- ESTADO: {is_ready_to_switch}\n")
                f.write(f"- EQUIPO_ORIGEN: {current_machine}\n")
                f.write(
                    f"- ACTUALIZADO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Chat: `{conv_id[:8]}`)\n"
                )
                f.write(
                    f"- CARGA_TOKENS_PREVIA: {current_tokens:,} tokens ({user_msg_count} mensajes)\n"
                )
                f.write(f"- CICLOS_COMPACT_USADOS: {checkpoints_count}/5\n")
                f.write(f"- ARCHIVOS_TOCADOS (escritos): [{files_str}]\n")
                leidos = ", ".join(sorted(read_files)[:15]) if read_files else "N/A"
                f.write(f"- ARCHIVOS_LEIDOS (no modificados): [{leidos}]\n")
                f.write(f"- ULTIMA_ORDEN_ALEXANDER: {last_user_goal}\n")
                f.write(f"- ULTIMO_PASO_NOVA: {last_nova_action}\n")
                f.write(f"- RUTA_LOG_HISTORICO: {log_file}\n")
                f.write(
                    "- REGLA_RECUPERACION: Si falta contexto historico detallado, leer RUTA_LOG_HISTORICO bajo demanda en 1 sola llamada (tope puente < 10k tokens).\n\n"
                )
                f.write("## Ultimas lineas habladas (Retomar desde aqui):\n\n")
                for entry in recent:
                    if len(entry) > 400:
                        entry = entry[:400] + " ... [ver log historico]"
                    f.write(f"- {entry}\n\n")
                if inherited_block and user_msg_count <= 4:
                    f.write(inherited_block)
        except Exception:
            pass

    return current_tokens, user_msg_count, checkpoints_count


def trigger_alert(current_tokens, ciclos_compact=0):
    """Dispara alerta sonora, aviso de voz nativo y persiste puente en Drive."""
    k_tokens = int(current_tokens / 1000)
    print(
        f"[ALERTA BUFFER] Sesion en {current_tokens:,} tokens ({k_tokens}k) | Ciclos: {ciclos_compact}/5. Puente persistido en Drive."
    )

    # 1. Beep nativo del sistema
    try:
        import winsound

        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass

    # 2. Aviso por voz nativo en segundo plano via VBScript (SAPI Helena a 0 tokens)
    try:
        vbs_path = os.path.join(os.path.dirname(__file__), "play_token_alert.vbs")
        if not os.path.exists(vbs_path):
            vbs_path = os.path.join(
                get_memory_dir(), "..", "scripts", "play_token_alert.vbs"
            )
        if os.path.exists(vbs_path):
            if ciclos_compact < 5:
                voice_msg = (
                    f"Alexander, la sesion supero los {k_tokens} mil tokens. "
                    f"Tienes {ciclos_compact} de 5 compactaciones. Escribe compact para resetear el bufer a 17 mil tokens."
                )
            else:
                voice_msg = (
                    f"Alexander, alcanzaste 5 compactaciones en esta sesion. "
                    f"El puente esta guardado en Drive para saltar a una ventana nueva limpia."
                )
            subprocess.Popen(
                ["wscript.exe", vbs_path, voice_msg],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def check_once(silent=False):
    purge_old_logs()
    conv_id, transcript = get_latest_transcript()
    if not transcript:
        return
    tokens, msgs, ciclos = parse_and_sync_transcript(conv_id, transcript)
    print(
        f"[Nova Buffer Guardian] Conversacion: {conv_id[:8]} | Carga actual: {tokens:,} tokens | Mensajes: {msgs} | Ciclos compact: {ciclos}/5"
    )

    # Cargar estado
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    raw_conv_data = state.get(conv_id, 0)
    if isinstance(raw_conv_data, dict):
        last_alert_tokens = raw_conv_data.get("tokens", 0)
        last_ciclos = raw_conv_data.get("ciclos", 0)
    else:
        last_alert_tokens = int(raw_conv_data or 0)
        last_ciclos = 0

    # Deteccion de compactacion de contexto: si los tokens cayeron mas de 15k o aumento el contador de checkpoints
    if tokens < (last_alert_tokens - 15000) or ciclos > last_ciclos:
        print(f"[COMPACT DETECTADO] Ciclo {ciclos}/5 activo | Buffer reducido a {tokens:,} tokens.")
        last_alert_tokens = tokens
        last_ciclos = ciclos
        state[conv_id] = {"tokens": tokens, "ciclos": ciclos}
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass

    should_alert = False
    if (
        not silent
        and tokens >= TOKEN_THRESHOLD
        and (last_alert_tokens == 0 or (tokens - last_alert_tokens) >= TOKEN_STEP)
    ):
        should_alert = True

    if should_alert:
        state[conv_id] = {"tokens": tokens, "ciclos": ciclos}
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass
        trigger_alert(tokens, ciclos_compact=ciclos)



def sync_all_historical_chats():
    """Extrae todos los chats historicos de brain/* a chat_logs/ y genera un indice maestro."""
    pattern = os.path.join(
        BRAIN_DIR, "*", ".system_generated", "logs", "transcript.jsonl"
    )
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
        mtime_str = datetime.fromtimestamp(os.path.getmtime(t_path)).strftime(
            "%Y-%m-%d %H:%M"
        )

        topics = []
        try:
            with open(t_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"USER_INPUT"' in line:
                        obj = json.loads(line)
                        c = obj.get("content", "").strip()
                        if "<USER_REQUEST>" in c:
                            c = (
                                c.split("<USER_REQUEST>")[-1]
                                .split("</USER_REQUEST>")[0]
                                .strip()
                            )
                        c = " ".join(c.split())
                        if c and len(c) > 2:
                            topics.append(c[:140] + ("..." if len(c) > 140 else ""))
                        if len(topics) >= 3:
                            break
        except Exception:
            pass

        topic_str = " | ".join(topics) if topics else "Sin texto de usuario"
        summary_entries.append(
            {
                "conv_id": conv_id,
                "date": mtime_str,
                "msgs": msgs,
                "tokens": tokens,
                "topics": topic_str,
            }
        )

    summary_file = os.path.join(MEMORY_DIR, "resumen_historico_chats.md")
    try:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(
                "# Archivo Historico Consolidado de Conversaciones (Antigravity Brain)\n"
            )
            f.write(
                f"*Sincronizado automaticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
            )
            f.write(
                f"*Total conversaciones respaldadas: **{total_conv}** | Mensajes totales: **{total_msgs}**\n\n"
            )
            f.write(
                "> Todos los dialogos completos en texto plano estan guardados en `memory\\chat_logs\\`.\n\n"
            )
            f.write(
                "| Fecha Ult. Act. | ID Chat | Msgs | Pico Tokens | Temas Tratados / Primeros Prompts |\n"
            )
            f.write("| :--- | :--- | :---: | :---: | :--- |\n")
            f.writelines(
                f"| {item['date']} | `{item['conv_id'][:8]}` | {item['msgs']} | {item['tokens']:,} | {item['topics']} |\n"
                for item in reversed(summary_entries)
            )
    except Exception as e:
        print(f"Error escribiendo resumen: {e}")

    print(
        f"[Nova Buffer Guardian] Historico completo respaldado: {total_conv} chats ({total_msgs} mensajes) -> {summary_file}"
    )


if __name__ == "__main__":
    if "--sync-all" in sys.argv:
        sync_all_historical_chats()
    elif "--daemon" in sys.argv:
        # 09/11 (Claude): antes importaba nova_puente_capturas.mover_adjuntos_recientes, que ya no existe (se
        # renombro el 08/11) -> el daemon se caia al arrancar y las conversaciones no se copiaban a chat_logs.
        # Mover adjuntos ya lo hace el propio puente (nova_puente_capturas.py --daemon): aqui solo la memoria.
        while True:
            with contextlib.suppress(Exception):
                check_once(silent=False)  # silent=True apagaria los avisos de 100k / compact / salto de ventana
            time.sleep(15)
    else:
        check_once(silent="--silent" in sys.argv)
