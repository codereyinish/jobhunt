from __future__ import annotations

import html
import json

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .apply.router import apply_path, classify_url
from .core import db
from .core.config import settings
from .match.score import location_ok, score_job

app = FastAPI()

CSS = """
:root{
  --bg:#08090c; --panel:#101319; --panel2:#161a21; --elevated:#1b2029;
  --line:#1d222b; --line2:#2a313d;
  --text:#eef1f6; --muted:#8b93a1; --faint:#565f6d;
  --accent:#7c8cff; --accent-2:#a6b0ff; --accent-soft:rgba(124,140,255,.14);
  --green:#5bc48b; --amber:#e0ac5e; --red:#ec6f88; --violet:#b6a3ff;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:
    radial-gradient(1200px 600px at 78% -8%, rgba(124,140,255,.06), transparent 60%),
    var(--bg);
  color:var(--text);
  font-family:'Inter','Inter var',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size:14px;line-height:1.5;letter-spacing:-.006em;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
  font-feature-settings:'cv02','cv03','cv04','ss01'}
.wrap{max-width:1120px;margin:0 auto;padding:38px 30px 110px}
header{display:flex;align-items:center;justify-content:space-between;
  padding-bottom:22px;margin-bottom:26px;border-bottom:1px solid var(--line)}
.brand{font-size:21px;font-weight:700;letter-spacing:-.03em;display:flex;align-items:center;gap:9px}
.brand .dot{width:7px;height:7px;border-radius:50%;background:var(--green);
  box-shadow:0 0 0 3px rgba(91,196,139,.16)}
.meta{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums;letter-spacing:0}
.meta b{color:var(--text);font-weight:600}
a{color:var(--accent);text-decoration:none;transition:color .12s}
a:hover{color:var(--accent-2)}

.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;
  padding:20px 22px;margin-bottom:18px}
.panel h2{font-size:11px;text-transform:uppercase;letter-spacing:.11em;
  color:var(--muted);margin:0 0 14px;font-weight:600}
details.panel>summary{list-style:none;cursor:pointer;font-size:11px;text-transform:uppercase;
  letter-spacing:.11em;color:var(--muted);font-weight:600;display:flex;align-items:center;
  justify-content:space-between}
details.panel>summary::-webkit-details-marker{display:none}
details.panel>summary::after{content:'⌄';font-size:15px;transition:transform .18s}
details.panel[open]>summary::after{transform:rotate(180deg)}
details.panel[open]>summary{margin-bottom:15px}

form.row{display:flex;gap:9px;flex-wrap:wrap;align-items:center}
form.col{display:flex;flex-direction:column;gap:11px;align-items:flex-start}
input,select,textarea{background:var(--panel2);color:var(--text);
  border:1px solid var(--line2);border-radius:9px;padding:9px 12px;font-size:13.5px;
  outline:none;font-family:inherit;transition:border-color .12s, box-shadow .12s}
input::placeholder,textarea::placeholder{color:var(--faint)}
input:focus,select:focus,textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
select{appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238b93a1' stroke-width='1.4'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 11px center;padding-right:28px}
input.url{flex:1;min-width:340px}
textarea{width:100%;resize:vertical;line-height:1.5}
label.chk{color:var(--muted);display:flex;gap:7px;align-items:center;font-size:13px;user-select:none}
button{background:var(--accent);color:#0b0f1e;border:none;border-radius:9px;
  padding:9px 18px;font-size:13.5px;font-weight:640;cursor:pointer;letter-spacing:-.01em;
  transition:filter .12s, transform .05s}
button:hover{filter:brightness(1.08)}
button:active{transform:translateY(1px)}
.hint{color:var(--faint);font-size:12px}

.result{border:1px solid var(--line2);border-radius:13px;padding:17px 19px;
  background:var(--panel2);margin-top:15px}
.result .t{font-size:16px;font-weight:640;margin:0 0 6px;letter-spacing:-.01em}
.kv{color:var(--muted);font-size:13px;margin:3px 0}
.kv b{color:var(--text);font-weight:560}
.verdict{margin-top:10px;font-size:14px}
.fit-c{color:var(--green);font-weight:640}
.nofit{color:var(--red);font-weight:700}

table{width:100%;border-collapse:collapse}
th{text-align:left;color:var(--muted);font-size:10.5px;text-transform:uppercase;
  letter-spacing:.09em;font-weight:600;padding:0 11px 13px}
td{padding:13px 11px;border-top:1px solid var(--line);vertical-align:middle}
tbody tr{transition:background .1s}
tbody tr:hover td{background:var(--panel2)}
td.num{color:var(--faint);width:28px;font-variant-numeric:tabular-nums;font-size:12.5px}
.score{font-variant-numeric:tabular-nums;font-weight:700;width:42px;letter-spacing:-.02em}
.fit{font-variant-numeric:tabular-nums;font-weight:700;color:var(--accent);width:42px}
.tier{font-size:12px;color:var(--violet);white-space:nowrap}
.ctype{font-size:12px;color:var(--muted);white-space:nowrap}
.ctype.staffing{color:var(--amber)}
.why{color:var(--muted);font-size:12.5px;max-width:300px;display:inline-block;line-height:1.45}
.dq{color:var(--red);font-size:12.5px;font-weight:560;max-width:300px;display:inline-block;line-height:1.45}
.ctxpre{background:var(--panel2);border:1px solid var(--line2);border-radius:10px;
  padding:13px 14px;font-size:12px;line-height:1.55;white-space:pre-wrap;
  color:var(--muted);max-height:190px;overflow:auto;margin:0}
.company{font-weight:600;white-space:nowrap;letter-spacing:-.01em}
.cname.loved{color:var(--accent)}
.love{margin-left:9px;cursor:pointer;color:var(--faint);font-size:13px;opacity:0;
  transition:opacity .12s, color .12s, transform .1s;user-select:none;vertical-align:middle}
tr:hover .love{opacity:.5}
.love:hover{color:var(--red)}
.love:active{transform:scale(1.3)}
.love.on{opacity:1;color:var(--red)}
.role{color:var(--text);max-width:310px}
.loc{color:var(--muted);font-size:13px;max-width:180px}
td a{white-space:nowrap;font-size:13px}
.pill{display:inline-block;padding:3px 11px;border-radius:999px;font-size:11.5px;
  font-weight:600;border:1px solid transparent;letter-spacing:.01em}
.pill.auto{color:var(--green);background:rgba(91,196,139,.10);border-color:rgba(91,196,139,.26)}
.pill.confirm{color:var(--amber);background:rgba(224,172,94,.10);border-color:rgba(224,172,94,.26)}
.pill.manual{color:var(--muted);background:rgba(139,147,161,.08);border-color:var(--line2)}
.empty{color:var(--muted);padding:44px 0;text-align:center}
.pager{display:flex;align-items:center;justify-content:center;gap:20px;
  margin-top:20px;font-size:13px;color:var(--muted)}
.pager .faint{color:var(--faint)}
.pager .pageno{font-variant-numeric:tabular-nums}

.brandwrap{display:flex;flex-direction:column;gap:5px}
.toolbar{display:flex;gap:9px;align-items:center}
.tool-btn{background:var(--panel);border:1px solid var(--line2);border-radius:999px;
  padding:9px 15px;font-size:13px;font-weight:560;color:var(--text);cursor:pointer;
  display:flex;align-items:center;gap:6px;transition:border-color .14s, background .14s}
.tool-btn:hover{border-color:var(--accent);background:var(--panel2)}
.heart-btn{width:40px;height:40px;border-radius:50%;background:var(--panel);
  border:1px solid var(--line2);display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--red);font-size:17px;transition:border-color .14s, background .14s}
.heart-btn:hover{border-color:var(--red);background:var(--panel2)}
.overlay{position:fixed;inset:0;background:rgba(4,6,10,.7);backdrop-filter:blur(4px);
  display:none;align-items:flex-start;justify-content:center;z-index:30;padding-top:9vh}
#favtoggle:checked ~ .fav-ov{display:flex}
#preftoggle:checked ~ .pref-ov{display:flex}
#ctxtoggle:checked ~ .ctx-ov{display:flex}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--panel2);border:1px solid var(--line2);border-radius:999px;
  padding:6px 8px 6px 13px;font-size:13px;font-weight:560;display:flex;align-items:center;gap:9px}
.chip .love{opacity:1;margin:0;color:var(--red);font-size:14px}
.modal{background:var(--panel);border:1px solid var(--line2);border-radius:18px;
  padding:24px 26px;width:min(600px,92vw);position:relative;
  max-height:84vh;overflow:auto;box-shadow:0 30px 80px rgba(0,0,0,.55)}
.filein{background:var(--panel2);border:1px dashed var(--line2);border-radius:10px;
  padding:11px 13px;font-size:13px;color:var(--muted);width:100%}
.modal-close{position:absolute;top:13px;right:17px;cursor:pointer;color:var(--muted);
  font-size:22px;line-height:1;text-decoration:none}
.modal-close:hover{color:var(--text)}
.modal-h{font-size:11px;text-transform:uppercase;letter-spacing:.11em;
  color:var(--muted);margin:0 0 14px;font-weight:600}
"""

_TIER_LABEL = {"voice_speech": "voice", "ai_ml": "ai/ml", "swe_backend": "swe"}
_TYPE_LABEL = {"yc_early": "YC/early", "funded_startup": "startup", "unicorn": "unicorn",
               "public_corp": "public", "staffing_proxy": "staffing", "unknown": "—"}
_PAGE = 20


def _pager(page: int, has_next: bool, base: dict) -> str:
    from urllib.parse import urlencode
    if page == 0 and not has_next:
        return ""
    prev = (f"<a href='?{urlencode({**base, 'page': page - 1})}'>← prev</a>"
            if page > 0 else "<span class=faint>← prev</span>")
    nxt = (f"<a href='?{urlencode({**base, 'page': page + 1})}'>next →</a>"
           if has_next else "<span class=faint>next →</span>")
    return f"<div class=pager>{prev}<span class=pageno>page {page + 1}</span>{nxt}</div>"


def _toggles() -> str:
    return ("<input type=checkbox id=favtoggle hidden>"
            "<input type=checkbox id=preftoggle hidden>"
            "<input type=checkbox id=ctxtoggle hidden>")


def _toolbar() -> str:
    return (
        "<div class=toolbar>"
        "<label for=ctxtoggle class=tool-btn>&#9998;&nbsp; Resume</label>"
        "<label for=preftoggle class=tool-btn>&#10022;&nbsp; Preference</label>"
        "<label for=favtoggle class=heart-btn title='Loved companies'>&#9829;</label>"
        "</div>"
    )


def _context_modal() -> str:
    from .core.config import analyze_prompt, resume_text
    from .match.analyze import _profile_block
    resume, prompt = resume_text(), analyze_prompt()
    return (
        "<div class='overlay ctx-ov'><div class=modal>"
        "<label for=ctxtoggle class=modal-close>&times;</label>"
        "<div class=modal-h>Your resume</div>"
        "<form class=col method=post action='/resume' enctype='multipart/form-data'>"
        "<input class=filein type=file name=file accept='.txt,.md,.pdf'>"
        f"<textarea name=resume rows=9 style='width:100%' "
        f"placeholder='…or paste it as plain text'>{_e(resume)}</textarea>"
        "<div class=row><button type=submit>Save resume</button>"
        "<span class=hint>upload a .pdf/.txt or paste · then <code>analyze --force</code></span></div>"
        "</form>"
        "<div class=modal-h style='margin-top:22px'>What Claude sees — profile</div>"
        f"<pre class=ctxpre>{_e(_profile_block())}</pre>"
        "<div class=modal-h style='margin-top:22px'>Claude prompt · advanced</div>"
        "<form class=col method=post action='/prompt'>"
        f"<textarea name=prompt rows=10 style='width:100%;font-family:ui-monospace,monospace;"
        f"font-size:12px'>{_e(prompt)}</textarea>"
        "<div class=row><button type=submit>Save prompt</button>"
        "<span class=hint>keep &lt;&lt;PROFILE&gt;&gt; &lt;&lt;RESUME&gt;&gt; &lt;&lt;JOBS&gt;&gt; markers</span></div>"
        "</form></div></div>"
    )


def _fav_modal() -> str:
    from .core.favorites import loved_companies
    loved = sorted(loved_companies())
    if loved:
        chips = "".join(
            f"<span class=chip>{_e(c)}<span class='love on chip-x' data-c=\"{_e(c)}\" "
            f"onclick='love(this)'>&#9829;</span></span>" for c in loved)
        loved_html = f"<div class=chips>{chips}</div>"
    else:
        loved_html = ("<div class=hint>No loved companies yet — tap the ♥ next to any "
                      "company in the list below.</div>")
    return (
        "<div class='overlay fav-ov'><div class=modal>"
        "<label for=favtoggle class=modal-close>&times;</label>"
        "<div class=modal-h>Loved companies</div>"
        f"{loved_html}"
        "<div class=modal-h style='margin-top:22px'>Add a company by link</div>"
        "<form class=col method=post action='/add'>"
        "<input class=url type=text name=url style='width:100%' "
        "placeholder='Paste a careers link — Greenhouse / Lever / Ashby / Workday…'>"
        "<div class=row><button type=submit>Add &amp; fetch</button>"
        "<span class=hint>scanned on every future search via their ATS</span></div>"
        "</form></div></div>"
    )


def _pref_modal() -> str:
    from .core.favorites import load_preference
    pref = load_preference()
    ph = ("Describe what you want in plain English — e.g. “early-career engineer, "
          "need visa sponsorship, love voice / speech AI but open to backend, no senior "
          "roles, no internships, NYC or remote”")
    return (
        "<div class='overlay pref-ov'><div class=modal>"
        "<label for=preftoggle class=modal-close>&times;</label>"
        "<div class=modal-h>Rank by preference &nbsp;·&nbsp; AI</div>"
        "<form class=col method=post action='/rank'>"
        f"<textarea name=preference rows=3 style='width:100%' placeholder=\"{_e(ph)}\">{_e(pref)}</textarea>"
        "<input type=hidden name=tier value=''>"
        "<input type=hidden name=min_score value=40>"
        "<div class=row><button type=submit>Rank with Claude</button>"
        "<span class=hint>uses your Claude Pro CLI · free · may take ~30s</span></div>"
        "</form></div></div>"
    )


def _page(body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<link rel=preconnect href='https://fonts.googleapis.com'>"
            f"<link rel=preconnect href='https://fonts.gstatic.com' crossorigin>"
            f"<link rel=stylesheet href='https://fonts.googleapis.com/css2?"
            f"family=Inter:wght@400;500;600;700&display=swap'>"
            f"<title>jobhunt</title><style>{CSS}</style></head>"
            f"<body>{_toggles()}{_fav_modal()}{_pref_modal()}{_context_modal()}"
            f"<div class=wrap>{body}</div>{_JS}</body></html>")


_JS = """<script>
function love(el){
  var f=new FormData(); f.append('company', el.dataset.c);
  fetch('/love',{method:'POST',body:f}).then(function(r){return r.json();})
    .then(function(d){
      el.classList.toggle('on', d.loved);
      var n=el.parentNode.querySelector('.cname');
      if(n) n.classList.toggle('loved', d.loved);
    });
}
</script>"""


def _e(v) -> str:
    return html.escape(str(v or ""))


def _header(total: int | None = None, fresh: int | None = None) -> str:
    meta = ""
    if total is not None:
        bits = [f"<b>{total}</b> tracked"]
        if fresh:
            bits.append(f"<b>{fresh}</b> new · 24h")
        meta = f"<div class=meta>{' &nbsp;·&nbsp; '.join(bits)}</div>"
    return (f"<header><div class=brandwrap>"
            f"<div class=brand>jobhunt<span class=dot></span></div>{meta}</div>"
            f"{_toolbar()}</header>")


def _check_form(url: str = "") -> str:
    return (
        "<div class=panel><h2>Check a job link</h2>"
        "<form class=row method=post action='/check'>"
        f"<input class=url type=text name=url placeholder='Paste a job posting URL…' value='{_e(url)}'>"
        "<label class=chk><input type=checkbox name=save value=1> save if it fits</label>"
        "<button type=submit>Check</button>"
        "</form></div>"
    )


def _filters(tier: str, min_score: int, fresh: bool, sort: str, view: str,
             min_fit: int) -> str:
    topts = [("", "all tiers"), ("voice_speech", "voice"),
             ("ai_ml", "ai/ml"), ("swe_backend", "swe")]
    tsel = "".join(
        f"<option value='{v}'{' selected' if v == tier else ''}>{lbl}</option>"
        for v, lbl in topts)
    vopts = [("", "all jobs"), ("apply", "✓ apply-ready"), ("rejected", "✕ rejected"),
             ("call", "◷ last analysis")]
    vsel = "".join(
        f"<option value='{v}'{' selected' if v == view else ''}>{lbl}</option>"
        for v, lbl in vopts)
    fchk = " checked" if fresh else ""
    is_open = " open" if (view or fresh or tier) else ""
    return (
        f"<details class=panel{is_open}><summary>Filters</summary>"
        "<form class=row method=get action='/'>"
        f"<select name=view>{vsel}</select>"
        f"<select name=tier>{tsel}</select>"
        f"<input type=number name=min_score value={min_score} style='width:92px' title='min score'>"
        f"<label class=chk><input type=checkbox name=fresh value=1{fchk}> last 24h</label>"
        f"<label class=chk>min fit <input type=number name=min_fit value={min_fit} "
        f"style='width:64px' title='AI fit cutoff (apply-ready)'></label>"
        f"<input type=hidden name=sort value='{_e(sort)}'>"
        "<button type=submit>Apply filters</button>"
        "</form></details>"
    )


def _why_cell(analysis: str | None, rejected: bool) -> str:
    """Color-coded 'why' — red disqualifiers for rejects, muted reason otherwise."""
    if not analysis:
        return ""
    try:
        a = json.loads(analysis) or {}
    except Exception:
        return ""
    dq = a.get("disqualifiers") or []
    if rejected and dq:
        return f"<span class=dq>{_e(' · '.join(dq))}</span>"
    return f"<span class=why>{_e(a.get('reason', ''))}</span>"


def _table(rows, fitcol, loved: set, show_why: bool = False) -> str:
    if not rows:
        return "<div class=empty>No jobs here. Run <code>jobhunt source</code> / <code>analyze</code>, or loosen filters.</div>"
    fit_h = "<th>Fit</th>" if fitcol else ""
    why_h = "<th>Why</th>" if show_why else ""
    head = (f"<table><thead><tr><th></th>{fit_h}<th>Score</th><th>Tier</th><th>Type</th>"
            f"<th>Company</th><th>Role</th><th>Location</th>{why_h}<th>Apply</th><th></th>"
            "</tr></thead><tbody>")
    body = []
    for i, r in enumerate(rows, 1):
        path = apply_path(classify_url(r["url"] or "", r["source"] or ""))
        loc = r["location"] or ("Remote" if r["remote"] else "—")
        fit_c = f"<td class=fit>{r[fitcol] if r[fitcol] is not None else '—'}</td>" if fitcol else ""
        ctype = r["company_type"]
        ct_cls = " staffing" if ctype == "staffing_proxy" else ""
        why_c = f"<td>{_why_cell(r['analysis'], rejected=not r['apply_ok'])}</td>" if show_why else ""
        comp = r["company"] or ""
        on = " on" if comp in loved else ""
        cn = " loved" if comp in loved else ""
        heart = (f"<span class=\"cname{cn}\">{_e(comp)}</span>"
                 f"<span class='love{on}' data-c=\"{_e(comp)}\" onclick='love(this)' "
                 f"title='favorite company'>&#9829;</span>")
        body.append(
            f"<tr><td class=num>{i}</td>{fit_c}"
            f"<td class=score>{r['score']}</td>"
            f"<td class=tier>{_TIER_LABEL.get(r['tier'], r['tier'] or '—')}</td>"
            f"<td class='ctype{ct_cls}'>{_TYPE_LABEL.get(ctype, '—')}</td>"
            f"<td class=company>{heart}</td>"
            f"<td class=role>{_e(r['title'])}</td>"
            f"<td class=loc>{_e(loc)}</td>{why_c}"
            f"<td><span class='pill {path}'>{path}</span></td>"
            f"<td><a href='{_e(r['url'])}' target=_blank rel=noopener>open ↗</a></td></tr>"
        )
    return head + "".join(body) + "</tbody></table>"


def _render(tier: str, min_score: int, fresh: bool, sort: str,
            preference: str = "", notice: str = "", view: str = "",
            min_fit: int = 50, page: int = 0) -> str:
    from .core.favorites import load_preference, loved_companies
    if not preference:
        preference = load_preference()
    loved = loved_companies()

    show_why = view in ("apply", "rejected", "call")
    if view == "call":
        q = "SELECT * FROM jobs WHERE analysis IS NOT NULL AND status != 'closed'"
        p: list = []
        if tier:
            q += " AND tier = ?"; p.append(tier)
        q += " ORDER BY analyzed_at DESC, afit DESC"
        fitcol = "afit"
    elif view == "apply":
        q = "SELECT * FROM jobs WHERE apply_ok = 1 AND afit >= ? AND status != 'closed'"
        p: list = [min_fit]
        if tier:
            q += " AND tier = ?"; p.append(tier)
        q += " ORDER BY afit DESC"
        fitcol = "afit"
    elif view == "rejected":
        q = "SELECT * FROM jobs WHERE analysis IS NOT NULL AND apply_ok = 0 AND status != 'closed'"
        p = []
        if tier:
            q += " AND tier = ?"; p.append(tier)
        q += " ORDER BY afit DESC"
        fitcol = "afit"
    else:
        q = "SELECT * FROM jobs WHERE score >= ? AND status != 'closed'"
        p = [min_score]
        if tier:
            q += " AND tier = ?"; p.append(tier)
        if fresh:
            q += " AND fetched_at >= datetime('now','-24 hours')"
        if sort == "fit":
            q += " ORDER BY fit IS NULL, fit DESC, score DESC"; fitcol = "fit"
        else:
            q += " ORDER BY score DESC, fetched_at DESC"; fitcol = None

    q += f" LIMIT {_PAGE + 1} OFFSET {page * _PAGE}"
    with db.connect() as conn:
        rows = conn.execute(q, p).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        fresh_n = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE fetched_at >= datetime('now','-24 hours')"
        ).fetchone()[0]
    has_next = len(rows) > _PAGE
    rows = rows[:_PAGE]
    base = {"view": view, "tier": tier, "min_score": min_score,
            "fresh": 1 if fresh else 0, "sort": sort, "min_fit": min_fit}
    notice_html = f"<div class=result>{notice}</div>" if notice else ""
    return _page(
        _header(total, fresh_n)
        + notice_html
        + _check_form()
        + _filters(tier, min_score, fresh, sort, view, min_fit)
        + "<div class=panel>" + _table(rows, fitcol, loved, show_why)
        + _pager(page, has_next, base) + "</div>"
    )


@app.get("/", response_class=HTMLResponse)
def index(tier: str = "", min_score: int = 40, fresh: int = 0, sort: str = "",
          view: str = "", min_fit: int = 50, page: int = 0):
    return _render(tier, min_score, bool(fresh), sort, view=view, min_fit=min_fit,
                   page=max(0, page))


@app.post("/resume", response_class=HTMLResponse)
async def resume_route(resume: str = Form(""), file: UploadFile = File(None)):
    from .core.config import resume_from_upload, save_resume
    if file is not None and file.filename:
        save_resume(resume_from_upload(file.filename, await file.read()))
    else:
        save_resume(resume)
    return _render("", 40, False, "", notice=(
        "Resume saved. Run <code>jobhunt analyze --force</code> to re-screen "
        "every job against it."))


@app.post("/prompt", response_class=HTMLResponse)
def prompt_route(prompt: str = Form("")):
    from .core.config import save_prompt
    save_prompt(prompt)
    return _render("", 40, False, "", notice=(
        "Prompt saved. Run <code>jobhunt analyze --force</code> to use it."))


@app.post("/love")
def love_route(company: str = Form(...)):
    from .core.favorites import toggle_loved
    return JSONResponse({"loved": toggle_loved(company)})


@app.post("/add", response_class=HTMLResponse)
def add_route(url: str = Form(...)):
    from .cli import _fetch_favorite, _ingest
    from .core.favorites import add_favorite, parse_company_url

    entry = parse_company_url(url)
    if not entry:
        return _render("", 40, False, "", notice=(
            "<span class=nofit>Couldn’t detect an ATS</span> in that link — use a "
            "Greenhouse / Lever / Ashby / Workday careers URL."))
    label = entry.get("token") or entry.get("tenant")
    state = add_favorite(entry)
    raw = _fetch_favorite(entry)
    added = len(_ingest(raw, settings())) if raw else 0
    notice = (f"<b>{_e(entry['vendor'])}/{_e(label)}</b> {state} · "
              f"fetched {len(raw)} postings, <b>{added}</b> matched your filters.")
    return _render("", 40, False, "", notice=notice)


@app.post("/rank", response_class=HTMLResponse)
def rank_route(preference: str = Form(...), tier: str = Form(""),
               min_score: int = Form(40)):
    from .core.favorites import save_preference
    from .match.llm import claude_available, rank

    save_preference(preference)
    if claude_available():
        q = "SELECT id, title, company, location FROM jobs WHERE score >= ?"
        p: list = [min_score]
        if tier:
            q += " AND tier = ?"; p.append(tier)
        q += " ORDER BY score DESC LIMIT 60"
        with db.connect() as conn:
            jobs = [dict(r) for r in conn.execute(q, p).fetchall()]
        fits = rank(preference, jobs)
        if fits:
            with db.connect() as conn:
                for jid, f in fits.items():
                    conn.execute("UPDATE jobs SET fit = ? WHERE id = ?", [f, jid])
    return _render(tier, min_score, False, sort="fit", preference=preference)


@app.post("/check", response_class=HTMLResponse)
def check(url: str = Form(...), save: str = Form("")):
    from .apply.inspect import inspect

    cfg = settings()
    try:
        info = inspect(url)
    except Exception as e:
        banner = f"<div class=result><div class=nofit>Couldn’t fetch that URL</div><div class=kv>{_e(e)}</div></div>"
        return _page(_header() + _check_form(url) + banner)

    passes, remote = location_ok(info, cfg)
    info["remote"] = 1 if remote else 0
    score, tier = score_job(info, cfg)
    path = apply_path(classify_url(info["final_url"], info.get("source", "")))
    min_score = cfg["sourcing"]["min_score"]
    fits = passes and score >= min_score

    saved = ""
    if save and fits:
        info["score"], info["tier"] = score, tier
        with db.connect() as conn:
            state = db.upsert_job(conn, info)
        saved = f" · <span class=kv>saved ({state})</span>"

    verdict = ("<span class=fit-c>✅ fits your criteria</span>" if fits
               else "<span class=nofit>✕ doesn’t fit</span>")
    note = ("<div class=kv>no JSON-LD on page — title-only read; open the link to confirm.</div>"
            if info.get("_no_jsonld") else "")
    banner = (
        "<div class=result>"
        f"<div class=t>{_e(info['title']) or 'Untitled'}</div>"
        f"<div class=kv><b>{_e(info['company']) or '?'}</b> · {_e(info['location']) or 'location ?'}"
        f" · US-ok {passes} · remote {bool(remote)}</div>"
        f"<div class=kv>apply via <b>{path}</b>"
        f"{'  (auto-fillable ATS)' if path == 'auto' else ''} · "
        f"score <b>{score}</b> {_TIER_LABEL.get(tier, tier or '—')}</div>"
        f"<div class=kv><a href='{_e(info['final_url'])}' target=_blank rel=noopener>{_e(info['final_url'])}</a></div>"
        f"{note}<div class=verdict>{verdict}{saved}</div></div>"
    )
    return _page(_header() + _check_form() + banner)


def main():
    import uvicorn
    print("jobhunt UI  →  http://127.0.0.1:8765")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
