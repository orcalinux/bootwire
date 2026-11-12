# src/bootwire/config.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

_DEFAULT = {
    "general": {
        "timeout": 0.5,         # seconds to wait for a response
        "erase_timeout": 5.0,   # seconds to wait for one ERASE response (one erase block)
        "max_retries": 3,       # resends after the first attempt
    },
    "serial": {
        "port": None,           # None = pick automatically or ask
        "baudrate": 115200,
    },
}


def load_config(path: Optional[str] = None) -> dict:
    """
    Load the first config file found, in this order:
      1. `path` argument
      2. $BOOTWIRE_CONFIG
      3. ./bootwire.yaml
      4. ~/.bootwire.yaml
    Values in the file override the defaults; unknown keys are ignored.
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    env_path = os.getenv("BOOTWIRE_CONFIG")
    if env_path:
        candidates.append(Path(env_path))
    candidates += [Path.cwd() / "bootwire.yaml", Path.home() / ".bootwire.yaml"]

    cfg = {section: dict(values) for section, values in _DEFAULT.items()}
    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = yaml.safe_load(p.read_text()) or {}
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        for section, defaults in _DEFAULT.items():
            values = data.get(section)
            if isinstance(values, dict):
                cfg[section].update({k: v for k, v in values.items() if k in defaults and v is not None})
        break
    return cfg
