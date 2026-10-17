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
            cols = [x for x in ["date", "symbol", "high", "low"] if x in schema.names]
            table = pq.read_table(p, columns=cols)
            df = table.to_pandas()
            if not {"date", "symbol", "high", "low"}.issubset(df.columns):
                continue
            df = df[["date", "symbol", "high", "low"]].copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            frames.append(df.dropna())
        if not frames:
            raise RuntimeError("MarketParquet files had no usable date/symbol/high/low data")
        out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")


def reconstruct_hilo(stock: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct classic 52-week new-high/new-low breadth.

    A new high is based on today's intraday HIGH exceeding the maximum HIGH
    observed in the symbol's prior 252 trading sessions. A new low is based
    on today's intraday LOW undercutting the minimum LOW over those prior
    sessions. The current day is never included in the reference window.
    """
    df = stock[["date", "symbol", "high", "low"]].copy().sort_values(["symbol", "date"])
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df = df.dropna(subset=["date", "symbol", "high", "low"])

    prior_hi = df.groupby("symbol", sort=False)["high"].transform(
        lambda s: s.shift(1).rolling(252, min_periods=252).max()
    )
    prior_lo = df.groupby("symbol", sort=False)["low"].transform(
        lambda s: s.shift(1).rolling(252, min_periods=252).min()
    )

    df["eligible_hilo"] = prior_hi.notna() & prior_lo.notna()
    df["new_high"] = df["eligible_hilo"] & (df["high"] > prior_hi)
    df["new_low"] = df["eligible_hilo"] & (df["low"] < prior_lo)

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
    daily["hl_persistence"] = [
        hl_persistence_score(vals[max(0, i - 19): i + 1])
        for i in range(len(vals))
    ]
    return daily


TRADINGVIEW_EPOCH = "tradingview_all_us_intraday_v1"
TRADINGVIEW_LEDGER = "docs/data/master_top_v218_hilo_ledger.csv"


def fetch_tradingview_hilo() -> dict:
    """
    Secretless delayed fallback for one daily H/L observation.

    Universe: primary NYSE/NASDAQ/AMEX common stocks plus DRs exposed by the
    TradingView America screener. H/L uses today's intraday high/low versus
    TradingView's 52-week high/low field. This is deliberately stored as its
    own source epoch and is never mixed with MarketParquet history inside one
    persistence window.
    """
    from tradingview_screener import Query, col

    cols = [
        "name", "close", "high", "low",
        "price_52_week_high", "price_52_week_low",
        "exchange", "type", "typespecs", "update_mode", "is_primary",
    ]
    _, df = (
        Query()
        .select(*cols)
        .where(col("is_primary") == True)
        .limit(30000)
        .get_scanner_data()
    )
    if df.empty:
        raise RuntimeError("TradingView screener returned no rows")

    us = df[df["exchange"].isin(["NYSE", "NASDAQ", "AMEX"])].copy()

    def has_common(x: object) -> bool:
        if isinstance(x, (list, tuple, set)):
            return "common" in x
        return "common" in str(x).lower()

    common = us[
        us["type"].eq("dr")
        | (us["type"].eq("stock") & us["typespecs"].map(has_common))
    ].copy()
    numeric = ["high", "low", "price_52_week_high", "price_52_week_low"]
    for k in numeric:
        common[k] = pd.to_numeric(common[k], errors="coerce")
    common = common.dropna(subset=numeric)
    if len(common) < 1000:
        raise RuntimeError(f"TradingView H/L universe unexpectedly small: {len(common)}")

    new_high = common["high"] >= common["price_52_week_high"] * (1.0 - 1e-10)
    new_low = common["low"] <= common["price_52_week_low"] * (1.0 + 1e-10)
    nh, nl = int(new_high.sum()), int(new_low.sum())
    denom = nh + nl
    balance = (nh - nl) / denom if denom else float("nan")
    modes = common["update_mode"].dropna().astype(str).value_counts().to_dict()

    return {
        "source_epoch": TRADINGVIEW_EPOCH,
        "universe": int(len(common)),
        "new_highs": nh,
        "new_lows": nl,
        "hl_balance": float(balance),
        "update_modes": modes,
        "exchanges": {
            str(ex): int(len(g)) for ex, g in common.groupby("exchange", sort=True)
        },
    }


def append_hilo_ledger(path: Path, asof: str, obs: dict) -> pd.DataFrame:
    cols = [
        "date", "source_epoch", "universe", "new_highs", "new_lows",
        "hl_balance", "update_modes", "exchanges",
    ]
    if path.exists():
        try:
            ledger = pd.read_csv(path)
        except Exception:
            ledger = pd.DataFrame(columns=cols)
    else:
        ledger = pd.DataFrame(columns=cols)

    row = {
        "date": asof,
        "source_epoch": obs["source_epoch"],
        "universe": obs["universe"],
        "new_highs": obs["new_highs"],
        "new_lows": obs["new_lows"],
        "hl_balance": obs["hl_balance"],
        "update_modes": json.dumps(obs.get("update_modes", {}), sort_keys=True),
        "exchanges": json.dumps(obs.get("exchanges", {}), sort_keys=True),
    }
    ledger = ledger[ledger.get("date", pd.Series(dtype=str)).astype(str) != asof]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger["date"] = ledger["date"].astype(str)
    ledger = ledger.sort_values("date").drop_duplicates(
        ["date", "source_epoch"], keep="last"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(path, index=False)
    return ledger


def live_hl_from_ledger(ledger: pd.DataFrame, source_epoch: str) -> tuple[float, int]:
    same = ledger.loc[ledger["source_epoch"].astype(str) == source_epoch].copy()
    same = same.sort_values("date").drop_duplicates("date", keep="last").tail(20)
    warm = int(len(same))
    if warm < 20:
        return float("nan"), warm
    return hl_persistence_score(pd.to_numeric(same["hl_balance"], errors="coerce")), warm


def score_from_live_hilo(
    asof: str,
    obs: dict,
    hl_score: float,
    baseline_trigger: float | None = None,
) -> tuple[ScoreSnapshot, pd.Series]:
    score_date = pd.Timestamp(asof)
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
    r1, r6 = rate_shock_1m(d1), rate_shock_6m(d6)
    pol = math.sqrt(r1 * r6)
    route = route_score(pol, hl_score, top_ratio)
    combined = max(float(baseline_trigger), route) if baseline_trigger is not None else None

    snap = ScoreSnapshot(
        version=VERSION, freeze_date=FREEZE_DATE, asof=asof,
        price_symbol="^GSPC", price_close=round(close, 4),
        price_60m_high=round(high_60m, 4), top_ratio=round(top_ratio, 6),
        top_proximity=round(top_proximity(top_ratio), 6),
        dgs2=round(y, 4), dgs2_1m=round(y1, 4), dgs2_6m=round(y6, 4),
        delta_1m_bp=round(d1, 2), delta_6m_bp=round(d6, 2),
        r1=round(r1, 4), r6=round(r6, 4), policy=round(pol, 4),
        new_highs=int(obs["new_highs"]), new_lows=int(obs["new_lows"]),
        hl_balance=round(float(obs["hl_balance"]), 6),
        hl_persistence=round(float(hl_score), 4),
        eligible_95=bool(top_ratio >= TOP_ELIGIBLE),
        hl_gate_75=bool(hl_score >= HL_GATE),
        supplemental_route=round(route, 4),
        route_triggered=bool(route >= TRIGGER_THRESHOLD),
        route_threshold=TRIGGER_THRESHOLD,
        combined_trigger=round(combined, 4) if combined is not None else None,
        baseline_trigger=round(float(baseline_trigger), 4) if baseline_trigger is not None else None,
        breadth_source="TradingView America screener primary common+DR, NYSE/NASDAQ/AMEX, intraday 52-week H/L; source-epoch persistence",
        rate_source="FRED DGS2 public CSV",
        price_source="Yahoo Finance ^GSPC daily close",
        research_status="frozen formula; TradingView source epoch began post-freeze; no threshold changes",
    )
    return snap, price


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
        breadth_source="MarketParquet stock_daily reconstructed intraday 52-week H/L; prior 252 sessions; 20-session persistence",
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
    baseline_env = os.getenv("MASTER_TOP_BASELINE_TRIGGER", "").strip()
    baseline = float(baseline_env) if baseline_env else None
    out = Path(os.getenv("MASTER_TOP_OUTPUT", "docs/data/master_top_v218.json"))
    out.parent.mkdir(parents=True, exist_ok=True)

    if api_key:
        stock = fetch_marketparquet_stock_history(api_key)
        snapshot, breadth, price = build_snapshot(stock, baseline_trigger=baseline)
        payload = update_payload(snapshot, price, out)
        payload["source_transition"] = {
            "active_source": "marketparquet_intraday_hilo_v1",
            "warmup": False,
            "note": "MarketParquet production path; H/L uses daily high/low vs prior 252 sessions.",
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        breadth.tail(40).reset_index().to_csv(
            out.with_name("master_top_v218_breadth_tail.csv"), index=False
        )
        print(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2))
        return

    # Secretless fallback. We intentionally do NOT splice this new H/L universe
    # into the pre-freeze proxy history. Each source epoch must warm up on its
    # own before it is allowed to vote in the frozen 20-session persistence.
    price = fetch_yahoo_close("^GSPC", years=6)
    asof = str(price.index[-1].date())
    obs = fetch_tradingview_hilo()
    ledger_path = Path(os.getenv("MASTER_TOP_HILO_LEDGER", TRADINGVIEW_LEDGER))
    ledger = append_hilo_ledger(ledger_path, asof, obs)
    hl_score, warm = live_hl_from_ledger(ledger, TRADINGVIEW_EPOCH)

    payload = load_json(out, {
        "version": VERSION,
        "freeze_date": FREEZE_DATE,
        "formula_frozen": True,
        "prospective_evidence_start": FREEZE_DATE,
        "episode_lock_sessions": EPISODE_LOCK_SESSIONS,
        "events": [],
        "history": [],
    })
    payload["live_observation"] = {
        "asof": asof,
        **obs,
        "hl_persistence_if_ready": round(float(hl_score), 4) if np.isfinite(hl_score) else None,
        "warmup_sessions": warm,
        "warmup_required": 20,
    }
    payload["source_transition"] = {
        "active_source": TRADINGVIEW_EPOCH if warm >= 20 else "pre_freeze_seed_score",
        "candidate_source": TRADINGVIEW_EPOCH,
        "warmup": bool(warm < 20),
        "warmup_sessions": warm,
        "warmup_required": 20,
        "note": "Do not mix pre-freeze close/proxy history with the post-freeze intraday H/L epoch. Until 20 same-definition sessions exist, the frozen scored snapshot is preserved and only raw live H/L is appended.",
    }

    if warm >= 20 and np.isfinite(hl_score):
        snapshot, price = score_from_live_hilo(
            asof, obs, float(hl_score), baseline_trigger=baseline
        )
        payload = update_payload(snapshot, price, out)
        payload["live_observation"] = {
            "asof": asof, **obs,
            "hl_persistence_if_ready": round(float(hl_score), 4),
            "warmup_sessions": warm, "warmup_required": 20,
        }
        payload["source_transition"] = {
            "active_source": TRADINGVIEW_EPOCH,
            "candidate_source": TRADINGVIEW_EPOCH,
            "warmup": False, "warmup_sessions": warm, "warmup_required": 20,
            "note": "Same-definition 20-session live epoch is warm; source may now vote without changing any frozen threshold.",
        }

    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload.get("live_observation", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
