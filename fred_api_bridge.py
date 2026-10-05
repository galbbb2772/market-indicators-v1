from __future__ import annotations

import os
from typing import Iterable

import pandas as pd
import requests

API_URL = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_START = "2015-01-01"


def fetch_fred_api(
    ids: Iterable[str],
    errors: dict[str, str] | None = None,
    api_key: str | None = None,
    observation_start: str = DEFAULT_START,
    timeout: int = 15,
) -> dict[str, pd.Series]:
    """Fetch FRED observations from the official keyed API, one series at a time.

    This is deliberately separate from update_data.py so source-provenance and
    research workflows can use a deterministic official-source path without
    changing production formulas. Missing/failed series are omitted and
    recorded in ``errors``.
    """
    err = errors if errors is not None else {}
    key = (api_key or os.getenv("FRED_API_KEY") or "").strip()
    if not key:
        err["fred_api:key"] = "FRED_API_KEY not configured"
        return {}

    out: dict[str, pd.Series] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "MarketRegimeLab-FRED-Archive/1.0"})

    for sid in ids:
        try:
            r = session.get(
                API_URL,
                params={
                    "series_id": sid,
                    "api_key": key,
                    "file_type": "json",
                    "observation_start": observation_start,
                },
                timeout=timeout,
            )
            r.raise_for_status()
            payload = r.json()
            rows = payload.get("observations") or []
            pts = {}
            for row in rows:
                value = row.get("value")
                if value in (None, ".", ""):
                    continue
                try:
                    dt = pd.Timestamp(row["date"])
                    val = float(value)
                except Exception:
                    continue
                pts[dt] = val
            if not pts:
                raise ValueError("official FRED API returned no usable observations")
            out[sid] = pd.Series(pts, dtype=float).sort_index().rename(sid)
        except Exception as exc:
            err[f"fred_api:{sid}"] = repr(exc)

    return out
