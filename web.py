from __future__ import annotations

import html
import json

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

from .apply.router import apply_path, classify_url
from .core import db
from .core.config import settings
from .match.score import location_ok, score_job

app = FastAPI()

CSS = """
:root{
  --bg:#0b0d10; --panel:#12151a; --panel2:#171b22;
  --line:#1c212a; --line2:#272e39;
  --text:#e7e9ee; --muted:#7b8494; --faint:#4b5461;
  --accent:#8ab4ff; --green:#54c07a; --amber:#d6a44a; --violet:#b28cff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
  font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:44px 28px 90px}
header{display:flex;align-items:center;justify-content:space-between;
  padding-bottom:18px;margin-bottom:26px;border-bottom:1px solid var(--line)}
.brand{font-size:22px;font-weight:680;letter-spacing:-.02em;display:flex;align-items:center;gap:9px}
.brand .dot{width:7px;height:7px;border-radius:50%;background:var(--green);
  box-shadow:0 0 0 3px rgba(84,192,122,.14)}
.meta{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.meta b{color:var(--text);font-weight:600}
a{color:var(--accent);text-decoration:none}
a:hover{opacity:.8}

.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:18px 20px;margin-bottom:22px}
.panel h2{font-size:11px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--muted);margin:0 0 13px;font-weight:600}

form.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
form.col{display:flex;flex-direction:column;gap:11px;align-items:flex-start}
input,select,textarea{background:var(--panel2);color:var(--text);
  border:1px solid var(--line2);border-radius:10px;padding:10px 12px;font-size:14px;
  outline:none;font-family:inherit}
input::placeholder,textarea::placeholder{color:var(--faint)}
input:focus,select:focus,textarea:focus{border-color:var(--accent)}
input.url{flex:1;min-width:340px}
textarea{width:100%;resize:vertical;line-height:1.5}
label.chk{color:var(--muted);display:flex;gap:7px;align-items:center;font-size:13px;user-select:none}
button{background:var(--accent);color:#08101f;border:none;border-radius:10px;
  padding:10px 17px;font-size:14px;font-weight:640;cursor:pointer}
button:hover{filter:brightness(1.07)}
.hint{color:var(--faint);font-size:12px}

.result{border:1px solid var(--line2);border-radius:12px;padding:16px 18px;
  background:var(--panel2);margin-top:15px}
.result .t{font-size:16px;font-weight:620;margin:0 0 6px}
.kv{color:var(--muted);font-size:13px;margin:3px 0}
.kv b{color:var(--text);font-weight:560}
.verdict{margin-top:10px;font-size:14px}
.fit-c{color:var(--accent)}
.nofit{color:#ff7a7a;font-weight:700}

table{width:100%;border-collapse:collapse}
th{text-align:left;color:var(--muted);font-size:11px;text-transform:uppercase;
  letter-spacing:.06em;font-weight:600;padding:0 12px 11px}
td{padding:11px 10px;border-top:1px solid var(--line);vertical-align:middle}
tr:hover td{background:var(--panel2)}
td.num{color:var(--faint);width:30px;font-variant-numeric:tabular-nums}
.score{font-variant-numeric:tabular-nums;font-weight:700;width:44px}
.fit{font-variant-numeric:tabular-nums;font-weight:700;color:var(--accent);width:44px}
.tier{font-size:12px;color:var(--violet);white-space:nowrap}
.ctype{font-size:12px;color:var(--muted);white-space:nowrap}
.ctype.staffing{color:var(--amber)}
.company{font-weight:600;white-space:nowrap}
.cname.loved{color:var(--accent)}
.love{margin-left:9px;cursor:pointer;color:var(--faint);font-size:13px;opacity:0;
  transition:opacity .12s, color .12s, transform .1s;user-select:none;vertical-align:middle}
tr:hover .love{opacity:.55}
.love:hover{color:#ff5a7a}
.love:active{transform:scale(1.3)}
.love.on{opacity:1;color:#ff5a7a}
.role{color:var(--text);max-width:300px}
.loc{color:var(--muted);font-size:13px;max-width:180px}
td a{white-space:nowrap}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;
  font-weight:600;border:1px solid transparent}
.pill.auto{color:var(--green);background:rgba(84,192,122,.10);border-color:rgba(84,192,122,.28)}
.pill.confirm{color:var(--amber);background:rgba(214,164,74,.10);border-color:rgba(214,164,74,.28)}
.pill.manual{color:var(--muted);background:rgba(123,132,148,.08);border-color:var(--line2)}
.empty{color:var(--muted);padding:36px 0;text-align:center}

.toolbar{position:fixed;top:20px;right:24px;z-index:20;display:flex;gap:10px;align-items:center}
.tool-btn{background:var(--panel);border:1px solid var(--line2);border-radius:999px;
  padding:9px 15px;font-size:13px;font-weight:600;color:var(--text);cursor:pointer;
  display:flex;align-items:center;gap:6px;transition:border-color .15s, background .15s}
.tool-btn:hover{border-color:var(--accent);background:var(--panel2)}
.heart-btn{width:42px;height:42px;border-radius:50%;background:var(--panel);
  border:1px solid var(--line2);display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:#ff5a7a;font-size:18px;transition:border-color .15s, background .15s}
.heart-btn:hover{border-color:#ff5a7a;background:var(--panel2)}
.overlay{position:fixed;inset:0;background:rgba(4,6,10,.66);backdrop-filter:blur(2px);
  display:none;align-items:flex-start;justify-content:center;z-index:30;padding-top:13vh}
#favtoggle:checked ~ .fav-ov{display:flex}
#preftoggle:checked ~ .pref-ov{display:flex}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--panel2);border:1px solid var(--line2);border-radius:999px;
  padding:6px 8px 6px 13px;font-size:13px;font-weight:600;display:flex;align-items:center;gap:9px}
.chip .love{opacity:1;margin:0;color:#ff5a7a;font-size:14px}
.modal{background:var(--panel);border:1px solid var(--line2);border-radius:16px;
  padding:22px 24px;width:min(560px,92vw);position:relative;
  box-shadow:0 24px 60px rgba(0,0,0,.5)}
.modal-close{position:absolute;top:11px;right:16px;cursor:pointer;color:var(--muted);
  font-size:22px;line-height:1;text-decoration:none}
.modal-close:hover{color:var(--text)}
.modal-h{font-size:11px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--muted);margin:0 0 14px;font-weight:600}
"""

_TIER_LABEL = {"voice_speech": "voice", "ai_ml": "ai/ml", "swe_backend": "swe"}
_TYPE_LABEL = {"yc_early": "YC/early", "funded_startup": "startup", "unicorn": "unicorn",
               "public_corp": "public", "staffing_proxy": "staffing", "unknown": "—"}


def _toolbar() -> str:
    return (
        "<input type=checkbox id=favtoggle hidden>"
        "<input type=checkbox id=preftoggle hidden>"
        "<div class=toolbar>"
        "<label for=preftoggle class=tool-btn>&#10022;&nbsp; Preference</label>"
        "<label for=favtoggle class=heart-btn title='Loved companies'>&#9829;</label>"
        "</div>"
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
            f"<title>jobhunt</title><style>{CSS}</style></head>"
            f"<body>{_toolbar()}{_fav_modal()}{_pref_modal()}"
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
        meta = f"<span class=meta>{' &nbsp;·&nbsp; '.join(bits)}</span>"
    return f"<header><div class=brand>jobhunt<span class=dot></span></div>{meta}</header>"


def _check_form(url: str = "") -> str:
    return (
        "<div class=panel><h2>Check a job link</h2>"
        "<form class=row method=post action='/check'>"
        f"<input class=url type=text name=url placeholder='Paste a job posting URL…' value='{_e(url)}'>"
        "<label class=chk><input type=checkbox name=save value=1> save if it fits</label>"
        "<button type=submit>Check</button>"
        "</form></div>"
    )


def _filters(tier: str, min_score: int, fresh: bool, sort: str, applyonly: bool) -> str:
    opts = [("", "all tiers"), ("voice_speech", "voice"),
            ("ai_ml", "ai/ml"), ("swe_backend", "swe")]
    sel = "".join(
        f"<option value='{v}'{' selected' if v == tier else ''}>{lbl}</option>"
        for v, lbl in opts)
    fchk = " checked" if fresh else ""
    achk = " checked" if applyonly else ""
    return (
        "<div class=panel><h2>Jobs</h2>"
        "<form class=row method=get action='/'>"
        f"<select name=tier>{sel}</select>"
        f"<input type=number name=min_score value={min_score} style='width:110px' title='min score'>"
        f"<label class=chk><input type=checkbox name=fresh value=1{fchk}> last 24h only</label>"
        f"<label class=chk><input type=checkbox name=apply value=1{achk}> apply-ready only</label>"
        f"<input type=hidden name=sort value='{_e(sort)}'>"
        "<button type=submit>Filter</button>"
        "</form></div>"
    )


def _table(rows, fitcol, loved: set) -> str:
    if not rows:
        return "<div class=empty>No jobs match. Run <code>jobhunt source</code> first, or loosen filters.</div>"
    fit_h = "<th>Fit</th>" if fitcol else ""
    head = (f"<table><thead><tr><th></th>{fit_h}<th>Score</th><th>Tier</th><th>Type</th>"
            "<th>Company</th><th>Role</th><th>Location</th><th>Apply</th><th></th></tr></thead><tbody>")
    body = []
    for i, r in enumerate(rows, 1):
        path = apply_path(classify_url(r["url"] or "", r["source"] or ""))
        loc = r["location"] or ("Remote" if r["remote"] else "—")
        fit_c = ""
        if fitcol:
            fv = r[fitcol]
            fit_c = f"<td class=fit>{fv if fv is not None else '—'}</td>"
        ctype = r["company_type"]
        ct_cls = " staffing" if ctype == "staffing_proxy" else ""
        reason = ""
        try:
            if r["analysis"]:
                reason = (json.loads(r["analysis"]) or {}).get("reason", "")
        except Exception:
            pass
        tip = f' title="{_e(reason)}"' if reason else ""
        comp = r["company"] or ""
        on = " on" if comp in loved else ""
        cn = " loved" if comp in loved else ""
        heart = (f"<span class=\"cname{cn}\">{_e(comp)}</span>"
                 f"<span class='love{on}' data-c=\"{_e(comp)}\" onclick='love(this)' "
                 f"title='favorite company'>&#9829;</span>")
        body.append(
            f"<tr{tip}><td class=num>{i}</td>{fit_c}"
            f"<td class=score>{r['score']}</td>"
            f"<td class=tier>{_TIER_LABEL.get(r['tier'], r['tier'] or '—')}</td>"
            f"<td class='ctype{ct_cls}'>{_TYPE_LABEL.get(ctype, '—')}</td>"
            f"<td class=company>{heart}</td>"
            f"<td class=role>{_e(r['title'])}</td>"
            f"<td class=loc>{_e(loc)}</td>"
            f"<td><span class='pill {path}'>{path}</span></td>"
            f"<td><a href='{_e(r['url'])}' target=_blank rel=noopener>open ↗</a></td></tr>"
        )
    return head + "".join(body) + "</tbody></table>"


def _render(tier: str, min_score: int, fresh: bool, sort: str,
            preference: str = "", notice: str = "", applyonly: bool = False) -> str:
    from .core.favorites import load_preference, loved_companies
    if not preference:
        preference = load_preference()
    loved = loved_companies()

    if applyonly:
        q = "SELECT * FROM jobs WHERE apply_ok = 1"
        p: list = []
        if tier:
            q += " AND tier = ?"; p.append(tier)
        q += " ORDER BY afit DESC LIMIT 200"
        fitcol = "afit"
    else:
        q = "SELECT * FROM jobs WHERE score >= ?"
        p = [min_score]
        if tier:
            q += " AND tier = ?"; p.append(tier)
        if fresh:
            q += " AND fetched_at >= datetime('now','-24 hours')"
        if sort == "fit":
            q += " ORDER BY fit IS NULL, fit DESC, score DESC"; fitcol = "fit"
        else:
            q += " ORDER BY score DESC, fetched_at DESC"; fitcol = None
        q += " LIMIT 200"

    with db.connect() as conn:
        rows = conn.execute(q, p).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        fresh_n = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE fetched_at >= datetime('now','-24 hours')"
        ).fetchone()[0]
    notice_html = f"<div class=result>{notice}</div>" if notice else ""
    return _page(
        _header(total, fresh_n)
        + notice_html
        + _check_form()
        + _filters(tier, min_score, fresh, sort, applyonly)
        + "<div class=panel>" + _table(rows, fitcol, loved) + "</div>"
    )


@app.get("/", response_class=HTMLResponse)
def index(tier: str = "", min_score: int = 40, fresh: int = 0, sort: str = "",
          apply: int = 0):
    return _render(tier, min_score, bool(fresh), sort, applyonly=bool(apply))


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
