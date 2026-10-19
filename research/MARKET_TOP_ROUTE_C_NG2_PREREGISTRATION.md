# Market Top Route_C NG2 — Bubble Phase-Gate Preregistration

Status:

```
PREREGISTERED / NOT VALIDATED / RESEARCH ONLY
```

This is a newly named next-generation Route_C hypothesis.

It does **not** recover the missing legacy V2.4 Route_C, and it does not retune the rejected Route_C_NG1 formula.

## Consumed training evidence

The complete 1993–2022 NG1-C episode set has already been inspected during the NG1 failure diagnostic.

Therefore none of those post-1993 cases may validate NG2.

The diagnostic showed that intended 2000 and 2021 states differ from many NG1 false/additional states along four structural dimensions:

1. valuation is extremely high;
2. concentration breadth itself is extremely high, rather than merely compensated by valuation;
3. broad credit-spread shock is not already the dominant extreme;
4. the Big Growth relative gap is still increasing over the prior three months.

These observations generate NG2. They do not validate it.

## Frozen base score

NG2 retains the NG1 concentration construction unchanged.

For the Fama-French 25 Size x Book-to-Market value-weighted portfolios:

```
PortfolioExhaustionRaw
  = 1 - count(R6_j > Market6) / 25

PortfolioExhaustionScore
  = expanding_percentile(PortfolioExhaustionRaw)

LeaderGapRaw
  = max(R6_j) - median(R6_j)

LeaderGapScore
  = expanding_percentile(LeaderGapRaw)

BigGrowthGapRaw
  = R6_BIG_LoBM - median(R6_j)

BigGrowthGapScore
  = expanding_percentile(BigGrowthGapRaw)

ConcentrationBreadth
  = cbrt(
      PortfolioExhaustionScore
      * LeaderGapScore
      * BigGrowthGapScore
    )

Route_C_NG1
  = sqrt(
      Valuation
      * ConcentrationBreadth
    )
```

where:

```
Valuation = expanding_percentile(Shiller CAPE)
```

No NG1 weight or score formula is changed.

## New NG2 phase gates

A month is an NG2 pressure-pass only when **all** of the following are true:

```
Route_C_NG1 >= 85
Valuation >= 98
ConcentrationBreadth >= 85
SpreadShockScore <= 50
BigGrowthGapChange3M > 0
```

where:

```
SpreadShockRaw
  = max(
      BAA10Y(t) - BAA10Y(t-3m),
      BAA10Y(t) - BAA10Y(t-6m)
    )

SpreadShockScore
  = expanding_percentile(SpreadShockRaw)

BigGrowthGapChange3M
  = BigGrowthGapRaw(t) - BigGrowthGapRaw(t-3m)
```

The gates are conjunctive. They are not averaged into a new score.

## Price-location gate

An NG2 research ARMED month additionally requires the frozen top-location rule:

```
index close within 5% of trailing 24-calendar-month close high
AND
that high formed within the preceding 3 calendar months
```

No direct trigger is authorized.

## Point-in-time convention

Frozen lags:

- Fama-French monthly inputs: +2 calendar months;
- Shiller CAPE: +1 calendar month;
- monthly BAA / GS10 spread input: +1 calendar month;
- percentiles: expanding, current-inclusive;
- no interpolation;
- no event-specific lag changes.

Warm-up:

```
at least 120 common effective months
```

must exist before a holdout month can count.

## Untouched validation set

Because post-1993 cases were consumed to design the phase gates, the first NG2 validation is the pre-1993 holdout:

```
1963-01 through 1992-12
```

or the first later month satisfying the frozen 120-month common-history requirement.

Pre-SPY price proxy:

```
S&P 500 index (^GSPC), unadjusted close
```

Before interpreting the holdout, the implementation must compare the same top-location rule on ^GSPC and SPY during an overlap window and require:

```
gate agreement >= 95%
```

No threshold or price-gate parameter may be changed after seeing that overlap.

## Positive mechanism windows

NG2 is specifically a valuation/concentration bubble-exhaustion route.

It must produce at least one ARMED month in each of:

```
1968-09 through 1969-01
1972-11 through 1973-02
```

These windows are frozen before pre-1993 Route_C_NG2 output is inspected.

## Full-holdout episode protocol

Every pre-1993 ARMED month is retained.

Consecutive ARMED months form one episode.

Episode anchor:

```
last trading-day close of the first ARMED month
```

Outcome horizon:

```
252 trading sessions
```

Classification:

```
MAJOR_TOP
  if worst return from anchor <= -15%

CLEAR_FALSE
  if worst return from anchor > -7.5%
  AND 252-session forward return > 0%

CORRECTION_OR_AMBIGUOUS
  otherwise
```

## Frozen decision rule

NG2 receives:

```
ACCEPT_HOLDOUT_CANDIDATE
```

only if all conditions hold:

1. ^GSPC/SPY overlap gate agreement is at least 95%;
2. both positive mechanism windows contain an ARMED month;
3. at least 2 complete holdout episodes exist;
4. at least 50% of complete episodes are MAJOR_TOP;
5. no more than 25% of complete episodes are CLEAR_FALSE.

Otherwise:

```
REJECT
```

If fewer than 2 complete episodes exist:

```
INSUFFICIENT_HOLDOUT_EVENTS
```

takes precedence over acceptance.

## Governance

After this preregistration:

- do not change 85;
- do not change 98;
- do not change 85 ConcentrationBreadth;
- do not change SpreadShock <= 50;
- do not change the sign of BigGrowthGapChange3M;
- do not change PIT lags;
- do not remove the top-location gate;
- do not delete failed episodes.

If NG2 fails, any structural change must be Route_C NG3 or later and preregistered before another validation set is inspected.

Production effect:

```
NONE
```
