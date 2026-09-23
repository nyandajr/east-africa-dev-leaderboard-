"""Shared constants for the East Africa Dev Leaderboard."""

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
CANDIDATES_FILE = DATA_DIR / "candidates.json"
LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"
HISTORY_FILE = DATA_DIR / "history.csv"
DASHBOARD_JSON = REPO_DIR / "docs" / "data.json"

# Verified live 2026-09-23 via GitHub's Search API -- real counts, not estimates.
COUNTRIES = {
    "Tanzania": 6402,
    "Kenya": 36592,
    "Uganda": 8793,
    "Rwanda": 6554,
    "Burundi": 553,
}

# Per-country shortlist size for the detailed classifier pass. Keeps total
# detailed-analysis API usage bounded and predictable regardless of how the
# underlying candidate pool grows.
SHORTLIST_SIZE_PER_COUNTRY = 40

# How many of a candidate's own (non-fork) repos get sampled for the
# classifier pass. More repos = better signal but more API calls per user.
REPOS_TO_SAMPLE_PER_USER = 5

# Commits sampled per repo when checking timing/message patterns.
COMMITS_TO_SAMPLE_PER_REPO = 30

UPDATE_CADENCE_DAYS = 5
