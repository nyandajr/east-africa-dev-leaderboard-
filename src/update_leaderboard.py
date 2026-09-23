"""Refreshes docs/data.json with real, current contribution counts for the
tracked candidate list via GitHub's GraphQL API. Runs on the VM's own
crontab every 5 days -- not GitHub Actions, same reasoning as every other
tracker in this portfolio (schedule triggers deliver a fraction of their
configured cadence for anything sub-hourly; at a 5-day cadence that's less
of a concern, but there's no reason to introduce a second automation
pattern into this portfolio for one repo).
"""

import json
import os
from datetime import datetime, timezone

import requests

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JSON = os.path.join(REPO_DIR, "docs", "data.json")
HISTORY_CSV = os.path.join(REPO_DIR, "data", "history.csv")

# The 10 names committers.top itself tracks for Tanzania, as of the
# 2026-09-23 launch. Config, not hardcoded logic -- add/remove names here
# as the community leaderboard shifts, no code changes needed.
TRACKED_USERS = [
    "Ajmalleonard", "ebrahimHakimuddin", "nyandajr", "raydanielg", "cleven12",
    "tacheraSasi", "isonlycoolie", "alobit21", "atilioobadia-cpu", "ALTUM-02",
]

GRAPHQL_URL = "https://api.github.com/graphql"


def fetch_contributions(login, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection { contributionCalendar { totalContributions } }
      }
    }
    """
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": {"login": login}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except (KeyError, TypeError):
        print(f"[update_leaderboard] couldn't fetch {login}: {data}")
        return None


def run(token=None):
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set -- GraphQL requires an authenticated token")

    results = []
    for login in TRACKED_USERS:
        count = fetch_contributions(login, token)
        if count is not None:
            results.append({"login": login, "contributions": count})
            print(f"[update_leaderboard] {login}: {count:,}")

    results.sort(key=lambda r: r["contributions"], reverse=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    os.makedirs(os.path.dirname(DATA_JSON), exist_ok=True)
    with open(DATA_JSON, "w") as f:
        json.dump({"generated_at": generated_at, "leaderboard": results}, f, indent=2)
    print(f"[update_leaderboard] wrote {DATA_JSON}")

    os.makedirs(os.path.dirname(HISTORY_CSV), exist_ok=True)
    is_new = not os.path.exists(HISTORY_CSV)
    with open(HISTORY_CSV, "a") as f:
        if is_new:
            f.write("generated_at,login,contributions\n")
        for r in results:
            f.write(f"{generated_at},{r['login']},{r['contributions']}\n")
    print(f"[update_leaderboard] appended to {HISTORY_CSV}")

    return results


if __name__ == "__main__":
    run()
