"""
Automated sanity tests for tennis_signal.py.

Run with either:
    python3 test_tennis_signal.py     # plain asserts, exits non-zero on failure
    pytest test_tennis_signal.py      # if pytest is installed

These are the checks called out in PLAN.md — verified by execution, not
eyeballed. The headline regression is that the formerly-recursive tiebreak
math no longer blows the stack on evenly-matched (close-probability) inputs.
"""

import sys

from tennis_signal import (
    prob_win_game,
    prob_win_tiebreak_from,
    prob_win_set_from,
    prob_win_match,
    TennisLiveSignal,
)


def _fair_from_00(pA_pt, pB_pt, best_of=3):
    sig = TennisLiveSignal("A", "B", best_of=best_of)
    sig.update_serve_stats(pA_pt=pA_pt, pB_pt=pB_pt)
    sig.update_score(0, 0, 0, 0, 'A')
    return sig.fair_prob_a()


def test_equal_players_50_50():
    """Two equal-skill players from 0-0 -> fair prob ~= 0.50 (within 0.005)."""
    fair = _fair_from_00(0.63, 0.63)
    assert abs(fair - 0.50) < 0.005, f"equal players should be ~0.50, got {fair}"


def test_dominant_server_favored():
    """One dominant server (p=0.90) vs weak (p=0.50) -> heavily favors dominant."""
    fair = _fair_from_00(0.90, 0.50)
    assert fair > 0.90, f"dominant server should be heavily favored, got {fair}"


def test_extreme_symmetric_no_recursion_error():
    """Both players p=0.50 exactly (max tie duration) must NOT throw
    RecursionError and must return ~= 0.50."""
    # Directly exercise the level that used to recurse without bound.
    tb = prob_win_tiebreak_from(0.50, 0.50, 0, 0, 'A', 7)
    assert abs(tb - 0.50) < 1e-9, f"symmetric tiebreak should be exactly 0.50, got {tb}"

    fair = _fair_from_00(0.50, 0.50)
    assert abs(fair - 0.50) < 0.005, f"symmetric match should be ~0.50, got {fair}"


def test_symmetric_tiebreak_all_servers():
    """Symmetric point-win% -> 0.50 tiebreak regardless of who serves first."""
    for fs in ('A', 'B'):
        tb = prob_win_tiebreak_from(0.61, 0.61, 0, 0, fs, 7)
        assert abs(tb - 0.50) < 1e-9, f"symmetric tiebreak (fs={fs}) should be 0.50, got {tb}"


def test_match_point_near_one():
    """Match-point scenario (one point from winning) -> prob near 1.0."""
    # Best-of-3: A up 1 set and 5-4 in games with A serving at 40-0 is not
    # directly expressible via the class (game-point granularity), so test the
    # near-certain macro states instead.

    # 40-0 on serve is triple game point: near-certain to hold, but a p=0.63
    # server can still be broken, so ~0.987 (not literally 1.0) is correct.
    game_ahead = prob_win_game_at(0.63, server_pts=3, returner_pts=0)
    assert game_ahead > 0.98, f"40-0 on serve should be ~1.0, got {game_ahead}"

    # Genuinely one point from the game with a strong server -> essentially 1.0.
    ace_machine = prob_win_game_at(0.90, server_pts=3, returner_pts=0)
    assert ace_machine > 0.999, f"40-0 for a 0.90 server should be ~1.0, got {ace_machine}"

    # A one set up in a best-of-3, serving 5-4: overwhelmingly ahead.
    sig = TennisLiveSignal("A", "B", best_of=3)
    sig.update_serve_stats(pA_pt=0.63, pB_pt=0.60)
    sig.update_score(setsA=1, setsB=0, gamesA=5, gamesB=4, server='A')
    fair = sig.fair_prob_a()
    assert fair > 0.95, f"a set up and serving 5-4 should be near-certain, got {fair}"

    # Match essentially over: A has clinched the deciding set score-wise.
    almost_won = prob_win_match(0.6, setsA=1, setsB=0, best_of=3)
    assert 0.0 < almost_won < 1.0, "sanity: mid-match prob strictly between 0 and 1"


def prob_win_game_at(p, server_pts, returner_pts):
    from tennis_signal import prob_win_game_from
    return prob_win_game_from(p, server_pts, returner_pts)


def test_probabilities_are_valid():
    """No NaN / out-of-range values across a sweep of inputs."""
    import math
    for pA in (0.50, 0.55, 0.62, 0.70, 0.85):
        for pB in (0.50, 0.55, 0.62, 0.70, 0.85):
            fair = _fair_from_00(pA, pB)
            assert not math.isnan(fair), f"NaN fair prob for {pA}/{pB}"
            assert 0.0 <= fair <= 1.0, f"fair prob out of range: {fair} for {pA}/{pB}"


def test_complementary_probabilities():
    """Swapping A and B should mirror the fair probability (sums to 1)."""
    fair_ab = _fair_from_00(0.66, 0.58)
    fair_ba = _fair_from_00(0.58, 0.66)
    assert abs((fair_ab + fair_ba) - 1.0) < 1e-6, f"probs should mirror: {fair_ab} + {fair_ba}"


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
        except Exception as e:  # e.g. RecursionError would surface here
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
