from __future__ import annotations

import io
import runpy
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pandas as pd
import requests

_ORIGINAL_GET = requests.sessions.Session.get


def _single_fred(self, url: str, sid: str, **kwargs) -> pd.DataFrame:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["id"] = [sid]
    single_url = urlunparse(parsed._replace(query=urlencode({k: v[-1] for k, v in query.items()})))
    last = None
    for attempt in range(3):
        try:
            local_kwargs = dict(kwargs)
            local_kwargs["timeout"] = (5, 25)
            r = _ORIGINAL_GET(self, single_url, **local_kwargs)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            if len(df.columns) < 2:
                raise ValueError(f"FRED {sid}: unexpected response")
            date_col = df.columns[0]
            value_col = sid if sid in df.columns else df.columns[1]
            out = df[[date_col, value_col]].copy()
            out.columns = ["DATE", sid]
            return out
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last or RuntimeError(f"FRED {sid}: request failed")


def resilient_get(self, url, **kwargs):
    if not isinstance(url, str) or "fred.stlouisfed.org/graph/fredgraph.csv" not in url:
        return _ORIGINAL_GET(self, url, **kwargs)

    parsed = urlparse(url)
    ids = (parse_qs(parsed.query).get("id") or [""])[-1]
    series_ids = [x.strip() for x in ids.split(",") if x.strip()]

    # First try the normal request, but give FRED more time and retry once.
    last = None
    for attempt in range(2):
        try:
            local_kwargs = dict(kwargs)
            local_kwargs["timeout"] = (5, 20)
            r = _ORIGINAL_GET(self, url, **local_kwargs)
            if r.ok:
                return r
            last = RuntimeError(f"FRED HTTP {r.status_code}")
        except Exception as exc:
            last = exc
        if attempt == 0:
            time.sleep(1.0)

    # Multi-series FRED CSV sometimes times out on GitHub runners. Fall back to
    # fetching each series separately, then rebuild the exact CSV shape expected
    # by update_data.py. A single failed series is left as NA rather than causing
    # the entire four-series chunk to disappear.
    if len(series_ids) > 1:
        merged = None
        successful = 0
        for sid in series_ids:
            try:
                one = _single_fred(self, url, sid, **kwargs)
                merged = one if merged is None else merged.merge(one, on="DATE", how="outer")
                successful += 1
            except Exception:
                continue
        if merged is not None and successful:
            merged = merged.sort_values("DATE")
            response = requests.Response()
            response.status_code = 200
            response.url = url
            response.encoding = "utf-8"
            response._content = merged.to_csv(index=False).encode("utf-8")
            return response

    raise last or RuntimeError("FRED request failed")


requests.sessions.Session.get = resilient_get

# ablation_runner executes update_data.py inside this same interpreter, so the
# FRED retry/fallback above applies to the whole refresh without changing the
# strategy formulas or Market Model V2 logic.
runpy.run_path("ablation_runner.py", run_name="__main__")
