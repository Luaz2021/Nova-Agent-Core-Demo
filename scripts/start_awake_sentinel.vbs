Set WshShell = CreateObject("WScript.Shell")
' v3.2: rutas del equipo del usuario (antes apuntaba al Drive privado del autor: G:\Mi unidad\...)
perfil = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
pyw = WshShell.ExpandEnvironmentStrings("%NOVA_PYTHONW%")
If pyw = "%NOVA_PYTHONW%" Or pyw = "" Then pyw = "pythonw.exe"
WshShell.Run """" & pyw & """ """ & perfil & "\.gemini\antigravity\scripts\nova_awake_sentinel.py""", 0, False