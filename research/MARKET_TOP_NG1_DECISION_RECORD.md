# Market Top NG1 — Final Research Decision

Status:

```
NG1_CLOSED_NO_TOP_ROUTE_PROMOTION
```

NG1 is closed as a model-development branch.

No NG1 parameter will be retuned.

## Route_C_NG1

Final decision:

```
REJECT
```

It detected the intended 2000 and 2021-2022 concentration regimes, but failed the preregistered 1998 negative control and generated too many additional historical ARMED episodes.

It is not promoted.

## Route_A_NG1

NG1-A did substantially better in its first screen.

It passed:

- the preregistered 2007 positive window;
- the 2000 / 2011 / 2018 negative windows;
- the preregistered cap of two additional historical episodes;
- an independent-source 2007 replay.

Independent 2007 replay:

```
Route_A_NG1 = 86.79223562
threshold = 85
margin = +1.79223562
```

So the 2007 hit is not a mirror-data artifact.

However, top specificity fails under the complete episode evidence.

## Evaluated NG1-A episodes

| Episode | Classification |
|---|---|
| 1998-11 → 1999-03 | CLEAR_TOP_FALSE_POSITIVE |
| 2007-11 | MAJOR_TOP_HIT |
| 2012-02 | CORRECTION_RISK_NOT_MAJOR_TOP |
| 2025-07 | CLEAR_TOP_FALSE_POSITIVE |
| 2025-09 | CORRECTION_RISK_NOT_MAJOR_TOP |

Summary:

```
evaluated episodes = 5
major-top hits = 1
clear top false positives = 2
correction / non-major-top = 2
```

The two post-2022 holdout episodes are especially important because they were not used in the original 1993-2022 screen.

### 2025-07

```
Route_A_NG1 = 85.4109
252-session return = +19.87%
worst below signal price = -1.64%
```

This is a clear false top.

### 2025-09

```
Route_A_NG1 = 85.3933
252-session return = +14.68%
max peak-to-trough correction = -9.13%
```

This is useful stress information, but not a major-top call.

## Final interpretation

The supported statement is:

> Route_A_NG1 is a source-validated credit/breadth stress diagnostic.

The unsupported statement is:

> Route_A_NG1 is a validated Market Top route.

Therefore:

```
Route_A_NG1 top-route decision = DO_NOT_PROMOTE
retained use = RESEARCH_CREDIT_BREADTH_STRESS_DIAGNOSTIC
```

It must not be inserted into:

```
Pressure = max(Route_A, Route_B, Route_C)
```

and it must not replace the unresolved legacy Route_A.

## Frozen governance

From this decision onward:

- do not tune NG1;
- do not rename NG1 as legacy Route_A;
- do not add NG1 to production Pressure;
- do not hide the 1998 or 2025-07 false positives;
- do not reinterpret correction signals as major-top successes.

If a more top-specific credit route is explored, it must be:

```
NG2 or later
```

with a new preregistration written before the new formula is tested.
