import subprocess
import sounddevice as sd
import numpy as np
import asyncio
import threading
import queue
import logging
import time

# TODO: PERFORMANCE - Replace subprocess.Popen with PyAV (C-bindings).
#       Removes the overhead of spawning/killing external .exe processes.
# TODO: AUDIO QUALITY - Implement a Volume Cross-Fader in _callback.
#       Instead of self.volume = new_vol, use a target_volume and 
#       incrementally approach it to prevent digital 'clicks' on stop/start.


logger = logging.getLogger(__name__)


class AudioManager:
    def __init__(self, device=None):
        self.device_id = device
        self.volume = 1.0
        self._audio_queue = queue.Queue(maxsize=1000)
        self.process = None
        self._stream = None
        self._lock = threading.RLock()
        self._current_session = 0
        logger.debug("AudioManager (Non-Blocking Pipe) initialized.")

    def set_volume(self, volume: float):
        with self._lock:
            self.volume = max(0.0, min(1.0, volume))

    def stop(self):
        """Atomic session increment. Returns the NEW ID."""
        with self._lock:
            self._current_session += 1
            sid = self._current_session
            self._cleanup_resources()
            logger.debug("[%d] Stop called. Resetting hardware.", sid)
            return sid

    def _terminate_process(self):
        """
        CRITICAL FIX: Kill process BEFORE closing pipes.
        Closing a full pipe blocks the thread. Killing the process breaks the pipe instantly.
        """
        proc = self.process
        if proc:
            self.process = None # Detach immediately so other threads stop using it
            try:
                proc.kill() # SIGKILL (Aggressive instant death)
                # No .wait(), let the OS reap it
            except Exception as e:
                logger.debug("Process kill error: %s", e)
            
            # Now it is safe to close pipes because the consumer is dead
            try:
                if proc.stdin: proc.stdin.close()
            except: pass
            try:
                if proc.stdout: proc.stdout.close()
            except: pass

    def _cleanup_resources(self):
        """Release all resources safely."""
        self._terminate_process()
        
        if self._stream:
            try:
                self._stream.abort() # Instant silence
                self._stream.close()
            except: pass
            self._stream = None

        # Flush queue without recreating it
        while not self._audio_queue.empty():
            try: self._audio_queue.get_nowait()
            except queue.Empty: break

    def _callback(self, outdata, frames, time, status):
        try:
            data = self._audio_queue.get_nowait()
            outdata[:] = data.astype(np.float32).reshape(-1, 1) * (self.volume / 32768.0)
        except (queue.Empty, ValueError):
            outdata.fill(0)

    def _start_playback_engine(self, samplerate):
        with self._lock:
            if not self._stream:
                self._stream = sd.OutputStream(
                    samplerate=samplerate, channels=1, dtype='float32', 
                    callback=self._callback, blocksize=1024, device=self.device_id
                )
                self._stream.start()

    def play_numpy(self, data, samplerate, session_id):
        with self._lock:
            if session_id != self._current_session: return
            self._cleanup_resources()
            if data.dtype != np.int16:
                data = (data * 32767).astype(np.int16)
            self._start_playback_engine(samplerate)

        def _feeder():
            block_size = 1024
            for i in range(0, len(data), block_size):
                if session_id != self._current_session: return
                chunk = data[i:i+block_size]
                if len(chunk) < block_size:
                    chunk = np.pad(chunk, (0, block_size - len(chunk)))
                self._audio_queue.put(chunk)
            self._block_until_done(session_id)
        threading.Thread(target=_feeder, daemon=True).start()

    async def play_stream(self, async_gen, session_id, samplerate=24000):
        with self._lock:
            if session_id != self._current_session: return
            self._cleanup_resources()
            
            self.process = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", 
                "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(samplerate), "pipe:1"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                bufsize=2 * 10**6 
            )
            self._start_playback_engine(samplerate)

        # Decoder Thread
        def _decoder():
            proc = self.process 
            while session_id == self._current_session and proc and proc.poll() is None:
                try:
                    raw = proc.stdout.read(2048)
                    if not raw: break
                    self._audio_queue.put(np.frombuffer(raw, dtype=np.int16))
                except: break
        threading.Thread(target=_decoder, daemon=True).start()

        # Feeder Thread
        write_queue = queue.Queue(maxsize=500)
        def _feeder():
            proc = self.process
            while session_id == self._current_session and proc:
                try:
                    chunk = write_queue.get(timeout=1.0)
                    try:
                        proc.stdin.write(chunk)
                        proc.stdin.flush()
                    except: break
                except queue.Empty: continue
                except: break
        threading.Thread(target=_feeder, daemon=True).start()

        try:
            async for chunk in async_gen:
                if session_id != self._current_session: return
                while True:
                    try:
                        write_queue.put_nowait(chunk)
                        break
                    except queue.Full:
                        if session_id != self._current_session: return
                        await asyncio.sleep(0.02)
        finally:
            # CRITICAL FIX:
            # 1. Wait for the playback queue to drain naturally.
            if session_id == self._current_session:
                await self._async_block_until_done(session_id)
            
            # 2. Only clean up the FFmpeg process (stdin/stdout/popen).
            # DO NOT call self.stop(), which increments the session ID and kills audio.
            with self._lock:
                if session_id == self._current_session:
                    self._terminate_process()
            # We leave self._stream active. It will just output silence when queue is empty.

    async def _async_block_until_done(self, sid):
        # Wait until the queue is fully empty.
        # Increase timeout or logic here if needed, but 
        # essentially we just wait for the consumer to finish.
        while not self._audio_queue.empty() and sid == self._current_session:
            await asyncio.sleep(0.1)

    def _block_until_done(self, sid):
        timeout = 0
        while not self._audio_queue.empty() and sid == self._current_session and timeout < 20:
            time.sleep(0.1)
            timeout += 1
        with self._lock:
            if sid == self._current_session: self._cleanup_resources()
