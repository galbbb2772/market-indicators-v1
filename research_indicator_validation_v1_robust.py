from __future__ import annotations

import json
from pathlib import Path

import research_indicator_validation_v1 as study

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "update_data.py"
CURRENT = ROOT / "docs" / "data" / "current.json"
OUT = ROOT / "docs" / "data" / "indicator_validation_v1.json"


def run_update_and_capture_robust():
    source = SRC.read_text(encoding="utf-8")

    # Research-only hardening: the production builder normally gives FRED only
    # 8 seconds. During full-history validation a transient timeout can silently
    # switch several factors to market-price fallbacks, which makes cross-factor
    # comparisons non-comparable. Keep formulas unchanged but allow three longer
    # attempts for each FRED chunk.
    old = '    r = HTTP.get(url, timeout=8)\n    r.raise_for_status()\n'
    new = (
        '    _fred_last = None\n'
        '    for _fred_attempt in range(3):\n'
        '        try:\n'
        '            r = HTTP.get(url, timeout=30)\n'
        '            r.raise_for_status()\n'
        '            break\n'
        '        except Exception as _fred_exc:\n'
        '            _fred_last = _fred_exc\n'
        '            if _fred_attempt == 2:\n'
        '                raise\n'
        '            time.sleep(2 ** _fred_attempt)\n'
    )
    if old not in source:
        raise RuntimeError("Could not harden fred_chunk timeout")
    source = source.replace(old, new, 1)

    needle = '    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")\n'
    injected = (
        '    global _ABLATION_CAPTURE\n'
        '    _ABLATION_CAPTURE={"series_store":series_store,"mk":mk,"ordered":ordered}\n'
        + needle
    )
    if needle not in source:
        raise RuntimeError("Could not instrument update_data.py")
    source = source.replace(needle, injected, 1)
    ns = {"__name__": "__main__", "__file__": str(SRC)}
    exec(compile(source, str(SRC), "exec"), ns, ns)
    return ns, ns.get("_ABLATION_CAPTURE")


def main():
    study.abl.run_update_and_capture = run_update_and_capture_robust
    study.main()

    source_payload = json.loads(CURRENT.read_text(encoding="utf-8"))
    out = json.loads(OUT.read_text(encoding="utf-8"))
    errors = source_payload.get("errors") or {}
    fred_errors = {k: v for k, v in errors.items() if str(k).startswith("fred:")}
    out["source_run"] = {
        "status": source_payload.get("status"),
        "working_count": source_payload.get("working_count"),
        "total_count": source_payload.get("total_count"),
        "generated_at": source_payload.get("generated_at"),
        "fred_error_count": len(fred_errors),
        "fred_errors": fred_errors,
        "all_errors": errors,
        "direct_fred_complete": len(fred_errors) == 0,
        "note": "Research capture uses unchanged formulas with longer/retried FRED HTTP reads to avoid accidental fallback selection from transient 8-second timeouts.",
    }
    if fred_errors:
        out["warnings"].append(
            "This run still had FRED retrieval errors; affected factors may use configured market-price fallbacks and should not be treated as final cross-factor evidence."
        )
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "eligible": out["coverage"]["eligible_indicator_count"],
        "source_working": out["source_run"]["working_count"],
        "fred_error_count": out["source_run"]["fred_error_count"],
        "direct_fred_complete": out["source_run"]["direct_fred_complete"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
