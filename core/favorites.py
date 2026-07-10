from __future__ import annotations

import re
from urllib.parse import urlparse

import yaml

from .config import CONFIG_DIR, DATA_DIR

FAV_PATH = CONFIG_DIR / "favorites.yaml"        # machine-managed, gitignored
PREF_PATH = DATA_DIR / "preference.txt"         # your saved rank preference


def parse_company_url(url: str) -> dict | None:
    """Detect the ATS vendor + token/tenant from a company careers URL.

    Supports Greenhouse, Lever, Ashby, Workday. Returns None if unrecognized.
    """
    u = urlparse(url if "//" in url else "https://" + url)
    host = (u.hostname or "").lower()
    parts = [p for p in u.path.split("/") if p]

    if "greenhouse.io" in host and parts:
        return {"vendor": "greenhouse", "token": parts[0]}
    if "lever.co" in host and parts:
        return {"vendor": "lever", "token": parts[0]}
    if "ashbyhq.com" in host and parts:
        return {"vendor": "ashby", "token": parts[0]}   # case-sensitive
    if "myworkdayjobs.com" in host:
        segs = parts[:]
        if segs and re.match(r"^[a-z]{2}-[A-Z]{2}$", segs[0]):   # drop locale
            segs = segs[1:]
        return {"vendor": "workday", "host": host,
                "tenant": host.split(".")[0], "site": segs[0] if segs else "Search"}
    return None


def _load() -> dict:
    if not FAV_PATH.exists():
        return {}
    with open(FAV_PATH) as f:
        return yaml.safe_load(f) or {}


def add_favorite(entry: dict) -> str:
    """Append a parsed company entry to favorites.yaml. Returns added/exists."""
    fav = _load()
    vendor = entry["vendor"]
    fav.setdefault(vendor, [])
    if vendor == "workday":
        if any(isinstance(w, dict) and w.get("host") == entry["host"] for w in fav["workday"]):
            return "exists"
        fav["workday"].append({"host": entry["host"], "tenant": entry["tenant"],
                               "site": entry["site"]})
    else:
        if entry["token"] in fav[vendor]:
            return "exists"
        fav[vendor].append(entry["token"])
    FAV_PATH.write_text(yaml.safe_dump(fav, sort_keys=True))
    return "added"


def load_preference() -> str:
    return PREF_PATH.read_text().strip() if PREF_PATH.exists() else ""


def save_preference(text: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    PREF_PATH.write_text(text.strip())
