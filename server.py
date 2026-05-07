import logging
from fastapi import FastAPI, Body, HTTPException
from core.TTSManager import TTSManager

# Configure logging at startup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("TTS.Server")

app = FastAPI(title="Edge-TTS & Pyttsx3 Background Service")
manager = TTSManager() # Now using the smart dynamic manager

@app.post("/speak")
def speak(payload: dict = Body(...)):
    """
    Directly triggers a speech request.
    Example JSON:
    {
        "text": "Hello world",
        "voice": "male_en",
        "volume": 0.8,
        "engine": "online"
    }
    """
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Text payload is required")

    logger.info(f"POST /speak received: {text[:30]}...")
    
    # We unpack the dictionary directly into the manager's speak method
    # It will use defaults for any missing keys
    manager.speak(**payload)
    
    return {"status": "request_sent", "payload": payload}

@app.post("/stop")
def stop():
    """Immediately stops any current speech across all engines."""
    logger.info("POST /stop received.")
    manager.stop()
    return {"status": "stopped"}

@app.post("/volume")
def set_volume(payload: dict = Body(...)):
    """
    Updates the system volume on the fly.
    Example JSON: {"volume": 0.5}
    """
    vol = payload.get("volume")
    if vol is None or not (0.0 <= float(vol) <= 1.0):
        raise HTTPException(status_code=400, detail="Volume must be between 0.0 and 1.0")
    
    manager.set_volume(float(vol))
    return {"status": "volume_updated", "new_volume": vol}

@app.get("/status")
def get_status():
    """Returns the current default settings and system state."""
    return {
        "defaults": manager.defaults,
        "system": "online"
    }

if __name__ == "__main__":
    import uvicorn
    # Running uvicorn directly for easy testing
    uvicorn.run(app, host="0.0.0.0", port=8000)
