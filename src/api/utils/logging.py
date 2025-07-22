import logging
import sys
import os

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger with a standard format.
    The logging level can be set via the LOG_LEVEL environment variable (e.g., INFO, DEBUG).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
