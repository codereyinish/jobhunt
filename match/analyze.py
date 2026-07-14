from __future__ import annotations

from ..core.config import profile, resume_text
from .llm import _extract_array, _run

# Lines worth keeping — they carry the real gating signals. Everything else
# (mission, benefits, boilerplate) is dropped to save tokens + reduce noise.
_SIGNAL = ("phd", "ph.d", "doctorate", "bachelor", "master", "degree", "year", "yrs",
           "sponsor", "visa", "authoriz", "clearance", "citizen", "green card", "opt",
           "h-1b", "h1b", "qualif", "requirement", "must have", "minimum", "preferred",
           "experience", "you have", "you'll", "we're looking", "responsib")


def _snippet(desc: str, cap: int = 1300) -> str:
    """Trim a JD to a short role header + only the requirement-bearing lines."""
    if not desc:
        return ""
    head = desc[:480]
    lines = [ln for ln in desc.splitlines() if any(s in ln.lower() for s in _SIGNAL)]
    tail = "\n".join(lines)
    out = head + ("\n---\n" + tail if tail else "")
    return out[:cap]


def _profile_block() -> str:
    p = profile()
    wa = p.get("work_authorization") or {}
    return (
        f"Highest education: {p.get('highest_education', '?')} "
        f"(has PhD: {bool(p.get('has_phd'))})\n"
        f"Years of experience: {p.get('years_experience', 0)}\n"
        f"Work authorization: {wa.get('status', '?')}; needs future sponsorship: "
        f"{wa.get('needs_sponsorship')}; can work now ~{p.get('work_window_years', '?')} years\n"
        f"Skills: {', '.join(p.get('skills', []) or [])}\n"
        f"Seeking: {', '.join(p.get('titles_seeking', []) or [])}"
    )


def analyze(jobs: list[dict], timeout: int = 300) -> dict[int, dict]:
    """Deep-read each job's requirements vs the candidate's profile AND resume."""
    if not jobs:
        return {}
    resume = resume_text()
    resume_block = (f"\nCANDIDATE RESUME (compare their real experience to each JD):\n"
                    f"{resume[:4500]}\n" if resume
                    else "\n(No resume provided — judge on the profile facts above.)\n")
    blocks = [
        f"### JOB {j['id']}\nTitle: {j.get('title', '')}\nCompany: {j.get('company', '')}\n"
        f"Location: {j.get('location', '')}\nRequirements:\n{_snippet(j.get('description', ''))}"
        for j in jobs
    ]
    prompt = (
        "You screen jobs for ONE candidate. Read each job's REQUIREMENTS carefully "
        "(titles lie) and compare them to the candidate's profile and resume.\n\n"
        f"CANDIDATE PROFILE:\n{_profile_block()}\n{resume_block}\n"
        "For EACH job return an object with:\n"
        "- id\n"
        "- company_type: yc_early | funded_startup | unicorn | public_corp | "
        "staffing_proxy | unknown\n"
        "- requires_phd: true ONLY if a PhD is REQUIRED/mandatory. If it says "
        "'PhD preferred', 'PhD or equivalent experience', or lists it as a plus, "
        "set false (a preferred qualification is not a hard bar).\n"
        "- min_years: the REQUIRED minimum years. Treat 'preferred'/'a plus' as not "
        "required (0). Use the lower bound of any range.\n"
        "- sponsorship: offers | silent | no\n"
        "- works_for_me: true/false — can THIS candidate realistically apply? Only set "
        "false for a HARD bar: a truly required PhD they lack, a required minimum of "
        "clearly more years than they have, or explicit 'no sponsorship now or in "
        "future'. Do NOT reject on merely 'preferred' qualifications. F-1 OPT grants "
        "~3 years, so 'must be authorized to work' is FINE.\n"
        "- fit: 0-100 — how well the candidate's RESUME/experience matches this JD\n"
        "- disqualifiers: array of short strings (empty if none)\n"
        "- reason: one short sentence\n\n"
        "Return ONLY a JSON array, no prose.\n\n"
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
