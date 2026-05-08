import logging.config
import os

def setup_logging(default_level=logging.INFO):
    if not os.path.exists("logs"):
        os.makedirs("logs")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "minimal": {
                # Format: 20:30:15 [INFO] TTS.Manager: Message
                # %(name)-12s pads the name to 12 chars to keep messages aligned
                "format": "%(asctime)s [%(levelname)s] %(name)-20s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "minimal",
                "level": "DEBUG",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/tts_service.log",
                "formatter": "minimal",
                "maxBytes": 5242880,
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "": { 
                "handlers": ["console", "file"],
                "level": default_level,
                },

            "core": { # This targets everything in 'core' folder
                "level": "DEBUG",
                "propagate": True,
                },
            "TTS": { # This targets 'TTS.Server' logger
                "level": "DEBUG",
                "propagate": True,
                },
            "uvicorn": {"propagate": True},
            # Optional: Quiet down noisy third-party libraries
            "uvicorn.access": {"level": "WARNING"},
        },
    }
    logging.config.dictConfig(config)
