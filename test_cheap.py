import unittest,sqlite3
from core import cheapest_fraction,store_snapshot
from market_timing import analyse
class CheapTests(unittest.TestCase):
 def test_quantity_weighted(self):
  self.assertEqual(cheapest_fraction([(2000,10),(2500,90),(3000,900)],.10),2450)
 def test_not_listing_weighted(self):
  self.assertEqual(cheapest_fraction([(100,1),(200,99)],.10),190)
 def test_snapshot_columns(self):
  db=sqlite3.connect(':memory:')
  db.executescript('CREATE TABLE snapshots(id INTEGER PRIMARY KEY,captured_at INTEGER,source TEXT,auction_count INTEGER);CREATE TABLE prices(snapshot_id INTEGER,item_id INTEGER,min_unit_copper INTEGER,median_unit_copper INTEGER,quantity INTEGER,listings INTEGER);CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,category TEXT DEFAULT "Uncategorised",subcategory TEXT DEFAULT "",updated_at INTEGER);')
  store_snapshot(db,{'auctions':[{'item':{'id':5},'quantity':10,'unit_price':100},{'item':{'id':5},'quantity':90,'unit_price':200}]})
  self.assertEqual(db.execute('SELECT cheap10_unit_copper FROM prices').fetchone()[0],100)
 def test_missing_legacy(self):
  self.assertEqual(analyse([(1700000000,100,200,100,2,None,None)],metric='cheap10'),{})
if __name__=='__main__':unittest.main()
