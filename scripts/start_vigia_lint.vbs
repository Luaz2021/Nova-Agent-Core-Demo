Set WshShell = CreateObject("WScript.Shell")
' 11/11 (Claude): rutas de ESTE equipo (antes iba "Alexander Martinez" y el Python de la laptop a mano)
perfil = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
pyw = WshShell.ExpandEnvironmentStrings("%NOVA_PYTHONW%")
If pyw = "%NOVA_PYTHONW%" Or pyw = "" Then pyw = "pythonw.exe"
WshShell.Run """" & pyw & """ """ & perfil & "\.gemini\nova_core\vigia_lint.py""", 0, False
