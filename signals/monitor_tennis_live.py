"""
monitor_tennis_live.py — End-to-end example: poll DraftKings' live tennis
moneyline via The Odds API, compare to your model's fair value, and push a
phone alert (ntfy) when an edge fires. Bet placement stays manual.

RUN IT:
    export ODDS_API_KEY=your_key_from_the-odds-api.com
    export NTFY_TOPIC=edge-signals-7f3a9c      # a secret topic only you know
    python3 monitor_tennis_live.py

Then, in the ntfy app on your phone, Subscribe to that same NTFY_TOPIC.

IMPORTANT — you still drive the match STATE. The Odds API gives you the price,
not the live score or the rolling serve% that is your actual edge. As the match
progresses, update `sig` (see update_from_your_feed below): either by hand at
changeovers, or from your own live-scores source. The monitor re-prices the
edge against DraftKings every poll and only pushes when it clears your
threshold (and only when the alert actually changes, not every tick).
"""

import os
import sys

from tennis_signal import TennisLiveSignal
from live_monitor import run_monitor
from odds_feed import TheOddsAPIClient, notify_ntfy, deduped, OddsFeedError


# ---- configure your match ---------------------------------------------------
NAME_A = os.environ.get("PLAYER_A", "Carlos Alcaraz")
NAME_B = os.environ.get("PLAYER_B", "Jannik Sinner")
BEST_OF = int(os.environ.get("BEST_OF", "3"))
EDGE_THRESHOLD = float(os.environ.get("EDGE_THRESHOLD", "0.03"))
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "90"))  # mind the free-tier quota

# The Odds API's tennis sport_key changes per tournament. Discover it once with
# client.find_sports("tennis") and set it here (or via env).
SPORT_KEY = os.environ.get("ODDS_SPORT_KEY", "")  # e.g. "tennis_atp_wimbledon"


def build():
    api_key = os.environ.get("ODDS_API_KEY")
    topic = os.environ.get("NTFY_TOPIC")
    if not api_key:
        sys.exit("Set ODDS_API_KEY (free key from the-odds-api.com).")
    if not topic:
        sys.exit("Set NTFY_TOPIC to a secret string, and Subscribe to it in the ntfy app.")

    client = TheOddsAPIClient(api_key)

    # Help the user find the sport_key if they didn't set one.
    sport_key = SPORT_KEY
    if not sport_key:
        matches = client.find_sports("tennis")
        if not matches:
            sys.exit("No active tennis sports on The Odds API right now.")
        print("Set ODDS_SPORT_KEY to one of these active tennis keys:")
        for sp in matches:
            print(f"  {sp['key']}  —  {sp['title']}")
        sys.exit(0)

    sig = TennisLiveSignal(NAME_A, NAME_B, best_of=BEST_OF, edge_threshold=EDGE_THRESHOLD)
    # Seed with your starting read — REPLACE with real rolling, surface-adjusted %.
    sig.update_serve_stats(pA_pt=0.66, pB_pt=0.60)
    sig.update_score(setsA=0, setsB=0, gamesA=0, gamesB=0, server="A")

    def update_from_your_feed():
        # TODO: keep `sig` current as you watch. By hand at changeovers:
        #   sig.update_score(setsA=1, setsB=0, gamesA=3, gamesB=2, server="B")
        #   sig.update_serve_stats(pA_pt=0.64, pB_pt=0.57)   # e.g. B tiring
        # ...or wire your own live-scores API here. Left as a no-op so the
        # example runs; your edge is only as good as what you put here.
        pass

    def fetch_state():
        update_from_your_feed()
        return sig

    def fetch_odds():
        odds_a, odds_b = client.draftkings_h2h(sport_key, NAME_A, NAME_B)
        return {"odds_a": odds_a, "odds_b": odds_b}

    def compute_signal(state, odds):
        return state.check_signal(odds["odds_a"], odds["odds_b"])

    def push(result):
        body = (f"{result['score']}\n"
                f"fair {result['fair_prob_A']:.0%} vs DK {result['market_implied_A']:.0%}  "
                f"(edge {result['edge_A']:+.1%})\n"
                f"stake {result['kelly_stake_pct']}% of bankroll")
        notify_ntfy(os.environ["NTFY_TOPIC"],
                    title=f"⚡ {result['signal']}", message=body,
                    tags="tennis,money_with_wings")
        rem = client.remaining_requests
        print(f"[pushed] {result['signal']}  (API requests left: {rem})")

    def on_error(exc):
        # One bad poll (network blip, name mismatch, quota) shouldn't kill it.
        print(f"[warn] poll skipped: {exc}")
        if isinstance(exc, OddsFeedError) and "401" in str(exc):
            return True  # bad key — stop the loop
        return False

    return fetch_state, fetch_odds, compute_signal, deduped(push), on_error, client


if __name__ == "__main__":
    fetch_state, fetch_odds, compute_signal, on_signal, on_error, client = build()
    print(f"Monitoring {NAME_A} vs {NAME_B} on DraftKings every {POLL_SECONDS:.0f}s. "
          f"Ctrl-C to stop.")
    try:
        run_monitor(fetch_state, fetch_odds, compute_signal,
                    poll_seconds=POLL_SECONDS, on_signal=on_signal, on_error=on_error)
    except KeyboardInterrupt:
        print(f"\nStopped. API requests remaining: {client.remaining_requests}")
