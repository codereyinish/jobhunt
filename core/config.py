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
    """Curated companies.yaml merged with the user's favorites.yaml (added via
    `jobhunt add`). Not cached, so newly-added favorites take effect at once."""
    base = _load("companies.yaml")
    fav_path = CONFIG_DIR / "favorites.yaml"
    fav = {}
    if fav_path.exists():
        with open(fav_path) as f:
            fav = yaml.safe_load(f) or {}

    merged: dict = {}
    for key in set(base) | set(fav):
        a, b = base.get(key) or [], fav.get(key) or []
        if key == "workday":
            seen, out = set(), []
            for w in a + b:
                h = w.get("host") if isinstance(w, dict) else w
                if h and h not in seen:
                    seen.add(h); out.append(w)
            merged[key] = out
        else:
            merged[key] = list(dict.fromkeys(a + b))
    return merged
