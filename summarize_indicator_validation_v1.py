from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'docs/data/indicator_validation_v1.json'
OUT=ROOT/'docs/data/indicator_validation_v1_summary.json'


def get(x,*path):
    cur=x
    for p in path:
        if not isinstance(cur,dict): return None
        cur=cur.get(p)
    return cur


def cluster_from_pairs(pairs,cut=0.85):
    g=defaultdict(set)
    for p in pairs:
        r=p.get('abs_rho')
        if r is None or r<cut: continue
        a,b=p['a'],p['b']; g[a].add(b); g[b].add(a)
    seen=set(); out=[]
    for k in sorted(g):
        if k in seen: continue
        q=deque([k]); comp=[]
        while q:
            x=q.popleft()
            if x in seen: continue
            seen.add(x); comp.append(x); q.extend(g[x]-seen)
        if len(comp)>1: out.append(sorted(comp))
    return sorted(out,key=lambda x:(-len(x),x[0]))


def compact(row):
    h10=get(row,'horizons','10d') or {}
    sic=get(h10,'supportive_ic') or {}
    raw=get(h10,'raw_ic') or {}
    phase=get(h10,'supportive_overlap_phase') or get(h10,'raw_overlap_phase') or {}
    eras=get(h10,'supportive_era_ic') or get(h10,'raw_era_ic') or {}
    regimes=get(h10,'supportive_regime_ic') or get(h10,'raw_regime_ic') or {}
    roll=get(row,'rolling_ic','supportive_10d') or get(row,'rolling_ic','raw_10d') or {}
    return {
      'id':row.get('id'),'name':row.get('name'),'role':row.get('model_v2_role'),'bucket':row.get('model_v2_bucket'),
      'polarity':row.get('impact_polarity'),'n':sic.get('n') or raw.get('n'),'rho10_supportive':sic.get('rho'),'rho10_raw':raw.get('rho'),
      'phase_median_rho10':phase.get('median_rho'),'phase_same_sign_pct10':phase.get('same_sign_as_full_pct'),
      'era_2017_2019_rho10':get(eras,'2017_2019','rho'),'era_2020_2021_rho10':get(eras,'2020_2021','rho'),'era_2022_present_rho10':get(eras,'2022_present','rho'),
      'above200_rho10':get(regimes,'above200','rho'),'below200_rho10':get(regimes,'below200','rho'),'high_vol_rho10':get(regimes,'high_ge20','rho'),'low_vol_rho10':get(regimes,'low_lt20','rho'),
      'rolling_median_rho10':roll.get('median_rho'),'rolling_positive_pct10':roll.get('positive_pct'),
      'max_peer':get(row,'redundancy_5d_change','peer'),'max_peer_abs_rho':get(row,'redundancy_5d_change','abs_rho')
    }


def main():
    d=json.loads(SRC.read_text(encoding='utf-8'))
    rows=d.get('indicators') or d.get('results') or []
    if not rows: raise RuntimeError('indicator rows missing')
    c=[compact(x) for x in rows]
    directional=[x for x in c if x['polarity'] in (-1,1) and x['rho10_supportive'] is not None]
    active=[x for x in directional if x['role']=='active']

    def stable_score(x):
        eras=[x['era_2017_2019_rho10'],x['era_2020_2021_rho10'],x['era_2022_present_rho10']]
        eras=[v for v in eras if v is not None]
        pos=sum(v>0 for v in eras)
        return (pos, x['phase_same_sign_pct10'] or -1, x['rho10_supportive'])

    top_full=sorted(directional,key=lambda x:x['rho10_supportive'],reverse=True)
    top_active=sorted(active,key=lambda x:x['rho10_supportive'],reverse=True)
    stable=sorted(directional,key=stable_score,reverse=True)
    stable_active=sorted(active,key=stable_score,reverse=True)
    oos=sorted([x for x in directional if x['era_2022_present_rho10'] is not None],key=lambda x:x['era_2022_present_rho10'],reverse=True)
    oos_active=sorted([x for x in active if x['era_2022_present_rho10'] is not None],key=lambda x:x['era_2022_present_rho10'],reverse=True)

    pairs=(d.get('redundancy') or {}).get('pairs') or []
    clusters=cluster_from_pairs(pairs,0.85)
    out={
      'schema':'INDICATOR-VALIDATION-V1-COMPACT-SUMMARY','generated_at':datetime.now(timezone.utc).isoformat(),'research_only':True,
      'source_generated_at':d.get('generated_at'),'coverage':d.get('coverage'),'model_version':d.get('model_version'),
      'counts':{'rows':len(c),'directional':len(directional),'active_directional':len(active),'redundancy_pairs_ge085':len(pairs),'redundancy_clusters_ge085':len(clusters)},
      'top_full_supportive_ic10':top_full[:20],'top_active_supportive_ic10':top_active[:20],
      'top_2022_present_supportive_ic10':oos[:20],'top_active_2022_present_supportive_ic10':oos_active[:20],
      'most_stable_cross_era':stable[:20],'most_stable_active_cross_era':stable_active[:20],
      'active_all':sorted(active,key=lambda x:x['id']),
      'largest_redundancy_clusters':clusters[:15],
      'guardrails':{'production_effect':'none','may_reweight':False,'may_remove':False,'descriptive_only':True},
      'warnings':['Reconstructed history is not fully point-in-time.','Current-history macro series may contain revisions.','Rankings are descriptive discovery evidence, not promotion tests.']
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'counts':out['counts'],'top_active10':[(x['id'],x['rho10_supportive'],x['era_2022_present_rho10']) for x in top_active[:10]],'stable_active':[(x['id'],x['rho10_supportive'],x['phase_same_sign_pct10'],x['era_2022_present_rho10']) for x in stable_active[:10]]},ensure_ascii=False))

if __name__=='__main__': main()
