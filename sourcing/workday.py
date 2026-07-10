from __future__ import annotations

import requests

from .base import UA, strip_html

CXS = "https://{host}/wday/cxs/{tenant}/{site}/jobs"


def fetch(entry: dict) -> list[dict]:
    """Fetch postings from one Workday tenant via its CXS search API.

    Workday has no single public endpoint — each company is its own tenant, so
    each entry needs host + tenant + site (read them off the careers-page URL:
    https://<host>/en-US/<site>/... where host starts with <tenant>).
    """
    host, tenant, site = entry.get("host"), entry.get("tenant"), entry.get("site")
    if not (host and tenant and site):
        return []
    url = CXS.format(host=host, tenant=tenant, site=site)
    headers = {"User-Agent": UA, "Accept": "application/json",
               "Content-Type": "application/json"}

    out: list[dict] = []
    offset, limit = 0, 20
    for _ in range(15):                       # cap ~300 jobs/tenant
        body = {"limit": limit, "offset": offset,
                "searchText": entry.get("search", ""), "appliedFacets": {}}
        try:
            r = requests.post(url, json=body, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError):
            break
        posts = data.get("jobPostings", [])
        if not posts:
            break
        for j in posts:
            path = j.get("externalPath", "")
            remote = "remote" in (j.get("remoteType") or "").lower()
            out.append({
                "source": "workday",
                "source_id": f"{tenant}:{path}",
                "company": tenant,
                "title": j.get("title", ""),
                "location": j.get("locationsText", ""),
                "remote": 1 if remote else 0,
                "url": f"https://{host}/en-US/{site}{path}",
                "description": strip_html(" ".join(j.get("bulletFields", []) or [])),
                "posted_at": j.get("postedOn", ""),
            })
        offset += limit
        if offset >= data.get("total", 0):
            break
    return out
