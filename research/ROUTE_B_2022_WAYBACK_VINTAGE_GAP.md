# 2022 Route_B — Wayback Vintage Coverage Audit

Status: **ARCHIVE COVERAGE GAP CONFIRMED**

The remaining question was whether the exact Ken French factor ZIP available by **2022-01-03** could be recovered from the Internet Archive.

A dedicated GitHub Actions workflow queried Wayback and downloaded the archived ZIP bytes directly.

## Result

Wayback returned six pre-cutoff candidates.

The newest usable archived ZIP was:

```
timestamp: 2021-04-13 02:05:42 UTC
last monthly row: 2021-02
```

Older captures included:

```
2020-07-14 -> through 2020-05
2020-05-03 -> through 2020-03
```

No archived ZIP captured on or before:

```
2022-01-03 23:59:59 UTC
```

contained the required:

```
2021-11
```

monthly factor row.

## Meaning

This is not a parsing or access failure.

The audit successfully:

- queried the Wayback CDX index;
- retrieved archived Ken French ZIP files;
- opened the ZIP bytes;
- parsed their monthly Fama–French factor tables.

The missing piece is simply that Wayback did not capture a sufficiently recent version before the cutoff.

Therefore:

```
exact Jan-3-2022 web-published factor vintage
= NOT RECOVERABLE FROM WAYBACK
```

## Evidence hierarchy after this audit

### Strong evidence

1. Conservative publication-lag replay:
   ```
   Route_B = 85.3343
   ```

2. Official Kenneth French July-2022 historical cut:
   ```
   Route_B = 85.5692
   ```

3. Independent static historical variants:
   ```
   Route_B range = 85.3048 to 85.6570
   ```

All pass the frozen 85 threshold.

### Remaining provenance gap

```
exact factor file available on 2022-01-03
= unresolved because no sufficiently recent archived copy was found
```

The correct research conclusion is therefore:

> 2022 Route_B is robust to observed historical revisions and passes an official 2022-era CRSP archive cut, but an exact January 3 publication-time factor-file replay cannot be proven from the archives currently recoverable.

No formula or threshold change is authorized by this gap.


## Superseding evidence update — official December-2021 vintage recovered

The Wayback result above remains factually correct:

```
no pre-2022-01-03 Wayback capture contains 2021-11
```

However, this is no longer the same thing as saying the **factor vintage content** is unavailable.

A direct official Historical_Archives probe found:

```
Historical_Archives/12 2021 Update/ftp/
F-F_Research_Data_Factors_CSV.zip
```

The file:

- is a valid official Ken French ZIP;
- ends at monthly row `202111`;
- internally states:

```
This file was created by CMPT_ME_BEME_RETS using the 202111 CRSP database.
```

Its SHA-256 is:

```
e3c1eb5dd56764be0ed851ef1c7cedb48fab895bc24302c932a15d8474938d86
```

Recomputed from that official December-2021 vintage:

```
SizeWeakness = 84.7368421053
```

Combined with the real pre-cutoff Shiller valuation and primary-source PolicyShock:

```
Route_B = 85.3338068250
threshold = 85
margin = +0.3338068250
```

Therefore the precise provenance split is now:

```
official Dec-2021 factor-vintage content = RECOVERED
exact Jan-3 Wayback/web-delivery bytes = NOT RECOVERED
```

The current server reports a 2022-11-29 `Last-Modified` header, so that HTTP metadata must not be used as proof that the exact current bytes were downloadable on 2022-01-03.

Thus the Wayback gap remains a **delivery-timestamp provenance gap**, not a numerical SizeWeakness-vintage gap.
