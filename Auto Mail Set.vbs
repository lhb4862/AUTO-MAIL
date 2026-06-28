Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder

Function RunHidden(command)
    On Error Resume Next
    shell.Run command, 0, False
    RunHidden = (Err.Number = 0)
    Err.Clear
End Function

If RunHidden("pythonw settings_gui.py") Then
    WScript.Quit 0
End If

If RunHidden("pyw -3 settings_gui.py") Then
    WScript.Quit 0
End If

MsgBox "Python is not installed or pythonw was not found." & vbCrLf & vbCrLf & "Install Python and add it to PATH.", vbCritical, "AUTO-MAIL"
