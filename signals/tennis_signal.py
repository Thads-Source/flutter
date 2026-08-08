"""
tennis_signal.py — Point-by-point Markov model for live tennis win probability,
plus a refreshable live signal class you update every point/game and re-query
as often as you want (recompute is cheap, that's the whole point).

MODEL ASSUMPTION: each point is i.i.d. given who's serving (points don't
depend on match history/momentum beyond current serve %). This is the
standard assumption behind essentially every public tennis win-prob model —
Klaassen & Magnus found momentum effects exist but are small enough that
this holds up fine for live edge-finding purposes.

YOUR JOB: keep pA_pt / pB_pt fed with ROLLING, SURFACE-ADJUSTED serve win %
— not season average, not career average. That's where your edge over the
book actually lives. The math below is just correct math on top of whatever
numbers you feed it — garbage in, garbage out.

IMPLEMENTATION NOTE: every probability function is iterative bottom-up
dynamic programming, NOT top-down recursion. An earlier version recursed
naively over point states; a tiebreak (or deuce) between evenly matched
players stays tied for an unbounded number of points, and the "stay tied
forever" branch of the recursion tree has infinite depth, so it blew
Python's recursion limit (~1000) on close matchups — exactly the common
case for live edge-finding. The fix: the sudden-death "win by two from a
level score" tail has a closed form (same trick as the classic win-from-
deuce formula), so no state table ever needs to extend past a small fixed
size no matter how close the players are. No recursion, no lru_cache to
babysit during a long live session.
"""

from devig import devig_two_way, devig_shin, kelly_fraction


# ---------- GAME LEVEL ----------

def _game_resolve(p: float, sp: int, rp: int, p_from_deuce: float, table: dict) -> float:
    """Value of a game state, using the closed-form deuce tail for the
    win-by-two region and the DP table for everything below it."""
    if sp >= 4 and sp - rp >= 2:
        return 1.0
    if rp >= 4 and rp - sp >= 2:
        return 0.0
    if sp >= 3 and rp >= 3:
        # Deuce / advantage region — closed form, no recursion needed.
        diff = sp - rp
        if diff == 0:            # deuce
            return p_from_deuce
        elif diff == 1:          # server has advantage
            return p + (1 - p) * p_from_deuce
        else:                    # returner has advantage (diff == -1)
            return p * p_from_deuce
    return table[(sp, rp)]


def prob_win_game_from(p: float, server_pts: int, returner_pts: int) -> float:
    """Probability server wins the game from current point score (0,15,30,40 -> 0,1,2,3).

    p = P(server wins a random point). Iterative bottom-up DP over the
    non-deuce states (server_pts/returner_pts in 0..3); the deuce region is
    resolved with the closed form (p*p)/(p*p + q*q).
    """
    p = round(p, 6)
    q = 1 - p
    denom = p * p + q * q
    p_from_deuce = (p * p) / denom if denom > 0 else 0.5

    table = {}
    # Fill states in order of decreasing total points so every neighbour
    # (one point further along) is already known when we need it.
    for total in range(6, -1, -1):
        for sp in range(0, 4):
            rp = total - sp
            if rp < 0 or rp > 3:
                continue
            if sp >= 3 and rp >= 3:
                continue  # deuce region handled by closed form in _game_resolve
            win_pt = _game_resolve(p, sp + 1, rp, p_from_deuce, table)
            lose_pt = _game_resolve(p, sp, rp + 1, p_from_deuce, table)
            table[(sp, rp)] = p * win_pt + q * lose_pt

    return _game_resolve(p, server_pts, returner_pts, p_from_deuce, table)


def prob_win_game(p: float) -> float:
    """P(server wins game from 0-0) given p = P(server wins a random point)."""
    return prob_win_game_from(p, 0, 0)


# ---------- TIEBREAK LEVEL ----------

def _tiebreak_server_at(point_number: int, first_server: str) -> str:
    """Standard breaker serve order: pt1 = first_server, then alternate every 2."""
    if point_number == 1:
        return first_server
    other = 'B' if first_server == 'A' else 'A'
    idx = point_number - 2
    pair = idx // 2
    return other if pair % 2 == 0 else first_server


def _tiebreak_level_prob(pA: float, pB: float) -> float:
    """Closed form for P(A wins) from any LEVEL sudden-death score in a
    tiebreak (e.g. 6-6, 7-7, ...), i.e. "win by two from here".

    From a level score the next two points form one 'block'. Whatever the
    server order of that block (A-then-B or B-then-A), the probability A
    takes the block 2-0 is pA*(1-pB), the probability B takes it 0-2 is
    pB*(1-pA), and any split returns to a level score. So:

        W = pA*(1-pB) / (pA*(1-pB) + pB*(1-pA))

    exactly analogous to the win-from-deuce formula, and independent of who
    served first. This collapses the otherwise-unbounded tie extension into
    a single term.
    """
    a_takes = pA * (1 - pB)
    b_takes = pB * (1 - pA)
    denom = a_takes + b_takes
    return a_takes / denom if denom > 0 else 0.5


def _tiebreak_resolve(pA: float, pB: float, ptsA: int, ptsB: int,
                      first_server: str, target: int, W: float, table: dict) -> float:
    """Value of a tiebreak state, resolving terminal/level/advantage states
    with closed forms and reading the DP table for the rest."""
    if ptsA >= target and ptsA - ptsB >= 2:
        return 1.0
    if ptsB >= target and ptsB - ptsA >= 2:
        return 0.0
    if ptsA >= target - 1 and ptsB >= target - 1:
        # Sudden-death region (level or one-point advantage).
        if ptsA == ptsB:
            return W
        server = _tiebreak_server_at(ptsA + ptsB + 1, first_server)
        p_a_pt = pA if server == 'A' else (1 - pB)
        if ptsA > ptsB:  # A one point from winning; else back to level -> W
            return p_a_pt * 1.0 + (1 - p_a_pt) * W
        else:            # B one point from winning; else back to level -> W
            return p_a_pt * W + (1 - p_a_pt) * 0.0
    return table[(ptsA, ptsB)]


def prob_win_tiebreak_from(pA: float, pB: float, ptsA: int, ptsB: int,
                           first_server: str, target: int = 7) -> float:
    """P(player A wins tiebreak) from current score. pA/pB = point-win% on own serve.

    Iterative bottom-up DP over states below the sudden-death region; the
    level/advantage tail past (target-1, target-1) is closed form, so this
    never recurses and never blows the stack even for pA == pB.
    """
    W = _tiebreak_level_prob(pA, pB)
    table = {}
    for total in range(2 * (target - 1), -1, -1):
        for a in range(0, target):
            b = total - a
            if b < 0 or b > target - 1:
                continue
            if a >= target - 1 and b >= target - 1:
                continue  # sudden-death region handled by closed form
            server = _tiebreak_server_at(a + b + 1, first_server)
            p_a_pt = pA if server == 'A' else (1 - pB)
            win_pt = _tiebreak_resolve(pA, pB, a + 1, b, first_server, target, W, table)
            lose_pt = _tiebreak_resolve(pA, pB, a, b + 1, first_server, target, W, table)
            table[(a, b)] = p_a_pt * win_pt + (1 - p_a_pt) * lose_pt

    return _tiebreak_resolve(pA, pB, ptsA, ptsB, first_server, target, W, table)


# ---------- SET LEVEL ----------

def _set_resolve(pA_pt: float, pB_pt: float, gamesA: int, gamesB: int, server: str,
                 tb_first_A: float, tb_first_B: float, table: dict) -> float:
    """Value of a set state, resolving terminal and 6-6 (tiebreak) states
    with closed forms and reading the DP table for the rest."""
    if gamesA >= 6 and gamesA - gamesB >= 2:
        return 1.0
    if gamesB >= 6 and gamesB - gamesA >= 2:
        return 0.0
    if gamesA == 6 and gamesB == 6:
        # Whoever serves next serves the first tiebreak point.
        return tb_first_A if server == 'A' else tb_first_B
    return table[(gamesA, gamesB, server)]


def prob_win_set_from(pA_game: float, pB_game: float, pA_pt: float, pB_pt: float,
                      gamesA: int, gamesB: int, server: str) -> float:
    """P(A wins set) from current game score. server = who serves the CURRENT/next game.

    Iterative bottom-up DP over game states (0..6 each). Games only ever
    increase, so there was no stack-depth failure here, but keeping it
    iterative removes the last of the top-down recursion and the lru_cache.
    """
    tb_first_A = prob_win_tiebreak_from(pA_pt, pB_pt, 0, 0, 'A')
    tb_first_B = prob_win_tiebreak_from(pA_pt, pB_pt, 0, 0, 'B')

    table = {}
    # Reachable non-terminal game scores all have gamesA, gamesB in 0..6.
    for total in range(12, -1, -1):
        for gA in range(0, 7):
            gB = total - gA
            if gB < 0 or gB > 6:
                continue
            # Terminal / tiebreak states are resolved on the fly, not stored.
            if (gA >= 6 and gA - gB >= 2) or (gB >= 6 and gB - gA >= 2) or (gA == 6 and gB == 6):
                continue
            for srv in ('A', 'B'):
                if srv == 'A':
                    hold = pA_game
                    v_hold = _set_resolve(pA_pt, pB_pt, gA + 1, gB, 'B', tb_first_A, tb_first_B, table)
                    v_break = _set_resolve(pA_pt, pB_pt, gA, gB + 1, 'B', tb_first_A, tb_first_B, table)
                    table[(gA, gB, srv)] = hold * v_hold + (1 - hold) * v_break
                else:
                    # A wins this game by breaking B's serve, prob (1 - pB_game).
                    v_break = _set_resolve(pA_pt, pB_pt, gA + 1, gB, 'A', tb_first_A, tb_first_B, table)
                    v_hold = _set_resolve(pA_pt, pB_pt, gA, gB + 1, 'A', tb_first_A, tb_first_B, table)
                    table[(gA, gB, srv)] = (1 - pB_game) * v_break + pB_game * v_hold

    return _set_resolve(pA_pt, pB_pt, gamesA, gamesB, server, tb_first_A, tb_first_B, table)


# ---------- MATCH LEVEL ----------

def prob_win_match(set_win_prob_A: float, setsA: int, setsB: int, best_of: int = 3) -> float:
    """P(A wins match) from current set score, given A's per-set win prob.

    Iterative bottom-up DP over set states. Trivially shallow (best-of-5 at
    most), but kept iterative for consistency with the rest of the module.
    """
    sets_needed = (best_of // 2) + 1
    p = round(set_win_prob_A, 6)

    table = {}
    for total in range(2 * sets_needed, -1, -1):
        for a in range(0, sets_needed + 1):
            b = total - a
            if b < 0 or b > sets_needed:
                continue
            if a == sets_needed:
                table[(a, b)] = 1.0
            elif b == sets_needed:
                table[(a, b)] = 0.0
            else:
                table[(a, b)] = p * table[(a + 1, b)] + (1 - p) * table[(a, b + 1)]

    return table[(setsA, setsB)]


def clear_caches():
    """Retained for backward compatibility. The probability functions are now
    pure iterative DP with no module-level cache to clear, so this is a no-op —
    there is no unbounded lru_cache to manage during a long live session."""
    pass


# ---------- LIVE REFRESHABLE CLASS ----------

class TennisLiveSignal:
    """
    Refreshable live tennis signal generator.
    Update serve stats / score whenever new data comes in, call check_signal()
    whenever new odds tick — every call recomputes fresh off current state,
    nothing stale carries over.
    """

    def __init__(self, player_a: str, player_b: str, best_of: int = 3,
                 kelly_frac: float = 0.25, edge_threshold: float = 0.03,
                 use_shin: bool = False):
        self.player_a = player_a
        self.player_b = player_b
        self.best_of = best_of
        self.kelly_frac = kelly_frac
        self.edge_threshold = edge_threshold
        self.use_shin = use_shin

        self.setsA = 0
        self.setsB = 0
        self.gamesA = 0
        self.gamesB = 0
        self.server = 'A'

        # REFRESH THESE from your rolling/surface-adjusted data feed
        self.pA_pt = 0.62
        self.pB_pt = 0.60

    def update_serve_stats(self, pA_pt: float, pB_pt: float):
        """Call whenever you get fresh rolling serve % (e.g. every few games,
        or the moment you notice a velo/first-serve% drop live)."""
        self.pA_pt = pA_pt
        self.pB_pt = pB_pt

    def update_score(self, setsA: int, setsB: int, gamesA: int, gamesB: int, server: str):
        """Call after every game completes from your live play-by-play feed."""
        self.setsA, self.setsB = setsA, setsB
        self.gamesA, self.gamesB = gamesA, gamesB
        self.server = server

    def fair_prob_a(self) -> float:
        """Recompute A's fair match win prob RIGHT NOW from current state. Cheap, call anytime."""
        pA_game = prob_win_game(self.pA_pt)
        pB_game = prob_win_game(self.pB_pt)
        set_win_prob_A = prob_win_set_from(
            round(pA_game, 6), round(pB_game, 6),
            round(self.pA_pt, 6), round(self.pB_pt, 6),
            self.gamesA, self.gamesB, self.server
        )
        return prob_win_match(set_win_prob_A, self.setsA, self.setsB, self.best_of)

    def check_signal(self, live_odds_a: int, live_odds_b: int) -> dict:
        """Compare fair prob to live market odds. Call every time odds tick."""
        fair_a = self.fair_prob_a()
        fair_b = 1 - fair_a

        devig_fn = devig_shin if self.use_shin else devig_two_way
        market_fair_a, market_fair_b = devig_fn(live_odds_a, live_odds_b)

        edge_a = fair_a - market_fair_a
        edge_b = fair_b - market_fair_b

        result = {
            "player_a": self.player_a, "player_b": self.player_b,
            "score": f"sets {self.setsA}-{self.setsB}, games {self.gamesA}-{self.gamesB}, serving: {self.server}",
            "fair_prob_A": round(fair_a, 4), "fair_prob_B": round(fair_b, 4),
            "market_implied_A": round(market_fair_a, 4), "market_implied_B": round(market_fair_b, 4),
            "edge_A": round(edge_a, 4), "edge_B": round(edge_b, 4),
            "signal": None, "kelly_stake_pct": 0.0,
        }

        if edge_a >= self.edge_threshold:
            result["signal"] = f"BET {self.player_a} @ {live_odds_a}"
            result["kelly_stake_pct"] = round(kelly_fraction(fair_a, live_odds_a, self.kelly_frac) * 100, 2)
        elif edge_b >= self.edge_threshold:
            result["signal"] = f"BET {self.player_b} @ {live_odds_b}"
            result["kelly_stake_pct"] = round(kelly_fraction(fair_b, live_odds_b, self.kelly_frac) * 100, 2)

        return result


# ---------- DEMO / SANITY CHECKS ----------
if __name__ == "__main__":
    # Sanity check 1: equal servers, 0-0, best of 3 -> should be ~50/50
    sig = TennisLiveSignal("A", "B", best_of=3)
    sig.update_serve_stats(pA_pt=0.63, pB_pt=0.63)
    sig.update_score(0, 0, 0, 0, 'A')
    print(f"Equal players, 0-0: fair A = {sig.fair_prob_a():.4f}  (should be ~0.50)")

    # Sanity check 2: better server should be favored even from 0-0
    sig2 = TennisLiveSignal("A", "B", best_of=3)
    sig2.update_serve_stats(pA_pt=0.68, pB_pt=0.58)
    sig2.update_score(0, 0, 0, 0, 'A')
    print(f"A has better serve, 0-0: fair A = {sig2.fair_prob_a():.4f}  (should be > 0.50)")

    # Real scenario: A up a set, 3-2 in set 2, B's serve % dropping (fatigue tell)
    print("\n--- Live scenario ---")
    sig3 = TennisLiveSignal("Alcaraz", "Sinner", best_of=3, edge_threshold=0.03)
    sig3.update_serve_stats(pA_pt=0.64, pB_pt=0.58)  # Sinner's serve dropping
    sig3.update_score(setsA=1, setsB=0, gamesA=3, gamesB=2, server='A')
    print(f"Score: {sig3.setsA}-{sig3.setsB} sets, {sig3.gamesA}-{sig3.gamesB} games, {sig3.player_a} serving")
    print(f"Fair prob {sig3.player_a}: {sig3.fair_prob_a():.4f}")

    signal = sig3.check_signal(live_odds_a=-140, live_odds_b=+120)
    for k, v in signal.items():
        print(f"  {k}: {v}")
