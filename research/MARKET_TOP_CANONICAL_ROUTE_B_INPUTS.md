# Canonical Route_B Inputs

This file restores the original Top Trigger definitions for the two non-policy Route_B inputs.

## Valuation

```
Valuation_t = expanding_percentile(Shiller CAPE_t)
```

The percentile is current-inclusive and uses only history available through t.

For live/PIT use, the signal must use the **last completed and available month**, not a final value for the current unfinished month.

As of 2026-10-16:

- current-month October CAPE is context only;
- September 2026 is the last completed month used for the signal;
- September CAPE = 40.5808740954;
- canonical Valuation = **98.9136649514**.

The reconstruction independently reproduces January 2022 CAPE 36.9368 at approximately the previously reported 97.9 percentile.

## SizeWeakness

Canonical definition:

```
CumSMB_6m = product(1 + SMB_m/100) - 1
B_size = -CumSMB_6m
SizeWeakness = expanding_percentile(B_size)
```

SMB is the Fama-French Small Minus Big factor.

The current Fama-French/CRSP data cut available in this study runs through August 2026.

For August 2026:

- six-month compounded SMB = +0.7635365%
- B_size = -0.7635365%
- SizeWeakness = **45.4469507101**

Therefore, using current strict-lag PolicyShock 62.7442467120:

```
Route_B =
cbrt(
  98.9136649514
  * 62.7442467120
  * 45.4469507101
)
= 65.5810427181
```

So the current Policy Route is:

```
Route_B = 65.58 < 85
=> NOT ARMED
```

## 2022 anti-lookahead correction

The previous research branch called Route_B≈88.72 a "strict-PIT" 2022-01-03 value. That label was too aggressive because it used a later monthly SizeWeakness reading.

For a conservative replay, use monthly inputs no later than November 2021:

- Valuation = 98.5807214666
- SizeWeakness = 84.7368421053
- PolicyShock = 74.3886192578

Then:

```
Route_B = 85.3342917570 > 85
```

The 2022 Policy route still passes, but only narrowly.

The older ~88.72 value is retained only as a later-month research comparison and must not be called the 2022-01-03 strict-PIT golden value.

## Vintage caveat

Ken French explicitly maintains historical factor archives and CRSP changed its US research-return source format from FIZ to CIZ beginning with the January 2025 data release.

The 2026 current-vintage historical reconstruction therefore may not be numerically identical to the factor values visible to a researcher in early 2022.

A true 2022-vintage replay remains a separate validation task; it must not be hidden by the current-vintage reconstruction.
