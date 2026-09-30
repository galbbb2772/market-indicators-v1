"""Source-safe historical macro caching. Never mix a FRED key with a new proxy.
Metadata is descriptive; all historical observations are revised, not as-published.
"""
from __future__ import annotations
from datetime import date

SOURCE_BY_KEY={'T10Y3M':'US_TREASURY_DIRECT','UNRATE':'US_BLS_DIRECT'}


def source_compatible(key:str,previous:dict)->bool:
    """A same-named FRED or unknown-source series MUST NOT be reused."""
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


def missing_internal_months(rows:list[list],first_month:str|None=None)->list[str]:
    """Missing only from earliest expected historical month through last observed.
    Missing months after the last observation might be legitimate publication lag.
    """
    if not rows:return []
    values={str(m)[:7] for m,_ in rows}
    start=first_month or min(values)
    return [m for m in _months_inclusive(start,max(values)) if m not in values]


def merge_same_source(key:str,previous:dict,new:dict,expected_first:str|None=None)->dict:
    """Use only compatible old source; report actual missing months after merge."""
    if new.get('source')!=SOURCE_BY_KEY[key]:raise ValueError('unexpected direct source')
    prev=previous if source_compatible(key,previous) else {}
    combined={str(month)[:7]:float(value) for month,value in prev.get('observations',[])}
    combined.update({str(month)[:7]:float(value) for month,value in new['observations']})
    rows=[[m,round(combined[m],4)] for m in sorted(combined)]
    gaps=missing_internal_months(rows,first_month=expected_first)
    status='partial' if new.get('failed_years') or gaps else 'refreshed'
    return {**new,'observations':rows,'start':rows[0][0],'end':rows[-1][0],
            'missing_month_count':len(gaps),'first_missing_month':gaps[0] if gaps else None,
            'status':status,
            'cache_reused':bool(prev),'source_mismatch_old_cache_discarded':bool(previous and not prev)}


def refetch_anchor(key:str,previous:dict)->str|None:
    """Resume normally but return to the earliest internal gap for backfill."""
    if not source_compatible(key,previous):return None
    rows=previous.get('observations') or []
    if not rows:return None
    first_expected={'T10Y3M':'1990-01','UNRATE':'1948-01'}[key]
    gaps=missing_internal_months(rows,first_month=first_expected)
    return gaps[0] if gaps else rows[-1][0]
