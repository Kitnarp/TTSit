import logging
from core.TTSFactory import TTSFactory

# Using __name__ is standard practice for module-level loggers
logger = logging.getLogger(__name__)

class TTSManager:
    def __init__(self):
        # Default global settings
        self.defaults = {
            "engine": "online",
            "voice": "female_en",
            "volume": 0.8,
            "device": None
        }
        logger.info("TTSManager initialized with defaults: %s", self.defaults)

    def speak(self, text: str, **kwargs):
        """
        Orchestrates speech synthesis by merging defaults with overrides.
        """
        if not text:
            logger.warning("Received speak request with empty text. Skipping.")
            return

        # 1. Merge defaults with user overrides
        ctx = {**self.defaults, **kwargs}
        
        # DEBUG level is perfect for seeing the final parameters without cluttering INFO
        logger.debug("Speak context merged: %s", ctx)

        try:
            # 2. Sync AudioManager settings
            audio = TTSFactory.get_audio_manager()
            
            # We log volume and device changes only if they differ or for audit
            audio.set_volume(ctx["volume"])
            if ctx["device"] is not None:
                audio.set_device(ctx["device"])

            # 3. Get the engine (Factory handles internet fallback internally)
            engine = TTSFactory.get_engine(ctx["engine"])

            # 4. Execute speech
            engine.speak(text, voice=ctx["voice"])
            
        except Exception:
            # logger.exception automatically captures the stack trace
            logger.exception("Failed to process speak request for text: '%s...'", text[:30])

    def set_volume(self, volume: float):
        """
        Directly updates the system volume via the shared AudioManager.
        """
        try:
            audio = TTSFactory.get_audio_manager()
            audio.set_volume(volume)
            logger.info("System volume set to %d%%", int(volume * 100))
        except Exception:
            logger.exception("Failed to update system volume.")

    def stop(self):
        """Global emergency stop across all engines."""
        try:
            logger.info("Global stop triggered.")
            TTSFactory.get_audio_manager().stop()
        except Exception:
            logger.exception("Error occurred during global stop.")

    def update_defaults(self, **kwargs):
        """Updates the persistent defaults for future speak calls."""
        old_defaults = self.defaults.copy()
        self.defaults.update(kwargs)
        logger.info("System defaults updated. Changes: %s", 
                    {k: v for k, v in kwargs.items() if old_defaults.get(k) != v})
