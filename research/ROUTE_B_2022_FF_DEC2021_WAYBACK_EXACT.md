# 2022 Route_B — Exact URL Wayback Audit for December-2021 FF Vintage

Status: **NO PRE-CUTOFF CAPTURE / DELIVERY-TIMESTAMP GAP ONLY**

The exact official archive URL tested was:

```
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/
Data_Library/Historical_Archives/12%202021%20Update/ftp/
F-F_Research_Data_Factors_CSV.zip
```

Hard cutoff:

```
2022-01-03 23:59:59 UTC
```

## Result

Wayback CDX returned:

```
pre-cutoff snapshots = 0
errors = []
```

Therefore:

```
exact SHA captured pre-cutoff = FALSE
any Dec-2021 vintage capture pre-cutoff = FALSE
```

This is not an access or parser failure. The exact URL simply has no qualifying Wayback capture.

## What remains established independently

The official December-2021 Historical_Archives ZIP is directly downloadable today and has been fingerprinted:

```
SHA-256
e3c1eb5dd56764be0ed851ef1c7cedb48fab895bc24302c932a15d8474938d86
```

Its internal header says:

```
This file was created by CMPT_ME_BEME_RETS using the 202111 CRSP database.
```

Its monthly table ends at:

```
202111
```

and reproduces:

```
SizeWeakness = 84.7368421053
Route_B = 85.3338068250
threshold = 85
PASS
```

using the genuine pre-cutoff Shiller valuation and primary-source PolicyShock chain.

## Final provenance split

The correct research language is now:

```
official Dec-2021 factor-vintage content = RECOVERED
numerical SizeWeakness replay = REPRODUCIBLE
2022 Route_B conservative replay = PASS

exact Jan-3 Wayback capture = ABSENT
exact Jan-3 web-delivery timestamp proof = UNAVAILABLE
```

The missing Wayback capture does not invalidate the recovered factor vintage. It limits only the strength of the claim about when the exact current ZIP bytes were externally observable at that URL.

No model parameter was changed.
