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
# Daily importance model v1: structural importance + current extremeness + D1/D2 shocks.

FRED_IDS = [
    "NFCI", "BAMLH0A0HYM2", "T10Y2Y", "T10Y3M", "DGS2", "DGS10",
    "DTWEXBGS", "BAA10Y", "ISRATIO", "BUSINV", "MTSDS133FMS", "UNRATE",
    "ICSA", "DFF", "ECBDFR", "WALCL", "LOANINV"
]
YAHOO = [
    "SPY","RSP","IWM","QQQ","DIA","HYG","LQD","GLD","TLT","XLI","HG=F",
    "^VIX","CL=F","DX-Y.NYB","^TNX","^IRX",
    "NVDA","AAPL","MSFT","AMZN","GOOGL","META","TSLA","AVGO","AMD",
    "XLK","XLC","XLY","XLP","XLF","XLV","XLE","XLB","XLU","XLRE"
]


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



def bls_unemployment(errors: dict[str, str]) -> pd.Series | None:
    """Monthly U.S. unemployment rate from the BLS public API."""
    try:
        now = datetime.now(timezone.utc)
        payload = {
            "seriesid": ["LNS14000000"],
            "startyear": str(now.year - 9),
            "endyear": str(now.year),
        }
        r = HTTP.post(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        rows = (((data.get("Results") or {}).get("series") or [{}])[0].get("data") or [])
        pts = {}
        for row in rows:
            period = row.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue
            ts = pd.Timestamp(year=int(row["year"]), month=int(period[1:]), day=1)
            val = pd.to_numeric(row.get("value"), errors="coerce")
            if pd.isna(val):
                continue
            pts[ts] = float(val)
        if not pts:
            raise ValueError("BLS returned no unemployment observations")
        return pd.Series(pts, dtype=float).sort_index()
    except Exception as exc:
        errors["bls:unemployment"] = repr(exc)
        return None


def treasury_deficit(errors: dict[str, str]) -> pd.Series | None:
    """Monthly U.S. federal deficit/surplus from Treasury Fiscal Data."""
    try:
        url = (
            "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
            "v1/accounting/mts/mts_table_1?page[size]=1000&sort=-record_date"
        )
        rows = request(url, 12).json().get("data") or []
        if not rows:
            raise ValueError("Treasury returned no rows")
        df = pd.DataFrame(rows)
        value_cols = []
        if "current_month_dfct_sur_amt" in df.columns:
            value_cols = ["current_month_dfct_sur_amt"]
        if not value_cols:
            value_cols = [
                x for x in df.columns
                if ("deficit" in x.lower() or "dfct" in x.lower()) and "current" in x.lower() and "amt" in x.lower()
            ]
        if not value_cols:
            value_cols = [x for x in df.columns if ("deficit" in x.lower() or "dfct" in x.lower()) and "amt" in x.lower()]
        if not value_cols:
            raise ValueError("No deficit field found: " + ",".join(df.columns))
        vcol = value_cols[0]
        df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
        df[vcol] = pd.to_numeric(df[vcol], errors="coerce")
        df = df.dropna(subset=["record_date", vcol]).copy()
        if "record_type_cd" in df.columns:
            monthly = df[df["record_type_cd"].astype(str).str.upper().eq("MTH")]
            if not monthly.empty:
                df = monthly
        if "classification_desc" in df.columns:
            desc = df["classification_desc"].astype(str)
            preferred = df[desc.str.contains("deficit|surplus", case=False, regex=True, na=False)]
            if not preferred.empty:
                df = preferred
        # Treasury table can expose more than one comparison row per record date.
        # Choose the row with the largest absolute monthly amount, which is the
        # government-wide total rather than a component/subtotal.
        df["_abs"] = df[vcol].abs()
        df = df.sort_values(["record_date", "_abs"]).groupby("record_date", as_index=False).tail(1)
        s = pd.Series(df[vcol].values, index=df["record_date"], dtype=float).sort_index()
        if s.empty:
            raise ValueError("No usable Treasury deficit observations")
        return s
    except Exception as exc:
        errors["treasury:fiscal_deficit"] = repr(exc)
        return None


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
    series_store = {}
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
            ss = pd.Series(s).dropna().astype(float).clip(0, 100).sort_index()
            if ss.empty:
                raise ValueError("empty score")
            series_store[k] = ss
            out[k] = pack(meta[k], ss, raw, unit, quality)
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
    bch=bc.get("history") or []
    if bch:
        pts={}
        for row in bch:
            if row.get("value") is None or not row.get("asof"):
                continue
            pts[pd.Timestamp(row["asof"])]=float(row["value"])
        s=pd.Series(pts,dtype=float).sort_index()
        if not s.empty:
            put("buffett_cash",s.clip(0,100),s,"%","manual")
    elif bc.get("value") is not None:
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
    elif "XLI" in mk and "SPY" in mk and "HG=F" in mk:
        xli,spy=align(C("XLI"),C("SPY"))
        cyc=pct(xli,120)-pct(spy,120)
        copper=pct(C("HG=F"),120)
        put("inventory_cycle",avg(score(cyc),score(copper)),cyc,"% XLI-SPY 120d","proxy")

    if "MTSDS133FMS" in fs:
        f=F("MTSDS133FMS").rolling(12,min_periods=6).sum()
        put("fiscal_deficit",score(-f),f,"USD mn / 12m")
    else:
        tdef = treasury_deficit(errors)
        if tdef is not None:
            # Treasury reports deficit/surplus monthly; higher positive deficit = more fiscal pressure.
            put("fiscal_deficit",score(tdef,window=120),tdef,"USD / month","direct")

    emp=[]
    if "UNRATE" in fs: emp.append(score(F("UNRATE")))
    if "ICSA" in fs: emp.append(score(F("ICSA")))
    if emp:
        put("employment",avg(*emp),F("UNRATE") if "UNRATE" in fs else avg(*emp),"% unemployment")
    else:
        unrate = bls_unemployment(errors)
        if unrate is not None:
            put("employment",score(unrate),unrate,"% unemployment","direct")

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


    # ---------- Core 61 daily proxy layer ----------
    # The master list contains conceptual indicators.  Where a dedicated
    # text/fundamental/issuance feed is not connected yet, we intentionally
    # leave the indicator empty instead of fabricating a value.

    def hist_score(key):
        s = series_store.get(key)
        if s is not None and not s.empty:
            return s
        obj = out.get(key) or {}
        rows = obj.get("history") or []
        if not rows:
            return None
        pts = {pd.Timestamp(x["date"]): float(x["score"]) for x in rows if x.get("score") is not None}
        return pd.Series(pts, dtype=float).sort_index() if pts else None

    def inv_score(s):
        return 100.0 - s

    def basket_volume_signal(symbols):
        parts=[]
        raws=[]
        for sym in symbols:
            if sym not in mk:
                continue
            v=V(sym)
            vr=v.rolling(5).mean()/v.rolling(60).mean()
            parts.append(score(vr))
            raws.append(vr)
        if not parts:
            return None,None
        return avg(*parts), avg(*raws)

    def basket_vol_signal(symbols):
        parts=[]
        raws=[]
        for sym in symbols:
            if sym not in mk:
                continue
            x=rv(C(sym),20)
            parts.append(score(x))
            raws.append(x)
        if not parts:
            return None,None
        return avg(*parts), avg(*raws)

    def put_new(key, s, raw=None, unit="", quality="proxy"):
        if key in meta and key not in out and s is not None:
            put(key,s,raw if raw is not None else s,unit,quality)

    # Market topic heat: activity + option-volatility attention proxy.
    p=[]
    for k in ("volume_speed","options_anomaly"):
        h=hist_score(k)
        if h is not None: p.append(h)
    if "SPY" in mk:
        p.append(score(abs(pct(C("SPY"),5))))
    if p: put_new("market_topic_heat",avg(*p),avg(*p),"score","proxy")

    # Cross-asset linkage: absolute rolling correlation between broad US equities
    # and gold / Treasuries / oil.
    if all(x in mk for x in ("SPY","QQQ","DIA")):
        er=pd.concat([C("SPY").pct_change(),C("QQQ").pct_change(),C("DIA").pct_change()],axis=1).mean(axis=1)
        cors=[]
        for sym in ("GLD","TLT","CL=F"):
            if sym in mk:
                rr=C(sym).pct_change().reindex(er.index).ffill()
                cors.append(er.rolling(60).corr(rr).abs())
        if cors:
            link=avg(*cors)
            put_new("cross_asset_correlation",score(link),link,"|corr| 60d","composite")

    # Hiking-cycle entry proxy: sustained rise in long rates.
    if "^TNX" in mk:
        y=C("^TNX")
        tighten=avg(score(pct(y,20)),score(pct(y,60)))
        put_new("global_cb_cycle_entry",tighten,pct(y,60),"% 10Y 60d","proxy")

    if "IWM" in mk:
        parts=[]
        if vix is not None: parts.append(score(vix))
        parts.append(score(-pct(C("IWM"),20)))
        put_new("retail_panic",avg(*parts),pct(C("IWM"),20),"% IWM 20d","proxy")

    p=[x for x in (hist_score("high_yield"),hist_score("liquidity_risk"),hist_score("market_fear")) if x is not None]
    if p: put_new("institutional_panic",avg(*p),avg(*p),"score","proxy")

    p=[x for x in (hist_score("concentration"),hist_score("cross_asset_correlation")) if x is not None]
    if "SPY" in mk: p.append(score(rv(C("SPY"),20),False))
    if p: put_new("quant_crowding",avg(*p),avg(*p),"score","proxy")

    p=[x for x in (hist_score("market_support"),) if x is not None]
    if "SPY" in mk: p.append(score(pct(C("SPY"),20)))
    if "IWM" in mk: p.append(score(pct(C("IWM"),20)))
    if p: put_new("money_making_effect",avg(*p),avg(*p),"score","composite")

    # Geopolitical market proxies: only price reaction, not news classification.
    gp=[]
    if vix is not None: gp.append(score(pct(vix,5)))
    if "GLD" in mk: gp.append(score(abs(pct(C("GLD"),5))))
    if "CL=F" in mk: gp.append(score(abs(pct(C("CL=F"),5))))
    if gp:
        g=avg(*gp)
        put_new("geo_news_impact",g,g,"score","proxy")
        lag=[]
        if "SPY" in mk: lag.append(score(abs(pct(C("SPY"),5))))
        if "GLD" in mk: lag.append(score(abs(pct(C("GLD"),10))))
        if "CL=F" in mk: lag.append(score(abs(pct(C("CL=F"),10))))
        if lag: put_new("geo_lag_reaction",avg(*lag),avg(*lag),"score","proxy")

    p=[x for x in (hist_score("inventory_cycle"),) if x is not None]
    if "XLI" in mk and "SPY" in mk:
        a,b=align(C("XLI"),C("SPY"))
        p.append(score(pct(a,120)-pct(b,120)))
    if "HG=F" in mk: p.append(score(pct(C("HG=F"),120)))
    if p: put_new("business_cycle",avg(*p),avg(*p),"score","proxy")

    p=[x for x in (hist_score("geo_news_impact"),hist_score("market_fear"),hist_score("gold"),hist_score("oil")) if x is not None]
    if p: put_new("geopolitical_risk",avg(*p),avg(*p),"score","proxy")

    if "LOANINV" in fs:
        loans=F("LOANINV")
        put_new("us_loans_total",score(loans),loans,"index","direct")
        g=yoy(loans)
        put_new("us_loans_speed",avg(score(g),score(g.diff())),g,"% YoY","direct")
    else:
        h=hist_score("credit_cycle")
        if h is not None:
            put_new("us_loans_total",h,h,"credit proxy","proxy")
            put_new("us_loans_speed",h,h,"credit proxy","proxy")

    p=[x for x in (hist_score("concentration"),hist_score("retail_participation")) if x is not None]
    if p: put_new("retail_holdings_concentration",avg(*p),avg(*p),"score","proxy")

    if "SPY" in mk and "^TNX" in mk:
        sr=C("SPY").pct_change()
        dy=C("^TNX").diff().reindex(sr.index).ffill()
        sens=sr.rolling(60).corr(dy)
        put_new("rate_cycle_sensitivity",score(sens.abs()),sens,"corr 60d","direct")

    ps=[x for x in (hist_score("market_support"),hist_score("money_making_effect")) if x is not None]
    mf=hist_score("market_fear")
    if mf is not None: ps.append(inv_score(mf))
    if ps: put_new("market_optimism",avg(*ps),avg(*ps),"score","composite")

    ps=[x for x in (hist_score("market_fear"),hist_score("largecap_panic"),hist_score("institutional_panic")) if x is not None]
    if ps: put_new("market_pessimism",avg(*ps),avg(*ps),"score","composite")

    lr=hist_score("liquidity_risk")
    if lr is not None:
        put_new("market_liquidity",inv_score(lr),inv_score(lr),"score","composite")

    if "SPY" in mk:
        s=C("SPY")
        dist=(s/s.rolling(20).mean()-1)*100
        over=score(dist.abs())
        put_new("market_overextension",over,dist,"% vs MA20","direct")
        spd=abs(pct(s,5))
        put_new("market_move_speed",score(spd),spd,"% abs 5d","direct")

    h=hist_score("concentration")
    if h is not None: put_new("breadth_concentration",h,h,"score","proxy")

    if "IWM" in mk and "SPY" in mk:
        a,b=align(C("IWM"),C("SPY"))
        rel=pct(a,60)-pct(b,60)
        sm=avg(score(pct(a,60)),score(rel))
        put_new("sme_survival_growth",sm,rel,"% IWM-SPY 60d","proxy")

    mag7=["NVDA","AAPL","MSFT","AMZN","GOOGL","META","TSLA"]
    ai7=["NVDA","MSFT","GOOGL","AMZN","META","AVGO","AMD"]
    ss,raw=basket_volume_signal(mag7)
    put_new("mag7_volume",ss,raw,"5d/60d volume","composite")
    ss,raw=basket_vol_signal(mag7)
    put_new("mag7_volatility",ss,raw,"% RV20","composite")
    ss,raw=basket_volume_signal(ai7)
    put_new("ai7_volume",ss,raw,"5d/60d volume","composite")
    ss,raw=basket_vol_signal(ai7)
    put_new("ai7_volatility",ss,raw,"% RV20","composite")

    # Mega-cap liquidity blow-up proxy combines basket volatility and broad fear.
    p=[x for x in (hist_score("mag7_volatility"),hist_score("market_fear"),hist_score("liquidity_risk")) if x is not None]
    if p: put_new("mega_liquidity_blowup",avg(*p),avg(*p),"score","proxy")

    op=hist_score("market_optimism")
    pe=hist_score("market_pessimism")
    if op is not None and pe is not None:
        a,b=align(op,pe)
        bias=(a+(100-b))/2
        put_new("market_bias",bias,bias,"score","composite")

    if "QQQ" in mk:
        qv=rv(C("QQQ"),20)
        put_new("tech100_volatility",score(qv),qv,"% RV20","proxy")

    sector_etfs={
        "sector_it_vol":"XLK","sector_comm_vol":"XLC","sector_cons_disc_vol":"XLY",
        "sector_cons_staples_vol":"XLP","sector_fin_vol":"XLF","sector_health_vol":"XLV",
        "sector_industrial_vol":"XLI","sector_energy_vol":"XLE","sector_materials_vol":"XLB",
        "sector_utilities_vol":"XLU","sector_realestate_vol":"XLRE"
    }
    for key,sym in sector_etfs.items():
        if sym in mk:
            vv=rv(C(sym),20)
            put_new(key,score(vv),vv,"% RV20","proxy")


    for item in CONFIG:
        if item["id"] not in out:
            out[item["id"]]={**item,"score":None,"raw":None,"raw_unit":"","d1":None,"d2":None,"asof":None,"history":[],"quality":"source_error"}

    ordered=[out[x["id"]] for x in CONFIG]

    # Market-state contribution model:
    # 0-100 score where >50 means healthier/more supportive conditions and
    # <50 means more stressed/negative conditions. Core61 gets full weight;
    # legacy supplemental factors get 35% weight to reduce double-counting.
    state_rows=[]
    for item in ordered:
        item["market_contribution_points"]=None
        pol=float(item.get("impact_polarity",0) or 0)
        if item.get("score") is None or pol == 0:
            continue
        layer_mult=1.0 if item.get("layer")=="core61" else 0.35
        w=float(item.get("importance_score",50))*layer_mult
        state_rows.append((item,w,pol))
    state_denom=sum(w for _,w,_ in state_rows) or 1.0
    state_edge=0.0
    state_d1=0.0
    state_d2=0.0
    for item,w,pol in state_rows:
        edge=pol*((float(item["score"])-50.0)/50.0)
        state_edge += w*edge
        state_d1 += w*pol*float(item.get("d1") or 0.0)
        state_d2 += w*pol*float(item.get("d2") or 0.0)
        item["market_contribution_points"]=round((w/state_denom)*pol*(float(item["score"])-50.0),3)
    market_state=float(np.clip(50.0+50.0*(state_edge/state_denom),0,100))
    market_state_d1=state_d1/state_denom
    market_state_d2=state_d2/state_denom
    # Four-zone traffic-light framework.
    # This is an operational research regime, not a buy/sell instruction.
    if market_state >= 65:
        market_state_label="supportive"
        traffic_light="green"
        execution_range="70–100%"
        execution_posture="积极/正常执行：允许策略按自身信号充分参与，但仍受原有风控约束。"
    elif market_state >= 55:
        market_state_label="mild_supportive"
        traffic_light="blue"
        execution_range="50–70%"
        execution_posture="正常偏精选：保留主要机会，降低低质量和边缘信号的执行优先级。"
    elif market_state >= 45:
        market_state_label="neutral"
        traffic_light="yellow"
        execution_range="25–50%"
        execution_posture="谨慎执行：缩小执行强度、提高确认门槛，优先等待结构与D1/D2改善。"
    else:
        market_state_label="stress"
        traffic_light="red"
        execution_range="0–25%"
        execution_posture="防守优先：尽量压低新增风险，以风险控制、流动性和对冲为主。"

    # Daily market structure: trend-vs-range plus volatility regime.
    market_structure="unknown"
    volatility_state="unknown"
    market_regime="unknown"
    trend_efficiency=None
    vol_percentile=None
    if "SPY" in mk:
        _spy=C("SPY").dropna()
        _r=_spy.pct_change()
        _eff=(_spy.pct_change(20).abs() / _r.abs().rolling(20).sum()).replace([np.inf,-np.inf],np.nan)
        _rv20=rv(_spy,20)
        _vp=rolling_percentile(_rv20,756)
        if not _eff.dropna().empty:
            trend_efficiency=float(_eff.dropna().iloc[-1])
        if not _vp.dropna().empty:
            vol_percentile=float(_vp.dropna().iloc[-1])
        ret20=float(_spy.pct_change(20).dropna().iloc[-1]*100) if not _spy.pct_change(20).dropna().empty else 0.0
        if trend_efficiency is not None and trend_efficiency >= 0.35:
            market_structure="上行趋势" if ret20 >= 0 else "下行趋势"
        else:
            market_structure="区域震荡"
        if vol_percentile is None:
            volatility_state="常态波动"
        elif vol_percentile >= 70:
            volatility_state="高波动"
        elif vol_percentile <= 30:
            volatility_state="低波动"
        else:
            volatility_state="常态波动"
        market_regime=f"{volatility_state} · {market_structure}"

    # Historical validation of the traffic-light score.
    # This is an exploratory, non-point-in-time diagnostic: some macro series are
    # indexed by observation date rather than their exact public release timestamp.
    regime_backtest={
        "status":"unavailable",
        "note":"Exploratory only; not a point-in-time production backtest."
    }
    if "SPY" in mk and series_store:
        try:
            spy_bt=C("SPY").dropna().sort_index()
            idx=spy_bt.index
            weighted_edges=[]
            weights=[]
            cover=[]
            for cfg in CONFIG:
                key=cfg["id"]
                pol=float(cfg.get("impact_polarity",0) or 0)
                s=series_store.get(key)
                if pol == 0 or s is None or s.empty:
                    continue
                layer_mult=1.0 if cfg.get("layer")=="core61" else 0.35
                w=float(cfg.get("importance_score",50))*layer_mult
                aligned=s.reindex(idx).ffill()
                edge=pol*(aligned-50.0)
                weighted_edges.append(edge*w)
                weights.append(aligned.notna().astype(float)*w)
                cover.append(aligned.notna().astype(int))
            if weighted_edges:
                num=pd.concat(weighted_edges,axis=1).sum(axis=1,min_count=1)
                den=pd.concat(weights,axis=1).sum(axis=1,min_count=1)
                cov=pd.concat(cover,axis=1).sum(axis=1)
                hist_state=(50.0+num/den).clip(0,100)
                hist_state=hist_state.where((den>0)&(cov>=20)).dropna()
                bt=pd.DataFrame({"state":hist_state,"close":spy_bt.reindex(hist_state.index)})
                bt["fwd_1d"]=(bt["close"].shift(-1)/bt["close"]-1)*100
                bt["fwd_5d"]=(bt["close"].shift(-5)/bt["close"]-1)*100
                bt["fwd_20d"]=(bt["close"].shift(-20)/bt["close"]-1)*100
                lows=[]
                vals=bt["close"].to_numpy(dtype=float)
                for i in range(len(bt)):
                    tail=vals[i+1:min(len(vals),i+21)]
                    lows.append(float((np.nanmin(tail)/vals[i]-1)*100) if len(tail) else np.nan)
                bt["worst_20d"]=lows

                def light_for(v, t1=45.0, t2=55.0, t3=65.0):
                    if v < t1: return "red"
                    if v < t2: return "yellow"
                    if v < t3: return "blue"
                    return "green"

                def summarize_thresholds(t1,t2,t3):
                    x=bt.copy()
                    x["light"]=[light_for(v,t1,t2,t3) for v in x["state"]]
                    stats={}
                    for light in ("red","yellow","blue","green"):
                        g=x[x["light"]==light]
                        valid20=g["fwd_20d"].dropna()
                        stats[light]={
                            "n":int(len(g)),
                            "avg_state":round(float(g["state"].mean()),2) if len(g) else None,
                            "avg_fwd_1d_pct":round(float(g["fwd_1d"].mean()),3) if g["fwd_1d"].notna().any() else None,
                            "avg_fwd_5d_pct":round(float(g["fwd_5d"].mean()),3) if g["fwd_5d"].notna().any() else None,
                            "avg_fwd_20d_pct":round(float(valid20.mean()),3) if len(valid20) else None,
                            "median_fwd_20d_pct":round(float(valid20.median()),3) if len(valid20) else None,
                            "positive_20d_rate_pct":round(float((valid20>0).mean()*100),1) if len(valid20) else None,
                            "avg_worst_20d_pct":round(float(g["worst_20d"].mean()),3) if g["worst_20d"].notna().any() else None
                        }
                    return stats

                current_stats=summarize_thresholds(45,55,65)

                # Small grid search for a candidate split. It is deliberately
                # constrained and labelled exploratory to avoid overfitting.
                candidates=[]
                for t1 in np.arange(40,50.1,2.5):
                    for t2 in np.arange(50,60.1,2.5):
                        for t3 in np.arange(60,70.1,2.5):
                            if not (t1<t2<t3):
                                continue
                            st=summarize_thresholds(float(t1),float(t2),float(t3))
                            if min(st[z]["n"] for z in ("red","yellow","blue","green")) < 12:
                                continue
                            means=[st[z]["avg_fwd_20d_pct"] for z in ("red","yellow","blue","green")]
                            if any(v is None for v in means):
                                continue
                            monotonic=sum(1 for a,b in zip(means,means[1:]) if b>=a)
                            spread=means[-1]-means[0]
                            rates=[st[z]["positive_20d_rate_pct"] or 0 for z in ("red","yellow","blue","green")]
                            rate_spread=(rates[-1]-rates[0])/100.0
                            score_obj=3.0*monotonic + spread + rate_spread
                            candidates.append((score_obj,float(t1),float(t2),float(t3),st))
                best=max(candidates,key=lambda z:z[0]) if candidates else None

                corr_df=bt[["state","fwd_20d"]].dropna()
                corr=float(corr_df["state"].corr(corr_df["fwd_20d"],method="spearman")) if len(corr_df)>10 else None
                regime_backtest={
                    "status":"ok",
                    "sample_start":str(bt.index.min().date()),
                    "sample_end":str(bt.index.max().date()),
                    "observations":int(len(bt)),
                    "score_min":round(float(bt["state"].min()),2),
                    "score_max":round(float(bt["state"].max()),2),
                    "spearman_state_vs_fwd20":round(corr,3) if corr is not None and np.isfinite(corr) else None,
                    "current_thresholds":{"red_below":45.0,"yellow_below":55.0,"blue_below":65.0,"green_from":65.0},
                    "current_stats":current_stats,
                    "exploratory_candidate":({
                        "red_below":best[1],
                        "yellow_below":best[2],
                        "blue_below":best[3],
                        "green_from":best[3],
                        "objective":round(float(best[0]),3),
                        "stats":best[4]
                    } if best else None),
                    "history":[{"date":str(i.date()),"score":round(float(v),2)} for i,v in hist_state.tail(756).items()],
                    "note":"Exploratory only. Uses available reconstructed indicator histories and may contain observation-date/release-date mismatch for macro series. Do not treat the candidate thresholds as final until a point-in-time out-of-sample validation is done."
                }
        except Exception as exc:
            errors["regime_backtest"]=repr(exc)

    positive=sorted(
        [x for x in ordered if (x.get("market_contribution_points") or 0)>0],
        key=lambda x:x["market_contribution_points"],reverse=True
    )
    negative=sorted(
        [x for x in ordered if (x.get("market_contribution_points") or 0)<0],
        key=lambda x:x["market_contribution_points"]
    )

    # 每日重要度：把长期“市场重要性”与当天异常程度、D1、D2结合。
    # 这是“今天该优先看什么”的关注分，不是买卖信号，也不代表方向。
    # 50% 基础重要性 + 30% Level偏离中性程度 + 12% D1冲击 + 8% D2加速度。
    for item in ordered:
        if item.get("score") is None:
            item["daily_importance_score"] = None
            item["daily_importance_rank"] = None
            item["attention_state"] = "no_data"
            continue
        base = float(item.get("importance_score", 50))
        extreme = min(100.0, abs(float(item["score"]) - 50.0) * 2.0)
        d1_shock = min(100.0, abs(float(item.get("d1") or 0.0)) * 5.0)
        d2_shock = min(100.0, abs(float(item.get("d2") or 0.0)) * 4.0)
        daily = 0.50 * base + 0.30 * extreme + 0.12 * d1_shock + 0.08 * d2_shock
        item["daily_importance_score"] = round(float(np.clip(daily, 0, 100)), 2)
        if daily >= 80:
            item["attention_state"] = "critical"
        elif daily >= 65:
            item["attention_state"] = "high"
        elif daily >= 50:
            item["attention_state"] = "watch"
        else:
            item["attention_state"] = "normal"

    ranked = sorted(
        [x for x in ordered if x.get("daily_importance_score") is not None],
        key=lambda x: (-x["daily_importance_score"], x.get("importance_rank", 999))
    )
    for rank, item in enumerate(ranked, 1):
        item["daily_importance_rank"] = rank

    denom = sum(float(x.get("importance_score", 50)) for x in ranked) or 1.0
    market_attention = sum(
        float(x["daily_importance_score"]) * float(x.get("importance_score", 50))
        for x in ranked
    ) / denom

    working=sum(x["score"] is not None for x in ordered)
    payload={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "status":"ok" if working>=20 else "partial",
        "working_count":working,
        "total_count":len(ordered),
        "market_attention_score":round(float(market_attention),2),
        "market_state_score":round(market_state,2),
        "market_state_d1":round(float(market_state_d1),2),
        "market_state_d2":round(float(market_state_d2),2),
        "market_state_label":market_state_label,
        "traffic_light":traffic_light,
        "traffic_framework":{
            "green":{"range":"65–100","meaning":"支持环境","execution_range":"70–100%","description":"结构整体健康，风险与流动性条件相对支持。"},
            "blue":{"range":"55–64.99","meaning":"中性偏支持","execution_range":"50–70%","description":"环境仍可执行，但更适合精选信号。"},
            "yellow":{"range":"45–54.99","meaning":"谨慎/过渡区","execution_range":"25–50%","description":"结构分化或边际恶化，需提高确认门槛。"},
            "red":{"range":"0–44.99","meaning":"压力区","execution_range":"0–25%","description":"系统压力占优，防守与风险控制优先。"}
        },
        "execution_range":execution_range,
        "execution_posture":execution_posture,
        "execution_note":"执行区间代表研究框架中的执行强度/风险预算参考，不等同于账户仓位或买卖建议；需要后续用历史回测校准。",
        "market_structure":market_structure,
        "volatility_state":volatility_state,
        "market_regime":market_regime,
        "regime_backtest":regime_backtest,
        "trend_efficiency":round(trend_efficiency,4) if trend_efficiency is not None else None,
        "volatility_percentile":round(vol_percentile,2) if vol_percentile is not None else None,
        "top_positive_contributors":[{"id":x["id"],"name":x["name"],"points":x["market_contribution_points"]} for x in positive[:8]],
        "top_negative_contributors":[{"id":x["id"],"name":x["name"],"points":x["market_contribution_points"]} for x in negative[:8]],
        "composite_method":{
            "score":"50 + importance-weighted signed deviation from each factor's neutral level",
            "core_weight":"core61 full weight",
            "supplemental_weight":"legacy supplemental factors use 35% weight to reduce double-counting",
            "direction":"higher composite score = more supportive/healthy market state; lower = more stressed/negative"
        },
        "importance_method":{
            "base":"长期基础重要性 0-100，由宏观传导、系统性、领先性和市场覆盖面排序",
            "daily":"每日重要度 = 50%基础重要性 + 30%Level极端度 + 12%D1冲击 + 8%D2加速度",
            "note":"每日重要度只表示今天值得优先关注的程度，不代表看多/看空或交易信号"
        },
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
