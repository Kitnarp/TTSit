import os
import pyttsx3
import threading
import tempfile
import soundfile as sf
import queue
import logging
from core.TTSBase import TTSBase

logger = logging.getLogger(__name__)

class TTSOffline(TTSBase):
    def __init__(self, player, default_voice="female_en"):
        super().__init__()
        self.player = player
        self.VOICE_MAP = {"female_en": "Zira", "male_en": "David"}
        self.default_voice = default_voice
        
        self._voice_id_cache = {}
        self._init_voice_cache()
        
        self._request_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._offline_worker, daemon=True)
        self._worker_thread.start()
        logger.info("Offline Engine (FFmpeg-Compatible) initialized.")

    def _init_voice_cache(self):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            for key, name_match in self.VOICE_MAP.items():
                for v in voices:
                    if name_match.lower() in v.name.lower():
                        self._voice_id_cache[key] = v.id
                        break
            engine.stop()
        except Exception:
            logger.exception("Failed to cache system voices")

    def _offline_worker(self):
        while True:
            text, voice_id, sid = self._request_queue.get()
            
            # 1. Pre-synthesis check
            if sid != self.player._current_session:
                self._request_queue.task_done()
                continue

            temp_path = None
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                if voice_id:
                    engine.setProperty("voice", voice_id)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    temp_path = tmp.name

                logger.info("[%d] Synthesizing offline: '%s...'", sid, text[:40].strip())
                engine.save_to_file(text, temp_path)
                engine.runAndWait() 
                engine.stop()
                del engine 

                # 2. Post-synthesis check: Ensure user hasn't requested a new speak during synthesis
                if sid == self.player._current_session and os.path.exists(temp_path):
                    # Read the generated WAV file
                    data, samplerate = sf.read(temp_path, dtype='int16')
                    
                    # 3. Use play_numpy from the rolled-back AudioManager
                    # This method handles the session validation and async feeding
                    self.player.play_numpy(data, samplerate, sid)
                else:
                    logger.debug("[%d] Discarding synthesis: session no longer active.", sid)

            except Exception:
                logger.exception("[%d] Offline synthesis failed", sid)
            finally:
                if temp_path and os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except: pass
                self._request_queue.task_done()

    def speak(self, text, voice=None):
        if not text: return

        # Capture fresh session ID and stop any current audio
        sid = self.player.stop()
        
        voice_id = self._voice_id_cache.get(voice, self._voice_id_cache.get(self.default_voice))
        self._request_queue.put((text, voice_id, sid))

    def stop(self):
        """Unified stop call."""
        self.player.stop()

    def set_volume(self, volume):
        self.player.set_volume(volume)
