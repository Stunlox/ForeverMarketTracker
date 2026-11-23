import sqlite3,unittest,time
from trade_ledger import migrate,save_lot,lots,realised_profit,sell_advice,delete_lot
class LedgerTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(':memory:')
  self.db.execute('CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,quality INTEGER)')
  self.db.execute('INSERT INTO items VALUES(1,"Righteous Orb",2)')
  self.db.execute('CREATE TABLE snapshots(id INTEGER PRIMARY KEY,captured_at INTEGER)')
  self.db.execute('CREATE TABLE prices(snapshot_id INTEGER,item_id INTEGER,min_unit_copper INTEGER,median_unit_copper INTEGER,quantity INTEGER,listings INTEGER,cheap10_unit_copper INTEGER,cheap20_unit_copper INTEGER)')
 def test_add_update_delete(self):
  key=save_lot(self.db,1,3,80000)
  self.assertEqual(lots(self.db)[0][4],3)
  save_lot(self.db,1,3,80000,True,90000,'sold',key)
  self.assertEqual(lots(self.db)[0][7],1)
  self.assertEqual(lots(self.db)[0][8],90000)
  save_lot(self.db,1,3,80000,False,None,'reopened',key)
  self.assertIsNone(lots(self.db)[0][8])
  delete_lot(self.db,key);self.assertEqual(lots(self.db),[])
 def test_validation(self):
  with self.assertRaises(ValueError):save_lot(self.db,1,0,80000)
  with self.assertRaises(ValueError):save_lot(self.db,1,1,80000,True,None)
  with self.assertRaises(ValueError):save_lot(self.db,2,1,80000)
 def test_profit(self):self.assertEqual(realised_profit(2,80000,90000),11000)
 def test_no_history(self):self.assertEqual(sell_advice(self.db,1,80000)['status'],'Insufficient history')
 def test_single_spike_not_window(self):
  now=int(time.time())
  for i in range(10):
   ts=now-(10-i)*3600
   self.db.execute('INSERT INTO snapshots VALUES(?,?)',(i+1,ts))
   price=160000 if i==5 else 90000
   self.db.execute('INSERT INTO prices VALUES(?,?,?,?,?,?,?,?)',(i+1,1,price,price,200,10,price,price))
  result=sell_advice(self.db,1,80000)
  self.assertNotEqual(result.get('expected'),160000)
  self.assertNotEqual(result.get('window'),'Monday 07:00')
if __name__=='__main__':unittest.main()
