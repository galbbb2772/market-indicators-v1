from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import update_data as ud

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'docs'/'data'/'sector_rotation_robustness_v1.json'
SUMMARY=ROOT/'docs'/'data'/'sector_rotation_robustness_v1_summary.json'
SPEC='research/sector_rotation_robustness_v1/STUDY_SPEC.md'
CUT=pd.Timestamp('2026-10-02')
SECTORS=['XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY']


def xsec_ic(s,y,min_n=7):
    z=pd.concat([s.rename('s'),y.rename('y')],axis=1).dropna()
    if len(z)<min_n or z.s.nunique()<2 or z.y.nunique()<2: return None
    r=z.s.rank().corr(z.y.rank())
    return None if pd.isna(r) else float(r)


def agg(vals):
    x=np.asarray([v for v in vals if v is not None and np.isfinite(v)],float)
    return {'n':len(x),'mean':None if not len(x) else round(float(x.mean()),6),'median':None if not len(x) else round(float(np.median(x)),6),'positive_pct':None if not len(x) else round(float((x>0).mean()*100),2)}


def metric(score,outcome):
    vals=[]; spreads=[]; dates=[]
    for dt in score.index.intersection(outcome.index):
        s=score.loc[dt]; y=outcome.loc[dt]
        r=xsec_ic(s,y)
        if r is None: continue
        z=pd.concat([s.rename('s'),y.rename('y')],axis=1).dropna().sort_values('s')
        if len(z)<7: continue
        vals.append(r); spreads.append(float(z.tail(2).y.mean()-z.head(2).y.mean())); dates.append(dt)
    return pd.Series(vals,index=dates,dtype=float), pd.Series(spreads,index=dates,dtype=float)


def phase(s,h=10):
    x=s.dropna().sort_index(); full=float(x.mean()) if len(x) else None
    vals=[]
    for off in range(h):
        w=x.iloc[off::h]
        vals.append(None if len(w)==0 else float(w.mean()))
    ok=[v for v in vals if v is not None]
    same=None if full in (None,0) or not ok else 100*sum((v>0)==(full>0) for v in ok)/len(ok)
    return {'full_mean':None if full is None else round(full,6),'same_sign_pct':None if same is None else round(same,2),'phase_means':[None if v is None else round(v,6) for v in vals]}


def main():
    raw={}; errors={}
    for s in ['SPY']+SECTORS:
        try:
            x=ud.yahoo(s); x=x[x.index<=CUT]
            if x.empty: raise ValueError('empty')
            raw[s]=x
        except Exception as exc: errors[s]=repr(exc)
    if 'SPY' not in raw: raise RuntimeError(errors)
    av=[s for s in SECTORS if s in raw]
    if len(av)<9: raise RuntimeError(f'available={av} errors={errors}')
    close=pd.concat({s:raw[s]['Close'] for s in ['SPY']+av},axis=1).sort_index().ffill()
    close=close[close.index<=CUT]
    if close.index.max()!=CUT: raise RuntimeError(f'cutoff missing latest={close.index.max()}')
    spy=close.SPY; sec=close[av]
    ex20=sec.pct_change(20)*100
    ex20=ex20.sub(spy.pct_change(20)*100,axis=0)
    ex60=sec.pct_change(60)*100
    ex60=ex60.sub(spy.pct_change(60)*100,axis=0)
    scores={
        'rel20_only':ex20.rank(axis=1,pct=True),
        'rel60_only':ex60.rank(axis=1,pct=True),
    }
    scores['combo_20_60']=0.5*scores['rel20_only']+0.5*scores['rel60_only']
    outcomes={}
    for h in (5,10,20):
        r=(sec.shift(-h)/sec-1)*100
        b=(spy.shift(-h)/spy-1)*100
        outcomes[h]=r.sub(b,axis=0)

    variants={}
    for name,score in scores.items():
        ic,sp=metric(score,outcomes[10])
        years={}
        for y in sorted(set(ic.index.year)):
            idx=ic.index[ic.index.year==y]
            years[str(y)]={'ic':agg(ic.reindex(idx).tolist()),'top2_minus_bottom2':agg(sp.reindex(idx).tolist())}
        variants[name]={'ic10':agg(ic.tolist()),'top2_minus_bottom2_10d':agg(sp.tolist()),'yearly':years,'phase10_ic':phase(ic,10)}

    combo=scores['combo_20_60']
    secondary={}
    for h in (5,20):
        ic,sp=metric(combo,outcomes[h])
        secondary[str(h)]={'ic':agg(ic.tolist()),'top2_minus_bottom2':agg(sp.tolist()),'phase_ic':phase(ic,h)}

    # Leave-one-sector-out, 10D combo.
    loo=[]
    full_ic,_=metric(combo,outcomes[10])
    full_mean=float(full_ic.mean())
    for drop in av:
        cols=[c for c in av if c!=drop]
        ic,_=metric(combo[cols],outcomes[10][cols])
        loo.append({'excluded_sector':drop,'n_dates':len(ic),'mean_ic10':round(float(ic.mean()),6),'delta_vs_full':round(float(ic.mean()-full_mean),6),'same_sign_as_full':bool((ic.mean()>0)==(full_mean>0))})

    # Fixed contrarian portfolio and sector conditional contribution.
    contrarian=[]; dates=[]
    by_sector={s:{'top2':[],'bottom2':[]} for s in av}
    for dt in combo.index.intersection(outcomes[10].index):
        z=pd.concat([combo.loc[dt].rename('s'),outcomes[10].loc[dt].rename('y')],axis=1).dropna().sort_values('s')
        if len(z)<8: continue
        low=z.head(2); high=z.tail(2)
        contrarian.append(float(low.y.mean()-high.y.mean())); dates.append(dt)
        for s in low.index: by_sector[s]['bottom2'].append(float(low.loc[s,'y']))
        for s in high.index: by_sector[s]['top2'].append(float(high.loc[s,'y']))
    contra=pd.Series(contrarian,index=dates,dtype=float)
    sector_rows=[]
    for s in av:
        top=by_sector[s]['top2']; bot=by_sector[s]['bottom2']
        sector_rows.append({
            'sector':s,
            'top2_count':len(top),'top2_mean_10d_excess_pct':None if not top else round(float(np.mean(top)),6),
            'bottom2_count':len(bot),'bottom2_mean_10d_excess_pct':None if not bot else round(float(np.mean(bot)),6),
            'bottom_minus_top_pp':None if not top or not bot else round(float(np.mean(bot)-np.mean(top)),6),
        })

    # Decade/year sign stability summary.
    combo_year=variants['combo_20_60']['yearly']
    signs=[v['ic']['mean'] for v in combo_year.values() if v['ic']['mean'] is not None]
    yearly_same=None if not signs or full_mean==0 else 100*sum((v>0)==(full_mean>0) for v in signs)/len(signs)

    payload={
        'schema':'SECTOR-ROTATION-ROBUSTNESS-V1',
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'research_only':True,'diagnostic_only':True,'post_discovery_followup':True,'production_effect':'none',
        'study_spec':SPEC,'frozen_through_market_date':str(CUT.date()),
        'coverage':{'start':str(close.index.min().date()),'end':str(close.index.max().date()),'trading_days':len(close),'sector_count':len(av),'sectors':av,'download_errors':errors},
        'variants_10d':variants,
        'combo_secondary_horizons':secondary,
        'leave_one_sector_out_10d':loo,
        'combo_yearly_same_sign_pct':round(yearly_same,2) if yearly_same is not None else None,
        'contrarian_bottom2_minus_top2_10d':{'summary':agg(contra.tolist()),'nonoverlap_phase':phase(contra,10)},
        'sector_top_bottom_contribution_10d':sector_rows,
        'guardrails':{'may_change_production':False,'may_optimize_lookbacks':False,'may_drop_sector':False,'historical_results_count_as_forward_oos':False},
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    compact={
        'schema':'SECTOR-ROTATION-ROBUSTNESS-V1-SUMMARY','generated_at':payload['generated_at'],'research_only':True,
        'frozen_through_market_date':payload['frozen_through_market_date'],'coverage':payload['coverage'],
        'variants_10d':{k:{'ic10':v['ic10'],'top2_minus_bottom2_10d':v['top2_minus_bottom2_10d'],'phase10_ic':v['phase10_ic']} for k,v in variants.items()},
        'leave_one_sector_out_10d':loo,'combo_yearly_same_sign_pct':payload['combo_yearly_same_sign_pct'],
        'contrarian_bottom2_minus_top2_10d':payload['contrarian_bottom2_minus_top2_10d'],'sector_top_bottom_contribution_10d':sector_rows,
        'guardrails':payload['guardrails'],
    }
    SUMMARY.write_text(json.dumps(compact,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({
        'coverage':payload['coverage'],
        'variants':{k:[v['ic10']['mean'],v['top2_minus_bottom2_10d']['mean'],v['phase10_ic']['same_sign_pct']] for k,v in variants.items()},
        'loo_minmax':[min(x['mean_ic10'] for x in loo),max(x['mean_ic10'] for x in loo)],
        'yearly_same_sign_pct':payload['combo_yearly_same_sign_pct'],
        'contrarian':payload['contrarian_bottom2_minus_top2_10d'],
        'sector_contribution':sector_rows,
    },ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
