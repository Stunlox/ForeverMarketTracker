import unittest,sqlite3,datetime as dt
from unittest.mock import patch
from market_timing import market_items,price_ratio
from simplified_market import confidence_label,top_deals

class Version11Tests(unittest.TestCase):
    def test_gradient(self):
        self.assertEqual(price_ratio(10,10,30),0)
        self.assertEqual(price_ratio(20,10,30),.5)
        self.assertEqual(price_ratio(30,10,30),1)
        self.assertIsNone(price_ratio(10,10,10))
    def test_confidence(self):
        self.assertEqual(confidence_label(2,1,1),'Low data')
        self.assertEqual(confidence_label(4,2,1),'Moderate')
        self.assertEqual(confidence_label(8,3,2),'Good')
        self.assertEqual(confidence_label(16,6,3),'High')
    def test_categories(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE items(item_id INTEGER,name TEXT,category TEXT,subcategory TEXT); CREATE TABLE snapshots(id INTEGER); CREATE TABLE prices(item_id INTEGER,snapshot_id INTEGER,quantity INTEGER,min_unit_copper INTEGER); INSERT INTO snapshots VALUES(1); INSERT INTO items VALUES(1,"Cloth","Trade Goods",""),(2,"Sword","Weapon",""); INSERT INTO prices VALUES(1,1,100,20),(2,1,1,500);')
        self.assertEqual(len(market_items(db,'Weapon',0)),1)
        self.assertEqual(len(market_items(db,'All categories',0)),2)
        self.assertEqual(len(market_items(db,'Trade Goods',0)),1)
    def test_two_day_early_signal(self):
        t=int(dt.datetime.now(dt.timezone.utc).timestamp())
        rows=[(t-86400,100,100,200,3,100,100),(t,150,150,200,3,150,150)]
        with patch('simplified_market.trade_goods',return_value=[(1,'Cloth','',1000,100)]),patch('simplified_market.observations',return_value=rows):
            deals,_=top_deals(None)
        self.assertEqual(len(deals),1)
        self.assertEqual(deals[0]['confidence'],'Low data')
        self.assertEqual(deals[0]['snapshots'],2)
