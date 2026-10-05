from __future__ import annotations

import pandas as pd

import research_indicator_family_validation_v1 as fam


def build_family_fixed(series_store, meta_map, members, index, allow_single=False):
    idx = pd.DatetimeIndex(index)
    parts = {}
    for k in members:
        s = fam.oriented_series(series_store, meta_map, k, idx)
        if s is not None:
            ss = pd.Series(s).copy()
            ss.index = pd.to_datetime(ss.index)
            parts[k] = ss.reindex(idx)
    if not parts:
        return pd.Series(dtype=float, index=idx), parts
    df = pd.DataFrame({k: v.to_numpy() for k, v in parts.items()}, index=idx)
    min_count = 1 if allow_single else 2
    comp = df.mean(axis=1, skipna=True).where(df.notna().sum(axis=1) >= min_count).dropna()
    comp.index = pd.DatetimeIndex(comp.index)
    return comp, parts


def main():
    fam.build_family = build_family_fixed
    fam.main()


if __name__ == "__main__":
    main()
