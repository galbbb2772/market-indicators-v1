from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROV = ROOT / 'docs/data/source_provenance_v1.json'
CANON = ROOT / 'docs/data/fred_canonical_v1.json'
REV = ROOT / 'docs/data/fred_revision_ledger_v1.json'
OUT = ROOT / 'docs/data/fred_official_readiness_v1.json'
SPEC = 'research/fred_official_readiness_v1/STUDY_SPEC.md'


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    p = load(PROV)
    c = load(CANON)
    r = load(REV)
    ids = list(p['fred']['configured_ids'])
    series = c.get('series') or {}
    nonempty = [sid for sid in ids if series.get(sid)]
    empty = [sid for sid in ids if not series.get(sid)]
    transports = p['fred'].get('series_transport') or {}
    missing_transport = [sid for sid in ids if not transports.get(sid)]
    unresolved = sorted(set(p['fred'].get('unresolved_ids') or []))
    api_key = bool(p['fred'].get('api_key_configured'))
    direct_complete = bool(p['fred'].get('direct_complete'))

    if not api_key:
        status = 'blocked_missing_api_key'
    elif not direct_complete or unresolved:
        status = 'blocked_incomplete_official_series'
    elif empty or missing_transport:
        status = 'blocked_canonical_snapshot_incomplete'
    else:
        status = 'ready'

    ready = status == 'ready'
    out = {
        'schema': 'FRED-OFFICIAL-READINESS-V1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'research_only': True,
        'diagnostic_only': True,
        'production_effect': 'none',
        'study_spec': SPEC,
        'status': status,
        'official_factor_map_ready': ready,
        'configured_count': len(ids),
        'canonical_nonempty_count': len(nonempty),
        'api_key_configured': api_key,
        'direct_complete': direct_complete,
        'api_available_count': p['fred'].get('api_available_count'),
        'csv_available_count': p['fred'].get('csv_available_count'),
        'unresolved_ids': unresolved,
        'empty_canonical_ids': empty,
        'missing_transport_ids': missing_transport,
        'revision_ledger_count': len(r.get('revisions') or []),
        'source_provenance_generated_at': p.get('generated_at'),
        'canonical_generated_at': c.get('generated_at'),
        'next_action': 'Configure repository secret FRED_API_KEY and rerun Source Provenance V1.' if not ready else 'Run Canonical FRED Factor Map V1/V2.',
        'guardrails': {
            'may_change_production': False,
            'may_reweight_model': False,
            'may_relabel_fallback_as_official': False,
            'automatic_promotion': False,
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
