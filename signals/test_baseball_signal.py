"""
Automated sanity tests for baseball_signal.py.

Run with:
    python3 test_baseball_signal.py     # plain asserts
    pytest test_baseball_signal.py      # if pytest is installed
"""

import math
import os
import random
import sys
import tempfile

from baseball_signal import (
    PlateAppearanceSignal,
    DEFAULT_COEF,
    BASE_SINGLE_RATE,
    count_leverage,
    predict_prob,
    build_feature_vector,
    logistic,
)


def test_neutral_pa_near_base_rate():
    """A fully neutral PA should predict ~ the league single rate."""
    sig = PlateAppearanceSignal("B", "P")
    p = sig.get_fair_prob()
    assert abs(p - BASE_SINGLE_RATE) < 1e-6, f"neutral PA should be ~{BASE_SINGLE_RATE}, got {p}"


def test_probabilities_valid_range():
    """Predictions stay in (0, 1) with no NaN across a feature sweep."""
    sig = PlateAppearanceSignal("B", "P")
    for balls in range(4):
        for strikes in range(3):
            for velo in (-5, 0, 5):
                for woba in (0.200, 0.320, 0.450):
                    sig.set_count(balls, strikes)
                    sig.set_pitch_velo(90 + velo, 90)
                    sig.set_batter_matchup(woba, "L", "R", park_factor=105)
                    p = sig.get_fair_prob()
                    assert not math.isnan(p), "NaN probability"
                    assert 0.0 < p < 1.0, f"prob out of range: {p}"


def test_hitters_count_raises_prob():
    """A hitter's count (2-0) should raise P(single) vs a two-strike count."""
    sig = PlateAppearanceSignal("B", "P")
    sig.set_count(2, 0)
    hi = sig.get_fair_prob()
    sig.set_count(0, 2)
    lo = sig.get_fair_prob()
    assert hi > lo, f"2-0 ({hi}) should beat 0-2 ({lo})"


def test_velo_drop_raises_prob():
    """Lower velo than the pitcher's average (fatigue) should raise P(single)."""
    sig = PlateAppearanceSignal("B", "P")
    sig.set_pitch_velo(94, 94)
    base = sig.get_fair_prob()
    sig.set_pitch_velo(91, 94)  # -3 mph
    tired = sig.get_fair_prob()
    assert tired > base, f"velo drop should raise prob: {tired} vs {base}"


def test_matchup_dominates():
    """Batter's rolling wOBA vs the pitch type is the strongest lever."""
    sig = PlateAppearanceSignal("B", "P")
    sig.set_batter_matchup(0.450, "L", "R")
    good = sig.get_fair_prob()
    sig.set_batter_matchup(0.250, "L", "R")
    bad = sig.get_fair_prob()
    assert good > bad, f"better matchup should raise prob: {good} vs {bad}"


def test_platoon_direction():
    """Opposite handedness (platoon advantage) beats same handedness; switch
    hitter always gets the advantage."""
    sig = PlateAppearanceSignal("B", "P")
    sig.set_batter_matchup(0.320, "L", "R")  # advantage
    adv = sig.get_fair_prob()
    sig.set_batter_matchup(0.320, "R", "R")  # disadvantage
    dis = sig.get_fair_prob()
    sig.set_batter_matchup(0.320, "S", "R")  # switch -> advantage
    switch = sig.get_fair_prob()
    assert adv > dis, f"platoon advantage should beat disadvantage: {adv} vs {dis}"
    assert abs(switch - adv) < 1e-9, "switch hitter should match the advantage case"


def test_kelly_and_edge_sane():
    """De-vig + Kelly must produce sane (non-negative, non-NaN) stakes and a
    fired signal when the model sees a real edge."""
    sig = PlateAppearanceSignal("Arraez", "Reliever", edge_threshold=0.03)
    sig.set_count(3, 1)
    sig.set_pitch_velo(90, 94)
    sig.set_batter_matchup(0.430, "L", "R", park_factor=106)
    res = sig.check_signal(live_odds=+320, live_odds_no=-420)
    assert not math.isnan(res["fair_prob_single"]), "NaN fair prob"
    assert res["kelly_stake_pct"] >= 0.0, "Kelly stake must be non-negative"
    # Sizeable model edge here should fire the single signal.
    assert res["signal"] is not None and "SINGLE" in res["signal"], f"expected a signal, got {res['signal']}"
    assert res["kelly_stake_pct"] > 0.0, "a fired signal should size a positive stake"


def test_check_signal_single_sided():
    """check_signal works with only the single-side line (no de-vig)."""
    sig = PlateAppearanceSignal("B", "P")
    res = sig.check_signal(live_odds=+500)  # only the yes side
    assert res["market_implied_single"] > 0.0
    assert abs(res["market_implied_single"] + res["market_implied_no_single"] - 1.0) < 1e-9


def _write_synthetic_csv(path, n=4000, seed=7):
    """Generate PA-level rows from a KNOWN logistic process so training can be
    checked against ground-truth coefficient directions."""
    rng = random.Random(seed)
    # Ground-truth model (log-odds).
    true = {"intercept": -1.6, "count_leverage": 2.5, "velo_delta": -0.08,
            "matchup_dev": 3.5, "park_dev": 1.0, "platoon": 0.2}
    header = ["balls", "strikes", "pitch_velo", "pitcher_avg_velo",
              "batter_woba_vs_pitch", "batter_hand", "pitcher_hand",
              "park_factor", "is_single"]
    with open(path, "w") as fh:
        fh.write(",".join(header) + "\n")
        counts = list(__import__("baseball_signal").COUNT_LEVERAGE_TABLE.keys())
        for _ in range(n):
            balls, strikes = rng.choice(counts)
            pitcher_avg = 93.0
            pitch_velo = pitcher_avg + rng.uniform(-4, 4)
            woba = round(rng.uniform(0.220, 0.440), 3)
            bhand = rng.choice(["L", "R"])
            phand = rng.choice(["L", "R"])
            park = rng.choice([95, 100, 100, 105, 110])
            platoon = 1 if bhand != phand else -1
            feats = build_feature_vector(
                count_lev=count_leverage(balls, strikes),
                velo_delta=pitch_velo - pitcher_avg,
                matchup_dev=woba - 0.320,
                park_dev=(park - 100) / 100.0,
                platoon=platoon,
            )
            p = predict_prob(feats, true)
            is_single = 1 if rng.random() < p else 0
            fh.write(f"{balls},{strikes},{pitch_velo:.2f},{pitcher_avg:.2f},"
                     f"{woba:.3f},{bhand},{phand},{park},{is_single}\n")


def test_train_from_csv_replaces_and_recovers():
    """train_from_csv must REPLACE the priors and recover the ground-truth
    coefficient SIGNS/direction from synthetic data."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.close()
    try:
        _write_synthetic_csv(tmp.name)
        sig = PlateAppearanceSignal("B", "P")
        before = dict(sig.coef)
        fitted = sig.train_from_csv(tmp.name, epochs=1500)

        # Coefficients were replaced, not left at the priors.
        assert sig.coef is fitted, "self.coef should be the fitted dict"
        assert fitted != before, "training should change the coefficients"

        # Directions recovered from the known generative process.
        assert fitted["count_leverage"] > 0, f"count_leverage sign wrong: {fitted['count_leverage']}"
        assert fitted["velo_delta"] < 0, f"velo_delta sign wrong: {fitted['velo_delta']}"
        assert fitted["matchup_dev"] > 0, f"matchup_dev sign wrong: {fitted['matchup_dev']}"
        assert fitted["platoon"] > 0, f"platoon sign wrong: {fitted['platoon']}"

        # Predictions remain valid probabilities after training.
        sig.set_count(2, 0)
        sig.set_pitch_velo(90, 93)
        sig.set_batter_matchup(0.420, "L", "R", 108)
        p = sig.get_fair_prob()
        assert 0.0 < p < 1.0, f"post-train prob out of range: {p}"
    finally:
        os.unlink(tmp.name)


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
