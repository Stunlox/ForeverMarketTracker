import unittest,sqlite3,time
from investment import budget_quantity,estimate,allocate,candidates
from simplified_market import temporary_spike_indices

class V12Tests(unittest.TestCase):
    def test_budget(self):
        self.assertEqual(budget_quantity(100,30,100),3)
        self.assertEqual(budget_quantity(100,30,2),2)
        self.assertEqual(budget_quantity(0,30,2),0)
    def test_net_profit(self):
        self.assertEqual(estimate(1000,100,200,8,5)['profit'],720)
    def test_spike_reversal(self):
        prices=[100,102,900,101,100]
        rows=[(i,v,v,100,1,v,v) for i,v in enumerate(prices)]
        self.assertEqual(temporary_spike_indices(rows),{2})
        self.assertEqual(temporary_spike_indices([(i,v,v,100,1,v,v) for i,v in enumerate([100,110,300,310,330])]),set())
    def test_allocation_cap(self):
        items=[{'buy':100,'resale':200,'supply':100,'affordable_supply':10,'name':str(i)} for i in range(5)]
        result=allocate(1000,items)
        self.assertLessEqual(sum(r['cost'] for r in result),1000)
        self.assertTrue(all(r['cost']<=350 for r in result))
    def test_candidates_search_and_unprofitable(self):
        db=sqlite3.connect(':memory:')
        db.executescript('''CREATE TABLE items(item_id INTEGER,name TEXT,category TEXT,quality INTEGER);
        CREATE TABLE snapshots(id INTEGER,captured_at INTEGER);
        CREATE TABLE prices(item_id INTEGER,snapshot_id INTEGER,quantity INTEGER,min_unit_copper INTEGER,cheap10_unit_copper INTEGER,cheap20_unit_copper INTEGER,median_unit_copper INTEGER);''')
        now=int(time.time());db.execute('INSERT INTO items VALUES(1,"Copper Ore","Trade Goods",2)')
        for i in range(3):
            db.execute('INSERT INTO snapshots VALUES(?,?)',(i+1,now-(2-i)*3600))
            db.execute('INSERT INTO prices VALUES(1,?,100,100,100,100,100)',(i+1,))
        self.assertEqual(candidates(db),[])
        found=candidates(db,include_all=True,search='copper')
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['affordable_supply'],10)
