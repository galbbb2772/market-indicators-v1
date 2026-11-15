# Route_A_NG1 — Independent Source Replay

Status:

```
PASS_INDEPENDENT_SOURCE_REPLAY
SOURCE_VALIDATED_SCREENING_CANDIDATE
```

Research only. This does not recover legacy Route_A and does not authorize production use.

## Why this replay exists

The first NG1 screening used one historical mirror set.

A first attempt to validate independently through the FRED graph CSV endpoint failed because GitHub Actions repeatedly timed out. That provider failure was not treated as model evidence.

A second attempt through the Federal Reserve DDP did not return the discontinued BAA series in the expected CSV package, so it was also not treated as a pass.

The successful replay uses a different immutable credit-data snapshot while keeping the preregistered formula unchanged.

## Independent data path

Fama-French inputs:

- official Kenneth R. French 25 Portfolios 5x5 ZIP;
- official 12 Industry Portfolios ZIP;
- official F-F Research Data Factors ZIP.

Credit inputs:

- repository: `Snow-Ouyang/Market-Regime-Clustering`;
- pinned commit: `71af02cba3493ffa15ac47f512dc346598f2e23f`;
- monthly FRED BAA and GS10 snapshots;
- common history begins 1953-04.

Price gate:

- Yahoo Finance SPY unadjusted Close.

The credit snapshot is independent of the BuyRisk mirror used in the first screen.

## PIT alignment

The preregistered lags are unchanged:

```
effective month = 2007-11
Fama-French source month = 2007-09
credit-spread source month = 2007-10
```

## Credit parity

Independent snapshot:

```
BAA 2007-10 = 6.48
GS10 2007-10 = 4.53
spread = 1.95
```

Reconstructed frozen spread-shock block:

```
SpreadShockRaw = 0.30
SpreadShockScore = 75.80893683
```

These values exactly reproduce the first-screen target after using the complete common history.

## Independent component scores

```
SpreadShockScore       = 75.80893683
FinanceWeaknessScore   = 92.57731959
SizeWeaknessScore      = 87.62886598
PortfolioExhaustion    = 92.26804124
```

Therefore:

```
Route_A_NG1 = 86.79223562
threshold   = 85
margin      = +1.79223562
```

The 2007-11 top-location gate also passes.

Hence:

```
2007-11 -> ARMED
```

## Research interpretation

This materially strengthens NG1-A relative to the initial screen because the target hit survives an independent source chain.

The allowed conclusion is:

> Route_A_NG1 is a source-validated screening candidate.

The following conclusions remain prohibited:

- legacy Route_A has been recovered;
- NG1-A is production-ready;
- NG1-A has prospective validation;
- the two additional historical episodes are harmless.

The next gate is explicit analysis of the two additional screening episodes:

```
1998-11 through 1999-03
2012-02
```

No parameter change is authorized by those case studies.
