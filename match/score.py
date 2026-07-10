from __future__ import annotations

# Ex-US signals that disqualify an otherwise-"remote" role.
_EX_US = ["europe", "emea", "united kingdom", " uk", "india", "apac", "germany",
          "france", "spain", "poland", "brazil", "latam", "ontario", "canada only",
          "australia", "singapore", "netherlands", "ireland", "finland", "denmark",
          "sweden", "portugal", "mexico", "argentina", "philippines", "nigeria"]


def location_ok(job: dict, cfg: dict) -> tuple[bool, bool]:
    """Return (passes_filter, is_remote) for a job under the location config."""
    loc = (job.get("location") or "").lower()
    remote = bool(job.get("remote")) or "remote" in loc
    locs = cfg["locations"]

    for city in locs.get("allowed_cities", []):
        if city.lower() in loc:
            return True, remote
    for st in locs.get("allowed_states", []):
        s = st.lower()
        if f", {s}" in loc or loc.strip() == s or f"({s})" in loc:
            return True, remote

    if remote and locs.get("allow_remote_us", True):
        if any(b in loc for b in _EX_US):
            return False, remote
        return True, remote

    if not loc:               # unknown location — keep for manual review
        return True, remote
    return False, remote


def score_job(job: dict, cfg: dict) -> tuple[int, str | None]:
    """Score a job and assign its tier. Returns (0, None) to drop the job.

    Tier is decided by the TITLE first — description keywords are boilerplate-
    heavy and cause false niche hits, so they only reinforce (or, if the title
    is generic, weakly infer) a tier.
    """
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()

    for ex in cfg.get("exclude_title_keywords", []):
        if ex.lower() in title:
            return 0, None
    for s in cfg.get("exclude_seniority", []):
        if s.lower() in title:
            return 0, None

    roles = cfg.get("require_role_keywords") or []
    if roles and not any(r.lower() in title for r in roles):
        return 0, None

    tiers = cfg["tiers"]

    # Tier from the title (authoritative).
    tier, weight = None, 0
    for name, spec in tiers.items():
        if any(k.lower() in title for k in spec["keywords"]) and spec["weight"] > weight:
            tier, weight = name, spec["weight"]

    # If the title is generic (e.g. "Software Engineer"), infer a niche tier
    # only when the description mentions it strongly (>= 2 distinct keywords).
    if tier is None:
        best = 0
        for name, spec in tiers.items():
            hits = sum(1 for k in spec["keywords"] if k.lower() in desc)
            if hits >= 2 and spec["weight"] > best:
                tier, best = name, spec["weight"]
                weight = int(spec["weight"] * 0.6)   # weaker: title didn't confirm
    if tier is None:
        return 0, None

    title_hits = sum(1 for k in tiers[tier]["keywords"] if k.lower() in title)
    desc_hits = sum(1 for k in tiers[tier]["keywords"] if k.lower() in desc)
    score = weight + title_hits * 8 + min(desc_hits, 5) * 2

    for k in cfg.get("boost_title_keywords", []):
        if k.lower() in title:
            score += cfg.get("boost_amount", 40)
            break
    return int(min(score, 200)), tier
