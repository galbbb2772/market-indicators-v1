# Frozen identity and data-quality boundaries

## Version identity constraints
- `MT-01` V2.1.8 **equals the implementation reused by** `MT-03` PB in V3 Stage-0; registry rows represent identities, **not two independent evidences**.
- `MT-02` V2.4R Route_B has distinct PolicyShock and FF SMB input; it must not be equated with PB/MT-01 simply because both mention rates.
- `MT-04` V3 CB uses SLOOS, business loan delinquencies and Baa spread; cannot backfill missing original legacy Route_A/MT-08.
- `MT-05` BE V0 and `MT-06` BE v25 are separate studied score families. Similar current extreme values do not prove identical inputs or event states.
- `MT-06` FINRA margin debt ≠ `MT-16` BEA corporate profit margin; different economic quantity, publication regime and denominator.
- `MT-11`/ `MT-13` next-generation Route_A/C NG3 do not restore `MT-08`/ `MT-09` original legacy Route_A/C. Unrecovered authentic child formulas remain marked missing.
- `MT-14` rejected NG3 CostPressure V1 is not a forward-approved negative control that may be fixed by opportunistically shortening its source release lag.
- A/C NG3 start prospective clock 2026-12; PB prefreeze 2026-09 signal remains a seed, not a pristine postfreeze origin.

## Status separation (mandatory)
`FROZEN_FORMULA` != `HISTORICAL_BACKTEST_DONE` != `PROSPECTIVE_OUTCOME_MATURED` != `PRODUCTION_AUTHORIZED`.

`SNAPSHOT_ASOF`, `REFERENCE_MONTH`, `SOURCE_PUBLISHED_AT`, `SOURCE_CAPTURED_AT`, `SCORE_COMPUTED_AT` and `EXECUTABLE_ACTION_TIME` are distinct fields. Unavailable is not zero. A re-computed latest-vintage historical score is not a true publication-vintage PIT forecast.

## Dashboard output schema (proposal; not yet deployed)
Required columns: `route_id`, `version`, `score`, `threshold`, `state`, `signal_asof`, `source_months`, `source_pub_evidence`, `captured_at`, `code_hash`, `data_hashes`, `freshness`, `research_status`, `production_authorization`, `coverage`, `censoring`, `next_release_needed`.

Show timestamp-aligned comparisons only. When any source is stale show `STALE`; when route unpublished show `RESEARCH_ONLY`; when no comparable source exists show `MISSING` instead of 0. Do not label PB/BE/CB/RouteB divergence as proof of a trading recommendation.

## Multi-route aggregation permission
No joint score or alarm severity scheme may be introduced until:
1. independent route sample histories have common as-of cutoffs and full source vintage evidence;
2. event grouping + prospective maturities fixed in a preregistered protocol;
3. negative controls included and historical false positives/misses reported;
4. combination rule locked before evaluating an untouched future period;
5. deployment approval is separately recorded.

## Version governance
This ledger snapshot is an audit artifact as of 2026-10-19. Any later research conclusion must point to a dated new file/version, not silently rewrite historical source provenance. Main branch remains untouched.
