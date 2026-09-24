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
COMMITTERS_BADGE_JSON = os.path.join(REPO_DIR, "docs", "committers_rank_badge.json")
CATCHUP_BADGE_JSON = os.path.join(REPO_DIR, "docs", "catchup_badge.json")
PACE_WINDOW_DAYS = 14

# The login whose committers.top rank gets published as a self-hosted
# shields.io endpoint badge (see fetch_committers_rank below).
PROFILE_BADGE_LOGIN = "nyandajr"
PROFILE_BADGE_COUNTRY = "Tanzania"

# Top 20 candidates per country by GitHub follower count (GitHub Search
# API, location:"<country>"), as of the 2026-09-23 launch. Raw lists,
# unfiltered by commit-authenticity classification -- same "count
# everyone, no exclusions" methodology committers.top itself uses. Config,
# not hardcoded logic -- add/remove names here as the community
# leaderboard shifts, no code changes needed.
TRACKED_USERS_BY_COUNTRY = {
    "Tanzania": [
        "Ajmalleonard", "ebrahimHakimuddin", "nyandajr", "raydanielg", "cleven12",
        "tacheraSasi", "isonlycoolie", "alobit21", "atilioobadia-cpu", "ALTUM-02",
        "dexflare", "nyenza", "lykmapipo", "karimshaban01", "avict18",
        "Kalebu", "isaka-james", "tarxemo", "gernest", "TheCollinsByte",
    ],
    "Kenya": [
        "JohnMwendwa", "dirambora", "david-kariuki", "omololevy", "godfreymatagaro",
        "Maxwell-Muthui-Mwangi", "jonkirathe", "iVGeek", "Mathenge-Alex", "fbiego",
        "Dark-Xploit", "mbitujames", "jumaallan", "betascribbles", "danielmuthama",
        "jackjulla", "Mulandii", "peanutsx50", "jmoseka", "Obraims",
    ],
    "Uganda": [
        "judeotine", "jod35", "codebender828", "jesar-enl", "KubanjaElijahEldred",
        "kidde60", "has2k1", "MUKE-coder", "chardso", "ceasor-elvis",
        "kallyas", "FahimWeblogicAndCyberTechnologies", "iamtutumo", "innocentmukjr",
        "KATUMBA-ANDREW-FELIX", "PerezChris99", "HassanBahati", "rubanzasilva",
        "Tumworobere", "Wanderajonah",
    ],
}

GRAPHQL_URL = "https://api.github.com/graphql"


def fetch_contributions(login, token):
    # Ranks by PUBLIC contributions (total minus GitHub's own
    # restrictedContributionsCount), not the raw total -- matches
    # committers.top's own methodology (verified by reading its source:
    # github.com/ashkulz/committers.top, output.go's
    # selectPublicContributions). Private-repo activity can't be seen or
    # verified by anyone looking at this board, so it shouldn't be able to
    # inflate a public ranking -- confirmed this was inflating
    # Ajmalleonard's rank by 71k+ contributions before this fix.
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar { totalContributions }
          restrictedContributionsCount
        }
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
        collection = data["data"]["user"]["contributionsCollection"]
        total = collection["contributionCalendar"]["totalContributions"]
        restricted = collection["restrictedContributionsCount"]
        return total - restricted
    except (KeyError, TypeError):
        print(f"[update_leaderboard] couldn't fetch {login}: {data}")
        return None


def fetch_committers_rank(login, country):
    """Pulls committers.top's own rank-only JSON feed and finds login's
    1-indexed position, for the self-hosted profile badge below. Returns
    None if the feed is unreachable or login isn't listed (don't want a
    stale badge on a transient failure -- caller keeps the last badge in
    that case rather than overwriting it with an error state).
    """
    try:
        resp = requests.get(f"https://committers.top/rank_only/{country.lower()}.json", timeout=15)
        resp.raise_for_status()
        users = resp.json().get("user", [])
        return users.index(login) + 1
    except (requests.RequestException, ValueError):
        return None


def fetch_recent_daily_pace(login, token, days=PACE_WINDOW_DAYS):
    """Average daily contribution count over the last `days` days, from
    GitHub's own contribution calendar -- used to project a realistic
    catch-up date rather than assuming a flat historical average.
    """
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar { weeks { contributionDays { contributionCount } } }
        }
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
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        all_days = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
        recent = all_days[-days:]
        return sum(recent) / len(recent) if recent else 0.0
    except (KeyError, TypeError):
        print(f"[update_leaderboard] couldn't fetch pace for {login}: {data}")
        return None


def write_catchup_badge(countries, token):
    """If PROFILE_BADGE_LOGIN isn't #1 in their country, projects how many
    days at current relative pace it'd take to close the gap, and
    publishes it as a self-hosted badge -- same reasoning as the
    committers.top rank badge: a real, live-computed number instead of a
    one-off answer that goes stale the moment it's given.
    """
    board = countries.get(PROFILE_BADGE_COUNTRY, [])
    if not board:
        return
    me = next((r for r in board if r["login"] == PROFILE_BADGE_LOGIN), None)
    leader = board[0]
    if me is None:
        return

    if leader["login"] == PROFILE_BADGE_LOGIN:
        badge = {
            "schemaVersion": 1, "label": "path to #1",
            "message": f"already #1 {PROFILE_BADGE_COUNTRY}",
            "color": "00bfff", "labelColor": "050b18",
        }
        print(f"[update_leaderboard] {PROFILE_BADGE_LOGIN} is already #1 in {PROFILE_BADGE_COUNTRY}")
    else:
        gap = leader["contributions"] - me["contributions"]
        my_pace = fetch_recent_daily_pace(PROFILE_BADGE_LOGIN, token)
        leader_pace = fetch_recent_daily_pace(leader["login"], token)
        if my_pace is None or leader_pace is None:
            print("[update_leaderboard] couldn't compute catch-up pace, leaving badge as-is")
            return
        net_pace = my_pace - leader_pace
        if net_pace <= 0:
            message = f"not closing ({gap:,} behind {leader['login']})"
        else:
            days_needed = gap / net_pace
            message = f"~{days_needed:.0f}d behind {leader['login']}"
        badge = {
            "schemaVersion": 1, "label": "path to #1",
            "message": message,
            "color": "00bfff", "labelColor": "050b18",
        }
        print(
            f"[update_leaderboard] {PROFILE_BADGE_LOGIN}: {gap:,} behind {leader['login']} "
            f"({my_pace:.0f}/day vs {leader_pace:.0f}/day, net {net_pace:+.0f}/day) -> {message}"
        )

    with open(CATCHUP_BADGE_JSON, "w") as f:
        json.dump(badge, f, indent=2)


def write_committers_badge(rank, country):
    if rank is None:
        print("[update_leaderboard] committers.top rank unavailable, leaving badge as-is")
        return
    badge = {
        "schemaVersion": 1,
        "label": "committers.top rank",
        "message": f"#{rank} {country}",
        "color": "00bfff",
        "labelColor": "050b18",
    }
    with open(COMMITTERS_BADGE_JSON, "w") as f:
        json.dump(badge, f, indent=2)
    print(f"[update_leaderboard] {PROFILE_BADGE_LOGIN} is #{rank} on committers.top/{country}")


def run(token=None):
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set -- GraphQL requires an authenticated token")

    countries = {}
    for country, users in TRACKED_USERS_BY_COUNTRY.items():
        results = []
        for login in users:
            count = fetch_contributions(login, token)
            if count is not None:
                results.append({"login": login, "contributions": count})
                print(f"[update_leaderboard] {country} — {login}: {count:,}")
        results.sort(key=lambda r: r["contributions"], reverse=True)
        countries[country] = results

    generated_at = datetime.now(timezone.utc).isoformat()

    os.makedirs(os.path.dirname(DATA_JSON), exist_ok=True)
    with open(DATA_JSON, "w") as f:
        json.dump({"generated_at": generated_at, "countries": countries}, f, indent=2)
    print(f"[update_leaderboard] wrote {DATA_JSON}")

    os.makedirs(os.path.dirname(HISTORY_CSV), exist_ok=True)
    is_new = not os.path.exists(HISTORY_CSV)
    with open(HISTORY_CSV, "a") as f:
        if is_new:
            f.write("generated_at,country,login,contributions\n")
        for country, results in countries.items():
            for r in results:
                f.write(f"{generated_at},{country},{r['login']},{r['contributions']}\n")
    print(f"[update_leaderboard] appended to {HISTORY_CSV}")

    rank = fetch_committers_rank(PROFILE_BADGE_LOGIN, PROFILE_BADGE_COUNTRY)
    write_committers_badge(rank, PROFILE_BADGE_COUNTRY)
    write_catchup_badge(countries, token)

    return countries


if __name__ == "__main__":
    run()
