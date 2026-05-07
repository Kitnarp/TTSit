import subprocess
import sounddevice as sd
import numpy as np
import asyncio
import threading
import queue

class AudioManager:
    def __init__(self, device=None):
        self.device_id = device
        self.volume = 1.0
        self._audio_queue = queue.Queue(maxsize=100)
        self._stop_event = threading.Event()
        self.process = None
        self._stream = None

    def set_device(self, device_id):
        self.stop()
        self.device_id = device_id
        print(f"[AudioManager] Device changed to: {device_id}")

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))

    def stop(self):
        """Immediately stops FFmpeg and the audio stream."""
        self._stop_event.set()
        
        # Kill FFmpeg process
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=0.5)
            except:
                if self.process: self.process.kill()
        
        # Close sounddevice stream
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except:
                pass

        # Clear the queue
        with self._audio_queue.mutex:
            self._audio_queue.queue.clear()
            
        self._stop_event.clear()

    def _callback(self, outdata, frames, time, status):
        """Standard callback feeding from the FFmpeg-filled queue."""
        try:
            # Get 16-bit PCM data from queue
            data = self._audio_queue.get_nowait()
            
            # Convert to float32 and apply volume
            # We divide by 32768 to normalize int16 to -1.0 to 1.0
            float_data = data.astype(np.float32) / 32768.0
            outdata[:] = float_data.reshape(-1, 1) * self.volume
            
        except (queue.Empty, ValueError):
            outdata.fill(0)

    def play_numpy(self, data, samplerate):
        """Plays full numpy arrays (pyttsx3) using the same callback pipeline."""
        self.stop()
        
        block_size = 1024
        # Ensure data is int16 for the queue consistency
        if data.dtype != np.int16:
            data = (data * 32767).astype(np.int16)

        self._stream = sd.OutputStream(
            samplerate=samplerate, device=self.device_id,
            channels=1, dtype='float32', callback=self._callback, blocksize=block_size
        )
        self._stream.start()

        for i in range(0, len(data), block_size):
            if self._stop_event.is_set(): break
            chunk = data[i:i+block_size]
            if len(chunk) < block_size:
                chunk = np.pad(chunk, (0, block_size - len(chunk)))
            self._audio_queue.put(chunk)

    async def play_stream(self, async_gen, samplerate=24000):
        """Streaming playback using FFmpeg as the decoder."""
        self.stop()
        block_size = 1024

        # 1. Start FFmpeg to decode incoming MP3 bytes to raw s16le PCM
        self.process = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
             "-ac", "1", "-ar", str(samplerate), "pipe:1"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=4096, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

        # 2. Start the sounddevice stream
        self._stream = sd.OutputStream(
            samplerate=samplerate, channels=1, dtype='float32', 
            callback=self._callback, blocksize=block_size, device=self.device_id
        )
        self._stream.start()

        # 3. Background thread to read FFmpeg's stdout and fill our queue
        def _ffmpeg_consumer():
            chunk_bytes = block_size * 2  # 1024 samples * 2 bytes (int16)
            while not self._stop_event.is_set():
                raw_pcm = self.process.stdout.read(chunk_bytes)
                if not raw_pcm: break
                
                # Convert raw bytes to int16 numpy array
                data = np.frombuffer(raw_pcm, dtype=np.int16)
                if len(data) > 0:
                    self._audio_queue.put(data)

        threading.Thread(target=_ffmpeg_consumer, daemon=True).start()

        # 4. Feed the async generator (Edge-TTS) into FFmpeg's stdin
        try:
            async for chunk in async_gen:
                if self._stop_event.is_set(): break
                try:
                    self.process.stdin.write(chunk)
                    self.process.stdin.flush()
                except (IOError, BrokenPipeError):
                    break
                await asyncio.sleep(0)
        finally:
            if self.process and self.process.stdin:
                self.process.stdin.close()

        # 5. Wait for the queue to finish playing
        while not self._audio_queue.empty() and not self._stop_event.is_set():
            await asyncio.sleep(0.1)
            
        self.stop()
