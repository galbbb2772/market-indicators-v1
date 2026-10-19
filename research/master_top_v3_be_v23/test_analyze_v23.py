"""Run in this directory: python -m unittest -v test_analyze_v23.py"""
import unittest
from analyze_v23 import LCG, auc, ci

class TestV23(unittest.TestCase):
    def test_auc_perfect(self):
        rows=[{"x":9,"y":True},{"x":7,"y":True},{"x":2,"y":False},{"x":1,"y":False}]
        self.assertEqual(auc(rows,"x","y"),1.0)
    def test_auc_reverse(self):
        rows=[{"x":1,"y":True},{"x":7,"y":False}]
        self.assertEqual(auc(rows,"x","y"),0.0)
    def test_auc_tie(self):
        self.assertEqual(auc([{"x":1,"y":True},{"x":1,"y":False}],"x","y"),.5)
    def test_auc_single_class(self):
        self.assertIsNone(auc([{"x":1,"y":True}],"x","y"))
    def test_lcg_reproducible(self):
        a,b=LCG(),LCG()
        self.assertEqual([a.draw(100) for _ in range(40)],[b.draw(100) for _ in range(40)])
    def test_zero_difference_bootstrap(self):
        rows=[{"bubble_build":str(i),"cape_pct":str(i),"mdd20":i>=5} for i in range(10)]
        lo,hi,n=ci(rows,LCG(),rep=400)
        self.assertEqual((lo,hi),(0,0))
        self.assertGreater(n,200)

if __name__=="__main__":unittest.main()
