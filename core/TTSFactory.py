import logging
from core.logging.session_logger import SessionLogger


base_logger = logging.getLogger(__name__)
logger = SessionLogger(base_logger)


class TTSFactory:
    """
    Factory is ONLY responsible for:
    - creating engines
    - caching instances
    - providing shared dependencies (AudioManager)

    It does NOT decide:
    - online/offline fallback
    - voice selection
    - connectivity logic
    """

    _engines = {}
    _audio_manager = None

    # -----------------------------
    # Shared dependency
    # -----------------------------
    @classmethod
    def get_audio_manager(cls):
        if cls._audio_manager is None:
            try:
                from core.AudioManager import AudioManager
                cls._audio_manager = AudioManager()
                logger.info("AudioManager initialized.")
            except Exception:
                logger.exception("Failed to initialize AudioManager.")
                raise

        return cls._audio_manager

    # -----------------------------
    # Engine registry (clean mapping)
    # -----------------------------
    _engine_map = {
        "online": "core.TTSOnline.TTSOnline",
        "offline": "core.TTSOffline.TTSOffline",
    }

    # -----------------------------
    # Engine factory
    # -----------------------------
    @classmethod
    def get_engine(cls, engine_type: str = "online"):
        """
        Returns cached or newly created engine instance.
        """

        # already created → reuse
        if engine_type in cls._engines:
            return cls._engines[engine_type]

        # invalid engine safeguard
        if engine_type not in cls._engine_map:
            logger.warning(
                "Unknown engine '%s', falling back to 'offline'.",
                engine_type
            )
            engine_type = "offline"

        try:
            module_path, class_name = cls._engine_map[engine_type].rsplit(".", 1)

            module = __import__(module_path, fromlist=[class_name])
            engine_class = getattr(module, class_name)

            instance = engine_class(
                player=cls.get_audio_manager()
            )

            cls._engines[engine_type] = instance

            logger.info("%s engine initialized.", engine_type)

            return instance

        except Exception:
            logger.exception("Failed to initialize engine: %s", engine_type)
            raise

    # -----------------------------
    # Utility
    # -----------------------------
    @classmethod
    def reset(cls):
        """Optional: full reset for debugging/testing."""
        cls._engines.clear()
        cls._audio_manager = None