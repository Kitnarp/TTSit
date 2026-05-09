# core/logging/session_logger.py

import logging

class SessionLogger(logging.LoggerAdapter):
    def __init__(self, logger, session_id="BOOT"):
        super().__init__(logger, {})
        self.session_id = session_id

    def process(self, msg, kwargs):
        sid = self.session_id or "BOOT"
        return f"[{sid}] {msg}", kwargs

    def set_sid(self, session_id):
        self.session_id = session_id

    def clear_sid(self):
        self.session_id = "BOOT"