import subprocess
import sounddevice as sd
import numpy as np
import asyncio
import threading
import queue
import logging
import time

from core.logging.session_logger import SessionLogger

logger = SessionLogger(logging.getLogger(__name__))


class AudioManager:
    def __init__(self, device=None):
        self.device_id = device
        self.volume = 1.0
        self._audio_queue = queue.Queue(maxsize=1000)
        self.process = None
        self._stream = None
        self._lock = threading.RLock()
        self._current_session = 0

        logger.info("AudioManager initialized")
        logger.debug("device=%s volume=%.2f", self.device_id, self.volume)

    # -----------------------------
    # Session control
    # -----------------------------
    def set_volume(self, volume: float):
        with self._lock:
            self.volume = max(0.0, min(1.0, volume))
            logger.info("Volume updated -> %.2f", self.volume)

    def stop(self):
        with self._lock:
            self._current_session += 1
            sid = self._current_session

            logger.set_sid(sid)
            logger.info("Session stopped (audio reset)")

            self._cleanup_resources()

            logger.debug("Audio resources cleared")
            return sid
        
    def set_device(self, device_id):
        """Updates the output device and resets resources to apply changes."""
        with self._lock:
            old_device = self.device_id
            self.device_id = device_id
            self._cleanup_resources()
            logger.info(f"Device changed | old={old_device} -> new={self.device_id} | resources=reset")

    # -----------------------------
    # Internal cleanup
    # -----------------------------
    def _terminate_process(self):
        proc = self.process
        if not proc:
            return

        self.process = None

        logger.debug("Terminating FFmpeg process")

        try:
            proc.kill()
        except Exception as e:
            logger.debug("Process kill error: %s", e)

        try:
            if proc.stdin:
                proc.stdin.close()
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass

    def _cleanup_resources(self):
        self._terminate_process()

        if self._stream:
            try:
                self._stream.abort()
                self._stream.close()
            except Exception:
                logger.debug("Stream cleanup failed")
            self._stream = None

        drained = 0
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
                drained += 1
            except queue.Empty:
                break

        logger.debug("Audio queue flushed (%d items)", drained)

    # -----------------------------
    # Playback core
    # -----------------------------
    def _callback(self, outdata, frames, time, status):
        try:
            data = self._audio_queue.get_nowait()
            outdata[:] = data.astype(np.float32).reshape(-1, 1) * (self.volume / 32768.0)
        except (queue.Empty, ValueError):
            outdata.fill(0)

    def _start_playback_engine(self, samplerate):
        with self._lock:
            if self._stream:
                return

            logger.debug("Starting playback engine | sr=%d", samplerate)

            self._stream = sd.OutputStream(
                samplerate=samplerate,
                channels=1,
                dtype="float32",
                callback=self._callback,
                blocksize=1024,
                device=self.device_id
            )
            self._stream.start()

    # -----------------------------
    # Offline playback
    # -----------------------------
    def play_numpy(self, data, samplerate, session_id):
        with self._lock:
            if session_id != self._current_session:
                logger.debug("Rejected stale numpy playback")
                return

            logger.set_sid(session_id)
            logger.info("Playing offline started...")

            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break

            if data.dtype != np.int16:
                data = (data * 32767).astype(np.int16)

            self._start_playback_engine(samplerate)

        def _feeder():
            block_size = 1024
            chunks = 0

            try:
                for i in range(0, len(data), block_size):

                    if session_id != self._current_session:
                        logger.debug("Offline playback interrupted")
                        return

                    chunk = data[i:i + block_size]

                    if len(chunk) < block_size:
                        chunk = np.pad(chunk, (0, block_size - len(chunk)))

                    self._audio_queue.put(chunk)
                    chunks += 1

                logger.debug("Offline chunks queued: %d", chunks)
                self._block_until_done(session_id)

                logger.info("Offline playback completed")

            except Exception:
                logger.exception("Offline feeder error")

        threading.Thread(target=_feeder, daemon=True).start()

    # -----------------------------
    # Streaming playback
    # -----------------------------
    async def play_stream(self, async_gen, session_id, samplerate=24000):
        with self._lock:
            if session_id != self._current_session:
                return

            logger.set_sid(session_id)
            logger.info("Starting stream playback")

            self._cleanup_resources()

            self.process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error",
                    "-i", "pipe:0",
                    "-f", "s16le",
                    "-acodec", "pcm_s16le",
                    "-ac", "1",
                    "-ar", str(samplerate),
                    "pipe:1"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=2 * 10**6
            )

            self._start_playback_engine(samplerate)

        def _decoder():
            proc = self.process
            chunks = 0

            while session_id == self._current_session and proc and proc.poll() is None:
                try:
                    raw = proc.stdout.read(2048)
                    if not raw:
                        break

                    self._audio_queue.put(np.frombuffer(raw, dtype=np.int16))
                    chunks += 1

                except Exception:
                    break

            logger.debug("Decoder finished | chunks=%d", chunks)

        threading.Thread(target=_decoder, daemon=True).start()

        write_queue = queue.Queue(maxsize=500)

        def _feeder():
            proc = self.process

            while session_id == self._current_session and proc:
                try:
                    chunk = write_queue.get(timeout=1.0)
                    proc.stdin.write(chunk)
                    proc.stdin.flush()

                except queue.Empty:
                    continue
                except Exception:
                    break

        threading.Thread(target=_feeder, daemon=True).start()

        try:
            async for chunk in async_gen:
                if session_id != self._current_session:
                    return

                while True:
                    try:
                        write_queue.put_nowait(chunk)
                        break
                    except queue.Full:
                        await asyncio.sleep(0.02)

        finally:
            if session_id == self._current_session:
                await self._async_block_until_done(session_id)

            with self._lock:
                if session_id == self._current_session:
                    self._terminate_process()

            logger.info("Stream playback finished")

    # -----------------------------
    # Helpers
    # -----------------------------
    def _block_until_done(self, sid):
        while not self._audio_queue.empty() and sid == self._current_session:
            time.sleep(0.05)

        time.sleep(0.35)

    async def _async_block_until_done(self, sid):
        while not self._audio_queue.empty() and sid == self._current_session:
            await asyncio.sleep(0.1)