from __future__ import annotations

from urllib.parse import urlparse

# host substring -> ATS/board name. Order matters (first match wins).
_HOSTS = [
    ("greenhouse.io", "greenhouse"),
    ("lever.co", "lever"),
    ("ashbyhq.com", "ashby"),
    ("myworkdayjobs.com", "workday"),
    ("icims.com", "icims"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("jobvite.com", "jobvite"),
    ("taleo.net", "taleo"),
    ("bamboohr.com", "bamboohr"),
    ("workable.com", "workable"),
    ("indeed.com", "indeed"),
    ("linkedin.com", "linkedin"),
    ("glassdoor.com", "glassdoor"),
]

# Where we can build a reliable standardized auto-filler.
AUTOFILLABLE = {"greenhouse", "lever", "ashby", "workday"}
# Board-hosted apply = you stay on their turf (LinkedIn = ban risk).
BOARD_HOSTED = {"indeed", "linkedin", "glassdoor"}


def classify_url(url: str, source: str = "") -> str:
    """Return the apply destination type for a job's URL.

    'custom' = an unknown company career site (snowflake form).
    """
    # Jobs sourced directly from an ATS endpoint are that ATS by definition.
    for name in ("greenhouse", "lever", "ashby"):
        if source.startswith(name):
            return name
    host = (urlparse(url).hostname or "").lower()
    for needle, name in _HOSTS:
        if needle in host:
            return name
    return "custom" if host else "unknown"


def apply_path(kind: str) -> str:
    if kind in AUTOFILLABLE:
        return "auto"          # standardized form -> Playwright auto-fill
    if kind in BOARD_HOSTED:
        return "confirm"       # board-hosted -> you click submit (LinkedIn risk)
    return "manual"            # custom/unknown -> AI agent or manual
