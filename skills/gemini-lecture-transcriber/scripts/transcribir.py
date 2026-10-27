import os
import sys
import argparse
import subprocess
import imageio_ffmpeg
from faster_whisper import WhisperModel

def transcribir_archivo(input_path, output_dir=None, model_size="tiny", device="cpu", compute_type="int8", borrar_video=False):
    if not os.path.exists(input_path):
        print(f"[!] Error: El archivo no existe: {input_path}")
        return False

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1].lower()

    if output_dir is None:
        output_dir = os.path.dirname(input_path)
    os.makedirs(output_dir, exist_ok=True)

    audio_path = input_path
    
    # 1. Si es video, extraer mp3 ligero
    if ext in [".mp4", ".mkv", ".mov", ".avi", ".webm"]:
        audio_path = os.path.join(output_dir, f"{base_name}.mp3")
        if not os.path.exists(audio_path):
            print(f"[*] 1. Extrayendo audio MP3 del video...")
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_bin, "-y", "-i", input_path,
                "-vn", "-acodec", "libmp3lame", "-q:a", "4",
                audio_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode != 0:
                print(f"[!] Error al extraer audio con ffmpeg")
                return False
            print(f"[+] Audio extraído: {audio_path}")
        else:
            print(f"[+] Reutilizando audio ya existente: {audio_path}")

    # 2. Transcripción con Faster-Whisper
    txt_output = os.path.join(output_dir, f"{base_name}_transcripcion.txt")
    print(f"[*] 2. Cargando modelo Faster-Whisper '{model_size}'...")
    
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"[*] 3. Transcribiendo audio a texto (en español)...")
        segments, info = model.transcribe(audio_path, language="es", beam_size=5)

        lineas = []
        for segment in segments:
            minuto = int(segment.start // 60)
            segundo = int(segment.start % 60)
            timestamp = f"[{minuto:02d}:{segundo:02d}]"
            linea = f"{timestamp} {segment.text.strip()}"
            lineas.append(linea)
            print(linea)

        texto_completo = "\n".join(lineas)
        with open(txt_output, "w", encoding="utf-8") as f:
            f.write(texto_completo)

        print(f"\n[+] ¡FINALIZADO CON ÉXITO!")
        print(f"[+] Archivo de transcripción generado:\n    {txt_output}")

    except Exception as e:
        print(f"[!] Error durante la transcripción: {e}")
        return False

    # 3. Borrar video si se solicita
    if borrar_video and ext in [".mp4", ".mkv", ".mov", ".avi", ".webm"]:
        try:
            os.remove(input_path)
            print(f"[+] Video original eliminado: {input_path}")
        except Exception as e:
            print(f"[!] No se pudo borrar el video: {e}")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcriptor local ultra-rápido de clases universitarias")
    parser.add_argument("archivo", help="Ruta al video o audio (.mp4, .mp3, etc.)")
    parser.add_argument("--output", "-o", default=None, help="Carpeta de salida")
    parser.add_argument("--modelo", "-m", default="tiny", choices=["tiny", "base", "small"], help="Tamaño del modelo Whisper")
    parser.add_argument("--borrar", "-b", action="store_true", help="Borrar video original tras extraer audio")

    args = parser.parse_args()
    transcribir_archivo(args.archivo, args.output, args.modelo, borrar_video=args.borrar)
