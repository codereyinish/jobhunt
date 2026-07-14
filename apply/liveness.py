from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

from ..sourcing.base import UA, http_get

# Phrases that mean a (non-ATS) posting is dead even at HTTP 200.
_DEAD = [
    "no longer accepting", "no longer available", "position has been filled",
    "posting is closed", "job is closed", "this job is no longer",
    "not currently accepting", "position is closed",
    "this position has been closed", "applications are closed",
]


def _parse(url: str):
    """(vendor, token, job_id) from an ATS job URL, else (None, None, None)."""
    u = urlparse(url)
    host = (u.hostname or "").lower()
    parts = [p for p in u.path.split("/") if p]
    if "greenhouse.io" in host and "jobs" in parts:
        i = parts.index("jobs")
        if len(parts) > i + 1:
            return "greenhouse", parts[0], parts[i + 1]
    if "lever.co" in host and len(parts) >= 2:
        return "lever", parts[0], parts[1]
    if "ashbyhq.com" in host and len(parts) >= 2:
        return "ashby", parts[0], parts[1]
    return None, None, None


def _api_ok(url: str) -> bool:
    try:
        http_get(url)          # raises on 4xx/5xx
        return True
    except requests.RequestException:
        return False


def _ashby_has(name: str, jid: str) -> bool:
    try:
        data = http_get(f"https://api.ashbyhq.com/posting-api/job-board/{name}").json()
    except (requests.RequestException, ValueError):
        return False
    return any(jid in (str(j.get("applyUrl", "")) + str(j.get("jobUrl", ""))
                       + str(j.get("id", ""))) for j in data.get("jobs", []))


def _html_ok(url: str) -> bool:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=12, allow_redirects=True)
    except requests.RequestException:
        return False
    if r.status_code >= 400 or "error=true" in r.url:   # greenhouse soft-404 redirect
        return False
    return not any(p in r.text.lower() for p in _DEAD)


def is_live(url: str) -> bool:
    """Is this posting still open? For ATS jobs we check the ATS API (the source
    of truth); for everything else, an HTTP + closed-phrase check."""
    if not url:
        return False
    vendor, token, jid = _parse(url)
    if vendor == "greenhouse" and jid:
        return _api_ok(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{jid}")
    if vendor == "lever" and jid:
        return _api_ok(f"https://api.lever.co/v0/postings/{token}/{jid}")
    if vendor == "ashby" and jid:
        return _ashby_has(token, jid)
    return _html_ok(url)
