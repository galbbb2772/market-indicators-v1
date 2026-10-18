# PolicyShock 2022 — Primary-Source PIT Audit

Status: **PASS / PRIMARY-SOURCE PIT CHAIN**

This audit isolates the PolicyShock leg of the 2022 Route_B reconstruction.

It does not depend on current FRED WALCL history for the three balance-sheet inputs.

## RateShock

Strict same-day exclusion is preserved.

For the 2022-01-03 state, the latest prior daily Treasury observation is:

```
2021-12-31 2Y = 0.73%
```

The frozen six-calendar-month anchor is:

```
2021-06-30 2Y = 0.25%
```

Therefore:

```
delta_6m = +48 bp

RateShock
= 100 * clip((48 - 10) / 60, 0, 1)
= 63.33333333
```

The audit live-downloads the U.S. Treasury Daily Treasury Par Yield Curve table and asserts those exact observations.

The Treasury evidence label is deliberately conservative:

```
OFFICIAL HISTORICAL SERIES
NOT ARCHIVED JAN-3 PAGE BYTES
```

## TaperShock

The three frozen WALCL inputs are directly present in dated Federal Reserve H.4.1 releases:

| H.4.1 release | Observation | Total assets, $mm |
|---|---|---:|
| 2021-07-01 | 2021-06-30 | 8,078,544 |
| 2021-09-30 | 2021-09-29 | 8,447,981 |
| 2021-12-30 | 2021-12-29 | 8,757,460 |

The observation spacing is exactly:

```
26w -> 13w = 91 days
13w -> now = 91 days
```

All three releases occurred before 2022-01-03.

Frozen calculation:

```
TaperShock = 90.97154814
```

Therefore:

```
PolicyShock
= 0.60 * 63.33333333
+ 0.40 * 90.97154814
= 74.38861926
```

## Conservative combined Route_B check

Use the genuine pre-cutoff Shiller valuation already recovered:

```
Valuation = 98.5790408526
```

and the lower current-vintage conservative SizeWeakness:

```
SizeWeakness = 84.7368421053
```

Then:

```
Route_B
= cbrt(
    98.5790408526
    * 74.3886192578
    * 84.7368421053
  )
= 85.3338068250
```

Result:

```
Route_B >= 85
PASS
```

The PolicyShock failure boundary under this conservative Valuation/Size pair is:

```
Critical PolicyShock = 73.51905461
```

Observed PolicyShock margin:

```
+0.86956464
```

## Evidence meaning

This materially strengthens the 2022 provenance chain.

We can now say:

- the three balance-sheet observations are proven by dated Federal Reserve primary-source releases available before 2022-01-03;
- the frozen 2Y values are reproduced from the official Treasury historical table;
- the PolicyShock formula reproduces the frozen 74.3886 value;
- even paired with the genuine pre-cutoff Shiller valuation and the lower SizeWeakness variant, Route_B remains above 85.

We still do **not** claim:

- exact archived Jan-3 Treasury page bytes were recovered;
- exact Jan-3 Ken French monthly factor bytes were recovered.

Those provenance gaps remain separately labeled.
