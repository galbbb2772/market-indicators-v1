# Market Top NG3 — PPI Revision-Semantics Decision

Status:

```
SOURCE_SEMANTICS_FROZEN
SA_MOM = SOURCE_ENGINEERING_DIAGNOSTIC_ONLY
NSA_LEVELS = REQUIRED_FOR_V1_ALIGNED_FIRST_RELEASE_RESEARCH
MODEL_OUTCOME_TEST = NOT AUTHORIZED
```

Research only. No production effect.

## Why this decision is required

The 1986–1988 pilot recovered historical **seasonally adjusted month-over-month** Finished Goods and Intermediate Goods changes. That proved that contemporaneous PPI vintages can be reconstructed.

It does **not** provide a permanently finalized comparison series after four months.

BLS distinguishes two revision mechanisms:

1. ordinary PPI respondent/late-report revision; and
2. annual seasonal-factor revision.

BLS states that not-seasonally-adjusted PPI indexes are routinely revised through the four-month revision cycle and are then final apart from corrections/rebasing. BLS also states that previously published seasonally adjusted indexes are recalculated annually and can be revised for the most recent five years.

Primary references:

- https://www.bls.gov/ppi/faqs/questions-and-answers.htm
- https://www.bls.gov/ppi/seasonal-adjustment/
- https://www.bls.gov/opub/hom/ppi/presentation.htm
- https://www.bls.gov/ppi/publications/price-adjustment-guide-for-contracting-parties.htm

## Consequence for the 1987 pilot

The previously recovered May 1987 first publication:

```
Finished Goods SA MoM = +0.3%
Intermediate Goods SA MoM = +0.5%
```

and a much later March 1988 historical table:

```
Finished Goods SA MoM = -0.1%
Intermediate Goods SA MoM = +0.5%
```

must not be interpreted as a pure four-month respondent-revision delta. A later annual seasonal-factor recalculation can also change historical SA values.

Likewise, repeated +4/+5/+6/+7 report snapshots are useful diagnostics, but they can straddle an annual seasonal-factor revision for observations near year-end.

Therefore the SA panel remains valuable for proving vintage availability and parser behavior, but it is not the clean source for an NG3 formula designed to preserve the V1 economic transform.

## Frozen source hierarchy for the next branch

NG3-CostPressure V1 used monthly **not-seasonally-adjusted** price indexes and 12-month changes.

A faster, V1-aligned first-release branch must therefore reconstruct:

```
first-published NSA index levels
four-month-final NSA index levels
documented publication dates
historical source labels / reference base
```

and compute YoY changes from levels that existed in the same historical information set.

Do not derive a V1-aligned faster model from SA MoM headlines merely because those headlines are easier to parse.

## Historical Table 2 path

Contemporaneous PPI Detailed Reports contain:

```
Table 2. Producer price indexes and percent changes
for selected commodity groupings by stage of processing
```

with unadjusted index columns for the report's current month and nearby comparison months.

The May 1987 report explicitly labels those columns as **Unadjusted index** and separately labels the SA percentage-change columns.

This table is therefore the preferred next extraction source for:

- Finished goods NSA level;
- Intermediate materials, supplies and components NSA level;
- same-vintage YoY reconstruction where the necessary prior-year level is available.

## Research boundary

The SA revision-consensus workflow is retained as a diagnostic and parser stress test.

It must not be promoted to a model input.

The next valid implementation gate is:

```
Table 2 NSA pilot
-> validate current-month level extraction
-> validate four-month-final NSA extraction
-> construct same-vintage YoY
-> freeze release-time semantics
-> preregister a new faster NG3 candidate
-> only then inspect market outcomes
```

Until then:

```
FASTER_NG3_FORMULA = NOT PREREGISTERED
HISTORICAL_OUTCOME_TEST = NO
PRODUCTION_EFFECT = NONE
```
