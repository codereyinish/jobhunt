"""Assisted ATS auto-fill.

Opens a *visible* Chromium on a job's application form, fills the fields it can
recognize from your profile (name, contact, links, and the work-authorization
questions that matter most for F-1 OPT), then hands YOU the browser to review
and click Submit. Nothing is ever submitted automatically.

Run:  python -m jobhunt.apply.autofill <job_id>
      python -m jobhunt.apply.autofill --url <application_url>   # ad-hoc test
"""
from __future__ import annotations

import sys
import time

from ..core import db
from ..core.config import profile

# ── What to fill. Each concept: the value, and label patterns to recognize it.
#    Order matters — first matching rule wins for a given field.


def _profile_values() -> dict:
    p = profile()
    name = (p.get("name") or "").strip()
    first, _, last = name.partition(" ")
    wa = p.get("work_authorization") or {}
    needs = bool(wa.get("needs_sponsorship"))
    return {
        "first": first,
        "last": last or first,
        "name": name,
        "email": (p.get("email") or "").strip(),
        "phone": (p.get("phone") or "").strip(),
        "linkedin": (p.get("linkedin") or "").strip(),
        "github": (p.get("github") or "").strip(),
        "portfolio": (p.get("portfolio") or "").strip(),
        "location": (p.get("location") or "").strip(),
        "resume_path": (p.get("resume_path") or "").strip(),
        # yes = authorized to work now (OPT); needs sponsorship in the future.
        "authorized": "yes",
        "sponsorship": "yes" if needs else "no",
    }


# concept -> label regexes (matched against label text, lowercased)
_TEXT_RULES = [
    ("email", r"e-?mail"),
    ("phone", r"phone|mobile|cell"),
    ("linkedin", r"linkedin"),
    ("github", r"github"),
    ("portfolio", r"portfolio|website|personal site|personal url"),
    ("first", r"first name|given name|legal first"),
    ("last", r"last name|surname|family name|legal last"),
    ("location", r"\b(current )?(location|city)\b|where do you (live|reside)|your city"),
    ("name", r"^\s*(full |your )?name\b|full legal name"),
]

# Never treat these as fillable text — they're custom dropdowns/essays where a
# wrong free-text answer does damage. If a label hits one, we leave it for you.
_SKIP = r"relocat|open to work|earliest|deadline|timeline|why |cover letter|" \
        r"salary|compensation|how did you hear|referr|pronoun|gender|race|" \
        r"veteran|disability|describe|tell us|what interests"

# select/radio questions -> which stored yes/no answer to use
_CHOICE_RULES = [
    ("sponsorship", r"sponsor|visa sponsor|require.*visa|now or in the future"),
    ("authorized", r"authorized to work|legally authorized|eligible to work|work authorization"),
]


def _match(label: str, rules) -> str | None:
    import re
    for concept, pat in rules:
        if re.search(pat, label):
            return concept
    return None


def _skippable(label: str) -> bool:
    import re
    return bool(re.search(_SKIP, label))


_JS_COLLECT = r"""() => {
  const els = [...document.querySelectorAll('input, textarea, select')];
  const out = [];
  els.forEach((el) => {
    const type = (el.type || '').toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image', 'checkbox', 'radio'].includes(type)) return;
    const off = el.offsetParent === null && el.tagName !== 'SELECT';
    if (off) return;                                   // skip hidden fields
    const idx = out.length;
    el.setAttribute('data-jh', idx);
    let label = '';
    if (el.id) {
      try { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
            if (l) label += ' ' + l.innerText; } catch (e) {}
    }
    const anc = el.closest('label, .field, .form-group, .application-field, [class*=field]');
    if (anc) label += ' ' + (anc.innerText || '');
    label += ' ' + (el.getAttribute('aria-label') || '') + ' ' +
             (el.name || '') + ' ' + (el.placeholder || '');
    out.push({
      idx, tag: el.tagName.toLowerCase(), type,
      label: label.replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 200),
      options: el.tagName === 'SELECT' ? [...el.options].map(o => o.text) : []
    });
  });
  // resume/CV file inputs, tracked separately
  const files = [];
  document.querySelectorAll('input[type=file]').forEach((el, i) => {
    el.setAttribute('data-jhf', i);
    const anc = el.closest('label, .field, [class*=field]');
    const lab = ((anc ? anc.innerText : '') + ' ' + (el.name || '') + ' ' +
                 (el.getAttribute('aria-label') || '')).toLowerCase();
    files.push({ i, label: lab });
  });
  return { fields: out, files };
}"""


def _choose_option(options: list[str], want: str) -> str | None:
    """Pick the option text matching a yes/no intent."""
    want = want.lower()
    for o in options:
        t = o.strip().lower()
        if want == "yes" and t in ("yes", "yes, i am", "yes, i do") or t == want:
            return o
    for o in options:                                  # loose: startswith
        if o.strip().lower().startswith(want):
            return o
    return None


def fill(page, vals: dict) -> list[str]:
    """Fill everything we recognize on the current page. Returns a log."""
    log: list[str] = []
    data = page.evaluate(_JS_COLLECT)

    for f in data["fields"]:
        sel = f"[data-jh='{f['idx']}']"
        label = f["label"]
        if _skippable(label):
            continue
        if f["tag"] == "select":
            concept = _match(label, _CHOICE_RULES) or _match(label, _TEXT_RULES)
            if not concept:
                continue
            want = vals.get(concept, "")
            opt = _choose_option(f["options"], want) if concept in ("authorized", "sponsorship") else None
            if opt:
                try:
                    page.select_option(sel, label=opt)
                    log.append(f"  ✓ [{label[:40]}] → {opt}")
                except Exception:
                    pass
            continue
        # text / textarea input
        concept = _match(label, _TEXT_RULES)
        if not concept:
            continue
        val = vals.get(concept, "")
        if not val:
            continue
        try:
            page.fill(sel, val)
            log.append(f"  ✓ [{label[:40]}] → {val}")
        except Exception:
            pass

    # resume upload
    resume = vals.get("resume_path")
    if resume and data["files"]:
        target = next((f for f in data["files"] if "resume" in f["label"] or "cv" in f["label"]),
                      data["files"][0])
        try:
            page.set_input_files(f"[data-jhf='{target['i']}']", resume)
            log.append(f"  ✓ resume uploaded ({resume})")
        except Exception as e:
            log.append(f"  ✗ resume upload failed: {e}")
    elif not resume:
        log.append("  ⚠ no resume_path in profile.yaml — upload it yourself")

    return log


def run(job: dict) -> None:
    from playwright.sync_api import sync_playwright

    url = job.get("url")
    if not url or url == "#":
        print("This job has no application URL.")
        return
    vals = _profile_values()
    print(f"\n▶ Opening application for: {job.get('title', '')} — {job.get('company', '')}")
    print(f"  {url}\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = browser.new_context(no_viewport=True)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2500)                    # let the form render

        # Some ATS hide the form behind an "Apply" button — click it if present.
        for txt in ("Apply for this job", "Apply", "I'm interested", "Apply Now"):
            try:
                btn = page.get_by_role("button", name=txt, exact=False).first
                if btn.is_visible(timeout=800):
                    btn.click(); page.wait_for_timeout(1500); break
            except Exception:
                continue

        log = fill(page, vals)
        print("Filled:")
        print("\n".join(log) if log else "  (no recognizable fields — fill manually)")
        print("\n⚠ REVIEW EVERY FIELD — especially work authorization — then click Submit yourself.")
        print("  Close the browser window when done.\n")

        if job.get("id"):
            _mark_drafted(job["id"])

        try:
            while browser.is_connected():
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def _mark_drafted(job_id: int) -> None:
    try:
        with db.connect() as conn:
            conn.execute("UPDATE jobs SET status='drafted' WHERE id=? AND status IN ('new','')", (job_id,))
            conn.execute(
                "INSERT INTO applications (job_id, status) VALUES (?, 'draft')", (job_id,))
            conn.commit()
    except Exception:
        pass


def _job_by_id(job_id: int) -> dict | None:
    with db.connect() as conn:
        r = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(r) if r else None


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python -m jobhunt.apply.autofill <job_id> | --url <url>")
        return 2
    if argv[0] == "--url":
        run({"url": argv[1], "title": "(ad-hoc)", "company": ""})
        return 0
    job = _job_by_id(int(argv[0]))
    if not job:
        print(f"No job with id {argv[0]}")
        return 1
    run(job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
