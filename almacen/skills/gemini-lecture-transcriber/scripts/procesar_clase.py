import sys
import os
import argparse
import subprocess
import imageio_ffmpeg
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence

def procesar_video(video_path, output_dir=None, borrar_video=False):
    if not os.path.exists(video_path):
        print(f"[!] Error: El archivo no existe: {video_path}")
        return False

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    if output_dir is None:
        output_dir = os.path.dirname(video_path)

    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, f"{base_name}.mp3")
    wav_path = os.path.join(output_dir, f"{base_name}_temp.wav")
    transcript_path = os.path.join(output_dir, f"{base_name}_transcripcion.txt")

    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    
    # 1. Si no existe el mp3, lo extraemos
    if not os.path.exists(audio_path):
        print(f"[*] 1. Extrayendo audio mp3 con FFmpeg...")
        cmd_ffmpeg = [
            ffmpeg_bin, "-y", "-i", video_path,
            "-vn", "-acodec", "libmp3lame", "-q:a", "4",
            audio_path
        ]
        res = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"[!] Error FFmpeg: {res.stderr.decode('utf-8', errors='ignore')}")
            return False
        print(f"[+] Audio extraído con éxito: {audio_path}")
    else:
        print(f"[+] Audio mp3 ya existente: {audio_path}")

    # 2. Transcripción por chunks de voz (sin descargas de modelos pesados)
    print(f"[*] 2. Preparando audio para reconocimiento de voz...")
    cmd_wav = [
        ffmpeg_bin, "-y", "-i", audio_path,
        "-ac", "1", "-ar", "16000",
        wav_path
    ]
    subprocess.run(cmd_wav, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    recognizer = sr.Recognizer()
    
    print(f"[*] 3. Transcribiendo bloques de audio a texto...")
    # Dividir el audio en trozos de 60 segundos para transcribir
    sound = AudioSegment.from_wav(wav_path)
    chunk_length_ms = 60 * 1000  # 60 segundos
    chunks = [sound[i:i + chunk_length_ms] for i in range(0, len(sound), chunk_length_ms)]

    full_transcript = []
    temp_chunk_file = os.path.join(output_dir, "chunk_temp.wav")

    for idx, chunk in enumerate(chunks):
        chunk.export(temp_chunk_file, format="wav")
        with sr.AudioFile(temp_chunk_file) as source:
            audio_listened = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_listened, language="es-ES")
                full_transcript.append(text)
                print(f"[Minuto {idx + 1}/{len(chunks)}] {text[:80]}...")
            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"[Minuto {idx + 1}] Error en bloque: {e}")

    # Limpiar temporales
    if os.path.exists(wav_path):
        os.remove(wav_path)
    if os.path.exists(temp_chunk_file):
        os.remove(temp_chunk_file)

    texto_final = "\n".join(full_transcript)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(texto_final)

    print(f"\n[+] ¡Transcripción completada con éxito! Guardada en:\n    {transcript_path}")

    if borrar_video:
        try:
            os.remove(video_path)
            print(f"[+] Video original eliminado para ahorrar espacio: {video_path}")
        except Exception as e:
            print(f"[!] No se pudo borrar el video: {e}")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extractor y transcriptor de clases universitarias")
    parser.add_argument("video", help="Ruta al video descargado (.mp4, .mkv, etc.)")
    parser.add_argument("--output", "-o", default=None, help="Carpeta de salida")
    parser.add_argument("--borrar", "-b", action="store_true", help="Borrar video original tras extraer audio")

    args = parser.parse_args()
    procesar_video(args.video, args.output, args.borrar)
