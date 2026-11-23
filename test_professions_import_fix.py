import unittest
from unittest.mock import patch
from professions_data import normalize_recipe,recipe_rejection,fetch_professions

class ImportFixTests(unittest.TestCase):
    def test_nested_forever_style_recipe(self):
        recipe={'spellId':123,'name':'Test','makes':{'item':{'id':900},'count':2},'reagents':[{'item':{'id':42},'count':3}]}
        parsed=normalize_recipe('alchemy',recipe)
        self.assertEqual(parsed[3:5],(900,2))
        self.assertIn('[42, 3]',parsed[-1])
    def test_missing_output_diagnostic(self):
        self.assertEqual(recipe_rejection({'id':123,'reagents':[{'itemId':1}]}),'missing auctionable output item ID')
    def test_failed_import_reports_keys_and_counts(self):
        class Response:
            status_code=200
            headers={}
            def raise_for_status(self):pass
            def json(self):
                self.__class__.calls+=1
                if self.__class__.calls==1:return {'data':[{'slug':'alchemy'}]}
                return {'data':{'recipes':[{'id':12,'name':'Mystery','reagents':[{'itemId':3}]}]},'meta':{'total':1}}
            calls=0
        with patch('professions_data.requests.Session') as session:
            session.return_value.get.return_value=Response()
            with self.assertRaisesRegex(ValueError,'1 checked.*missing auctionable output item ID.*Recipe keys:'):
                fetch_professions({'foreverdb_key':'test'})
if __name__=='__main__':unittest.main()
