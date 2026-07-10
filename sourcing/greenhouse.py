from __future__ import annotations

import requests

from .base import http_get, strip_html

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"


def fetch(token: str) -> list[dict]:
    """Fetch all public postings for one Greenhouse board token.

    Invalid/unknown tokens 404 — we return [] so callers can scan
    speculative tokens safely.
    """
    try:
        r = http_get(API.format(token=token))
    except requests.RequestException:
        return []
    out = []
    for j in r.json().get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        out.append({
            "source": "greenhouse",
            "source_id": f"{token}:{j['id']}",
            "company": token,
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("absolute_url", ""),
            "description": strip_html(j.get("content", "")),
            "posted_at": j.get("updated_at", ""),
        })
    return out
