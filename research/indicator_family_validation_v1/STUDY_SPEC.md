# Market-Price Indicator Family Validation V1

Status: research-only / diagnostic-only. No production effect.

## Why
Individual-indicator validation shows many stable but weak ICs and several exact/highly redundant pairs. The correct next unit of analysis is the information family, not the single indicator.

## Frozen source rule
Use only the source-invariant market-price/derived histories from `research_indicator_validation_marketprice_v1.py`. Official-macro/FRED-dependent formulas are excluded from this study.

## Frozen family membership
Every listed indicator belongs to at most one family. Membership is fixed before results and is conceptual, not chosen by historical IC.

### volatility_risk
- largecap_panic
- retail_panic
- options_anomaly
- tech100_volatility
- vol_60d_change
- mag7_volatility
- ai7_volatility
- sector_it_vol
- sector_comm_vol
- sector_cons_disc_vol
- sector_cons_staples_vol
- sector_fin_vol
- sector_health_vol
- sector_industrial_vol
- sector_energy_vol
- sector_materials_vol
- sector_utilities_vol
- sector_realestate_vol

### valuation_structure
- valuation_cycle
- valuation_percentile
- valuation_speed
- market_overextension
- market_support
- money_making_effect
- sme_survival_growth

### participation_concentration
- retail_participation
- retail_holdings_concentration
- concentration
- breadth_concentration
- quant_crowding

### volume_activity
- market_volume
- volume_speed
- market_topic_heat
- mag7_volume
- ai7_volume

### cross_asset_event
- cross_asset_correlation
- rate_cycle_sensitivity
- gold
- oil
- geo_news_impact
- geo_lag_reaction
- global_cb_cycle_entry

### price_speed_context
- market_move_speed

`price_speed_context` is kept as a one-member control family rather than silently merging it after seeing results.

## Composite rule
For each member with `impact_polarity` +/-1, convert to supportive orientation:
`supportive = 50 + impact_polarity * (score - 50)`.
Neutral-polarity members are excluded from the family composite but retained in membership diagnostics.

The family composite is the equal-weight mean of available supportive member scores. No importance weights, no fitted weights, no member selection.

Require at least 2 simultaneously available oriented members for multi-member families. The single-member control is allowed by definition.

## Validation
For every family:
- 1D/5D/10D/20D/60D Spearman IC vs SPY forward close return;
- deterministic non-overlap phase robustness;
- 2017-2019 / 2020-2021 / 2022-present era IC;
- above/below MA200 and RV20 >=20/<20 regime IC;
- 252D rolling IC sampled every 21 sessions for 10D and 20D;
- quintile Q5-Q1 spread;
- 10D leave-one-member-out sensitivity, with no member removal decision.

## Family redundancy
Compute pairwise Spearman correlation of 5D family-composite changes and report all |rho| >= 0.70.

## Guardrails
- Historical results cannot change production weights or active/context/archive membership.
- No family is promoted based on this study alone.
- No family membership may be changed after results without creating a new study version.
- Reconstructed market-price histories are still research histories, not a perfect real-time point-in-time archive.
