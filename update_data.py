from __future__ import annotations

import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "current.json"
CONFIG = json.loads((ROOT / "indicator_config.json").read_text(encoding="utf-8"))
MANUAL = ROOT / "manual_inputs.json"

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "market-regime-lab/1.0"})

FRED_IDS = [
    "VIXCLS", "NFCI", "BAMLH0A0HYM2", "T10Y2Y", "T10Y3M", "DGS2", "DGS10",
    "DTWEXBGS", "BAA10Y", "DCOILWTICO", "ISRATIO", "BUSINV", "MTSDS133FMS",
    "UNRATE", "ICSA", "DFF", "ECBDFR", "WALCL", "LOANINV"
]


def get_fred(ids: list[str]) -> dict[str, pd.Series]:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + ",".join(ids)
    r = HTTP.get(url, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
    out = {}
    for sid in ids:
        if sid in df.columns:
            s = pd.to_numeric(df[sid], errors="coerce").dropna()
            if not s.empty:
                out[sid] = s.rename(sid)
    return out


def stooq(symbol: str) -> pd.DataFrame:
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d"
    r = HTTP.get(url, timeout=45)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "Date" not in df.columns or "Close" not in df.columns:
        raise ValueError(f"Unexpected Stooq response for {symbol}")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def align(*series: pd.Series) -> list[pd.Series]:
    idx = pd.DatetimeIndex([])
    for s in series:
        idx = idx.union(pd.DatetimeIndex(s.index))
    idx = idx.sort_values()
    return [s.reindex(idx).ffill() for s in series]


def pct_change(s: pd.Series, n: int) -> pd.Series:
    return s.pct_change(n) * 100.0


def rolling_percentile(s: pd.Series, window: int = 756) -> pd.Series:
    s = s.dropna().astype(float)
    minp = min(60, max(10, window // 10))

    def f(a: np.ndarray) -> float:
        if len(a) == 0 or not np.isfinite(a[-1]):
            return np.nan
        return float(100.0 * np.mean(a <= a[-1]))

    return s.rolling(window=window, min_periods=minp).apply(f, raw=True)


def score(s: pd.Series, high_is_high: bool = True, window: int = 756) -> pd.Series:
    p = rolling_percentile(s, window)
    return p if high_is_high else 100.0 - p


def mean_scores(*parts: pd.Series) -> pd.Series:
    return pd.concat(parts, axis=1).sort_index().ffill().mean(axis=1, skipna=True)


def realized_vol(close: pd.Series, n: int) -> pd.Series:
    return close.pct_change().rolling(n).std() * math.sqrt(252) * 100.0


def yearly_growth(s: pd.Series) -> pd.Series:
    if len(s) < 3:
        return s * np.nan
    days = pd.Series(s.index).diff().dt.days.dropna()
    med = float(days.median()) if not days.empty else 30
    periods = 52 if med <= 10 else 12 if med <= 45 else 4
    return s.pct_change(periods) * 100.0


def pack(meta: dict, score_s: pd.Series, raw_s: pd.Series | None = None,
         raw_unit: str = "", quality: str | None = None) -> dict:
    s = pd.Series(score_s).dropna().astype(float).clip(0, 100)
    if s.empty:
        raise ValueError("empty score series")
    d1 = s.diff()
    d2 = d1.diff()
    raw = pd.Series(raw_s).dropna().astype(float) if raw_s is not None else s
    hist = [
        {"date": str(ts.date()), "score": round(float(v), 2)}
        for ts, v in s.tail(180).items() if np.isfinite(v)
    ]
    return {
        **meta,
        "score": round(float(s.iloc[-1]), 2),
        "raw": round(float(raw.iloc[-1]), 4) if not raw.empty else None,
        "raw_unit": raw_unit,
        "d1": round(float(d1.dropna().iloc[-1]), 2) if not d1.dropna().empty else None,
        "d2": round(float(d2.dropna().iloc[-1]), 2) if not d2.dropna().empty else None,
        "asof": str(s.index[-1].date()),
        "history": hist,
        "quality": quality or meta.get("type", "ok"),
    }


def main() -> None:
    errors: dict[str, str] = {}
    meta = {x["id"]: x for x in CONFIG}
    result: dict[str, dict] = {}

    try:
        fs = get_fred(FRED_IDS)
    except Exception as exc:
        fs = {}
        errors["fred_batch"] = repr(exc)

    market = {}
    for sym in ["spy.us", "rsp.us", "iwm.us", "hyg.us", "lqd.us", "gld.us"]:
        try:
            market[sym] = stooq(sym)
        except Exception as exc:
            errors[f"stooq:{sym}"] = repr(exc)

    def F(k: str) -> pd.Series:
        return fs[k]

    def C(k: str) -> pd.Series:
        return market[k]["Close"].dropna()

    def V(k: str) -> pd.Series:
        return market[k]["Volume"].replace(0, np.nan).dropna()

    def put(key: str, score_s: pd.Series, raw_s: pd.Series | None = None,
            unit: str = "", quality: str | None = None) -> None:
        try:
            result[key] = pack(meta[key], score_s, raw_s, unit, quality)
        except Exception as exc:
            errors[f"calc:{key}"] = repr(exc)

    if "iwm.us" in market and "spy.us" in market:
        iwm, spy = align(C("iwm.us"), C("spy.us"))
        rel = pct_change(iwm, 20) - pct_change(spy, 20)
        vol = V("iwm.us").reindex(iwm.index).ffill()
        vr = vol.rolling(5).mean() / vol.rolling(60).mean()
        put("retail_participation", mean_scores(score(rel), score(vr)), rel, "% relative 20d", "proxy")

    if "spy.us" in market and "rsp.us" in market:
        spy = C("spy.us")
        parts = [score(spy / spy.rolling(n).mean() - 1) for n in (20, 50, 200)]
        rsp, spya = align(C("rsp.us"), spy)
        parts.append(score(pct_change(rsp, 20) - pct_change(spya, 20)))
        put("market_support", mean_scores(*parts), spy / spy.rolling(200).mean() - 1, "SPY/MA200 - 1")

    cb = []
    if "DFF" in fs:
        cb.append(score(F("DFF").diff(), high_is_high=False, window=260))
    if "ECBDFR" in fs:
        cb.append(score(F("ECBDFR").diff(), high_is_high=False, window=260))
    if cb:
        put("global_cb_rhythm", mean_scores(*cb), mean_scores(*cb), "easing score")

    if "VIXCLS" in fs and "spy.us" in market:
        spy = C("spy.us")
        dd20 = -(spy / spy.rolling(20).max() - 1) * 100
        put("largecap_panic", mean_scores(score(F("VIXCLS")), score(dd20)), F("VIXCLS"), "VIX")

    if "VIXCLS" in fs and "BAMLH0A0HYM2" in fs:
        put("market_fear", mean_scores(score(F("VIXCLS")), score(F("BAMLH0A0HYM2"))), F("VIXCLS"), "VIX")

    if "VIXCLS" in fs:
        vix = F("VIXCLS")
        jump = pct_change(vix, 5)
        put("options_anomaly", mean_scores(score(vix), score(jump)), jump, "% VIX 5d", "proxy")

    liq = []
    if "NFCI" in fs:
        liq.append(score(F("NFCI")))
    if "BAMLH0A0HYM2" in fs:
        liq.append(score(F("BAMLH0A0HYM2")))
    if "WALCL" in fs:
        liq.append(score(pct_change(F("WALCL"), 4), high_is_high=False, window=260))
    if liq:
        put("liquidity_risk", mean_scores(*liq), mean_scores(*liq), "score")

    if "DGS2" in fs and "DGS10" in fs:
        put("treasury_rate_regime", mean_scores(score(F("DGS2")), score(F("DGS10"))), F("DGS10"), "% 10Y")

    usd = []
    if "DTWEXBGS" in fs:
        usd.append(score(pct_change(F("DTWEXBGS"), 20)))
    if "BAA10Y" in fs:
        usd.append(score(F("BAA10Y")))
    if usd:
        put("usd_credit", mean_scores(*usd), mean_scores(*usd), "score")

    if "gld.us" in market:
        g = C("gld.us")
        put("gold", mean_scores(score(g), score(pct_change(g, 20))), g, "GLD")

    if "DCOILWTICO" in fs:
        o = F("DCOILWTICO")
        put("oil", mean_scores(score(o), score(pct_change(o, 20))), o, "USD/bbl")

    manual = {}
    if MANUAL.exists():
        try:
            manual = json.loads(MANUAL.read_text(encoding="utf-8"))
        except Exception as exc:
            errors["manual_inputs"] = repr(exc)
    bc = manual.get("buffett_cash_ratio") or {}
    if bc.get("value") is not None:
        ts = pd.Timestamp(bc.get("asof") or pd.Timestamp.utcnow().date())
        one = pd.Series([float(bc["value"])], index=[ts])
        put("buffett_cash", one.clip(0, 100), one, "%", "manual")
    else:
        result["buffett_cash"] = {**meta["buffett_cash"], "score": None, "raw": None, "raw_unit": "%",
                                  "d1": None, "d2": None, "asof": None, "history": [], "quality": "manual_pending"}

    if "BAMLH0A0HYM2" in fs:
        hy = F("BAMLH0A0HYM2")
        put("high_yield", score(hy), hy, "% OAS")

    inv = []
    if "ISRATIO" in fs:
        inv.append(score(F("ISRATIO")))
    if "BUSINV" in fs:
        inv.append(score(yearly_growth(F("BUSINV"))))
    if inv:
        put("inventory_cycle", mean_scores(*inv), mean_scores(*inv), "score")

    if "MTSDS133FMS" in fs:
        f = F("MTSDS133FMS").rolling(12, min_periods=6).sum()
        put("fiscal_deficit", score(-f), f, "USD mn / 12m")

    emp = []
    if "UNRATE" in fs:
        emp.append(score(F("UNRATE")))
    if "ICSA" in fs:
        emp.append(score(F("ICSA")))
    if emp:
        raw = F("UNRATE") if "UNRATE" in fs else mean_scores(*emp)
        put("employment", mean_scores(*emp), raw, "% unemployment")

    if "spy.us" in market:
        spy = C("spy.us")
        ratio = spy / spy.rolling(200).mean()
        val_score = score(ratio, window=1260)

        put("valuation_cycle", val_score, ratio, "SPY/MA200", "proxy")

        vol = V("spy.us")
        put("market_volume", score(vol), vol, "shares")

        vratio = vol.rolling(5).mean() / vol.rolling(20).mean() - 1
        put("volume_speed", score(vratio), vratio * 100, "%")

        rv20 = realized_vol(spy, 20)
        rv60 = realized_vol(spy, 60)
        spread = rv20 - rv60
        put("vol_60d_change", mean_scores(score(rv60), score(spread)), rv60, "% annualized")

        put("valuation_percentile", val_score, ratio, "SPY/MA200", "proxy")

        speed = pct_change(ratio, 20)
        put("valuation_speed", score(speed), speed, "% / 20d", "proxy")

    if "spy.us" in market and "rsp.us" in market:
        spy, rsp = align(C("spy.us"), C("rsp.us"))
        conc = pct_change(spy, 60) - pct_change(rsp, 60)
        put("concentration", score(conc), conc, "% SPY-RSP 60d", "proxy")

    lev = []
    if "NFCI" in fs:
        lev.append(score(F("NFCI")))
    if "BAMLH0A0HYM2" in fs:
        lev.append(score(F("BAMLH0A0HYM2")))
    if "hyg.us" in market and "lqd.us" in market:
        hyg, lqd = align(C("hyg.us"), C("lqd.us"))
        lev.append(score(hyg / lqd, high_is_high=False))
    if lev:
        put("leverage_liquidity", mean_scores(*lev), mean_scores(*lev), "score", "proxy")

    sys_parts = []
    if "VIXCLS" in fs:
        sys_parts.append(score(F("VIXCLS")))
    if "BAMLH0A0HYM2" in fs:
        sys_parts.append(score(F("BAMLH0A0HYM2")))
    if "NFCI" in fs:
        sys_parts.append(score(F("NFCI")))
    if "spy.us" in market:
        spy = C("spy.us")
        dd = -(spy / spy.cummax() - 1) * 100
        sys_parts.append(score(dd))

    systemic = None
    if sys_parts:
        systemic = mean_scores(*sys_parts)
        put("systemic_risk", systemic, systemic, "score")

    if systemic is not None and len(systemic.dropna()) > 70:
        r60 = mean_scores(score(systemic, window=60), score(systemic.diff(60), window=252))
        put("risk_60d", r60, systemic, "systemic score")

    if "LOANINV" in fs:
        loans = F("LOANINV")
        yoy = yearly_growth(loans)
        accel = yoy.diff()
        put("credit_cycle", mean_scores(score(yoy), score(accel)), yoy, "% YoY")

    curve = []
    raw = None
    if "T10Y2Y" in fs:
        raw = F("T10Y2Y")
        curve.append(score(raw, high_is_high=False))
    if "T10Y3M" in fs:
        curve.append(score(F("T10Y3M"), high_is_high=False))
    if curve:
        put("yield_curve", mean_scores(*curve), raw if raw is not None else mean_scores(*curve), "% 10Y-2Y")

    for item in CONFIG:
        if item["id"] not in result:
            result[item["id"]] = {
                **item, "score": None, "raw": None, "raw_unit": "", "d1": None, "d2": None,
                "asof": None, "history": [], "quality": "source_error"
            }

    ordered = [result[x["id"]] for x in CONFIG]
    working = sum(x["score"] is not None for x in ordered)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if working >= 20 else "partial",
        "working_count": working,
        "total_count": len(ordered),
        "errors": errors,
        "derivative_definition": {
            "d1": "一级导：当前指标分 - 上一期指标分（变化动能）",
            "d2": "二级导：当前一级导 - 上一期一级导（动能变化速率）"
        },
        "indicators": ordered,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {working}/{len(ordered)} indicators")
    if working < 15:
        print(json.dumps(errors, ensure_ascii=False, indent=2))
        sys.exit(2)


if __name__ == "__main__":
    main()
