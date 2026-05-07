import os
import pyttsx3
import threading
import tempfile
import soundfile as sf
import queue
import time
from core.TTSBase import TTSBase

class TTSOffline(TTSBase):
    def __init__(self, player, default_voice="female_en"):
        super().__init__()
        self.player = player
        self.VOICE_MAP = {"female_en": "Zira", "male_en": "David"}
        self.default_voice = default_voice
        
        # Voice Cache
        print("[TTSOffline] Initializing voice cache...")
        self._voice_id_cache = {}
        self._init_voice_cache()
        
        # Dedicated Worker for pyttsx3 to keep COM objects stable
        self._request_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._offline_worker, daemon=True)
        self._worker_thread.start()
        print(f"[TTSOffline] Background worker started. Default voice: {self.default_voice}")

    def _init_voice_cache(self):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            for key, name_match in self.VOICE_MAP.items():
                for v in voices:
                    if name_match.lower() in v.name.lower():
                        self._voice_id_cache[key] = v.id
                        print(f"[TTSOffline] Cached voice: {key} -> {v.name}")
                        break
            engine.stop()
        except Exception as e:
            print(f"[TTSOffline] Error during voice cache initialization: {e}")

    def _offline_worker(self):
        """Refactored worker that re-initializes the engine for every call."""
        print("[TTSOffline] Worker thread is ready.")
        
        while True:
            text, voice_id = self._request_queue.get()
            print(f"[TTSOffline] Processing: \"{text[:40]}...\"")
            
            temp_path = None
            try:
                # 1. Initialize engine FRESH for this specific request
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                if voice_id:
                    engine.setProperty("voice", voice_id)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    temp_path = tmp.name

                # 2. Synthesis
                engine.save_to_file(text, temp_path)
                engine.runAndWait() 
                
                # 3. CRITICAL: Stop and delete the engine to release COM resources
                engine.stop()
                del engine 

                # Playback logic remains the same
                if not self.player._stop_event.is_set() and os.path.exists(temp_path):
                    data, samplerate = sf.read(temp_path, dtype='int16')
                    self.player.play_numpy(data, samplerate)

            except Exception as e:
                print(f"[TTSOffline] Worker Error: {e}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except: pass
                self._request_queue.task_done()


    def speak(self, text, voice=None):
        """Queues the request for the worker thread."""
        if not text:
            print("[TTSOffline] Empty text received. Skipping.")
            return

        # 1. Stop current audio
        self.stop()
        
        # 2. Resolve voice
        voice_id = self._voice_id_cache.get(voice)
        if not voice_id:
            voice_id = self._voice_id_cache.get(self.default_voice)
            if voice: # Only print if they actually requested a specific voice that failed
                print(f"[TTSOffline] Voice '{voice}' not found, using default.")

        # 3. Queue request
        print(f"\n[TTSOffline] New Speak Request (Offline): {text[:50]}...")
        self._request_queue.put((text, voice_id))

    def stop(self):
        """Standardized stop call."""
        if self.player:
            self.player.stop()

    def set_volume(self, volume):
        print(f"[TTSOffline] Setting volume to: {volume*100:.0f}%")
        self.player.set_volume(volume)
