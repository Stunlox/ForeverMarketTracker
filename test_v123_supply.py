import sqlite3,time,unittest
from supply_filter import eligible,average_quantities

class SupplyFilterTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE snapshots(id INTEGER PRIMARY KEY,captured_at INTEGER);CREATE TABLE prices(snapshot_id INTEGER,item_id INTEGER,quantity INTEGER);')
        now=int(time.time())
        self.db.executemany('INSERT INTO snapshots VALUES (?,?)',[(1,now-3600),(2,now)])
        self.db.executemany('INSERT INTO prices VALUES (?,?,?)',[(1,11,200),(2,11,20),(1,12,20),(2,12,300)])
        self.rows=[{'item_id':11,'supply':20},{'item_id':12,'supply':300}]
    def tearDown(self):self.db.close()
    def test_latest_default_100(self):
        self.assertEqual([r['item_id'] for r in eligible(self.db,self.rows)],[12])
    def test_historical_average_100(self):
        self.assertEqual([r['item_id'] for r in eligible(self.db,self.rows,100,'Historical average')],[11,12])
        self.assertEqual(average_quantities(self.db,[11],30)[11],110)
    def test_disable_minimum(self):
        self.assertEqual(len(eligible(self.db,self.rows,0)),2)
    def test_missing_history_not_eligible(self):
        self.assertEqual(eligible(self.db,[{'item_id':13,'supply':1000}],100,'Historical average'),[])
if __name__=='__main__':unittest.main()
