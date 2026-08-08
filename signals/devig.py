"""
devig.py — Convert American odds to fair (de-vigged) probabilities.
Also handles EV per dollar and fractional Kelly stake sizing.

This is the shared math layer every sport-specific signal file imports.
Nothing sport-specific lives here — pure odds math.
"""


def american_to_prob(odds: int) -> float:
    """Convert American odds to implied probability (INCLUDES the vig)."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)


def prob_to_american(prob: float) -> int:
    """Convert a probability back into fair American odds (no vig)."""
    if prob <= 0 or prob >= 1:
        raise ValueError("prob must be strictly between 0 and 1")
    if prob >= 0.5:
        return round(-100 * prob / (1 - prob))
    else:
        return round(100 * (1 - prob) / prob)


def devig_two_way(odds_a: int, odds_b: int) -> tuple:
    """
    Multiplicative de-vig for a 2-way market (tennis ML, PA single/no-single,
    any binary prop). Strips the juice proportionally.
    Returns (fair_prob_a, fair_prob_b) — these sum to exactly 1.0.
    """
    imp_a = american_to_prob(odds_a)
    imp_b = american_to_prob(odds_b)
    overround = imp_a + imp_b
    return imp_a / overround, imp_b / overround


def devig_shin(odds_a: int, odds_b: int, tol: float = 1e-8) -> tuple:
    """
    Shin's method — corrects for favorite-longshot bias, more accurate than
    multiplicative when odds are lopsided (heavy favorites). Use this over
    devig_two_way when one side is -300 or shorter.
    Solves for insider-trading parameter z via bisection.
    """
    imp_a = american_to_prob(odds_a)
    imp_b = american_to_prob(odds_b)

    def shin_probs(z):
        # Shin (1993) closed form for 2-outcome market
        a = ((z**2 + 4 * (1 - z) * imp_a**2 / (imp_a + imp_b)) ** 0.5 - z) / (2 * (1 - z))
        b = ((z**2 + 4 * (1 - z) * imp_b**2 / (imp_a + imp_b)) ** 0.5 - z) / (2 * (1 - z))
        return a, b

    lo, hi = 0.0, 0.2  # z rarely exceeds ~0.15 in real markets
    for _ in range(100):
        mid = (lo + hi) / 2
        a, b = shin_probs(mid)
        if abs((a + b) - 1.0) < tol:
            break
        if (a + b) > 1.0:
            lo = mid
        else:
            hi = mid
    a, b = shin_probs(mid)
    total = a + b
    return a / total, b / total


def edge(fair_prob: float, live_odds: int) -> float:
    """Your edge = fair_prob - implied_prob_from_live_odds. Positive = bet it."""
    implied = american_to_prob(live_odds)
    return fair_prob - implied


def ev_per_dollar(fair_prob: float, live_odds: int) -> float:
    """Expected value per $1 staked at given American odds."""
    payout = live_odds / 100 if live_odds > 0 else 100 / -live_odds
    return fair_prob * payout - (1 - fair_prob)


def kelly_fraction(fair_prob: float, live_odds: int, fraction: float = 0.25) -> float:
    """
    Fractional Kelly stake as a % of bankroll.
    fraction=0.25 = quarter Kelly — the move for live model-based betting.
    Full Kelly (fraction=1.0) will absolutely wreck you the second your
    model's probability estimate is off, which on live micro-markets it will be.
    """
    b = live_odds / 100 if live_odds > 0 else 100 / -live_odds
    q = 1 - fair_prob
    f_star = (b * fair_prob - q) / b
    return max(0.0, f_star * fraction)


if __name__ == "__main__":
    # quick sanity check
    a, b = devig_two_way(-140, +120)
    print(f"devig_two_way(-140, +120) -> fair A: {a:.4f}, fair B: {b:.4f}, sum: {a+b:.4f}")
    a2, b2 = devig_shin(-140, +120)
    print(f"devig_shin(-140, +120)    -> fair A: {a2:.4f}, fair B: {b2:.4f}, sum: {a2+b2:.4f}")
    print(f"EV per $1 at -140 if fair prob is {a:.4f}: {ev_per_dollar(a, -140):.4f}")
    print(f"Quarter Kelly stake %: {kelly_fraction(a, -140, 0.25)*100:.2f}%")
