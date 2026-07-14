from __future__ import annotations

import html

# Hard-gate signals — the lines that usually cause a rejection (highlight RED).
_GATE = ("phd", "ph.d", "doctorate", "sponsor", "visa", "authoriz", "clearance",
         "citizen", "green card", " opt", "h-1b", "h1b", "security clearance",
         "5+ years", "6+ years", "7+ years", "8+ years", "10+ years")
# Requirement/experience signals — relevant context (highlight AMBER).
_REQ = ("year", "yrs", "degree", "bachelor", "master", "requirement", "qualif",
        "must have", "minimum", "preferred", "experience", "required")


def highlight_html(desc: str) -> str:
    """Render a JD as HTML with requirement lines color-quoted:
    red for hard-gate lines (PhD/years/sponsorship), amber for other requirements."""
    lines = []
    for raw in (desc or "").splitlines():
        low = raw.lower()
        safe = html.escape(raw)
        if not raw.strip():
            lines.append("")
            continue
        if any(g in low for g in _GATE):
            lines.append(f"<span class=hl-gate>{safe}</span>")
        elif any(r in low for r in _REQ):
            lines.append(f"<span class=hl-req>{safe}</span>")
        else:
            lines.append(safe)
    return "<br>".join(lines)
