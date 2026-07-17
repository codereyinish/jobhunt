from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import yaml

from .config import CONFIG_DIR, DATA_DIR

FAV_PATH = CONFIG_DIR / "favorites.yaml"        # machine-managed, gitignored
PREF_PATH = DATA_DIR / "preference.txt"         # your saved rank preference
LOVED_PATH = DATA_DIR / "loved.json"            # ❤ companies (by name)
LESSONS_PATH = DATA_DIR / "lessons.json"        # why you rejected past apply-ready picks
LESSONS_CAP = 40                                # keep the prompt injection bounded


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


def loved_companies() -> set[str]:
    if LOVED_PATH.exists():
        try:
            return set(json.loads(LOVED_PATH.read_text()))
        except ValueError:
            return set()
    return set()


def toggle_loved(company: str) -> bool:
    """Add/remove a company from the ❤ set. Returns True if now loved."""
    company = (company or "").strip()
    if not company:
        return False
    loved = loved_companies()
    now = company not in loved
    loved.add(company) if now else loved.discard(company)
    DATA_DIR.mkdir(exist_ok=True)
    LOVED_PATH.write_text(json.dumps(sorted(loved)))
    return now


def load_lessons() -> list:
    """Your dislikes: [{id, title, company, reason}] — reasons a past apply-ready
    pick was wrong, fed back into the analyze prompt so calls stop repeating it."""
    if LESSONS_PATH.exists():
        try:
            return json.loads(LESSONS_PATH.read_text()) or []
        except ValueError:
            return []
    return []


def _save_lessons(lessons: list) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    LESSONS_PATH.write_text(json.dumps(lessons[-LESSONS_CAP:], indent=2))


def add_lesson(title: str, company: str, reason: str) -> int:
    """Record why a job shouldn't have surfaced. Returns the new lesson's id."""
    import time
    reason = (reason or "").strip()
    if not reason:
        return 0
    lid = int(time.time() * 1000)
    lessons = load_lessons()
    lessons.append({"id": lid, "title": (title or "").strip(),
                    "company": (company or "").strip(), "reason": reason})
    _save_lessons(lessons)
    return lid


def remove_lesson(lid: int) -> None:
    _save_lessons([l for l in load_lessons() if l.get("id") != lid])


def lessons_block() -> str:
    """The dislikes formatted for injection into the analyze prompt."""
    lessons = load_lessons()
    if not lessons:
        return ""
    lines = "\n".join(
        f'- "{l.get("title","")}"'
        + (f' at {l["company"]}' if l.get("company") else "")
        + f': {l.get("reason","")}'
        for l in lessons)
    return (
        "\nLESSONS FROM THE CANDIDATE — they reviewed earlier picks and explained why "
        "these were WRONG to surface as strong matches. Treat these as hard preferences: "
        "apply the same judgment and do NOT rate jobs highly that repeat these problems.\n"
        f"{lines}\n")


def load_preference() -> str:
    return PREF_PATH.read_text().strip() if PREF_PATH.exists() else ""


def save_preference(text: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    PREF_PATH.write_text(text.strip())
