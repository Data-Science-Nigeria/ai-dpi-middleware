import sys

from loguru import logger

# Initialize Loguru settings
logger.remove()  # Remove default logger configuration

logger.add(
    sys.stdout,
    format="{time} - {level} - {message}",
    level="INFO",
    backtrace=True,
    diagnose=True,
)

logger.add(
    "logs/all.log", rotation="100 MB", retention="3 days", level="DEBUG"
)
