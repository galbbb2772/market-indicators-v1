# 2022 Route_B — PIT Uncertainty Budget

Status: **PASS, BUT WITH A NARROW MARGIN**

This note quantifies how much input-vintage movement would be required to overturn the most conservative observed 2022 Route_B pass.

It does not change the formula, threshold, or any historical labels.

## Conservative baseline

Use the strongest point-in-time chain currently available:

```
Valuation = 98.5790408526
  genuine pre-cutoff Shiller archive, latest usable 2021-09 observation

PolicyShock = 74.3886192578
  Treasury historical table + dated Federal Reserve H.4.1 releases

SizeWeakness = 84.7368421053
  lower observed official/current reconstruction
```

Then:

```
Route_B = 85.3338068250
threshold = 85
margin = +0.3338068250
```

So the result is a pass, but it is not a wide-margin pass.

## Single-input failure boundaries

Holding the other two inputs fixed:

| Input | Baseline | Failure boundary | Relative deterioration required |
|---|---:|---:|---:|
| Valuation | 98.5790 | 97.4267 | 1.1689% |
| PolicyShock | 74.3886 | 73.5191 | 1.1689% |
| SizeWeakness | 84.7368 | 83.7463 | 1.1689% |

Any one input would therefore need to deteriorate by about **1.169%** on its own to move Route_B back to 85.

## Joint proportional stress

Because Route_B is the cube root of the three-input product:

```
Route_B = cbrt(V * P * S)
```

the same-direction proportional deterioration needed to hit the threshold is:

| Inputs moving together | Required deterioration per input |
|---|---:|
| one input only | 1.1689% |
| two inputs equally | 0.5862% each |
| all three inputs equally | 0.3912% each |

This is the important caveat.

A 0.3338-point score margin sounds larger than it is: sufficiently coordinated small vintage shifts across all three inputs could overturn the pass.

## Observed vintage variation

What has actually been observed so far:

```
Valuation:
98.5790409 archived pre-cutoff
98.5807215 current reconstruction
span = 0.00168 points
```

```
SizeWeakness official archive range:
84.7368421 to 85.7017544
span = 0.96491 points
```

```
PolicyShock:
74.3886193
reproduced from primary-source Treasury / H.4.1 chain
```

Every observed combination tested remains above 85.

## Correct interpretation

The correct evidence statement is:

> Route_B > 85 is robust across every observed historical vintage and the primary-source PolicyShock chain, but the minimum reconstructed margin is narrow and exact Jan-3 monthly source bytes remain partly unrecovered.

Do not describe the 2022 Route_B result as having a large safety cushion.

Do not widen the margin by changing weights, thresholds, or publication-lag assumptions.
