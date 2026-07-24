import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler

import config

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-14s | %(message)s"
_configured = False

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9\-_]{12,}"),
    re.compile(r"sk-ant-[A-Za-z0-9\-_]{12,}"),
    re.compile(r"\b[A-Za-z0-9]{20,}\.[A-Za-z0-9\-_]{20,}\b"),  # ollama key shape
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-_.]{12,}"),
    re.compile(r"(?i)(api[_-]?key\S{0,3}\s*[:=]\s*)\S{8,}"),
]


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        red = msg
        for pat in _SECRET_PATTERNS:
            red = pat.sub(lambda m: (m.group(1) if m.groups() else "") + "[REDACTED]", red)
        if red != msg:
            record.msg = red
            record.args = ()
        return True


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    root = logging.getLogger("knoc8")
    root.setLevel(logging.DEBUG)
    redactor = _RedactFilter()

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_FORMAT, datefmt="%H:%M:%S"))
    console.addFilter(redactor)
    root.addHandler(console)

    logfile = config.LOGS_DIR / f"knoc8_{datetime.now():%Y-%m-%d}.log"
    file_handler = RotatingFileHandler(
        logfile, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    file_handler.addFilter(redactor)
    root.addHandler(file_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"knoc8.{name}")
