"""
Nova Destilador - Extractor y Analizador Autonomo de Videos (Reels & TikTok)
=============================================================================
Creado para Alexander Martinez (@Luaz2021)
Opera 100% en local a 0 tokens de nube: yt-dlp + FFmpeg + Ollama (coder de nova_modelos.json, hoy qwen3.5:9b)
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import urllib.request

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def get_next_video_dir():
    existing = []
    if os.path.exists(OUTPUT_DIR):
        for item in os.listdir(OUTPUT_DIR):
            if os.path.isdir(os.path.join(OUTPUT_DIR, item)) and item.startswith("video"):
                try:
                    num = int(item.replace("video", ""))
                    existing.append(num)
                except ValueError:
                    pass
    next_num = max(existing, default=0) + 1
    target_path = os.path.join(OUTPUT_DIR, f"video{next_num}")
    os.makedirs(target_path, exist_ok=True)
    return target_path, f"video{next_num}"


def _modelo_nova():
    try:
        return json.loads(open(os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "scripts", "nova_modelos.json"), encoding="utf-8").read())["coder"]
    except Exception:
        return "qwen3.5:9b"


def query_ollama(prompt, model=None):
    model = model or _modelo_nova()
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 450
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return json.loads(res_json.get("response", "{}"))
    except Exception as e:
        return {"error": str(e), "fallback": True}


def run_cmd(cmd_list):
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    p = subprocess.Popen(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    stdout, stderr = p.communicate()
    return p.returncode, stdout, stderr


def process_video_url(url, folder_path, folder_name, log_cb):
    log_cb(f"[{folder_name}] Iniciando descarga de: {url[:50]}...")
    temp_info = os.path.join(TEMP_DIR, f"{folder_name}.info.json")

    dl_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--ffmpeg-location", FFMPEG_EXE,
        "-f", "b/best",
        "--write-info-json",
        "-o", os.path.join(TEMP_DIR, f"{folder_name}.%(ext)s"),
        url
    ]
    code, stdout, stderr = run_cmd(dl_cmd)

    # Buscar el archivo descargado
    actual_video = None
    for ext in [".mp4", ".mkv", ".webm"]:
        cand = os.path.join(TEMP_DIR, f"{folder_name}{ext}")
        if os.path.exists(cand):
            actual_video = cand
            break

    # Si fallo la descarga sin cookies, reintentar usando cookies de Brave
    if not actual_video:
        log_cb(f"[{folder_name}] Reintentando con cookies de Brave...")
        dl_cmd_brave = dl_cmd + ["--cookies-from-browser", "brave"]
        code, stdout, stderr = run_cmd(dl_cmd_brave)
        for ext in [".mp4", ".mkv", ".webm"]:
            cand = os.path.join(TEMP_DIR, f"{folder_name}{ext}")
            if os.path.exists(cand):
                actual_video = cand
                break

    metadata = {}
    if os.path.exists(temp_info):
        try:
            with open(temp_info, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    title = metadata.get("title", "Sin titulo")
    description = metadata.get("description", "")
    duration = float(metadata.get("duration", 0.0))
    uploader = metadata.get("uploader", "Creador desconocido")

    cuts = [0.0]
    if actual_video and os.path.exists(actual_video):
        log_cb(f"[{folder_name}] Midiendo cortes de plano con FFmpeg...")
        scene_cmd = [
            FFMPEG_EXE, "-i", actual_video,
            "-filter_complex", "select='gt(scene,0.28)',metadata=print",
            "-f", "null", "-"
        ]
        _, _, sc_err = run_cmd(scene_cmd)
        for line in sc_err.splitlines():
            if "pts_time:" in line:
                m = re.search(r"pts_time:([0-9.]+)", line)
                if m:
                    t = float(m.group(1))
                    if t > 0.3 and (not cuts or t - cuts[-1] > 0.3):
                        cuts.append(round(t, 2))

    if duration <= 0 and cuts:
        duration = cuts[-1] + 2.0
    if duration <= 0:
        duration = 15.0

    total_cuts = len(cuts)
    cpm = round((total_cuts / duration) * 60, 1) if duration > 0 else 0
    avg_shot = round(duration / max(total_cuts, 1), 2)

    if cpm >= 28:
        style_3d = "neon_fast_pace"
        camera_move = "zoom_punch"
        light_style = "rim_neon"
    elif cpm >= 16:
        style_3d = "minimal_clean"
        camera_move = "orbit_smooth"
        light_style = "studio_soft"
    else:
        style_3d = "editorial_cinematic"
        camera_move = "slow_dolly_in"
        light_style = "ambient_dramatic"

    measured_data = {
        "url": url,
        "creador": uploader,
        "titulo": title,
        "duracion_segundos": duration,
        "cortes_detectados": cuts,
        "cortes_por_minuto": cpm,
        "duracion_media_plano": avg_shot,
        "mapeo_3d_deterministico": {
            "estilo": style_3d,
            "movimiento_camara": camera_move,
            "iluminacion": light_style
        }
    }

    log_cb(f"[{folder_name}] Destilando estructura y tipo de render con Ollama...")
    ollama_prompt = f"""Eres un Director de Video y Analista de Retencion. Analiza estos datos de un Reel/TikTok y devuelve un JSON estricto:

Titulo: {title}
Descripcion: {description[:400]}
Duracion: {duration}s
Cortes por minuto: {cpm} (Duracion media plano: {avg_shot}s)
Cortes en segundos: {cuts[:8]}

Responde UNICAMENTE un JSON con esta estructura exacta:
{{
  "tema_principal": "resumen en 1 linea de que trata el video",
  "tipo_render": "2d_pixel_art_game | 3d_procedural | motion_graphics | live_action_real",
  "estilo_visual": "descripcion breve de estetica visual (ej. retro 16-bit, neon dark, minimalista)",
  "gancho": {{
    "tipo": "pregunta | afirmacion_polemica | interrupcion_patron | resultado_primero",
    "duracion_segundos": 3.0,
    "resumen_gancho": "que hace o dice en los primeros 3 segundos"
  }},
  "arco_narrativo": ["gancho", "problema", "desarrollo", "cierre"],
  "ritmo_dopamina": "alto | medio | pausado",
  "leccion_para_nova": "que tecnica de edicion o guion debemos replicar en HyperFrames"
}}"""

    ollama_res = query_ollama(ollama_prompt)

    final_json = {
        "identificador": folder_name,
        "timestamp_procesamiento": time.strftime("%Y-%m-%d %H:%M:%S"),
        "datos_medidos": measured_data,
        "destilacion_ollama": ollama_res
    }

    json_path = os.path.join(folder_path, "datos.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(folder_path, "resumen.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Ficha de Destilacion - {folder_name.upper()}\n\n")
        f.write(f"- **URL:** {url}\n")
        f.write(f"- **Creador:** {uploader}\n")
        f.write(f"- **Tema:** {ollama_res.get('tema_principal', 'N/D')}\n")
        f.write(f"- **Tipo de Render:** `{ollama_res.get('tipo_render', 'N/D')}`\n")
        f.write(f"- **Estilo Visual:** {ollama_res.get('estilo_visual', 'N/D')}\n")
        f.write(f"- **Duracion:** {duration}s | **Ritmo:** {cpm} cortes/min (cada {avg_shot}s)\n\n")
        f.write(f"## 1. Gancho (0 a 3s)\n")
        f.write(f"- **Tipo:** {ollama_res.get('gancho', {}).get('tipo', 'N/D')}\n")
        f.write(f"- **Estrategia:** {ollama_res.get('gancho', {}).get('resumen_gancho', 'N/D')}\n\n")
        f.write(f"## 2. Recomendacion 3D para HyperFrames\n")
        f.write(f"- **Estilo Visual:** `{style_3d}`\n")
        f.write(f"- **Camara Three.js:** `{camera_move}`\n")
        f.write(f"- **Iluminacion:** `{light_style}`\n\n")
        f.write(f"## 3. Leccion de Edicion para Nova\n")
        f.write(f"> {ollama_res.get('leccion_para_nova', 'N/D')}\n")

    if actual_video and os.path.exists(actual_video):
        try:
            os.remove(actual_video)
        except Exception:
            pass
    if os.path.exists(temp_info):
        try:
            os.remove(temp_info)
        except Exception:
            pass

    log_cb(f"[{folder_name}] Guardado OK en {folder_name}/ (datos.json y resumen.md)")
    return final_json


class DestiladorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nova Destilador - Extractor de Reels & TikTok")
        self.root.geometry("740x660")
        self.root.minsize(680, 520)
        self.root.configure(bg="#0f172a")

        self.setup_ui()

    def setup_ui(self):
        # Header azul marino elegante
        header = tk.Frame(self.root, bg="#1e3a8a", padx=20, pady=16)
        header.pack(fill="x")

        lbl_title = tk.Label(
            header,
            text="NOVA DESTILADOR DE VIDEOS",
            font=("Segoe UI", 14, "bold"),
            fg="#ffffff",
            bg="#1e3a8a"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            header,
            text="Procesamiento en segundo plano a 0 tokens cloud · yt-dlp + FFmpeg + Ollama",
            font=("Segoe UI", 9),
            fg="#bfdbfe",
            bg="#1e3a8a"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Contenedor principal
        body = tk.Frame(self.root, bg="#0f172a", padx=20, pady=15)
        body.pack(fill="both", expand=True)

        lbl_inst = tk.Label(
            body,
            text="Pega tus enlaces de TikTok o Instagram (uno por linea):",
            font=("Segoe UI", 10, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        )
        lbl_inst.pack(anchor="w", pady=(0, 6))

        # Caja de texto visible y contrastada
        self.txt_urls = scrolledtext.ScrolledText(
            body,
            height=8,
            bg="#1e293b",
            fg="#ffffff",
            insertbackground="#38bdf8",
            font=("Consolas", 10),
            relief="solid",
            bd=1,
            padx=12,
            pady=10
        )
        self.txt_urls.pack(fill="x", pady=(0, 15))
        self.txt_urls.insert("1.0", "# Pega aqui tus enlaces, por ejemplo:\n# https://www.instagram.com/reel/C...\n# https://www.tiktok.com/@user/video/...\n")

        # Botonera
        btn_frame = tk.Frame(body, bg="#0f172a")
        btn_frame.pack(fill="x", pady=(0, 10))

        self.btn_run = tk.Button(
            btn_frame,
            text="Iniciar Destilacion en Lote",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            padx=22,
            pady=9,
            cursor="hand2",
            command=self.start_batch
        )
        self.btn_run.pack(side="left")

        self.btn_folder = tk.Button(
            btn_frame,
            text="Abrir Carpeta Output",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#f1f5f9",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=9,
            cursor="hand2",
            command=self.open_output_folder
        )
        self.btn_folder.pack(side="right")

        # Estado y progreso
        self.lbl_status = tk.Label(
            body,
            text="Estado: Listo para recibir enlaces.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.lbl_status.pack(anchor="w", pady=(6, 4))

        self.progress = ttk.Progressbar(body, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 12))

        # Consola de log en vivo
        lbl_log = tk.Label(
            body,
            text="Registro de actividad en vivo:",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#0f172a"
        )
        lbl_log.pack(anchor="w", pady=(0, 4))

        self.txt_log = scrolledtext.ScrolledText(
            body,
            height=10,
            bg="#020617",
            fg="#38bdf8",
            font=("Consolas", 9),
            relief="solid",
            bd=1,
            padx=10,
            pady=8
        )
        self.txt_log.pack(fill="both", expand=True)

    def log(self, text):
        def _append():
            self.txt_log.insert(tk.END, f"{text}\n")
            self.txt_log.see(tk.END)
        self.root.after(0, _append)

    def set_status(self, text):
        self.root.after(0, lambda: self.lbl_status.config(text=f"Estado: {text}"))

    def open_output_folder(self):
        if sys.platform == "win32":
            os.startfile(OUTPUT_DIR)
        else:
            subprocess.Popen(["xdg-open", OUTPUT_DIR])

    def start_batch(self):
        raw = self.txt_urls.get("1.0", tk.END).strip().splitlines()
        urls = [line.strip() for line in raw if line.strip() and not line.strip().startswith("#")]

        if not urls:
            messagebox.showwarning("Sin Enlaces", "Por favor pega al menos una URL valida de Instagram o TikTok.")
            return

        self.btn_run.config(state="disabled", text="Procesando en segundo plano...")
        self.progress["maximum"] = len(urls)
        self.progress["value"] = 0

        t = threading.Thread(target=self.run_worker, args=(urls,), daemon=True)
        t.start()

    def run_worker(self, urls):
        processed = 0
        batch_summary = []
        total = len(urls)

        self.log(f"--- Iniciando lote de {total} videos ---")

        for idx, url in enumerate(urls, 1):
            self.set_status(f"Procesando [{idx}/{total}]: {url[:45]}...")
            folder_path, folder_name = get_next_video_dir()
            try:
                res = process_video_url(url, folder_path, folder_name, self.log)
                batch_summary.append(res)
                processed += 1
            except Exception as e:
                self.log(f"[{folder_name}] ERROR: {e}")
            finally:
                self.root.after(0, lambda: self.progress.step(1))

        summary_file = os.path.join(OUTPUT_DIR, "ultimo_lote.json")
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump({
                    "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_procesados": processed,
                    "videos": batch_summary
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        self.set_status("Lote completado con exito.")
        self.log(f"--- Fin: {processed}/{total} videos destilados en output/ ---")
        self.root.after(0, lambda: self.btn_run.config(state="normal", text="Iniciar Destilacion en Lote"))

        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        self.root.after(0, lambda: messagebox.showinfo(
            "Destilacion Completada",
            f"Se han destilado {processed} videos en la carpeta output.\n\n"
            "Ya puedes cerrar esta ventana, volver a Antigravity y decirme:\n"
            "'Nova, revisa lo que aprendimos hoy'."
        ))


if __name__ == "__main__":
    root = tk.Tk()
    app = DestiladorApp(root)
    root.mainloop()
