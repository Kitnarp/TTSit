# Core/TTSFactory.py

from core.TTSOnline import TTSOnline
from core.TTSOffline import TTSOffline
import socket

def has_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


class TTSFactory:
    @staticmethod
    def create(engine: str = "offline", voice: str = None, device=None):
        if engine == "online":
            if has_internet():
                return TTSOnline(default_voice=voice, device=device)
            else:
                print("[TTSFactory] ERROR: No internet connection! using offline engine!")
                return TTSOffline(default_voice=voice, device=device)
        elif engine == "offline":
            return TTSOffline(default_voice=voice, device=device)
        else:
            raise ValueError(f"Unknown TTS engine: {engine}")