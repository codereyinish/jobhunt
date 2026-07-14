from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


@lru_cache
def _load(name: str) -> dict:
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f) or {}


def settings() -> dict:
    return _load("settings.yaml")


def profile() -> dict:
    return _load("profile.yaml")


def resume_text() -> str:
    """Your resume as plain text — from config/resume.txt (preferred, gitignored)
    or a .txt/.md resume_path. Used by the deep-read to compare you vs each JD."""
    p = CONFIG_DIR / "resume.txt"
    if p.exists():
        return p.read_text().strip()
    rp = (profile().get("resume_path") or "").strip()
    if rp.lower().endswith((".txt", ".md")):
        try:
            return Path(rp).read_text().strip()
        except OSError:
            return ""
    return ""


def save_resume(text: str) -> None:
    (CONFIG_DIR / "resume.txt").write_text((text or "").strip())


def search_terms() -> list:
    """JobSpy search keywords — from config/keywords.txt (editable in the UI) or
    the settings.yaml jobspy.search_terms fallback."""
    p = CONFIG_DIR / "keywords.txt"
    if p.exists():
        terms = [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]
        if terms:
            return terms
    return (settings().get("jobspy") or {}).get("search_terms", [])


def save_keywords(text: str) -> None:
    (CONFIG_DIR / "keywords.txt").write_text((text or "").strip())


def resume_from_upload(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded resume (.txt/.md/.pdf)."""
    name = (filename or "").lower()
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore").strip()
    if name.endswith(".pdf"):
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    return data.decode("utf-8", errors="ignore").strip()


_PROMPT_PATH = CONFIG_DIR / "analyze_prompt.txt"


def analyze_prompt() -> str:
    """The editable deep-read prompt template. Must keep <<PROFILE>>, <<RESUME>>,
    <<JOBS>> markers. Falls back to the built-in default if the file is absent."""
    if _PROMPT_PATH.exists():
        t = _PROMPT_PATH.read_text().strip()
        if t:
            return t
    from ..match.analyze import DEFAULT_PROMPT
    return DEFAULT_PROMPT


def save_prompt(text: str) -> None:
    _PROMPT_PATH.write_text((text or "").strip())


def companies() -> dict:
    """Curated companies.yaml merged with the user's favorites.yaml (added via
    `jobhunt add`). Not cached, so newly-added favorites take effect at once."""
    base = _load("companies.yaml")
    fav_path = CONFIG_DIR / "favorites.yaml"
    fav = {}
    if fav_path.exists():
        with open(fav_path) as f:
            fav = yaml.safe_load(f) or {}

    merged: dict = {}
    for key in set(base) | set(fav):
        a, b = base.get(key) or [], fav.get(key) or []
        if key == "workday":
            seen, out = set(), []
            for w in a + b:
                h = w.get("host") if isinstance(w, dict) else w
                if h and h not in seen:
                    seen.add(h); out.append(w)
            merged[key] = out
        else:
            merged[key] = list(dict.fromkeys(a + b))
    return merged
