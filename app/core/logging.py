import sys

from loguru import logger

from app.config import get_config

_cfg = get_config()

logger.remove()

logger.add(
    sys.stdout,
    format="{time} - {level} - {message}",
    level=_cfg['logging']['level'],
    backtrace=True,
    diagnose=True,
)

logger.add(
    _cfg['logging']['file'],
    rotation="100 MB",
    retention="3 days",
    level="DEBUG",
)
