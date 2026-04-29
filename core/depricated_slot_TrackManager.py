# Core/TrackManager.py

import threading
import json
from Core.TTSFactory import TTSFactory

class TrackManager:
    def __init__(self, config_file="routes.json"):
        # Load track configs from external file
        with open(config_file, "r", encoding="utf-8") as f:
            self.track_configs = json.load(f)

        # Active playback slots
        self.slots = {name: None for name in self.track_configs}

    def speak(self, slot: str, text: str, engine: str = None, voice: str = None):
        if slot not in self.track_configs:
            return {"error": f"Invalid slot '{slot}'"}

        # Stop old playback if slot is occupied
        if self.slots[slot]:
            self.slots[slot]["tts"].stop()

        # Resolve profile: caller may override engine/voice, device is fixed
        config = self.track_configs[slot].copy()
        if engine:
            config["engine"] = engine
        if voice:
            config["voice"] = voice

        # Create TTS instance
        tts = TTSFactory.create(
            engine=config["engine"],
            voice=config["voice"],
            device=config["device"]
        )

        def run():
            tts.speak(text, voice=config["voice"])

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        self.slots[slot] = {"tts": tts, "thread": thread}
        return {
            "status": "playing",
            "slot": slot,
            "engine": config["engine"],
            "voice": config["voice"],
            "device": config["device"],
            "text": text
        }

    def stop(self, slot: str):
        if slot not in self.slots:
            return {"error": f"Invalid slot '{slot}'"}

        if self.slots[slot]:
            self.slots[slot]["tts"].stop()
            self.slots[slot] = None
            return {"status": "stopped", "slot": slot}

        return {"error": f"No active playback in slot '{slot}'"}

    def stop_all(self):
        for slot, entry in self.slots.items():
            if entry:
                entry["tts"].stop()
                self.slots[slot] = None
        return {"status": "stopped_all"}

    def status(self):
        active = [slot for slot, entry in self.slots.items() if entry]
        return {
            "active_slots": active,
            "track_configs": self.track_configs
        }