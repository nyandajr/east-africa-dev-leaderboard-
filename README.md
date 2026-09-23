# East Africa Dev Ledger

A real, GitHub-verified developer leaderboard for East Africa, refreshed
every 5 days directly from GitHub's own GraphQL API — built after
[committers.top](https://committers.top) was found stale for weeks at a
time and, worse, ranking farmed commit history as real activity.

**[Live dashboard](https://nyandajr.github.io/east-africa-dev-leaderboard/)**

## Why this exists

committers.top ranked `ebrahimHakimuddin` #2 on Tanzania's leaderboard for a
repo whose own README claims it doesn't create real commits — it does:
~137,000 of them, messages literally reading "commit 5000," "commit 4999,"
all landing in the same second. Raw commit counts alone can't catch that,
and the scraper feeding the site had gone stale since 2026-09-02 with
nobody the wiser.

## How it works

**Phase A — discovery** (`src/discover.py`): cheap candidate shortlisting
per country via GitHub's Search API, sorted by followers — the same signal
committers.top itself leans on. Verified live counts as of 2026-09-23:
Tanzania 6,402 · Kenya 36,592 · Uganda 8,793 · Rwanda 6,554 · Burundi 553
GitHub users with a location set.

**Phase B — classification** (`src/classify.py`): samples each candidate's
own (non-fork) repos and labels their commit pattern as one of:

- `FARMED` — generic/sequential commit messages ("commit 5000") landing
  multiple-per-timestamp. Disqualifying, full stop.
- `IMPORTED_HISTORY` — real commits, but pushed all at once from history
  that predates the repo itself by a month or more (e.g. `Ajmalleonard`'s
  `opin` repo: 17k+ genuine commits from a 13-month-old local history).
- `AUTOMATED_PIPELINE` — very regular commit intervals with real,
  content-aware messages — legitimate cron-driven pipelines, the same
  pattern this portfolio's own trackers use. Counted at face value, same
  as organic — only confirmed farming is excluded.
- `ORGANIC` — normal human (or AI-assisted) development.

Every category is grounded in a real case found during this portfolio's
investigation of committers.top, not a theoretical taxonomy.

**Phase C — refresh** (`src/update_leaderboard.py`): pulls each tracked
user's real `contributionsCollection.contributionCalendar.totalContributions`
straight from GitHub's GraphQL API and writes `docs/data.json`, which the
dashboard renders client-side. Runs on the VM's own crontab every 5 days —
not GitHub Actions, same reasoning as every other tracker in this
portfolio (schedule triggers deliver a fraction of their configured
cadence for sub-hourly jobs; less of a concern at 5 days, but no reason to
introduce a second automation pattern for one repo).

## Data

- `docs/data.json` — current leaderboard snapshot, fetched by the dashboard.
- `data/history.csv` — append-only history of every refresh, for tracking
  movement over time.
