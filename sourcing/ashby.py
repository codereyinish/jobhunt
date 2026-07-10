from __future__ import annotations

import requests

from .base import http_get, strip_html

API = "https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true"


def fetch(name: str) -> list[dict]:
    """Fetch public postings for one Ashby job-board name.

    Board names are company-configured and case-sensitive; unknown names 404,
    so we return [] and let callers scan candidates safely.
    """
    try:
        r = http_get(API.format(name=name))
    except requests.RequestException:
        return []
    try:
        data = r.json()
    except ValueError:
        return []
    out = []
    for j in data.get("jobs", []):
        loc = j.get("location") or ""
        out.append({
            "source": "ashby",
            "source_id": f"{name}:{j.get('id', j.get('jobUrl', ''))}",
            "company": name,
            "title": j.get("title", ""),
            "location": loc,
            "remote": 1 if j.get("isRemote") else 0,
            "url": j.get("applyUrl") or j.get("jobUrl", ""),
            "description": strip_html(j.get("descriptionHtml") or j.get("descriptionPlain", "")),
            "posted_at": j.get("publishedAt", ""),
        })
    return out
