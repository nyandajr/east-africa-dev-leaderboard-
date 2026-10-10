"""Phase A: candidate discovery, sourced from committers.top's own public
rank feed rather than re-deriving a candidate pool from scratch.

The original approach used GitHub's Search API (location:"<country>",
sorted by followers) and capped the shortlist at 40 per country. That
missed real, highly active developers badly: a live spot-check against
committers.top/tanzania_public found 9 developers with 1,500-4,000+
contributions each who all ranked beyond followers-rank 100 (one as
deep as rank 645 -- Barakael, 11 followers), and a 10th (av-dev2) whose
location field is "dar es salaam" with no country name in it at all,
so no location-text search would ever find them regardless of depth.

committers.top has already solved discovery at a scale (GH Archive-based
crawling, not a per-request API) this project can't replicate every 5
days. Its rank_only/<country>.json feed is the same data this repo
already pulls for its own committers.top rank badge -- confirmed live
to contain all 10 of the above (256/256 Tanzania candidates total).

This phase is intentionally "trust their discovery, verify everything
else": classify.py (Phase B) is this project's actual differentiator,
flagging FARMED/IMPORTED_HISTORY accounts that a raw contribution count
-- committers.top's or GitHub's own -- doesn't distinguish.
"""

import requests

from config import COUNTRIES

RANK_FEED_URL = "https://committers.top/rank_only/{country}.json"


def discover_country(country):
    """Returns every candidate committers.top tracks for `country`."""
    resp = requests.get(RANK_FEED_URL.format(country=country.lower()), timeout=30)
    resp.raise_for_status()
    logins = resp.json().get("user", [])
    return [{"login": login, "country": country} for login in logins]


def discover_all():
    all_candidates = {}
    for country in COUNTRIES:
        found = discover_country(country)
        print(f"[discover] {country}: {len(found)} candidates")
        all_candidates[country] = found
    return all_candidates


if __name__ == "__main__":
    discover_all()
