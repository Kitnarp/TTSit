# VOICETTS/server.py
from fastapi import FastAPI, Body
from core.ProfileManager import ProfileManager

app = FastAPI()
manager = ProfileManager(config_file="profiles.json")

@app.post("/speak")
def speak(payload: dict = Body(...)):
    """
    Speak using a profile.
    JSON payload fields:
      - profile (required): which profile to use
      - text (required): text to speak
      - engine (optional): override engine
      - voice (optional): override voice
    """
    print("[server.py /speak] payload: ", payload)
    return manager.speak(
        profile=payload.get("profile"),
        text=payload.get("text"),
        engine=payload.get("engine"),
        voice=payload.get("voice")
    )

@app.post("/stop")
def stop(payload: dict = Body(...)):
    """
    Stop playback for a given profile.
    JSON payload fields:
      - profile (required): which profile to stop
    """
    return manager.stop(profile=payload.get("profile"))

@app.post("/stop_all")
def stop_all():
    """Stop playback for all profiles."""
    return manager.stop_all()

@app.get("/status")
def status():
    """Return active profiles and their configs."""
    return manager.status()