import unittest,sqlite3
from core import import_catalogue
class CatalogueTests(unittest.TestCase):
 def test_mapping_and_update(self):
  db=sqlite3.connect(':memory:')
  db.executescript("CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,category TEXT,subcategory TEXT,updated_at INTEGER); CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);")
  self.assertEqual(import_catalogue(db,[{'id':123,'name':'Axe','classId':2,'subclassId':0}]),1)
  self.assertEqual(db.execute('SELECT name,category,subcategory FROM items').fetchone(),('Axe','Weapons','Axes (1H)'))
  self.assertEqual(import_catalogue(db,[{'id':123,'name':'New Axe','classId':2,'subclassId':0}]),1)
  self.assertEqual(db.execute('SELECT COUNT(*) FROM items').fetchone()[0],1)
 def test_empty_does_not_mark_refreshed(self):
  db=sqlite3.connect(':memory:')
  db.executescript("CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,category TEXT,subcategory TEXT,updated_at INTEGER); CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);")
  with self.assertRaises(ValueError):import_catalogue(db,[])
  self.assertEqual(db.execute('SELECT COUNT(*) FROM metadata').fetchone()[0],0)
if __name__=='__main__':unittest.main()
