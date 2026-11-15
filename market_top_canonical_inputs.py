from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Iterable, Sequence


@dataclass(frozen=True)
class CanonicalRouteBInputs:
    valuation: float
    size_weakness: float


def expanding_percentile_current(values: Sequence[float]) -> float:
    """Current-inclusive empirical percentile, matching the frozen Top Trigger rule."""
    xs = [float(x) for x in values]
    if not xs:
        raise ValueError("values must not be empty")
    current = xs[-1]
    return 100.0 * sum(x <= current for x in xs) / len(xs)


def compounded_return_pct(returns_pct: Sequence[float]) -> float:
    """Compound simple percentage returns."""
    xs = [float(x) for x in returns_pct]
    if not xs:
        raise ValueError("returns_pct must not be empty")
    return (prod(1.0 + x / 100.0 for x in xs) - 1.0) * 100.0


def size_block_from_smb_6m(smb_6m_pct: Sequence[float]) -> float:
    """B_size = -CumSMB_6m."""
    if len(smb_6m_pct) != 6:
        raise ValueError("exactly six monthly SMB returns are required")
    return -compounded_return_pct(smb_6m_pct)


def size_weakness_history(smb_monthly_pct: Sequence[float]) -> list[float | None]:
    """Expanding-percentile SizeWeakness from monthly Fama-French SMB.

    For each month t with at least six observations:
      B_size_t = -CumSMB_{t-5:t}
      SizeWeakness_t = ECDF_t(B_size_t)

    Percentiles are current-inclusive and use only B_size observations available
    through t.
    """
    xs = [float(x) for x in smb_monthly_pct]
    out: list[float | None] = [None] * len(xs)
    blocks: list[float] = []
    for i in range(5, len(xs)):
        b = size_block_from_smb_6m(xs[i - 5:i + 1])
        blocks.append(b)
        out[i] = expanding_percentile_current(blocks)
    return out


def valuation_history(cape_monthly: Sequence[float]) -> list[float]:
    """Canonical Valuation = expanding percentile of Shiller CAPE."""
    xs = [float(x) for x in cape_monthly]
    out: list[float] = []
    for i in range(len(xs)):
        out.append(expanding_percentile_current(xs[: i + 1]))
    return out
