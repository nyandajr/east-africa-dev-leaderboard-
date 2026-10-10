"""Shared constants for the East Africa Dev Leaderboard."""

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"
HISTORY_FILE = DATA_DIR / "history.csv"
DASHBOARD_JSON = REPO_DIR / "docs" / "data.json"

# Countries tracked -- the key doubles as committers.top's URL slug
# (lowercased) in discover.py.
COUNTRIES = ["Tanzania", "Kenya", "Uganda", "Rwanda", "Burundi"]

# How many of a candidate's own (non-fork) repos get sampled for the
# classifier pass. More repos = better signal but more API calls per user.
REPOS_TO_SAMPLE_PER_USER = 5

# Commits sampled per repo when checking timing/message patterns.
COMMITS_TO_SAMPLE_PER_REPO = 30

# How many developers get published per country after classification and
# ranking -- the board is a "top N", not a full dump of every committers.top
# candidate (currently 256 per country).
BOARD_SIZE_PER_COUNTRY = 20

UPDATE_CADENCE_DAYS = 5
