"""VM-side automation entry point -- run from the VM's own crontab every 5
days, not GitHub Actions (same proven pattern as the other 7 trackers in
this portfolio; GitHub's schedule trigger was repeatedly measured at
~15-21% real delivery for sub-hourly cadences -- less of a concern at a
5-day cadence, but no reason to introduce a second automation pattern into
this portfolio for one repo).
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_DIR / "src"
DATA_FILES = [
    "data/history.csv", "docs/data.json",
    "docs/committers_rank_badge.json", "docs/catchup_badge.json",
]

sys.path.insert(0, str(SRC_DIR))
load_dotenv(REPO_DIR / ".env")  # populates GITHUB_TOKEN for update_leaderboard.py


def run(*args, check=True):
    return subprocess.run(list(args), cwd=str(REPO_DIR), check=check)


def sync_with_remote():
    # --hard, not --soft, and BEFORE the pipeline runs -- reset --soft only
    # moves HEAD, leaving stale index entries for any file this script
    # doesn't explicitly `git add`, which then get silently recommitted on
    # the next force-push. Learned this the hard way on hormuz-strait-monitor.
    run("git", "fetch", "origin", "main")
    run("git", "reset", "--hard", "origin/main")


def build_commit_message(countries):
    total = sum(len(entries) for entries in countries.values())
    leader = None
    leader_country = None
    for country, entries in countries.items():
        if entries and (leader is None or entries[0]["contributions"] > leader["contributions"]):
            leader = entries[0]
            leader_country = country
    if leader is None:
        return f"data: leaderboard refresh — {total} tracked"
    return (
        f"data: leaderboard refresh — {leader['login']} ({leader_country}) leads "
        f"({leader['contributions']:,} contributions) — {total} tracked across "
        f"{len(countries)} countries"
    )


def git_commit_and_push(countries, token):
    # freddynyanda@proton.me is Fred's real, verified GitHub email -- same
    # standardization as every other tracker in this portfolio.
    run("git", "config", "user.name", "nyandajr")
    run("git", "config", "user.email", "freddynyanda@proton.me")
    run("git", "add", *DATA_FILES, check=False)

    diff = run("git", "diff", "--cached", "--quiet", check=False)
    if diff.returncode == 0:
        print("[run_and_push] no changes to commit")
        return

    run("git", "commit", "-m", build_commit_message(countries))
    # Authenticated URL built at push time from the .env token, rather than
    # storing credentials in git config on disk.
    push_url = f"https://{token}@github.com/nyandajr/east-africa-dev-leaderboard-.git"
    run("git", "push", "--force", push_url, "HEAD:main")


def main():
    sync_with_remote()

    import update_leaderboard
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set in the VM's environment")
    countries = update_leaderboard.run(token=token)

    git_commit_and_push(countries, token)
    print("[run_and_push] done")


if __name__ == "__main__":
    main()
