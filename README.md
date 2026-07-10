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

## How it works

```
DISCOVER   ATS endpoints (by company)  +  JobSpy / Indeed (by keyword)
FILTER     US location + role tiers (edit to your field) + drop senior/PM/etc
STORE      SQLite, deduped, freshness-tracked
NOTIFY     desktop ping on fresh, high-score matches
CLASSIFY   which jobs land on an auto-applyable ATS form
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
