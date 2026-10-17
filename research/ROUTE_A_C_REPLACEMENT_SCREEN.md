# Route_A / Route_C Replacement Screen

Status: **ALL TESTED REPLACEMENTS REJECTED**

This study does not alter original V2.4. It records failed replacement hypotheses so they are not rediscovered and silently promoted later.

## Route_A

### A1 — credit level

```
Credit =
  0.5 * expanding_pct(BAA - GS10)
+ 0.5 * expanding_pct(SLOOS, lagged one quarter)

Route_A = sqrt(Credit * Breadth)
```

2007 fingerprints:

| Signal month | Route_A |
|---|---:|
| 2007-08 | 60.44 |
| 2007-12 | 78.71 |
| 2008-01 | 83.06 |
| 2008-02 | 85.56 |

**Decision: REJECTED.**

It does not reach the 85 route threshold until February 2008, too late to represent the accepted 2007 top-path mechanism.

### A2 — credit deterioration speed

```
SpreadShockRaw = max(delta3M(BAA-GS10), delta6M(BAA-GS10))
SpreadShockScore = expanding_pct(SpreadShockRaw)

CreditBreakdown =
  0.5 * SpreadShockScore
+ 0.5 * expanding_pct(SLOOS, lagged one quarter)

Route_A = sqrt(CreditBreakdown * Breadth)
```

2007:

| Signal month | Route_A |
|---|---:|
| 2007-08 | 64.65 |
| 2007-12 | 81.15 |
| 2008-01 | 84.48 |
| 2008-02 | 85.86 |

**Decision: REJECTED.**

Changing from credit level to credit speed helps but does not solve the timing problem. No threshold or weighting retune is authorized.

## Route_C

### C1 — absolute-positive sector participation

Uses the share of the 12 industries with positive six-month absolute returns.

Full 1993–2022 screen:

- Route_C >= 85: 41 months
- Early Breadth: 9 months
- C-route ARMED months: 17

It produced false/unaccepted episodes including 1998, 2004, 2005 and later-bear-market signals.

**Decision: REJECTED.**

### C2 — market-relative participation, arithmetic combination

This corrects an important interpretation clue:

```
RelativeParticipationRaw =
  1 - count(Industry6M > Market6M) / 12
```

but combines it with leader-gap using an arithmetic mean.

Full 1993–2022 screen:

- Route_C >= 85: 70 months
- Early Breadth: 16 months
- C-route ARMED months: 52

False Early Breadth episodes include:

- 1995-03
- 1997-03
- 1998-02 / 1998-08
- 1999-01 through 1999-03
- 2005-04 / 2005-08
- 2011-03 through 2011-05
- 2020-03
- 2021-08 through 2021-09

It also fails to reproduce the accepted 2021-10 Early Breadth event.

**Decision: REJECTED.**

### C3 — market-relative participation, geometric combination

C3 was preregistered before validation:

```
ConcentrationBreadth_C3 =
  sqrt(RelativeParticipationScore * LeaderGapScore)

Route_C_C3 =
  sqrt(Valuation * ConcentrationBreadth_C3)
```

The motivation was to require both narrow participation and extreme leader gap simultaneously rather than permit arithmetic compensation.

Full 1993–2022 screen:

- Route_C >= 85: 68 months
- Early Breadth: 16 months
- C-route ARMED months: 51

The false Early Breadth episode set is still materially the same as C2. Most importantly:

```
effective 2021-10 Route_C_C3 ~= 73.19
```

so it still does not recreate the accepted 2021-10 Early Breadth event.

It does strongly identify the 2000 concentration regime:

- effective 2000-01: 99.16
- effective 2000-03: 99.47
- effective 2000-04: 99.73

but that is not enough.

**Decision: REJECTED.**

## Research conclusion

The common recovered motifs—BAA/SLOOS credit stress, SMB weakness, 12-industry participation, and leader-gap concentration—are useful clues but are not sufficient to reproduce the final accepted V2.4 routes.

Therefore:

```
original Route_A = UNRESOLVED
original Route_C = UNRESOLVED
```

and all A1/A2/C1/C2/C3 replacements remain quarantined.

The next valid recovery target is the actual Breadth / Route_C definition that produced the accepted **2021-10 Early Breadth** event. We should recover that artifact or definition rather than tune these rejected candidates.
