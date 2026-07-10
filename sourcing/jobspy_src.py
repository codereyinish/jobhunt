from __future__ import annotations

import math

from ..core.config import settings


def _clean(v):
    """JobSpy returns pandas cells — normalise NaN/None to ''."""
    if v is None:
        return ""
    try:
        if isinstance(v, float) and math.isnan(v):
            return ""
    except (TypeError, ValueError):
        pass
    return v


def fetch() -> list[dict]:
    """Scrape configured boards via JobSpy, one query per (term, location).

    Kept deliberately resilient: any single failing query is skipped so one
    rate-limited board can't sink the whole run.
    """
    cfg = settings().get("jobspy") or {}
    if not cfg.get("enabled"):
        return []

    from jobspy import scrape_jobs   # imported lazily; heavy dependency

    sites = cfg.get("sites") or ["indeed"]
    terms = cfg.get("search_terms") or ["software engineer"]
    locations = cfg.get("locations") or ["New York, NY"]
    results = int(cfg.get("results_wanted", 20))
    hours_old = cfg.get("hours_old")
    country = cfg.get("country_indeed", "USA")

    out: list[dict] = []
    seen: set[str] = set()
    for term in terms:
        for loc in locations:
            try:
                df = scrape_jobs(
                    site_name=sites,
                    search_term=term,
                    google_search_term=f"{term} jobs near {loc}",
                    location=loc,
                    results_wanted=results,
                    hours_old=hours_old,
                    country_indeed=country,
                    description_format="markdown",
                    verbose=0,
                )
            except Exception:
                continue
            if df is None or len(df) == 0:
                continue
            for _, r in df.iterrows():
                site = _clean(r.get("site")) or "jobspy"
                jid = _clean(r.get("id")) or _clean(r.get("job_url"))
                sid = f"{site}:{jid}"
                if not jid or sid in seen:
                    continue
                seen.add(sid)
                url = _clean(r.get("job_url_direct")) or _clean(r.get("job_url"))
                out.append({
                    "source": f"jobspy:{site}",
                    "source_id": sid,
                    "company": _clean(r.get("company")),
                    "title": _clean(r.get("title")),
                    "location": _clean(r.get("location")),
                    "remote": 1 if _clean(r.get("is_remote")) is True else 0,
                    "url": url,
                    "description": str(_clean(r.get("description")) or ""),
                    "posted_at": str(_clean(r.get("date_posted")) or ""),
                })
    return out
