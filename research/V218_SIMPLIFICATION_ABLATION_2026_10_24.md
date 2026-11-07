# MASTER TOP V2.1.8 component-ablation study — 2026-10-24

**Research only. Frozen V2.1.8 production remains unchanged.**

Inputs reused exactly as previously produced: corrected WIKI 2000–2018 broader historical sample, user's accepted 2019–Oct2026 stitched research replay, FINSABER 2000–2018 as robustness control, and the previously verified ^GSPC / 2Y Treasury daily macro-gate series. No stock-level source was redefined in this study.

## Decision question

Why are many historic stress periods scoring so low, and which part should be removed or softened first without turning the system into a constant bear-market alarm?

Original frozen route:
`Policy × sqrt(HL/100) × sqrt(TopProx)`, with **HL>=75**, **TopRatio>=0.95**, threshold **55**, 126-session episode lock.

## Actual ablation results

| Variant | Alert days (WIKI+2019+) | Dedup episodes | Matured episodes | Matured <=-15% MDD | Matured >-10% MDD |
|---|---:|---:|---:|---:|---:|
| Frozen original | 27 | 2 | 1 | 1 | 0 |
| Remove HL hard gate | 37 | 2 | 1 | 1 | 0 |
| Lower HL gate to 60 | 34 | 2 | 1 | 1 | 0 |
| Remove Top factor | 249 | 9 | 8 | 3 | 3 |
| **Remove Policy factor** | **51** | **6** | **5** | **4** | **0** |
| Breadth only | 1,341 | 29 | 27 | 14 | 9 |
| R6 only policy | 26 | 2 | 1 | 1 | 0 |
| R1 only policy | 30 | 3 | 2 | 2 | 0 |
| max(R1,R6) | 31 | 3 | 2 | 2 | 0 |
| mean(R1,R6) | 27 | 2 | 1 | 1 | 0 |
| 90–100% Top soft band | 60 | 3 | 2 | 1 | 1 |

The 55 threshold is held constant **only for sensitivity comparability**. A revised score distribution would need independent calibration before production.

## What blocks the historic crises?

- **2000 dot-com / early bear**: HL reached 97.47 and Policy reached 100, but the current TopProx timing blocks the frozen route once breadth deterioration becomes visible. Removing Top produces a Feb-23-2000 alert; breadth-only first flags Feb-15.
- **2007–09 GFC**: HL reaches 100 and policy reaches 78.53, yet the simultaneous Policy × Top × HL configuration never reaches 55. Removing Policy gives **2007-12-10 / 57.64**, followed by -50.37% 12m maximum drawdown.
- **2020 COVID**: HL reaches 100 but Policy is 0 during the acute window; original, no-top, and no-policy each remain zero because the other instantaneous factor also fails. Breadth alone flags Mar-10-2020.
- **2021–22**: all components overlap; original works, first route Dec-07-2021.
- **2024–25**: HL reaches 100 but Policy max is only 28.14 in the studied window; removing Policy first flags May-03-2024.

## Candidate A — first simplification to carry forward

**Keep market breadth + top location. Remove Policy from the mandatory multiplicative score. Keep Policy as confirmation metadata.**

Research formula:
`CandidateA = 100 × sqrt(HL/100) × sqrt(TopProx)`, with existing **HL>=75**, **TopRatio>=0.95** and the research comparison threshold **55**.

Candidate-A deduplicated events:
- 2007-12-10, 57.64 → next-12m MDD -50.37%
- 2014-10-03, 68.58 → -12.35%
- 2021-12-07, 84.62 → -25.43%
- 2024-05-03, 62.65 → -18.90%
- 2025-01-03, 68.88 → -18.90%
- 2026-09-18, 69.53 → outcome not matured

Among the five matured Candidate-A episodes, **4 experienced >=15% drawdown and all 5 experienced >=10% drawdown**. This is materially better historical coverage than the frozen route while avoiding the huge alert explosion of breadth-only/no-top variants.

FINSABER is a narrower robustness source: Candidate A produced only one >=55 day there, so the exact early-history result remains universe-sensitive.

## Recommendation from this pass

1. **Do not remove Top location first.** Doing so creates 249 alert days and 3 mature weak episodes (> -10% MDD), including 2005/2006.
2. **Do not use breadth alone.** It produces 1,341 alert days and 29 episodes.
3. **Changing only the HL hard gate is low-value.** It barely changes historical coverage.
4. **Changing R1/R6 combination alone is also low-value.** It adds little historical coverage.
5. **Policy is the first component worth removing from hard multiplication.** Retain it as a context/confidence label instead of making it mandatory.
6. Candidate A still misses the 2000 and 2020 cases, so the next research line should test **recent-top memory** or a separate fast-crash regime rather than deleting Top entirely.

No merge to production, no dashboard changes, no retuning of the frozen V2.1.8 score.
