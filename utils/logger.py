import logging
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "artifacts" / "logs" / "run.log"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Get a named logger that writes to the console and to artifacts/logs/run.log."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter(_FORMAT)
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(console)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    return logger
