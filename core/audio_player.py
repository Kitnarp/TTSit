# Core/audio_player.py

import asyncio
import subprocess
import sounddevice as sd
import numpy as np
import threading

class AudioPlayer:
    def __init__(self, device=None, samplerate=24000, channels=1):
        self.device = device
        self.samplerate = samplerate
        self.channels = channels
        self.process = None
        self._consumer_thread = None
        self._stop_requested = False
        self._stream = None

    def stop(self):
        self._stop_requested = True
        print("[AudioPlayer] Stop requested.")

        # Kill ffmpeg immediately
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()

        # Stop audio stream
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass

    async def play_stream(self, input_bytes_async_gen):
        self._stop_requested = False

        self.process = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0",
             "-f", "s16le", "-acodec", "pcm_s16le",
             "-ac", str(self.channels), "-ar", str(self.samplerate),
             "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=4096,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        self._stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype='int16',
            device=self.device
        )
        self._stream.start()

        def _consumer(stdout, stream):
            while not self._stop_requested:
                pcm = stdout.read(4096)
                if not pcm:
                    break
                data = np.frombuffer(pcm, dtype=np.int16)
                if len(data) > 0:
                    stream.write(data)
            print("[AudioPlayer] Consumer finished")

        self._consumer_thread = threading.Thread(
            target=_consumer,
            args=(self.process.stdout, self._stream),
            daemon=True
        )
        self._consumer_thread.start()

        async for chunk in input_bytes_async_gen:
            if self._stop_requested:
                break
            self.process.stdin.write(chunk)
            await asyncio.sleep(0)

        # Cleanup if not already stopped
        if not self._stop_requested:
            self.process.stdin.close()
            self.process.wait()
            self._consumer_thread.join()
            self._stream.stop()
            self._stream.close()

        print("[AudioPlayer] Playback finished")