# PolicyShock V2.1.1 — Frozen Research Spec

Status: **FROZEN / PASS**

This file freezes the independent Policy / Liquidity route used by the Market Top Trigger research model.

## Core formulas

```
RateShock = 100 * clip(((DGS2_now - DGS2_6m) * 100 - 10) / 60, 0, 1)

g_prev = WALCL_13w / WALCL_26w - 1
g_cur  = WALCL_now / WALCL_13w - 1

TaperShock =
    100
    * clip(g_prev / 0.03, 0, 1)
    * clip((g_prev - g_cur) / 0.01, 0, 1)

PolicyShock = 0.60 * RateShock + 0.40 * TaperShock

Route_B = cbrt(Valuation * PolicyShock * SizeWeakness)
```

ARMED threshold remains **85**.

## Point-in-time rules

1. DGS2 and WALCL must be gated by publication availability, not observation date alone.
2. WALCL Wednesday observations may only be consumed after the corresponding H.4.1 release is available.
3. Monthly CAPE and Fama-French SMB inputs must be gated by publication availability. Never use a later month to score an earlier trading day.
4. EOD market-derived values may update state only after the close; no close-to-same-close execution.
5. Missing data is not silently converted to zero risk.

## Structural invariant

Pure rate repricing must be unable to arm Route_B by itself:

```
PolicyShock_max_when_TaperShock_0 = 60
Route_B_max = cbrt(100 * 60 * 100) = 84.34 < 85
```

## 2022 conservative publication-lag golden case

As-of 2022-01-03, use daily/weekly macro information already released and conservatively restrict monthly Valuation/SizeWeakness to November 2021.

Inputs:

- DGS2 latest released: 0.73
- DGS2 six-month anchor: 0.25
- WALCL: 8.078544T -> 8.447981T -> 8.757460T
- Valuation (2021-11 CAPE expanding percentile): 98.5807214666
- SizeWeakness (2021-11 -CumSMB_6m expanding percentile, current-vintage reconstruction): 84.7368421053

Expected outputs:

- RateShock = 63.3333333333
- TaperShock = 90.9715481444
- PolicyShock = 74.3886192578
- Route_B = **85.3342917570**

Expected result:

```
Route_B > 85 => PASS
```

The earlier research value Route_B≈88.72 used later monthly size information and must not be labeled the 2022-01-03 strict-PIT golden result.

## Vintage evidence status

The macro PolicyShock leg is now independently primary-source validated for the 2022-01-03 replay:

- U.S. Treasury historical 2Y values reproduce 2021-12-31 = 0.73% and 2021-06-30 = 0.25%;
- dated Federal Reserve H.4.1 releases directly establish the 2021-06-30, 2021-09-29, and 2021-12-29 total-assets observations before the 2022-01-03 cutoff;
- these inputs reproduce PolicyShock = 74.38861926.

The remaining vintage limitation is monthly Valuation / SizeWeakness source bytes, not the PolicyShock macro leg.

For Valuation, a genuine pre-cutoff Shiller workbook through 2021-09 gives 98.57904085 and still preserves Route_B > 85.

For SizeWeakness, the exact Ken French monthly file visible on 2022-01-03 has not been recovered. Official July-2022 and later historical archive cuts plus the lower current-vintage reconstruction all preserve Route_B > 85. This must be described as revision-robust evidence, not exact Jan-3 factor-byte recovery.

The Treasury rate evidence uses the current official historical table; archived Jan-3 Treasury page bytes were not recovered. That provenance distinction remains explicit.

## Negative controls

- Pure RateShock=100 with TaperShock=0 cannot arm Route_B.
- Approximate 2005 PolicyShock=48 cannot arm Route_B even with both other inputs at 100.
- 2011 RateShock≈28.3 cannot arm Route_B even under the intentionally extreme assumption TaperShock=100.
- Continuing QT (no prior expansion) produces TaperShock=0.
- Pre-WALCL history may use TaperShock=0 by construction.
- An in-era data outage returns missing/NA, not zero.

## Versioning

Any change to the frozen rate/taper thresholds, 0.60/0.40 weights, Route_B aggregation, ARMED interaction, or publication-time semantics requires a new version.
