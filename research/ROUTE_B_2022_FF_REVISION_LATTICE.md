# 2022 Route_B — Fama-French Official Revision Lattice

Status: **PASS ACROSS 2022–2026 OFFICIAL ARCHIVE CUTS**

This audit keeps the frozen inputs unchanged:

```
Valuation = 98.5807214666
PolicyShock = 74.3886192578
Route_B threshold = 85
target SizeWeakness month = 2021-11
```

and recomputes the SMB-derived SizeWeakness from five official Ken French historical archive cuts.

| Official cut | SizeWeakness | Route_B | Margin |
|---|---:|---:|---:|
| July 2022 | 85.4386 | 85.5692 | +0.5692 |
| July 2023 | 85.3509 | 85.5399 | +0.5399 |
| July 2024 | 85.7018 | 85.6570 | +0.6570 |
| July 2025 | 84.7368 | 85.3343 | +0.3343 |
| August 2026 | 84.7368 | 85.3343 | +0.3343 |

Therefore:

```
minimum observed Route_B = 85.334291757
minimum observed margin = +0.334291757
all five official archives pass
```

## Revision magnitude

Across the five official cuts:

```
SizeWeakness range = 0.964912 points
Route_B range = 0.322683 points
```

The underlying monthly SMB revisions for the six months used by the 2021-11 score are small:

| Month | Min SMB | Max SMB | Revision range |
|---|---:|---:|---:|
| 2021-06 | 1.60 | 1.70 | 0.10 |
| 2021-07 | -3.99 | -3.93 | 0.06 |
| 2021-08 | -0.46 | -0.32 | 0.14 |
| 2021-09 | 0.66 | 0.72 | 0.06 |
| 2021-10 | -2.37 | -2.26 | 0.11 |
| 2021-11 | -1.32 | -1.31 | 0.01 |

## Interpretation

This does not recover the exact Fama-French file visible on 2022-01-03.

It does establish that every official annual historical cut available from 2022 through 2026 keeps the frozen Route_B above 85. The observed CRSP/Fama-French historical revisions therefore do not explain the 2022 Route_B pass and, across observed official vintages, never erase it.

No threshold or weight was changed.
