#Requires AutoHotkey v2.0

; --- SETTINGS ---
global pythonExe := "python"
global cliScript := "tts_cli.py"
global currentVol := 0.8

; Voice Cycling Setup
global voiceList := ["female_en", "male_en", "male_in", "female_jp", "female_cn"]
global voiceIndex := 1 
; ----------------

; Ctrl + Shift + S: Speak Clipboard
^+s:: {
    clip := A_Clipboard
    if (clip = "")
        return

    cleanText := StrReplace(clip, '"', "'")
    currentVoice := voiceList[voiceIndex]
    
    ; Include the --voice flag in the command
    cmd := pythonExe . ' "' . cliScript . '" --text "' . cleanText . '" --volume ' . currentVol . ' --voice "' . currentVoice . '"'
    Run(cmd, , "Hide")
}

; Ctrl + Shift + V: Cycle Voice
^+v:: {
    global voiceIndex
    voiceIndex := (voiceIndex >= voiceList.Length) ? 1 : voiceIndex + 1
    
    newVoice := voiceList[voiceIndex]
    ToolTip("Voice Switched to: " . newVoice)
    SetTimer(() => ToolTip(), -1500)
}

; Ctrl + Shift + Up/Down: Volume (Keeping previous logic)
^+Up::   { 
    global currentVol
    currentVol := Round(Min(1.0, currentVol + 0.1), 1)
    SetVolume() 
}
^+Down:: { 
    global currentVol
    currentVol := Round(Max(0.0, currentVol - 0.1), 1)
    SetVolume() 
}

SetVolume() {
    cmd := pythonExe . ' "' . cliScript . '" --volume ' . currentVol
    Run(cmd, , "Hide")
    ToolTip("TTS Volume: " . (currentVol * 100) . "%")
    SetTimer(() => ToolTip(), -1000)
}
