import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from weekday_strategy import slot,paired_signals
UK=ZoneInfo('Europe/London')
def stamp(y,m,d,h):return int(datetime(y,m,d,h,tzinfo=UK).timestamp())
class TestWeekdayStrategy(unittest.TestCase):
    def test_weekend_excluded(self):
        self.assertIsNone(slot(stamp(2026,11,21,19)))
        self.assertIsNone(slot(stamp(2026,11,22,14)))
    def test_friday_evening_excluded(self):self.assertIsNone(slot(stamp(2026,11,20,19)))
    def test_only_consecutive_weekdays(self):
        observations=[(1,stamp(2026,11,16,19),100,500),(1,stamp(2026,11,17,14),150,500),
            (1,stamp(2026,11,17,19),100,500),(1,stamp(2026,11,18,14),150,500),
            (1,stamp(2026,11,18,19),100,500),(1,stamp(2026,11,19,14),150,500),
            (2,stamp(2026,11,20,19),100,500),(2,stamp(2026,11,23,14),200,500)]
        result=paired_signals(observations)
        self.assertEqual(result[1]['pairs'],3)
        self.assertNotIn(2,result)
    def test_loss_is_not_recommended(self):
        observations=[]
        for d in (16,17,18):
            observations.extend([(1,stamp(2026,11,d,19),200,100),(1,stamp(2026,11,d+1,14),100,100)])
        self.assertEqual(paired_signals(observations),{})
    def test_dst_uk_hours(self):
        self.assertEqual(slot(stamp(2026,7,6,19))[1],'buy')
        self.assertEqual(slot(stamp(2026,7,7,14))[1],'sell')
if __name__=='__main__':unittest.main()
