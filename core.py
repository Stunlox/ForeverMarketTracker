"""Local market history and auction snapshot processing."""
import json, sqlite3, statistics, time
from pathlib import Path

APP_DIR = Path.home() / 'AppData' / 'Local' / 'ForeverMarketTracker' if __import__('os').name == 'nt' else Path.home() / '.forever_market_tracker'
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / 'market.sqlite3'
SETTINGS_PATH = APP_DIR / 'settings.json'

def load_settings():
    defaults = {'region':'eu','realm_id':'','namespace':'dynamic-eu','auction_url':'','foreverdb_url':'','foreverdb_key':'','client_id':'2659c616a4cc4e4e85ba016f1e0d20b6','client_secret':'','interval_minutes':60,'catalogue_days':30,'ah_cut_percent':5}
    if SETTINGS_PATH.exists():
        try: defaults.update(json.loads(SETTINGS_PATH.read_text(encoding='utf8')))
        except (ValueError,OSError): pass
    return defaults

def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps(settings,indent=2),encoding='utf8')
    try: __import__('os').chmod(SETTINGS_PATH,0o600)
    except OSError: pass

def connect():
    db=sqlite3.connect(DB_PATH)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT DEFAULT 'Uncategorised', subcategory TEXT DEFAULT '', updated_at INTEGER);
    CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, captured_at INTEGER NOT NULL, source TEXT NOT NULL, auction_count INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS prices (snapshot_id INTEGER NOT NULL, item_id INTEGER NOT NULL, min_unit_copper INTEGER NOT NULL, median_unit_copper INTEGER NOT NULL, quantity INTEGER NOT NULL, listings INTEGER NOT NULL, PRIMARY KEY(snapshot_id,item_id));
    CREATE INDEX IF NOT EXISTS idx_prices_item ON prices(item_id,snapshot_id);
    CREATE TABLE IF NOT EXISTS watchlist (item_id INTEGER PRIMARY KEY, target_copper INTEGER);
    CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
    ''')
    return db

def copper(value):
    g,s=divmod(max(0,int(value)),10000)
    silver,c=divmod(s,100)
    return f'{g:,}g {silver:02d}s {c:02d}c'

def parse_auctions(payload):
    """Blizzard-like auctions payload; prices are per unit, not stack total."""
    if not isinstance(payload,dict) or not isinstance(payload.get('auctions'),list):
        raise ValueError('Expected JSON object with auctions array; endpoint/schema not verified')
    by_item={}
    for auction in payload['auctions']:
        item=auction.get('item') or {}
        item_id=item.get('id') if isinstance(item,dict) else auction.get('item_id')
        qty=auction.get('quantity',0)
        if not isinstance(item_id,int) or not isinstance(qty,int) or qty<=0: continue
        total=auction.get('buyout')
        unit=auction.get('unit_price')
        if unit is None and isinstance(total,int) and total>0: unit=(total+qty-1)//qty
        if not isinstance(unit,int) or unit<=0: continue
        by_item.setdefault(item_id,[]).append((unit,qty))
    return by_item

def weighted_median(entries):
    ordered=sorted(entries)
    total=sum(q for _,q in ordered)
    running=0
    for price,q in ordered:
        running+=q
        if running*2>=total:return price
    return 0

def store_snapshot(db,payload,source='Blizzard API'):
    data=parse_auctions(payload)
    if not data: raise ValueError('No usable buyout auctions found; refusing to store empty snapshot')
    with db:
        cur=db.execute('INSERT INTO snapshots(captured_at,source,auction_count) VALUES (?,?,?)',(int(time.time()),source,len(payload['auctions'])))
        sid=cur.lastrowid
        db.executemany('INSERT INTO prices VALUES (?,?,?,?,?,?)',[(sid,item,min(p for p,_ in entries),weighted_median(entries),sum(q for _,q in entries),len(entries)) for item,entries in data.items()])
        db.executemany("INSERT OR IGNORE INTO items(item_id,name,updated_at) VALUES (?, ?, ?)",[(item,f'Item #{item}',int(time.time())) for item in data])
    return len(data)

def import_catalogue(db,items):
    rows=[]
    for obj in items:
        item_id=obj.get('id',obj.get('item_id'))
        if not isinstance(item_id,int):continue
        name=obj.get('name') or f'Item #{item_id}'
        if isinstance(name,dict):name=name.get('en_US') or next(iter(name.values()),f'Item #{item_id}')
        category=obj.get('category') or obj.get('item_class') or 'Uncategorised'
        subcategory=obj.get('subcategory') or obj.get('item_subclass') or ''
        if isinstance(category,dict):category=category.get('name',str(category.get('id','Uncategorised')))
        if isinstance(subcategory,dict):subcategory=subcategory.get('name',str(subcategory.get('id','')))
        rows.append((item_id,str(name),str(category),str(subcategory),int(time.time())))
    with db:
        db.executemany('''INSERT INTO items VALUES (?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET name=excluded.name,category=excluded.category,subcategory=excluded.subcategory,updated_at=excluded.updated_at''',rows)
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('catalogue_refreshed',?)",(str(int(time.time())),))
    return len(rows)

def market_rows(db,search='',category='All',period_days=30):
    since=int(time.time())-period_days*86400
    sql='''WITH latest AS (SELECT p.item_id,MAX(p.snapshot_id) sid FROM prices p GROUP BY p.item_id), historical AS (SELECT p.item_id,p.min_unit_copper price FROM prices p JOIN snapshots s ON s.id=p.snapshot_id WHERE s.captured_at>=?), current AS (SELECT p.* FROM prices p JOIN latest l ON p.item_id=l.item_id AND p.snapshot_id=l.sid) SELECT i.item_id,i.name,i.category,i.subcategory,c.min_unit_copper,c.quantity,c.listings,h.price FROM current c JOIN items i ON i.item_id=c.item_id LEFT JOIN historical h ON h.item_id=i.item_id WHERE i.name LIKE ? AND (?='All' OR i.category=?) ORDER BY i.name'''
    grouped={}
    for item_id,name,cat,sub,current,qty,listings,hist in db.execute(sql,(since,'%'+search+'%',category,category)):
        if item_id not in grouped:grouped[item_id]=[item_id,name,cat,sub,current,qty,listings,[]]
        if hist is not None:grouped[item_id][-1].append(hist)
    output=[]
    for item_id,name,cat,sub,current,qty,listings,history in grouped.values():
        median=int(statistics.median(history)) if history else current
        discount=(median-current)/median*100 if median else 0
        output.append((item_id,name,cat,sub,current,median,discount,qty,listings,len(history)))
    return output

def history(db,item_id,days=30):
    return db.execute('''SELECT s.captured_at,p.min_unit_copper,p.median_unit_copper,p.quantity FROM prices p JOIN snapshots s ON s.id=p.snapshot_id WHERE p.item_id=? AND s.captured_at>=? ORDER BY s.captured_at''',(item_id,int(time.time())-days*86400)).fetchall()
