import asyncio
import threading
import edge_tts
import time
from core.TTSBase import TTSBase

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
        
        self._loop = None
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._worker_thread.start()
        print(f"[TTSOnline] Background worker started. Default voice: {self.default_voice}")

    def _run_worker(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _resolve_voice(self, voice_key: str) -> str:
        resolved = self.VOICE_MAP.get(voice_key)
        if not resolved:
            resolved = self.VOICE_MAP[self.default_voice]
            print(f"[TTSOnline] Voice '{voice_key}' not found. Falling back to: {resolved}")
        return resolved

    def speak(self, text: str, voice: str = None):
        if not text:
            print("[TTSOnline] Speak requested with empty text. Ignoring.")
            return
        
        print(f"\n[TTSOnline] New Speak Request: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
        
        # Stop existing audio
        self.stop()
        
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._async_speak(text, voice), self._loop)
        else:
            print("[TTSOnline] Error: Async loop is not running.")

    async def _async_speak(self, text: str, voice: str):
        edge_voice = self._resolve_voice(voice)
        print(f"[TTSOnline] Initializing stream with voice: {edge_voice}")
        
        try:
            communicate = edge_tts.Communicate(text, voice=edge_voice)
            start_time = time.time()

            async def byte_generator():
                chunks_received = 0
                async for chunk in communicate.stream():
                    if self.player._stop_event.is_set():
                        print(f"[TTSOnline] Stream interrupted by user after {chunks_received} chunks.")
                        break
                    
                    if chunk["type"] == "audio":
                        if chunks_received == 0:
                            latency = (time.time() - start_time) * 1000
                            print(f"[TTSOnline] First audio chunk received in {latency:.2f}ms")
                        
                        chunks_received += 1
                        yield chunk["data"]

            # Pipe to AudioManager
            await self.player.play_stream(byte_generator(), samplerate=24000)
            print("[TTSOnline] Playback finished successfully.")
                
        except Exception as e:
            print(f"[TTSOnline] CRITICAL ERROR during streaming: {type(e).__name__}: {e}")

    def stop(self):
        """Standardized stop call."""
        if self.player:
            self.player.stop()

    def set_volume(self, volume: float):
        print(f"[TTSOnline] Setting volume to: {volume*100:.0f}%")
        self.player.set_volume(volume)
