import unittest
from datetime import datetime,timezone
from market_timing import analyse,summarize
class TimingTests(unittest.TestCase):
 def test_repeat_minimum(self):
  ts=int(datetime(2026,11,16,12,tzinfo=timezone.utc).timestamp())
  cells=analyse([(ts,10,20,100,3)],metric='median')
  self.assertFalse(cells[(0,12)]['eligible'])
  self.assertIsNone(summarize(cells))
 def test_robust_median(self):
  ts=int(datetime(2026,11,16,12,tzinfo=timezone.utc).timestamp())
  cells=analyse([(ts,1,100,50,2),(ts+7*86400,1,200,100,3),(ts+14*86400,1,100,150,4)],metric='median')
  self.assertEqual(cells[(0,12)]['median_price'],100)
  self.assertEqual(cells[(0,12)]['median_quantity'],100)
if __name__=='__main__':unittest.main()
