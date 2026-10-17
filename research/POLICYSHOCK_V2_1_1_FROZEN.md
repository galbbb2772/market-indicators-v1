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

1. DGS2 and WALCL must be gated by **publication availability**, not observation date alone.
2. WALCL Wednesday observations may only be consumed after the corresponding H.4.1 release is available.
3. Current-month final CAPE must never be used earlier in that same month. Use the last completed, available month or a true vintage reconstruction.
4. EOD market-derived values may update state only after the close; no close-to-same-close execution.
5. Missing data is not silently converted to zero risk.

## Structural invariant

Pure rate repricing must be unable to arm Route_B by itself:

```
PolicyShock_max_when_TaperShock_0 = 60
Route_B_max = cbrt(100 * 60 * 100) = 84.34 < 85
```

This invariant is intentional and frozen.

## 2022 strict-PIT golden case

Inputs:

- DGS2 latest released: 0.73
- DGS2 six-month anchor: 0.25
- WALCL: 8.078544T -> 8.447981T -> 8.757460T
- Valuation: 97.9
- SizeWeakness: 95.9

Expected outputs:

- RateShock = 63.3333333333
- TaperShock = 90.9715481444
- PolicyShock = 74.3886192578
- Route_B = 88.7229415743

Expected result:

```
Route_B > 85  => PASS
```

## Negative controls

The regression suite must retain these behaviors:

- Pure RateShock=100 with TaperShock=0 cannot arm Route_B.
- Approximate 2005 PolicyShock=48 cannot arm Route_B even with both other inputs at 100.
- 2011 RateShock≈28.3 cannot arm Route_B even under the intentionally extreme assumption TaperShock=100.
- Continuing QT (no prior expansion) produces TaperShock=0.
- Pre-WALCL history may use TaperShock=0 by construction.
- An in-era data outage returns missing/NA, not zero.

## Versioning

Any change to:

- 10 bp floor,
- 60 bp rate span,
- 3% expansion gate,
- 1% deceleration gate,
- 0.60 / 0.40 weights,
- Route_B geometric aggregation,
- ARMED threshold interaction,
- publication-time semantics,

requires a new version. Do not overwrite V2.1.1.
