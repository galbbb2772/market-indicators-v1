#!/usr/bin/env python3
"""Fetch direct US index closes from Yahoo Finance for a research chart.

Uses the index symbols themselves, not ETF proxies:
  ^GSPC = S&P 500
  ^IXIC = NASDAQ Composite
  ^DJI  = Dow Jones Industrial Average
"""
from __future__ import annotations
import argparse
from datetime import date, timedelta
from pathlib import Path
import time
import pandas as pd
import yfinance as yf

TICKERS = {"^GSPC": "SP500", "^IXIC": "NASDAQ_COMPOSITE", "^DJI": "DJIA"}

def fetch_one(ticker: str, start: str, end: str) -> pd.Series:
    last_error = None
    for attempt in range(5):
        try:
            d = yf.download(
                ticker, start=start, end=end, interval="1d",
                auto_adjust=False, actions=False, progress=False,
                threads=False, group_by="column", timeout=30,
            )
            if d is None or d.empty:
                raise RuntimeError("Yahoo returned no rows")
            if isinstance(d.columns, pd.MultiIndex):
                # yfinance versions vary in the order of the column levels.
                candidates = [(ticker, "Close"), ("Close", ticker)]
                col = next((c for c in candidates if c in d.columns), None)
                if col is None:
                    raise RuntimeError(f"Close column missing: {list(d.columns)[:8]}")
                s = d[col]
            else:
                if "Close" not in d.columns:
                    raise RuntimeError(f"Close column missing: {list(d.columns)}")
                s = d["Close"]
            s = pd.to_numeric(s, errors="coerce").dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            s.name = TICKERS[ticker]
            return s
        except Exception as e:
            last_error = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {ticker}: {last_error}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2000-01-01")
    ap.add_argument("--end", default=(date.today() + timedelta(days=1)).isoformat())
    ap.add_argument("--output", default="direct_index_history.csv")
    args = ap.parse_args()

    series = [fetch_one(t, args.start, args.end) for t in TICKERS]
    prices = pd.concat(series, axis=1).sort_index()
    prices = prices.loc[(prices.index >= pd.Timestamp(args.start)) &
                        (prices.index < pd.Timestamp(args.end))]
    prices.index.name = "date"
    prices = prices.dropna(how="all")
    for col in TICKERS.values():
        if col not in prices or prices[col].dropna().empty:
            raise RuntimeError(f"Missing entire index series: {col}")
        first = prices[col].first_valid_index()
        last = prices[col].last_valid_index()
        if first > pd.Timestamp("2000-01-05"):
            raise RuntimeError(f"{col} starts too late: {first.date()}")
        if last < pd.Timestamp.today().normalize() - pd.Timedelta(days=5):
            raise RuntimeError(f"{col} data is stale: last={last.date()}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    prices.reset_index().to_csv(out, index=False, float_format="%.6f")
    print(f"Saved {out}: {len(prices)} rows; {prices.index.min().date()} to {prices.index.max().date()}")
    for col in TICKERS.values():
        print(f"{col}: {prices[col].first_valid_index().date()} -> {prices[col].last_valid_index().date()}, {prices[col].notna().sum()} closes")

if __name__ == "__main__":
    main()
