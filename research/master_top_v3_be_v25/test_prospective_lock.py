"""Run: python -m unittest -v test_prospective_lock.py"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from prospective_lock import validate, lock


class PITLockTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p = Path(self.temp.name) / 'source.csv'
        p.write_bytes(b'research-source\n')
        source = dict(reference_month='2026-09', published_at='2026-10-20T12:00:00Z',
                      captured_at='2026-11-01T02:00:00Z', source_url='https://example.org/source',
                      snapshot_path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        self.rec = dict(schema_version='BE_V25_PROSPECTIVE_1', signal_month='2026-10',
                        locked_at='2026-11-01T03:00:00Z', data_status='COMPLETE_MONTH',
                        is_true_oos_validated=False, code_sha256='a'*64,
                        sources={'cape':dict(source), 'margin':dict(source),
                                 'spy':dict(source, reference_month='2026-10')})

    def test_valid(self):
        self.assertTrue(validate(self.rec))

    def test_incomplete_month(self):
        self.rec['locked_at']='2026-10-30T23:00:00Z'
        with self.assertRaises(ValueError): validate(self.rec)

    def test_future_margin_reference(self):
        self.rec['sources']['margin']['reference_month']='2026-11'
        with self.assertRaises(ValueError): validate(self.rec)

    def test_future_published_source(self):
        self.rec['sources']['margin']['published_at']='2026-11-02T12:00:00Z'
        with self.assertRaises(ValueError): validate(self.rec)

    def test_corrupted_source(self):
        self.rec['sources']['margin']['sha256']='b'*64
        with self.assertRaises(ValueError): validate(self.rec)

    def test_append_only_lock(self):
        ledger=Path(self.temp.name)/'ledger'
        self.assertTrue(lock(self.rec, ledger).is_file())
        with self.assertRaises(FileExistsError): lock(self.rec, ledger)

    def test_validation_claim_disallowed(self):
        self.rec['is_true_oos_validated']=True
        with self.assertRaises(ValueError): validate(self.rec)


if __name__ == '__main__': unittest.main()
