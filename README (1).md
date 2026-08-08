# Daily Momentum Scan

A small hobby project: scans ~1,000 large-cap US stocks every weekday after the
market close, ranks them by relative strength and trend quality (a classic
momentum methodology in the spirit of O'Neil / IBD relative-strength ratings),
and publishes a simple leaderboard.

**Today's board → [docs/leaderboard.md](docs/leaderboard.md)**

## How it works

- **Score (1–10):** weighted price momentum across 3–12 month windows,
  percentile-ranked across the scan universe and blended with absolute trend
  quality (moving-average structure, distance from 52-week high/low). A +1
  bonus marks elite setups, so scores can exceed 10.
- **Statuses:** 🌊 momentum building → 🟢 strong uptrend leader → 🟡 weakening →
  🔴 trend broken. The day counter is cumulative across a run.
- **Universe:** Russell 1000 + S&P 500 + a supplement of liquid growth names.
  Energy/Materials names are flagged.
- Runs via GitHub Actions every weekday after the US close; each day's board is
  archived under `docs/history/`.

## Files

`engine.py` (scoring + status logic) · `universe.py` (ticker sources) ·
`run_daily.py` (daily job) · `.github/workflows/leaderboard.yml` (schedule)

_Educational tool only. Nothing here is investment advice._
