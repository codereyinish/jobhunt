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

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
