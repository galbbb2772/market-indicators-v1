# Source-Invariant Factor Component Audit V1

Status: **research-only / diagnostic-only**. This study cannot change production weights, thresholds, model membership, traffic-light logic, or execution rules.

## Goal

Explain why some family composites are weak even when individual indicators inside them appear informative. Decompose the already-frozen Source-Invariant Factor Map V1 into its redundancy components and test each component separately.

## Data/source rule

- Reuse `research_factor_map_source_invariant_v1.source_invariant_capture()`.
- Official macro/FRED/BLS/Treasury retrieval is forced off.
- Every id in `research_indicator_validation_v1_sourceaware.FRED_DEPENDENT` is excluded before analysis.
- No new proxy is invented to replace an excluded source-dependent indicator.

## Orientation and family definition

Exactly inherit `research/factor_map_v1/STUDY_SPEC.md`:

- polarity +1 -> supportive score = score;
- polarity -1 -> supportive score = 100-score;
- same frozen family taxonomy;
- within-family redundancy graph uses Spearman of 5-trading-day score changes, |rho| >=0.85, pair n>=120;
- each connected component is a redundancy component;
- component score = equal-weight mean of member supportive scores.

No component sign is flipped after seeing results.

## Component tests

For every redundancy component with enough history:

- 5D / 10D / 20D Spearman IC;
- 10D IC for 2017-2019, 2020-2021, 2022-present;
- 10D IC above/below MA200 and RV20 >=20 / <20;
- 252-session rolling 10D IC and overlap-phase sign stability;
- 10D quintile Q5-Q1 spread;
- univariate Leave-One-Year-Out linear prediction vs train-mean baseline;
- partial Spearman after controlling for (a) other components in the same family and (b) all other family aggregates;
- fixed ridge(alpha=10) Leave-One-Year-Out ablation from the full component feature set.

## Family cancellation audit

For every family compare:

- family 10D IC from Source-Invariant Factor Map V1;
- strongest absolute component 10D IC (descriptive only);
- strongest absolute component partial 10D IC;
- number of positive vs negative component ICs;
- component sign agreement;
- whether the equal-weight family composite is materially weaker than a constituent component.

A `cancellation_flag` is descriptive only and is true when:

`max_component_abs_ic10 - abs(family_ic10) >= 0.05`

This threshold is fixed before reading results and MUST NOT trigger automatic reweighting.

## Guardrails

- No winner becomes a new production factor from this study.
- No family weights or component weights are optimized.
- No indicator is removed because of one historical component result.
- Any future representative-factor or weighting change requires a separate preregistered OOS challenger.
