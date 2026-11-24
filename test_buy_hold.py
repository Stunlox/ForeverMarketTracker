import unittest,datetime as dt
from buy_hold import windows,UK
class BuyHoldTests(unittest.TestCase):
    def test_repeated_future_window(self):
        now=dt.datetime(2026,11,24,9,tzinfo=UK).timestamp()
        points=[(dt.datetime(2026,11,d,14,tzinfo=UK).timestamp(),95000,98000,200) for d in (11,18)]
        w=windows(points,now,48,80000,5,5)
        self.assertEqual(w[0],95000)
        self.assertEqual(w[3],2)
        self.assertEqual(windows(points,now,24,80000,5,5)[5],'Low')
        self.assertIsNone(windows(points,now,48,95000,5,0))
        self.assertIsNone(windows(points[:1],now,48,80000,5,5))

    def test_short_history_daily_fallback(self):
        now=dt.datetime(2026,11,24,9,tzinfo=UK).timestamp()
        points=[(dt.datetime(2026,11,d,14,tzinfo=UK).timestamp(),95000,98000,200) for d in (21,22,23)]
        w=windows(points,now,24,80000,5,5)
        self.assertEqual(w[5],'Moderate')
        self.assertEqual(w[0],95000)
        self.assertLessEqual(w[1],24)
        self.assertIsNone(windows(points,now,24,95000,5,0))
        self.assertIsNone(windows(points[:1],now,24,80000,5,5))
