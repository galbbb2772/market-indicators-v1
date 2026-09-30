"""Research bootstrap: vetted direct official providers, source-safe caching.
No raw public output before both vendor-rights and deployment-authority reviews.
"""
from __future__ import annotations
import argparse,csv,io,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
import requests
import build_structure_lab as lab
from macro_sources import treasury_spread,bls_unrate
from macro_integrity import merge_same_source,refetch_anchor,SOURCE_BY_KEY
from cycle_research import cycle_report

ROOT=Path(__file__).resolve().parent
TARGET=ROOT/'docs/data/structure_lab.json'
FULL_MACRO=lab.MACRO.copy()
DIRECT={'T10Y3M':treasury_spread,'UNRATE':bls_unrate}
EXPECTED_START={'T10Y3M':'1990-01','UNRATE':'1948-01'}


def _previous():
    try:return json.loads(TARGET.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}


def assemble(prices=True,existing=None,optional_fred=False):
    prior=existing if existing is not None else _previous()
    # The old FRED endpoint is NEVER mandatory or allowed to block direct sources.
    lab.MACRO={}
    if prices:
        out=lab.build(prior)
    else:
        out={'schema':'STRUCTURE-LAB-V1','generated_at':datetime.now(timezone.utc).isoformat(),
             'instruments':prior.get('instruments',{}),'news_tension':prior.get('news_tension',[]),
             'news_status':prior.get('news_status','no_news'),'errors':dict(prior.get('errors',{})),
             'policy':dict(prior.get('policy',{}))}
    out['macro']=dict(prior.get('macro') or {})
    session=requests.Session()
    session.headers.update({'User-Agent':'MarketStructureLab/1.0 (research)'})
    for key,download in DIRECT.items():
        previous=out['macro'].get(key,{})
        last_month=refetch_anchor(key,previous)
        try:
            source=download(session,last_month=last_month)
            # Never combine a legacy FRED T10Y3M with Treasury par yield proxy;
            # similarly do not silently combine unknown-cache UNRATE with BLS.
            merged=merge_same_source(key,previous,source,EXPECTED_START[key])
            label='（US Treasury par-yield PROXY, not FRED T10Y3M）' if key=='T10Y3M' else '（US BLS direct）'
            out['macro'][key]={'name':FULL_MACRO[key]+label,**merged}
            out['errors'].pop(key,None)
            print('DIRECT',key,source['source'],len(merged['observations']),
                  merged['status'],'missing_months',merged['missing_month_count'],
                  'discarded_incompatible_old_cache',merged['source_mismatch_old_cache_discarded'],flush=True)
        except Exception as exc:
            out['errors'][key]=type(exc).__name__+': '+str(exc)[:140]
            if previous.get('source')==SOURCE_BY_KEY[key] and previous.get('observations'):
                out['macro'][key]['status']='stale_cached'
            else:
                # The old series of the same ID from a different vendor is NOT
                # a valid fallback for the differently defined direct source.
                out['macro'].pop(key,None)
            print('DIRECT UNAVAILABLE',key,out['errors'][key],flush=True)
    for key in FULL_MACRO:
        if key in DIRECT:continue
        if not optional_fred:
            if key not in out['macro']:
                out['errors'][key]='Direct official provider unverified; no synthetic series'
            continue
        try:
            # PRIVATE research only: vendor rights, exact definitions and
            # vintage dates MUST be reviewed before publication or forecast use.
            r=session.get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={key}',timeout=7)
            r.raise_for_status();monthly={}
            for row in csv.DictReader(io.StringIO(r.text)):
                try:monthly[row['DATE'][:7]]=float(row[key])
                except (ValueError,KeyError,TypeError):pass
            if not monthly:raise ValueError('No valid FRED observations')
            hist=[[m,round(v,4)] for m,v in sorted(monthly.items())]
            out['macro'][key]={'name':FULL_MACRO[key],'observations':hist,
                'start':hist[0][0],'end':hist[-1][0],'source':'FRED_OPTIONAL_RESEARCH',
                'point_in_time':False,'frequency':'last_observation_each_month','status':'refreshed'}
        except Exception as exc:
            out['errors'][key]=type(exc).__name__+': '+str(exc)[:140]
            if key in out['macro']:out['macro'][key]['status']='stale_cached'
    out['policy']['macro']='Treasury par-yield spread PROXY and BLS direct unemployment; revised, not publication-time data; source-safe cache and missing-month audit'
    out['policy']['publication_gate']='No raw/vendor-history redistribution or new-site deployment without vendor-rights audit and explicit owner authorization'
    try:
        out['cycle_research']=cycle_report(out['instruments'],out.get('news_tension') or [])
    except Exception as exc:
        out['errors']['cycle_research']=type(exc).__name__+': '+str(exc)[:140]
        prior_cycle=prior.get('cycle_research')
        out['cycle_research']={**prior_cycle,'status':'stale_cached'} if isinstance(prior_cycle,dict) else {'status':'unavailable'}
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true',help='no files written')
    p.add_argument('--no-prices',action='store_true');args=p.parse_args()
    out=assemble(prices=not args.no_prices,optional_fred=os.getenv('RESEARCH_FETCH_FRED')=='1')
    if args.probe:
        print('PROBE ONLY', {k:(v.get('start'),v.get('end'),v.get('status')) for k,v in out['macro'].items()})
        print('CYCLE STATUS',out['cycle_research'].get('status'))
        return
    if (os.getenv('STRUCTURE_PUBLIC_DATA_LICENSES_APPROVED')!='true' or
        os.getenv('STRUCTURE_DEPLOY_AUTHORIZED')!='true'):
        print('Publication gated: explicit data-rights AND owner website authorization required. No public JSON written.')
        return
    TARGET.parent.mkdir(exist_ok=True,parents=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=TARGET.parent,delete=False) as f:
        json.dump(out,f,ensure_ascii=False,separators=(',',':'));temp=f.name
    os.replace(temp,TARGET)
    print('Updated approved public research dataset:',TARGET)

if __name__=='__main__':main()
