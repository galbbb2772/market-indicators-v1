# Market Top Trigger Task 2 — Decision Record

Status: **CORE TASK PASS WITH LEGACY PROVENANCE GAPS**

## Original task

Repair the 2022 miss by extending the PolicyShock route with:

- 2Y Treasury policy repricing;
- Fed balance-sheet QE/taper dynamics;

while keeping the rest of the V2.4 state machine frozen.

## Core result

The task succeeds.

Conservative publication-lag 2022 replay:

```
Valuation = 98.580721
PolicyShock = 74.388619
SizeWeakness = 84.736842

Route_B = 85.334292
```

Therefore:

```
2022-01-03
Route_B > 85
+ top-location gate
=> ARMED
```

The independently versioned price-confirmation candidate then gives:

```
2022-01-20
DD12 >= 4.5%
T_v2.4R >= 70
=> PRICE_BREAKDOWN_v2.4R
```

So the new research path is:

```
2022-01-03 ARMED
    -> 17 calendar days
2022-01-20 PRICE_BREAKDOWN_v2.4R
```

No PolicyShock threshold or weight was retuned after this result.

## What remains historically accepted

The prior V2.4 result:

```
2021-10 EARLY_BREADTH
```

remains the accepted historical label for the 2022 event.

The new policy path is additive redundancy. It does not rewrite that old label.

## What was genuinely restored

### Route_B

```
Route_B =
cbrt(
  Valuation
  * PolicyShock
  * SizeWeakness
)
```

Canonical inputs:

```
Valuation = expanding percentile of Shiller CAPE

SizeWeakness =
  expanding percentile(
    - compounded Fama-French SMB over six months
  )
```

### PolicyShock V2.1.1

```
PolicyShock =
  0.60 * RateShock
+ 0.40 * TaperShock
```

with the frozen invariant that a pure rate shock cannot arm Route_B by itself.

### T_v2.4R

A new transparent price confirmation was preregistered and validated separately. It is not presented as the missing original T.

## What was not recovered

The exact original final child formulas for:

- Route_A / Credit / Breadth;
- Route_C / ConcentrationBreadth;
- original T.

Most importantly, the exact formula/code that produced the accepted 2021-10 Early Breadth output was not found in personal-context retrieval, Library files, repo history, research branches, or the user's other related repositories.

Therefore the accepted 2021-10 output now has an explicit provenance label:

```
LEGACY_ACCEPTED_OUTPUT
FORMULA_PROVENANCE = MISSING
```

## Replacement screening

We did not silently fill the missing formulas with plausible substitutes.

Two Route_A candidates were tested and rejected:

- A1 credit-level formulation;
- A2 spread-shock formulation.

Both detect the 2007 credit deterioration too late, crossing 85 only around February 2008.

Three Route_C candidates were tested and rejected:

- C1 absolute-positive industry participation;
- C2 market-relative participation with arithmetic aggregation;
- C3 preregistered market-relative participation with geometric aggregation.

C2/C3 produce many historical false Early Breadth signals and fail to reproduce the accepted 2021-10 event.

No further threshold/weight tuning of these failed candidates is authorized.

## Current research-live state

As of 2026-10-16:

```
PolicyShock = 62.7442
Valuation = 98.9137
SizeWeakness = 45.4470

Route_B = 65.5810
=> NOT ARMED
```

and:

```
T_v2.4R = 13.7747
DD12 = 2.033%
=> NO PRICE BREAKDOWN
```

Because original Route_A and Route_C are unresolved:

```
Full Pressure = PARTIAL_ROUTE_COVERAGE
```

It is valid to say the **Policy Route is not armed**.

It is not valid to claim the complete legacy V2.4 model is currently IDLE.

## Research decision

The 2022 repair is accepted as a successful independent policy path.

Further A/C work must follow one of two routes:

1. recover an authentic original artifact; or
2. build a newly named, preregistered next-generation model from a genuinely new hypothesis.

Do not keep retuning A1/A2/C1/C2/C3 until they resemble the legacy fixtures.


## Forward Shadow operational status

The validated Route_B path is now implemented as a forward research process.

GitHub Actions live dry-run passed end-to-end using real external data.

Current 2026-10-16 output:

```
2Y Treasury = 4.74%
6M anchor = 3.78%
RateShock = 100.00

TaperShock = 6.8606
PolicyShock = 62.7442

Valuation = 98.9137
SizeWeakness = 45.4470

Route_B = 65.5810
top-location gate = TRUE
Route_B pressure gate = FALSE
Route_B-only state = IDLE

T_v2.4R = 13.7753
DD12 = 2.0331%
Price Breakdown = FALSE
```

The first direct FRED live attempt timed out from GitHub Actions. That was treated as a provider failure, not a model failure.

The operational source path is now:

- 2Y Treasury: U.S. Treasury official Daily Treasury Par Yield Curve Rates;
- WALCL: current static FRED WALCL mirror, with direct FRED retained as fallback;
- Valuation: Robert Shiller / Yale feed;
- SizeWeakness: Ken French Data Library SMB;
- SPY: Yahoo Finance unadjusted Close.

The pipeline records the actual provider used in every snapshot.

The initial forward snapshot/history are stored under `docs/data/`, and the existing dashboard now contains a separate **Market Top Shadow · Route_B Forward** card.

The dashboard explicitly preserves:

```
Route_A = UNRESOLVED
Route_C = UNRESOLVED
Full Pressure authoritative = FALSE
```

so the Route_B-only state cannot be mistaken for the full legacy V2.4 model.
