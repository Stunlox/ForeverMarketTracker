import sqlite3,unittest
from unittest.mock import patch
from exclusions import migrate,exclude,restore,excluded_ids,import_vendor_metadata
from timing_advice import item_timing

class Version121Tests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE items(item_id INTEGER PRIMARY KEY,name TEXT,quality INTEGER)')
        self.db.execute('INSERT INTO items VALUES (101,\'Thick Logs\',1)')
        migrate(self.db)
    def tearDown(self):self.db.close()
    def test_exclude_restore(self):
        exclude(self.db,101,'Vendor (manual)')
        self.assertIn(101,excluded_ids(self.db))
        self.assertEqual(self.db.execute('SELECT reason FROM item_exclusions').fetchone()[0],'Vendor (manual)')
        restore(self.db,101)
        self.assertNotIn(101,excluded_ids(self.db))
    def test_vendor_only_requires_explicit_flag(self):
        import_vendor_metadata(self.db,[{'id':101,'name':'Thick Logs','vendor':True}])
        self.assertNotIn(101,excluded_ids(self.db))
        import_vendor_metadata(self.db,[{'id':101,'vendorOnly':True}])
        self.assertIn(101,excluded_ids(self.db))
    def test_insufficient_timing(self):
        with patch('timing_advice.observations',return_value=[]):
            self.assertEqual(item_timing(self.db,101),('Insufficient history','Insufficient history'))
    def test_timing_prices(self):
        import datetime as dt
        from zoneinfo import ZoneInfo
        uk=ZoneInfo('Europe/London')
        a=int(dt.datetime(2026,11,16,8,tzinfo=uk).timestamp())
        b=int(dt.datetime(2026,11,20,19,tzinfo=uk).timestamp())
        rows=[(a,10000,10000,100,10,10000,10000),(b,20000,20000,100,10,20000,20000)]
        with patch('timing_advice.observations',return_value=rows):
            self.assertEqual(item_timing(self.db,101),('Provisional — insufficient repeated hours','Provisional — insufficient repeated hours'))
if __name__=='__main__':unittest.main()
