"""Official primary-source macro readers. These are revised/current observations,
not publication-time/ALFRED vintages. Treasury spread is a proxy, not FRED T10Y3M.
"""
from __future__ import annotations
import csv
import io
import re
from datetime import datetime, timezone
import requests

TREASURY_URL = ('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/'
 'daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&'
 'field_tdr_date_value={year}&page&_format=csv')
BLS_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000'


def _month_rows(data: list[tuple[str,float]]) -> list[list]:
    """Use last actual trading observation per month; never forward-fill."""
    bymonth = {}
    for day, val in sorted(data):
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):
            bymonth[day[:7]] = round(float(val),4)
    return [[k,bymonth[k]] for k in sorted(bymonth)]


def treasury_spread(session:requests.Session,last_month:str|None=None,
                    initial_year:int=1990,current_year:int|None=None)->dict:
    """10-year minus 3-month US Treasury *par yield* spread. Last daily observation each month."""
    year=current_year or datetime.now(timezone.utc).year
    first=max(initial_year,int(last_month[:4])-1) if last_month else initial_year
    data=[]; failures=[]
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
                except (KeyError,TypeError,ValueError):
                    continue
            if not parsed:raise ValueError('No valid 10Y & 3M pairs')
        except (requests.RequestException,ValueError) as exc:
            failures.append(f'{y}: {type(exc).__name__}')
    rows=_month_rows(data)
    if not rows:raise RuntimeError('US Treasury returned no valid spread observations: '+', '.join(failures[:4]))
    return {'observations':rows,'source':'US_TREASURY_DIRECT',
      'source_url':'https://home.treasury.gov/resource-center/data-chart-center/interest-rates',
      'definition':'US Treasury daily par yield (10 Yr minus 3 Mo), last valid day per month; proxy NOT identical to FRED T10Y3M',
      'completeness':'partial_year_fetch' if failures else 'full_requested_range',
      'failed_years':failures,'frequency':'monthly_last_daily','point_in_time':False}


def bls_unrate(session:requests.Session,last_month:str|None=None,
               first_year:int=1948,current_year:int|None=None)->dict:
    """Monthly BLS civilian unemployment rate LNS14000000, no API key required."""
    year=current_year or datetime.now(timezone.utc).year
    first=max(first_year,int(last_month[:4])-1) if last_month else first_year
    rows={};failures=[]
    for y in range(first,year+1,10):
        end=min(y+9,year)
        try:
            r=session.get(BLS_URL,params={'startyear':y,'endyear':end},timeout=8)
            r.raise_for_status(); obj=r.json()
            if obj.get('status')!='REQUEST_SUCCEEDED':
                raise RuntimeError(f"BLS status {obj.get('status')}")
            for item in obj.get('Results',{}).get('series',[{}])[0].get('data',[]):
                month=item.get('period','')
                if re.fullmatch('M(0[1-9]|1[0-2])',month):
                    val=float(item['value'])
                    if 0<=val<100:rows[f"{item['year']}-{month[1:]}"]=round(val,4)
        except (requests.RequestException,KeyError,IndexError,ValueError,RuntimeError) as exc:
            failures.append(f'{y}-{end}: {type(exc).__name__}')
    out=[[month,rows[month]] for month in sorted(rows)]
    if not out:raise RuntimeError('US BLS returned no unemployment observations: '+', '.join(failures[:4]))
    return {'observations':out,'source':'US_BLS_DIRECT','source_url':'https://www.bls.gov/cps/',
       'definition':'BLS LNS14000000 civilian unemployment rate, seasonally adjusted, monthly',
       'completeness':'partial_decade_fetch' if failures else 'full_requested_range',
       'failed_years':failures,'frequency':'monthly','point_in_time':False}
