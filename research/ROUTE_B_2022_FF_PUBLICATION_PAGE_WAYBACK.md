# 2022 Route_B — Fama-French Publication-Page Wayback Audit

Status: **NO PRE-CUTOFF PUBLICATION-PAGE PROOF**

This audit tested a different provenance question from the ZIP-byte audit.

The official December-2021 Fama-French historical archive has already been recovered and its content is reproducible:

```
CRSP database = 202111
last monthly row = 202111
SizeWeakness = 84.7368421053
Route_B = 85.3338068250
```

The remaining question was whether a Ken French **official web page** captured before:

```
2022-01-03 23:59:59 UTC
```

independently showed that the monthly FF3 series already extended through November 2021.

## Wayback result

The live audit inspected two qualifying pre-cutoff official-page captures.

Result:

```
status = NO_PRE_CUTOFF_PUBLICATION_PAGE_PROOF
snapshot_count = 2
query_errors = []
```

Observed evidence:

- one captured page did not expose a parseable FF3 monthly terminal month;
- the parseable FF3 description-page capture ended at:

```
Monthly Returns ... October 2021
```

No qualifying pre-cutoff page was found showing:

```
Monthly Returns ... November 2021
```

## Meaning

This does **not** contradict the recovered December-2021 archive content.

It means the surviving web archive is too sparse to independently establish the publication timestamp of the November-2021 factor update.

Therefore the evidence split remains:

```
official Dec-2021 factor-vintage content = RECOVERED
numerical SizeWeakness replay = REPRODUCIBLE
conservative Route_B = PASS

exact ZIP pre-cutoff Wayback capture = ABSENT
official page pre-cutoff 202111 publication proof = ABSENT
exact Jan-3 web-delivery timing = UNPROVEN
```

The lack of web-delivery proof is a provenance limitation, not a reason to alter the model.

No formula, threshold, lag, or weight was changed.
