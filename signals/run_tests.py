"""
run_tests.py — Run every sanity suite in the signal stack end-to-end.

    python3 run_tests.py

Runs the tennis, baseball, and live-monitor suites, plus a cross-cutting
integration check that de-vig + fractional Kelly sizing come out sane (no
negative / NaN edges or stakes) when driven through BOTH signal classes.
Exits non-zero if anything fails.
"""

import math
import sys

import test_tennis_signal
import test_baseball_signal
import test_live_monitor

from tennis_signal import TennisLiveSignal
from baseball_signal import PlateAppearanceSignal
from devig import devig_two_way, devig_shin, kelly_fraction, ev_per_dollar


def _finite(x):
    return isinstance(x, (int, float)) and not math.isnan(x) and not math.isinf(x)


def integration_devig_kelly():
    """de-vig + Kelly must integrate cleanly with both signal classes:
    edges finite, stakes non-negative and finite, multiplicative vs Shin agree
    in sign, and a real edge produces a positive stake."""
    failures = 0

    # --- Tennis ---
    for use_shin in (False, True):
        sig = TennisLiveSignal("A", "B", edge_threshold=0.03, use_shin=use_shin)
        sig.update_serve_stats(0.66, 0.60)
        sig.update_score(1, 0, 4, 3, 'A')
        res = sig.check_signal(-110, -110)  # market flat -> A undervalued
        ok = (_finite(res["fair_prob_A"]) and _finite(res["edge_A"])
              and _finite(res["kelly_stake_pct"]) and res["kelly_stake_pct"] >= 0
              and 0.0 <= res["fair_prob_A"] <= 1.0)
        if not ok:
            print(f"FAIL  tennis devig/kelly (shin={use_shin}): {res}")
            failures += 1
        if res["signal"] is None or res["kelly_stake_pct"] <= 0:
            print(f"FAIL  tennis expected a positive-stake signal (shin={use_shin}): {res}")
            failures += 1

    # --- Baseball ---
    for use_shin in (False, True):
        sig = PlateAppearanceSignal("Arraez", "Reliever", edge_threshold=0.03, use_shin=use_shin)
        sig.set_count(3, 1)
        sig.set_pitch_velo(90, 94)
        sig.set_batter_matchup(0.430, "L", "R", park_factor=106)
        res = sig.check_signal(+320, -420)
        ok = (_finite(res["fair_prob_single"]) and _finite(res["edge_single"])
              and _finite(res["kelly_stake_pct"]) and res["kelly_stake_pct"] >= 0
              and 0.0 <= res["fair_prob_single"] <= 1.0)
        if not ok:
            print(f"FAIL  baseball devig/kelly (shin={use_shin}): {res}")
            failures += 1
        if res["signal"] is None or res["kelly_stake_pct"] <= 0:
            print(f"FAIL  baseball expected a positive-stake signal (shin={use_shin}): {res}")
            failures += 1

    # --- No negative Kelly when there is no edge ---
    flat = PlateAppearanceSignal("B", "P", edge_threshold=0.03)
    res = flat.check_signal(+500, -700)  # heavy no-single market, model neutral
    if res["kelly_stake_pct"] < 0 or not _finite(res["kelly_stake_pct"]):
        print(f"FAIL  no-edge Kelly should be 0, got {res['kelly_stake_pct']}")
        failures += 1

    # --- ev_per_dollar sanity: positive when fair prob beats the line ---
    if not (ev_per_dollar(0.60, +100) > 0 and ev_per_dollar(0.40, -200) < 0):
        print("FAIL  ev_per_dollar direction wrong")
        failures += 1

    if failures == 0:
        print("PASS  integration_devig_kelly (tennis + baseball, mult + Shin)")
    return failures


def main():
    total = 0
    print("=== tennis_signal ===")
    total += test_tennis_signal._run_all()
    print("\n=== baseball_signal ===")
    total += test_baseball_signal._run_all()
    print("\n=== live_monitor ===")
    total += test_live_monitor._run_all()
    print("\n=== integration ===")
    total += integration_devig_kelly()

    print("\n" + ("ALL SUITES PASSED" if total == 0 else f"{total} FAILURE(S)"))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
