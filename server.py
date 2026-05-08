from fastapi import FastAPI, Body, HTTPException
from core.TTSManager import TTSManager
from core.logging_config import setup_logging
import logging

# 1. Setup professional logging immediately
setup_logging()
logger = logging.getLogger("TTS.Server")

app = FastAPI(title="Edge-TTS & Pyttsx3 Background Service")

try:
    manager = TTSManager()

except Exception as e:
    logger.critical(f"Failed to initialize TTSManager: {e}")
    raise

@app.post("/speak")
def speak(payload: dict = Body(...)):
    text = payload.get("text")
    if not text:
        logger.warning("Received /speak request with no text.")
        raise HTTPException(status_code=400, detail="Text payload is required")

    # Log incoming request details for debugging
    engine = payload.get("engine", "default")
    voice = payload.get("voice", "default")
    logger.debug("========================= Speak Requested =========================")
    
    try:
        manager.speak(**payload)
        return {"status": "request_sent", "payload": payload}
    except Exception as e:
        # This captures the full traceback in your log file!
        logger.exception("Error occurred during manager.speak")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop():
    logger.info("Global stop requested via API.")
    manager.stop()
    return {"status": "stopped"}

@app.post("/volume")
def set_volume(payload: dict = Body(...)):
    vol = payload.get("volume")
    if vol is None:
        logger.warning("Volume request missing 'volume' key.")
        raise HTTPException(status_code=400, detail="Missing volume key")
    
    try:
        vol_float = float(vol)
        if not (0.0 <= vol_float <= 1.0):
            raise ValueError("Out of range")
            
        manager.set_volume(vol_float)
        logger.info(f"Volume updated to: {vol_float}")
        return {"status": "volume_updated", "new_volume": vol_float}
    except ValueError:
        logger.error(f"Invalid volume value received: {vol}")
        raise HTTPException(status_code=400, detail="Volume must be a float between 0.0 and 1.0")

@app.get("/status")
def get_status():
    logger.debug("Status check requested.")
    return {
        "defaults": manager.defaults,
        "system_ready": True
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None) # Use our custom config
