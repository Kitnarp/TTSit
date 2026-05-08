import logging
import socket
from core.logging_config import setup_logging

# Use the module path for the logger name
logger = logging.getLogger(__name__)

class TTSFactory:
    _instances = {}  # Stores singletons: {'online': <TTSOnline>, 'offline': <TTSOffline>}
    _audio_manager = None  # The SINGLE source of truth

    @classmethod
    def get_audio_manager(cls):
        if cls._audio_manager is None:
            try:
                from core.AudioManager import AudioManager
                cls._audio_manager = AudioManager()
            except Exception:
                logger.exception("Failed to initialize AudioManager.")
                raise
        return cls._audio_manager

    @classmethod
    def get_engine(cls, engine_type="online"):
        # 1. Connectivity Check for Online Engine
        if engine_type == "online":
            if not cls._is_internet_available():
                logger.warning("No internet connection detected. Falling back to 'offline' engine.")
                engine_type = "offline"

        # 2. Get shared AudioManager
        manager = cls.get_audio_manager()

        # 3. Return existing instance if already created (Cached)
        if engine_type in cls._instances:
            logger.debug("Returning cached %s engine instance.", engine_type)
            return cls._instances[engine_type]

        # 4. Lazy Loading: Create and store if not exists
        logger.info("Lazy loading new %s engine instance...", engine_type)
        try:
            if engine_type == "online":
                from core.TTSOnline import TTSOnline
                cls._instances["online"] = TTSOnline(player=manager)
            else:
                from core.TTSOffline import TTSOffline
                cls._instances["offline"] = TTSOffline(player=manager)
            
            logger.info("%s engine successfully initialized.", engine_type.capitalize())
        except Exception:
            logger.exception("Failed to initialize %s engine.", engine_type)
            raise

        return cls._instances[engine_type]

    @staticmethod
    def _is_internet_available():
        """Checks connectivity to Google DNS with a 2-second timeout."""
        try:
            # socket.create_connection is a blocking call; logger.debug tracks it
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
