# MASTER TOP V2.1.8 — three-factor weighted-sum research (2026-10-24)

**Research only. Frozen V2.1.8 production/main/dashboard are unchanged.**

The user's simplification is implemented exactly: retain all three 0–100 factors and replace the mandatory multiplication with a weighted sum.

`Score = w_policy * Policy + w_HL * HL + w_top * TopProx100`, with weights summing to 1.

TopProx100 keeps the existing 5% band: `100 * clip((TopRatio - .95)/.05,0,1)`.

The legacy threshold 55 is retained **only as a sensitivity reference**. A weighted score has a different distribution; 55 is not claimed calibrated for production.

## Actual fixed-weight results

| weights (Policy / HL / Top) | alert days | dedup episodes | matured | matured <=-10% | matured <=-15% | matured weak >-10% | early-window coverage |
|---|---:|---:|---:|---:|---:|---:|---|
| 30 / 50 / 20 (user-initial) | 349 | 13 | 11 | 8 | 5 | 3 | 2000 + 2021–22 + 2024/25; misses GFC/COVID |
| 20 / 50 / 30 | 329 | 14 | 12 | 9 | 6 | 3 | adds GFC; misses COVID |
| **10 / 45 / 45** | **170** | **13** | **11** | **9** | **7** | **2** | 2000 + GFC + 2021–22 + 2024/25; misses COVID |
| **25 / 55 / 20** | **587** | **19** | **17** | **14** | **10** | **3** | covers 2000 + GFC + COVID + 2021–22 + 2024/25 |
| ~33 / 33 / 33 | 349 | 13 | 12 | 8 | 5 | 4 | 2000 + GFC + 2021–22; misses COVID |

FINSABER early-history robustness alert-days at the same threshold: 46, 22, 5, 179, and 93 respectively. This confirms early-history results remain universe-sensitive.

## Two research candidates to keep

### Candidate W — top-warning
**Policy 10% / HL 45% / Top 45%.**
- 170 threshold days, 13 126-session episodes.
- 11 episodes have mature 12m outcomes: 9 later reached >=10% max drawdown; 7 reached >=15%; 2 were weaker than 10%.
- First studied alerts: dot-com 2000-03-16; GFC 2007-12-10; 2021–22 2021-12-06; 2024/25 2024-05-03.
- No COVID alert at threshold55 because the top position collapses too rapidly while policy is weak.
- This is the cleaner version if the system's identity remains **market-top warning**.

### Candidate C — crisis coverage
**Policy 25% / HL 55% / Top 20%.**
- 587 threshold days, but the 126-session lock compresses these to 19 episodes.
- 17 mature episodes: 14 later reached >=10% drawdown, 10 reached >=15%, 3 were weaker than 10%.
- First studied alerts: dot-com 2000-02-15; GFC 2007-12-06; COVID 2020-03-20; 2021–22 2021-12-06; 2024/25 2024-05-06.
- COVID is a **crash confirmation**, not a pre-top prediction: the first threshold crossing is after the rapid decline had started.

## Light HL guard

A separate HL>=40 guard was run over the 5%-step weight grid. For the useful high-HL combinations it makes essentially no difference, so it is not justified as an additional rule at this stage.

## Main finding

The user's weighted-sum idea solves the original structural defect: one low factor no longer multiplies the whole score to zero.

However, **weights and threshold are now one calibration problem**. Keeping the old 55 threshold mechanically causes much more time above threshold than the frozen multiplicative score. The next legitimate step is threshold calibration/OOS validation, not adding more factors.

At the same 55 threshold:
- More Top weight → cleaner/earlier top-warning identity, but COVID remains intentionally missed.
- More HL weight (~55%+) → broader crisis coverage including COVID, but materially more alert-days.
- Policy can stay in the model at a smaller weight; it no longer needs to be a hard blocker.

Research implementation: `research/v218_weighted_sum_grid.py`.
Deterministic semantics: `tests/test_v218_weighted_sum_grid.py`.
