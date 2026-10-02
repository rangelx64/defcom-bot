import logging

from .config import settings

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO),
                    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
