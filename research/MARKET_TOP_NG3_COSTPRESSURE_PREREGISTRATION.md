# Market Top NG3-CostPressure — Numerical Preregistration

Status: PREREGISTERED / NOT VALIDATED / RESEARCH ONLY.

This record was committed before the first NG3-CostPressure historical outcome screen. It does not recover legacy Route_A or Route_C, does not modify Route_B, and does not authorize production use.

## Frozen hypothesis and sources

The candidate asks whether synchronized inflation and producer-cost pressure can identify major equity-top risk more specifically than simple inflation-only or producer-gap baselines.

Source series are BLS monthly not-seasonally-adjusted indexes:

- CPI-U all items: CUUR0000SA0
- PPI finished goods: WPUFD49207
- PPI processed goods for intermediate demand: WPUID61

No BEA margin value enters the score. MarginConfirm remains separate; missing or non-comparable margin means MARGIN_NOT_COMPARABLE, not zero and not pass.

## Frozen transforms

For source month m:

CPIYoY = 100 * (CPI(m) / CPI(m-12) - 1)

FinishedPPIYoY = 100 * (FinishedPPI(m) / FinishedPPI(m-12) - 1)

IntermediatePPIYoY = 100 * (IntermediatePPI(m) / IntermediatePPI(m-12) - 1)

FinishedGapRaw = FinishedPPIYoY - CPIYoY

IntermediateGapRaw = IntermediatePPIYoY - CPIYoY

The three expanding current-inclusive percentile scores are InflationLevelScore, FinishedGapScore and IntermediateGapScore.

Frozen candidate:

CostPressure_NG3 = cube root of (InflationLevelScore * FinishedGapScore * IntermediateGapScore).

No weights are fitted.

## Frozen PIT convention

All three components use the same source month.

effective_month = source_month + 6 calendar months.

The +6-month delay is deliberately conservative. It allows the PPI revision window to close and keeps CPI synchronized to the slower PPI block. Lead time is intentionally sacrificed for a cleaner non-lookahead test.

No event-specific lag is allowed. No missing month is interpolated.

A minimum of 120 valid transformed source months is required before any ARMED state can occur.

## Frozen market-location gate

Price source is the S&P 500 price index (^GSPC), daily unadjusted close.

At the last trading-day close of the effective month:

- close must be within 5% of the trailing 24-calendar-month highest close;
- that high must have formed within the preceding 3 calendar months.

Both conditions are required.

## Frozen candidate state

Threshold = 85.

NG3_COST_ARMED is true only when CostPressure_NG3 >= 85 and the TopLocationGate is true.

This first screen has no direct trigger, no price-breakdown confirmation and no MarginConfirm requirement.

## Frozen baselines

Inflation-only baseline:
InflationOnlyScore = InflationLevelScore, threshold 85, same +6-month lag and same TopLocationGate.

Producer-gap baseline:
ProducerGapScore = sqrt(FinishedGapScore * IntermediateGapScore), threshold 85, same +6-month lag and same TopLocationGate.

Top-location-only baseline:
TopLocationGate alone. This baseline is descriptive and is not part of the incremental-value promotion gate.

## Frozen first-screen windows

Decision windows:

- 1957-01 through 1967-12
- 1975-01 through 1986-12
- 1988-01 through 2006-12

Known hypothesis-generation windows are excluded from the first-screen decision:

- 1968-01 through 1974-12
- 1987-01 through 1987-12

Those episodes may not later be counted as validation wins or losses.

This is preregistered historical validation relative to the formula commit; it is not claimed to be epistemically untouched financial history.

## Frozen episode and outcome rules

Consecutive ARMED months form one episode. The anchor is the last trading-day close of the first ARMED month.

Each complete episode is followed for 252 trading sessions.

WorstVsSignal = minimum future close / signal close - 1.

Classification:

- MAJOR_TOP_HIT if WorstVsSignal <= -20%
- CORRECTION_RISK_NOT_MAJOR_TOP if -20% < WorstVsSignal <= -10%
- CLEAR_TOP_FALSE_POSITIVE if WorstVsSignal > -10%

Also report 63-, 126- and 252-session forward returns, worst return from the anchor, maximum peak-to-trough drawdown and endpoint date.

Only complete 252-session episodes count in the decision.

## Frozen structural acceptance gate

STRUCTURAL_PASS requires all of:

1. at least 3 complete candidate episodes;
2. at least 2 MAJOR_TOP_HIT episodes;
3. at most 1 CLEAR_TOP_FALSE_POSITIVE;
4. major-top-hit fraction >= 0.50.

Fewer than 3 complete episodes gives INSUFFICIENT_SCREEN_EVENTS, not pass.

Otherwise a failed rule gives STRUCTURAL_FAIL.

## Frozen incremental-value gate

For candidate, InflationOnly and ProducerGap:

MajorFraction = major hits / complete episodes.

FalseFraction = clear false positives / complete episodes.

Against both score-based baselines, NG3 must have:

- MajorFraction greater than or equal to the baseline;
- FalseFraction less than or equal to the baseline;
- at least one of those two comparisons strictly better for each baseline.

A baseline with zero complete episodes yields BASELINE_INSUFFICIENT and prevents full promotion.

Final first-screen decision is ACCEPT_SCREENING_CANDIDATE only when both STRUCTURAL_PASS and INCREMENTAL_VALUE_PASS are true.

Otherwise the result is REJECT or INSUFFICIENT_SCREEN_EVENTS as applicable.

## Governance

After outcomes are generated, do not lower 85, shorten +6 months, remove the TopLocationGate, change the 12-month YoY window, change geometric aggregation, add MarginConfirm to rescue misses, or alter the screening windows.

Any structural change requires a new named NG version and a new preregistration before testing.

Production inclusion remains unauthorized. Legacy Route_A and Route_C remain unresolved. Route_B remains unchanged.
