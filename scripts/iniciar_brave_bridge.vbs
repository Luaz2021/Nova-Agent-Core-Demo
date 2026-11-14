' Lanza el puente Nova <-> Brave (v3.1) en segundo plano, desde la copia LOCAL.
' Si ya hay un puente escuchando en 5005, el nuevo no puede abrir el puerto y se cierra solo.
Set WshShell = CreateObject("WScript.Shell")
script = WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.gemini\antigravity\scripts\nova_brave_bridge_v3.py"
WshShell.Run "pythonw.exe """ & script & """", 0, False
