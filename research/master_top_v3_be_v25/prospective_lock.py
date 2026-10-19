"""Fail-closed prospective signal ledger for MASTER TOP V3 Bubble Exhaustion.

Usage: python prospective_lock.py candidate.json ledger_directory
Validation checks availability/provenance, NOT that the model is scientifically valid.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys


def timestamp(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('Timestamp must be explicit UTC with Z suffix')
    try:
        x = dt.datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as e:
        raise ValueError('Invalid timestamp') from e
    return x


def previous_month(month):
    try:
        year, mo = map(int, month.split('-'))
        assert len(month) == 7 and 1 <= mo <= 12
    except (ValueError, AssertionError) as e:
        raise ValueError('Month must be YYYY-MM') from e
    return f'{year-1:04d}-12' if mo == 1 else f'{year:04d}-{mo-1:02d}'


def validate(record):
    assert record['schema_version'] == 'BE_V25_PROSPECTIVE_1'
    month = record['signal_month']
    prior = previous_month(month)
    run_at = timestamp(record['locked_at'])
    end = dt.datetime(int(month[:4]), int(month[5:7]), 1, tzinfo=dt.timezone.utc)
    if run_at < (dt.datetime(int(month[:4])+1, 1, 1, tzinfo=dt.timezone.utc)
                 if month.endswith('-12') else
                 dt.datetime(int(month[:4]), int(month[5:7])+1, 1, tzinfo=dt.timezone.utc)):
        raise ValueError('Month is not complete; no production-like monthly signal')
    if record.get('data_status') != 'COMPLETE_MONTH':
        raise ValueError('Only completed-month records can be locked')
    if record.get('is_true_oos_validated', False):
        raise ValueError('Validation status cannot be self-certified by a signal record')
    if not re.fullmatch(r'[a-f0-9]{64}', record['code_sha256']):
        raise ValueError('Code hash is missing or malformed')
    for name in ('margin', 'cape', 'spy'):
        src = record['sources'][name]
        ref = src['reference_month']
        if ref > (month if name == 'spy' else prior):
            raise ValueError(name + ' references future data')
        if name == 'spy' and ref != month:
            raise ValueError('SPY source must correspond to signal month')
        pub = timestamp(src['published_at'])
        captured = timestamp(src['captured_at'])
        if pub > run_at or captured > run_at:
            raise ValueError('Input was not available at lock time')
        if not src.get('source_url', '').startswith('https://'):
            raise ValueError('Source URL must be explicit and HTTPS')
        local = pathlib.Path(src['snapshot_path'])
        if not local.is_file():
            raise ValueError(name + ' raw bytes not locally snapshotted')
        sha = hashlib.sha256(local.read_bytes()).hexdigest()
        if sha != src['sha256']:
            raise ValueError(name + ' source hash mismatch')
    return True


def lock(record, directory):
    validate(record)
    root = pathlib.Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    name = f"{record['signal_month']}.json"
    destination = root / name
    # Exclusive create: cannot rewrite prior signals after seeing subsequent outcomes.
    with destination.open('x', encoding='utf-8') as file:
        json.dump(record, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write('\n')
    return destination


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[1], encoding='utf-8') as file:
        candidate = json.load(file)
    print(lock(candidate, sys.argv[2]))
