import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from official_indpro import fed_g17_indpro,parse_g17_indpro
from macro_integrity import merge_same_source,refetch_anchor


class OfficialIndustrialProductionTests(unittest.TestCase):
    SAMPLE='''"B50001: Total index"\n"B50001" 1919 4.1000 4.2000 . 4.4000\n"B50001" 1920 5.1000 5.2000\n"B50030: Final products and nonindustrial supplies"\n"B50030" 1919 777 888\n'''

    def test_exact_series_ignores_other_industrial_groups(self):
        rows=parse_g17_indpro(self.SAMPLE)
        self.assertEqual(rows,[['1919-01',4.1],['1919-02',4.2],
                               ['1919-04',4.4],['1920-01',5.1],['1920-02',5.2]])

    def test_gaps_are_not_interpolated_or_hidden(self):
        src={'source':'FED_G17_DIRECT','observations':parse_g17_indpro(self.SAMPLE),
             'failed_years':[]}
        result=merge_same_source('INDPRO',{},src,expected_first='1919-01')
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['first_missing_month'],'1919-03')
        self.assertEqual(result['missing_month_count'],9)

    def test_provider_provenance_revised_flag(self):
        reply=Mock(text=self.SAMPLE)
        out=fed_g17_indpro(Mock(get=Mock(return_value=reply)),last_month='1919-01')
        self.assertEqual(out['source'],'FED_G17_DIRECT')
        self.assertEqual(out['series_code'],'B50001')
        self.assertEqual(out['frequency'],'monthly')
        self.assertIs(out['point_in_time'],False)
        self.assertEqual(len(out['observations']),5)

    def test_html_error_is_not_silent(self):
        with self.assertRaisesRegex(ValueError,'HTML'):
            fed_g17_indpro(Mock(get=Mock(return_value=Mock(text='<html>bad gateway</html>'))))

    def test_missing_header_duplicate_and_bad_value_rejected(self):
        with self.assertRaisesRegex(ValueError,'header missing'):
            parse_g17_indpro('"B50001" 1919 5 6 7')
        with self.assertRaisesRegex(ValueError,'duplicate'):
            parse_g17_indpro(self.SAMPLE+'\n"B50001" 1919 1\n')
        with self.assertRaisesRegex(ValueError,'invalid G17'):
            parse_g17_indpro('"B50001: Total index"\n"B50001" 1919 5.0 NOPE 6.0')

    def test_incompatible_fred_cache_not_mixed(self):
        previous={'source':'FRED_OPTIONAL_RESEARCH',
                  'observations':[['1919-01',9999]]}
        official={'source':'FED_G17_DIRECT','observations':[['1919-01',4.1]],
                  'failed_years':[]}
        merged=merge_same_source('INDPRO',previous,official,expected_first='1919-01')
        self.assertEqual(merged['observations'],[['1919-01',4.1]])
        self.assertTrue(merged['source_mismatch_old_cache_discarded'])
        self.assertIsNone(refetch_anchor('INDPRO',previous))

if __name__=='__main__':unittest.main()
