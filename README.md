# Market Leadership Board — live replica

A transparent replica of the "market leader" leaderboard: score 1–10, statuses
Leaderboard → 🌊 Wave → 🟢 Green → 🟡 Weakening → 🔴 Broken, cumulative day counter.
Runs itself every weekday after US market close and publishes the board to this repo.

**Today's board → [docs/leaderboard.md](docs/leaderboard.md)** (bookmark it; checking takes seconds)

## One-time setup (~5 minutes, free)

1. Create a GitHub account if you don't have one, then create a new repository
   (private is fine), e.g. `leader-board`.
2. Upload every file in this folder to the repo, keeping the folder structure —
   the `.github/workflows/leaderboard.yml` path must be exact.
   (Easiest: on the repo page, "Add file → Upload files", drag the whole folder contents.)
3. Go to the repo's **Actions** tab → enable workflows → open **Daily leaderboard**
   → **Run workflow**. First run takes ~4 minutes. After that it runs itself
   every weekday at 5:45pm ET.

That's it. The board lives at `docs/leaderboard.md`, machine-readable at
`docs/leaderboard.json`, and every day is archived under `docs/history/` so his
boards can be compared against ours date-by-date.

## How the engine decides (all of it)

- **Score (1–10, absolute):** weighted momentum (`2×3mo + 6mo + 9mo + 12mo` returns)
  percentile-ranked, made steeply convex (12th power) and multiplied by an absolute
  quality blend (momentum strength, trend-template fraction, 52-week-high proximity).
  Result: only a handful of names score 7+, and in corrections none do — matching
  his boards. +1 elite bonus (how scores exceed 10).
- **Leaderboard entry:** score ≥ 7.0 — first day a name appears with no status symbol.
- **🌊 Wave:** earned from the 2nd consecutive qualifying day (score ≥ 7 with
  50-day avg > 200-day avg, price above a rising 200-day avg). Counter starts at 1.
- **🟢 Green:** from run-day 4 onward, if score ≥ 8.5 and the full template passes:
  price > 50 > 200-day avg, 200-day rising, within 25% of the 52-week high, ≥ 30%
  above the 52-week low. The counter is cumulative over the run (wave + green days).
- **🟡 Weakening:** an ex-green that slipped but still scores ≥ 7.5 above its 200-day
  avg (max 10 days' grace; yellow can be skipped entirely).
  **🔴 Broken:** everything else; shown 5 days, then drops off.
- **Commodity names** (Energy / Materials) are flagged — they can appear but are
  not traded, per his rule.
- Universe: S&P 500 + NASDAQ-100 (~550 liquid large caps).

## Calibration during beta

Exact thresholds/weights of his system are unknown — they can only be matched by
behavior. Compare `docs/history/<date>.json` against his posted boards daily and
tune the knobs at the top of `engine.py` (`GREEN_PCT`, `WAVE_PCT`, `BOARD_SCORE_MIN`,
`GREEN_MIN_RUN`) until the boards agree. Known open questions: his exact momentum
weights, yellow-recovery counter behavior, red display duration, and whether his
universe extends beyond large caps.

_Educational tool. Not investment advice._
