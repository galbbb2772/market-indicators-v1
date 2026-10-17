# 2022 Route_B — Fama–French Revision Sensitivity

Status: **PASS REVISION SENSITIVITY / EXACT JAN-2022 VINTAGE STILL UNRESOLVED**

The conservative 2022 policy-path result is narrow:

```
Valuation = 98.5807214666
PolicyShock = 74.3886192578
SizeWeakness = 84.7368421053

Route_B = 85.3342917570
threshold = 85
```

Because this margin is small, historical-data revisions matter.

## Exact vintage limitation

Kenneth French maintains official historical archives for the Fama/French 3 Factors, but the retained archives are annual **July data cuts released in August**.

That is useful for historical revision research, but it does not directly provide the exact monthly factor file that was visible on **2022-01-03**.

Therefore this study does **not** claim exact publication-time vintage recovery.

## Failure boundary

Holding the conservative 2022 Valuation and PolicyShock fixed:

```
critical SizeWeakness
= 85^3 / (Valuation * PolicyShock)
= 83.74488435
```

If the true point-in-time SizeWeakness were below about **83.745**, the independent Route_B path would fall below 85.

Current canonical:

```
SizeWeakness = 84.73684211
margin above critical = 0.99195775
```

## Cross-version sensitivity test

The same frozen rule was re-run on several independently stored Fama–French 3-factor histories.

| Variant | SMB Jun→Nov 2021 | SizeWeakness | Route_B |
|---|---|---:|---:|
| Current canonical | 1.70, -3.93, -0.32, 0.66, -2.26, -1.31 | 84.7368 | 85.3343 |
| Static A | 1.70, -3.93, -0.32, 0.66, -2.26, -1.31 | 84.6491 | 85.3048 |
| Static B | 1.76, -3.96, -0.46, 0.75, -2.30, -1.36 | 85.2632 | 85.5106 |
| Static C | 1.70, -3.93, -0.32, 0.66, -2.27, -1.31 | 84.7368 | 85.3343 |
| Static D | 1.60, -3.94, -0.46, 0.67, -2.37, -1.32 | 85.7018 | 85.6570 |

Observed Route_B range:

```
85.3048 to 85.6570
```

Every sampled historical variant remains above the frozen threshold.

Minimum sampled margin:

```
Route_B - 85 = +0.3048
```

and the lowest sampled SizeWeakness remains:

```
84.6491 - 83.7449 = +0.9042
```

above the mathematical failure boundary.

## Interpretation

This materially strengthens the 2022 result.

It is now fair to say:

> The reconstructed 2022 Route_B pass is robust to the range of Fama–French historical revisions observed across the sampled independent static histories.

It is still **not** fair to say:

> The exact 2022-01-03 publication-time Fama–French vintage has been recovered.

Those are different claims.

## Frozen research decision

Keep:

```
2022-01-03 Route_B policy path = PASS
```

with two labels:

```
publication-lag conservative = YES
revision-sensitivity pass = YES
exact monthly vintage proof = NO
```

No PolicyShock weight, Route_B threshold, or SizeWeakness formula was changed during this test.
