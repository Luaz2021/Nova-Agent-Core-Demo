import sys
import re
import os
import json
import subprocess

def get_youtube_id(url):
    pattern = r'(?:v=|\/|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def transcribe_youtube(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en', 'es-419', 'auto'])
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
    except Exception as e:
        return None

def transcribe_ytdlp(url, output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--write-auto-sub", "--write-sub",
            "--sub-lang", "es,en",
            "--skip-download",
            "--sub-format", "vtt/srt/best",
            "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        return False

def clean_vtt(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Quitar marcas de tiempo y tags VTT
    lines = content.splitlines()
    clean_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('WEBVTT') or '-->' in line or line.isdigit():
            continue
        line = re.sub(r'<[^>]+>', '', line)
        if line and line not in seen:
            seen.add(line)
            clean_lines.append(line)
    return " ".join(clean_lines)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No URL provided"}))
        sys.exit(1)
        
    url = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "G:\\Mi unidad\\Antigravity\\transcripts"
    
    # 1. Intentar por YouTube Transcript API si es de YouTube
    yt_id = get_youtube_id(url)
    if yt_id:
        text = transcribe_youtube(yt_id)
        if text:
            filename = f"youtube_{yt_id}.txt"
            path = os.path.join(out_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(json.dumps({"success": True, "file": path, "length": len(text)}))
            sys.exit(0)
            
    # 2. Intentar con yt-dlp para otras plataformas (Instagram, etc.)
    success = transcribe_ytdlp(url, out_dir)
    print(json.dumps({"success": success, "note": "Procesado mediante extractor universal"}))
