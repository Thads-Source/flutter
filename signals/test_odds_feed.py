"""
Offline sanity tests for odds_feed.py — parser and payload construction only.
No network calls (no real API key needed).

Run with:
    python3 test_odds_feed.py
    pytest test_odds_feed.py
"""

import sys

from odds_feed import extract_dk_h2h, notify_ntfy, notify_pushover, deduped, OddsFeedError


SAMPLE = [{
    "id": "abc123",
    "sport_key": "tennis_atp_example",
    "home_team": "Carlos Alcaraz",
    "away_team": "Jannik Sinner",
    "bookmakers": [
        {"key": "fanduel", "title": "FanDuel", "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "Carlos Alcaraz", "price": -150},
                {"name": "Jannik Sinner", "price": 130}]}]},
        {"key": "draftkings", "title": "DraftKings", "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "Carlos Alcaraz", "price": -140},
                {"name": "Jannik Sinner", "price": 120}]}]},
    ],
}]


def test_extracts_draftkings_not_other_book():
    a, b = extract_dk_h2h(SAMPLE, "Alcaraz", "Sinner")
    assert (a, b) == (-140, 120), f"should pull DK prices, got {(a, b)}"


def test_name_matching_is_lenient():
    # last-name / partial spellings still resolve
    a, b = extract_dk_h2h(SAMPLE, "carlos alcaraz", "J. Sinner")
    assert (a, b) == (-140, 120)


def test_order_independent():
    a, b = extract_dk_h2h(SAMPLE, "Sinner", "Alcaraz")
    assert (a, b) == (120, -140), "returns prices in the order the names were asked"


def test_missing_event_raises():
    try:
        extract_dk_h2h(SAMPLE, "Djokovic", "Nadal")
        assert False, "should have raised for an unknown matchup"
    except OddsFeedError as e:
        assert "No draftkings h2h price" in str(e)


def test_no_draftkings_raises():
    only_fd = [{
        "home_team": "A", "away_team": "B",
        "bookmakers": [{"key": "fanduel", "markets": [
            {"key": "h2h", "outcomes": [
                {"name": "A", "price": -110}, {"name": "B", "price": -110}]}]}],
    }]
    try:
        extract_dk_h2h(only_fd, "A", "B")
        assert False, "should raise when DraftKings isn't present"
    except OddsFeedError:
        pass


def test_ntfy_payload_dry_run():
    p = notify_ntfy("edge-secret", "EDGE", "BET Alcaraz @ -140",
                    priority="urgent", tags="tennis", dry_run=True)
    assert p["url"].endswith("/edge-secret")
    assert p["headers"]["Title"] == "EDGE"
    assert p["headers"]["Priority"] == "urgent"
    assert p["body"] == "BET Alcaraz @ -140"


def test_pushover_payload_dry_run():
    p = notify_pushover("tok", "usr", "EDGE", "BET Alcaraz @ -140", dry_run=True)
    assert "pushover.net" in p["url"]
    assert "message=BET" in p["body"]


def test_deduped_only_alerts_on_change():
    sent = []
    on_signal = deduped(lambda r: sent.append(r["signal"]))

    on_signal({"signal": "BET A @ -140", "kelly_stake_pct": 2.5})   # new -> send
    on_signal({"signal": "BET A @ -140", "kelly_stake_pct": 2.5})   # same -> quiet
    on_signal({"signal": "BET A @ -140", "kelly_stake_pct": 3.1})   # stake changed -> send
    on_signal({"signal": "BET B @ +120", "kelly_stake_pct": 1.0})   # side changed -> send
    assert sent == ["BET A @ -140", "BET A @ -140", "BET B @ +120"], f"got {sent}"


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
