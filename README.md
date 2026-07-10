# jobhunt

A free, local, single-user job-search tool — a DIY alternative to the paid
"auto-apply" sites.

It pulls fresh, relevant jobs from company ATS boards (**Greenhouse, Lever,
Ashby, Workday**) and the big job boards (**Indeed / Google** via JobSpy),
filters and ranks them to your preferences, and tracks them in a local SQLite
database. No account, no subscription, no paid API. Planned AI steps (resume
tailoring, cover letters) run through the local `claude` CLI, so there's no
metered bill either.

## Why

Paid auto-apply services charge a monthly fee to do what is mostly public data
plus a browser script. This does the same thing locally, for free, and you can
read and extend every line.

## Architecture

One pass, top to bottom: **sources → filter → store → notify → browse/classify.**

```
        ┌──────────────────── SOURCES (find jobs) ────────────────────┐
BY COMPANY ─►  Greenhouse   Lever   Ashby   Workday    (public ATS endpoint per company)
(you list who)              sourcing/{greenhouse,lever,ashby,workday}.py

BY KEYWORD ─►  JobSpy → Indeed + Google     RemoteOK feed     Adzuna (optional, free key)
(you list role)  sourcing/jobspy_src.py      remoteok.py        adzuna.py
                                    │
                                    ▼
                        raw postings  (one merged, normalized list)
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
1. LOCATION FILTER          2. SCORE + TIER              3. DROP if
   US city/state/remote?       title-driven tiers            not US, or
   match/score.py              (edit to YOUR field)          score < min_score
   location_ok()               score_job()
                                    │
                                    ▼
                    4. STORE → SQLite   (core/db.py · data/jobs.db)
                       dedupe by (source, source_id); new rows stamped first_seen
                                    │
                                    ▼
                    5. NOTIFY (poll only) — new job & score ≥ notify_min → desktop ping
                                    │
                                    ▼
                    6. BROWSE / CLASSIFY   (cli.py)
                       list · show · classify → auto-fillable ATS?  (apply/router.py)
```

### The stages

1. **Fetch** — every source returns the same normalized dict (`source, source_id,
   company, title, location, url, description, …`). ATS sources ask *by company*
   (`ashby/Deepgram → 65 jobs`); keyword sources ask *by term × location*.
2. **Location filter** (`match/score.py → location_ok`) — keep US city/state +
   US-remote, drop ex-US.
3. **Score + tier** (`score_job`) — drop senior/PM/sales titles, require a role
   word, then assign a tier by title. Default tiers `voice_speech → ai_ml →
   swe_backend` are just an example — **edit them to your field** in
   `settings.yaml`. Anything under `min_score` is discarded.
4. **Store** (`core/db.py`) — upsert into SQLite, deduped by `(source, source_id)`
   so re-runs only add genuinely new jobs; each new row gets a `first_seen` stamp.
5. **Notify** (`poll` only) — a new job scoring ≥ `notify_min_score` fires a
   desktop notification.
6. **Browse / classify** — `list` (ranked), `show` (full JD), `classify` (which
   jobs land on an auto-fillable ATS form vs. custom sites).

### 24/7 loop

`scheduler/install.sh` installs a launchd agent that runs `poll` every 20 minutes —
stages 1–5 automatically, pinging you when a fresh high-score match lands.

### Codebase map

```
cli.py               commands: source · poll · list · show · classify · check
core/config.py       loads the YAML configs
core/db.py           SQLite schema + upsert/dedupe
sourcing/            one file per source (base.py = shared HTTP + HTML strip)
match/score.py       location filter + tiered scorer
apply/router.py      classify a job URL → auto / confirm / manual
apply/inspect.py     `check <url>`: fetch + score + resolve a pasted job link
config/*.yaml        settings (filters/tiers) · companies (ATS list) · profile (you)
scheduler/install.sh macOS 24/7 poller
```

## Quickstart

```bash
git clone https://github.com/codereyinish/jobhunt
cd jobhunt
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp config/profile.example.yaml config/profile.yaml   # then edit it

alias jh=".venv/bin/python -m jobhunt.cli"
jh source           # fetch + score + store
jh list             # ranked matches
jh list --new-hours 24
jh show 12          # full job detail
jh classify         # how many jobs are auto-applyable
jh check <job-url>  # paste any job link: does it fit? where do I apply? (--save to keep)
```

## Configure (all editable)

- `config/settings.yaml` — cities/states, keyword **tiers** (set these to your
  field), seniority/role filters, JobSpy search terms.
- `config/companies.yaml` — ATS tokens to scan: Greenhouse/Lever/Ashby names +
  Workday tenants. Invalid ones are skipped, so add freely.
- `config/profile.yaml` — you (for scoring and future auto-apply).

## Run it 24/7 (macOS)

```bash
bash scheduler/install.sh    # launchd: polls every 20 min, notifies on new matches
```

## Status

**Working:** discovery, filtering, ranking, freshness, notifications, apply-triage.
**Planned:** resume/cover-letter tailoring (`claude` CLI), auto-fill + submit on
ATS forms (Playwright), application tracking via email.

## Notes

A personal-use tool. ATS endpoints are public and employer-sanctioned; scraping
the big boards via JobSpy is subject to those sites' terms — use responsibly, at
low volume, and never automate account logins.

## License

MIT
