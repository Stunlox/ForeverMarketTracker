import unittest,sqlite3
from core import parse_auctions,weighted_median,store_snapshot
class TestCore(unittest.TestCase):
 def test_stack_unit(self):
  self.assertEqual(parse_auctions({'auctions':[{'item':{'id':12},'quantity':3,'buyout':100}]}),{12:[(34,3)]})
 def test_weighted(self):self.assertEqual(weighted_median([(10,1),(20,10)]),20)
 def test_reject(self):
  with self.assertRaises(ValueError):parse_auctions({'items':[]})
 def test_store(self):
  db=sqlite3.connect(':memory:');db.executescript('CREATE TABLE snapshots(id INTEGER PRIMARY KEY,captured_at INTEGER,source TEXT,auction_count INTEGER);CREATE TABLE prices(snapshot_id INTEGER,item_id INTEGER,min_unit_copper INTEGER,median_unit_copper INTEGER,quantity INTEGER,listings INTEGER);CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,category TEXT DEFAULT "Uncategorised",subcategory TEXT DEFAULT "",updated_at INTEGER);')
  self.assertEqual(store_snapshot(db,{'auctions':[{'item':{'id':5},'quantity':2,'unit_price':250}]}),1)
  self.assertEqual(db.execute('SELECT min_unit_copper FROM prices').fetchone()[0],250)
if __name__=='__main__':unittest.main()
