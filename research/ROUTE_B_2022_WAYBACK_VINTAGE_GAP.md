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
