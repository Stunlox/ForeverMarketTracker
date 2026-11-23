import sqlite3,unittest
from vendor_catalogue import stock_type,parse_vendor,save_inventory,vendor_classification
from exclusions import excluded_ids,exclude

class VendorTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)')
    def tearDown(self):self.db.close()
    def test_stock_explicit_only(self):
        self.assertEqual(stock_type({'limitedStock':True}),'limited')
        self.assertEqual(stock_type({'limitedStock':False}),'unlimited')
        self.assertEqual(stock_type({'maxCount':0}),'unknown')
        self.assertEqual(stock_type({'stockType':'limited'}),'limited')
    def test_vendor_parse(self):
        rows=parse_vendor({'id':123,'seenInForever':True},{'data':{'items':[{'itemId':5,'limitedStock':False},{'itemId':6,'limitedStock':True},{'itemId':7}]}})
        self.assertEqual(rows,[(5,123,'unlimited','forever'),(6,123,'limited','forever'),(7,123,'unknown','forever')])
    def test_checkbox_filters_and_manual_override(self):
        save_inventory(self.db,[(5,123,'unlimited','forever'),(6,123,'limited','classic'),(7,123,'unknown','unknown')])
        self.assertEqual(excluded_ids(self.db),{5,6})
        self.assertEqual(excluded_ids(self.db,include_unlimited=True),{6})
        self.assertEqual(excluded_ids(self.db,include_limited=True),{5})
        self.assertEqual(excluded_ids(self.db,include_unlimited=True,include_limited=True),set())
        exclude(self.db,5)
        self.assertEqual(excluded_ids(self.db,include_unlimited=True,include_limited=True),{5})
        self.assertEqual(dict(vendor_classification(self.db)),{'unlimited':1,'limited':1,'unknown':1})
    def test_failed_import_does_not_change_existing_rows(self):
        save_inventory(self.db,[(5,123,'unlimited','forever')])
        with self.assertRaises(sqlite3.IntegrityError):save_inventory(self.db,[(6,123,'bogus','forever')])
        self.assertEqual(self.db.execute('SELECT item_id FROM vendor_inventory').fetchall(),[(5,)])
if __name__=='__main__':unittest.main()
