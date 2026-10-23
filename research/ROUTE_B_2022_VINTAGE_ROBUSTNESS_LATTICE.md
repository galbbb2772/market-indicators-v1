# 2022 Route_B — Vintage Robustness Lattice

Status: **PASS ACROSS OBSERVED VINTAGE COMBINATIONS**

The 2022 Route_B result has now been tested across current-vintage, official 2022-era, and genuine pre-cutoff archived inputs.

| Scenario | Valuation | SizeWeakness | Route_B | Margin |
|---|---:|---:|---:|---:|
| Current conservative reconstruction | 98.5807 | 84.7368 | 85.3343 | +0.3343 |
| Official FF July-2022 cut | 98.5807 | 85.4386 | 85.5692 | +0.5692 |
| Archived Sep-2021 Shiller + official FF | 98.5790 | 85.4386 | 85.5687 | +0.5687 |
| Archived Sep-2021 Shiller + lower current SizeWeakness | 98.5790 | 84.7368 | 85.3338 | +0.3338 |

All use the unchanged:

```
PolicyShock = 74.3886192578
Route_B threshold = 85
```

## Failure boundaries

With the observed inputs, the frozen 85 threshold would fail only below approximately:

```
SizeWeakness = 83.7449
```

at the current conservative Valuation/Policy pair.

Using official 2022-era SizeWeakness:

```
critical Valuation = 96.6265
```

Using the lower current-vintage SizeWeakness:

```
critical Valuation = 97.4267
```

Using the real archived September-2021 Valuation plus the lower current SizeWeakness:

```
critical PolicyShock = 73.5191
actual PolicyShock = 74.3886
margin = +0.8696
```

## Evidence limits

This does **not** prove every exact input byte available on 2022-01-03.

Remaining exact-vintage gaps:

- Ken French monthly file containing 2021-11 was not captured by Wayback before the cutoff;
- Shiller workbook containing 2021-11 was not captured by Wayback before the cutoff.

What is established:

- official Ken French 2022-era archive preserves the pass;
- a genuine Shiller pre-cutoff workbook already yields a sufficiently high Valuation;
- the lower current-vintage SizeWeakness also preserves the pass when paired with that archived Valuation;
- observed historical revisions therefore do not explain or create the Route_B > 85 result.

No parameter tuning is authorized by this robustness study.


## Official Fama-French revision lattice, 2022–2026

The SMB-derived SizeWeakness was recomputed from every currently available official annual Fama-French 3-factor archive cut covering the 2021-11 target month:

| Cut | SizeWeakness | Route_B | Margin |
|---|---:|---:|---:|
| July 2022 | 85.4386 | 85.5692 | +0.5692 |
| July 2023 | 85.3509 | 85.5399 | +0.5399 |
| July 2024 | 85.7018 | 85.6570 | +0.6570 |
| July 2025 | 84.7368 | 85.3343 | +0.3343 |
| August 2026 | 84.7368 | 85.3343 | +0.3343 |

Across all five official revisions:

```
SizeWeakness range = 0.964912 points
Route_B range = 0.322683 points
minimum Route_B = 85.334292
minimum margin = +0.334292
```

Thus every observed official CRSP/Fama-French revision preserves the frozen 85 threshold pass.
