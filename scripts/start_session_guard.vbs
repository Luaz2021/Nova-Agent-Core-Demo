' 11/11 (Claude): arranca el guardian de sesion SIN ninguna ventana (ni cmd ni Windows Terminal).
' Con Windows Terminal como consola por defecto, "powershell -WindowStyle Hidden" lanzado por WMI abria una ventana;
' desde wscript con estilo 0 no se ve nada. Uso: wscript.exe "<NOVA_HOME>\antigravity\scripts\start_session_guard.vbs"
Set WshShell = CreateObject("WScript.Shell")
perfil = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & perfil & "\.gemini\antigravity\scripts\session_guard.ps1""", 0, False
