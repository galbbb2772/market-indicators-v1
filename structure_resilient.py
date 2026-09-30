"""Research-only bootstrap: direct Treasury/BLS first; failed feeds preserve cached data.
No public JSON is written until operator confirms all vendor publication permissions.
"""
from __future__ import annotations
import argparse, csv, io, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
import requests
import build_structure_lab as lab
from macro_sources import treasury_spread, bls_unrate

ROOT=Path(__file__).resolve().parent
TARGET=ROOT/'docs/data/structure_lab.json'
FULL_MACRO=lab.MACRO.copy()
DIRECT={'T10Y3M':treasury_spread,'UNRATE':bls_unrate}


def _previous():
    try:return json.loads(TARGET.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}


def assemble(prices=True,existing=None,optional_fred=False):
    prior=existing if existing is not None else _previous()
    # Do not let the legacy builder block on FRED before primary sources can run.
    lab.MACRO={}
    if prices:
        out=lab.build(prior)
    else:
        out={'schema':'STRUCTURE-LAB-V1','generated_at':datetime.now(timezone.utc).isoformat(),
             'instruments':prior.get('instruments',{}), 'news_tension':prior.get('news_tension',[]),
             'news_status':prior.get('news_status','no_news'),'errors':dict(prior.get('errors',{})),
             'policy':dict(prior.get('policy',{}))}
    out['macro']=dict(prior.get('macro') or {})
    session=requests.Session()
    session.headers.update({'User-Agent':'MarketStructureLab/1.0 (research)'})
    for key,download in DIRECT.items():
        prev_rows=out['macro'].get(key,{}).get('observations') or []
        last_month=prev_rows[-1][0] if prev_rows else None
        try:
            source=download(session,last_month=last_month)
            combined={month:value for month,value in prev_rows}
            combined.update({month:value for month,value in source['observations']})
            history=[[month,combined[month]] for month in sorted(combined)]
            label='（US Treasury par-yield proxy）' if key=='T10Y3M' else '（US BLS direct）'
            out['macro'][key]={'name':FULL_MACRO[key]+label, **source,
                'observations':history,'start':history[0][0],'end':history[-1][0],
                'status':'partial' if source['failed_years'] else 'refreshed'}
            print('DIRECT',key,source['source'],len(history),source['completeness'],flush=True)
        except Exception as exc:
            out['errors'][key]=type(exc).__name__+': '+str(exc)[:140]
            if key in out['macro']:out['macro'][key]['status']='stale_cached'
            print('DIRECT UNAVAILABLE',key,out['errors'][key],flush=True)
    for key in FULL_MACRO:
        if key in DIRECT:continue
        if not optional_fred:
            if key not in out['macro']:
                out['errors'][key]='Direct official provider unverified; no synthetic series'
            continue
        try:
            # Research-only optional fallback: do NOT redistribute before auditing
            # FRED terms and any underlying third-party rights.
            url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={key}'
            r=session.get(url,timeout=7);r.raise_for_status()
            monthly={}
            for row in csv.DictReader(io.StringIO(r.text)):
                try:monthly[row['DATE'][:7]]=float(row[key])
                except (ValueError,KeyError,TypeError):pass
            if not monthly:raise ValueError('No valid FRED observations')
            hist=[[m,round(v,4)] for m,v in sorted(monthly.items())]
            out['macro'][key]={'name':FULL_MACRO[key],'observations':hist,
                'start':hist[0][0],'end':hist[-1][0], 'source':'FRED_OPTIONAL_RESEARCH',
                'point_in_time':False,'frequency':'last_observation_each_month','status':'refreshed'}
        except Exception as exc:
            out['errors'][key]=type(exc).__name__+': '+str(exc)[:140]
            if key in out['macro']:out['macro'][key]['status']='stale_cached'
    out['policy']['macro']='Direct Treasury par-yield proxy and direct BLS unemployment; revised not publication-time data'
    out['policy']['publication_gate']='No redistribution of Yahoo OHLCV or uncertain-license macro history without explicit rights audit'
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--probe',action='store_true',help='no files written')
    p.add_argument('--no-prices',action='store_true')
    args=p.parse_args()
    out=assemble(prices=not args.no_prices,optional_fred=os.getenv('RESEARCH_FETCH_FRED')=='1')
    if args.probe:
        print('PROBE ONLY', {k:(v.get('start'),v.get('end'),v.get('status')) for k,v in out['macro'].items()})
        return
    if os.getenv('STRUCTURE_PUBLIC_DATA_LICENSES_APPROVED')!='true':
        print('Publication gated: no public JSON file written.')
        return
    TARGET.parent.mkdir(exist_ok=True,parents=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=TARGET.parent,delete=False) as f:
        json.dump(out,f,ensure_ascii=False,separators=(',',':')); temp=f.name
    os.replace(temp,TARGET)
    print('Updated approved public research dataset:',TARGET)

if __name__=='__main__': main()
