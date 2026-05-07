# Core/TTSBase.py
from abc import ABC, abstractmethod


class TTSBase(ABC):
    @abstractmethod
    def speak(self, text: str, voice: str = None):
        """Start speaking text asynchronously (non-blocking)."""
        pass

    @abstractmethod
    def stop(self):
        """Stop playback immediately."""
        pass

    @abstractmethod
    def set_volume(self, value):
        pass