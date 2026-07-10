from __future__ import annotations

import html
import re

import requests

UA = "Mozilla/5.0 (compatible; jobhunt/0.1; personal job search)"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n\s*\n\s*\n+")


def http_get(url: str, params: dict | None = None, timeout: int = 20,
             headers: dict | None = None) -> requests.Response:
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, headers=h, timeout=timeout)
    r.raise_for_status()
    return r


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    text = _WS_RE.sub("\n\n", text)
    return text.strip()
