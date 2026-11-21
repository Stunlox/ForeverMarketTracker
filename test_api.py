import unittest
from unittest.mock import patch,Mock
from api import AuctionClient,ROOT,NAMESPACE
class ApiTests(unittest.TestCase):
 def test_uses_forever_namespace(self):self.assertEqual(NAMESPACE,'dynamic-forever-eu')
 def test_requires_selected_house(self):
  with self.assertRaisesRegex(ValueError,'Discover Houses'):
   AuctionClient({'house_id':''}).fetch()
 def test_combines_commodities(self):
  client=AuctionClient({'house_id':'110','client_id':'id','client_secret':'secret'})
  client.authenticate=lambda:None
  with patch.object(client,'request',side_effect=[{'auctions':[{'item':{'id':1},'quantity':1,'buyout':100}]},{'auctions':[{'item':{'id':2},'quantity':3,'unit_price':50}]}]) as req:
   result=client.fetch()
   self.assertEqual(len(result['auctions']),2)
   self.assertEqual(req.call_args_list[1].args[0],ROOT+'110/commodities')
if __name__=='__main__':unittest.main()
