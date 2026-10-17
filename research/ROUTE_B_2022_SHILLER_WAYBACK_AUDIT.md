# 2022 Route_B — Shiller Wayback Valuation Audit

Status: **ARCHIVE GAP + CONSERVATIVE PRE-CUTOFF ROBUSTNESS PASS**

The remaining Valuation-vintage question was whether the Robert Shiller `ie_data.xls` workbook available by **2022-01-03** could be recovered with the November 2021 CAPE row.

## Wayback result

The audit queried the historical Yale workbook URL in both HTTP and HTTPS forms with a hard cutoff:

```
2022-01-03 23:59:59 UTC
```

Wayback returned 25 pre-cutoff candidates.

The newest clean, temporally consistent, parseable workbook was:

```
capture: 2021-10-12 12:29:41 UTC
last month: 2021-09
CAPE: 38.3422797126
```

No clean pre-cutoff workbook containing **2021-11** was recovered.

Therefore:

```
exact Jan-3-2022 Shiller Valuation vintage = UNRESOLVED
```

## Parser audit

An initial audit iteration exposed an important parser hazard: the workbook contains an **Excess CAPE Yield** series, which must not be mistaken for CAPE.

The audit now:

- accepts an exact `CAPE` header when present;
- otherwise falls back to the canonical Shiller workbook location, Excel column M;
- rejects implausible CAPE scale;
- rejects Wayback workbooks whose last data month is later than the capture month.

The corrected September-2021 CAPE is **38.3423**, not the roughly 0.03 excess-yield scale.

## Archived Valuation score

Using only the cumulative CAPE history inside that real 2021-10-12 workbook:

```
Valuation_2021-09 = 98.5790408526
```

This is nearly identical to the current reconstruction used for November 2021:

```
98.5807214666
```

## Route_B robustness with official SizeWeakness archive

Using:

```
Archived Sep-2021 Valuation = 98.5790408526
PolicyShock = 74.3886192578
Official Jul-2022 archive SizeWeakness = 85.4385964912
```

gives:

```
Route_B = 85.5687255790
margin above 85 = +0.5687255790
```

The critical Valuation boundary in this combination is:

```
96.6264833161
```

## Cross-vintage conservative combination

Use the same real pre-cutoff archived Valuation, but replace SizeWeakness with the **lower** current-vintage conservative reconstruction:

```
SizeWeakness = 84.7368421053
```

Then:

```
Route_B = 85.3338068250
margin above 85 = +0.3338068250
```

The corresponding critical Valuation is:

```
97.4267026396
```

and the archived score still sits above it.

## Interpretation

We still cannot claim:

> the exact November-2021 Shiller workbook available on 2022-01-03 has been recovered.

We can now claim something stronger than before:

> A real pre-cutoff Shiller workbook captured on 2021-10-12 already places Valuation high enough that the 2022 Route_B pass survives both the official 2022-era SizeWeakness archive and the lower current-vintage SizeWeakness reconstruction.

No threshold or weight was changed after observing the archived workbook.
