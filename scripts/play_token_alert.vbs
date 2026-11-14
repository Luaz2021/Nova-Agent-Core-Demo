' Script de Alerta por Voz Nativa de Windows para Nova
' Ejecutado silenciosamente via wscript.exe sin ventanas negras ni dependencias
Dim voiceText
If WScript.Arguments.Count > 0 Then
    voiceText = WScript.Arguments(0)
Else
    voiceText = "Atencion Alexander: La sesion ha superado el limite optimo de tokens. El puente esta guardado en Drive para saltar a una ventana limpia."
End If

On Error Resume Next
Set s = CreateObject("SAPI.SpVoice")
For Each v In s.GetVoices
    If InStr(v.GetDescription, "Helena") > 0 Then
        Set s.Voice = v
        Exit For
    End If
Next
s.Volume = 100
s.Speak voiceText
