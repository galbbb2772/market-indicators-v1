from __future__ import annotations

import argparse
import io
import json
from typing import Any

import pandas as pd
import requests

from policyshock_v211 import route_b

ORIGINAL_URLS = [
    "http://www.econ.yale.edu/~shiller/data/ie_data.xls",
    "https://www.econ.yale.edu/~shiller/data/ie_data.xls",
]
CDX = "https://web.archive.org/cdx/search/cdx"
CUTOFF = "20220103235959"
TARGET_MONTH = "202111"

POLICY_SHOCK_2022_01_03 = 74.3886192578
SIZE_WEAKNESS_OFFICIAL_2022_ARCHIVE = 85.43859649122807
ROUTE_B_THRESHOLD = 85.0


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "market-top-shiller-wayback-audit/1.0"})
    return s


def find_snapshots() -> tuple[list[dict[str, str]], list[str]]:
    s = session()
    candidates: list[dict[str, str]] = []
    errors: list[str] = []

    for original in ORIGINAL_URLS:
        try:
            r = s.get(
                CDX,
                params={
                    "url": original,
                    "from": "2019",
                    "to": "20220103",
                    "output": "json",
                    "fl": "timestamp,original,statuscode,mimetype,digest",
                    "filter": "statuscode:200",
                    "collapse": "digest",
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if not data or len(data) < 2:
                continue
            hdr = data[0]
            for row in data[1:]:
                x = dict(zip(hdr, row))
                ts = str(x.get("timestamp") or "")
                if ts and ts <= CUTOFF:
                    candidates.append(x)
        except Exception as exc:
            errors.append(f"{original}: {exc!r}")

    dedup: dict[tuple[str, str], dict[str, str]] = {}
    for x in candidates:
        key = (str(x.get("timestamp")), str(x.get("digest")))
        dedup[key] = x

    return (
        sorted(dedup.values(), key=lambda x: x["timestamp"], reverse=True),
        errors,
    )


def _date_to_ym(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y%m")

    try:
        x = float(value)
        year = int(x)
        month = int(round((x - year) * 100))
        if 1871 <= year <= 2100 and 1 <= month <= 12:
            return f"{year:04d}{month:02d}"
    except Exception:
        pass

    text = str(value).strip()
    for fmt in ("%Y.%m", "%Y-%m", "%Y/%m"):
        try:
            return pd.to_datetime(text, format=fmt).strftime("%Y%m")
        except Exception:
            continue
    return None


def parse_shiller_xls(content: bytes) -> list[dict[str, float | str]]:
    bio = io.BytesIO(content)

    # The historical workbook has long used sheet "Data" with the column
    # header beginning after seven metadata rows. Keep a fallback scan so a
    # harmless header-row shift does not masquerade as a missing vintage.
    last_error: Exception | None = None
    for skiprows in range(6, 11):
        try:
            df = pd.read_excel(
                bio,
                sheet_name="Data",
                skiprows=skiprows,
                engine="xlrd",
            )
            bio.seek(0)
            normalized = {
                str(col).strip().lower(): col
                for col in df.columns
            }
            cape_col = normalized.get("cape")

            # Historical ie_data.xls workbooks can have merged/multi-row
            # headers where CAPE does not survive as the literal column name.
            # In the canonical Shiller workbook CAPE is Excel column M,
            # i.e. zero-based dataframe column 12. Never use a generic
            # substring match because "Excess CAPE Yield" is a different
            # series and is roughly 1/CAPE in scale.
            if cape_col is None and len(df.columns) > 12:
                candidate = df.columns[12]
                if "yield" not in str(candidate).strip().lower():
                    cape_col = candidate
                else:
                    # Even when the header text is shifted, column M remains
                    # the canonical workbook location.
                    cape_col = df.columns[12]

            if cape_col is None:
                raise ValueError(f"CAPE column not found: {list(df.columns)}")

            date_col = df.columns[0]
            rows: list[dict[str, float | str]] = []
            for _, row in df.iterrows():
                ym = _date_to_ym(row[date_col])
                cape = pd.to_numeric(row[cape_col], errors="coerce")
                if ym is None or pd.isna(cape):
                    continue
                rows.append({"ym": ym, "cape": float(cape)})

            if len(rows) < 1000:
                raise ValueError(
                    f"parsed Shiller CAPE history too short: {len(rows)}"
                )

            tail = [float(x["cape"]) for x in rows[-24:]]
            finite_tail = [x for x in tail if pd.notna(x)]
            if not finite_tail:
                raise ValueError("parsed CAPE tail is empty")
            median_tail = float(pd.Series(finite_tail).median())
            if not (5.0 <= median_tail <= 100.0):
                raise ValueError(
                    "parsed CAPE scale is implausible; likely wrong workbook "
                    f"column (tail median={median_tail})"
                )

            return rows
        except Exception as exc:
            last_error = exc
            bio.seek(0)

    raise ValueError(f"unable to parse Shiller workbook: {last_error!r}")


def expanding_percentile_current(values: list[float]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    current = float(values[-1])
    return 100.0 * sum(float(x) <= current for x in values) / len(values)


def audit_workbook(content: bytes) -> dict[str, Any]:
    rows = parse_shiller_xls(content)
    target_i = next(
        (i for i, x in enumerate(rows) if str(x["ym"]) == TARGET_MONTH),
        None,
    )
    if target_i is None:
        values = [float(x["cape"]) for x in rows]
        valuation = expanding_percentile_current(values)
        rb = route_b(
            valuation,
            POLICY_SHOCK_2022_01_03,
            SIZE_WEAKNESS_OFFICIAL_2022_ARCHIVE,
        )
        if rb is None:
            raise ValueError("Route_B missing")
        critical_valuation = (
            ROUTE_B_THRESHOLD**3
            / (
                POLICY_SHOCK_2022_01_03
                * SIZE_WEAKNESS_OFFICIAL_2022_ARCHIVE
            )
        )
        return {
            "has_target": False,
            "last_month": str(rows[-1]["ym"]) if rows else None,
            "last_cape": float(rows[-1]["cape"]),
            "last_valuation": float(valuation),
            "route_b_using_last_available_valuation": float(rb),
            "critical_valuation": float(critical_valuation),
            "last_valuation_margin_above_critical": float(
                valuation - critical_valuation
            ),
        }

    truncated = rows[: target_i + 1]
    values = [float(x["cape"]) for x in truncated]
    valuation = expanding_percentile_current(values)
    rb = route_b(
        valuation,
        POLICY_SHOCK_2022_01_03,
        SIZE_WEAKNESS_OFFICIAL_2022_ARCHIVE,
    )
    if rb is None:
        raise ValueError("Route_B missing")

    critical_valuation = (
        ROUTE_B_THRESHOLD**3
        / (
            POLICY_SHOCK_2022_01_03
            * SIZE_WEAKNESS_OFFICIAL_2022_ARCHIVE
        )
    )

    return {
        "has_target": True,
        "last_month": str(rows[-1]["ym"]),
        "target_month": TARGET_MONTH,
        "target_cape": float(truncated[-1]["cape"]),
        "monthly_cape_rows_through_target": len(truncated),
        "valuation": float(valuation),
        "policy_shock": POLICY_SHOCK_2022_01_03,
        "size_weakness": SIZE_WEAKNESS_OFFICIAL_2022_ARCHIVE,
        "route_b": float(rb),
        "threshold": ROUTE_B_THRESHOLD,
        "passes": bool(rb >= ROUTE_B_THRESHOLD),
        "critical_valuation": float(critical_valuation),
        "valuation_margin_above_critical": float(
            valuation - critical_valuation
        ),
        "route_margin_above_threshold": float(rb - ROUTE_B_THRESHOLD),
    }


def download_snapshot(snapshot: dict[str, str]) -> tuple[bytes, dict[str, Any]]:
    s = session()
    ts = snapshot["timestamp"]
    original = snapshot["original"]
    raw_url = f"https://web.archive.org/web/{ts}id_/{original}"
    r = s.get(raw_url, timeout=90)
    r.raise_for_status()
    content = r.content
    if len(content) < 50_000:
        raise ValueError(
            f"archived Shiller workbook unexpectedly small: {len(content)}"
        )
    parsed = audit_workbook(content)

    last_month = parsed.get("last_month")
    capture_month = str(ts)[:6]
    if last_month and str(last_month) > capture_month:
        raise ValueError(
            "Wayback temporal inconsistency: workbook last month "
            f"{last_month} is later than capture month {capture_month}"
        )

    return content, parsed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    snaps, errors = find_snapshots()
    attempts: list[dict[str, Any]] = []
    recovered: dict[str, Any] | None = None

    for snap in snaps:
        try:
            _, parsed = download_snapshot(snap)
            row = {
                "timestamp": snap["timestamp"],
                "original": snap["original"],
                "mimetype": snap.get("mimetype"),
                "digest": snap.get("digest"),
                **parsed,
            }
            attempts.append(row)

            # The Shiller workbook is cumulative monthly history. Once the
            # newest usable pre-cutoff workbook is parsed, an older workbook
            # cannot contain a later monthly row that this one lacks.
            if parsed.get("has_target"):
                recovered = row
            break
        except Exception as exc:
            attempts.append(
                {
                    "timestamp": snap.get("timestamp"),
                    "original": snap.get("original"),
                    "error": repr(exc),
                }
            )

    if recovered is not None:
        result: dict[str, Any] = {
            "schema_version": "route-b-2022-shiller-wayback-audit-1",
            "status": "RECOVERED_PRE_CUTOFF_SHILLER_WITH_202111",
            "cutoff": CUTOFF,
            "exact_or_pre_cutoff_vintage": True,
            "wayback_timestamp": recovered["timestamp"],
            "wayback_original": recovered["original"],
            "snapshot_count": len(snaps),
            "attempts": attempts,
            "errors": errors,
            **{
                k: v
                for k, v in recovered.items()
                if k
                not in {
                    "timestamp",
                    "original",
                    "mimetype",
                    "digest",
                }
            },
            "interpretation": (
                "A Robert Shiller ie_data.xls snapshot captured no later than "
                "2022-01-03 contained the 2021-11 CAPE row. The frozen "
                "Valuation percentile and Route_B were recomputed from that "
                "pre-cutoff workbook without changing thresholds or weights."
            ),
        }
    else:
        usable = [x for x in attempts if x.get("last_month")]
        newest = max(
            usable,
            key=lambda x: str(x.get("timestamp")),
            default=None,
        )
        result = {
            "schema_version": "route-b-2022-shiller-wayback-audit-1",
            "status": "NO_PRE_CUTOFF_SHILLER_SNAPSHOT_WITH_202111",
            "cutoff": CUTOFF,
            "exact_or_pre_cutoff_vintage": False,
            "snapshot_count": len(snaps),
            "attempts": attempts,
            "errors": errors,
            "latest_usable_snapshot": newest,
            "interpretation": (
                "Wayback did not provide a usable pre-2022-01-03 Shiller "
                "workbook containing the 2021-11 CAPE row. The exact "
                "publication-time Valuation vintage therefore remains "
                "unresolved."
            ),
        }

    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
