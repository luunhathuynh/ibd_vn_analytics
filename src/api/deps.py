from __future__ import annotations

from src.config import load_config

SERVICE_VERSION = "0.1.0"


def get_config() -> dict:
    return load_config()
