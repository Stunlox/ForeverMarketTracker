import sqlite3, unittest
from core import import_catalogue,item_quality,quality_for_items,QUALITY_COLORS
class RarityTests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(item_quality({'quality':4}),4)
        self.assertEqual(item_quality({'quality':{'id':3}}),3)
        self.assertEqual(item_quality({'rarity':'Uncommon'}),2)
        self.assertIsNone(item_quality({'name':'unknown'}))
        self.assertIsNone(item_quality({'quality':99}))
    def test_migration_and_preservation(self):
        db=sqlite3.connect(':memory:')
        db.execute('CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,category TEXT,subcategory TEXT,updated_at INTEGER)')
        db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)')
        import_catalogue(db,[{'id':123,'name':'Rare ore','classId':7,'quality':3}])
        self.assertEqual(quality_for_items(db,[123])[123],3)
        import_catalogue(db,[{'id':123,'name':'Rare ore','classId':7}])
        self.assertEqual(quality_for_items(db,[123])[123],3)
        self.assertIn(3,QUALITY_COLORS)
if __name__=='__main__':unittest.main()
