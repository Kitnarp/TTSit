#Requires AutoHotkey v2.0

; --- SETTINGS ---
global pythonExe := "python"
global cliScript := "tts_cli.py"
global currentVol := 0.8

; Voice & Engine State
global voiceList := ["female_en", "male_en", "male_in", "female_jp", "female_cn"]
global voiceIndex := 1 
global currentEngine := "online" ; Default engine
; ----------------

; Ctrl + Shift + S: Speak Clipboard
^+s:: {
    clip := A_Clipboard
    if (clip = "")
        return

    cleanText := StrReplace(clip, '"', "'")
    currentVoice := voiceList[voiceIndex]
    
    ; Pass both --voice and --engine to the CLI
    cmd := pythonExe . ' "' . cliScript . '" --text "' . cleanText . '" --volume ' . currentVol . ' --voice "' . currentVoice . '" --engine "' . currentEngine . '"'
    Run(cmd, , "Hide")
}

; Ctrl + Shift + E: Toggle Engine (Online <-> Offline)
^+e:: {
    global currentEngine
    currentEngine := (currentEngine == "online") ? "offline" : "online"
    
    ToolTip("Engine Switched to: " . StrUpper(currentEngine))
    SetTimer(() => ToolTip(), -1500)
}

; Ctrl + Shift + V: Cycle Voice
^+v:: {
    global voiceIndex
    voiceIndex := (voiceIndex >= voiceList.Length) ? 1 : voiceIndex + 1
    
    newVoice := voiceList[voiceIndex]
    ToolTip("Voice Switched to: " . newVoice)
    SetTimer(() => ToolTip(), -1500)
}

; --- Volume Controls ---
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
