from __future__ import annotations

import html
import re

# Only the actual hard-gate phrases get flagged RED — the parts that would
# disqualify an early-career candidate. Everything else stays normal so the
# fault actually stands out (instead of the whole JD turning red).
_PATTERNS = [
    r"ph\.?\s?d\b",
    r"doctoral|doctorate",
    # 3+ years / 5-7 years / 10 years — skip "1-2 years" (not a blocker)
    r"(?:[3-9]|1[0-9])\s*\+?\s*(?:to\s*\d+\s*|-\s*\d+\s*)?(?:years|yrs)",
    r"no sponsorship|not (?:able to |be able to )?sponsor\w*|without sponsorship"
    r"|unable to sponsor|do(?:es)? not (?:offer |provide )?sponsor\w*|cannot sponsor"
    r"|sponsorship (?:is )?not",
    r"security clearance|active clearance|ts/sci|secret clearance",
    r"u\.?s\.? citizen\w*|must be a citizen",
    r"green card",
]
_RE = re.compile("(" + "|".join(_PATTERNS) + ")", re.I)


def highlight_html(desc: str) -> str:
    """Escape the JD and wrap only the hard-gate phrases in a red span."""
    safe = html.escape(desc or "")
    safe = _RE.sub(r"<span class=hl-gate>\1</span>", safe)
    return safe.replace("\n", "<br>")
