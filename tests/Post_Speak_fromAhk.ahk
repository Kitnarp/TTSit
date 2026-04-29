#Requires AutoHotkey v2.0

pgdn:: {
    ClipWait
    text := A_Clipboard
    if (text = "")
    {
        MsgBox "Clipboard is empty."
        return
    }

    ; Write clipboard text to a temporary file
    tmpFile := A_Temp "\tts_input.txt"
    FileDelete tmpFile
    FileAppend text, tmpFile, "UTF-8"

    ; Call Python with speakfile option
    RunWait(Format('python "E:\_Scripts\_PYTHON\VoiceTTS\send_tts.py" speakfile "{1}" track1 online male_in', tmpFile), , "Hide")
}

^!a:: {
    ClipWait
    text := A_Clipboard
    if (text = "")
    {
        MsgBox "Clipboard is empty."
        return
    }

    ; Write clipboard text to a temporary file
    tmpFile := A_Temp "\tts_input2.txt"
    FileDelete tmpFile
    FileAppend text, tmpFile, "UTF-8"

    ; Call Python with speakfile option
    RunWait Format('python "E:\_Scripts\_PYTHON\VoiceTTS\send_tts.py" speakfile "{1}" track2 online female_jp', tmpFile), , "Hide"
}

^!x:: {
    RunWait 'python "E:\_Scripts\_PYTHON\VoiceTTS\send_tts.py" stop_all', , "Hide"
}

^!t:: {
    RunWait 'python "E:\_Scripts\_PYTHON\VoiceTTS\send_tts.py" status', , "Hide"
}