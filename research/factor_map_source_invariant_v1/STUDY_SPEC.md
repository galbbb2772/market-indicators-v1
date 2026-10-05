# Source-Invariant Factor Map V1 — Study Specification

Status: **research-only / diagnostic-only**. No production weights, thresholds, model membership, traffic-light logic, or execution rules may change from this study.

## Purpose

Audit whether the Factor Map V1 conclusions survive when official macro/FRED/BLS/Treasury availability cannot change an indicator formula.

## Frozen source rule

- Force official macro retrieval off exactly as in `research_indicator_validation_marketprice_v1.py`.
- Before factor construction, remove every id in `research_indicator_validation_v1_sourceaware.FRED_DEPENDENT`.
- This leaves only the formula-invariant market-price/derived stratum.
- Do not replace excluded indicators with newly invented proxies.

## Factor-map rule

All remaining definitions are inherited unchanged from `research/factor_map_v1/STUDY_SPEC.md`:

- supportive orientation from configured polarity;
- same frozen semantic family taxonomy;
- within-family redundancy components from |Spearman 5D score-change| >=0.85, pair n>=120;
- equal weight inside redundancy component, equal weight across components;
- 5/10/20D IC, eras, MA200/volatility regimes, rolling IC, overlap phases;
- univariate LOYO;
- partial Spearman controlling other remaining families;
- multivariate ridge(alpha=10) LOYO family ablation.

## Comparison

Report side-by-side against the already-frozen `docs/data/factor_map_v1_summary.json`:

- family existence / disappearance;
- member and redundancy-component counts;
- 10D IC and 2022+ IC;
- full and 2022+ partial IC;
- LOYO ablation delta;
- sign agreement.

A family absent after source-dependent removal is marked `not_source_invariant_evaluable`; absence is not a negative result.

## Interpretation

- The source-invariant map is the primary robustness view when official-source retrieval was unavailable in the original Factor Map run.
- The original Factor Map remains a valid reconstruction of the formulas actually produced under that run, but source-dependent family rankings remain provisional.
- This study cannot promote, reweight, delete, or substitute any production factor.
