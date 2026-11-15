# 2022 Route_B — December-2021 FF Namespace Wayback Audit

Status: **NO PRE-CUTOFF NAMESPACE CAPTURE / DELIVERY-TIMESTAMP GAP CONFIRMED**

The exact December-2021 FF3 ZIP audit returned no pre-cutoff capture.  
The publication-page audit also found no pre-cutoff page proving the 2021-11 factor month.

This audit widened the search to the entire official namespace:

```
Kenneth French
Data_Library/Historical_Archives/12 2021 Update/
```

using Wayback CDX prefix matching.

Cutoff:

```
2022-01-03 23:59:59 UTC
```

Four URL variants were queried:

- HTTP / HTTPS;
- lower-case / upper-case `Faculty` path variants.

Live GitHub Actions result:

```
query errors = 0
pre-cutoff namespace captures = 0
```

Therefore:

```
exact ZIP pre-cutoff capture = ABSENT
pre-cutoff publication-page proof through 202111 = ABSENT
pre-cutoff Dec-2021 namespace capture = ABSENT
```

## What this means

This strengthens the diagnosis of the remaining provenance limitation.

It does **not** prove:

> the December-2021 archive was not publicly available by 2022-01-03.

Wayback is an incomplete crawler.

It does prove:

> surviving Wayback coverage cannot independently timestamp delivery of the recovered December-2021 archive, even when the search is widened from the exact FF3 ZIP URL to the full archive namespace.

The independently established content evidence remains unchanged:

```
official Dec-2021 archive content = RECOVERED
internal CRSP database = 202111
last monthly row = 202111
SizeWeakness = 84.7368421053

pre-cutoff Shiller Valuation = 98.5790408526
primary-source PolicyShock = 74.3886192578

Route_B = 85.3338068250
threshold = 85
PASS
```

So the final split remains:

```
NUMERICAL_INPUT_CHAIN = CLOSED
OFFICIAL_FACTOR_VINTAGE_CONTENT = RECOVERED
EXACT_WEB_DELIVERY_TIMESTAMP = UNPROVEN
WAYBACK_DELIVERY_COVERAGE = INSUFFICIENT
```

No model parameter, lag, threshold, or historical label is changed.
