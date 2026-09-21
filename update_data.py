from __future__ import annotations

import io
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "current.json"
CONFIG = json.loads((ROOT / "indicator_config.json").read_text(encoding="utf-8"))
MANUAL = ROOT / "manual_inputs.json"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 MarketRegimeLab/1.1"})

FRED_IDS = [
    "NFCI", "BAMLH0A0HYM2", "T10Y2Y", "T10Y3M", "DGS2", "DGS10",
    "DTWEXBGS", "BAA10Y", "ISRATIO", "BUSINV", "MTSDS133FMS", "UNRATE",
    "ICSA", "DFF", "ECBDFR", "WALCL", "LOANINV"
]
YAHOO = ["SPY", "RSP", "IWM", "HYG", "LQD", "GLD", "^VIX", "CL=F", "DX-Y.NYB", "^TNX", "^IRX"]


def request(url: str, timeout: int = 30) -> requests.Response:
    last = None
    for base in (url, url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")):
        for wait in (0, 2):
            if wait:
                time.sleep(wait)
            try:
                r = HTTP.get(base, timeout=timeout)
                if r.ok:
                    return r
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
            except Exception as exc:
                last = exc
    raise last or RuntimeError("request failed")


def yahoo(symbol: str) -> pd.DataFrame:
    sym = quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1d&events=history&includeAdjustedClose=true"
    data = request(url, 8).json()
    res = (data.get("chart") or {}).get("result")
    if not res:
        raise ValueError(str((data.get("chart") or {}).get("error")))
    obj = res[0]
    ts = obj.get("timestamp") or []
    q = ((obj.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((obj.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    close = adj if adj and len(adj) == len(ts) else q.get("close")
    vol = q.get("volume") or [None] * len(ts)
    if not ts or not close:
        raise ValueError("no Yahoo history")
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    df = pd.DataFrame({"Close": pd.to_numeric(close, errors="coerce"), "Volume": pd.to_numeric(vol, errors="coerce")}, index=idx)
    return df.dropna(subset=["Close"]).sort_index()


def fred_chunk(ids: list[str]) -> dict[str, pd.Series]:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + ",".join(ids) + "&cosd=2015-01-01"
    r = HTTP.get(url, timeout=8)
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


def get_fred(ids: list[str], errors: dict[str, str]) -> dict[str, pd.Series]:
    out = {}
    for i in range(0, len(ids), 4):
        chunk = ids[i:i+4]
        try:
            out.update(fred_chunk(chunk))
        except Exception as exc:
            errors["fred:" + ",".join(chunk)] = repr(exc)
    return out


def align(*series: pd.Series) -> list[pd.Series]:
    idx = pd.DatetimeIndex([])
    for s in series:
        idx = idx.union(pd.DatetimeIndex(s.index))
    idx = idx.sort_values()
    return [s.reindex(idx).ffill() for s in series]


def pct(s: pd.Series, n: int) -> pd.Series:
    return s.pct_change(n) * 100.0


def rolling_percentile(s: pd.Series, window: int = 756) -> pd.Series:
    s = s.dropna().astype(float)
    minp = min(60, max(10, window // 10))
    def f(a):
        return np.nan if len(a) == 0 or not np.isfinite(a[-1]) else 100.0 * np.mean(a <= a[-1])
    return s.rolling(window, min_periods=minp).apply(f, raw=True)


def score(s: pd.Series, high: bool = True, window: int = 756) -> pd.Series:
    p = rolling_percentile(s, window)
    return p if high else 100.0 - p


def avg(*ss: pd.Series) -> pd.Series:
    return pd.concat(ss, axis=1).sort_index().ffill().mean(axis=1, skipna=True)


def rv(close: pd.Series, n: int) -> pd.Series:
    return close.pct_change().rolling(n).std() * math.sqrt(252) * 100.0


def yoy(s: pd.Series) -> pd.Series:
    if len(s) < 3:
        return s * np.nan
    gaps = pd.Series(s.index).diff().dt.days.dropna()
    med = float(gaps.median()) if not gaps.empty else 30
    n = 52 if med <= 10 else 12 if med <= 45 else 4
    return s.pct_change(n) * 100.0


def pack(meta: dict, s: pd.Series, raw: pd.Series | None = None, unit: str = "", quality: str | None = None) -> dict:
    s = pd.Series(s).dropna().astype(float).clip(0, 100)
    if s.empty:
        raise ValueError("empty score")
    d1 = s.diff()
    d2 = d1.diff()
    raw = pd.Series(raw).dropna().astype(float) if raw is not None else s
    return {
        **meta,
        "score": round(float(s.iloc[-1]), 2),
        "raw": round(float(raw.iloc[-1]), 4) if not raw.empty else None,
        "raw_unit": unit,
        "d1": round(float(d1.dropna().iloc[-1]), 2) if not d1.dropna().empty else None,
        "d2": round(float(d2.dropna().iloc[-1]), 2) if not d2.dropna().empty else None,
        "asof": str(s.index[-1].date()),
        "history": [{"date": str(i.date()), "score": round(float(v), 2)} for i, v in s.tail(180).items() if np.isfinite(v)],
        "quality": quality or meta.get("type", "ok"),
    }


def main():
    errors = {}
    meta = {x["id"]: x for x in CONFIG}
    out = {}
    fs = get_fred(FRED_IDS, errors)
    mk = {}
    for sym in YAHOO:
        try:
            mk[sym] = yahoo(sym)
        except Exception as exc:
            errors[f"yahoo:{sym}"] = repr(exc)

    def C(k): return mk[k]["Close"].dropna()
    def V(k): return mk[k]["Volume"].replace(0, np.nan).dropna()
    def F(k): return fs[k]
    def put(k, s, raw=None, unit="", quality=None):
        try:
            out[k] = pack(meta[k], s, raw, unit, quality)
        except Exception as exc:
            errors[f"calc:{k}"] = repr(exc)

    if "IWM" in mk and "SPY" in mk:
        iwm, spy = align(C("IWM"), C("SPY"))
        rel = pct(iwm,20)-pct(spy,20)
        iv = V("IWM").reindex(iwm.index).ffill()
        vr = iv.rolling(5).mean()/iv.rolling(60).mean()
        put("retail_participation", avg(score(rel),score(vr)), rel, "% relative 20d", "proxy")

    if "SPY" in mk and "RSP" in mk:
        spy=C("SPY")
        parts=[score(spy/spy.rolling(n).mean()-1) for n in (20,50,200)]
        rsp,spya=align(C("RSP"),spy)
        parts.append(score(pct(rsp,20)-pct(spya,20)))
        put("market_support",avg(*parts),spy/spy.rolling(200).mean()-1,"SPY/MA200 - 1")

    cb=[]
    if "DFF" in fs: cb.append(score(F("DFF").diff(),False,260))
    if "ECBDFR" in fs: cb.append(score(F("ECBDFR").diff(),False,260))
    if cb:
        put("global_cb_rhythm",avg(*cb),avg(*cb),"easing score")
    elif "^TNX" in mk:
        y=C("^TNX")
        put("global_cb_rhythm",score(pct(y,20),False),pct(y,20),"% 10Y 20d","proxy")

    vix = C("^VIX") if "^VIX" in mk else None
    if vix is not None and "SPY" in mk:
        spy=C("SPY")
        dd=-(spy/spy.rolling(20).max()-1)*100
        put("largecap_panic",avg(score(vix),score(dd)),vix,"VIX")

    if vix is not None:
        credit = None
        if "BAMLH0A0HYM2" in fs:
            credit=score(F("BAMLH0A0HYM2"))
        elif "HYG" in mk and "LQD" in mk:
            h,l=align(C("HYG"),C("LQD"))
            credit=score(h/l,False)
        if credit is not None:
            put("market_fear",avg(score(vix),credit),vix,"VIX")
        jump=pct(vix,5)
        put("options_anomaly",avg(score(vix),score(jump)),jump,"% VIX 5d","proxy")

    liq=[]
    if "NFCI" in fs: liq.append(score(F("NFCI")))
    if "BAMLH0A0HYM2" in fs: liq.append(score(F("BAMLH0A0HYM2")))
    if "HYG" in mk and "LQD" in mk:
        h,l=align(C("HYG"),C("LQD"))
        liq.append(score(h/l,False))
    if liq:
        put("liquidity_risk",avg(*liq),avg(*liq),"score")

    if "DGS10" in fs and "DGS2" in fs:
        put("treasury_rate_regime",avg(score(F("DGS10")),score(F("DGS2"))),F("DGS10"),"% 10Y")
    elif "^TNX" in mk:
        y=C("^TNX")
        put("treasury_rate_regime",score(y),y,"10Y yield","proxy")

    usd=[]
    if "DTWEXBGS" in fs:
        usd.append(score(pct(F("DTWEXBGS"),20)))
    elif "DX-Y.NYB" in mk:
        usd.append(score(pct(C("DX-Y.NYB"),20)))
    if "BAA10Y" in fs:
        usd.append(score(F("BAA10Y")))
    elif "HYG" in mk and "LQD" in mk:
        h,l=align(C("HYG"),C("LQD"))
        usd.append(score(h/l,False))
    if usd:
        put("usd_credit",avg(*usd),avg(*usd),"score")

    if "GLD" in mk:
        g=C("GLD")
        put("gold",avg(score(g),score(pct(g,20))),g,"GLD")
    if "CL=F" in mk:
        o=C("CL=F")
        put("oil",avg(score(o),score(pct(o,20))),o,"WTI future")

    manual={}
    try:
        manual=json.loads(MANUAL.read_text(encoding="utf-8")) if MANUAL.exists() else {}
    except Exception as exc:
        errors["manual_inputs"]=repr(exc)
    bc=(manual.get("buffett_cash_ratio") or {})
    if bc.get("value") is not None:
        t=pd.Timestamp(bc.get("asof") or pd.Timestamp.utcnow().date())
        s=pd.Series([float(bc["value"])],index=[t])
        put("buffett_cash",s.clip(0,100),s,"%","manual")
    else:
        out["buffett_cash"]={**meta["buffett_cash"],"score":None,"raw":None,"raw_unit":"%","d1":None,"d2":None,"asof":None,"history":[],"quality":"manual_pending"}

    if "BAMLH0A0HYM2" in fs:
        h=F("BAMLH0A0HYM2")
        put("high_yield",score(h),h,"% OAS")
    elif "HYG" in mk and "LQD" in mk:
        h,l=align(C("HYG"),C("LQD"))
        r=h/l
        put("high_yield",score(r,False),r,"HYG/LQD","proxy")

    inv=[]
    if "ISRATIO" in fs: inv.append(score(F("ISRATIO")))
    if "BUSINV" in fs: inv.append(score(yoy(F("BUSINV"))))
    if inv:
        put("inventory_cycle",avg(*inv),avg(*inv),"score")

    if "MTSDS133FMS" in fs:
        f=F("MTSDS133FMS").rolling(12,min_periods=6).sum()
        put("fiscal_deficit",score(-f),f,"USD mn / 12m")

    emp=[]
    if "UNRATE" in fs: emp.append(score(F("UNRATE")))
    if "ICSA" in fs: emp.append(score(F("ICSA")))
    if emp:
        put("employment",avg(*emp),F("UNRATE") if "UNRATE" in fs else avg(*emp),"% unemployment")

    if "SPY" in mk:
        spy=C("SPY")
        ratio=spy/spy.rolling(200).mean()
        vs=score(ratio,window=1260)
        put("valuation_cycle",vs,ratio,"SPY/MA200","proxy")
        vol=V("SPY")
        put("market_volume",score(vol),vol,"shares")
        vr=vol.rolling(5).mean()/vol.rolling(20).mean()-1
        put("volume_speed",score(vr),vr*100,"%")
        rv20,rv60=rv(spy,20),rv(spy,60)
        put("vol_60d_change",avg(score(rv60),score(rv20-rv60)),rv60,"% annualized")
        put("valuation_percentile",vs,ratio,"SPY/MA200","proxy")
        spd=pct(ratio,20)
        put("valuation_speed",score(spd),spd,"% / 20d","proxy")

    if "SPY" in mk and "RSP" in mk:
        s,r=align(C("SPY"),C("RSP"))
        x=pct(s,60)-pct(r,60)
        put("concentration",score(x),x,"% SPY-RSP 60d","proxy")

    lev=[]
    if "NFCI" in fs: lev.append(score(F("NFCI")))
    if "BAMLH0A0HYM2" in fs: lev.append(score(F("BAMLH0A0HYM2")))
    if "HYG" in mk and "LQD" in mk:
        h,l=align(C("HYG"),C("LQD"))
        lev.append(score(h/l,False))
    if lev:
        put("leverage_liquidity",avg(*lev),avg(*lev),"score","proxy")

    sys=[]
    if vix is not None: sys.append(score(vix))
    if "BAMLH0A0HYM2" in fs:
        sys.append(score(F("BAMLH0A0HYM2")))
    elif "HYG" in mk and "LQD" in mk:
        h,l=align(C("HYG"),C("LQD"))
        sys.append(score(h/l,False))
    if "NFCI" in fs: sys.append(score(F("NFCI")))
    if "SPY" in mk:
        s=C("SPY")
        sys.append(score(-(s/s.cummax()-1)*100))
    systemic=None
    if sys:
        systemic=avg(*sys)
        put("systemic_risk",systemic,systemic,"score")
    if systemic is not None and len(systemic.dropna())>70:
        r60=avg(score(systemic,window=60),score(systemic.diff(60),window=252))
        put("risk_60d",r60,systemic,"systemic score")

    if "LOANINV" in fs:
        l=F("LOANINV")
        g=yoy(l)
        put("credit_cycle",avg(score(g),score(g.diff())),g,"% YoY")
    elif "HYG" in mk and "LQD" in mk:
        h,l=align(C("HYG"),C("LQD"))
        x=h/l
        put("credit_cycle",score(pct(x,60)),pct(x,60),"HYG/LQD 60d","proxy")

    curve=[]
    raw=None
    if "T10Y2Y" in fs:
        raw=F("T10Y2Y")
        curve.append(score(raw,False))
    if "T10Y3M" in fs:
        curve.append(score(F("T10Y3M"),False))
    if curve:
        put("yield_curve",avg(*curve),raw if raw is not None else avg(*curve),"% 10Y-2Y")
    elif "^TNX" in mk and "^IRX" in mk:
        a,b=align(C("^TNX"),C("^IRX"))
        spread=a-b
        put("yield_curve",score(spread,False),spread,"10Y-13W","proxy")

    for item in CONFIG:
        if item["id"] not in out:
            out[item["id"]]={**item,"score":None,"raw":None,"raw_unit":"","d1":None,"d2":None,"asof":None,"history":[],"quality":"source_error"}

    ordered=[out[x["id"]] for x in CONFIG]
    working=sum(x["score"] is not None for x in ordered)
    payload={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "status":"ok" if working>=20 else "partial",
        "working_count":working,
        "total_count":len(ordered),
        "errors":errors,
        "derivative_definition":{
            "d1":"一级导：当前指标分 - 上一期指标分（变化动能）",
            "d2":"二级导：当前一级导 - 上一期一级导（动能变化速率）"
        },
        "indicators":ordered
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"updated {working}/{len(ordered)} indicators")
    if errors:
        print(json.dumps(errors,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
