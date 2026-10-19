from __future__ import annotations

import argparse
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from pypdf import PdfReader

try:
    from research.build_market_top_ng3_first_release_panel_1986_1988 import (
        PANEL_MONTHS,
        SOURCE_MONTHS,
        parse_schedule,
        pdf_url,
    )
except ModuleNotFoundError:
    from build_market_top_ng3_first_release_panel_1986_1988 import (
        PANEL_MONTHS,
        SOURCE_MONTHS,
        parse_schedule,
        pdf_url,
    )


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _one_number(text: str) -> float | None:
    t = _norm(text).replace(",", "")
    if not re.fullmatch(r"[+-]?(?:\d+\.\d+|\.\d+|\d+)", t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _numbers_in_text(text: str) -> list[float]:
    t = _norm(text).replace(",", "")
    out = []
    for tok in re.findall(r"[+-]?(?:[0-9]+[.][0-9]+|[.][0-9]+|[0-9]+)", t):
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out

