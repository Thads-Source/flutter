"""
live_monitor.py — Generic polling loop that ties a signal model to a live
data + odds feed.

This is deliberately sport-agnostic: it knows nothing about tennis or
baseball. You give it three callables — one that fetches current game state,
one that fetches current market odds, and one that turns (state, odds) into a
signal result dict — and it polls them on an interval, firing your callback
ONLY when a signal actually fires (no spam on every no-edge tick).

    run_monitor(fetch_state_fn, fetch_odds_fn, compute_signal_fn,
                poll_seconds=5, on_signal=callback)

Design notes:
  * Each poll cycle is wrapped in try/except, so one malformed feed response
    (timeout, half-written JSON, a None where you expected a dict) logs and is
    skipped rather than killing a loop you meant to run for hours.
  * A "signal fired" is defined as compute_signal_fn(...) returning a dict
    whose "signal" key is truthy — matching the shape TennisLiveSignal and
    PlateAppearanceSignal already return from check_signal().

THIS REPO HAS NO LIVE DATA SOURCE WIRED IN. The fetch_* callables are yours
to implement against whatever book / scraper / feed you use — see the TODO
markers in the example fetchers at the bottom.
"""

import time
import traceback


def signal_fired(result) -> bool:
    """Default predicate for 'did a signal fire'. Matches the check_signal()
    result shape used by the tennis and baseball signal classes: a dict with a
    truthy 'signal' key."""
    return bool(result) and bool(result.get("signal"))


def run_monitor(fetch_state_fn, fetch_odds_fn, compute_signal_fn,
                poll_seconds: float = 5,
                on_signal=None,
                on_error=None,
                fired_predicate=signal_fired,
                max_polls: int = None,
                sleep_fn=time.sleep,
                should_continue=None):
    """Poll a live feed and fire a callback whenever a betting signal appears.

    Parameters
    ----------
    fetch_state_fn : callable() -> state
        Returns the current game state (score, count, serve %, whatever your
        compute_signal_fn needs). TODO: wire to your play-by-play feed.
    fetch_odds_fn : callable() -> odds
        Returns the current market odds. TODO: wire to your sportsbook API.
    compute_signal_fn : callable(state, odds) -> result_dict
        Combines state + odds into a signal result (e.g. a signal class's
        check_signal(...) output). Should return a dict; 'signal' truthy means
        a bet is indicated.
    poll_seconds : float
        Seconds to wait between poll cycles.
    on_signal : callable(result_dict) -> None
        Called ONLY when fired_predicate(result) is True. This is where you
        alert / place / log the bet. If None, the result is printed.
    on_error : callable(exception) -> None
        Called when a poll cycle raises. If None, the traceback is printed and
        the loop continues. Returning a truthy value from on_error stops the loop.
    fired_predicate : callable(result_dict) -> bool
        Decides whether a result counts as a fired signal. Defaults to the
        check_signal() shape ('signal' key truthy).
    max_polls : int or None
        Stop after this many poll cycles. None = run forever (the live default).
        Mainly for tests and dry runs.
    sleep_fn : callable(seconds) -> None
        Injectable sleep (tests pass a no-op). Defaults to time.sleep.
    should_continue : callable() -> bool or None
        Optional external kill switch checked at the top of each cycle; return
        False to stop the loop gracefully (e.g. match/game over).

    Returns
    -------
    int : the number of signals that fired during the run.
    """
    if on_signal is None:
        def on_signal(result):
            print(f"[SIGNAL] {result}")

    polls = 0
    signals = 0
    while True:
        if max_polls is not None and polls >= max_polls:
            break
        if should_continue is not None and not should_continue():
            break

        try:
            state = fetch_state_fn()
            odds = fetch_odds_fn()
            result = compute_signal_fn(state, odds)

            if fired_predicate(result):
                signals += 1
                on_signal(result)
            # else: no edge this tick — stay quiet, do not spam the callback.

        except Exception as exc:  # one bad feed response must not kill the loop
            if on_error is not None:
                if on_error(exc):
                    break
            else:
                print(f"[live_monitor] poll cycle failed, skipping tick: {exc}")
                traceback.print_exc()

        polls += 1

        # Don't sleep after the final poll of a bounded run.
        if max_polls is not None and polls >= max_polls:
            break
        sleep_fn(poll_seconds)

    return signals


# ---------------------------------------------------------------------------
# EXAMPLE WIRING — replace the TODO bodies with your real feed.
# ---------------------------------------------------------------------------
#
# The monitor is generic; here's how you'd hook it to the tennis signal class.
# Nothing below runs against a real source — it's a template.

def example_tennis_wiring():
    """Template showing how to point run_monitor at a TennisLiveSignal.

    Copy this, replace the TODO bodies, and call run_monitor(...) with the
    three closures it builds.
    """
    from tennis_signal import TennisLiveSignal

    sig = TennisLiveSignal("Player A", "Player B", best_of=3, edge_threshold=0.03)

    def fetch_state():
        # TODO: pull live score + rolling serve% from your play-by-play feed
        #       (e.g. an official data API, a scraper, or a websocket push).
        #       Return whatever compute_signal needs; here we mutate `sig` in
        #       place and return it.
        # sig.update_score(setsA=?, setsB=?, gamesA=?, gamesB=?, server='A')
        # sig.update_serve_stats(pA_pt=?, pB_pt=?)
        raise NotImplementedError("wire fetch_state() to your play-by-play feed")

    def fetch_odds():
        # TODO: pull the current two-way moneyline for this match from your
        #       sportsbook API / odds screen. Return American odds for A and B.
        # return {"odds_a": -140, "odds_b": +120}
        raise NotImplementedError("wire fetch_odds() to your sportsbook feed")

    def compute_signal(state, odds):
        # `state` is `sig` (already refreshed by fetch_state); `odds` is the
        # dict fetch_odds returned.
        return state.check_signal(odds["odds_a"], odds["odds_b"])

    def on_signal(result):
        # TODO: your alert / bet placement / logging goes here.
        print(f"FIRE: {result['signal']} — stake {result['kelly_stake_pct']}% "
              f"(edge A {result['edge_A']}, B {result['edge_B']})")

    return fetch_state, fetch_odds, compute_signal, on_signal


def example_baseball_wiring():
    """Template showing how to point run_monitor at a PlateAppearanceSignal."""
    from baseball_signal import PlateAppearanceSignal

    sig = PlateAppearanceSignal("Batter", "Pitcher", edge_threshold=0.03)

    def fetch_state():
        # TODO: pull live count, pitch velo vs pitcher avg, rolling matchup,
        #       handedness, and park from your feed, then refresh `sig`.
        # sig.set_count(balls=?, strikes=?)
        # sig.set_pitch_velo(current_velo=?, pitcher_avg_velo=?)
        # sig.set_batter_matchup(batter_woba_vs_pitch=?, batter_hand=?,
        #                        pitcher_hand=?, park_factor=?)
        raise NotImplementedError("wire fetch_state() to your Statcast/PBP feed")

    def fetch_odds():
        # TODO: pull the live "to hit a single this PA" two-way prop.
        # return {"odds_single": +260, "odds_no_single": -320}
        raise NotImplementedError("wire fetch_odds() to your sportsbook feed")

    def compute_signal(state, odds):
        return state.check_signal(odds["odds_single"], odds.get("odds_no_single"))

    def on_signal(result):
        # TODO: your alert / bet placement / logging goes here.
        print(f"FIRE: {result['signal']} — stake {result['kelly_stake_pct']}%")

    return fetch_state, fetch_odds, compute_signal, on_signal


if __name__ == "__main__":
    # Self-contained dry run with FAKE feeds so you can see the loop behave
    # without any live source. Odds drift until an edge appears, the callback
    # fires once, and a deliberately broken tick is swallowed by the try/except.
    from tennis_signal import TennisLiveSignal

    sig = TennisLiveSignal("A", "B", best_of=3, edge_threshold=0.03)
    sig.update_serve_stats(pA_pt=0.64, pB_pt=0.62)  # A slightly stronger
    sig.update_score(0, 0, 3, 3, 'A')               # tight set -> fair A ~0.58

    ticks = iter([
        {"odds_a": -160, "odds_b": +140},    # market already agrees -> no edge, stay quiet
        {"odds_a": None, "odds_b": +140},    # broken feed -> should be skipped
        {"odds_a": -110, "odds_b": -110},    # market lagging -> real edge -> FIRE
    ])

    def fetch_state():
        return sig

    def fetch_odds():
        return next(ticks)

    def compute_signal(state, odds):
        return state.check_signal(odds["odds_a"], odds["odds_b"])

    fired = run_monitor(
        fetch_state, fetch_odds, compute_signal,
        poll_seconds=0, max_polls=3, sleep_fn=lambda s: None,
    )
    print(f"\nDry run complete — {fired} signal(s) fired "
          f"(1 no-edge tick, 1 broken tick skipped, 1 fire).")
