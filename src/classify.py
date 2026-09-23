"""Phase B: the actual differentiator -- classifies a user's real commit
activity into categories, rather than trusting a raw contribution count.

Every pattern here is grounded in a real case found and verified this
project's earlier investigation of committers.top, not theoretical:
  - IMPORTED_HISTORY: Ajmalleonard/opin -- 17k+ real commits, but pushed
    all at once from a ~13-month-old local history. Detected by comparing
    the repo's push date against the actual spread of commit dates inside
    it.
  - FARMED: ebrahimHakimuddin's "repo-to-beat-top-git-commits-in-tanzania"
    -- ~137,000 commits, messages literally "commit 5000", "commit 4999"...
    all landing in the same second. Detected via sequential/generic
    message patterns and multiple commits sharing one timestamp.
  - AUTOMATED_PIPELINE: legitimate cron-driven data pipelines (the pattern
    this portfolio's own 7 VM trackers use) -- very regular intervals, but
    with real, content-aware messages describing actual data changes, not
    placeholder text.
  - ORGANIC: normal human (or AI-agent-assisted) development -- varied
    timing, varied and substantive messages.
"""

import re
import statistics
from collections import Counter
from datetime import datetime

import requests

from config import COMMITS_TO_SAMPLE_PER_REPO, REPOS_TO_SAMPLE_PER_USER

API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json"}

GENERIC_MESSAGE_RE = re.compile(
    r"^(commit\s*#?\d+|update|wip|test|\.|fix|changes?)$", re.IGNORECASE
)


def _get(url, params=None, token=None):
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _user_repos(login, limit=REPOS_TO_SAMPLE_PER_USER, token=None):
    repos = _get(f"{API}/users/{login}/repos",
                 params={"per_page": 100, "sort": "pushed", "type": "owner"}, token=token)
    if not repos:
        return []
    non_forks = [r for r in repos if not r.get("fork")]
    return sorted(non_forks, key=lambda r: r.get("size", 0), reverse=True)[:limit]


def _repo_commits(login, repo_name, limit=COMMITS_TO_SAMPLE_PER_REPO, token=None):
    commits = _get(
        f"{API}/repos/{login}/{repo_name}/commits",
        params={"author": login, "per_page": limit}, token=token,
    )
    return commits or []


def _classify_repo(repo, commits):
    """Returns one label for a single repo's commit pattern."""
    if not commits:
        return None

    dates = []
    messages = []
    for c in commits:
        try:
            dates.append(datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")))
        except (KeyError, ValueError):
            continue
        messages.append(c["commit"]["message"].split("\n")[0].strip())

    if not dates:
        return None

    # -- FARMED: generic/sequential messages + repeated identical timestamps --
    generic_count = sum(1 for m in messages if GENERIC_MESSAGE_RE.match(m))
    timestamp_counts = Counter(dates)
    max_same_timestamp = max(timestamp_counts.values())
    if generic_count / len(messages) > 0.5 and max_same_timestamp >= 5:
        return "FARMED"

    # -- IMPORTED_HISTORY: commit dates span far earlier than the repo's own push date --
    repo_pushed = repo.get("pushed_at")
    repo_created = repo.get("created_at")
    if repo_created:
        try:
            created_dt = datetime.fromisoformat(repo_created.replace("Z", "+00:00"))
            oldest_commit = min(dates)
            span_days = (created_dt - oldest_commit).days
            if span_days > 30:  # commits predate the repo's own existence by a month+
                return "IMPORTED_HISTORY"
        except ValueError:
            pass

    # -- AUTOMATED_PIPELINE: very regular intervals between commits --
    if len(dates) >= 5:
        sorted_dates = sorted(dates)
        gaps_minutes = [
            (b - a).total_seconds() / 60
            for a, b in zip(sorted_dates, sorted_dates[1:])
        ]
        if len(gaps_minutes) >= 4:
            median_gap = statistics.median(gaps_minutes)
            if median_gap > 0:
                deviation = statistics.pstdev(gaps_minutes) / median_gap
                # low relative variance in timing = suspiciously regular = automation
                if deviation < 0.3 and 5 <= median_gap <= 24 * 60:
                    return "AUTOMATED_PIPELINE"

    return "ORGANIC"


def classify_user(candidate, token=None):
    """Returns the candidate dict enriched with a `classification` summary:
    the label distribution across their sampled repos, and an overall tag.
    """
    login = candidate["login"]
    repos = _user_repos(login, token=token)

    labels = []
    for repo in repos:
        commits = _repo_commits(login, repo["name"], token=token)
        label = _classify_repo(repo, commits)
        if label:
            labels.append(label)

    label_counts = Counter(labels)
    if not label_counts:
        overall = "UNKNOWN"
    elif label_counts.get("FARMED", 0) > 0:
        overall = "FARMED"  # any confirmed farming repo is disqualifying, full stop
    elif label_counts.most_common(1)[0][0] == "IMPORTED_HISTORY" and len(label_counts) == 1:
        overall = "IMPORTED_HISTORY"
    elif label_counts.get("AUTOMATED_PIPELINE", 0) > label_counts.get("ORGANIC", 0):
        overall = "AUTOMATED_PIPELINE"
    else:
        overall = "ORGANIC"

    candidate["classification"] = {
        "overall": overall,
        "repo_labels": dict(label_counts),
        "repos_sampled": len(repos),
    }
    return candidate
