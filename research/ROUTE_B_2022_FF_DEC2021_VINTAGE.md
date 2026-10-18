# 2022 Route_B — Official December-2021 Fama–French Vintage

Status: **PASS / OFFICIAL DECEMBER-2021 VINTAGE CONTENT RECOVERED**

This closes the main **SizeWeakness content-vintage** gap in the 2022 Route_B replay.

## Official source

The live GitHub Actions audit downloads:

```
Kenneth R. French
Historical_Archives/12 2021 Update
F-F_Research_Data_Factors_CSV.zip
```

The ZIP is valid, and its monthly factor table ends at:

```
202111
```

The file identifies its own vintage internally:

```
This file was created by CMPT_ME_BEME_RETS using the 202111 CRSP database.
```

Recorded ZIP fingerprint:

```
SHA-256
e3c1eb5dd56764be0ed851ef1c7cedb48fab895bc24302c932a15d8474938d86
```

## Old-vintage SMB values

The official December-2021 vintage contains:

```
2021-06   +1.80
2021-07   -3.96
2021-08   -0.48
2021-09   +0.80
2021-10   -2.28
2021-11   -1.35
```

These differ from later Ken French revisions, which is positive provenance evidence: this is not merely a current factor history exposed under an old-looking path.

Using the frozen rule:

```
B_size = -CumSMB_6m
SizeWeakness = expanding_percentile(B_size)
```

gives:

```
SizeWeakness = 84.7368421053
```

## Conservative cross-vintage Route_B

Combine:

```
Valuation
= 98.5790408526
(real Wayback Shiller pre-cutoff workbook)

PolicyShock
= 74.3886192578
(primary-source Treasury + dated H.4.1 audit)

SizeWeakness
= 84.7368421053
(official December-2021 FF vintage)
```

Then:

```
Route_B = 85.3338068250
threshold = 85
margin = +0.3338068250
```

The critical SizeWeakness boundary is:

```
83.7463120661
```

so the recovered December-2021 score is about:

```
+0.9905300392
```

percentile points above the failure boundary.

## What this resolves

It is now valid to say:

> The frozen SizeWeakness input can be reproduced from an official Kenneth French December-2021 historical vintage built from the 202111 CRSP database.

This is materially stronger than relying on a July-2022 annual archive or current history.

## What remains unproven

The current HTTP response says:

```
Last-Modified: Tue, 29 Nov 2022 17:09:26 GMT
```

That metadata reflects later server handling and cannot prove that the exact current ZIP bytes were downloadable from the same URL on 2022-01-03.

Wayback also did not capture a sufficiently recent FF ZIP before the cutoff.

Therefore the precise provenance split is:

```
official Dec-2021 factor-vintage content = RECOVERED
exact Jan-3 URL byte availability = NOT INDEPENDENTLY PROVEN
```

The second caveat is about web-delivery provenance, not about the numerical SizeWeakness replay.

No formula, lag, threshold, or weight was changed.
