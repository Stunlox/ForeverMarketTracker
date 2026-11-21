"""WoW Forever auction client, adapted from the working Forever Gold Companion."""
import requests
from urllib.parse import urlparse

ROOT = 'https://eu.api.blizzard.com/data/wow/ruleset/1/auctions/'
NAMESPACE = 'dynamic-forever-eu'

class AuctionClient:
    def __init__(self, settings):
        self.settings = settings
        self.session = requests.Session()

    def token(self):
        response = requests.post('https://oauth.battle.net/token',
            auth=(self.settings['client_id'], self.settings['client_secret']),
            data={'grant_type':'client_credentials'}, timeout=30)
        response.raise_for_status()
        return response.json()['access_token']

    def authenticate(self):
        self.session.headers['Authorization'] = 'Bearer ' + self.token()

    def request(self, url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'eu.api.blizzard.com':
            raise ValueError('Refusing to send Blizzard token to an untrusted host')
        response = self.session.get(url, params={'namespace':NAMESPACE}, timeout=180)
        if not response.ok:
            raise RuntimeError(f'HTTP {response.status_code}: {response.text[:1200]}')
        return response.json()

    def discover_houses(self):
        self.authenticate()
        payload = self.request(ROOT)
        houses = payload.get('auctions', [])
        if not isinstance(houses, list):
            raise ValueError('Auction index did not return a list')
        return houses

    def fetch(self):
        house = str(self.settings.get('house_id','')).strip()
        if not house.isdigit():
            raise ValueError('Choose a WoW Forever auction house from Discover Houses first')
        self.authenticate()
        base = ROOT + house
        normal = self.request(base)
        commodities = self.request(base + '/commodities')
        for payload in (normal, commodities):
            if not isinstance(payload,dict) or not isinstance(payload.get('auctions'),list):
                raise ValueError('Unexpected auction response; no snapshot saved')
        # Existing store_snapshot accepts combined auctions; commodity prices are per unit.
        return {'auctions': normal['auctions'] + commodities['auctions']}

def fetch_catalogue(settings):
    """Single-page catalogue import; monthly pagination is not implemented yet."""
    url = settings.get('foreverdb_url','').strip()
    if not url:
        raise ValueError('Enter a verified ForeverDB catalogue endpoint')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('foreverdb.net','www.foreverdb.net'):
        raise ValueError('Catalogue must be served from foreverdb.net over HTTPS')
    response = requests.get(url,headers={'X-API-Key':settings.get('foreverdb_key',''),
                                          'User-Agent':'ForeverMarketTracker/0.4 (ForeverDB credited)'},timeout=60)
    response.raise_for_status()
    payload = response.json()
    data = payload.get('data',payload) if isinstance(payload,dict) else payload
    if isinstance(data,list):return data
    if isinstance(data,dict):
        for key in ('items','results'):
            if isinstance(data.get(key),list):return data[key]
    raise ValueError('Unsupported ForeverDB catalogue response')
