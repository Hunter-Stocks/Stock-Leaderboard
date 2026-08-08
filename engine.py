"""Market Leadership engine v3 — matched to his observed behavior.

Pipeline:  high score -> Leaderboard (7+) -> 🌊 Wave -> 🟢 Green -> 🟡 -> 🔴

Semantics replicated from his boards and training:
- "Current" score is ABSOLUTE 1-10 (not a pure percentile): board entry at 7+,
  only a handful of names qualify (his boards: 1-15), corrections can empty it.
  Occasional bonus pushes a score above 10.
- Day counter is CUMULATIVE across the run (wave days + green days):
  SNOW 🌊3 Mon -> 🟢7 Fri. "Buy day 4-6" = first days of green.
- A name can join the board score-only, with no status (CRWD at 8.0);
  a wave is earned starting the second qualifying day.
- Wave can turn green on run-day 4 at the earliest.
- Yellow can be skipped (green -> red directly).
- Waves that stop qualifying vanish quietly (DDOG).
- Commodity names (Energy/Materials) appear but are flagged as not-traded.
- Board updates once daily after the close.

Calibration knobs are at the top — tune them against his live boards during beta.
"""
import numpy as np
import pandas as pd

NONE, WAVE, GREEN, YELLOW, RED = 0, 1, 2, 3, 4
EMOJI = {NONE: "", WAVE: "🌊", GREEN: "🟢", YELLOW: "🟡", RED: "🔴"}

# --- calibration knobs ---
BOARD_MIN = 7.0        # score to make the team (his: "score above 7")
GREEN_MIN_SCORE = 8.5  # score a wave needs to turn/stay green
HOLD_MIN_SCORE = 7.5   # ex-green grace zone (yellow) score floor
GREEN_MIN_RUN = 4      # earliest run-day a wave can turn green
YELLOW_MAX_DAYS = 10   # yellow longer than this -> red
RED_DISPLAY_DAYS = 5   # reds stay visible this many days
PCT_POWER = 12         # convexity of the percentile component
QUALITY_FLOOR = 0.2    # score floor multiplier when absolute quality is weak
MIN_HISTORY = 210


def compute_signals(close: pd.DataFrame):
    c = close
    ma50 = c.rolling(50).mean()
    ma200 = c.rolling(200).mean()
    hi52 = c.rolling(252, min_periods=MIN_HISTORY).max()
    lo52 = c.rolling(252, min_periods=MIN_HISTORY).min()
    r63, r126, r189, r252 = (c / c.shift(n) - 1 for n in (63, 126, 189, 252))
    rs_raw = 2 * r63 + r126 + r189 + r252
    trend = {
        "above50": c > ma50,
        "m50gt200": ma50 > ma200,
        "above200": c > ma200,
        "m200rising": ma200 > ma200.shift(20),
        "nearhigh": c >= 0.75 * hi52,
        "abovelow": c >= 1.30 * lo52,
    }
    return rs_raw, trend, hi52


def compute_scores(rs_raw, trend, close, hi52, valid):
    """Absolute-feeling 1-10 score:
    convex cross-sectional percentile x absolute quality blend.
    +1 bonus for elite setups (score can exceed 10)."""
    P = rs_raw.where(valid).rank(axis=1, pct=True)
    M = ((rs_raw - 0.5) / 2.0).clip(0, 1)                       # momentum strength
    T = sum(t.astype(float) for t in trend.values()) / len(trend)  # template fraction
    H = ((close / hi52 - 0.70) / 0.30).clip(0, 1)               # 52w-high proximity
    Q = 0.5 * M + 0.3 * T + 0.2 * H
    score = 10 * (P ** PCT_POWER) * (QUALITY_FLOOR + (1 - QUALITY_FLOOR) * Q)
    all_trend = np.logical_and.reduce([trend[k].values for k in trend])
    elite = (P >= 0.97) & pd.DataFrame(all_trend, index=P.index, columns=P.columns) \
            & (close >= 0.95 * hi52)
    return (score + elite.astype(float)).round(2).where(valid), P


def run_status_machine(scores: pd.DataFrame, pct: pd.DataFrame, trend: dict, valid: pd.DataFrame):
    """Returns status and display_days (cumulative run count for wave/green,
    days-in-status for yellow/red)."""
    SC = scores.values
    q_full = np.logical_and.reduce([trend[k].values for k in trend])   # full template
    core = trend["m50gt200"].values & trend["above200"].values & trend["m200rising"].values
    q_board = (SC >= BOARD_MIN)
    q_wave = q_board & core
    q_green = (SC >= GREEN_MIN_SCORE) & q_full
    q_hold = (SC >= HOLD_MIN_SCORE) & trend["above200"].values
    V = valid.values

    n_days, n_tk = SC.shape
    status = np.zeros((n_days, n_tk), dtype=np.int8)
    disp = np.zeros((n_days, n_tk), dtype=np.int16)
    prev = np.zeros(n_tk, dtype=np.int8)
    run = np.zeros(n_tk, dtype=np.int16)     # cumulative run days (wave+green+yellow)
    in_st = np.zeros(n_tk, dtype=np.int16)   # consecutive days in current status
    streak = np.zeros(n_tk, dtype=np.int16)  # consecutive days qualifying for a wave

    for i in range(n_days):
        for j in range(n_tk):
            st = prev[j]
            if not V[i, j] or np.isnan(SC[i, j]):
                prev[j] = NONE; run[j] = 0; in_st[j] = 0; streak[j] = 0
                continue
            streak[j] = streak[j] + 1 if q_wave[i, j] else 0
            if st in (NONE, RED):
                if streak[j] >= 2:            # day 1 on the board is status-less
                    new = WAVE; run[j] = 1
                else:
                    new = st
            elif st == WAVE:
                if q_wave[i, j] or q_green[i, j]:
                    run[j] += 1
                    new = GREEN if (q_green[i, j] and run[j] >= GREEN_MIN_RUN) else WAVE
                else:
                    new = NONE; run[j] = 0    # waves die quietly
            elif st == GREEN:
                run[j] += 1
                if q_green[i, j]:
                    new = GREEN
                elif q_hold[i, j]:
                    new = YELLOW
                else:
                    new = RED; run[j] = 0     # yellow can be skipped
            else:  # YELLOW
                run[j] += 1
                if q_green[i, j]:
                    new = GREEN               # recovery: counter kept counting
                elif q_hold[i, j] and in_st[j] < YELLOW_MAX_DAYS:
                    new = YELLOW
                else:
                    new = RED; run[j] = 0
            in_st[j] = in_st[j] + 1 if new == st else 1
            prev[j] = new
            status[i, j] = new
            disp[i, j] = run[j] if new in (WAVE, GREEN) else (in_st[j] if new in (YELLOW, RED) else 0)

    status = pd.DataFrame(status, index=scores.index, columns=scores.columns)
    disp = pd.DataFrame(disp, index=scores.index, columns=scores.columns)
    return status, disp


def build_board(day, status, disp, scores, names=None, sectors=None):
    """His daily leaderboard: score-only names at 7+, active statuses, reds briefly."""
    st, dy, sc = status.loc[day], disp.loc[day], scores.loc[day]
    rows = []
    for tk in status.columns:
        s = int(st[tk])
        val = sc[tk]
        if np.isnan(val):
            continue
        show = (s in (WAVE, GREEN, YELLOW)
                or (s == RED and dy[tk] <= RED_DISPLAY_DAYS)
                or (s == NONE and val >= BOARD_MIN))
        if not show:
            continue
        sector = (sectors or {}).get(tk, "")
        rows.append({
            "status": EMOJI[s],
            "days": int(dy[tk]) if s else "",
            "symbol": tk,
            "name": (names or {}).get(tk, ""),
            "score": round(float(val), 2),
            "commodity_flag": "⚠️ commodity — not traded"
                              if sector in ("Energy", "Materials") else "",
        })
    rows.sort(key=lambda r: -r["score"])
    return rows
