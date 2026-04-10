import sys

from loguru import logger

from app.config_yaml import get_yaml_config

_cfg = get_yaml_config().logging

logger.remove()

logger.add(
    sys.stdout,
    format="{time} - {level} - {message}",
    level=_cfg.level,
    backtrace=True,
    diagnose=True,
)

logger.add(
    _cfg.file,
    rotation="100 MB",
    retention="3 days",
    level="DEBUG",
)
