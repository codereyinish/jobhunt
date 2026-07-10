from __future__ import annotations

import requests

from .base import http_get, strip_html

API = "https://remoteok.com/api"


def fetch() -> list[dict]:
    """Fetch the RemoteOK public feed (no auth). First element is a legal
    notice, not a job, so we skip anything without an 'id'."""
    try:
        r = http_get(API)
    except requests.RequestException:
        return []
    out = []
    for j in r.json():
        if not isinstance(j, dict) or "id" not in j:
            continue
        out.append({
            "source": "remoteok",
            "source_id": str(j["id"]),
            "company": j.get("company", "") or "",
            "title": j.get("position", "") or "",
            "location": j.get("location", "") or "Remote",
            "remote": 1,
            "url": j.get("url", "") or "",
            "description": strip_html(j.get("description", "")),
            "posted_at": j.get("date", "") or "",
        })
    return out
