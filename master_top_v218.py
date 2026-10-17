from __future__ import annotations

import io
import json
import math
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

VERSION = "MASTER-TOP-V2.1.8-FROZEN"
FREEZE_DATE = "2026-10-17"
TRIGGER_THRESHOLD = 55.0
HL_GATE = 75.0
TOP_ELIGIBLE = 0.95
EPISODE_LOCK_SESSIONS = 126
MARKETPARQUET_BASE = "https://marketparquet.com/api/v1"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def rate_shock_6m(delta_bp: float) -> float:
    return 100.0 * clip((float(delta_bp) - 10.0) / 60.0)


def rate_shock_1m(delta_bp: float) -> float:
    return 100.0 * clip(float(delta_bp) / 20.0)


def policy_score(delta_6m_bp: float, delta_1m_bp: float) -> float:
    r6 = rate_shock_6m(delta_6m_bp)
    r1 = rate_shock_1m(delta_1m_bp)
    return math.sqrt(r6 * r1)


def hl_persistence_score(hl_balances: Iterable[float]) -> float:
    vals = [float(x) for x in hl_balances if x is not None and np.isfinite(x)]
    if len(vals) < 15:
        return float("nan")
    vals = vals[-20:]
    mean_hl = float(np.mean(vals))
    neg_frac = float(np.mean(np.asarray(vals) < 0.0))
    severity = clip(-mean_hl / 0.30)
    return 100.0 * math.sqrt(severity * neg_frac)


def top_proximity(top_ratio: float) -> float:
    return clip((float(top_ratio) - 0.95) / 0.05)


def route_score(policy: float, hl_score: float, top_ratio: float) -> float:
    if not np.isfinite(hl_score):
        return 0.0
    if float(top_ratio) < TOP_ELIGIBLE or float(hl_score) < HL_GATE:
        return 0.0
    return (
        float(policy)
        * math.sqrt(float(hl_score) / 100.0)
        * math.sqrt(top_proximity(float(top_ratio)))
    )


@dataclass
class ScoreSnapshot:
    version: str
    freeze_date: str
    asof: str
    price_symbol: str
    price_close: float
    price_60m_high: float
    top_ratio: float
    top_proximity: float
    dgs2: float
    dgs2_1m: float
    dgs2_6m: float
    delta_1m_bp: float
    delta_6m_bp: float
    r1: float
    r6: float
    policy: float
    new_highs: int
    new_lows: int
    hl_balance: float
    hl_persistence: float
    eligible_95: bool
    hl_gate_75: bool
    supplemental_route: float
    route_triggered: bool
    route_threshold: float
    combined_trigger: float | None
    baseline_trigger: float | None
    breadth_source: str
    rate_source: str
    price_source: str
    research_status: str


def http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "MarketTopV218/1.0 (+https://github.com/galbbb2772/market-indicators-v1)"})
    return s


def fetch_yahoo_close(symbol: str = "^GSPC", years: int = 6) -> pd.Series:
    end = datetime.now(timezone.utc) + timedelta(days=1)
    start = end - timedelta(days=365 * years + 30)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
        f"?period1={int(start.timestamp())}&period2={int(end.timestamp())}"
        "&interval=1d&events=history&includeAdjustedClose=true"
    )
    s = http_session()
    last_exc: Exception | None = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            r = s.get(url.replace("query1.finance.yahoo.com", host), timeout=30)
            r.raise_for_status()
            payload = r.json()
            obj = payload["chart"]["result"][0]
            ts = obj.get("timestamp") or []
            q = (obj.get("indicators", {}).get("quote") or [{}])[0]
            adj = (obj.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
            close = adj if adj and len(adj) == len(ts) else q.get("close")
            idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
            out = pd.Series(pd.to_numeric(close, errors="coerce"), index=idx, dtype=float).dropna().sort_index()
            if out.empty:
                raise ValueError("Yahoo returned empty series")
            return out
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Yahoo price fetch failed: {last_exc}")


def fetch_dgs2() -> pd.Series:
    r = http_session().get(FRED_CSV, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    date_col = "DATE" if "DATE" in df.columns else df.columns[0]
    val_col = "DGS2" if "DGS2" in df.columns else df.columns[1]
    idx = pd.to_datetime(df[date_col], errors="coerce")
    vals = pd.to_numeric(df[val_col], errors="coerce")
    s = pd.Series(vals.to_numpy(), index=idx, dtype=float).dropna().sort_index()
    if s.empty:
        raise ValueError("FRED DGS2 returned no usable data")
    return s


def asof_value(s: pd.Series, dt: pd.Timestamp) -> float:
    x = s.loc[s.index <= pd.Timestamp(dt)]
    if x.empty:
        raise ValueError(f"no data on/before {dt}")
    return float(x.iloc[-1])


def marketparquet_manifest(api_key: str, start: str, end: str) -> list[dict]:
    r = http_session().get(
        f"{MARKETPARQUET_BASE}/manifest/stock_daily",
        params={"start": start, "end": end},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    if r.status_code in (401, 403):
        raise RuntimeError(f"MarketParquet authorization failed ({r.status_code})")
    r.raise_for_status()
    files = (r.json() or {}).get("files") or []
    if not files:
        raise RuntimeError("MarketParquet manifest returned no stock_daily files")
    return sorted(files, key=lambda x: str(x.get("date", "")))


def _download_parquet(item: dict, dest: Path) -> Path:
    r = http_session().get(item["download_url"], timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def fetch_marketparquet_stock_history(api_key: str, lookback_calendar_days: int = 440) -> pd.DataFrame:
    import pyarrow.parquet as pq

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=lookback_calendar_days)
    files = marketparquet_manifest(api_key, str(start), str(today))
    with tempfile.TemporaryDirectory(prefix="v218_mktpq_") as td:
        root = Path(td)
        jobs = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for i, item in enumerate(files):
                dest = root / (item.get("filename") or f"stock_{i}.parquet")
                jobs.append(ex.submit(_download_parquet, item, dest))
            paths = [f.result() for f in as_completed(jobs)]

        frames: list[pd.DataFrame] = []
        for p in paths:
            schema = pq.read_schema(p)
            cols = [c for c in ["date", "symbol", "close"] if c in schema.names]
            table = pq.read_table(p, columns=cols)
            df = table.to_pandas()
            if "date" not in df.columns or "symbol" not in df.columns or "close" not in df.columns:
                continue
            df = df[["date", "symbol", "close"]].copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            frames.append(df.dropna())
        if not frames:
            raise RuntimeError("MarketParquet files had no usable date/symbol/close data")
        out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")


def reconstruct_hilo(stock: pd.DataFrame) -> pd.DataFrame:
    df = stock[["date", "symbol", "close"]].copy().sort_values(["symbol", "date"])
    g = df.groupby("symbol", sort=False)["close"]
    prev = g.shift(1)
    prior_hi = prev.groupby(df["symbol"], sort=False).rolling(252, min_periods=252).max().reset_index(level=0, drop=True)
    prior_lo = prev.groupby(df["symbol"], sort=False).rolling(252, min_periods=252).min().reset_index(level=0, drop=True)
    df["eligible_hilo"] = prior_hi.notna() & prior_lo.notna()
    df["new_high"] = df["eligible_hilo"] & (df["close"] >= prior_hi)
    df["new_low"] = df["eligible_hilo"] & (df["close"] <= prior_lo)
    daily = df.groupby("date").agg(
        issues=("symbol", "nunique"),
        hilo_eligible=("eligible_hilo", "sum"),
        new_highs=("new_high", "sum"),
        new_lows=("new_low", "sum"),
    ).sort_index()
    denom = daily["new_highs"] + daily["new_lows"]
    daily["hl_balance"] = np.where(
        denom > 0,
        (daily["new_highs"] - daily["new_lows"]) / denom,
        np.nan,
    )
    vals = daily["hl_balance"].to_list()
    scores = []
    for i in range(len(vals)):
        scores.append(hl_persistence_score(vals[max(0, i - 19): i + 1]))
    daily["hl_persistence"] = scores
    return daily


def trading_sessions_between(price: pd.Series, start: str, end: str) -> int:
    s = price.loc[(price.index > pd.Timestamp(start)) & (price.index <= pd.Timestamp(end))]
    return int(len(s))


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_snapshot(stock: pd.DataFrame, baseline_trigger: float | None = None) -> tuple[ScoreSnapshot, pd.DataFrame, pd.Series]:
    breadth = reconstruct_hilo(stock)
    valid = breadth.dropna(subset=["hl_persistence"])
    if valid.empty:
        raise RuntimeError("not enough stock history to compute 20-day H/L persistence")
    score_date = pd.Timestamp(valid.index[-1])
    b = valid.loc[score_date]

    price = fetch_yahoo_close("^GSPC", years=6)
    p = price.loc[price.index <= score_date]
    if len(p) < 1260:
        raise RuntimeError("not enough S&P 500 history for 60M high")
    close = float(p.iloc[-1])
    high_60m = float(p.iloc[-1260:].max())
    top_ratio = close / high_60m

    dgs2 = fetch_dgs2()
    y = asof_value(dgs2, score_date)
    y1 = asof_value(dgs2, score_date - pd.DateOffset(months=1))
    y6 = asof_value(dgs2, score_date - pd.DateOffset(months=6))
    d1 = (y - y1) * 100.0
    d6 = (y - y6) * 100.0
    r1 = rate_shock_1m(d1)
    r6 = rate_shock_6m(d6)
    pol = math.sqrt(r1 * r6)
    hl = float(b["hl_persistence"])
    route = route_score(pol, hl, top_ratio)
    combined = max(float(baseline_trigger), route) if baseline_trigger is not None else None

    snap = ScoreSnapshot(
        version=VERSION,
        freeze_date=FREEZE_DATE,
        asof=str(score_date.date()),
        price_symbol="^GSPC",
        price_close=round(close, 4),
        price_60m_high=round(high_60m, 4),
        top_ratio=round(top_ratio, 6),
        top_proximity=round(top_proximity(top_ratio), 6),
        dgs2=round(y, 4),
        dgs2_1m=round(y1, 4),
        dgs2_6m=round(y6, 4),
        delta_1m_bp=round(d1, 2),
        delta_6m_bp=round(d6, 2),
        r1=round(r1, 4),
        r6=round(r6, 4),
        policy=round(pol, 4),
        new_highs=int(b["new_highs"]),
        new_lows=int(b["new_lows"]),
        hl_balance=round(float(b["hl_balance"]), 6),
        hl_persistence=round(hl, 4),
        eligible_95=bool(top_ratio >= TOP_ELIGIBLE),
        hl_gate_75=bool(hl >= HL_GATE),
        supplemental_route=round(route, 4),
        route_triggered=bool(route >= TRIGGER_THRESHOLD),
        route_threshold=TRIGGER_THRESHOLD,
        combined_trigger=round(combined, 4) if combined is not None else None,
        baseline_trigger=round(float(baseline_trigger), 4) if baseline_trigger is not None else None,
        breadth_source="MarketParquet stock_daily reconstructed 52-week H/L; 252 prior sessions; 20-session persistence",
        rate_source="FRED DGS2 public CSV",
        price_source="Yahoo Finance ^GSPC daily close",
        research_status="frozen formula; post-freeze data only may accumulate prospective evidence",
    )
    return snap, breadth, price


def update_payload(snapshot: ScoreSnapshot, price: pd.Series, out_path: Path) -> dict:
    payload = load_json(out_path, {
        "version": VERSION,
        "freeze_date": FREEZE_DATE,
        "formula_frozen": True,
        "prospective_evidence_start": FREEZE_DATE,
        "episode_lock_sessions": EPISODE_LOCK_SESSIONS,
        "events": [
            {
                "start_date": "2026-09-10",
                "type": "LIVE_HOLDOUT_PRE_FREEZE_SIGNAL",
                "status": "open",
                "note": "Signal inputs were observed before the 2026-10-17 formula freeze; future path after freeze is prospective evidence, not a pure pre-freeze OOS signal-generation test."
            }
        ],
        "history": [],
    })
    payload["version"] = VERSION
    payload["freeze_date"] = FREEZE_DATE
    payload["formula_frozen"] = True
    payload["latest"] = asdict(snapshot)

    hist = payload.setdefault("history", [])
    hist = [x for x in hist if x.get("asof") != snapshot.asof]
    hist.append({
        "asof": snapshot.asof,
        "route": snapshot.supplemental_route,
        "policy": snapshot.policy,
        "hl_persistence": snapshot.hl_persistence,
        "top_ratio": snapshot.top_ratio,
        "triggered": snapshot.route_triggered,
    })
    hist = sorted(hist, key=lambda x: x.get("asof", ""))[-800:]
    payload["history"] = hist

    events = payload.setdefault("events", [])
    if snapshot.route_triggered:
        last = events[-1] if events else None
        open_new = True
        if last and last.get("start_date"):
            try:
                sessions = trading_sessions_between(price, last["start_date"], snapshot.asof)
                if sessions < EPISODE_LOCK_SESSIONS:
                    open_new = False
                    last["status"] = "open"
                    last["last_trigger_date"] = snapshot.asof
                    last["sessions_since_start"] = sessions
            except Exception:
                pass
        if open_new:
            events.append({
                "start_date": snapshot.asof,
                "last_trigger_date": snapshot.asof,
                "type": "PROSPECTIVE_POST_FREEZE_EPISODE",
                "status": "open",
                "sessions_since_start": 0,
            })

    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return payload


def main() -> None:
    api_key = os.getenv("MARKETPARQUET_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("MARKETPARQUET_API_KEY is required for production breadth reconstruction")
    baseline_env = os.getenv("MASTER_TOP_BASELINE_TRIGGER", "").strip()
    baseline = float(baseline_env) if baseline_env else None
    out = Path(os.getenv("MASTER_TOP_OUTPUT", "docs/data/master_top_v218.json"))
    out.parent.mkdir(parents=True, exist_ok=True)

    stock = fetch_marketparquet_stock_history(api_key)
    snapshot, breadth, price = build_snapshot(stock, baseline_trigger=baseline)
    payload = update_payload(snapshot, price, out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    tail = breadth.tail(40).reset_index()
    tail.to_csv(out.with_name("master_top_v218_breadth_tail.csv"), index=False)
    print(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
