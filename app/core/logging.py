import sys

from loguru import logger

from app.config import get_config

_logging_cfg = get_config().get('logging', {})  # type: ignore

logger.remove()

logger.add(
    sys.stdout,
    format="{time} - {level} - {message}",
    level=_logging_cfg.get('level'),
    backtrace=True,
    diagnose=True,
)

logger.add(
    _logging_cfg.get('file'),
    rotation="100 MB",
    retention="3 days",
    level="DEBUG",
)
