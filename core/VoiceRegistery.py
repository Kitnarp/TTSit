import json
import logging
import os
from typing import Dict, Any, Optional

from core.logging.session_logger import SessionLogger

base_logger = logging.getLogger(__name__)
logger = SessionLogger(base_logger)

class VoiceRegistry:
    """Central registry for all TTS voices."""

    def __init__(self, config_path: str = "core/voices.json"):
        self.config_path = os.path.abspath(config_path)
        self._voices: Dict[str, Dict[str, Any]] = {}
        self._offline_defaults: Dict[str, int] = {}

        logger.info("VoiceRegistry initializing")
        logger.debug("Resolved config path: %s", self.config_path)
        self._load()

    def _load(self):
        logger.debug("VoiceRegistry loading started")

        if not os.path.exists(self.config_path):
            logger.critical("Voice config file not found | path: %s", self.config_path)
            self._voices, self._offline_defaults = {}, {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.debug("Voice JSON parsed successfully")

            if not isinstance(data, dict):
                logger.critical("Invalid voices.json root type | expected: dict, received: %s", type(data).__name__)
                self._voices, self._offline_defaults = {}, {}
                return

            self._voices = data.get("voices", {})
            self._offline_defaults = data.get("offline_defaults", {})

            self._export_keys()

            logger.info("VoiceRegistry loaded | voices=%d offline_defaults=%d", len(self._voices), len(self._offline_defaults))
            logger.debug("Voice keys: %s", list(self._voices.keys()))
            logger.debug("Offline defaults: %s", self._offline_defaults)

            if not self._voices: logger.warning("VoiceRegistry loaded with 0 voices")
            if not self._offline_defaults: logger.warning("No offline default voices configured")

        except json.JSONDecodeError as e:
            logger.critical("Invalid voices.json | line=%d col=%d reason: %s", e.lineno, e.colno, e.msg)
            self._voices, self._offline_defaults = {}, {}
        except Exception:
            logger.exception("Unexpected VoiceRegistry load failure")
            self._voices, self._offline_defaults = {}, {}

    def _export_keys(self):
        """Writes current voice keys to a shared text file safely."""
        target_path = "active_voices.txt"
        temp_path = target_path + ".tmp"

        try:
            # 1. Get the keys and join with newlines
            keys_str = "\n".join(self._voices.keys())
            
            # 2. Write to a temporary file first
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(keys_str)
                
            # 3. Atomically rename/replace the file
            # This ensures AHK/C++ never sees a 'partial' file
            os.replace(temp_path, target_path)
            logger.debug("Exported %d keys to %s", len(self._voices), target_path)
            
        except Exception as e:
            logger.error("Failed to export voice keys: %s", e)


    def reload(self):
        logger.info("Reloading VoiceRegistry")
        self._load()

    def get(self, voice_key: str) -> Optional[Dict[str, Any]]:
        voice = self._voices.get(voice_key)
        if voice is None: logger.debug("Voice key lookup failed | key=%s", voice_key)
        return voice

    def resolve(self, voice_key: str, engine: str = "online") -> Optional[str]:
        logger.debug("Voice resolve requested | key=%s engine=%s", voice_key, engine)
        voice = self.get(voice_key)

        if not voice:
            logger.warning("Voice resolution failed | missing key=%s", voice_key)
            return None

        if engine == "online":
            resolved = voice.get("online")
            if resolved:
                logger.debug("Online voice resolved | key=%s voice_id=%s", voice_key, resolved)
                voicetype = voice.get("display")
                if voicetype: logger.info(f"Voice: {voicetype}.")
                return resolved
            logger.warning("Online voice mapping missing | voice_key=%s", voice_key)
            return None

        if engine == "offline":
            gender = voice.get("gender", "female")
            resolved = self._offline_defaults.get(gender)
            if resolved:
                logger.debug("Offline fallback resolved | key=%s gender=%s voice_id=%s", voice_key, gender, resolved)
                return resolved
            logger.warning("Offline fallback missing | gender=%s", gender)
            return None

        logger.error("Unknown engine requested | engine: %s", engine)
        return None

    def list_keys(self):
        return list(self._voices.keys())

    def list_pretty(self):
        return {k: v.get("display", k) for k, v in self._voices.items()}

    def list_full(self):
        return self._voices

    def search(self, query: str):
        query = query.lower()
        results = {k: v for k, v in self._voices.items() if query in k.lower() or query in v.get("display", "").lower()}
        logger.debug("Voice search completed | query=%s results=%d", query, len(results))
        return results

    def safe_resolve(self, voice_key: str, engine: str = "online", fallback: str = None) -> Optional[str]:
        logger.debug("Safe resolve started | key=%s engine=%s fallback=%s", voice_key, engine, fallback)
        resolved = self.resolve(voice_key, engine)

        if resolved:
            return resolved

        if fallback and fallback in self._voices:
            logger.warning("Explicit fallback triggered | fallback_key=%s", fallback)
            return self.resolve(fallback, engine)

        return None
