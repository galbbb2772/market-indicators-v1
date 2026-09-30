"""Official US macro readers. Revised observations only, NOT point-in-time vintages.
Treasury 10Y minus 3M par-yield proxy is not identical to FRED T10Y3M.
BLS no-key retrieval prioritizes new data and audits historical completeness.
"""
from __future__ import annotations
import csv,io,re
from datetime import datetime,timezone
import requests

TREASURY_URL=('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/'
 'daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&'
 'field_tdr_date_value={year}&page&_format=csv')
BLS_URL='https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000'
# OFFICIAL BLS CPS structural absence. No household survey was collected
# in 2025-10 due to the US government shutdown; it will never be backfilled.
# https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm
BLS_KNOWN_UNAVAILABLE={'2025-10'}


def _month_rows(data:list[tuple[str,float]])->list[list]:
    bymonth={}
    for day,val in sorted(data):
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):bymonth[day[:7]]=round(float(val),4)
    return [[k,bymonth[k]] for k in sorted(bymonth)]


def treasury_spread(session:requests.Session,last_month:str|None=None,
                    initial_year:int=1990,current_year:int|None=None)->dict:
    year=current_year or datetime.now(timezone.utc).year
    first=max(initial_year,int(last_month[:4])-1) if last_month else initial_year
    data=[];failures=[]
    for y in range(first,year+1):
        try:
            r=session.get(TREASURY_URL.format(year=y),timeout=8)
            r.raise_for_status()
            if 'csv' not in r.headers.get('Content-Type','').lower() and 'Date' not in r.text[:100]:
                raise ValueError('Treasury response not a rates CSV')
            parsed=0
            for row in csv.DictReader(io.StringIO(r.text.lstrip('\ufeff'))):
                try:
                    d=datetime.strptime(row['Date'].strip(),'%m/%d/%Y').date().isoformat()
                    three,ten=float(row['3 Mo']),float(row['10 Yr'])
                    if 0<three<30 and 0<ten<30:
                        data.append((d,ten-three));parsed+=1
                except (KeyError,TypeError,ValueError):continue
            if not parsed:raise ValueError('No valid 10Y/3M pairs')
        except (requests.RequestException,ValueError) as exc:
            failures.append(f'{y}: {type(exc).__name__}')
    rows=_month_rows(data)
    if not rows:raise RuntimeError('Treasury returned no observations: '+', '.join(failures[:4]))
    return {'observations':rows,'source':'US_TREASURY_DIRECT',
      'source_url':'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
      'definition':'US Treasury 10 Yr minus 3 Mo daily par yield, last actual observation/month; proxy NOT FRED T10Y3M',
      'completeness':'partial_year_fetch' if failures else 'full_requested_range',
      'failed_years':failures,'frequency':'monthly_last_daily','point_in_time':False}


def _bls_chunk(session:requests.Session,start:int,end:int)->dict[str,float]:
    r=session.get(BLS_URL,params={'startyear':start,'endyear':end},timeout=8)
    r.raise_for_status();obj=r.json()
    if obj.get('status')!='REQUEST_SUCCEEDED':
        raise RuntimeError('BLS status '+str(obj.get('status')))
    series=obj.get('Results',{}).get('series',[])
    if not series:raise ValueError('No BLS series')
    out={}
    for item in series[0].get('data',[]):
        mo=item.get('period','')
        if not re.fullmatch(r'M(0[1-9]|1[0-2])',mo):continue
        try:yy=int(item['year']);value=float(item['value'])
        except (ValueError,TypeError,KeyError):continue
        if start<=yy<=end and 0<=value<100:
            out[f'{yy}-{mo[1:]}']=round(value,4)
    if not out:raise ValueError('No valid monthly BLS observations')
    return out


def _months(start:str,end:str)->list[str]:
    sy,sm=map(int,start.split('-'));ey,em=map(int,end.split('-'))
    out=[]
    while (sy,sm)<=(ey,em):
        out.append(f'{sy:04d}-{sm:02d}');sm+=1
        if sm>12:sy+=1;sm=1
        if len(out)>1800:raise ValueError('Invalid BLS monthly range')
    return out


def bls_unrate(session:requests.Session,last_month:str|None=None,
               first_year:int=1948,current_year:int|None=None)->dict:
    """No-key BLS: latest 4yr first, then older 10yr blocks, repair real gaps.
    Never interpolate BLS's uncollected 2025-10 unemployment observation.
    """
    now=datetime.now(timezone.utc)
    year=current_year or now.year
    first=max(first_year,int(last_month[:4])-1) if last_month else first_year
    if first>year:raise ValueError('BLS first_year later than current_year')
    failures=[];rows={};attempts=0;MAX_REQUESTS=23  # BLS no-key quota: 25/day

    def fetch(start:int,end:int)->bool:
        nonlocal attempts
        if attempts>=MAX_REQUESTS:
            failures.append(f'{start}-{end}: request_budget_exhausted');return False
        attempts+=1
        try:
            rows.update(_bls_chunk(session,start,end));return True
        except (requests.RequestException,KeyError,IndexError,ValueError,RuntimeError) as exc:
            failures.append(f'{start}-{end}: {type(exc).__name__}');return False

    if year>=2020:
        recent=max(first,year-3)
        if not fetch(recent,year):
            middle=(recent+year)//2
            fetch(recent,middle)
            if middle+1<=year:fetch(middle+1,year)
        historical_end=recent-1
    else:
        historical_end=year
    for y in range(first,historical_end+1,10):
        end=min(y+9,historical_end)
        if fetch(y,end):continue
        for lo in range(y,end+1,5):fetch(lo,min(lo+4,end))

    # Repair real missing observations only. The known 2025-10 absence is
    # a missing source observation, NOT a network or retrieval failure.
    if rows and year==now.year:
        latest_expected=(f'{now.year:04d}-{now.month-1:02d}' if now.month>1
                         else f'{now.year-1:04d}-12')
        audit_end=min(latest_expected,f'{year:04d}-12')
        observed=set(rows)
        missing=[mo for mo in _months(f'{first:04d}-01',audit_end)
                 if mo not in observed and mo not in BLS_KNOWN_UNAVAILABLE]
        for y in sorted({int(mo[:4]) for mo in missing},reverse=True):
            if attempts>=MAX_REQUESTS:break
            fetch(y,y)

    if not rows:
        raise RuntimeError('US BLS returned no unemployment values: '+', '.join(failures[:4]))
    out=[[mo,rows[mo]] for mo in sorted(rows)]
    if year==now.year:
        expected=(f'{now.year:04d}-{now.month-2:02d}' if now.month>=3
                  else (f'{now.year-1}-11' if now.month==1 else f'{now.year-1}-12'))
        expected=min(expected,f'{year:04d}-12')
    else:
        expected=out[-1][0]
    missing=[m for m in _months(f'{first:04d}-01',expected)
             if m not in rows and m not in BLS_KNOWN_UNAVAILABLE]
    officially_unavailable=sorted(m for m in BLS_KNOWN_UNAVAILABLE
                                  if out[0][0]<=m<=out[-1][0] and m not in rows)
    return {'observations':out,'source':'US_BLS_DIRECT','source_url':'https://www.bls.gov/cps/',
       'definition':'BLS LNS14000000 civilian unemployment rate, seasonally adjusted; revised not vintage data',
       'completeness':'partial_month_coverage' if missing else 'full_expected_month_coverage',
       'failed_years':[f'Unrecovered monthly gap: {m}' for m in missing[:24]],
       'official_unavailable_months':officially_unavailable,
       'official_unavailable_provenance':'https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm',
       'request_errors':failures,'missing_requested_month_count':len(missing),
       'expected_through':expected,'request_count':attempts,
       'frequency':'monthly','point_in_time':False}
