# Live Betting Signal Stack

Live in-play fair-probability signal generators for two sports, compared
against de-vigged market odds. A signal fires when
`fair_prob - market_implied_prob >= edge_threshold`. Everything is cheap to
recompute on every new tick (point, pitch, or odds change) — no state reload.

## Modules

| File | What it is |
| --- | --- |
| `devig.py` | Shared odds math: American ↔ probability, multiplicative + Shin de-vig, EV/\$, fractional Kelly. |
| `tennis_signal.py` | Point-by-point Markov win probability + `TennisLiveSignal`. |
| `baseball_signal.py` | Per-plate-appearance logistic P(single) + `PlateAppearanceSignal`. |
| `live_monitor.py` | Generic, sport-agnostic polling loop. |

## Running

```bash
python3 tennis_signal.py      # tennis demo
python3 baseball_signal.py    # baseball demo
python3 live_monitor.py       # monitor dry run against fake feeds
python3 run_tests.py          # all sanity suites + integration check
```

The tests use plain `assert`s and exit non-zero on failure, so they also run
under `pytest` if you have it. No third-party dependencies — stdlib only.

## The recursion fix (tennis)

The tiebreak/deuce win-probability used to be naive top-down recursion. Between
evenly matched players a tiebreak can stay tied for an unbounded number of
points, and the "stay tied forever" branch of the recursion tree has infinite
depth, so it hit Python's recursion limit and raised `RecursionError` on the
common close-matchup case (e.g. symmetric 0.63/0.63).

All probability functions are now **iterative bottom-up dynamic programming**.
The unbounded sudden-death tail ("win by two from a level score") is collapsed
with a closed form — the same trick as the classic win-from-deuce formula:

```
W = pA·(1-pB) / (pA·(1-pB) + pB·(1-pA))
```

so no state table ever extends past a small fixed size regardless of how close
the players are. No recursion, no `lru_cache` to babysit during a long session.
The closed forms are cross-checked against Monte Carlo simulation in the tests.

## Baseball model

Logistic regression on five sabermetrically-informed features (count leverage,
pitch-velo delta vs the pitcher's season average, batter's rolling wOBA vs the
pitch type, singles park factor, handedness platoon). It ships with **default
prior coefficients so it runs out of the box** with no training data. Call
`PlateAppearanceSignal.train_from_csv(path)` to **replace** those priors with
coefficients fit to real PA-level Statcast/Retrosheet data.

## What's intentionally not here

- No live odds API integration — wire your own feed into `live_monitor.py`'s
  `fetch_state_fn` / `fetch_odds_fn` (see the TODO markers).
- No backtesting framework, no UI. This is a library, not an app.

> Feed these models rolling, current, context-adjusted inputs. The math is only
> as good as the numbers you give it.
