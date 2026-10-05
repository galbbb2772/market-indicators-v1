from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import update_data as ud

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "sector_rotation_stage2_v1.json"
SUMMARY = ROOT / "docs" / "data" / "sector_rotation_stage2_v1_summary.json"
SPEC = "research/sector_rotation_stage2_v1/STUDY_SPEC.md"
FROZEN_THROUGH = pd.Timestamp("2026-10-02")
SEED = 20261005
PLACEBO_N = 1000
SECTORS = ["XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY"]


def finite(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def xsec_spearman(a: pd.Series, b: pd.Series, min_n=8):
    z=pd.concat([a.rename('a'),b.rename('b')],axis=1).dropna()
    if len(z)<min_n or z.a.nunique()<2 or z.b.nunique()<2:
        return None
    r=z.a.rank(method='average').corr(z.b.rank(method='average'))
    return None if pd.isna(r) else float(r)


def aggregate(vals):
    x=np.asarray([v for v in vals if v is not None and np.isfinite(v)],dtype=float)
    if len(x)==0:
        return {"n":0,"mean":None,"median":None,"positive_pct":None}
    return {"n":int(len(x)),"mean":round(float(x.mean()),6),"median":round(float(np.median(x)),6),"positive_pct":round(float((x>0).mean()*100),2)}


def phase_robustness(s: pd.Series, horizon: int):
    x=s.dropna().sort_index()
    full=float(x.mean()) if len(x) else None
    phases=[]
    for off in range(horizon):
        w=x.iloc[off::horizon]
        phases.append({"offset":off,"n":len(w),"mean":None if len(w)==0 else round(float(w.mean()),6)})
    vals=[p['mean'] for p in phases if p['mean'] is not None]
    same=None
    if full is not None and full!=0 and vals:
        same=100*sum((v>0)==(full>0) for v in vals)/len(vals)
    return {"full_mean":None if full is None else round(full,6),"same_sign_pct":None if same is None else round(same,2),"phase_min":None if not vals else round(min(vals),6),"phase_max":None if not vals else round(max(vals),6),"phases":phases}


def regime_summary(metric: pd.Series, masks: dict[str,pd.Series]):
    out={}
    for k,m in masks.items():
        idx=metric.index.intersection(m.index[m.fillna(False)])
        out[k]=aggregate(metric.reindex(idx).dropna().tolist())
    return out


def placebo_mean_ic(score: pd.DataFrame, outcome: pd.DataFrame, dates: pd.Index, rng: np.random.Generator, reps=PLACEBO_N):
    obs=[]
    arrays=[]
    for dt in dates:
        z=pd.concat([score.loc[dt].rename('s'),outcome.loc[dt].rename('y')],axis=1).dropna()
        if len(z)<8 or z.s.nunique()<2 or z.y.nunique()<2:
            continue
        sr=z.s.rank(method='average').to_numpy(float)
        yr=z.y.rank(method='average').to_numpy(float)
        sr=(sr-sr.mean())/(sr.std() or 1.0)
        yr=(yr-yr.mean())/(yr.std() or 1.0)
        obs.append(float(np.mean(sr*yr)))
        arrays.append((sr,yr))
    if not arrays:
        return {"n_dates":0,"observed_mean_ic":None,"p_two_sided":None,"null_percentile":None,"replications":0}
    observed=float(np.mean(obs))
    null=[]
    for _ in range(reps):
        day=[]
        for sr,yr in arrays:
            yp=yr[rng.permutation(len(yr))]
            day.append(float(np.mean(sr*yp)))
        null.append(float(np.mean(day)))
    p=(1+sum(abs(v)>=abs(observed) for v in null))/(1+len(null))
    pct=100*sum(v<=observed for v in null)/len(null)
    return {"n_dates":len(arrays),"observed_mean_ic":round(observed,6),"p_two_sided":round(float(p),6),"null_percentile":round(float(pct),2),"replications":len(null)}


def main():
    symbols=['SPY']+SECTORS
    raw={}
    errors={}
    for sym in symbols:
        try:
            df=ud.yahoo(sym)
            df=df[df.index<=FROZEN_THROUGH].copy()
            if df.empty:
                raise RuntimeError('empty history')
            raw[sym]=df
        except Exception as exc:
            errors[sym]=repr(exc)
    if 'SPY' not in raw:
        raise RuntimeError(f'SPY missing: {errors}')
    available=[s for s in SECTORS if s in raw]
    if len(available)<9:
        raise RuntimeError(f'Need >=9 sectors, got {len(available)}; errors={errors}')

    close=pd.concat({s:raw[s]['Close'] for s in ['SPY']+available},axis=1).sort_index().ffill()
    volume=pd.concat({s:raw[s]['Volume'] for s in available},axis=1).sort_index()
    close=close[close.index<=FROZEN_THROUGH]
    volume=volume.reindex(close.index)
    if close.index.max()!=FROZEN_THROUGH:
        raise RuntimeError(f'Frozen date missing; latest={close.index.max()}')

    spy=close['SPY']
    sec=close[available]
    ret1=sec.pct_change()*100
    spy1=spy.pct_change()*100
    rel20=sec.pct_change(20)*100 - (spy.pct_change(20)*100).to_numpy()[:,None]
    rel60=sec.pct_change(60)*100 - (spy.pct_change(60)*100).to_numpy()[:,None]
    r20=rel20.rank(axis=1,pct=True,method='average')
    r60=rel60.rank(axis=1,pct=True,method='average')
    momentum=0.5*r20+0.5*r60

    abs_excess=(ret1.sub(spy1,axis=0)).abs()
    volratio=volume/volume.rolling(20,min_periods=15).mean()
    activity=0.5*abs_excess.rank(axis=1,pct=True,method='average')+0.5*volratio.rank(axis=1,pct=True,method='average')

    outcomes={}
    absout={}
    for h in (5,10,20):
        sr=(sec.shift(-h)/sec-1)*100
        br=(spy.shift(-h)/spy-1)*100
        ex=sr.sub(br,axis=0)
        outcomes[h]=ex
        if h in (5,10): absout[h]=ex.abs()

    # SPY regimes.
    ma200=spy.rolling(200).mean()
    rv20=spy.pct_change().rolling(20).std()*math.sqrt(252)*100
    masks={
        'above200':spy>=ma200,
        'below200':spy<ma200,
        'high_vol':rv20>=20,
        'low_vol':rv20<20,
    }

    horizons={}
    daily_ic={}
    daily_spread={}
    for h in (5,10,20):
        ics=[]; spreads=[]; dates=[]
        for dt in momentum.index:
            y=outcomes[h].loc[dt]
            s=momentum.loc[dt]
            r=xsec_spearman(s,y)
            if r is None:
                continue
            z=pd.concat([s.rename('s'),y.rename('y')],axis=1).dropna().sort_values('s')
            if len(z)<8: continue
            spread=float(z.tail(2).y.mean()-z.head(2).y.mean())
            dates.append(dt); ics.append(r); spreads.append(spread)
        ic_s=pd.Series(ics,index=dates,dtype=float)
        sp_s=pd.Series(spreads,index=dates,dtype=float)
        daily_ic[h]=ic_s; daily_spread[h]=sp_s
        yearly={}
        for yr in sorted(set(ic_s.index.year)):
            idx=ic_s.index[ic_s.index.year==yr]
            yearly[str(yr)]={"ic":aggregate(ic_s.reindex(idx).tolist()),"top2_minus_bottom2_pp":aggregate(sp_s.reindex(idx).tolist())}
        horizons[str(h)]= {
            'daily_cross_sectional_ic':aggregate(ic_s.tolist()),
            'top2_minus_bottom2_pp':aggregate(sp_s.tolist()),
            'yearly':yearly,
            'regime_ic':regime_summary(ic_s,masks),
            'regime_spread':regime_summary(sp_s,masks),
            'nonoverlap_phase_ic':phase_robustness(ic_s,h),
            'nonoverlap_phase_spread':phase_robustness(sp_s,h),
        }

    # Top-3 leader persistence.
    persistence={}
    for h in (5,10,20):
        vals=[]
        dates=list(momentum.index)
        for i in range(len(dates)-h):
            a=momentum.loc[dates[i]].dropna()
            b=momentum.loc[dates[i+h]].dropna()
            common=a.index.intersection(b.index)
            if len(common)<8: continue
            topa=set(a.reindex(common).nlargest(3).index)
            topb=set(b.reindex(common).nlargest(3).index)
            vals.append(len(topa&topb)/3)
        x=np.asarray(vals,float)
        persistence[str(h)]={"n":len(x),"mean_overlap_fraction":None if len(x)==0 else round(float(x.mean()),6),"median_overlap_fraction":None if len(x)==0 else round(float(np.median(x)),6),"all_three_pct":None if len(x)==0 else round(float((x==1).mean()*100),2)}

    # Activity predicts magnitude, not direction.
    activity_result={}
    activity_ic={}
    for h in (5,10):
        vals=[]; dates=[]
        for dt in activity.index:
            r=xsec_spearman(activity.loc[dt],absout[h].loc[dt])
            if r is not None:
                vals.append(r); dates.append(dt)
        s=pd.Series(vals,index=dates,dtype=float)
        activity_ic[h]=s
        activity_result[str(h)]={
            'daily_cross_sectional_ic_to_abs_excess':aggregate(s.tolist()),
            'regime':regime_summary(s,masks),
            'nonoverlap_phase':phase_robustness(s,h),
        }

    # Fixed primary placebo: 10D momentum direction and 10D activity magnitude.
    rng=np.random.default_rng(SEED)
    p_mom=placebo_mean_ic(momentum,outcomes[10],daily_ic[10].index,rng)
    p_act=placebo_mean_ic(activity,absout[10],activity_ic[10].index,rng)

    payload={
        'schema':'SECTOR-ROTATION-STAGE2-V1',
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'research_only':True,
        'diagnostic_only':True,
        'production_effect':'none',
        'study_spec':SPEC,
        'frozen_through_market_date':str(FROZEN_THROUGH.date()),
        'universe':{'benchmark':'SPY','configured_sectors':SECTORS,'available_sectors':available,'download_errors':errors},
        'coverage':{'start':str(close.index.min().date()),'end':str(close.index.max().date()),'trading_days':len(close),'sector_count':len(available)},
        'definitions':{
            'momentum_score':'0.5*xsec_percentile(sector20D-SPY20D)+0.5*xsec_percentile(sector60D-SPY60D)',
            'activity_score':'0.5*xsec_percentile(abs(sector1D-SPY1D))+0.5*xsec_percentile(volume/20Davgvolume)',
        },
        'momentum':horizons,
        'leader_persistence_top3':persistence,
        'activity':activity_result,
        'placebo':{'seed':SEED,'replications':PLACEBO_N,'momentum_10d_mean_daily_ic':p_mom,'activity_10d_abs_excess_mean_daily_ic':p_act},
        'guardrails':{'may_change_production':False,'may_optimize_thresholds':False,'may_optimize_weights':False,'historical_results_count_as_forward_oos':False},
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    compact={
        'schema':'SECTOR-ROTATION-STAGE2-V1-SUMMARY',
        'generated_at':payload['generated_at'],
        'research_only':True,
        'frozen_through_market_date':payload['frozen_through_market_date'],
        'coverage':payload['coverage'],
        'momentum':{h:{
            'daily_cross_sectional_ic':horizons[h]['daily_cross_sectional_ic'],
            'top2_minus_bottom2_pp':horizons[h]['top2_minus_bottom2_pp'],
            'regime_ic':horizons[h]['regime_ic'],
            'nonoverlap_phase_ic':horizons[h]['nonoverlap_phase_ic'],
        } for h in ('5','10','20')},
        'leader_persistence_top3':persistence,
        'activity':activity_result,
        'placebo':payload['placebo'],
        'guardrails':payload['guardrails'],
    }
    SUMMARY.write_text(json.dumps(compact,ensure_ascii=False,indent=2),encoding='utf-8')

    print(json.dumps({
        'coverage':payload['coverage'],
        'momentum':{h:[horizons[h]['daily_cross_sectional_ic']['mean'],horizons[h]['top2_minus_bottom2_pp']['mean'],horizons[h]['nonoverlap_phase_ic']['same_sign_pct']] for h in ('5','10','20')},
        'persistence':persistence,
        'activity10':activity_result['10']['daily_cross_sectional_ic_to_abs_excess'],
        'placebo':payload['placebo'],
    },ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
