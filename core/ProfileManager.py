# Core/ProfileManager.py

import threading
import json
from core.TTSFactory import TTSFactory

class ProfileManager:
    def __init__(self, config_file="profiles.json"):
        # Load profiles from external file
        with open(config_file, "r", encoding="utf-8") as f:
            self.profiles = json.load(f)

        # Active playback per profile
        self.active = {name: None for name in self.profiles}
        print(self.active)

    def speak(self, profile: str, text: str, engine: str = None, voice: str = None):
        if profile not in self.profiles:
            return {"error": f"Invalid profile '{profile}'"}

        if self.active[profile]:
            self.active[profile]["tts"].stop()

        config = self.profiles[profile].copy()
        config["engine"] = engine or config.get("engine", "offline")
        config["voice"]  = voice or config.get("voice", "female_en_us")

        tts = TTSFactory.create(
            engine=config["engine"],
            voice=config["voice"],
            device=config["device"]
        )

        def run():
            tts.speak(text, voice=config["voice"])

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        self.active[profile] = {"tts": tts, "thread": thread}
        return {
            "status": "playing",
            "profile": profile,
            "engine": config["engine"],
            "voice": config["voice"],
            "device": config["device"],
            "text": text
        }

    def stop(self, profile: str):
        if profile not in self.active:
            return {"error": f"Invalid profile '{profile}'"}

        if self.active[profile]:
            self.active[profile]["tts"].stop()
            self.active[profile] = None
            return {"status": "stopped", "profile": profile}

        return {"error": f"No active playback in profile '{profile}'"}

    def stop_all(self):
        for profile, entry in self.active.items():
            if entry:
                entry["tts"].stop()
                self.active[profile] = None
                print("[ProfileManager: Stoped all]")
        return {"status": "stopped_all"}

    def status(self):
        active_profiles = [p for p, entry in self.active.items() if entry]
        return {
            "active_profiles": active_profiles,
            "profiles": self.profiles
        }