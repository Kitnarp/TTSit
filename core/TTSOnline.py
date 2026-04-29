# Core/TTSOnline.py
from core.TTSBase import TTSBase
import asyncio
import edge_tts
import threading
import socket
from core.audio_player import AudioPlayer

def has_internet(host="8.8.8.8", port=53, timeout=3):
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
        "male_in": "en-IN-PrabhatNeural",
        "female_jp": "ja-JP-NanamiNeural",
        "male_jp": "ja-JP-KeitaNeural",
        "female_cn": "zh-CN-XiaoxiaoNeural",
    }

    def __init__(self, default_voice="female_en", device=None):
        if default_voice in self.VOICE_MAP:
            self.default_voice = default_voice
        else:
            self.default_voice = "female_en"

        self._play_thread = None
        self._stop_requested = False
        self.player = AudioPlayer(device=device)

    def _resolve_voice(self, voice_key: str) -> str:
        if voice_key in self.VOICE_MAP:
            return self.VOICE_MAP[voice_key]
        if self.default_voice in self.VOICE_MAP:
            print(f"[TTSOnline] Unknown voice '{voice_key}', falling back to default '{self.default_voice}'.")
            return self.VOICE_MAP[self.default_voice]
        first_voice = next(iter(self.VOICE_MAP.values()))
        print(f"[TTSOnline] Unknown voice '{voice_key}', no valid default, using '{first_voice}'.")
        return first_voice

    def speak(self, text: str, voice: str = None):
        print(f"Voice received: {voice}")
        # print(self.player.list_devices())

        def run():
            async def inner():
                edge_voice = self._resolve_voice(voice)
                communicate = edge_tts.Communicate(text, voice=edge_voice)

                async def audio_chunks():
                    async for chunk in communicate.stream():
                        if self._stop_requested:
                            break
                        if chunk["type"] == "audio":
                            # print(f"[TTSOnline] Got audio chunk of {len(chunk['data'])} bytes")
                            yield chunk["data"]

                await self.player.play_stream(audio_chunks())
                print("[TTSOnline] Finished streaming playback.")


            asyncio.run(inner())
            # async def test():
            #     communicate = edge_tts.Communicate("This is a longer sentence to test streaming.", voice="en-US-AriaNeural")
            #     async for chunk in communicate.stream():
            #         print("[EdgeTTS]", chunk["type"], len(chunk.get("data", b"")))
            # asyncio.run(test())


        self._stop_requested = False
        self._play_thread = threading.Thread(target=run, daemon=True)
        self._play_thread.start()
        print(f"[TTSOnline] Speaking (stream via sounddevice): {text}")

    def stop(self):
        self._stop_requested = True
        self.player.stop()
        print("[TTSOnline] Stop requested.")