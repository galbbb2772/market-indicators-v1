# FRED Official Readiness V1

## Purpose

Expose one deterministic readiness gate for official-source macro research. This study does not fetch new data and does not change any production formula, model weight, or signal. It only summarizes the already archived Source Provenance V1 and canonical FRED snapshot.

## Inputs

- `docs/data/source_provenance_v1.json`
- `docs/data/fred_canonical_v1.json`
- `docs/data/fred_revision_ledger_v1.json`

## Frozen readiness requirements

`official_factor_map_ready = true` only when all of the following are true:

1. `FRED_API_KEY` was configured on the provenance run (`api_key_configured=true`).
2. Every configured FRED series is available (`direct_complete=true`).
3. Every configured series has a non-empty canonical history.
4. Every configured series has a recorded transport.
5. No configured series is listed as unresolved.

The API-key requirement is intentionally stricter than merely obtaining CSV data: V1 defines the official canonical research lane as the keyed official FRED API lane. CSV/fallback observations remain useful provenance but are not allowed to unlock the official Factor Map V1/V2 evidence lane.

## Status labels

- `ready`
- `blocked_missing_api_key`
- `blocked_incomplete_official_series`
- `blocked_canonical_snapshot_incomplete`

## Guardrails

- research/diagnostic only
- no production effect
- no automatic promotion
- no relabelling fallback formulas as official-source evidence
- no backfilling point-in-time revisions before the first archived canonical snapshot
