"""Descriptive cyclicity and causal walk-forward diagnostic; NEVER a trading forecast.

Prices are historical revised vendor observations. Forecast candidates are
calculated after signal CLOSE; outcome is a nonoverlapping future closing path.
No completed-box scores or ex-post news reconstruction enter features.
"""
from __future__ import annotations
import math
from collections import Counter
from statistics import mean, stdev

WEEKLY_LAGS=(1,2,4,8,13,26,52)
MIN_TRAIN_EVENTS=48
MIN_STATE_EVENTS=25


def pearson_lag(values:list[float],lag:int)->float|None:
    if len(values)<max(52,4*lag) or lag<1 or len(values)<=lag:return None
    a=values[:-lag];b=values[lag:];ma=mean(a);mb=mean(b)
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    den=(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))**.5
    return round(num/den,4) if den>1e-12 else None


def weekly_sector_relative(sector:list[list],spy:list[list])->list[list]:
    """Consecutive NONoverlapping 5-session sector-minus-SPY simple returns."""
    benchmarks={b[0]:float(b[4]) for b in spy}
    seq=[(row[0],float(row[4]),benchmarks[row[0]]) for row in sector if row[0] in benchmarks]
    result=[]
    for i in range(5,len(seq),5):
        prev,now=seq[i-5],seq[i]
        if min(prev[1],now[1],prev[2],now[2])>0:
            result.append([now[0],round(100*((now[1]/prev[1]-1)-(now[2]/prev[2]-1)),4)])
    return result


def sector_cyclicity(sector:list[list],spy:list[list])->dict:
    s=weekly_sector_relative(sector,spy)
    vals=[r[1] for r in s]
    lag=[{'lag_weeks':lag,'correlation':pearson_lag(vals,lag)} for lag in WEEKLY_LAGS]
    return {'status':'descriptive_not_proven_cycle' if len(vals)>=208 else 'insufficient_4year_weekly_history',
        'weeks':len(vals),'start':s[0][0] if s else None,'end':s[-1][0] if s else None,
        'weekly_relative_return_mean_pct':round(mean(vals),4) if vals else None,
        'lags':lag,'method':'nonoverlapping 5 aligned trading-session sector ETF minus SPY simple returns; autocorrelation is descriptive only',
        'p_values':None,'cycle_predictive_claim':False}


def _prior_state(close:list[float],i:int)->str:
    if i<200:raise ValueError('needs 200 prior daily observations')
    ma=sum(close[i-199:i+1])/200
    recent=[close[j]/close[j-1]-1 for j in range(i-19,i+1)]
    rv=stdev(recent)*(252**.5)
    return ('above' if close[i]>=ma else 'below')+'_' + ('highvol' if rv>=.25 else 'lowvol')


def walkforward_up_probability(bars:list[list],horizon:int)->dict:
    """Expanding, end-confirmed, nonoverlap 5/20-session directional evaluation.

    A previously observed sample is trainable only when j+h <= current i.
    Baseline is prior observed unconditional up frequency; conditional uses
    predeclared 200MA and 25%-annualized 20D-vol buckets with prior shrinkage.
    """
    if horizon not in (5,20):raise ValueError('only preregistered horizons 5, 20')
    closes=[float(r[4]) for r in bars];days=[str(r[0]) for r in bars]
    events=[];tested=[]
    for i in range(200,len(closes)-horizon,horizon):
        if closes[i]<=0 or closes[i+horizon]<=0:continue
        state=_prior_state(closes,i)
        matured=[e for e in events if e['end_i']<=i]
        if len(matured)>=MIN_TRAIN_EVENTS:
            base=sum(e['up'] for e in matured)/len(matured)
            same=[e for e in matured if e['state']==state]
            p=(sum(e['up'] for e in same)+25*base)/(len(same)+25) if len(same)>=MIN_STATE_EVENTS else base
            tested.append({'signal_date':days[i],'outcome_end':days[i+horizon],
                'p_pct':round(100*p,3),'baseline_pct':round(100*base,3),
                'observed_up':int(closes[i+horizon]>closes[i]),'state':state,
                'conditional_train_n':len(same),'all_train_n':len(matured)})
        events.append({'end_i':i+horizon,'up':int(closes[i+horizon]>closes[i]),'state':state})
    if len(tested)<60:
        return {'status':'insufficient_oos_samples','horizon_sessions':horizon,
                'n':len(tested),'minimum_evaluable':60,'claim':'none','reliability':[],
                'brier_model':None,'brier_base':None,'brier_skill':None,'yearly':[]}
    bmodel=mean((r['p_pct']/100-r['observed_up'])**2 for r in tested)
    bbase=mean((r['baseline_pct']/100-r['observed_up'])**2 for r in tested)
    bins=[]
    for lo in range(0,100,20):
        subset=[r for r in tested if lo<=r['p_pct']<(lo+20 if lo<80 else 101)]
        bins.append({'forecast_bucket':f'{lo}-{lo+20}%','n':len(subset),
                    'forecast_mean_pct':round(mean(r['p_pct'] for r in subset),2) if len(subset)>=10 else None,
                    'observed_up_pct':round(100*mean(r['observed_up'] for r in subset),2) if len(subset)>=10 else None})
    years=sorted(set(r['signal_date'][:4] for r in tested))
    annual=[]
    for year in years:
        group=[r for r in tested if r['signal_date'][:4]==year]
        bm=mean((r['p_pct']/100-r['observed_up'])**2 for r in group)
        bb=mean((r['baseline_pct']/100-r['observed_up'])**2 for r in group)
        annual.append({'year':year,'n':len(group),'model_brier':round(bm,5),
                       'base_brier':round(bb,5),'brier_difference':round(bb-bm,5)})
    improvement=bbase-bmodel
    return {'status':'exploratory_walkforward_not_a_live_forecast',
        'horizon_sessions':horizon,'n':len(tested),'first':tested[0]['signal_date'],
        'last_completed':tested[-1]['outcome_end'],
        'brier_model':round(bmodel,5),'brier_base':round(bbase,5),
        'brier_difference':round(improvement,5),
        'brier_skill':round(improvement/bbase,5) if bbase>0 else None,
        'interpretation':'brier_diff > 0 means lower sampled error than the strictly past-only unconditional baseline; does not establish stable forecasting ability',
        'reliability':bins,'yearly':annual,'claim':'exploratory, require true as-published data and independent forward samples'}


def cycle_report(instruments:dict,news:list)->dict:
    index=instruments.get('SPY',{}).get('bars') or []
    if not index:
        return {'status':'unavailable_no_spy','sectors':{},'directional':{},'news_status':'unavailable'}
    sectors={}
    for sym,item in instruments.items():
        if item.get('group')=='sector':
            sectors[sym]=sector_cyclicity(item.get('bars') or [],index)
    boxes={}
    for name in ('small','large'):
        ages=[int(b['days']) for b in instruments.get('SPY',{}).get('boxes',[])
              if b.get('scale')==name and b.get('end_at') and b.get('days')]
        ages.sort()
        boxes[name]={'completed_n':len(ages),'median_sessions':ages[len(ages)//2] if ages else None,
                     'min_sessions':min(ages) if ages else None,
                     'p90_sessions':ages[int(.9*(len(ages)-1))] if ages else None,
                     'warning':'completed episodes only: censoring and algorithm selection bias; never entry features'}
    return {'status':'research_only','cycle_proof':False,
        'directional':{str(h):walkforward_up_probability(index,h) for h in (5,20)},
        'sectors':sectors,'boxes':boxes,'news_status':'insufficient_for_cycle_tests' if len(news)<250 else 'requires_publication_time_audit',
        'warning':'Weekly correlations and historical walk-forward Brier diagnostics do not prove seasonality or actionable prediction; data source/coverage and model multiplicity remain research risks'}
