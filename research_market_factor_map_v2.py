from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'docs/data'
OUT = DATA / 'market_factor_map_v2.json'
SUMMARY = DATA / 'market_factor_map_v2_summary.json'
SPEC = 'research/market_factor_map_v2/STUDY_SPEC.md'
FROZEN = '2026-10-02'


def load(name: str, required: bool = True):
    p = DATA / name
    if not p.exists():
        if required:
            raise FileNotFoundError(p)
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def family_status(row: dict) -> str:
    if row.get('loyo_univariate_improvement_pct', 0) > 0 and row.get('phase_same_sign_pct10', 0) >= 80:
        return 'historical_factor'
    return 'regime_or_descriptive'


def component_row(r: dict) -> dict:
    return {
        'id': r['key'],
        'family': r['family'],
        'members': r['members'],
        'kind': 'source_invariant_component',
        'status': r.get('screening_label', 'regime_or_descriptive'),
        'historical_ic10': r.get('ic10'),
        'historical_ic10_2022_present': r.get('ic10_2022_present'),
        'historical_partial_ic10': r.get('partial_ic10'),
        'historical_partial_ic10_2022_present': r.get('partial_ic10_2022_present'),
        'bh_fdr_q': r.get('bh_fdr_q'),
        'phase_same_sign_pct10': r.get('phase_same_sign_pct10'),
        'univariate_loyo_improvement_pct': r.get('univariate_loyo_improvement_pct'),
        'q5_minus_q1_10d_pp': r.get('q5_minus_q1_10d_pp'),
        'screening_gate_pass_count': r.get('screening_gate_pass_count'),
        'source_stability': 'source_invariant',
    }


def main():
    fmap = load('factor_map_source_invariant_v1_summary.json')
    sig = load('source_invariant_component_significance_v1_summary.json')
    oos = load('source_invariant_representatives_oos_v1.json')
    sector = load('sector_rotation_state_v1_summary.json')
    prov = load('source_provenance_v1.json')
    ready = load('fred_official_readiness_v1.json', required=False)
    canonical = load('factor_map_canonical_fred_v1_summary.json', required=False)

    if ready is None:
        api_key = bool(prov['fred'].get('api_key_configured'))
        direct = bool(prov['fred'].get('direct_complete'))
        readiness_status = 'ready' if api_key and direct else ('blocked_missing_api_key' if not api_key else 'blocked_incomplete_official_series')
        readiness = {'status': readiness_status, 'official_factor_map_ready': readiness_status == 'ready'}
    else:
        readiness = ready

    families = []
    for r in fmap['families']:
        families.append({
            'id': r['family'], 'kind': 'source_invariant_family', 'status': family_status(r),
            'style': r.get('style'), 'ic10': r.get('ic10'), 'ic10_2022_present': r.get('ic10_2022_present'),
            'partial_ic10': r.get('partial_ic10'), 'partial_ic10_2022_present': r.get('partial_ic10_2022_present'),
            'phase_same_sign_pct10': r.get('phase_same_sign_pct10'),
            'loyo_univariate_improvement_pct': r.get('loyo_univariate_improvement_pct'),
            'loyo_ablation_delta_pct': r.get('loyo_ablation_delta_pct'),
            'role': 'return_state_or_regime', 'source_stability': 'source_invariant',
        })

    oos_counts = (oos.get('status') or {}).get('counts') or {}
    representatives = []
    for r in sig.get('forward_oos_priority') or []:
        x = component_row(r)
        c = oos_counts.get(r['key']) or {}
        x.update({
            'status': 'forward_oos_priority',
            'forward_observation_count': c.get('forward_observation_count', 0),
            'matured_10d_count': c.get('matured_10d_count', 0),
            'discrepancy_count': c.get('discrepancy_count', 0),
            'role': 'prospective_return_factor_candidate',
        })
        representatives.append(x)

    component_watchlist = []
    for r in sig.get('regime_or_descriptive') or []:
        x = component_row(r)
        x['status'] = 'regime_or_descriptive'
        x['role'] = 'component_level_watchlist_not_promoted'
        component_watchlist.append(x)
    component_watchlist.sort(key=lambda x: (-int(x.get('screening_gate_pass_count') or 0), -abs(float(x.get('historical_ic10') or 0))))

    plain = sector['activity_interaction']['plain_contrarian_ic10']
    weighted = sector['activity_interaction']['activity_weighted_contrarian_ic10']
    states = sector['state_results']
    sector_context = {
        'id': 'sector_rotation_dispersion', 'kind': 'market_state_context', 'status': 'state_context',
        'role': 'cross_sectional_rotation_context',
        'plain_contrarian_ic10': plain.get('mean'),
        'activity_weighted_contrarian_ic10': weighted.get('mean'),
        'activity_weight_delta_ic10': sector['activity_interaction'].get('delta_mean_ic'),
        'high_dispersion_bottom2_minus_top2_10d_pp': states['high_dispersion']['contrarian_bottom2_minus_top2_10d']['mean'],
        'low_dispersion_bottom2_minus_top2_10d_pp': states['low_dispersion']['contrarian_bottom2_minus_top2_10d']['mean'],
        'high_persistence_bottom2_minus_top2_10d_pp': states['high_persistence']['contrarian_bottom2_minus_top2_10d']['mean'],
        'low_persistence_bottom2_minus_top2_10d_pp': states['low_persistence']['contrarian_bottom2_minus_top2_10d']['mean'],
        'interpretation': 'Weak sector mean reversion is stronger in high cross-sectional dispersion; activity weighting does not improve the base contrarian IC.',
    }

    canonical_by_family = {r['family']: r for r in (canonical or {}).get('families', [])}
    canonical_snapshot = (canonical or {}).get('canonical_fred_snapshot') or {}

    def official_family_row(identifier: str, canonical_family: str, role: str) -> dict:
        evidence = canonical_by_family.get(canonical_family)
        source_ready = bool(readiness.get('official_factor_map_ready'))
        evidence_ready = source_ready and evidence is not None
        status = family_status(evidence) if evidence_ready else 'provisional_source_dependent'
        return {
            'id': identifier,
            'kind': 'official_macro_family',
            'canonical_family': canonical_family,
            'status': status,
            'role': role,
            'official_source_ready': source_ready,
            'canonical_evidence_available': evidence is not None,
            'readiness_status': readiness.get('status'),
            'canonical_ic10': None if evidence is None else evidence.get('ic10'),
            'canonical_ic10_2022_present': None if evidence is None else evidence.get('ic10_2022_present'),
            'canonical_partial_ic10': None if evidence is None else evidence.get('partial_ic10'),
            'canonical_partial_ic10_2022_present': None if evidence is None else evidence.get('partial_ic10_2022_present'),
            'canonical_phase_same_sign_pct10': None if evidence is None else evidence.get('phase_same_sign_pct10'),
            'canonical_loyo_univariate_improvement_pct': None if evidence is None else evidence.get('loyo_univariate_improvement_pct'),
            'canonical_loyo_ablation_delta_pct': None if evidence is None else evidence.get('loyo_ablation_delta_pct'),
            'canonical_snapshot_generated_at': canonical_snapshot.get('canonical_generated_at'),
            'source_stability': 'official_canonical_snapshot' if evidence_ready else 'official_source_pending',
            'interpretation': 'Official-source readiness removes source uncertainty, but evidence status is still determined by robustness/LOYO rather than by source availability alone.',
        }

    source_dependent = [
        official_family_row('liquidity_credit_official', 'liquidity_credit', 'liquidity_and_credit_state'),
        official_family_row('official_macro_rates', 'rates_policy', 'rates_and_curve_state'),
    ]

    external_context = [{
        'id':'task14_cross_market_confirmation','kind':'external_stage2_context','status':'external_stage2_context',
        'role':'Task1/4 context only; not a production gate','source_repo':'galbbb2772/market-structure-lab',
        'source_path':'docs/data/task14_crossmarket_confirmation_v1.json',
        'note':'Cross-market confirmation is maintained in Market Structure Lab and is intentionally not imported into this repo calculation.'
    }]

    status_counts = {}
    registry = families + representatives + component_watchlist + [sector_context] + source_dependent + external_context
    for x in registry:
        status_counts[x['status']] = status_counts.get(x['status'], 0) + 1

    out = {
        'schema':'MARKET-FACTOR-MAP-V2','generated_at':datetime.now(timezone.utc).isoformat(),
        'research_only':True,'diagnostic_only':True,'production_effect':'none','frozen_through_market_date':FROZEN,
        'study_spec':SPEC,'design':'evidence_registry_not_weighted_score',
        'source_invariant_families':families,'forward_oos_representatives':representatives,
        'component_watchlist':component_watchlist,'sector_rotation_context':sector_context,
        'source_dependent_official_families':source_dependent,'external_stage2_context':external_context,
        'fred_readiness':{
            'status':readiness.get('status'),
            'official_factor_map_ready':bool(readiness.get('official_factor_map_ready')),
            'canonical_factor_map_available': canonical is not None,
            'configured_count':readiness.get('configured_count',prov['fred'].get('configured_count')),
            'canonical_nonempty_count':readiness.get('canonical_nonempty_count'),
            'canonical_snapshot_generated_at': canonical_snapshot.get('canonical_generated_at'),
        },
        'status_counts':status_counts,'prospective_gate':oos.get('confirmatory_protocol'),
        'guardrails':{'may_change_production':False,'may_reweight_model':False,'may_remove_indicator':False,'automatic_promotion':False,'historical_results_count_as_forward_oos':False},
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    compact={
        'schema':'MARKET-FACTOR-MAP-V2-SUMMARY','generated_at':out['generated_at'],'research_only':True,'frozen_through_market_date':FROZEN,
        'design':out['design'],'status_counts':status_counts,'fred_readiness':out['fred_readiness'],
        'forward_oos_representatives':representatives,'component_watchlist':component_watchlist,
        'sector_rotation_context':sector_context,'source_invariant_families':families,
        'source_dependent_official_families':source_dependent,'external_stage2_context':external_context,'guardrails':out['guardrails'],
    }
    SUMMARY.write_text(json.dumps(compact,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status_counts':status_counts,'fred':out['fred_readiness'],'official_families':source_dependent,'oos_representatives':[x['id'] for x in representatives],'component_watchlist_count':len(component_watchlist),'sector':sector_context},ensure_ascii=False))


if __name__=='__main__':
    main()
