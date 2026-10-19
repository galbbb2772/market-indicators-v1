# Market Top NG2-A — Pre-1993 Holdout Result

Status:

```
NG2_A_CLOSED_INSUFFICIENT_HOLDOUT_EVENTS
```

Decision:

```
INSUFFICIENT_HOLDOUT_EVENTS
```

Research only. No production scoring path is changed.

## Frozen test

The NG2-A formula and decision rule were committed before the holdout workflow was run.

Validation window:

```
requested: 1963-01 through 1992-12
effective after 120-month aligned warm-up: 1963-10 through 1992-12
monthly states: 351
```

The workflow completed successfully.

Workflow run:

```
39202778112
```

Result artifact:

```
market-top-ng2-a-pre1993-result
artifact id: 12164084180
sha256: e0cd5a5425736aa74cb631fafd3ce5bb0d97c0b01eaf0de54773435915d9a159
```

## Frozen decision outcome

The preregistered route produced:

```
ARMED episodes = 0
complete episodes = 0
major-top hits = 0
correction-risk episodes = 0
clear false-top episodes = 0
```

Therefore the preregistered minimum of two complete ARMED episodes is not met.

This is not a validation pass and is not converted into a failure by changing the threshold after the fact.

## Why there were no ARMED episodes

NG2 did exceed the pressure threshold during the 1990-1991 stress sequence:

| Effective month | Route_A_NG2 | Pressure >= 85 | Top-location gate |
|---|---:|---|---|
| 1990-11 | 86.5933 | yes | no |
| 1990-12 | 88.4544 | yes | no |
| 1991-01 | 86.2335 | yes | no |

The frozen top-location gate therefore correctly prevented those late stress states from becoming top calls.

The highest NG2 score while the top-location gate was actually true was:

```
1991-02 Route_A_NG2 = 82.9479
```

which remains below 85.

Other high gated observations include:

```
1990-07 = 78.4340
1987-08 = 77.2826
1987-01 = 76.7790
1964-02 = 76.3008
1964-03 = 75.6679
```

No threshold is changed in response.

## Structural interpretation

The frozen NG2 lead-lag idea did not generate enough pre-top events in the untouched holdout.

The strongest route values occurred after the 1990 market had already moved far enough from its recent high that the top-location condition was false.

The supported conclusion is:

> NG2-A can become extreme during late credit/breadth stress, but this holdout does not provide enough ARMED top episodes to validate it as a Market Top Route_A replacement.

The unsupported conclusions are:

- lowering 85 until an episode appears;
- removing the top-location gate;
- changing the FinancialLeadScore construction after seeing the holdout;
- calling the absence of false positives a successful validation.

## Pre-SPY price bridge sanity check

The frozen S&P 500 index proxy was compared with SPY over an overlap window:

```
1995-02 through 1999-12
months = 59
gate agreements = 58
agreement rate = 98.3051%
```

Only one month disagreed:

```
1999-05
S&P 500 gate = true
SPY gate = false
```

This supports the price-proxy bridge as a reasonable research approximation, but does not alter the NG2 decision.

## Governance

From this result onward:

- Route_A_NG2 is not promoted;
- legacy Route_A remains UNRESOLVED;
- NG2 parameters remain frozen;
- production Pressure must not include NG2;
- any structural redesign must be named NG3 or later and preregistered before another validation set is inspected.

No post-holdout retuning is authorized.
