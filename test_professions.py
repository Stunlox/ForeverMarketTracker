import sqlite3,unittest,json
from professions_data import migrate,normalize_recipe,save_recipes,profitability
from vendor_catalogue import save_inventory

class ProfessionsTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT);CREATE TABLE prices(snapshot_id INTEGER,item_id INTEGER,min_unit_copper INTEGER,median_unit_copper INTEGER,quantity INTEGER);CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);')
    def tearDown(self):self.db.close()
    def test_recipe_parse(self):
        r=normalize_recipe('alchemy',{'id':1,'name':'Potion','outputItemId':9,'outputQuantity':2,'reagents':[{'itemId':3,'quantity':2}]})
        self.assertEqual(r[3:5],(9,2));self.assertEqual(json.loads(r[-1]),[[3,2]])
    def test_unknown_recipe_rejected(self):self.assertIsNone(normalize_recipe('alchemy',{'id':1,'name':'Enchant'}))
    def test_vendor_cheaper(self):
        r=normalize_recipe('alchemy',{'id':1,'name':'Potion','outputItemId':9,'reagents':[{'itemId':3,'quantity':2}]})
        save_recipes(self.db,[r]);save_inventory(self.db,[(3,5,'unlimited','forever',50)])
        self.db.executemany('INSERT INTO prices VALUES (?,?,?,?,?)',[(1,3,120,100,200),(1,9,500,500,20)])
        row=profitability(self.db,'alchemy')[0]
        self.assertEqual(row['cost'],100);self.assertEqual(row['profit'],375);self.assertEqual(row['materials'][0][3],'NPC vendor')
    def test_missing_prices_not_zero(self):
        r=normalize_recipe('alchemy',{'id':1,'name':'Potion','outputItemId':9,'reagents':[{'itemId':3,'quantity':2}]})
        save_recipes(self.db,[r]);self.assertIsNone(profitability(self.db,'alchemy')[0]['profit'])
    def test_failed_save_preserves_data(self):
        r=normalize_recipe('alchemy',{'id':1,'name':'Potion','outputItemId':9,'reagents':[{'itemId':3}]})
        save_recipes(self.db,[r]);
        with self.assertRaises(ValueError):save_recipes(self.db,[])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM craft_recipes').fetchone()[0],1)
