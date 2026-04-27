# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

import os
import re
import yaml
from typing import Any


_ENV_PLACEHOLDER = re.compile(r"\[([A-Z][A-Z0-9_]*)\]")

def get_yaml(yaml_path):
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML config file not found at {yaml_path}")
    with yaml_path.open() as f:
        raw = yaml.safe_load(f) or {}
    return _substitute_env_vars(raw)

def _substitute_env_vars(obj: Any) -> Any:
    """Recursively replace [VAR_NAME] placeholders with env var values."""
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
                    return os.environ.get(match.group(1)) or match.group(0)
        return _ENV_PLACEHOLDER.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj
