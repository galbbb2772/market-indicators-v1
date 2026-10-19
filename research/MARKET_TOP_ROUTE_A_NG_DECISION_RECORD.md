# Market Top Route_A — Next-Generation Decision Record

Status: **RESEARCH LINEAGE FROZEN THROUGH NG3 PREREGISTRATION**

This file is the canonical summary of the Route_A research line. It prevents rejected or diagnostic versions from being mistaken for the missing legacy Route_A.

## Legacy Route_A

```
status = UNRESOLVED
```

The original final Credit/Breadth child formulas were never recovered.

Rejected reconstruction attempts:

- A1 level-credit;
- A2 spread-shock.

Neither is legacy Route_A.

## NG1

NG1 was a new, explicitly versioned stress model:

```
Route_A_NG1 =
fourth_root(
  SpreadShockScore
  * FinanceWeaknessScore
  * SizeWeaknessScore
  * PortfolioExhaustionScore
)
```

It successfully reproduced a 2007 stress/top configuration, including independent-source replay.

But it also produced:

- 1998 clear false top;
- 2012 correction, not major top;
- 2025-07 clear false top;
- 2025-09 correction, not major top;
- 1955-11 correction/ambiguous;
- 1991-02 clear false.

Decision:

```
NG1_CLOSED_NO_TOP_ROUTE_PROMOTION
```

NG1 may remain a credit/breadth stress diagnostic. It is not a production top route.

## NG2

NG2 preregistered the hypothesis that financial-equity weakness leading spread stress could improve top specificity:

```
FinancialLeadGapRaw =
  FinanceWeaknessScore - SpreadShockScore

FinancialLeadGapScore =
  expanding_pct(FinancialLeadGapRaw)

Route_A_NG2 =
  sqrt(Route_A_NG1 * FinancialLeadGapScore)
```

The first untouched validation was the 1953-1992 temporal holdout.

Result:

```
monthly states = 470

Route_A_NG2 >= 85 ignoring price gate = 1 month
top-location gate pass = 191 months
NG2 ARMED episodes = 0

preregistered minimum evaluable episodes = 2
```

Decision:

```
REJECT_NG2_TOP_ROUTE
```

The rejection is frozen. No threshold or formula retuning is allowed inside NG2.

### NG2 failure mechanism

Lead-gap does contain ordering information in consumed cases:

- 1998: 48.80
- 2007: 65.64
- 2012: 54.29
- 2025-07: 43.79
- 2025-09: 58.52

But multiplying the lead-gap percentile into route severity over-compresses the desired signal:

```
2007 NG1 = 86.79
2007 NG2 = 75.48
```

So the useful interpretation is **phase information**, not another severity factor.

## NG3

NG3 is preregistered **prospective-only**.

It does not claim any untouched historical validation because the 1953-2026 U.S. history has already been consumed by earlier screening, holdout, or hypothesis generation.

NG3 preserves NG1 severity:

```
Route_A_NG3_score = Route_A_NG1
```

and changes lead-lag into an eligibility gate:

```
FinancialLeadGapRaw >= 10 percentile points

effective_history_months >= 120
```

ARMED additionally requires:

```
Route_A_NG1 >= 85
AND unchanged 24M top-location gate
```

### Prospective boundary

Preregistered:

```
2026-10-19
```

First countable effective month:

```
2026-12
```

with source months:

```
Fama-French = 2026-10
Credit       = 2026-11
```

Evidence-quality clarification:

- the October 2026 Fama-French month was not complete or published when NG3 was preregistered on 2026-10-19, so the December signal itself was still unknown;
- however, October 2026 **straddles** the preregistration date and is not a source month wholly after preregistration;
- therefore effective 2026-12 remains countable under the original frozen preregistration, but must be tagged `SOURCE_MONTH_STRADDLES_PREREGISTRATION`;
- effective 2027-01, using Fama-French 2026-11 and credit 2026-12, is the first month whose required monthly source periods are wholly post-preregistration.

This is a disclosure/evidence-quality clarification only. The NG3 formula, gates, first countable month, and promotion-review rule are unchanged.

Any earlier NG3 output is:

```
RETROSPECTIVE_TRAINING_DIAGNOSTIC
```

and cannot validate the model.

### Current seeded monitor

Latest completed diagnostic effective month:

```
2026-09
```

Values:

```
NG3 score = 39.4242
FinancialLeadGapRaw = -7.4313

Route >= 85       = FALSE
Lead gap >= 10    = FALSE
120M warmup       = TRUE
Top-location gate = TRUE

state = IDLE
```

This does **not** count toward prospective evidence.

## Promotion governance

NG3 starts at:

```
PROSPECTIVE_VALIDATION_PENDING
```

No production promotion review is allowed until at least:

```
4 complete prospective episodes
with full 252-session outcomes
```

exist.

No retrospective success rate may be invented for NG3.

Any post-preregistration change to:

- score formula;
- +10 phase gate;
- 120-month warmup;
- threshold 85;
- PIT lags;
- top-location gate;
- outcome protocol;

requires:

```
NG4 or later
```

## Current canonical Route_A research state

```
legacy Route_A = UNRESOLVED

NG1 = CLOSED / diagnostic only
NG2 = REJECTED
NG3 = PROSPECTIVE VALIDATION PENDING
```

No version currently qualifies as a recovered or production Route_A.


### Prospective evidence-gap accounting

The NG3 monitor must preserve missing prospective months explicitly.

If all eligible runs fail for an entire countable effective month, a later revised data vintage must not silently recreate that month as though it were the first successful post-close snapshot.

The monthly evidence book therefore records:

```
missing_effective_months
evidence_gaps_present
```

and each opened episode records the source-temporality tier that generated it.
