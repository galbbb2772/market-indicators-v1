# Market Top Shadow Live Snapshot — 2026-10-16

Status: **ROUTE_B RESOLVED / FULL PRESSURE PARTIAL / RESEARCH ONLY**

## Current canonical Policy Route

### PolicyShock

- 2Y Treasury: 3.76% on 2026-04-15 -> 4.77% on 2026-10-15
- six-month move: +101 bp
- RateShock = 100
- WALCL TaperShock = 6.861
- PolicyShock = **62.744**

The rate shock is extreme, but the balance-sheet taper component is weak.

### Canonical Valuation

The original Top Trigger definition has been restored:

```
Valuation = expanding percentile of Shiller CAPE
```

For PIT use on 2026-10-16, October's unfinished month is not used. September 2026 is the last completed signal month:

- CAPE = 40.5808741
- Valuation = **98.913665**

The live current CAPE around 40.54 remains context only.

### Canonical SizeWeakness

The original definition has also been restored:

```
B_size = -CumSMB_6m
SizeWeakness = expanding percentile(B_size)
```

Latest available Fama-French month in this study: August 2026.

- CumSMB_6m = +0.7635365%
- B_size = -0.7635365%
- SizeWeakness = **45.446951**

### Route_B

```
Route_B =
cbrt(
  98.913665
  * 62.744247
  * 45.446951
)
= 65.581043
```

Therefore:

```
Route_B = 65.58 < 85
Policy Route = NOT ARMED
```

The current setup has extreme valuation and extreme 2Y repricing, but not the small-cap weakness or QE-to-taper reversal needed to reproduce the 2022 policy route.

## Price confirmation

SPY on 2026-10-16:

- Close = 763.25
- 252-session high close = 779.09
- drawdown = 2.033%
- prior-completed 10M MA = 720.884
- T_v2.4R = **13.775**

```
PRICE_BREAKDOWN_v2.4R = FALSE
```

## 2022 PIT correction retained

The old research branch used Route_B≈88.72 as the 2022-01-03 strict-PIT golden value.

That was too aggressive because it used later monthly SizeWeakness information.

Using November 2021 monthly inputs conservatively:

- Valuation = 98.580721
- SizeWeakness = 84.736842
- PolicyShock = 74.388619

gives:

```
Route_B = 85.334292 > 85
```

So the 2022 Policy route still passes, but only narrowly.

## Overall state

Canonical Route_B is now resolved. However:

- Route_A = unresolved
- Route_C = unresolved

Therefore the full:

```
Pressure = max(Route_A, Route_B, Route_C)
```

cannot yet be declared authoritative.

Current research-live state:

```
Policy Route_B: 65.58 -> NOT ARMED
T_v2.4R: 13.78 -> NO BREAKDOWN
Full Pressure: PARTIAL_ROUTE_COVERAGE
```

The next task is to restore Route_A and Route_C from their original definitions rather than substitute Market Model V2 proxies.
