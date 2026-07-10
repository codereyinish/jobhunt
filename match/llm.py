from __future__ import annotations

import json
import re
import shutil
import subprocess


def claude_available() -> bool:
    return shutil.which("claude") is not None


def _run(prompt: str, timeout: int = 180) -> str:
    """Call the local `claude` CLI headless (uses the user's subscription)."""
    claude = shutil.which("claude") or "claude"
    r = subprocess.run([claude, "-p", prompt], capture_output=True, text=True,
                       timeout=timeout)
    return (r.stdout or "").strip()


def _extract_array(text: str):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def rank(preference: str, jobs: list[dict], timeout: int = 180) -> dict[int, int]:
    """Semantically score each job 0-100 against a plain-English preference.

    Returns {job_id: fit}. One `claude -p` call for the whole shortlist, so it's
    fast and free — pre-filter to a shortlist before calling.
    """
    if not jobs:
        return {}
    listing = "\n".join(
        f"{j['id']}: {j.get('title', '')} @ {j.get('company', '')} — {j.get('location', '')}"
        for j in jobs
    )
    prompt = (
        "You rank job postings for a candidate by fit.\n\n"
        f"CANDIDATE PREFERENCE:\n{preference}\n\n"
        "Score EACH job 0-100 (100 = ideal fit). Judge role, seniority, field and "
        "location. Match semantically — e.g. a 'voice AI' preference should reward "
        "speech / audio / ASR / conversational roles even if worded differently, and "
        "penalise roles that clash (wrong seniority, unrelated field).\n\n"
        'Return ONLY a JSON array, no prose: [{"id": <id>, "fit": <0-100>}, ...]\n\n'
        f"JOBS:\n{listing}"
    )
    data = _extract_array(_run(prompt, timeout)) or []
    out: dict[int, int] = {}
    for item in data:
        try:
            out[int(item["id"])] = max(0, min(100, int(item["fit"])))
        except (KeyError, ValueError, TypeError):
            continue
    return out
