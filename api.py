"""Authenticated snapshot client. No unsupported private-server endpoint assumptions."""
import requests
from urllib.parse import urlparse

class AuctionClient:
    def __init__(self,settings):self.settings=settings
    def token(self):
        region=self.settings['region'].lower()
        if region not in ('us','eu','kr','tw'):raise ValueError('Invalid Blizzard region')
        response=requests.post(f'https://{region}.battle.net/oauth/token',auth=(self.settings['client_id'],self.settings['client_secret']),data={'grant_type':'client_credentials'},timeout=25)
        response.raise_for_status()
        return response.json()['access_token']
    def endpoint(self):
        if self.settings.get('auction_url'):return self.settings['auction_url']
        realm=self.settings.get('realm_id','').strip()
        if not realm.isdigit():raise ValueError('Enter verified connected realm ID or a verified auction URL')
        region=self.settings['region'].lower()
        return f'https://{region}.api.blizzard.com/data/wow/connected-realm/{realm}/auctions'
    def fetch(self):
        url=self.endpoint()
        parsed=urlparse(url)
        if parsed.scheme!='https' or not parsed.hostname:raise ValueError('Auction endpoint must be HTTPS')
        # Credentials only ever go to the official Blizzard host.
        official=parsed.hostname==f"{self.settings['region'].lower()}.api.blizzard.com"
        if not official:raise ValueError('Refusing to send Blizzard credentials to a non-Blizzard endpoint')
        headers={'Authorization':'Bearer '+self.token()}
        response=requests.get(url,headers=headers,params={'namespace':self.settings['namespace'],'locale':'en_US'},timeout=90)
        response.raise_for_status()
        payload=response.json()
        if not isinstance(payload,dict) or not isinstance(payload.get('auctions'),list):raise ValueError('Response is not a supported auction snapshot')
        return payload

def fetch_catalogue(settings):
    url=settings.get('foreverdb_url','').strip()
    if not url:raise ValueError('Configure a verified ForeverDB item-catalogue URL')
    parsed=urlparse(url)
    if parsed.scheme!='https':raise ValueError('Catalogue URL must be HTTPS')
    headers={}
    if settings.get('foreverdb_key'):headers['Authorization']='Bearer '+settings['foreverdb_key']
    response=requests.get(url,headers=headers,timeout=60)
    response.raise_for_status()
    data=response.json()
    if isinstance(data,list):return data
    for key in ('items','results','data'):
        if isinstance(data,dict) and isinstance(data.get(key),list):return data[key]
    raise ValueError('Unsupported catalogue response; pagination/field mapping needs configuration')
