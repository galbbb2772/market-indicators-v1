# Market Factor Map V2 — Integration Spec

Version: V2.0 / frozen through 2026-10-02.

## Purpose

Create a single evidence map from the completed Stage-2 research without creating a new optimized score. V2 is an evidence registry, not a production model.

## Local inputs

- `docs/data/factor_map_source_invariant_v1_summary.json`
- `docs/data/source_invariant_component_significance_v1_summary.json`
- `docs/data/source_invariant_representatives_oos_v1.json`
- `docs/data/sector_rotation_state_v1_summary.json`
- `docs/data/source_provenance_v1.json`
- `docs/data/fred_official_readiness_v1.json` when available

## Evidence statuses

- `forward_oos_priority`: preregistered source-invariant representative with an append-only future ledger.
- `historical_factor`: family-level historical evidence with at least one positive generalization diagnostic; not prospective evidence.
- `state_context`: useful for describing market state/risk but not supported as a standalone trading alpha.
- `regime_or_descriptive`: historical relationship with material instability, redundancy, or weak generalization.
- `provisional_source_dependent`: interpretation depends on official macro data that has not passed canonical readiness.
- `external_stage2_context`: evidence maintained in another frozen research repo; descriptive here only.

## V2 design rules

1. Do not average all families into a new Market Score.
2. Do not optimize family weights.
3. Keep representative component evidence separate from family averages when cancellation is known.
4. Sector Rotation enters as context: high cross-sectional dispersion can amplify weak sector mean reversion, but V1/V2 do not define a standalone production trade.
5. Official liquidity/credit and official macro-rate families remain provisional until the FRED readiness gate is `ready`.
6. Historical evidence through 2026-10-02 does not count as future OOS.
7. Cross-market Task1/4 confirmation is referenced as external Stage-2 context and may not modify Task1/4 production/OOS definitions.

## Guardrails

- research only
- no production effect
- no automatic promotion
- no weight changes
- no indicator deletion
- no hidden substitution of fallback macro formulas for official-source evidence
