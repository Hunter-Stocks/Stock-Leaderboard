"""Universe: closest replica of "scans thousands of US stocks".

Layer 1: Russell 1000 members via iShares IWB daily holdings CSV (~1,000 large caps)
Layer 2: S&P 500 + NASDAQ-100 from Wikipedia (adds GICS sectors; fallback)
Layer 3: hardcoded supplement of liquid growth names that live outside the S&P 500
         (guarantees SNOW / NET / etc. are always scanned)
Each layer is best-effort; failures are logged, never fatal.
"""
from io import StringIO

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) leaderboard-research"}
IWB_CSV = ("https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/"
           "1467271812596.ajax?fileType=csv&fileName=IWB_holdings&dataType=fund")
WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX = "https://en.wikipedia.org/wiki/Nasdaq-100"

SUPPLEMENT = {  # large liquid names often outside the S&P 500
    "SNOW": ("Snowflake Inc.", "Information Technology"),
    "NET": ("Cloudflare Inc.", "Information Technology"),
    "MDB": ("MongoDB Inc.", "Information Technology"),
    "TEAM": ("Atlassian Corp.", "Information Technology"),
    "ZS": ("Zscaler Inc.", "Information Technology"),
    "OKTA": ("Okta Inc.", "Information Technology"),
    "HUBS": ("HubSpot Inc.", "Information Technology"),
    "VEEV": ("Veeva Systems", "Health Care"),
    "TOST": ("Toast Inc.", "Information Technology"),
    "GTLB": ("GitLab Inc.", "Information Technology"),
    "IOT": ("Samsara Inc.", "Information Technology"),
    "CVNA": ("Carvana Co.", "Consumer Discretionary"),
    "APP": ("AppLovin Corp.", "Information Technology"),
    "HOOD": ("Robinhood Markets", "Financials"),
    "SOFI": ("SoFi Technologies", "Financials"),
    "RBLX": ("Roblox Corp.", "Communication Services"),
    "COIN": ("Coinbase Global", "Financials"),
    "PLTR": ("Palantir Technologies", "Information Technology"),
}


def _clean_ticker(t):
    t = str(t).strip().upper().replace(".", "-").replace(" ", "")
    return t if t.isascii() and 0 < len(t) <= 6 and t not in ("--", "-") else None


def _russell1000(names, sectors):
    r = requests.get(IWB_CSV, headers=HEADERS, timeout=60)
    r.raise_for_status()
    text = r.text
    # iShares CSVs carry ~9 preamble lines; find the real header row
    lines = text.splitlines()
    hdr = next(i for i, l in enumerate(lines) if l.startswith("Ticker,"))
    df = pd.read_csv(StringIO("\n".join(lines[hdr:])))
    if "Asset Class" in df.columns:
        df = df[df["Asset Class"].astype(str).str.strip() == "Equity"]
    added = 0
    for _, row in df.iterrows():
        tk = _clean_ticker(row.get("Ticker"))
        if not tk:
            continue
        names.setdefault(tk, str(row.get("Name", "")).title())
        sec = str(row.get("Sector", "")).strip()
        if sec and sec.lower() != "nan":
            sectors.setdefault(tk, sec)
        added += 1
    print(f"universe layer 1 (Russell 1000): {added} rows")


def _wiki_tables(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.read_html(StringIO(r.text))


def _sp500_ndx(names, sectors):
    sp = _wiki_tables(WIKI_SP500)[0]
    for _, row in sp.iterrows():
        tk = _clean_ticker(row["Symbol"])
        if tk:
            names.setdefault(tk, str(row["Security"]))
            sectors[tk] = str(row["GICS Sector"])  # GICS overrides layer-1 sector
    print(f"universe layer 2a (S&P 500): {len(sp)} rows")
    ndx = None
    for t in _wiki_tables(WIKI_NDX):
        cols = [str(c).strip().lower() for c in t.columns]
        if any(c in ("ticker", "symbol", "ticker symbol") for c in cols) and len(t) > 50:
            ndx = t
            break
    if ndx is None:
        print("universe layer 2b (NASDAQ-100): table not found — skipped")
        return
    cmap = {str(c).strip().lower(): c for c in ndx.columns}
    tcol = cmap.get("ticker") or cmap.get("symbol") or cmap.get("ticker symbol")
    ncol = next((c for c in ndx.columns if "ompany" in str(c)), tcol)
    scol = next((c for c in ndx.columns if "ector" in str(c)), None)
    for _, row in ndx.iterrows():
        tk = _clean_ticker(row[tcol])
        if tk:
            names.setdefault(tk, str(row[ncol]))
            if scol:
                sectors.setdefault(tk, str(row[scol]))
    print(f"universe layer 2b (NASDAQ-100): {len(ndx)} rows")


def get_universe():
    names, sectors = {}, {}
    for layer, fn in [("Russell 1000", _russell1000), ("S&P500+NDX", _sp500_ndx)]:
        try:
            fn(names, sectors)
        except Exception as e:
            print(f"universe layer '{layer}' FAILED: {type(e).__name__}: {e}")
    for tk, (nm, sec) in SUPPLEMENT.items():
        names.setdefault(tk, nm)
        sectors.setdefault(tk, sec)
    tickers = sorted(names)
    print(f"universe total: {len(tickers)} tickers")
    if len(tickers) < 400:
        raise RuntimeError(f"universe too small ({len(tickers)}) — all sources failed")
    return tickers, names, sectors
