from __future__ import annotations

from ..core.config import profile, resume_text
from .llm import _extract_array, _run

# Editable via the UI (config/analyze_prompt.txt). Must keep the three markers.
DEFAULT_PROMPT = """\
You predict, for ONE candidate, the realistic odds of GETTING each job (landing an \
interview/offer) IF they apply — by comparing their RESUME to the role's real \
requirements and how competitive it is. Titles lie; read the requirements and \
responsibilities, then judge honestly.

CANDIDATE PROFILE:
<<PROFILE>>
<<RESUME>>
<<LESSONS>>
For EACH job return an object with:
- id
- company_type: yc_early | funded_startup | unicorn | public_corp | staffing_proxy | unknown
- requires_phd: true ONLY if a PhD is REQUIRED/mandatory. If 'PhD preferred' or 'or \
equivalent experience', set false.
- min_years: the REQUIRED minimum years. Treat 'preferred'/'a plus' as not required (0). \
Use the lower bound of any range.
- sponsorship: offers | silent | no
- works_for_me: true/false — can THIS candidate realistically apply? Only false for a HARD \
bar: a truly required PhD they lack, clearly more required years than they have, or \
explicit 'no sponsorship now or in future'. Do NOT reject on merely 'preferred' quals. \
F-1 OPT grants ~3 years, so 'must be authorized to work' is FINE.
- fit: 0-100 — realistic probability of an interview/offer if they apply, given their \
resume vs this role's bar AND typical competition. Be honest and calibrated.
- disqualifiers: array of {"label","quote"} objects. label = a SHORT tag, max 4 \
words (e.g. "PhD required", "5+ years", "US citizen only", "Master's required"). \
quote = the EXACT verbatim text from the job description that triggered it, copied \
word-for-word so it can be found in the text (max ~15 words). Empty array if none.
- reason: one short sentence citing the key resume-vs-requirement evidence

Return ONLY a JSON array, no prose.

JOBS:

<<JOBS>>"""

# Lines worth keeping — they carry the real gating signals. Everything else
# (mission, benefits, boilerplate) is dropped to save tokens + reduce noise.
_SIGNAL = ("phd", "ph.d", "doctorate", "bachelor", "master", "degree", "year", "yrs",
           "sponsor", "visa", "authoriz", "clearance", "citizen", "green card", "opt",
           "h-1b", "h1b", "qualif", "requirement", "must have", "minimum", "preferred",
           "experience", "you have", "you'll", "we're looking", "responsib")


def _snippet(desc: str, cap: int = 2400) -> str:
    """Keep the role context (top of the JD, where responsibilities + most
    requirements live) plus any requirement-bearing lines from the remainder."""
    if not desc:
        return ""
    head = desc[:1700]
    lines = [ln for ln in desc[1700:].splitlines() if any(s in ln.lower() for s in _SIGNAL)]
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


def _assemble(jobs_block: str) -> str:
    """Fill the editable template: profile + resume + learned lessons + jobs.
    Shared by the real call and the 'See prompt' preview so they never drift."""
    from ..core.config import analyze_prompt
    from ..core.favorites import lessons_block
    resume = resume_text()
    resume_block = (f"CANDIDATE RESUME (compare their real experience to each JD):\n"
                    f"{resume[:4500]}\n" if resume
                    else "(No resume provided — judge on the profile facts above.)\n")
    tmpl = analyze_prompt()
    lessons = lessons_block()
    if "<<LESSONS>>" in tmpl:
        tmpl = tmpl.replace("<<LESSONS>>", lessons)
    elif lessons:                                # older custom prompts: inject before jobs
        tmpl = tmpl.replace("<<JOBS>>", lessons + "\n<<JOBS>>", 1)
    return (tmpl.replace("<<PROFILE>>", _profile_block())
                .replace("<<RESUME>>", resume_block)
                .replace("<<JOBS>>", jobs_block))


def effective_prompt() -> str:
    """The prompt a call would actually send, with a placeholder for the job batch —
    for the 'See prompt' view so you can see your lessons baked in."""
    return _assemble("[ …the batch of shortlisted jobs being screened is inserted here… ]")


def analyze(jobs: list[dict], timeout: int = 300) -> dict[int, dict]:
    """Deep-read each job's requirements vs the candidate's profile AND resume."""
    if not jobs:
        return {}
    blocks = "\n".join(
        f"### JOB {j['id']}\nTitle: {j.get('title', '')}\nCompany: {j.get('company', '')}\n"
        f"Location: {j.get('location', '')}\nRequirements:\n{_snippet(j.get('description', ''))}"
        for j in jobs
    )
    prompt = _assemble(blocks)
    data = _extract_array(_run(prompt, timeout)) or []
    out: dict[int, dict] = {}
    for item in data:
        try:
            out[int(item["id"])] = item
        except (KeyError, ValueError, TypeError):
            continue
    return out
