# Source Provenance & FRED Revision Archive V1

Status: **research/data-engineering only**. This layer does not change any production score, indicator formula, model weight, threshold, membership, traffic-light rule, or execution rule.

## Problem

Several indicators can change historical formula when FRED/official sources are unavailable and market-price fallbacks are used. Historical research must therefore distinguish:

1. the economic indicator definition;
2. the actual source/formula mode used by a run;
3. revisions to official time series.

## V1 scope

V1 archives the FRED series listed in `update_data.FRED_IDS` and records source/formula provenance for official-source-dependent indicators. BLS/Treasury fallback endpoints are recorded as possible modes but their full raw revision archives are outside V1.

## Outputs

- `docs/data/source_provenance_v1.json`: latest source status, hashes and inferred formula modes;
- `docs/data/source_provenance_history_v1.json`: append-only run-level provenance ledger from the date this archive starts;
- `docs/data/fred_canonical_v1.json`: latest full normalized FRED series snapshot;
- `docs/data/fred_revision_ledger_v1.json`: append-only revisions detected by comparing the new FRED snapshot with the previously archived canonical values.

## FRED normalization

For every available series:

- normalize observation date to `YYYY-MM-DD`;
- store numeric value only;
- sort ascending by observation date;
- SHA256 the canonical `date=value` sequence;
- retain start/end date, count and latest value.

## Revision rule

When a date exists in both old and new canonical snapshots and its numeric value changes beyond 1e-12, append a revision record:

- source id;
- observation date;
- old value;
- new value;
- detection timestamp.

New observations are not classified as revisions.

The revision ledger makes point-in-time reconstruction possible only from the moment this archive begins; it cannot recover revisions that happened before V1 was created.

## Formula-mode provenance

For each official-source-dependent indicator, record the deterministic source mode implied by which FRED ids are available in that run, e.g. `fred_direct`, `fred_plus_market`, `market_fallback`, `official_fallback`, or `downstream_mixed`.

This is descriptive provenance. It does not modify the formulas themselves.

## Guardrails

- A failed FRED fetch must be archived as a failed/partial source run, not silently treated as equivalent to direct-source validation.
- No fallback result can be relabelled as official-source evidence.
- No historical Alpha claim may merge direct-source and fallback-formula observations without an explicit source-mode robustness test.
- V1 does not block production automatically.
