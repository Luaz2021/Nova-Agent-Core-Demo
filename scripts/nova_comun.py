"""
Nova Comun - utilidades compartidas multiplataforma (Windows / macOS / Linux)
=============================================================================
- nombre_usuario(): lee el nombre de ~/.gemini/antigravity/memory/perfil_usuario.json (lo crea el instalador).
- notificar(titulo, mensaje): aviso de escritorio (toast en Windows, osascript en macOS, notify-send en Linux).
- pitido(): aviso sonoro corto (winsound en Windows, campana de terminal en el resto).
- hablar(texto): voz del sistema (SAPI en Windows, say en macOS, spd-say / espeak-ng / espeak en Linux).
Todo es "mejor esfuerzo": si algo no existe en el equipo, se ignora sin romper a quien lo llama.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

PERFIL = Path.home() / ".gemini" / "antigravity" / "memory" / "perfil_usuario.json"
_SIN_VENTANA = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW


def nombre_usuario(defecto: str = "") -> str:
    """Nombre con el que Nova llama al usuario ('' si no hay perfil)."""
    try:
        nombre = str(json.loads(PERFIL.read_text(encoding="utf-8-sig")).get("nombre", "")).strip()
        return nombre or defecto
    except (OSError, ValueError, AttributeError):
        return defecto


def _lanzar(cmd: list[str]) -> None:
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=_SIN_VENTANA)
    except OSError:
        pass


def _ps_texto(t: str) -> str:
    """Texto seguro para meterlo entre comillas simples de PowerShell."""
    return t.replace("'", "''").replace("\n", " ")


def notificar(titulo: str, mensaje: str) -> None:
    if sys.platform == "win32":
        t, m = _ps_texto(titulo), _ps_texto(mensaje)
        ps = (
            "try { "
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
            "$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            "$n = $tpl.GetElementsByTagName('text'); "
            f"$n.Item(0).AppendChild($tpl.CreateTextNode('{t}')) > $null; "
            f"$n.Item(1).AppendChild($tpl.CreateTextNode('{m}')) > $null; "
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Google.AntigravityIDE').Show("
            "[Windows.UI.Notifications.ToastNotification]::new($tpl)) "
            "} catch { "
            "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
            "$i = New-Object System.Windows.Forms.NotifyIcon; $i.Icon = [System.Drawing.SystemIcons]::Warning; $i.Visible = $true; "
            f"$i.ShowBalloonTip(7000, '{t}', '{m}', [System.Windows.Forms.ToolTipIcon]::Warning); Start-Sleep -Seconds 7; $i.Dispose() }}"
        )
        _lanzar(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps])
    elif sys.platform == "darwin":
        # json.dumps da una cadena con comillas dobles y escapes validos para AppleScript
        _lanzar(["osascript", "-e", f"display notification {json.dumps(mensaje)} with title {json.dumps(titulo)}"])
    elif shutil.which("notify-send"):
        _lanzar(["notify-send", "-u", "normal", titulo, mensaje])


def pitido() -> None:
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(880, 180)
            winsound.Beep(1175, 240)
            return
        except (ImportError, RuntimeError):
            pass
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except (OSError, ValueError):
        pass


def hablar(texto: str) -> None:
    """Voz del sistema, sin bloquear."""
    texto = (texto or "").strip()[:300]
    if not texto:
        return
    if sys.platform == "win32":
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.Speak('{_ps_texto(texto)}')")
        _lanzar(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps])
    elif sys.platform == "darwin":
        _lanzar(["say", texto])
    else:
        for prog, args in (("spd-say", ["-l", "es"]), ("espeak-ng", ["-v", "es"]), ("espeak", ["-v", "es"])):
            if shutil.which(prog):
                _lanzar([prog, *args, texto])
                return
