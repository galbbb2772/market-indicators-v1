# Canonical FRED Factor Map V1

Status: **research-only / diagnostic-only**.

Purpose: reconstruct the existing Factor Map using a repository-archived, complete official FRED snapshot rather than live network retrieval or market-price fallbacks.

## Eligibility gate

This study is allowed to run only when `docs/data/source_provenance_v1.json` reports:

- all configured FRED series available;
- `fred.direct_complete == true`;
- every configured FRED ID has a non-empty series in `docs/data/fred_canonical_v1.json`.

If the gate is not satisfied, the study must stop and must not create or refresh a canonical Factor Map result.

## Data rule

- FRED observations come only from `docs/data/fred_canonical_v1.json`.
- The archived transport may be the official keyed FRED API or official FRED CSV, but no market-price proxy may substitute for a missing FRED series.
- BLS/Treasury fallbacks remain governed by the existing production formula and are not silently relabelled as FRED evidence.
- The canonical snapshot hashes and transport metadata are written into the result for reproducibility.

## Model rule

Reuse `research_factor_map_v1.py` unchanged except for the source capture. Family assignments, redundancy threshold, equal-component family aggregation, IC definitions, partial correlations, LOYO, and ablation are all inherited unchanged.

## Guardrails

- No production changes.
- No family reassignment.
- No threshold or weight optimization.
- No historical canonical result may be counted as Forward-OOS evidence.
- Compare canonical results with the Source-Invariant Factor Map; do not merge the two evidence strata.
