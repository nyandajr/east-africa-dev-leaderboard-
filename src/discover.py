"""Phase A: cheap discovery + shortlisting.

Uses GitHub's Search API to find candidate users per country, sorted by
followers (a signal already included in search results, so this phase
costs only a handful of requests per country regardless of pool size --
no per-user calls needed here). Produces a shortlist that Phase B (the
detailed classifier in classify.py) then does deeper, more expensive
analysis on.
"""

import json
import time

import requests

from config import CANDIDATES_FILE, COUNTRIES, SHORTLIST_SIZE_PER_COUNTRY

SEARCH_URL = "https://api.github.com/search/users"
HEADERS = {"Accept": "application/vnd.github+json"}


def _request(url, params, token=None):
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def discover_country(country, limit=SHORTLIST_SIZE_PER_COUNTRY, token=None):
    """Returns up to `limit` candidates for a country, sorted by followers
    descending -- the same "top by followers first" filter committers.top
    itself uses, since checking every single user in a 30k+ pool isn't
    feasible within any reasonable API budget.
    """
    candidates = []
    per_page = 100
    page = 1
    while len(candidates) < limit and page <= 10:  # GitHub search caps at 1000 results total
        data = _request(
            SEARCH_URL,
            {"q": f'location:"{country}"', "sort": "followers", "order": "desc",
             "per_page": per_page, "page": page},
            token=token,
        )
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            candidates.append({
                "login": item["login"],
                "id": item["id"],
                "country": country,
                "html_url": item["html_url"],
            })
        page += 1
        time.sleep(1)  # be a polite citizen of the search API's stricter rate limit

    return candidates[:limit]


def discover_all(token=None):
    all_candidates = []
    for country in COUNTRIES:
        print(f"[discover] {country}...")
        found = discover_country(country, token=token)
        print(f"[discover]   {len(found)} candidates")
        all_candidates.extend(found)

    CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CANDIDATES_FILE, "w") as f:
        json.dump(all_candidates, f, indent=2)
    print(f"[discover] {len(all_candidates)} total candidates -> {CANDIDATES_FILE}")
    return all_candidates


if __name__ == "__main__":
    discover_all()
