# Route_A / Route_C Recovery Status

Status: **STRUCTURE RECOVERED / CHILD DEFINITIONS UNRESOLVED**

The research record is sufficient to confirm the outer V2.4 architecture:

```
Route_A = sqrt(Credit * Breadth)
Route_B = cbrt(Valuation * PolicyShock * SizeWeakness)
Route_C = sqrt(Valuation * ConcentrationBreadth)

Pressure = max(Route_A, Route_B, Route_C)
```

Route_B is now fully reconstructable. Route_A and Route_C are not.

## Route_A

Confirmed role:

**Credit / Breadth Breakdown**

Confirmed outer form:

```
Route_A = sqrt(Credit * Breadth)
```

However, prior research contains multiple evolving Credit/Breadth implementations. Recovered fragments include:

- Breadth families using A/D, NH/NL, moving-average participation, equal-weight versus cap-weight, and small-versus-large participation;
- Credit families using BAA-10Y spread, SLOOS/lending standards, delinquency acceleration, credit growth/underwriting quality, and funding stress.

The retained record contains mutually different intermediate formulas. No final V2.4 code artifact or unambiguous final child-block specification was recovered.

Therefore none of these candidate fragments may be promoted into live Route_A.

```
Route_A status = UNRESOLVED
```

## Route_C

Confirmed role:

**Bubble / Concentration / Breadth Exhaustion**

Confirmed outer form:

```
Route_C = sqrt(Valuation * ConcentrationBreadth)
```

Canonical Valuation has been restored as the expanding percentile of Shiller CAPE.

The research record also preserves the intended ConcentrationBreadth mechanism:

- 12-sector participation/exhaustion over a roughly six-month leadership window;
- evidence based on very narrow sector participation and a large leader-versus-median gap.

But the exact final V2.4 mapping and aggregation were not recovered.

Therefore the 12-sector concept remains a recovery clue, not executable canonical code.

```
Route_C status = UNRESOLVED
```

## Current live consequence

As of 2026-10-16:

```
Route_B = 65.5810 -> NOT ARMED
T_v2.4R = 13.7747 -> NO PRICE BREAKDOWN
Route_A = unresolved
Route_C = unresolved
```

So it is valid to say:

> the Policy Route is not armed and price breakdown is absent.

It is **not** valid to say:

> the full Market Top model is IDLE.

because:

```
Pressure = max(A, B, C)
```

and A/C are not yet canonical.

Full state therefore remains:

```
PARTIAL_ROUTE_COVERAGE
```

## Recovery rule

A/C may be restored only if one of the following occurs:

1. the actual final formula/code artifact is recovered; or
2. a replacement is explicitly preregistered under a new version name and validated separately.

Earlier candidate formulas may not silently inherit the V2.4 Route_A or Route_C names.
