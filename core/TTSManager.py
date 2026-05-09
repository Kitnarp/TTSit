import logging
from core.logging.session_logger import SessionLogger
from core.TTSFactory import TTSFactory
from core.VoiceRegistery import VoiceRegistry


base_logger = logging.getLogger(__name__)
logger = SessionLogger(base_logger)


def _preview(text: str, limit: int = 120) -> str:
    """
    Clean single-line preview for logs.
    """
    # cleaned = text 
    # normalize whitespace/newlines FIRST
    cleaned = " ".join(text.split())
    

    # truncate safely
    if len(cleaned) > limit:
        return cleaned[:limit] + "..."

    return cleaned


def _format_tts_block(text: str) -> str:
    preview = _preview(text)

    return (
        "text:\n"
        f"    {preview}"
    )


class TTSManager:
    def __init__(self):
        self.voice_registry = VoiceRegistry()

        self.defaults = {
            "engine": "online",
            "voice": "female_en",
            "volume": 0.8,
            "device": None
        }

        logger.info("TTSManager ready.")
        logger.debug("Defaults initialized: %s", self.defaults)

    # -----------------------------
    # Speak pipeline
    # -----------------------------
    def speak(self, text: str, **kwargs):
        if not text:
            logger.debug("Empty speak request ignored.")
            return

        ctx = {**self.defaults, **kwargs}

        # INFO: high-level trace of request
        logger.info(
            "Speak request | engine=%s voice=%s volume=%.2f \n" +  _format_tts_block(text),
            ctx["engine"],
            ctx["voice"],
            ctx["volume"],
        )

        logger.debug("Merged context: %s", ctx)

        try:
            audio = TTSFactory.get_audio_manager()

            # -----------------------------
            # Audio configuration
            # -----------------------------
            volume = ctx.get("volume", 0.8)
            audio.set_volume(volume)
            logger.debug("Audio volume set to %.2f", volume)

            if ctx.get("device") is not None:
                logger.debug("Audio device override: %s", ctx["device"])
                audio.set_device(ctx["device"])

            # -----------------------------
            # Engine selection
            # -----------------------------
            engine = TTSFactory.get_engine(ctx["engine"])
            logger.debug("Engine selected: %s", ctx["engine"])

            # -----------------------------
            # Voice resolution
            # -----------------------------
            voice_key = ctx.get("voice")
            logger.debug(
                "Resolving voice | key=%s engine=%s",
                voice_key,
                ctx["engine"]
            )

            voice_id = self.voice_registry.resolve(
                voice_key,
                engine=ctx["engine"]
            )

            if voice_id:
                logger.debug(
                    "Voice resolved | key=%s -> id=%s",
                    voice_key,
                    voice_id
                )
            else:
                logger.warning(
                    "Primary voice resolution failed | key=%s",
                    voice_key
                )

                voice_id = self.voice_registry.safe_resolve(
                    voice_key,
                    engine=ctx["engine"]
                )

                logger.info(
                    "Fallback voice selected | voice_id=%s",
                    voice_id
                )

            if not voice_id:
                logger.error(
                    "Voice resolution failed completely. Aborting speak."
                )
                return

            # -----------------------------
            # Execute speech
            # -----------------------------
            logger.info(
                "Speech execution started | engine=%s voice_id=%s",
                ctx["engine"],
                voice_id
            )

            engine.speak(text, voice_id=voice_id)

        except Exception:
            logger.exception(
                "Speak pipeline failed | text='%s...'",
                text[:30]
            )

    # -----------------------------
    # Volume control
    # -----------------------------
    def set_volume(self, volume: float):
        try:
            logger.debug("Volume change requested | value=%.2f", volume)

            audio = TTSFactory.get_audio_manager()
            audio.set_volume(volume)

        except Exception:
            logger.exception("Failed to update volume")

    # -----------------------------
    # Stop control
    # -----------------------------
    def stop(self):
        try:
            logger.info("Global stop triggered")

            TTSFactory.get_audio_manager().stop()

            logger.debug("AudioManager stop executed")

        except Exception:
            logger.exception("Global stop failed")

    # -----------------------------
    # Voice UI helpers
    # -----------------------------
    def list_voices(self):
        logger.debug("Voice list requested")
        return self.voice_registry.list_pretty()

    def search_voices(self, query: str):
        logger.debug("Voice search | query=%s", query)
        return self.voice_registry.search(query)

    def reload_voices(self):
        logger.info("Reloading voice registry")
        self.voice_registry.reload()
