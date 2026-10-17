# 2022 Route_B — Official Ken French Archive Audit

Status: **PASS / OFFICIAL NEAR-VINTAGE EVIDENCE**

A dedicated GitHub Actions audit downloaded the official Kenneth R. French historical archive:

```
July 2022 data cut
released August 2022
F-F Research Data Factors
```

and recomputed the frozen 2021-11 SizeWeakness input.

## Official archive input

SMB from June through November 2021:

```
2021-06   +1.70
2021-07   -3.99
2021-08   -0.43
2021-09   +0.72
2021-10   -2.35
2021-11   -1.32
```

Using the unchanged rule:

```
B_size = -CumSMB_6m
SizeWeakness = expanding current-inclusive percentile(B_size)
```

the official July-2022 archive gives:

```
SizeWeakness = 85.43859649
```

Holding the frozen conservative 2022 inputs:

```
Valuation = 98.5807214666
PolicyShock = 74.3886192578
```

we get:

```
Route_B
= cbrt(Valuation * PolicyShock * SizeWeakness)
= 85.56921185
```

Therefore:

```
Route_B >= 85
PASS
```

Margin:

```
Route_B - 85 = +0.56921185
```

The mathematical SizeWeakness failure boundary is:

```
83.74488435
```

Official July-2022 archive margin above that boundary:

```
+1.69371214
```

## Comparison with current canonical history

Current canonical reconstructed history:

```
SizeWeakness = 84.73684211
Route_B = 85.33429176
```

Official July-2022 archive:

```
SizeWeakness = 85.43859649
Route_B = 85.56921185
```

The newer database revisions therefore do **not** create the 2022 pass. The official 2022-era annual archive actually gives a slightly stronger result.

## Evidence level

We can now say:

> The 2022 Route_B pass survives an official Ken French 2022 CRSP historical data cut.

We still cannot say:

> We recovered the exact factor file that was available on 2022-01-03.

The official archive policy retains annual July cuts, not every monthly publication vintage.

So the correct evidence labels are:

```
conservative publication lag = PASS
official 2022 annual-cut robustness = PASS
cross-version revision sensitivity = PASS
exact Jan-3 monthly vintage = UNRESOLVED
```

No threshold, weight, or formula was changed after observing this archive result.
