"""Official Federal Reserve G.17 industrial production total index, revised history.

The G.17 `ip_sa.txt` row `B50001` is the seasonally adjusted TOTAL
industrial-production index (2017=100), the definition of FRED INDPRO.
This download is a revised current history, NOT period-as-published vintages.
"""
from __future__ import annotations
import re
import requests

G17_IP_SA_URL = 'https://www.federalreserve.gov/releases/g17/Current/ipdisk/ip_sa.txt'
ROW = re.compile(r'^\s*"B50001"\s+(\d{4})\s+(.+?)\s*$', re.MULTILINE)
HEADER = re.compile(r'^\s*"B50001:\s*Total index"\s*$', re.MULTILINE | re.IGNORECASE)


def parse_g17_indpro(raw: str) -> list[list]:
    """Read ONLY G.17 B50001, preserving true missing months and original cadence."""
    if not HEADER.search(raw):
        raise ValueError('G17 total-index B50001 header missing (wrong file?)')
    observations = {}
    for match in ROW.finditer(raw):
        year = int(match.group(1))
        tokens = match.group(2).split()
        if not (1919 <= year <= 2100 and 1 <= len(tokens) <= 12):
            raise ValueError('invalid G17 B50001 year/month row')
        for month, token in enumerate(tokens, start=1):
            # . / NA represent absent official observations. Never impute.
            if token.upper() in ('.', 'NA', 'ND', 'N/A'):
                continue
            try:
                value = float(token)
            except ValueError as exc:
                raise ValueError(f'invalid G17 industrial-production value in {year}-{month:02d}') from exc
            if not 0 < value < 10000:
                raise ValueError('implausible G17 industrial-production index value')
            key = f'{year:04d}-{month:02d}'
            if key in observations:
                raise ValueError(f'duplicate G17 B50001 observation {key}')
            observations[key] = round(value, 4)
    if not observations:
        raise ValueError('no G17 B50001 monthly industrial production observations')
    return [[key, observations[key]] for key in sorted(observations)]


def fed_g17_indpro(session: requests.Session, last_month: str | None = None) -> dict:
    """Full revised series so changed historic Fed values supersede same-source cache.

    `last_month` is intentionally unused: historical annual benchmark revisions
    require the full official series rather than a recent-only append.
    """
    response = session.get(G17_IP_SA_URL, timeout=18)
    response.raise_for_status()
    content = response.text
    if '<html' in content[:300].lower():
        raise ValueError('G17 endpoint returned HTML, not official text data')
    rows = parse_g17_indpro(content)
    return {'observations': rows, 'source': 'FED_G17_DIRECT',
            'source_url': G17_IP_SA_URL,
            'definition': 'Federal Reserve G.17 B50001 Industrial Production: TOTAL Index, seasonally adjusted, 2017=100 (same series definition as FRED INDPRO)',
            'series_code': 'B50001', 'frequency': 'monthly',
            'point_in_time': False, 'failed_years': [],
            'completeness': 'official_file_parsed; full chronological gap audit required'}
