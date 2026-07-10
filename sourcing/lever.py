from __future__ import annotations

import requests

from .base import http_get, strip_html

API = "https://api.lever.co/v0/postings/{token}?mode=json"


def fetch(token: str) -> list[dict]:
    """Fetch all public postings for one Lever company token."""
    try:
        r = http_get(API.format(token=token))
    except requests.RequestException:
        return []
    out = []
    for j in r.json():
        cats = j.get("categories") or {}
        out.append({
            "source": "lever",
            "source_id": f"{token}:{j['id']}",
            "company": token,
            "title": j.get("text", ""),
            "location": cats.get("location", "") or "",
            "url": j.get("hostedUrl", ""),
            "description": strip_html(j.get("descriptionPlain") or j.get("description", "")),
            "posted_at": str(j.get("createdAt", "")),
        })
    return out
