; tests/Post_request.ahk

#Requires AutoHotkey v2.0

; --- SETTINGS ---
global pythonExe := "python"
global cliScript := "tts_cli.py"
global voiceFile := "../active_voices.txt" ; The shared file from Python
global currentVol := 0.8

; Voice & Engine State (Initialized by LoadVoices)
global voiceList := []
global voiceIndex := 1 
global currentEngine := "online"

; Initial Load
LoadVoices()
; ----------------

; Load function to read the shared file
LoadVoices() {
    global voiceList, voiceIndex
    if !FileExist(voiceFile) {
        ToolTip("Error: " . voiceFile . " not found!")
        SetTimer(() => ToolTip(), -3000)
        return
    }

    try {
        fileContent := FileRead(voiceFile)
        ; Split by newline, omitting empty lines
        voiceList := StrSplit(Trim(fileContent, "`r`n"), "`n", "`r")
        
        if (voiceList.Length == 0) {
            voiceList := ["No voices found"]
        }
        
        voiceIndex := 1 ; Reset to first voice on reload
        ToolTip("Voices Loaded: " . voiceList.Length)
        SetTimer(() => ToolTip(), -1500)
    } catch {
        ToolTip("Failed to read voice file")
        SetTimer(() => ToolTip(), -2000)
    }
}

; Ctrl + Shift + R: Manual Reload of voices (NEW)
^+r:: LoadVoices()

; Ctrl + Shift + X: Stop Playback
^+x:: {
    cmd := pythonExe . ' "' . cliScript . '" --stop'
    Run(cmd, , "Hide")
    ToolTip("TTS Stopped")
    SetTimer(() => ToolTip(), -1000)
}

; Ctrl + Shift + S: Speak Clipboard
^+s:: {
    clip := A_Clipboard
    if (clip = "")
        return

    cleanText := StrReplace(clip, '"', "'")
    currentVoice := voiceList[voiceIndex]
    
    cmd := pythonExe . ' "' . cliScript . '" --text "' . cleanText . '" --voice "' . currentVoice . '" --engine "' . currentEngine . '"'
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
    if (voiceList.Length == 0)
        return
    voiceIndex := (voiceIndex >= voiceList.Length) ? 1 : voiceIndex + 1
    
    newVoice := voiceList[voiceIndex]
    ToolTip("Voice Switched to: " . newVoice)
    SetTimer(() => ToolTip(), -1500)
}

; --- Volume Controls ---
^+Up::   { 
    global currentVol
    currentVol := Round(Min(1.0, currentVol + 0.05), 2)
    SetVolume() 
}
^+Down:: { 
    global currentVol
    currentVol := Round(Max(0.0, currentVol - 0.05), 2)
    SetVolume() 
}

SetVolume() {
    cmd := pythonExe . ' "' . cliScript . '" --volume ' . currentVol
    Run(cmd, , "Hide")
    ToolTip("TTS Volume: " . (currentVol * 100) . "%")
    SetTimer(() => ToolTip(), -1000)
}
