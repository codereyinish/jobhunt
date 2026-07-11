from __future__ import annotations

import argparse
import subprocess

from .core import db
from .core.config import companies, settings
from .match.score import location_ok, score_job
from .sourcing import (adzuna, ashby, greenhouse, jobspy_src, lever, remoteok,
                       workday)


def _notify(title: str, message: str):
    """Best-effort macOS desktop notification."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification {message!r} with title {title!r}'],
            check=False, capture_output=True,
        )
    except Exception:
        pass


def _ingest(raw: list[dict], cfg: dict) -> list[dict]:
    """Score, location-filter, and store raw postings. Returns rows that were
    newly inserted (i.e. seen for the first time)."""
    min_score = cfg["sourcing"]["min_score"]
    maxc = cfg["sourcing"]["max_description_chars"]
    require_us = cfg["locations"].get("require_us", True)

    new_rows: list[dict] = []
    with db.connect() as conn:
        for job in raw:
            passes, remote = location_ok(job, cfg)
            if require_us and not passes:
                continue
            job["remote"] = 1 if remote else 0
            score, tier = score_job(job, cfg)
            if score < min_score:
                continue
            job["score"], job["tier"] = score, tier
            if job.get("description"):
                job["description"] = job["description"][:maxc]
            if db.upsert_job(conn, job) == "inserted":
                new_rows.append(job)
    return new_rows


def _fetch_all(cfg: dict, comp: dict, verbose: bool = True) -> list[dict]:
    raw: list[dict] = []

    def log(msg):
        if verbose:
            print(msg)

    ro = remoteok.fetch()
    log(f"  remoteok               : {len(ro)}")
    raw += ro
    for tok in comp.get("greenhouse", []) or []:
        js = greenhouse.fetch(tok)
        if js:
            log(f"  greenhouse/{tok:<12}: {len(js)}")
        raw += js
    for tok in comp.get("lever", []) or []:
        js = lever.fetch(tok)
        if js:
            log(f"  lever/{tok:<17}: {len(js)}")
        raw += js
    for tok in comp.get("ashby", []) or []:
        js = ashby.fetch(tok)
        if js:
            log(f"  ashby/{tok:<17}: {len(js)}")
        raw += js
    for wd in comp.get("workday", []) or []:
        js = workday.fetch(wd)
        if js:
            log(f"  workday/{str(wd.get('tenant', '')):<15}: {len(js)}")
        raw += js
    if (cfg.get("adzuna") or {}).get("app_id"):
        al = adzuna.fetch()
        log(f"  adzuna                 : {len(al)}")
        raw += al
    if (cfg.get("jobspy") or {}).get("enabled"):
        log("  jobspy (scraping boards, may take a minute)…")
        jl = jobspy_src.fetch()
        log(f"  jobspy                 : {len(jl)}")
        raw += jl
    return raw


def cmd_source(args):
    cfg, comp = settings(), companies()
    print("Fetching sources…")
    raw = _fetch_all(cfg, comp)
    print(f"Total raw postings: {len(raw)}")
    new_rows = _ingest(raw, cfg)
    print(f"\n{len(new_rows)} NEW jobs added (rest already tracked).")
    for j in sorted(new_rows, key=lambda x: -x["score"])[:15]:
        print(f"  +{j['score']:>3} {(j['tier'] or '-'):<12} "
              f"{(j['company'] or '')[:22]:<22} {(j['title'] or '')[:44]}")
    print("\nBrowse:  jobhunt list       New only:  jobhunt list --new-hours 24")


def cmd_poll(args):
    """Scheduler entrypoint: fetch quietly, notify on fresh high-score jobs."""
    cfg, comp = settings(), companies()
    raw = _fetch_all(cfg, comp, verbose=False)
    new_rows = _ingest(raw, cfg)
    threshold = cfg["sourcing"].get("notify_min_score", 60)
    hot = [j for j in new_rows if j["score"] >= threshold]
    print(f"[poll] {len(new_rows)} new, {len(hot)} above notify threshold "
          f"({threshold}).")
    if hot:
        top = max(hot, key=lambda x: x["score"])
        _notify(
            f"{len(hot)} new job match(es)",
            f"{top['title']} @ {top['company']} (+{top['score']})",
        )


def cmd_list(args):
    q = "SELECT * FROM jobs WHERE score >= ?"
    p: list = [args.min_score]
    if args.tier:
        q += " AND tier = ?"; p.append(args.tier)
    if args.status:
        q += " AND status = ?"; p.append(args.status)
    if args.new_hours:
        q += " AND fetched_at >= datetime('now', ?)"; p.append(f"-{args.new_hours} hours")
    order = "fetched_at DESC, score DESC" if args.new_hours else "score DESC, fetched_at DESC"
    q += f" ORDER BY {order} LIMIT ?"; p.append(args.limit)

    with db.connect() as conn:
        rows = conn.execute(q, p).fetchall()

    for r in rows:
        rem = "REMOTE" if r["remote"] else "      "
        src = (r["source"] or "").split(":")[0][:9]
        print(f"[{r['id']:>4}] {r['score']:>3} {(r['tier'] or '-'):<12} {rem} "
              f"{src:<9} {(r['company'] or '')[:18]:<18} "
              f"{(r['title'] or '')[:42]:<42} {(r['location'] or '')[:20]}")
    label = f" (posted/seen in last {args.new_hours}h)" if args.new_hours else ""
    print(f"\n{len(rows)} jobs{label}. Detail:  jobhunt show <id>")


def cmd_show(args):
    with db.connect() as conn:
        r = conn.execute("SELECT * FROM jobs WHERE id = ?", [args.id]).fetchone()
    if not r:
        print("not found")
        return
    print(f"{r['title']}  @  {r['company']}")
    print(f"score {r['score']} | tier {r['tier']} | {r['location']} | "
          f"remote={r['remote']} | status={r['status']}")
    print(f"source {r['source']} | first seen {r['fetched_at']} | posted {r['posted_at']}")
    print(r["url"])
    print("-" * 72)
    print((r["description"] or "")[:3500])


def _fetch_favorite(entry: dict) -> list[dict]:
    from .sourcing import ashby, greenhouse, lever, workday
    v = entry["vendor"]
    if v == "greenhouse":
        return greenhouse.fetch(entry["token"])
    if v == "lever":
        return lever.fetch(entry["token"])
    if v == "ashby":
        return ashby.fetch(entry["token"])
    if v == "workday":
        return workday.fetch(entry)
    return []


def cmd_add(args):
    """Add a company to your favorites (ATS search list) from its careers URL."""
    from .core.favorites import add_favorite, parse_company_url

    entry = parse_company_url(args.url)
    if not entry:
        print("Couldn't detect an ATS from that URL.\n"
              "Supported: Greenhouse, Lever, Ashby, Workday careers links.")
        return
    label = entry.get("token") or entry.get("tenant")
    state = add_favorite(entry)
    print(f"{entry['vendor']}/{label}: {state} to favorites.")

    raw = _fetch_favorite(entry)
    if not raw:
        print("  (no public postings found — token may be wrong or board is empty.)")
        return
    new = _ingest(raw, settings())
    print(f"  fetched {len(raw)} postings, {len(new)} match your filters and were added.")


def cmd_analyze(args):
    """Deep-read the shortlist's descriptions vs your profile, via claude."""
    import json

    from .match.analyze import analyze
    from .match.llm import claude_available

    if not claude_available():
        print("The `claude` CLI isn't on PATH — install Claude Code to use analyze.")
        return

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, title, company, location, description FROM jobs "
            "WHERE score >= ? AND afit IS NULL ORDER BY score DESC LIMIT ?",
            [args.min_score, args.limit],
        ).fetchall()
    jobs = [dict(r) for r in rows]
    if not jobs:
        print("Nothing new to analyze (shortlist already screened, or run `source`).")
        return

    results: dict[int, dict] = {}
    for i in range(0, len(jobs), args.batch):
        chunk = jobs[i:i + args.batch]
        print(f"  reading jobs {i + 1}-{i + len(chunk)} of {len(jobs)}…")
        results.update(analyze(chunk))

    kept = 0
    with db.connect() as conn:
        for jid, a in results.items():
            fit = int(a.get("fit", 0) or 0)
            ok = 1 if (a.get("works_for_me") and fit >= args.threshold) else 0
            kept += ok
            conn.execute(
                "UPDATE jobs SET company_type=?, afit=?, apply_ok=?, analysis=? WHERE id=?",
                [a.get("company_type", "unknown"), fit, ok, json.dumps(a), jid])
        top = conn.execute(
            "SELECT company, title, company_type, afit, analysis FROM jobs "
            "WHERE apply_ok = 1 ORDER BY afit DESC LIMIT 25").fetchall()

    print(f"\nAnalyzed {len(results)}. {kept} cleared your hard gates. Apply list:\n")
    for r in top:
        reason = ""
        try:
            reason = (json.loads(r["analysis"]) or {}).get("reason", "")
        except Exception:
            pass
        print(f"  {r['afit']:>3} {(r['company_type'] or '?'):<15} "
              f"{(r['company'] or '')[:18]:<18} {(r['title'] or '')[:34]:<34} {reason[:40]}")


def cmd_rank(args):
    """Rank stored jobs against a plain-English preference via the claude CLI."""
    from .match.llm import claude_available, rank

    if not claude_available():
        print("The `claude` CLI isn't on PATH — install Claude Code to use rank.")
        return

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, title, company, location FROM jobs WHERE score >= ? "
            "ORDER BY score DESC LIMIT ?", [args.min_score, args.limit],
        ).fetchall()
    jobs = [dict(r) for r in rows]
    if not jobs:
        print("No jobs to rank — run `source` first.")
        return

    print(f"Ranking {len(jobs)} jobs against your preference (claude)…")
    fits = rank(args.preference, jobs)
    if not fits:
        print("No scores returned. Try rephrasing the preference.")
        return
    with db.connect() as conn:
        for jid, f in fits.items():
            conn.execute("UPDATE jobs SET fit = ? WHERE id = ?", [f, jid])
        top = conn.execute(
            "SELECT company, title, fit FROM jobs WHERE fit IS NOT NULL "
            "ORDER BY fit DESC LIMIT 25").fetchall()
    print(f"Scored {len(fits)} jobs. Top matches:\n")
    for r in top:
        print(f"  fit {r['fit']:>3}  {(r['company'] or '')[:20]:<20} {(r['title'] or '')[:46]}")


def cmd_rescore(args):
    """Re-apply the current filters/scoring to everything already stored, with
    no re-fetching. Run this after editing settings.yaml to see the effect."""
    cfg = settings()
    min_score = cfg["sourcing"]["min_score"]
    updated = removed = 0
    with db.connect() as conn:
        for r in conn.execute("SELECT * FROM jobs").fetchall():
            job = {"title": r["title"], "description": r["description"],
                   "location": r["location"], "remote": r["remote"]}
            passes, _ = location_ok(job, cfg)
            score, tier = score_job(job, cfg)
            if not passes or score < min_score:
                conn.execute("DELETE FROM jobs WHERE id = ?", [r["id"]])
                removed += 1
            else:
                conn.execute("UPDATE jobs SET score = ?, tier = ? WHERE id = ?",
                             [score, tier, r["id"]])
                updated += 1
    print(f"Rescored {updated} kept, {removed} removed under current filters.")


def cmd_check(args):
    """Paste a job URL -> extract it, score it against your tiers, and resolve
    the real ATS apply path."""
    from .apply.inspect import inspect
    from .apply.router import apply_path, classify_url

    cfg = settings()
    print("Fetching…")
    try:
        info = inspect(args.url)
    except Exception as e:
        print(f"Could not fetch/parse that URL: {e}")
        return

    passes, remote = location_ok(info, cfg)
    info["remote"] = 1 if remote else 0
    score, tier = score_job(info, cfg)
    kind = classify_url(info["final_url"], info.get("source", ""))
    path = apply_path(kind)
    min_score = cfg["sourcing"]["min_score"]
    fits = passes and score >= min_score

    print(f"\n  Title      : {info['title'] or '(couldn’t read — JS-only page?)'}")
    print(f"  Company    : {info['company'] or '?'}")
    print(f"  Location   : {info['location'] or '?'}  (US-ok: {passes}, remote: {bool(remote)})")
    print(f"  Apply via  : {kind}  ->  {path}"
          f"{'   [auto-fillable ATS]' if path == 'auto' else ''}")
    print(f"  Final URL  : {info['final_url']}")
    print(f"  Score/tier : {score}  {tier or '-'}  (min {min_score})")
    if info.get("_no_jsonld"):
        print("  note       : no JSON-LD on page — score is title-only; "
              "open the URL to confirm.")
    print(f"\n  => {'✅ FITS your criteria' if fits else '❌ does not fit'} "
          f"({'above' if score >= min_score else 'below'} min_score, "
          f"{'US' if passes else 'non-US'})")

    if args.save and fits:
        info["score"], info["tier"] = score, tier
        with db.connect() as conn:
            state = db.upsert_job(conn, info)
        print(f"  saved to DB ({state}).")
    elif args.save:
        print("  not saved (doesn’t fit; use nothing to force, or fix filters).")


def cmd_classify(args):
    from collections import Counter

    from .apply.router import AUTOFILLABLE, apply_path, classify_url

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT company, title, url, source, score FROM jobs "
            "WHERE score >= ? ORDER BY score DESC", [args.min_score],
        ).fetchall()

    kinds, paths = Counter(), Counter()
    for r in rows:
        k = classify_url(r["url"] or "", r["source"] or "")
        kinds[k] += 1
        paths[apply_path(k)] += 1

    total = len(rows)
    print(f"{total} jobs (score >= {args.min_score}) by apply destination:\n")
    for kind, n in kinds.most_common():
        star = "  <- auto-fill" if kind in AUTOFILLABLE else ""
        print(f"  {kind:<16} {n:>4}{star}")
    print("\nBy apply path:")
    for path, n in paths.most_common():
        pct = 100 * n // total if total else 0
        print(f"  {path:<10} {n:>4}  ({pct}%)")
    print(f"\n=> {paths['auto']} of {total} can be fully auto-applied "
          f"(land on a standardized ATS form).")


def main():
    ap = argparse.ArgumentParser(prog="jobhunt")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("source", help="fetch + score + store jobs (verbose)")
    s.set_defaults(fn=cmd_source)

    pl = sub.add_parser("poll", help="quiet fetch + desktop notify (for scheduler)")
    pl.set_defaults(fn=cmd_poll)

    l = sub.add_parser("list", help="list tracked jobs")
    l.add_argument("--min-score", type=int, default=30)
    l.add_argument("--tier", choices=["voice_speech", "ai_ml", "swe_backend"])
    l.add_argument("--status")
    l.add_argument("--new-hours", type=int, default=0,
                   help="only jobs first seen within the last N hours")
    l.add_argument("--limit", type=int, default=40)
    l.set_defaults(fn=cmd_list)

    sh = sub.add_parser("show", help="show one job's full detail")
    sh.add_argument("id", type=int)
    sh.set_defaults(fn=cmd_show)

    c = sub.add_parser("classify", help="check which jobs lead to an auto-applyable ATS")
    c.add_argument("--min-score", type=int, default=60)
    c.set_defaults(fn=cmd_classify)

    ck = sub.add_parser("check", help="paste a job URL -> fit + ATS apply path")
    ck.add_argument("url")
    ck.add_argument("--save", action="store_true", help="store it if it fits")
    ck.set_defaults(fn=cmd_check)

    rs = sub.add_parser("rescore", help="re-apply filters to stored jobs (after editing settings)")
    rs.set_defaults(fn=cmd_rescore)

    rk = sub.add_parser("rank", help="rank jobs by a plain-English preference (claude)")
    rk.add_argument("preference", help="what you want, in plain English")
    rk.add_argument("--min-score", type=int, default=40)
    rk.add_argument("--limit", type=int, default=60)
    rk.set_defaults(fn=cmd_rank)

    ad = sub.add_parser("add", help="add a company to favorites from its careers URL")
    ad.add_argument("url")
    ad.set_defaults(fn=cmd_add)

    an = sub.add_parser("analyze", help="deep-read shortlist JDs vs your profile (claude)")
    an.add_argument("--min-score", type=int, default=60)
    an.add_argument("--limit", type=int, default=40)
    an.add_argument("--batch", type=int, default=6)
    an.add_argument("--threshold", type=int, default=60, help="apply-list fit cutoff")
    an.set_defaults(fn=cmd_analyze)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
