"""Daily job: pull ~21 months of adjusted daily closes for the universe,
compute scores + statuses, publish docs/leaderboard.md + .json + history."""
import json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from engine import (compute_signals, compute_scores, run_status_machine,
                    build_board, MIN_HISTORY)
from universe import get_universe

OUT = Path("docs")
(OUT / "history").mkdir(parents=True, exist_ok=True)

tickers, names, sectors = get_universe()
print(f"universe: {len(tickers)} tickers")

data = yf.download(tickers, period="21mo", interval="1d",
                   auto_adjust=True, group_by="column", threads=True, progress=False)
close = data["Close"].dropna(axis=1, how="all")
print(f"panel: {close.shape}")

# hygiene: drop garbage bars (bad ticks) and thin histories
med = close.rolling(21, min_periods=5).median()
ratio = close / med
close = close.mask((ratio > 4) | (ratio < 0.25) | (close <= 0.02))
enough = close.notna().sum() >= MIN_HISTORY
close = close.loc[:, enough]

rs_raw, trend, hi52 = compute_signals(close)
valid = close.notna() & rs_raw.notna()
pct = rs_raw.where(valid).rank(axis=1, pct=True)
scores = compute_scores(pct, trend, close, hi52)
status, disp = run_status_machine(pct, trend, valid)

day = status.index[-1]
board = build_board(day, status, disp, scores, names, sectors)
datestr = day.strftime("%Y-%m-%d")

# ---- write outputs ----
json.dump({"date": datestr, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "board": board},
          open(OUT / "leaderboard.json", "w"), indent=1)
json.dump({"date": datestr, "board": board},
          open(OUT / "history" / f"{datestr}.json", "w"), indent=1)

greens = sum(1 for r in board if r["status"] == "🟢")
lines = [f"# Market Leadership Board — {datestr}", "",
         f"_{greens} green leader(s) · {len(board)} names on the board · updates weekdays after close_", "",
         "| Status | Symbol | Name | Score | Note |",
         "|---|---|---|---|---|"]
for r in board:
    st = f"{r['status']} {r['days']}".strip()
    lines.append(f"| {st} | **{r['symbol']}** | {r['name']} | {r['score']} | {r['commodity_flag']} |")
lines += ["", "Legend: 🌊 momentum building · 🟢 market leader · 🟡 leadership weakening · 🔴 leadership broken.",
          "Day count is cumulative over the run (wave + green). Score = relative-strength percentile × 10 (+1 elite bonus).",
          "", "_Educational output, not investment advice._"]
(OUT / "leaderboard.md").write_text("\n".join(lines))
print(f"published board for {datestr}: {len(board)} rows, {greens} green")
