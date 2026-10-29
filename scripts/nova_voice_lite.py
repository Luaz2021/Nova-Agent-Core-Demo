"""
Nova Voice Companion (Community Edition Multiplataforma)
=========================================================
Creado por Saul Alexander Martinez Rivas (@Luaz2021)
Sintetizador ligero de voz neural ejecutiva:
- macOS: Utilidad nativa 'say'
- Linux: 'spd-say' o 'espeak-ng'
- Windows: PowerShell SAPI o edge-tts
"""

import sys
import subprocess
import shutil

def speak(text: str):
    if not text:
        return

    # Limitar a resumen ejecutivo breve (max 300 caracteres)
    resumen = text.strip()[:300]
    
    # 1. macOS (Audio nativo a 0 dependencias)
    if sys.platform == "darwin":
        subprocess.run(["say", "-v", "Monica", resumen], check=False)
        return

    # 2. Linux (Utilidades estandar de accesibilidad)
    if sys.platform.startswith("linux"):
        if shutil.which("spd-say"):
            subprocess.run(["spd-say", "-l", "es", resumen], check=False)
            return
        elif shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", "-v", "es", resumen], check=False)
            return
        elif shutil.which("espeak"):
            subprocess.run(["espeak", "-v", "es", resumen], check=False)
            return

    # 3. Windows (PowerShell SAPI integrado sin librerias externas)
    if sys.platform == "win32":
        clean_text = resumen.replace('"', '""').replace("'", "''")
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$synth.Speak('{clean_text}');"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
        return

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mensaje = " ".join(sys.argv[1:])
        speak(mensaje)
    else:
        print("Uso: python nova_voice_lite.py 'Texto para sintetizar'")
