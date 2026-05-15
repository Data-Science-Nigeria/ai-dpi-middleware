from pathlib import Path
from loguru import logger
from app.utils.load_yaml import get_yaml


_CONFIG_PATH = Path(__file__).parent / "default_config.yaml"

logger.info(f"Loading configuration from: {_CONFIG_PATH}")

settings = None

def get_config() -> dict:
    """Load configuration from environment variables."""
    if settings is not None:
        return settings
    return get_yaml(_CONFIG_PATH)

