from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from .config import DATA_DIR

DB_PATH = DATA_DIR / "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    source_id    TEXT NOT NULL,
    company      TEXT,
    title        TEXT,
    location     TEXT,
    remote       INTEGER DEFAULT 0,
    url          TEXT,
    description  TEXT,
    posted_at    TEXT,
    fetched_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    score        INTEGER DEFAULT 0,
    tier         TEXT,
    fit          INTEGER,               -- 0-100 semantic fit vs your preference (LLM)
    company_type TEXT,                  -- yc_early|funded_startup|unicorn|public_corp|staffing_proxy
    afit         INTEGER,               -- deep-read fit 0-100 (JD + your profile)
    apply_ok     INTEGER,               -- 1 if it clears your hard gates
    analysis     TEXT,                  -- JSON: requirements, sponsorship, reason
    analyzed_at  TEXT,                  -- when the deep-read last ran
    analysis_run INTEGER,               -- which analyze run/"call" produced this
    fetch_run    INTEGER,               -- which fetch batch first discovered this
    checked_at   TEXT,                  -- last liveness probe (NULL = never checked)
    pinned       INTEGER DEFAULT 0,     -- manually added to the apply list
    status       TEXT DEFAULT 'new',    -- new | drafted | applied | skipped
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id       INTEGER NOT NULL REFERENCES jobs(id),
    status       TEXT DEFAULT 'draft',  -- draft | submitted | failed
    cover_letter TEXT,
    answers      TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    submitted_at TEXT,
    notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score  ON jobs(score);
"""


@contextmanager
def connect():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        for col in ("fit INTEGER", "company_type TEXT", "afit INTEGER",
                    "apply_ok INTEGER", "analysis TEXT", "analyzed_at TEXT",
                    "analysis_run INTEGER", "fetch_run INTEGER", "checked_at TEXT",
                    "pinned INTEGER DEFAULT 0"):                # migrate older DBs
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
        yield conn
        conn.commit()
    finally:
        conn.close()


def next_fetch_run(conn) -> int:
    """The batch number for a new fetch: one past the highest stamped so far."""
    return (conn.execute("SELECT COALESCE(MAX(fetch_run), 0) FROM jobs").fetchone()[0] or 0) + 1


def upsert_job(conn, job: dict, fetch_run: int | None = None) -> str:
    """Insert a job, ignoring duplicates by (source, source_id).

    Returns 'inserted' for a new row, 'skipped' if it already existed.
    """
    cur = conn.execute(
        """INSERT OR IGNORE INTO jobs
           (source, source_id, company, title, location, remote, url,
            description, posted_at, score, tier, status, fetch_run)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job["source"], job["source_id"], job.get("company"), job.get("title"),
            job.get("location"), int(job.get("remote", 0)), job.get("url"),
            job.get("description"), job.get("posted_at"), int(job.get("score", 0)),
            job.get("tier"), job.get("status", "new"), fetch_run,
        ),
    )
    return "inserted" if cur.rowcount else "skipped"
