"""
odds_feed.py — Pull live DraftKings odds from The Odds API and push phone
alerts via ntfy. Standard-library only (urllib) — no third-party deps.

WHY NOT "CONNECT TO DRAFTKINGS DIRECTLY":
DraftKings has no public odds API and no bet-placement API, and its Terms of
Service prohibit scraping and automated betting. The legitimate path is a
licensed odds aggregator — The Odds API (https://the-odds-api.com) — which
resells DraftKings' posted lines. This module reads those lines. It NEVER
places a bet: you get a push alert and place the bet yourself in the DK app.

WHAT THIS AUTOMATES (and what it doesn't):
  * fetch_odds  -> automated here (DraftKings h2h price via The Odds API).
  * fetch_state -> STILL YOURS. Odds APIs give prices, not the live score or
                   (especially) the rolling serve% / wOBA that are your edge.
                   You keep the signal object's state current as you watch;
                   this module only refreshes the market price it's compared to.

QUOTA WARNING: The Odds API free tier is ~500 requests/month. One h2h fetch =
1 request. Polling every 30s burns ~120/hour, i.e. the whole month in ~4
hours. Use a conservative poll_seconds (60-120s) and only while your match is
live. `remaining_requests` is surfaced after every call so you can watch it.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request


class OddsFeedError(Exception):
    """Raised on a bad/blocked API response so the monitor's try/except can
    swallow one bad poll without dying."""


# ---------------------------------------------------------------------------
# The Odds API client
# ---------------------------------------------------------------------------

class TheOddsAPIClient:
    """Thin wrapper over The Odds API v4 (https://the-odds-api.com).

    Get a free key at the-odds-api.com, then:
        client = TheOddsAPIClient(api_key)
        client.find_sports("tennis")          # discover the sport_key
        client.draftkings_h2h(sport_key, "Alcaraz", "Sinner")
    """

    BASE = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str, region: str = "us",
                 bookmaker: str = "draftkings", odds_format: str = "american",
                 timeout: float = 10.0):
        if not api_key:
            raise ValueError("api_key is required (get a free one at the-odds-api.com)")
        self.api_key = api_key
        self.region = region
        self.bookmaker = bookmaker
        self.odds_format = odds_format
        self.timeout = timeout
        self.remaining_requests = None  # updated from response headers
        self.used_requests = None

    def _get(self, path: str, params: dict):
        q = dict(params)
        q["apiKey"] = self.api_key
        url = f"{self.BASE}{path}?{urllib.parse.urlencode(q)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                # Quota accounting lives in response headers.
                self.remaining_requests = resp.headers.get("x-requests-remaining")
                self.used_requests = resp.headers.get("x-requests-used")
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 401:
                raise OddsFeedError(f"401 Unauthorized — check your API key. {body}")
            if e.code == 422:
                raise OddsFeedError(f"422 — bad sport_key or params. {body}")
            if e.code == 429:
                raise OddsFeedError(f"429 — out of quota / rate limited. {body}")
            raise OddsFeedError(f"HTTP {e.code} from The Odds API. {body}")
        except urllib.error.URLError as e:
            raise OddsFeedError(f"network error reaching The Odds API: {e.reason}")

    def list_sports(self, all_sports: bool = False):
        """Return the list of available sports (dicts with 'key','title',...)."""
        return self._get("/sports", {"all": "true" if all_sports else "false"})

    def find_sports(self, substring: str):
        """Convenience: sports whose key/title contains `substring` (case-insensitive).
        Use this to discover e.g. the current tennis tournament's sport_key."""
        s = substring.lower()
        return [sp for sp in self.list_sports(all_sports=True)
                if s in sp.get("key", "").lower() or s in sp.get("title", "").lower()]

    def fetch_odds(self, sport_key: str, markets: str = "h2h"):
        """Raw odds payload for a sport, DraftKings only, this client's format."""
        return self._get(f"/sports/{sport_key}/odds", {
            "regions": self.region,
            "markets": markets,
            "oddsFormat": self.odds_format,
            "bookmakers": self.bookmaker,
        })

    def draftkings_h2h(self, sport_key: str, name_a: str, name_b: str):
        """Return (odds_a, odds_b) — DraftKings moneyline for the event whose two
        h2h outcomes match name_a / name_b. Raises OddsFeedError if not found."""
        events = self.fetch_odds(sport_key, markets="h2h")
        return extract_dk_h2h(events, name_a, name_b, bookmaker=self.bookmaker)


def _tokens(s: str):
    return [t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t]


def _name_matches(outcome_name: str, wanted: str) -> bool:
    """Lenient player/team name match: handles 'Carlos Alcaraz' vs 'Alcaraz',
    'J. Sinner' vs 'Jannik Sinner', and different orderings — without matching
    on a shared first name alone."""
    ao, aw = _tokens(outcome_name), _tokens(wanted)
    if not ao or not aw:
        return False
    jo, jw = "".join(ao), "".join(aw)
    if jo in jw or jw in jo:      # full normalized substring either direction
        return True
    return ao[-1] == aw[-1]        # same last-name token


def extract_dk_h2h(events, name_a: str, name_b: str, bookmaker: str = "draftkings"):
    """Pure parser (unit-testable, no network): pull the (odds_a, odds_b) h2h
    prices for name_a/name_b from a The-Odds-API events payload.

    Returns American odds as ints. Raises OddsFeedError with a specific reason
    if the event, bookmaker, market, or an outcome name can't be found.
    """
    for ev in events or []:
        teams = [ev.get("home_team", ""), ev.get("away_team", "")]
        matched = (any(_name_matches(t, name_a) for t in teams)
                   and any(_name_matches(t, name_b) for t in teams))
        if not matched:
            # Fall back to matching against the h2h outcome names directly.
            pass

        for bk in ev.get("bookmakers", []):
            if bk.get("key") != bookmaker:
                continue
            for mkt in bk.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                outcomes = mkt.get("outcomes", [])
                odds_a = _find_price(outcomes, name_a)
                odds_b = _find_price(outcomes, name_b)
                if odds_a is not None and odds_b is not None:
                    return int(round(odds_a)), int(round(odds_b))

    raise OddsFeedError(
        f"No {bookmaker} h2h price found for '{name_a}' vs '{name_b}'. "
        f"Check the names match DraftKings' spelling and the match is posted/live."
    )


def _find_price(outcomes, wanted):
    for o in outcomes:
        if _name_matches(o.get("name", ""), wanted):
            return o.get("price")
    return None


# ---------------------------------------------------------------------------
# Phone push — ntfy (free, no account) with a Pushover fallback
# ---------------------------------------------------------------------------

def notify_ntfy(topic: str, title: str, message: str,
                server: str = "https://ntfy.sh", priority: str = "high",
                tags: str = "money_with_wings", click: str = None,
                timeout: float = 10.0, dry_run: bool = False):
    """Push a notification to your phone via ntfy.

    Setup (one time): install the ntfy app (iOS/Android), and 'Subscribe' to a
    topic name only you know — treat the topic like a password, e.g.
    'edge-signals-7f3a9c'. Pass that same string as `topic` here. No key needed.

    priority: 'min'|'low'|'default'|'high'|'urgent'. tags: comma list of emoji
    shortcodes (see ntfy.sh/docs). `click` is a URL opened when tapped.
    """
    url = f"{server.rstrip('/')}/{topic}"
    headers = {"Title": title, "Priority": priority, "Tags": tags}
    if click:
        headers["Click"] = click
    if dry_run:
        return {"url": url, "headers": headers, "body": message}
    req = urllib.request.Request(url, data=message.encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise OddsFeedError(f"ntfy push failed: {e}")


def notify_pushover(token: str, user: str, title: str, message: str,
                    priority: int = 1, timeout: float = 10.0, dry_run: bool = False):
    """Alternative push via Pushover (requires an account + app). Kept as a
    fallback; ntfy is the zero-setup default."""
    data = urllib.parse.urlencode({
        "token": token, "user": user, "title": title,
        "message": message, "priority": priority,
    }).encode("utf-8")
    if dry_run:
        return {"url": "https://api.pushover.net/1/messages.json", "body": data.decode()}
    req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise OddsFeedError(f"Pushover push failed: {e}")


def deduped(notify_fn):
    """Wrap a notifier so the SAME signal string isn't pushed on every poll —
    only fire the alert when the signal text changes (edge appears, flips, or
    the recommended stake/side changes). Returns a function(result_dict)."""
    last = {"key": None}

    def _on_signal(result):
        key = f"{result.get('signal')}|{result.get('kelly_stake_pct')}"
        if key == last["key"]:
            return  # same alert as last tick — stay quiet
        last["key"] = key
        return notify_fn(result)

    return _on_signal


if __name__ == "__main__":
    # No network here — just show the alert payload that WOULD be sent, and the
    # parser working against a sample The-Odds-API response.
    sample = [{
        "home_team": "Carlos Alcaraz", "away_team": "Jannik Sinner",
        "bookmakers": [{"key": "draftkings", "title": "DraftKings", "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "Carlos Alcaraz", "price": -140},
                {"name": "Jannik Sinner", "price": 120}]}]}],
    }]
    print("parsed DK h2h:", extract_dk_h2h(sample, "Alcaraz", "Sinner"))
    print("ntfy payload:", notify_ntfy("edge-demo", "EDGE", "BET Alcaraz @ -140",
                                       dry_run=True))
