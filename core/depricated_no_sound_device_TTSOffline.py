# Core/TTSOffline.py
from Core.TTSBase import TTSBase
import pyttsx3
import multiprocessing


def _speak_worker(text, voice_id):
    engine = pyttsx3.init()
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.say(text)
    engine.runAndWait()


class TTSOffline(TTSBase):
    VOICE_MAP = {
        "female_en": "Microsoft Zira Desktop",
        "male_en": "Microsoft David Desktop",
    }

    def __init__(self, default_voice="female_en_us"):
        self.default_voice = default_voice
        self._process = None

    def _resolve_voice(self, voice_key: str):
        target_voice = self.VOICE_MAP.get(voice_key)
        engine = pyttsx3.init()
        for v in engine.getProperty("voices"):
            if target_voice and target_voice in v.name:
                return v.id
        return None

    def speak(self, text: str, voice: str = None):
        voice_key = voice or self.default_voice
        voice_id = self._resolve_voice(voice_key)

        # Kill any previous process
        if self._process and self._process.is_alive():
            self.stop()

        self._process = multiprocessing.Process(
            target=_speak_worker, args=(text, voice_id)
        )
        self._process.start()
        print(f"[OfflineTTS] Spoke with voice {voice_key}: {text}")

    def stop(self):
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join()
            print("[OfflineTTS] Playback stopped.")