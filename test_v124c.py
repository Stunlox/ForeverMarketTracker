import unittest,sqlite3,json
from vendor_catalogue import purchase_price,parse_vendor,save_inventory,vendor_price_coverage
from professions_data import migrate,profitability

class PatchTests(unittest.TestCase):
    def test_purchase_price_variants(self):
        self.assertEqual(purchase_price({'buyPrice':120}),120)
        self.assertEqual(purchase_price({'price':{'copper':350}}),350)
        self.assertEqual(purchase_price({'cost':{'amountCopper':99}}),99)
        self.assertIsNone(purchase_price({'sellPrice':100}))
        self.assertIsNone(purchase_price({'price':100}))
    def test_vendor_coverage_and_profitability(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,quality INTEGER); CREATE TABLE snapshots(id INTEGER PRIMARY KEY); CREATE TABLE prices(snapshot_id INTEGER,item_id INTEGER,min_unit_copper INTEGER,median_unit_copper INTEGER,quantity INTEGER); CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);')
        db.executemany('INSERT INTO items VALUES (?,?,?)',[(10,'Vial',1),(20,'Potion',2)])
        db.execute('INSERT INTO snapshots VALUES (1)')
        db.executemany('INSERT INTO prices VALUES (?,?,?,?,?)',[(1,10,1000,1000,50),(1,20,5000,5000,20)])
        save_inventory(db,[(10,1,'unlimited','forever',200),(20,2,'unknown','classic')])
        self.assertEqual(vendor_price_coverage(db),{'total':2,'priced':1,'missing':1,'items':1})
        migrate(db);db.execute('INSERT INTO craft_recipes VALUES (?,?,?,?,?,?,?)',('alchemy',5,'Potion',20,1,1,json.dumps([[10,2]])))
        rows=profitability(db,'alchemy')
        self.assertEqual(rows[0]['quality'],2)
        self.assertEqual(rows[0]['profit'],4350)
        self.assertEqual(rows[0]['materials'][0].source,'NPC vendor')
        self.assertEqual(rows[0]['materials'][0].stock,'unlimited')
        db.close()
    def test_vendor_detail_nested(self):
        self.assertEqual(parse_vendor({'id':5},{'data':{'items':[{'itemId':10,'purchasePrice':{'copper':40}}]}})[0][-1],40)

if __name__=='__main__':unittest.main()
