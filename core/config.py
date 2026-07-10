from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


@lru_cache
def _load(name: str) -> dict:
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f) or {}


def settings() -> dict:
    return _load("settings.yaml")


def profile() -> dict:
    return _load("profile.yaml")


def companies() -> dict:
    return _load("companies.yaml")
