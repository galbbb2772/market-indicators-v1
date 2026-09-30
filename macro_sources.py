"""Official primary-source macro readers: revised observations, NOT historical vintages.
Treasury 10Y minus 3M daily *par-yield* proxy is NOT identical to FRED T10Y3M.
"""
from __future__ import annotations
import csv,io,re
from datetime import datetime,timezone
import requests

TREASURY_URL=('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/'
 'daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&'
 'field_tdr_date_value={year}&page&_format=csv')
BLS_URL='https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000'


def _month_rows(data:list[tuple[str,float]])->list[list]:
    """Last observed actual day of each month; no interpolated months."""
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
                raise ValueError('Treasury response was not a rates CSV')
            parsed=0
            for row in csv.DictReader(io.StringIO(r.text.lstrip('\ufeff'))):
                try:
                    d=datetime.strptime(row['Date'].strip(),'%m/%d/%Y').date().isoformat()
                    three=float(row['3 Mo']);ten=float(row['10 Yr'])
                    if 0<three<30 and 0<ten<30:
                        data.append((d,ten-three));parsed+=1
                except (KeyError,TypeError,ValueError):continue
            if not parsed:raise ValueError('No valid 10Y & 3M pairs')
        except (requests.RequestException,ValueError) as exc:
            failures.append(f'{y}: {type(exc).__name__}')
    rows=_month_rows(data)
    if not rows:raise RuntimeError('US Treasury returned no valid spread observations: '+', '.join(failures[:4]))
    return {'observations':rows,'source':'US_TREASURY_DIRECT',
      'source_url':'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
      'definition':'US Treasury daily par yield (10 Yr minus 3 Mo), last daily observation per month; proxy NOT FRED T10Y3M',
      'completeness':'partial_year_fetch' if failures else 'full_requested_range',
      'failed_years':failures,'frequency':'monthly_last_daily','point_in_time':False}


def _bls_chunk(session:requests.Session,start:int,end:int)->dict[str,float]:
    r=session.get(BLS_URL,params={'startyear':start,'endyear':end},timeout=8)
    r.raise_for_status();obj=r.json()
    if obj.get('status')!='REQUEST_SUCCEEDED':
        raise RuntimeError(f"BLS status {obj.get('status')}")
    series=obj.get('Results',{}).get('series',[])
    if not series:raise ValueError('No BLS series in response')
    out={}
    for item in series[0].get('data',[]):
        month=item.get('period','')
        if re.fullmatch(r'M(0[1-9]|1[0-2])',month):
            val=float(item['value'])
            if 0<=val<100:out[f"{item['year']}-{month[1:]}"]=round(val,4)
    if not out:raise ValueError('BLS returned no monthly rows')
    return out


def bls_unrate(session:requests.Session,last_month:str|None=None,
               first_year:int=1948,current_year:int|None=None)->dict:
    """No-key BLS series LNS14000000; retry failed 10y block as two 5y blocks."""
    year=current_year or datetime.now(timezone.utc).year
    first=max(first_year,int(last_month[:4])-1) if last_month else first_year
    rows={};failures=[]
    for y in range(first,year+1,10):
        end=min(y+9,year)
        try:
            rows.update(_bls_chunk(session,y,end));continue
        except (requests.RequestException,KeyError,IndexError,ValueError,RuntimeError):
            # A vendor timeout or per-request response failure must not silently
            # turn an entire historical decade into a claimed complete series.
            for low in range(y,end+1,5):
                high=min(low+4,end)
                try:rows.update(_bls_chunk(session,low,high))
                except (requests.RequestException,KeyError,IndexError,ValueError,RuntimeError) as exc:
                    failures.append(f'{low}-{high}: {type(exc).__name__}')
    out=[[month,rows[month]] for month in sorted(rows)]
    if not out:raise RuntimeError('US BLS returned no unemployment observations: '+', '.join(failures[:4]))
    return {'observations':out,'source':'US_BLS_DIRECT','source_url':'https://www.bls.gov/cps/',
       'definition':'BLS LNS14000000 civilian unemployment rate, seasonally adjusted, monthly',
       'completeness':'partial_chunk_fetch' if failures else 'full_requested_range',
       'failed_years':failures,'frequency':'monthly','point_in_time':False}
