import os
import pyttsx3
import threading
import tempfile
import soundfile as sf
import queue
import logging

from core.logging.session_logger import SessionLogger
from core.TTSBase import TTSBase

base_logger = logging.getLogger(__name__)
logger = SessionLogger(base_logger)


class TTSOffline(TTSBase):
    """
    Offline TTS engine (pyttsx3-based)
    Session-aware via SessionLogger context binding
    """

    def __init__(self, player, default_voice_id=None):
        super().__init__()

        self.player = player
        self.default_voice_id = default_voice_id

        self._request_queue = queue.Queue()

        self._worker_thread = threading.Thread(
            target=self._offline_worker,
            daemon=True
        )
        self._worker_thread.start()

        logger.info("Offline TTS engine ready.")
        logger.debug(
            "Engine initialized | default_voice=%s | thread=%s",
            self.default_voice_id,
            self._worker_thread.name
        )

    # -----------------------------
    # Worker loop
    # -----------------------------
    def _offline_worker(self):
        logger.debug("Offline worker loop started.")

        while True:
            text, voice_id, sid = self._request_queue.get()

            # Bind session to logging context
            logger.set_sid(session_id=sid)

            logger.debug(
                "Job received | text_len=%d | voice_id=%s | active_session=%s",
                len(text) if text else 0,
                voice_id,
                self.player._current_session
            )

            # session guard
            if sid != self.player._current_session:
                logger.debug("Stale job discarded (session mismatch)")
                self._request_queue.task_done()
                continue

            temp_path = None

            try:
                logger.info("Generating offline speech...")

                engine = pyttsx3.init()
                engine.setProperty("rate", 170)
                engine_voices = engine.getProperty("voices")

                if voice_id:
                    logger.debug("Applying voice_id=%s", voice_id)
                    engine.setProperty("voice", engine_voices[voice_id-1].id)
                else:
                    logger.debug("Using system default voice")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    temp_path = tmp.name

                logger.debug("Writing temp audio file")

                engine.save_to_file(text, temp_path)
                engine.runAndWait()
                engine.stop()
                del engine

                logger.debug("Synthesis completed")

                # session validation before playback
                if sid != self.player._current_session:
                    logger.info("Discarding audio (new session started)")

                elif not os.path.exists(temp_path):
                    logger.error("Temp audio file missing: %s", temp_path)

                else:
                    logger.info("Playing offline speech...")

                    data, samplerate = sf.read(temp_path, dtype="int16")

                    logger.debug(
                        "Audio loaded | sr=%d | frames=%d",
                        samplerate,
                        len(data)
                    )

                    self.player.play_numpy(data, samplerate, sid)

            except Exception:
                logger.exception("Offline TTS failed")

            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        logger.debug("Temp file cleaned")
                    except Exception:
                        logger.warning("Failed to delete temp file")

                self._request_queue.task_done()

                # IMPORTANT: clear session context after job
                logger.clear_sid()

    # -----------------------------
    # Public API
    # -----------------------------
    def speak(self, text: str, voice_id: str = None):
        if not text:
            logger.debug("Empty speak request ignored")
            return

        sid = self.player.stop()

        # bind session globally for entire pipeline
        logger.set_sid(session_id=sid)

        final_voice = voice_id or self.default_voice_id

        logger.info("Offline speak request queued")
        logger.debug(
            "Request params | voice=%s | text_len=%d",
            final_voice,
            len(text)
        )

        self._request_queue.put((text, final_voice, sid))

    def stop(self):
        logger.info("Offline engine stop requested")
        self.player.stop()

    def set_volume(self, volume):
        logger.debug("Volume update: %.2f", volume)
        self.player.set_volume(volume)