"""
Automated sanity tests for live_monitor.py.

Run with:
    python3 test_live_monitor.py     # plain asserts
    pytest test_live_monitor.py      # if pytest is installed
"""

import sys

from live_monitor import run_monitor, signal_fired


NOOP_SLEEP = lambda s: None


def test_fires_only_on_signal():
    """on_signal must fire only for ticks whose result has a truthy 'signal'."""
    ticks = [
        {"signal": None},
        {"signal": "BET A @ -110"},
        {"signal": None},
        {"signal": "BET B @ +120"},
    ]
    it = iter(ticks)
    fired = []

    def fetch_state():
        return None

    def fetch_odds():
        return None

    def compute(state, odds):
        return next(it)

    count = run_monitor(fetch_state, fetch_odds, compute,
                        poll_seconds=0, on_signal=fired.append,
                        max_polls=len(ticks), sleep_fn=NOOP_SLEEP)
    assert count == 2, f"expected 2 signals, got {count}"
    assert len(fired) == 2, f"callback fired {len(fired)} times, expected 2"
    assert fired[0]["signal"] == "BET A @ -110"
    assert fired[1]["signal"] == "BET B @ +120"


def test_no_spam_on_no_edge():
    """A run of pure no-edge ticks must never call on_signal."""
    def compute(state, odds):
        return {"signal": None}

    fired = []
    count = run_monitor(lambda: None, lambda: None, compute,
                        poll_seconds=0, on_signal=fired.append,
                        max_polls=10, sleep_fn=NOOP_SLEEP)
    assert count == 0 and fired == [], "no-edge ticks should stay silent"


def test_bad_feed_does_not_kill_loop():
    """A raising poll cycle is swallowed; the loop keeps going and later
    signals still fire."""
    calls = {"n": 0}

    def compute(state, odds):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ValueError("simulated broken feed response")
        if calls["n"] == 3:
            return {"signal": "BET A @ -110"}
        return {"signal": None}

    errors = []
    fired = []
    count = run_monitor(lambda: None, lambda: None, compute,
                        poll_seconds=0, on_signal=fired.append,
                        on_error=lambda e: errors.append(e),
                        max_polls=4, sleep_fn=NOOP_SLEEP)
    assert len(errors) == 1, f"expected 1 caught error, got {len(errors)}"
    assert count == 1, f"expected 1 signal after recovery, got {count}"
    assert calls["n"] == 4, "loop should have completed all 4 polls"


def test_on_error_can_stop_loop():
    """Returning truthy from on_error stops the loop early."""
    def compute(state, odds):
        raise RuntimeError("fatal")

    stops = []
    count = run_monitor(lambda: None, lambda: None, compute,
                        poll_seconds=0,
                        on_error=lambda e: stops.append(e) or True,
                        max_polls=10, sleep_fn=NOOP_SLEEP)
    assert len(stops) == 1, "on_error should have been called exactly once before stopping"
    assert count == 0


def test_should_continue_kill_switch():
    """should_continue=False stops the loop gracefully (e.g. game over)."""
    state = {"polls": 0}

    def compute(s, o):
        return {"signal": None}

    def keep_going():
        state["polls"] += 1
        return state["polls"] <= 3  # allow 3 cycles, then stop

    count = run_monitor(lambda: None, lambda: None, compute,
                        poll_seconds=0, should_continue=keep_going,
                        max_polls=100, sleep_fn=NOOP_SLEEP)
    # keep_going is checked at the top of each cycle; it returns True 3 times.
    assert state["polls"] == 4, f"expected 4 checks (3 True + 1 False), got {state['polls']}"
    assert count == 0


def test_sleep_between_but_not_after_last():
    """sleep_fn is called between ticks but not after the final bounded poll."""
    sleeps = []

    def compute(s, o):
        return {"signal": None}

    run_monitor(lambda: None, lambda: None, compute,
                poll_seconds=5, max_polls=3,
                sleep_fn=lambda s: sleeps.append(s))
    assert sleeps == [5, 5], f"expected 2 inter-tick sleeps for 3 polls, got {sleeps}"


def test_signal_fired_predicate():
    """The default predicate matches the check_signal() result shape."""
    assert signal_fired({"signal": "BET A"}) is True
    assert signal_fired({"signal": None}) is False
    assert signal_fired({}) is False
    assert signal_fired(None) is False


def test_end_to_end_with_real_signal_class():
    """Wire the monitor to a real TennisLiveSignal + fake odds feed and confirm
    it fires exactly when the modeled edge crosses the threshold."""
    from tennis_signal import TennisLiveSignal

    sig = TennisLiveSignal("A", "B", best_of=3, edge_threshold=0.03)
    sig.update_serve_stats(0.64, 0.62)
    sig.update_score(0, 0, 3, 3, 'A')  # fair A ~0.58

    ticks = iter([
        {"odds_a": -160, "odds_b": +140},  # market agrees -> no edge
        {"odds_a": -110, "odds_b": -110},  # market lagging -> edge -> fire
    ])
    fired = []
    count = run_monitor(
        lambda: sig,
        lambda: next(ticks),
        lambda s, o: s.check_signal(o["odds_a"], o["odds_b"]),
        poll_seconds=0, on_signal=fired.append, max_polls=2, sleep_fn=NOOP_SLEEP,
    )
    assert count == 1, f"expected exactly 1 fire, got {count}"
    assert "BET A" in fired[0]["signal"], f"unexpected signal: {fired[0]['signal']}"
    assert fired[0]["kelly_stake_pct"] > 0, "fired signal should size a positive stake"


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
