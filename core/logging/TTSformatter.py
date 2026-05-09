import logging

class TTSFormatter(logging.Formatter):

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[41m",  # red background
    }

    RESET = "\033[0m"

    LEVEL_WIDTH = 5  # INFO , DEBUG, WARN , ERROR, CRIT

    def format(self, record):
        level = record.levelname

        color = self.COLORS.get(level, "")

        # -----------------------------
        # padded + colored copy
        # -----------------------------
        padded_level = f"{level:<{self.LEVEL_WIDTH}}"

        colored_level = f"{color}{padded_level}{self.RESET}"

        # IMPORTANT: do NOT overwrite record.levelname
        record.levelname_colored = colored_level

        return super().format(record)