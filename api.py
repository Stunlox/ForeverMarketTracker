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

def fetch_catalogue(settings, progress=None):
    """Fetch the entire ForeverDB item catalogue in pages, respecting rate limits.

    Returns all items only after every page succeeds. A failed page never marks
    the catalogue as refreshed, so users can retry safely.
    """
    import time
    from urllib.parse import urlparse
    base = 'https://foreverdb.net/api/v1/items'
    configured = settings.get('foreverdb_url', '').strip()
    if configured:
        parsed = urlparse(configured)
        if parsed.scheme != 'https' or parsed.hostname not in ('foreverdb.net','www.foreverdb.net') or parsed.path.rstrip('/') != '/api/v1/items':
            raise ValueError('ForeverDB catalogue URL must be https://foreverdb.net/api/v1/items')
    key = settings.get('foreverdb_key','').strip()
    if not key:
        raise ValueError('Enter your ForeverDB API key in Settings')
    session = requests.Session()
    session.headers.update({'X-API-Key':key,'User-Agent':'ForeverMarketTracker/0.5 (personal app; ForeverDB.net credited)'})
    result = []
    offset = 0
    total = None
    while True:
        for attempt in range(4):
            response = session.get(base, params={'limit':100,'offset':offset}, timeout=60)
            if response.status_code == 429 and attempt < 3:
                retry = response.headers.get('Retry-After','5')
                try: delay = min(90,max(1,int(retry)))
                except ValueError: delay = 5
                time.sleep(delay)
                continue
            response.raise_for_status()
            break
        payload = response.json()
        if not isinstance(payload,dict):
            raise ValueError('Unexpected ForeverDB catalogue response')
        data = payload.get('data',[])
        if isinstance(data,dict):
            rows = data.get('items',data.get('results',[]))
        else: rows = data
        if not isinstance(rows,list):
            raise ValueError('ForeverDB catalogue response missing items list')
        meta = payload.get('meta') or {}
        if isinstance(meta,dict) and meta.get('total') is not None:
            total = int(meta['total'])
        if not rows:
            if total is not None and offset < total:
                raise ValueError(f'Catalogue ended early at {offset} of {total} items')
            break
        result.extend(rows)
        offset += len(rows)
        if progress: progress(offset,total)
        if total is not None and offset >= total: break
        if len(rows) < 100: break
        if offset > 100000: raise ValueError('Unexpectedly large catalogue; import stopped')
        time.sleep(0.12)
    if not result: raise ValueError('ForeverDB returned no catalogue items')
    return result
