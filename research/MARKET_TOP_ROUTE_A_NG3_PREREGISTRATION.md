# Market Top Route_A NG3 — Prospective Phase-Gate Preregistration

Status: **PREREGISTERED / PROSPECTIVE-ONLY / RESEARCH ONLY**

NG1 is closed as a top route.
NG2 is rejected.

NG3 is a new hypothesis generated from already-consumed evidence and therefore **cannot claim a new historical holdout**.

## Why NG3 exists

NG2 showed two things simultaneously:

1. financial-equity lead relative to spread shock contains useful ordering information;
2. multiplying that lead-gap percentile into the route score over-compresses the stress signal.

Known consumed cases:

| Episode | Outcome | NG1 | LeadGapRaw | LeadGapScore | NG2 |
|---|---|---:|---:|---:|---:|
| 1998-11 | clear false | 96.30 | -5.21 | 48.80 | 68.55 |
| 2007-11 | major top | 86.79 | +16.77 | 65.64 | 75.48 |
| 2012-02 | correction | 86.30 | +4.20 | 54.29 | 68.44 |
| 2025-07 | clear false | 85.45 | -6.29 | 43.79 | 61.17 |
| 2025-09 | correction | 85.40 | +8.00 | 58.52 | 70.69 |

Pre-1993 consumed cases also showed an expanding-percentile startup artifact in 1953-11.

Therefore NG3 changes the role of lead-lag from **severity multiplier** to **eligibility / phase gate**.

## Frozen NG1 severity score

NG3 reuses the unchanged NG1 score:

```
SpreadShockScore
  = expanding_pct(
      max(delta3m(BAA-GS10), delta6m(BAA-GS10))
    )

FinanceWeaknessScore
  = expanding_pct(-(Finance6M-Market6M))

SizeWeaknessScore
  = expanding_pct(-CumSMB_6m)

PortfolioExhaustionScore
  = expanding_pct(
      1 - count(FF25_6m > Market6M) / 25
    )

Route_A_NG1
  = fourth_root(
      SpreadShockScore
      * FinanceWeaknessScore
      * SizeWeaknessScore
      * PortfolioExhaustionScore
    )
```

No NG1 component is reweighted.

## New NG3 phase gate

```
FinancialLeadGapRaw
  = FinanceWeaknessScore - SpreadShockScore
```

Eligibility:

```
effective_history_months >= 120

AND

FinancialLeadGapRaw >= 10 percentile points
```

The 10-point gap is intentionally simple: financial-equity weakness must be at least one decile more extreme than broad spread-shock severity.

This threshold is **hypothesis-generated from consumed data**. It is not independently validated and must not be described as such.

The 120-month rule is a ten-year minimum-history guard against unstable early expanding-percentile ranks. It directly addresses the NG2 startup artifact and is frozen before prospective evidence begins.

## NG3 score/state

The lead gap does not create a fifth score.

```
Route_A_NG3_score = Route_A_NG1
```

The candidate is eligible only if the phase gate passes.

ARMED requires all of:

```
Route_A_NG1 >= 85

FinancialLeadGapRaw >= 10

effective_history_months >= 120

price within 5% of trailing 24-calendar-month close high

that high formed within the preceding 3 calendar months
```

No direct trigger is authorized.

## Point-in-time rules

Unchanged from NG1:

- Fama-French monthly inputs: +2 calendar months;
- credit-spread monthly inputs: +1 calendar month;
- percentiles: expanding/current-inclusive;
- no interpolation;
- no event-specific lag;
- price gate uses SPY unadjusted Close.

## Prospective boundary

Preregistration date:

```
2026-10-19
```

No effective month earlier than:

```
2026-12
```

may count as NG3 prospective evidence.

Why December 2026:

```
effective 2026-12
  -> FF source month 2026-10
  -> credit source month 2026-11
```

Both source months occur after this preregistration.

Any 2026-11 or earlier computation is allowed only as:

```
RETROSPECTIVE_TRAINING_DIAGNOSTIC
```

and cannot validate NG3.

## Forward source policy

Fama-French:

1. official Kenneth R. French current ZIPs;
2. verified mirror only as fallback, with source label.

Credit:

1. direct FRED BAA and GS10 monthly series;
2. fallback to a current static snapshot only when:
   - snapshot manifest identifies FRED as source;
   - BAA and GS10 have the same latest month;
   - latest month is no more than two calendar months behind runtime;
   - snapshot generation timestamp is recorded.

Current approved fallback:

```
dlockar1mtg/MacroIntelligencePlatform
data/snapshot/BAA.csv
data/snapshot/GS10.csv
data/snapshot/MANIFEST.json
```

At preregistration the manifest was generated 2026-10-16 and both monthly series extend through 2026-09.

Price:

- Yahoo Finance SPY unadjusted Close, with query1/query2 fallback.

## Prospective outcome protocol

For each future NG3 ARMED episode:

```
anchor = last trading day of first ARMED effective month
horizons = 63 / 126 / 252 sessions
```

Primary 252-session classification remains:

```
MAJOR_TOP
  if worst_return_from_anchor <= -15%

CLEAR_FALSE
  if worst_return_from_anchor > -7.5%
  AND 252-session forward return > 0%

CORRECTION_OR_AMBIGUOUS
  otherwise
```

A later drawdown from a substantially higher price does not rescue an original false top.

## Validation governance

NG3 starts as:

```
PROSPECTIVE_VALIDATION_PENDING
```

No production promotion is authorized.

A formal promotion decision is forbidden until at least:

```
4 complete 252-session prospective episodes
```

exist.

At that point, a separate decision record must be written. No acceptance rule may be retroactively invented before those four episodes are complete; the episode data must remain fully visible.

## No-retune rule

From this preregistration forward, do not change inside NG3:

- Route_A_NG1 component formulas;
- route threshold 85;
- +10 lead-gap gate;
- 120-month warmup;
- PIT lags;
- top-location gate;
- prospective start month;
- outcome definitions.

Any redesign is NG4 or later.
