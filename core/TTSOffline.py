# Core/TTSOffline.py
from core.TTSBase import TTSBase
import pyttsx3
import multiprocessing
import sounddevice as sd
import soundfile as sf
import tempfile
import os

def _speak_worker(text, voice_id, device):
    # Generate speech to a temp WAV file
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmpfile.close()

    engine = pyttsx3.init()
    if voice_id:
        engine.setProperty("voice", voice_id)
    engine.save_to_file(text, tmpfile.name)
    engine.runAndWait()

    # Play WAV on chosen device
    data, samplerate = sf.read(tmpfile.name, dtype='int16')
    sd.play(data, samplerate=samplerate, device=device)
    sd.wait()

    os.remove(tmpfile.name)
    print(f"[OfflineTTS] Played on device {device}: {text}")

class TTSOffline(TTSBase): 
    VOICE_MAP = {
        "female_en": "Microsoft Zira Desktop",
        "male_en": "Microsoft David Desktop",
    }

    def __init__(self, default_voice=None, device=None):
        if default_voice in self.VOICE_MAP:
            self.default_voice = default_voice
        else:
            self.default_voice = "female_en"
        self._process = None
        self.device = device

    def set_output_device(self, device):
        """Set output device by index or name (from sd.query_devices())."""
        self.device = device

    def _resolve_voice(self, voice_key: str):
        target_voice = self.VOICE_MAP.get(voice_key)
        print("Resolved voice: ", target_voice)
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
            target=_speak_worker, args=(text, voice_id, self.device)
        )
        self._process.start()
        print(f"[OfflineTTS] Speaking with voice {voice_key} on device {self.device}")

    def stop(self):
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join()
            print("[OfflineTTS] Playback stopped.")