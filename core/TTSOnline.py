import asyncio
import threading
import edge_tts
import time
import logging

from core.logging.session_logger import SessionLogger
from core.TTSBase import TTSBase

base_logger = logging.getLogger(__name__)
logger = SessionLogger(base_logger)


class TTSOnline(TTSBase):
    def __init__(self, player):
        super().__init__()

        self.player = player

        self._current_task = None
        self._lock = threading.Lock()

        self._loop = None
        self._worker_thread = threading.Thread(
            target=self._run_worker,
            daemon=True
        )
        self._worker_thread.start()

        logger.info("TTSOnline engine initialized (Edge-TTS ready).")
        logger.debug("Worker thread started: %s", self._worker_thread.name)

    # -----------------------------
    # Async loop
    # -----------------------------
    def _run_worker(self):
        logger.debug("Async event loop starting")

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        logger.debug("Async event loop running")
        self._loop.run_forever()

    # -----------------------------
    # Public API
    # -----------------------------
    def speak(self, text: str, voice_id: str):
        if not text:
            logger.debug("Empty text ignored in speak()")
            return

        if not voice_id:
            logger.error("Speak request rejected: missing voice_id")
            return

        with self._lock:
            sid = self.player.stop()

            # 🔥 bind session globally
            logger.set_sid(sid)

            logger.info("Speaking started (voice=%s)", voice_id)
            logger.debug("Text length: %d characters", len(text))

            # cancel previous task
            if self._current_task and not self._current_task.done():
                logger.debug("Cancelling previous TTS task")

                self._loop.call_soon_threadsafe(
                    lambda: self._current_task.cancel()
                )

            if self._loop and self._loop.is_running():
                logger.debug("Scheduling async Edge-TTS task")

                coro = self._async_speak(text, voice_id, sid)

                self._current_task = asyncio.run_coroutine_threadsafe(
                    coro,
                    self._loop
                )

            else:
                logger.error("Async loop not running — cannot speak")

    # -----------------------------
    # Core streaming
    # -----------------------------
    async def _async_speak(self, text: str, voice_id: str, session_id: int):
        start_time = time.perf_counter()

        # ensure session is bound inside async thread too
        logger.set_sid(session_id)

        logger.info("Generating speech audio...")

        try:
            communicate = edge_tts.Communicate(text, voice=voice_id)

            async def byte_generator():
                first_chunk = True
                chunk_count = 0

                logger.debug("Connecting to Edge-TTS stream")

                async for chunk in communicate.stream():

                    if session_id != self.player._current_session:
                        logger.info("Speech interrupted (new request received)")
                        return

                    if chunk["type"] == "audio":

                        chunk_count += 1

                        if first_chunk:
                            latency = (time.perf_counter() - start_time) * 1000

                            logger.info(
                                "Audio streaming started (latency=%.0fms)",
                                latency
                            )

                            first_chunk = False

                        if chunk_count % 25 == 0:
                            logger.debug("Streaming audio chunks: %d", chunk_count)

                        yield chunk["data"]

                logger.debug(
                    "Edge-TTS stream completed (%d chunks)",
                    chunk_count
                )

            await self.player.play_stream(
                byte_generator(),
                session_id=session_id,
                samplerate=24000
            )

            logger.info("Speech playback completed")

        except asyncio.CancelledError:
            logger.info("Speech cancelled")

        except Exception:
            logger.exception("TTSOnline error during synthesis")

        finally:
            # 🔥 critical cleanup
            logger.clear_sid()

    # -----------------------------
    # Control
    # -----------------------------
    def stop(self):
        with self._lock:
            logger.info("Stopping TTSOnline playback")

            if self._current_task and not self._current_task.done():
                logger.debug("Cancelling active async task")
                self._loop.call_soon_threadsafe(
                    lambda: self._current_task.cancel()
                )

            self.player.stop()

            logger.clear_sid()

    def set_volume(self, volume: float):
        logger.info("Volume changed: %.2f", volume)
        self.player.set_volume(volume)