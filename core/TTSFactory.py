# core/TTSFactory.py

class TTSFactory:
    _instances = {}  # Stores singletons: {'online': <TTSOnline>, 'offline': <TTSOffline>}
    _audio_manager = None  # The SINGLE source of truth

    @classmethod
    def get_audio_manager(cls):
        if cls._audio_manager is None:
            from core.AudioManager import AudioManager
            cls._audio_manager = AudioManager()
        return cls._audio_manager

    @classmethod
    def get_engine(cls, engine_type="online"):
        # 1. If online is requested, check connectivity
        if engine_type == "online":
            if not cls._is_internet_available():
                print("[Factory] No internet. Falling back to offline engine.")
                engine_type = "offline"

        manager = cls.get_audio_manager() # Get the shared instance

        # 2. Return existing instance if already created
        if engine_type in cls._instances:
            return cls._instances[engine_type]

        # 3. Otherwise, create and store it (Lazy Loading)
        if engine_type == "online":
            from core.TTSOnline import TTSOnline
            cls._instances["online"] = TTSOnline(player=manager)
        else:
            from core.TTSOffline import TTSOffline
            cls._instances["offline"] = TTSOffline(player=manager)

        return cls._instances[engine_type]

    @staticmethod
    def _is_internet_available():
        import socket
        try:
            # Check connection to a reliable host (like Google DNS)
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
