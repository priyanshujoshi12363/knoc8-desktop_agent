import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import config

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-14s | %(message)s"
_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    root = logging.getLogger("knoc8")
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_FORMAT, datefmt="%H:%M:%S"))
    root.addHandler(console)

    logfile = config.LOGS_DIR / f"knoc8_{datetime.now():%Y-%m-%d}.log"
    file_handler = RotatingFileHandler(
        logfile, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"knoc8.{name}")
