import unittest
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
from simplified_market import top_deals,slot_name

class SimplifiedTests(unittest.TestCase):
    def test_empty(self):
        with patch('simplified_market.trade_goods',return_value=[]):
            deals,count=top_deals(None)
        self.assertEqual((deals,count),([],0))
    def test_sparse_history_not_ranked(self):
        with patch('simplified_market.trade_goods',return_value=[(1,'Wool Cloth','Cloth',1000,10)]),patch('simplified_market.observations',return_value=[]):
            deals,count=top_deals(None)
        self.assertEqual(deals,[]);self.assertEqual(count,1)
    def test_repeat_weekly_spread(self):
        rows=[]
        for week in range(5):
            for weekday,price in [(0,100),(3,200)]:
                stamp=int((datetime(2026,9,7,12,tzinfo=timezone.utc)+timedelta(weeks=week,days=weekday)).timestamp())
                rows.append((stamp,price,price,2000,20,price,price))
        with patch('simplified_market.trade_goods',return_value=[(1,'Wool Cloth','Cloth',2000,100)]),patch('simplified_market.observations',return_value=rows):
            deals,_=top_deals(None,days=365,min_dates=8)
        self.assertEqual(len(deals),1)
        self.assertEqual(deals[0]['buy_time'],'Monday 13:00' if __import__('zoneinfo').ZoneInfo('Europe/London').utcoffset(datetime(2026,9,7))==timedelta(hours=1) else 'Monday 12:00')
        self.assertAlmostEqual(deals[0]['margin_pct'],90.0)
    def test_ah_cut_blocks_false_profit(self):
        rows=[]
        for week in range(5):
            for weekday,price in [(0,100),(3,103)]:
                stamp=int((datetime(2026,9,7,12,tzinfo=timezone.utc)+timedelta(weeks=week,days=weekday)).timestamp())
                rows.append((stamp,price,price,2000,20,price,price))
        with patch('simplified_market.trade_goods',return_value=[(1,'Wool Cloth','Cloth',2000,100)]),patch('simplified_market.observations',return_value=rows):
            deals,_=top_deals(None,days=365,min_dates=8)
        self.assertEqual(deals,[])
if __name__=='__main__':unittest.main()
