"""Universe: S&P 500 + NASDAQ-100 tickers, names, and GICS sectors (Wikipedia)."""
from io import StringIO

import pandas as pd
import requests

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX = "https://en.wikipedia.org/wiki/Nasdaq-100"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) leaderboard-research"}


def _tables(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.read_html(StringIO(r.text))


def get_universe():
    sp = _tables(WIKI_SP500)[0]
    sp_t = sp["Symbol"].str.replace(".", "-", regex=False)
    names = dict(zip(sp_t, sp["Security"]))
    sectors = dict(zip(sp_t, sp["GICS Sector"]))

    ndx = None
    for t in _tables(WIKI_NDX):
        cols = [str(c).lower() for c in t.columns]
        if any(("ticker" in c) or ("symbol" in c) for c in cols) and len(t) > 80:
            ndx = t
            break
    if ndx is not None:
        tcol = [c for c in ndx.columns if "icker" in str(c) or "ymbol" in str(c)][0]
        ncol = [c for c in ndx.columns if "ompany" in str(c)] or [tcol]
        scol = [c for c in ndx.columns if "ector" in str(c)]
        nd_t = ndx[tcol].str.replace(".", "-", regex=False)
        for i, tk in enumerate(nd_t):
            names.setdefault(tk, str(ndx[ncol[0]].iloc[i]))
            if scol:
                sectors.setdefault(tk, str(ndx[scol[0]].iloc[i]))

    tickers = sorted(names)
    return tickers, names, sectors
