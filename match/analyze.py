from __future__ import annotations

from ..core.config import profile
from .llm import _extract_array, _run


def _profile_block() -> str:
    p = profile()
    wa = p.get("work_authorization") or {}
    return (
        f"Highest education: {p.get('highest_education', '?')} "
        f"(has PhD: {bool(p.get('has_phd'))})\n"
        f"Years of experience: {p.get('years_experience', 0)}\n"
        f"Work authorization: {wa.get('status', '?')}; needs future sponsorship: "
        f"{wa.get('needs_sponsorship')}; can work now for ~"
        f"{p.get('work_window_years', '?')} years on current status\n"
        f"Skills: {', '.join(p.get('skills', []) or [])}\n"
        f"Seeking: {', '.join(p.get('titles_seeking', []) or [])}\n"
        f"About: {p.get('summary', '')}"
    )


def analyze(jobs: list[dict], max_desc: int = 2600, timeout: int = 300) -> dict[int, dict]:
    """Deep-read each job DESCRIPTION vs the candidate profile via claude -p.

    Returns {id: analysis dict}. Batch a shortlist into this — do not call it
    over the whole DB.
    """
    if not jobs:
        return {}
    blocks = []
    for j in jobs:
        desc = (j.get("description") or "")[:max_desc]
        blocks.append(
            f"### JOB {j['id']}\nTitle: {j.get('title', '')}\n"
            f"Company: {j.get('company', '')}\nLocation: {j.get('location', '')}\n"
            f"Description:\n{desc}"
        )
    prompt = (
        "You screen jobs for ONE specific candidate. Read each job DESCRIPTION "
        "carefully — titles lie, the description holds the real requirements "
        "(education, years, visa sponsorship).\n\n"
        f"CANDIDATE:\n{_profile_block()}\n\n"
        "For EACH job, output an object with these fields:\n"
        "- id (integer)\n"
        "- company_type: yc_early | funded_startup | unicorn | public_corp | "
        "staffing_proxy | unknown  (staffing_proxy = consultancy/body-shop that "
        "reposts other companies' roles, e.g. Cognizant/Infosys/generic 'X Solutions Inc')\n"
        "- requires_phd: true/false (does it require or strongly prefer a PhD?)\n"
        "- min_years: integer years of experience required (0 for entry/new-grad)\n"
        "- sponsorship: offers | silent | no  (does the JD address visa sponsorship?)\n"
        "- works_for_me: true/false — can THIS candidate realistically apply? Set "
        "false if it needs a PhD they lack, more years than they have, or explicitly "
        "no sponsorship when they need it. Note: F-1 OPT already grants ~3 years of "
        "work authorization, so 'must be authorized to work' is usually FINE; only "
        "'no sponsorship now or in the future' is disqualifying.\n"
        "- fit: 0-100 overall fit for this candidate\n"
        "- disqualifiers: array of short strings (empty if none)\n"
        "- reason: one short sentence\n\n"
        "Return ONLY a JSON array of these objects, no prose.\n\n"
        f"JOBS:\n\n{chr(10).join(blocks)}"
    )
    data = _extract_array(_run(prompt, timeout)) or []
    out: dict[int, dict] = {}
    for item in data:
        try:
            out[int(item["id"])] = item
        except (KeyError, ValueError, TypeError):
            continue
    return out
