import unittest
from unittest.mock import patch
from pricing_reference import isolated_spikes
from vendor_catalogue import fetch_vendors

class PatchETests(unittest.TestCase):
    def test_isolated_16g_removed_but_sustained_change_kept(self):
        base=1700000000
        rows=[(base+i*3600,v,v,250,1,v,v) for i,v in enumerate([80000,82000,159954,90000,92000])]
        self.assertEqual(isolated_spikes(rows,price_index=5),{2})
        rows=[(base+i*3600,v,v,250,1,v,v) for i,v in enumerate([80000,82000,159954,161000,160000])]
        self.assertEqual(isolated_spikes(rows,price_index=5),set())
    def test_live_vendor_counts_do_not_require_extra_requests(self):
        class Response:
            status_code=200
            headers={}
            def __init__(self,data):self.data=data
            def raise_for_status(self):pass
            def json(self):return self.data
        calls=[]
        def get(_session,url,params=None,timeout=None):
            calls.append(url)
            if url.endswith('/vendors'):return Response({'data':[{'id':10},{'id':20}]})
            if url.endswith('/10'):return Response({'data':{'items':[{'itemId':1,'buyPrice':75},{'itemId':2}]}})
            return Response({'data':{'items':[{'itemId':3,'purchasePrice':{'copper':20}}]}})
        updates=[]
        with patch('vendor_catalogue.requests.Session.get',new=get),patch('vendor_catalogue.time.sleep'):
            rows,count=fetch_vendors({'foreverdb_key':'fake'},lambda stage,current,total:updates.append((stage,current,total)))
        self.assertEqual(len(calls),3)
        self.assertEqual((count,len(rows)),(2,3))
        self.assertIn('2 rows | 1 priced | 1 priced items | 1 missing',updates[-2][0])
        self.assertIn('3 rows | 2 priced | 2 priced items | 1 missing',updates[-1][0])
if __name__=='__main__':unittest.main()
