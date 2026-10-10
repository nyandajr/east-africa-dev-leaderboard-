# East Africa Dev Ledger

A real, GitHub-verified developer leaderboard for East Africa, refreshed
every 5 days directly from GitHub's own GraphQL API — built after
[committers.top](https://committers.top) was found stale for weeks at a
time and, worse, ranking farmed commit history as real activity.

**[Live dashboard](https://nyandajr.github.io/east-africa-dev-leaderboard-/)**

## Why this exists

committers.top ranked `ebrahimHakimuddin` #2 on Tanzania's leaderboard for a
repo whose own README claims it doesn't create real commits — it does:
~137,000 of them, messages literally reading "commit 5000," "commit 4999,"
all landing in the same second. Raw commit counts alone can't catch that,
and the scraper feeding the site had gone stale since 2026-09-02 with
nobody the wiser.

## How it works

**Discovery** (`src/discover.py`): candidates per country come straight
from committers.top's own public `rank_only/<country>.json` feed — not
re-derived from GitHub's Search API. An earlier version shortlisted the
top 40 candidates per country by GitHub follower count, which turned out
to miss real, highly active developers badly: a live spot-check against
committers.top/tanzania_public found 9 developers with 1,500-4,000+
contributions each who all ranked beyond followers-rank 100 (one as deep
as rank 645), plus a 10th whose location field doesn't contain the
country's name at all, so no location-text search would ever surface
them. committers.top has already solved discovery at a scale (GH
Archive-based crawling) this project can't replicate every 5 days, so
this project now trusts their discovery and focuses its own effort on
the part that's actually its differentiator: classification.

**Classification** (`src/classify.py`): every candidate's own (non-fork)
repos get sampled and their commit pattern labeled as one of `FARMED`
(generic/sequential messages like "commit 5000" landing multiple-per-
timestamp — how `ebrahimHakimuddin`'s ~137k-commit repo was caught),
`IMPORTED_HISTORY` (real commits pushed all at once from history that
predates the repo itself), `AUTOMATED_PIPELINE` (regular intervals with
real, content-aware messages — legitimate cron-driven pipelines), or
`ORGANIC`. `FARMED` is the only disqualifying label — it drops the
account from the board regardless of contribution count. This used to be
an investigative tool only, verified against known cases but never
actually applied to the published list; it's now wired into every run.

**Refresh** (`src/update_leaderboard.py`): for every non-`FARMED`
candidate, pulls their real
`contributionsCollection.contributionCalendar.totalContributions` (minus
GitHub's own `restrictedContributionsCount`, so private-repo activity
can't inflate a public ranking) from GitHub's GraphQL API, drops anyone
at 0, ranks the rest, and keeps the top 20 per country for
`docs/data.json`. Runs on the VM's own crontab every 5 days — not GitHub
Actions, same reasoning as every other tracker in this portfolio
(schedule triggers deliver a fraction of their configured cadence for
sub-hourly jobs; less of a concern at 5 days, but no reason to introduce
a second automation pattern for one repo).

## Data

- `docs/data.json` — current leaderboard snapshot per country, fetched by
  the dashboard.
- `data/history.csv` — append-only history of every refresh, for tracking
  movement over time. Rows before the 3-country expansion don't have a
  `country` column (Tanzania-only at the time).
