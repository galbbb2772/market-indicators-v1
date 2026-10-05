# Source-Invariant Component Significance Audit V1

Status: **research-only / diagnostic-only / post-discovery screening**.

This study does not change production weights, thresholds, indicator formulas, or Market Model V2.

## Universe

Use the exact source-invariant component construction from `research_factor_components_source_invariant_v1.py`:

- official/FRED-dependent indicators are excluded;
- within-family redundancy uses the already frozen `|rho| >= 0.85` rule on 5D score changes;
- component scores are equal-weight means of the surviving supportive-direction indicator scores;
- target is SPY forward 10-trading-day close-to-close return.

## Dependence-aware inference

Daily 10D forward returns overlap. Therefore ordinary IID p-values are not used.

Frozen inference settings:

- random seed: `20261005`;
- moving-block bootstrap block length: `20` trading days;
- bootstrap replications: `1000`;
- null test: circular shift of the target rank series while preserving each series' serial structure;
- circular-shift replications: `1000`;
- shifts shorter than `20` sessions (or within 20 sessions of a full wrap) are excluded;
- empirical p-values are two-sided;
- multiple-testing correction: Benjamini-Hochberg FDR across all eligible components, applied to the 10D circular-shift p-values.

The block-bootstrap statistic is the Spearman correlation, implemented as Pearson correlation of the full-sample rank transforms within each resampled block path.

## Screening labels

These labels are for future OOS prioritization only and are not evidence of production readiness.

A component is `forward_oos_priority` only when all of the following are true:

1. `abs(IC10) >= 0.05`;
2. full-history IC10 and 2022+ IC10 have the same non-zero sign;
3. 20-session block-bootstrap 95% CI excludes zero;
4. BH-FDR q-value <= 0.10;
5. overlap-phase same-sign rate >= 80%;
6. partial IC10 is non-zero and has the same sign as the raw IC10;
7. univariate LOYO MSE improvement is positive.

A component that fails one or more gates may still be labelled `regime_or_descriptive` or `weak_or_unstable` for research interpretation.

## Guardrails

- No threshold search.
- No weight optimization.
- No changing family assignments after seeing the results.
- No deleting indicators from production based on this audit.
- No historical result from this audit counts as Forward-OOS evidence.
