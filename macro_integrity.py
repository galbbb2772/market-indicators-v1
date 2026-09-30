"""Source-safe historical macro integrity; never mix differently defined series.

US BLS confirms no CPS unemployment observation exists for 2025-10:
https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm
Only this documented structural absence is exempt from the monthly gap audit.
"""
from __future__ import annotations

SOURCE_BY_KEY={'T10Y3M':'US_TREASURY_DIRECT','UNRATE':'US_BLS_DIRECT',
               'INDPRO':'FED_G17_DIRECT'}
KNOWN_UNAVAILABLE_BY_KEY={'UNRATE':{'2025-10'},'T10Y3M':set(),
                          'INDPRO':set()}
BLS_ABSENCE_URL='https://www.bls.gov/cps/methods/2025-federal-government-shutdown-impact-cps.htm'


def source_compatible(key:str,previous:dict)->bool:
    return bool(isinstance(previous,dict) and previous.get('source')==SOURCE_BY_KEY[key])


def _months_inclusive(start:str,end:str)->list[str]:
    y,m=map(int,start[:7].split('-'));ey,em=map(int,end[:7].split('-'))
    if not (1<=m<=12 and 1<=em<=12):raise ValueError('invalid month')
    out=[]
    while (y,m)<=(ey,em):
        out.append(f'{y:04d}-{m:02d}');m+=1
        if m==13:y+=1;m=1
        if len(out)>2400:raise ValueError('implausibly large monthly series')
    return out


def missing_internal_months(rows:list[list],first_month:str|None=None,
                            exclude_months=None)->list[str]:
    """Report holes through last observed month; exempt only proved source absences."""
    if not rows:return []
    values={str(m)[:7] for m,_ in rows}
    start=first_month or min(values)
    exempt=set(exclude_months or [])
    return [m for m in _months_inclusive(start,max(values)) if m not in values and m not in exempt]


def merge_same_source(key:str,previous:dict,new:dict,expected_first:str|None=None)->dict:
    if new.get('source')!=SOURCE_BY_KEY[key]:raise ValueError('unexpected direct source')
    prev=previous if source_compatible(key,previous) else {}
    combined={str(month)[:7]:float(value) for month,value in prev.get('observations',[])}
    combined.update({str(month)[:7]:float(value) for month,value in new['observations']})
    rows=[[m,round(combined[m],4)] for m in sorted(combined)]
    exempt=KNOWN_UNAVAILABLE_BY_KEY.get(key,set())
    gaps=missing_internal_months(rows,first_month=expected_first,exclude_months=exempt)
    known_absences=sorted(m for m in exempt if rows[0][0]<=m<=rows[-1][0] and m not in combined)
    status='partial' if new.get('failed_years') or gaps else 'refreshed'
    return {**new,'observations':rows,'start':rows[0][0],'end':rows[-1][0],
            'missing_month_count':len(gaps),'first_missing_month':gaps[0] if gaps else None,
            'official_unavailable_months':known_absences,
            'official_unavailable_provenance':BLS_ABSENCE_URL if key=='UNRATE' and known_absences else None,
            'status':status,'cache_reused':bool(prev),
            'source_mismatch_old_cache_discarded':bool(previous and not prev)}


def refetch_anchor(key:str,previous:dict)->str|None:
    if not source_compatible(key,previous):return None
    rows=previous.get('observations') or []
    if not rows:return None
    first_expected={'T10Y3M':'1990-01','UNRATE':'1948-01','INDPRO':'1919-01'}[key]
    gaps=missing_internal_months(rows,first_month=first_expected,
                                exclude_months=KNOWN_UNAVAILABLE_BY_KEY.get(key,set()))
    return gaps[0] if gaps else rows[-1][0]
