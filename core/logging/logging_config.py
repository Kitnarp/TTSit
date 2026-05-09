import logging
import logging.config
from core.logging.TTSformatter import TTSFormatter
import os


def setup_logging(default_level=logging.INFO):
    os.makedirs("logs", exist_ok=True)

    config = {
        "version": 1,

        # IMPORTANT:
        # keeps uvicorn, comtypes, etc under control
        "disable_existing_loggers": False,

        # -----------------------------
        # FORMATTERS
        # -----------------------------
        "formatters": {

            # clean human-readable format
            "console": {
                "format": "%(asctime)s [%(levelname)s] %(name)-20s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "color_console": {
                "()": TTSFormatter,
                "format": "%(asctime)s [%(levelname_colored)s] %(name)-20s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
            # file logging stays simple (no colors)
            "file": {
                "format": "%(asctime)s [%(levelname)s] %(name)-20s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },

        # -----------------------------
        # HANDLERS
        # -----------------------------
        "handlers": {

            # console output (DEV DEBUG focus)
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "color_console",
                "level": "INFO",
            },

            # persistent logs
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/tts_service.log",
                "formatter": "file",
                "maxBytes": 5_242_880,
                "backupCount": 5,
                "encoding": "utf-8",
                "level": "DEBUG",
            },
        },

        # -----------------------------
        # LOGGERS
        # -----------------------------
        "loggers": {

            # ROOT LOGGER (everything goes through here)
            "": {
                "handlers": ["console", "file"],
                "level": default_level,
            },

            # -------------------------
            # CORE SYSTEM (your code)
            # -------------------------
            "core": {
                "level": "DEBUG",
                "propagate": True,
            },

            "TTS": {
                "level": "DEBUG",
                "propagate": True,
            },

            # -------------------------
            # NOISY LIBRARIES FILTERED
            # -------------------------

            # Windows COM TTS backend spam suppression
            "comtypes": {
                "level": "ERROR",
                "propagate": False,
            },

            "comtypes.client._code_cache": {
                "level": "ERROR",
                "propagate": False,
            },

            # Edge / uvicorn noise control
            "uvicorn": {
                "level": "WARNING",
                "propagate": False,
            },

            "uvicorn.access": {
                "level": "WARNING",
                "propagate": False,
            },

            # asyncio noise reduction (optional but helpful)
            "asyncio": {
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)