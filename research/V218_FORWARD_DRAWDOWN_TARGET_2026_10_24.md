# V2.1.8 weighted three-factor — forward 5%/10% first-passage target

**Research only; frozen production V2.1.8 remains unchanged.**

Target definition:
- From the **signal-day S&P 500 close**, not from a later peak.
- Primary: first close **-5% or lower within 60 market sessions**.
- Secondary: first close **-10% or lower within 126 market sessions**.
- Also track -15% and waiting time.
- Probability denominators use only signals with the full requested forward horizon.

Primary weighted research score in this pass:
`10% Policy + 45% HL + 45% Top`.

## Empirical risk ladder

| Score threshold | Fully observed 60d signals | 5% within 60d | Median days to -5% | Fully observed 126d signals | 10% within 126d | Median days to -10% |
|---|---:|---:|---:|---:|---:|---:|
| >=55 | 149 | 67.1% | 18.5 | 149 | 54.4% | 44 |
| >=60 | 59 | **84.7%** | **21** | 59 | **72.9%** | **48** |
| >=65 | 38 | 94.7% | 24.5 | 38 | 86.8% | 49 |

At >=60, 69.5% also reached -15% within 126 market sessions; median first -15% was 86 sessions.

Unconditional scored-day historical baselines:
- Any scored day -> -5% within 60 sessions: about **35.5%**.
- Any scored day -> -10% within 126 sessions: about **26.3%**.

Thus score>=60 gives roughly **2.4x** the baseline probability of a -5% move within 60 sessions, and about **2.8x** the baseline probability of -10% within 126 sessions.

## Recommended target semantics for the next model-selection pass

- **Watch >=55**: historical early-warning state.
- **High Risk >=60**: primary success definition = at least -5% from signal close within 60 market sessions.
- **Extreme >=65**: higher conditional hit-rate, but current historical observations are much fewer and concentrated; do not declare this the sole production threshold yet.
- Secondary severity target for any High Risk alert: -10% within 126 sessions.

Daily observations are serially clustered. 126-session de-duplicated episode counts are much smaller, so both daily hit-rate and episode hit-rate must be retained in validation. Do not interpret 84.7% as 59 independent historical events.

## Historical split caution

The >=60 result is substantially stronger in 2019–2026 than the early WIKI period, so threshold/weight selection still needs an out-of-time split or walk-forward calibration. >=65 has too few early-history observations to be treated as robust despite very high pooled hit rates.

Deliverable generated in the conversation:
`V218_前瞻5pct_10pct回撤目标研究_2026-10-24.zip`.
