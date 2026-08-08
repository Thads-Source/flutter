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
| `odds_feed.py` | Pull DraftKings lines via The Odds API + push phone alerts (ntfy). Stdlib only. |
| `monitor_tennis_live.py` | End-to-end example: DK tennis odds → model → phone push on a fired edge. |

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

## Connecting a live odds feed (DraftKings via The Odds API) + phone alerts

There is **no way to plug into DraftKings directly** — DK has no public odds
API and no bet-placement API, and its Terms of Service prohibit scraping and
automated betting. The legitimate route is a licensed odds aggregator, **The
Odds API** (the-odds-api.com, free tier ~500 requests/month), which resells
DraftKings' posted lines. `odds_feed.py` reads those lines and pushes a phone
alert; **you place the bet yourself in the DraftKings app.**

```bash
export ODDS_API_KEY=your_free_key            # from the-odds-api.com
export NTFY_TOPIC=edge-signals-7f3a9c        # a secret string only you know
python3 monitor_tennis_live.py               # prints tennis sport_keys to pick
export ODDS_SPORT_KEY=tennis_atp_...         # pick one it printed
export PLAYER_A="Carlos Alcaraz" PLAYER_B="Jannik Sinner"
python3 monitor_tennis_live.py               # now it polls + alerts
```

Install the **ntfy** app (iOS/Android), Subscribe to your `NTFY_TOPIC`, and
alerts land on your phone. No account or purchase needed. (`notify_pushover`
is included as a fallback.)

Two honest limits of this setup:
- **Match state is still yours.** Odds APIs give prices, not the live score or
  the rolling serve% that is your actual edge. Keep the signal object current
  as you watch (see `update_from_your_feed` in the example).
- **Quota.** One odds fetch = 1 request; polling every 30s drains the free tier
  in ~4 hours. Use `POLL_SECONDS=90+` and only while your match is live —
  `client.remaining_requests` is printed after each poll.

> The **web app** (the hosted artifact) can't do any of this: its sandbox
> blocks all outbound network calls by design, so auto-odds only works in this
> Python version running on your own machine.

## What's intentionally not here

- No bet placement — impossible/against ToS on DraftKings; alerts only.
- No backtesting framework. Separate task if you want one.
- No per-PA "single" prop auto-fetch — that micro-market generally isn't
  exposed by odds APIs (or DK's API-less feed), so the baseball line stays
  manual entry in the app for now.

> Feed these models rolling, current, context-adjusted inputs. The math is only
> as good as the numbers you give it.
