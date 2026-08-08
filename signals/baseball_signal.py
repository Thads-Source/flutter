"""
baseball_signal.py — Per-plate-appearance P(single) logistic model plus a
refreshable live signal class, mirroring the shape of TennisLiveSignal.

WHAT IT PREDICTS: probability that the CURRENT plate appearance results in a
single (a two-way prop market: "batter records a single this PA" — yes/no).

MODEL: logistic regression on five features with sabermetrically-informed
default (prior) coefficients so it runs out of the box with no training data.
Call train_from_csv(path) to REPLACE those priors with coefficients fit to
real PA-level Statcast/Retrosheet data when you have it.

FEATURES (each centered so 0 == league-neutral):
  1. count_leverage   — hitter's counts (2-0, 3-1, 3-0) force the pitcher to
                        groove one; two-strike counts favor the pitcher. A
                        small wOBA-by-count table, centered at 0.
  2. velo_delta       — current pitch velo minus the pitcher's season average
                        for that pitch type (mph). Negative delta = fatigue =
                        contact quality up, so this gets a NEGATIVE coefficient.
  3. matchup_dev      — batter's rolling (30-day) wOBA vs the specific pitch
                        type about to be thrown, minus league-average wOBA.
                        The strongest single-PA signal; positive coefficient.
  4. park_dev         — singles park factor as a fraction above/below neutral
                        ((park_factor - 100)/100). Positive coefficient, small.
  5. platoon          — +1 batter has the handedness platoon advantage, -1 at
                        a disadvantage, 0 neutral. Small positive coefficient.

As with the tennis model: the math is only as good as the numbers you feed
it. Keep matchup_dev and velo_delta fed from rolling, current data — that is
where your edge over the book lives.
"""

import csv
import math

from devig import devig_two_way, devig_shin, kelly_fraction


# League-average anchors used to center the features. Adjust to the run
# environment / season if you like; they only shift what "neutral" means.
LEAGUE_AVG_WOBA = 0.320
BASE_SINGLE_RATE = 0.15  # singles per PA, league-wide, roughly

# ---- Default / prior coefficients (log-odds units) --------------------------
# Direction and magnitude are informed by public sabermetric results, not
# fit to any particular dataset. train_from_csv() REPLACES these wholesale.
#   intercept: logit(BASE_SINGLE_RATE) so a fully neutral PA ~= league rate.
DEFAULT_COEF = {
    "intercept": math.log(BASE_SINGLE_RATE / (1 - BASE_SINGLE_RATE)),  # ~ -1.7346
    "count_leverage": 2.0,   # feature ~[-0.14, +0.25]; a 2-0 count -> ~+0.24 logit
    "velo_delta": -0.06,     # per mph; -3 mph (tiring) -> +0.18 logit
    "matchup_dev": 3.0,      # per wOBA point of deviation; +0.100 -> +0.30 logit
    "park_dev": 0.8,         # per fractional dev; park 110 -> +0.10 -> +0.08 logit
    "platoon": 0.12,         # platoon advantage -> +0.12 logit
}

FEATURE_ORDER = ["count_leverage", "velo_delta", "matchup_dev", "park_dev", "platoon"]

# wOBA-by-count deviations from overall average (rough public-data priors),
# used as the count_leverage feature value. Positive == hitter's count.
COUNT_LEVERAGE_TABLE = {
    (3, 0): 0.25, (2, 0): 0.12, (3, 1): 0.17, (1, 0): 0.03,
    (0, 0): 0.00, (2, 1): 0.04, (3, 2): 0.05,
    (1, 1): -0.01, (0, 1): -0.04, (2, 2): -0.05,
    (1, 2): -0.10, (0, 2): -0.14,
}


def logistic(z: float) -> float:
    """Numerically stable logistic sigmoid."""
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def count_leverage(balls: int, strikes: int) -> float:
    """Centered wOBA-by-count value for the given count. Positive = hitter's count."""
    return COUNT_LEVERAGE_TABLE.get((balls, strikes), 0.0)


def build_feature_vector(count_lev: float, velo_delta: float, matchup_dev: float,
                         park_dev: float, platoon: float) -> dict:
    """Assemble the named feature vector the model scores. Kept as a dict so
    coefficients and features stay aligned by name, never by position."""
    return {
        "count_leverage": count_lev,
        "velo_delta": velo_delta,
        "matchup_dev": matchup_dev,
        "park_dev": park_dev,
        "platoon": platoon,
    }


def predict_prob(features: dict, coef: dict) -> float:
    """P(single) = sigmoid(intercept + sum(coef_i * feature_i))."""
    z = coef["intercept"]
    for name in FEATURE_ORDER:
        z += coef[name] * features.get(name, 0.0)
    return logistic(z)


def train_logistic(rows, feature_order=FEATURE_ORDER, lr=0.05, epochs=2000,
                   l2=1e-4):
    """Fit logistic-regression coefficients by batch gradient descent.

    `rows` is an iterable of (feature_dict, label) with label in {0, 1}.
    Returns a coef dict shaped like DEFAULT_COEF. Pure Python — no numpy — so
    it drops in anywhere, at the cost of speed on huge datasets.
    """
    data = [(f, float(y)) for f, y in rows]
    if not data:
        raise ValueError("no training rows provided")

    coef = {"intercept": 0.0}
    for name in feature_order:
        coef[name] = 0.0

    n = len(data)
    for _ in range(epochs):
        grad = {k: 0.0 for k in coef}
        for feats, y in data:
            pred = predict_prob(feats, coef)
            err = pred - y
            grad["intercept"] += err
            for name in feature_order:
                grad[name] += err * feats.get(name, 0.0)
        # Average gradient + L2 shrinkage (not on the intercept).
        coef["intercept"] -= lr * (grad["intercept"] / n)
        for name in feature_order:
            coef[name] -= lr * (grad[name] / n + l2 * coef[name])

    return coef


class PlateAppearanceSignal:
    """
    Refreshable live baseball signal generator for P(single) this plate
    appearance. Mirrors TennisLiveSignal: feed it live state as it arrives,
    call check_signal() whenever the odds tick — every call recomputes fresh
    off the current state, nothing stale carries over.
    """

    def __init__(self, batter: str, pitcher: str,
                 kelly_frac: float = 0.25, edge_threshold: float = 0.03,
                 use_shin: bool = False, coef: dict = None):
        self.batter = batter
        self.pitcher = pitcher
        self.kelly_frac = kelly_frac
        self.edge_threshold = edge_threshold
        self.use_shin = use_shin

        # Start from the priors; train_from_csv() replaces these in place.
        self.coef = dict(coef) if coef is not None else dict(DEFAULT_COEF)

        # Live state — all default to league-neutral until you set them.
        self.balls = 0
        self.strikes = 0
        self.velo_delta = 0.0
        self.matchup_dev = 0.0
        self.park_dev = 0.0
        self.platoon = 0

    # ---- refreshers (call as new live data arrives) ----

    def set_count(self, balls: int, strikes: int):
        """Update the current count (0-3 balls, 0-2 strikes)."""
        self.balls = balls
        self.strikes = strikes

    def set_pitch_velo(self, current_velo: float, pitcher_avg_velo: float):
        """Set the velo delta = current pitch velo - pitcher's season avg for
        this pitch type (mph). Negative (pitcher losing velo) helps the batter."""
        self.velo_delta = current_velo - pitcher_avg_velo

    def set_batter_matchup(self, batter_woba_vs_pitch: float,
                           batter_hand: str, pitcher_hand: str,
                           park_factor: float = 100.0):
        """Set the batter/pitch-type matchup, handedness platoon, and park.

        batter_woba_vs_pitch : batter's rolling (30-day) wOBA vs the pitch type
                               about to be thrown.
        batter_hand/pitcher_hand : 'L', 'R', or 'S' (switch). Switch hitters
                               always take the platoon advantage.
        park_factor          : singles park factor (100 = neutral).
        """
        self.matchup_dev = batter_woba_vs_pitch - LEAGUE_AVG_WOBA
        self.park_dev = (park_factor - 100.0) / 100.0
        self.platoon = self._platoon_value(batter_hand, pitcher_hand)

    @staticmethod
    def _platoon_value(batter_hand: str, pitcher_hand: str) -> int:
        b = (batter_hand or "").upper()
        p = (pitcher_hand or "").upper()
        if b == "S":
            return 1  # switch hitter bats to gain the advantage
        if not b or not p:
            return 0
        return 1 if b != p else -1  # opposite hands = platoon advantage

    # ---- query ----

    def _features(self) -> dict:
        return build_feature_vector(
            count_lev=count_leverage(self.balls, self.strikes),
            velo_delta=self.velo_delta,
            matchup_dev=self.matchup_dev,
            park_dev=self.park_dev,
            platoon=self.platoon,
        )

    def get_fair_prob(self) -> float:
        """Recompute P(single) RIGHT NOW from current state. Cheap, call anytime."""
        return predict_prob(self._features(), self.coef)

    def check_signal(self, live_odds: int, live_odds_no: int = None) -> dict:
        """Compare fair P(single) to live market odds. Call every odds tick.

        live_odds    : American odds for the SINGLE (yes) side.
        live_odds_no : American odds for the NO-single side. If given, the two
                       sides are de-vigged together (preferred). If omitted,
                       the raw implied prob of the single line is used and the
                       no-single side is taken as its complement.
        """
        from devig import american_to_prob

        fair_yes = self.get_fair_prob()
        fair_no = 1 - fair_yes

        if live_odds_no is not None:
            devig_fn = devig_shin if self.use_shin else devig_two_way
            market_yes, market_no = devig_fn(live_odds, live_odds_no)
        else:
            market_yes = american_to_prob(live_odds)
            market_no = 1 - market_yes

        edge_yes = fair_yes - market_yes
        edge_no = fair_no - market_no

        result = {
            "batter": self.batter, "pitcher": self.pitcher,
            "count": f"{self.balls}-{self.strikes}",
            "fair_prob_single": round(fair_yes, 4),
            "fair_prob_no_single": round(fair_no, 4),
            "market_implied_single": round(market_yes, 4),
            "market_implied_no_single": round(market_no, 4),
            "edge_single": round(edge_yes, 4),
            "edge_no_single": round(edge_no, 4),
            "signal": None, "kelly_stake_pct": 0.0,
        }

        if edge_yes >= self.edge_threshold:
            result["signal"] = f"BET {self.batter} SINGLE @ {live_odds}"
            result["kelly_stake_pct"] = round(
                kelly_fraction(fair_yes, live_odds, self.kelly_frac) * 100, 2)
        elif live_odds_no is not None and edge_no >= self.edge_threshold:
            result["signal"] = f"BET NO SINGLE @ {live_odds_no}"
            result["kelly_stake_pct"] = round(
                kelly_fraction(fair_no, live_odds_no, self.kelly_frac) * 100, 2)

        return result

    # ---- training ----

    def train_from_csv(self, path: str, lr: float = 0.05, epochs: int = 2000,
                       l2: float = 1e-4) -> dict:
        """Refit coefficients on real PA-level data and REPLACE the priors.

        Expected CSV columns (header row required), one row per plate
        appearance:
            balls, strikes, pitch_velo, pitcher_avg_velo,
            batter_woba_vs_pitch, batter_hand, pitcher_hand, park_factor,
            is_single
        `is_single` is the label (1 if the PA ended in a single, else 0).
        Missing park_factor defaults to 100 (neutral).

        Returns the fitted coef dict (also stored on self.coef).
        """
        rows = []
        with open(path, newline="") as fh:
            reader = csv.DictReader(fh)
            required = {"balls", "strikes", "pitch_velo", "pitcher_avg_velo",
                        "batter_woba_vs_pitch", "batter_hand", "pitcher_hand",
                        "is_single"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV missing required columns: {sorted(missing)}")

            for r in reader:
                balls = int(r["balls"])
                strikes = int(r["strikes"])
                velo_delta = float(r["pitch_velo"]) - float(r["pitcher_avg_velo"])
                matchup_dev = float(r["batter_woba_vs_pitch"]) - LEAGUE_AVG_WOBA
                park_factor = float(r.get("park_factor") or 100.0)
                park_dev = (park_factor - 100.0) / 100.0
                platoon = self._platoon_value(r["batter_hand"], r["pitcher_hand"])
                feats = build_feature_vector(
                    count_lev=count_leverage(balls, strikes),
                    velo_delta=velo_delta,
                    matchup_dev=matchup_dev,
                    park_dev=park_dev,
                    platoon=platoon,
                )
                rows.append((feats, int(r["is_single"])))

        fitted = train_logistic(rows, lr=lr, epochs=epochs, l2=l2)
        self.coef = fitted  # REPLACE the priors, do not merge
        return fitted


# ---------- DEMO / SANITY CHECKS ----------
if __name__ == "__main__":
    # Neutral PA -> fair prob near the league single rate.
    sig = PlateAppearanceSignal("Batter", "Pitcher")
    print(f"Neutral PA: P(single) = {sig.get_fair_prob():.4f}  (should be ~{BASE_SINGLE_RATE})")

    # Favorable spot: hitter's count, pitcher losing velo, good matchup, platoon edge.
    print("\n--- Favorable live spot ---")
    sig2 = PlateAppearanceSignal("Arraez", "Reliever", edge_threshold=0.03)
    sig2.set_count(balls=2, strikes=0)               # hitter's count
    sig2.set_pitch_velo(current_velo=91.0, pitcher_avg_velo=94.0)  # -3 mph, tiring
    sig2.set_batter_matchup(batter_woba_vs_pitch=0.400,           # elite vs this pitch
                            batter_hand="L", pitcher_hand="R",     # platoon edge
                            park_factor=104)                       # hitter-friendly
    print(f"Favorable PA: P(single) = {sig2.get_fair_prob():.4f}")

    signal = sig2.check_signal(live_odds=+260, live_odds_no=-320)
    for k, v in signal.items():
        print(f"  {k}: {v}")

    # Unfavorable: two-strike count, pitcher gaining velo, poor matchup.
    print("\n--- Unfavorable live spot ---")
    sig3 = PlateAppearanceSignal("WeakHitter", "Ace")
    sig3.set_count(balls=0, strikes=2)
    sig3.set_pitch_velo(current_velo=98.0, pitcher_avg_velo=96.0)
    sig3.set_batter_matchup(batter_woba_vs_pitch=0.250, batter_hand="R",
                            pitcher_hand="R", park_factor=96)
    print(f"Unfavorable PA: P(single) = {sig3.get_fair_prob():.4f}")
