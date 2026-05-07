import logging
from core.TTSFactory import TTSFactory

logger = logging.getLogger("TTS.Manager")

class TTSManager:
    def __init__(self):
        # Default global settings
        self.defaults = {
            "engine": "online",
            "voice": "female_en",
            "volume": 0.8,
            "device": None
        }

    def speak(self, text: str, **kwargs):
        """
        The only method the user needs.
        Usage: 
            manager.speak("Hi") -> Uses all defaults
            manager.speak("Hi", voice="male_jp") -> Overrides only voice
            manager.speak("Hi", engine="offline", volume=1.0) -> Multi-override
        """
        if not text:
            return

        # 1. Merge defaults with user overrides (kwargs)
        # This creates a 'context' for just this one sentence
        ctx = {**self.defaults, **kwargs}

        try:
            # 2. Sync AudioManager settings
            audio = TTSFactory.get_audio_manager()
            audio.set_volume(ctx["volume"])
            if ctx["device"] is not None:
                audio.set_device(ctx["device"])

            # 3. Get the engine (handles internet-check fallback internally)
            engine = TTSFactory.get_engine(ctx["engine"])

            # 4. Fire and forget
            engine.speak(text, voice=ctx["voice"])
            
            logger.info(f"Speaking: [{ctx['engine']}/{ctx['voice']}] '{text[:30]}...'")
            
        except Exception as e:
            logger.error(f"Manager failed to process speak request: {e}")
    

    def set_volume(self, volume: float):
        """
        Directly updates the system volume.
        :param volume: Float between 0.0 and 1.0
        """
        audio = TTSFactory.get_audio_manager()
        audio.set_volume(volume)
        logger.info(f"[TTSManager] Volume updated to {volume * 100:.0f}%")


    def stop(self):
        """Global emergency stop."""
        TTSFactory.get_audio_manager().stop()

    def update_defaults(self, **kwargs):
        """Allow the user to change their 'preferred' setup on the fly."""
        self.defaults.update(kwargs)
        logger.info(f"System defaults updated: {self.defaults}")
