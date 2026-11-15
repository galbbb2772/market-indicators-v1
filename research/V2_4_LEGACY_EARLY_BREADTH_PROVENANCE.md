# V2.4 Legacy Early-Breadth Provenance Gap

Status: **CONFIRMED PROVENANCE GAP**

The accepted historical V2.4 matrix contains:

```
2022 event
accepted trigger: 2021-10
accepted trigger type: EARLY_BREADTH
```

That accepted output remains part of the historical research record.

However, the exact implementation that produced it has not been recovered.

## What was searched

The recovery pass covered:

- prior personal-context retrieval;
- available Library/conversation files;
- current and research branches of `market-indicators-v1`;
- `frozen-v4`;
- `frozen-v4-dashboard`;
- `market-structure-lab`;
- `market-research-terminal`;
- commit-message searches for breadth, Route_C, V2.4, concentration, credit and market-top terminology.

No final V2.4 Early Breadth code artifact was found.

The old `market-indicators-v1` research branches contain Market Model V2/backtest work, not the Market Top Trigger implementation.

## What is known

The outer state rule is preserved:

```
Early Breadth =
    Pressure >= 85
    AND Route_C >= 85
    AND delta Breadth_3m >= 10
```

and:

```
Route_C = sqrt(Valuation * ConcentrationBreadth)
```

But the exact final child definitions that generated the accepted 2021-10 result are not reproducible from retained artifacts.

Specifically unresolved:

- final `ConcentrationBreadth` mapping;
- final `Breadth` mapping;
- exact monthly / daily alignment used by `delta Breadth_3m`;
- exact point-in-time publication semantics of those child inputs.

## Why the recovered clues are not enough

Five explicit replacement candidates have now been tested without post-hoc threshold tuning:

- A1 — rejected;
- A2 — rejected;
- C1 — rejected;
- C2 — rejected;
- C3 — rejected.

C2/C3 used the strongest retained concentration clue—12-industry market-relative participation plus leader-versus-median gap—yet produced many false Early Breadth episodes and did not reproduce 2021-10.

Therefore the clue is not a complete formula.

## Evidence policy

The 2021-10 fixture is now classified as:

```
LEGACY_ACCEPTED_OUTPUT
FORMULA_PROVENANCE = MISSING
```

It may be used to say:

> the prior research run accepted a 2021-10 Early Breadth path.

It may **not** be used to say:

> the current repository can reproduce the exact V2.4 Early Breadth formula.

Nor may a replacement be tuned until it matches 2021-10 and then silently inherit the original Route_C name.

## Consequence for the present research branch

The independently reconstructed path remains valid:

```
2022-01-03
PolicyShock V2.1.1
-> Route_B = 85.3343
-> ARMED

2022-01-20
T_v2.4R + DD12 gate
-> PRICE_BREAKDOWN_v2.4R
```

That path does not depend on recovering the missing legacy Route_C formula.

Current 2026 research-live status also remains:

```
Route_B = 65.58 -> NOT ARMED
T_v2.4R = 13.77 -> NO BREAKDOWN
Full Pressure = PARTIAL_ROUTE_COVERAGE
```

Original Route_A and Route_C remain unresolved.
