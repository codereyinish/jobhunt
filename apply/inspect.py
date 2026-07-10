from __future__ import annotations

import json
import re

import requests

from ..sourcing.base import UA, strip_html

_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def _find_jobposting(html: str) -> dict | None:
    """Pull a schema.org JobPosting out of the page's JSON-LD, if present.
    Most Greenhouse/Lever/company pages embed one; JS-only SPAs (Ashby/Workday)
    may not."""
    for m in _LD_RE.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            graph = obj.get("@graph")
            if isinstance(graph, list):
                candidates = candidates + graph
            t = obj.get("@type", "")
            if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                return obj
    return None


def _location(jp: dict) -> str:
    if jp.get("jobLocationType") == "TELECOMMUTE":
        return "Remote"
    jl = jp.get("jobLocation")
    if isinstance(jl, list):
        jl = jl[0] if jl else None
    if isinstance(jl, dict):
        addr = jl.get("address", jl)
        if isinstance(addr, dict):
            country = addr.get("addressCountry")
            if isinstance(country, dict):
                country = country.get("name")
            parts = [addr.get("addressLocality"), addr.get("addressRegion"), country]
            return ", ".join(p for p in parts if isinstance(p, str) and p)
    return ""


def inspect(url: str) -> dict:
    """Fetch a job URL, follow redirects, and extract a normalized job dict.
    `final_url` is the resolved destination used for ATS classification.
    """
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
    final_url, html = r.url, r.text

    jp = _find_jobposting(html)
    if jp:
        org = jp.get("hiringOrganization")
        company = org.get("name", "") if isinstance(org, dict) else str(org or "")
        info = {
            "title": jp.get("title", ""),
            "company": company,
            "location": _location(jp),
            "description": strip_html(jp.get("description", "")),
        }
    else:                                   # fallback: page <title>
        m = _TITLE_RE.search(html)
        info = {"title": strip_html(m.group(1)) if m else "",
                "company": "", "location": "", "description": ""}
        info["_no_jsonld"] = True

    info["url"] = final_url
    info["final_url"] = final_url
    info["source"] = "manual"
    info["source_id"] = final_url
    return info
