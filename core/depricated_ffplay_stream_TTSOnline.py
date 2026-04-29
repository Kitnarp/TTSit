# Core/TTSOnline

import asyncio
import edge_tts
import subprocess
import threading
import socket

def has_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


class TTSOnline:
    VOICE_MAP = {
        "female_en": "en-US-AriaNeural",
        "male_en": "en-US-AndrewNeural",
        "male_in": "en-IN-PrabhatNeural",
        "female_jp": "ja-JP-NanamiNeural",
        "male_jp": "ja-JP-KeitaNeural",
        "female_cn": "zh-CN-XiaoxiaoNeural",

    }

    def __init__(self, default_voice="female_en"):
        self.default_voice = default_voice
        self._play_thread = None
        self._stop_requested = False
        self._ffmpeg_proc = None

    def _resolve_voice(self, voice_key: str) -> str:
        # Try requested voice
        if voice_key in self.VOICE_MAP:
            return self.VOICE_MAP[voice_key]

        # Fallback to default voice if valid
        if self.default_voice in self.VOICE_MAP:
            print(f"[TTSOnline] Unknown voice '{voice_key}', falling back to default '{self.default_voice}'.")
            return self.VOICE_MAP[self.default_voice]

        # Final fallback: pick the first available voice
        first_voice = next(iter(self.VOICE_MAP.values()))
        print(f"[TTSOnline] Unknown voice '{voice_key}', no valid default, using '{first_voice}'.")
        return first_voice

    def speak(self, text: str, voice: str = None):
        if not has_internet():
            print("[TTSOnline] No internet, cannot stream.")
            return

        def run():
            async def inner():
                edge_voice = self._resolve_voice(voice)
                communicate = edge_tts.Communicate(text, voice=edge_voice)

                # Launch ffplay to decode MP3 from stdin
                self._ffmpeg_proc = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )


                print("Started ffplay, PID:", self._ffmpeg_proc.pid)


                async for chunk in communicate.stream():
                    if self._stop_requested:
                        break
                    if chunk["type"] == "audio" and self._ffmpeg_proc.stdin:
                        try:
                            self._ffmpeg_proc.stdin.write(chunk["data"])
                        except BrokenPipeError:
                            break

                if self._ffmpeg_proc:
                    try:
                        self._ffmpeg_proc.stdin.close()
                    except Exception:
                        pass
                    self._ffmpeg_proc.wait()

                print("[TTSOnline] Finished streaming speech.")

            asyncio.run(inner())

        self._stop_requested = False
        self._play_thread = threading.Thread(target=run, daemon=True)
        self._play_thread.start()
        print(f"[TTSOnline] Speaking (stream via ffplay): {text}")

    def stop(self):
        self._stop_requested = True
        if self._ffmpeg_proc:
            self._ffmpeg_proc.terminate()
        print("[TTSOnline] Stop requested.")