# Market Top NG1 A/C — First Screening

Status:

```
Route_C_NG1 = REJECT
Route_A_NG1 = ACCEPT_SCREENING_CANDIDATE
```

Research only. No legacy V2.4 formula is replaced.

The screening was run once after the NG1 formula, lags, threshold, positive windows and negative controls were preregistered.

No parameter was changed after seeing the result.

## Source set

- Fama-French 25 Size x Book-to-Market portfolios: current historical mirror of the 202605 CRSP cut;
- Fama-French 12 Industry portfolios: same cut;
- Fama-French market / SMB: same cut;
- BAA and GS10: FRED historical mirrors;
- Shiller CAPE: canonical Shiller feed;
- SPY: daily unadjusted close.

Screening sample:

```
1993-01 through 2022-12
360 monthly states
```

PIT lags remained exactly as preregistered:

```
Fama-French monthly inputs +2 calendar months
Shiller CAPE +1 calendar month
BAA-GS10 spread +1 calendar month
```

## Route_C_NG1

It detects both intended concentration regimes.

### 2000 positive window

```
2000-03 Route_C_NG1 = 92.36 -> ARMED
```

### 2022 positive window

```
2021-10 = 95.59 -> ARMED
2021-11 = 89.45 -> ARMED
2021-12 = 93.71 -> ARMED
```

But it fails a preregistered negative control:

```
1998-06 Route_C_NG1 = 93.05 -> ARMED
```

and it produces many additional historical ARMED episodes, including 1995, 1996, 1997, 1998-99, 2017 and 2020.

Therefore:

```
Route_C_NG1 = REJECT
```

No weight/threshold/window retuning is allowed inside NG1.

## Route_A_NG1

Primary target:

```
2007-11 Route_A_NG1 = 86.72 -> ARMED
```

The preregistered negative windows are clean:

```
2000-01 through 2000-04 = no ARMED
2011-03 through 2011-07 = no ARMED
2018-08 through 2018-12 = no ARMED
```

Full-sample ARMED episodes:

```
1998-11 through 1999-03
2007-11
2012-02
```

Outside the 2007 positive episode there are exactly:

```
2 additional episodes
```

which is equal to, but does not exceed, the preregistered maximum of 2.

Therefore:

```
Route_A_NG1 = ACCEPT_SCREENING_CANDIDATE
```

This is deliberately a weak promotion.

It means only that the candidate survived the preregistered first historical screen.

It does **not** mean:

- production-ready;
- recovered legacy Route_A;
- validated with exact historical source vintages;
- validated prospectively.

## Next gate for Route_A_NG1

Before promotion beyond screening candidate:

1. reproduce the 2007 result from independently fetched official/raw sources rather than the current mirror set;
2. inspect the two additional episodes as explicit case studies rather than hiding them;
3. lock a forward implementation and accumulate prospective observations;
4. do not change NG1 parameters if the independent replay is unfavorable.
