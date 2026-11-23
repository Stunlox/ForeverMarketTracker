import unittest
from pricing_reference import isolated_spikes,conservative_resale
from simplified_market import temporary_spike_indices

class PricingV124dTests(unittest.TestCase):
    def test_righteous_orb_one_hour_spike(self):
        prices=[80000,85000,159954,90000,87000]
        rows=[(i*3600,p,p,200 if i!=2 else 43,1,p,p) for i,p in enumerate(prices)]
        self.assertEqual(temporary_spike_indices(rows),{2})
    def test_sustained_repricing_is_not_removed(self):
        prices=[80000,85000,150000,155000,158000]
        rows=[(i*3600,p,p,200,1,p,p) for i,p in enumerate(prices)]
        self.assertEqual(temporary_spike_indices(rows),set())
    def test_weekly_pattern_not_removed(self):
        rows=[(i*86400,p,p,200,1,p,p) for i,p in enumerate([80000,150000,85000])]
        self.assertEqual(temporary_spike_indices(rows),set())
    def test_resale_lower_quartile(self):
        self.assertEqual(conservative_resale([90000,92000,95000,110000,160000]),92000)
    def test_empty(self):
        self.assertIsNone(conservative_resale([]))

if __name__=='__main__':unittest.main()
