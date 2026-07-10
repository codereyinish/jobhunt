from __future__ import annotations

from .base import http_get, strip_html
from ..core.config import settings

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def fetch() -> list[dict]:
    """Query the Adzuna API (official, keyword-based) across search_terms x
    locations. Returns [] if no free key is configured yet."""
    cfg = settings().get("adzuna") or {}
    app_id, app_key = cfg.get("app_id"), cfg.get("app_key")
    if not app_id or not app_key:
        return []

    country = cfg.get("country", "us")
    per_page = int(cfg.get("results_per_page", 50))
    terms = cfg.get("search_terms") or ["machine learning engineer"]
    locations = cfg.get("locations") or ["New York"]

    out: list[dict] = []
    seen: set[str] = set()
    for term in terms:
        for loc in locations:
            params = {
                "app_id": app_id, "app_key": app_key,
                "what": term, "where": loc,
                "results_per_page": per_page, "sort_by": "date",
            }
            if cfg.get("max_days_old"):
                params["max_days_old"] = cfg["max_days_old"]
            try:
                data = http_get(API.format(country=country), params=params).json()
            except Exception:
                continue
            for j in data.get("results", []):
                jid = str(j.get("id", ""))
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                out.append({
                    "source": "adzuna",
                    "source_id": jid,
                    "company": (j.get("company") or {}).get("display_name", ""),
                    "title": j.get("title", ""),
                    "location": (j.get("location") or {}).get("display_name", ""),
                    "url": j.get("redirect_url", ""),
                    "description": strip_html(j.get("description", "")),
                    "posted_at": j.get("created", ""),
                })
    return out
