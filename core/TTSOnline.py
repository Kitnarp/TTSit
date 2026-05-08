import asyncio
import threading
import edge_tts
import time
import logging
from core.TTSBase import TTSBase

logger = logging.getLogger(__name__)

class TTSOnline(TTSBase):
    VOICE_MAP = {
        "female_en": "en-US-AriaNeural",
        "male_en": "en-US-AndrewNeural",
        "male_in": "en-IN-PrabhatNeural",
        "female_jp": "ja-JP-NanamiNeural",
        "male_jp": "ja-JP-KeitaNeural",
        "female_cn": "zh-CN-XiaoxiaoNeural",
    }

    def __init__(self, player, default_voice="female_en"):
        super().__init__()
        self.player = player
        self.default_voice = default_voice if default_voice in self.VOICE_MAP else "female_en"
        
        self._current_task = None
        self._lock = threading.Lock()
        
        self._loop = None
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._worker_thread.start()
        logger.info("Online Engine (FFmpeg-Stream) initialized.")

    def _run_worker(self):
        """Dedicated background loop for network and synthesis."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _resolve_voice(self, voice_key: str) -> str:
        return self.VOICE_MAP.get(voice_key, self.VOICE_MAP.get(self.default_voice, "en-US-AriaNeural"))

    def speak(self, text: str, voice: str = None):
        """Entry point for new speech requests."""
        if not text: return
        
        with self._lock:
            # 1. Increment session ID and abort current hardware playback
            target_sid = self.player.stop()

            # 2. Cancel the previous async task immediately
            if self._current_task and not self._current_task.done():
                # We use a lambda to ensure the cancel call happens on the worker loop
                self._loop.call_soon_threadsafe(lambda: self._current_task.cancel())

            # 3. Schedule the new speech coroutine
            if self._loop and self._loop.is_running():
                logger.info("[%d] New Speak Request: '%s...'", target_sid, text[:40].strip())
                coro = self._async_speak(text, voice, target_sid)
                self._current_task = asyncio.run_coroutine_threadsafe(coro, self._loop)
            else:
                logger.error("Async worker loop is not running.")

    async def _async_speak(self, text: str, voice: str, session_id: int):
        """Async internal logic for streaming from EdgeTTS."""
        edge_voice = self._resolve_voice(voice)
        start_time = time.perf_counter()
        
        try:
            communicate = edge_tts.Communicate(text, voice=edge_voice)
            
            async def byte_generator():
                """Feeds chunks to the player; aborts instantly if session changes."""
                first_chunk = True
                async for chunk in communicate.stream():
                    # CRITICAL: Stop requesting data from web if a new speak() arrived
                    if session_id != self.player._current_session:
                        logger.debug("[%d] Aborting network stream: session stale.", session_id)
                        return
                        
                    if chunk["type"] == "audio":
                        if first_chunk:
                            latency = (time.perf_counter() - start_time) * 1000
                            logger.debug("[%d] First chunk latency: %.2fms", session_id, latency)
                            first_chunk = False
                        yield chunk["data"]

            # Hand off to the session-aware player
            await self.player.play_stream(byte_generator(), session_id=session_id, samplerate=24000)
                
        except asyncio.CancelledError:
            logger.debug("[%d] Async speak task cancelled.", session_id)
        except Exception:
            logger.exception("[%d] TTSOnline Error", session_id)

    def stop(self):
        """Stops the current task and the player."""
        with self._lock:
            if self._current_task and not self._current_task.done():
                self._loop.call_soon_threadsafe(lambda: self._current_task.cancel())
            self.player.stop()

    def set_volume(self, volume: float):
        """Implements abstract method from TTSBase."""
        self.player.set_volume(volume)
