# Core/TTSOnline.py

from Core.TTSBase import TTSBase
from Core.TTSOffline import TTSOffline

import os
import threading
import asyncio
import edge_tts
import tempfile
import socket

from pydub import AudioSegment
import simpleaudio as sa


def has_internet(host="8.8.8.8", port=53, timeout=3):
    """Quick connectivity check by attempting a socket connection."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


class TTSOnline(TTSBase):
    VOICE_MAP = {
        "female_en": "en-US-AriaNeural",
        "male_en": "en-US-AndrewNeural",
        "female_jp": "ja-JP-NanamiNeural",
        "male_jp": "ja-JP-KeitaNeural",
        "male_in": "en-IN-PrabhatNeural",
    }

    def __init__(self, default_voice="female_en"):
        self.default_voice = default_voice
        self._play_thread = None
        self._stop_requested = False
        self._offline_fallback = None
        self._play_obj = None  # simpleaudio playback object

    def _resolve_voice(self, voice_key: str):
        """Safely resolve a voice key to an Edge TTS voice ID."""
        # Try requested voice
        voice_id = self.VOICE_MAP.get(voice_key)
        if voice_id:
            return voice_id

        # Fallback to default voice
        default_id = self.VOICE_MAP.get(self.default_voice)
        if default_id:
            return default_id

        # Final fallback: pick the first available voice
        return next(iter(self.VOICE_MAP.values()), None)

    def speak(self, text: str, voice: str = None):
        if not has_internet():
            print("[TTSOnline] No internet, falling back to Offline TTS.")
            self._offline_fallback = TTSOffline(default_voice=self.default_voice)
            self._offline_fallback.speak(text, voice=voice)
            return

        def run():
            async def inner():
                voice_key = voice or self.default_voice
                edge_voice = self._resolve_voice(voice_key)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    filename = tmp.name

                communicate = edge_tts.Communicate(text, voice=edge_voice)
                await communicate.save(filename)
                print("Finish Speech")

                # Decode MP3 and play with simpleaudio
                sound = AudioSegment.from_mp3(filename)
                self._play_obj = sa.play_buffer(
                    sound.raw_data,
                    num_channels=sound.channels,
                    bytes_per_sample=sound.sample_width,
                    sample_rate=sound.frame_rate
                )

                # Wait for playback or stop request
                while self._play_obj.is_playing():
                    if self._stop_requested:
                        self._play_obj.stop()
                        break

                os.remove(filename)

            asyncio.run(inner())

        self._stop_requested = False
        self._offline_fallback = None
        self._play_thread = threading.Thread(target=run, daemon=True)
        self._play_thread.start()
        print(f"[TTSOnline] Speaking: {text}")

    def stop(self):
        if self._offline_fallback:
            self._offline_fallback.stop()
            print("[TTSOnline] Stopped offline fallback playback.")
        else:
            self._stop_requested = True
            if self._play_obj:
                self._play_obj.stop()
            print("[TTSOnline] Stop requested (online).")