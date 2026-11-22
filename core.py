"""Local market history and auction snapshot processing."""
import json, sqlite3, statistics, time
from pathlib import Path

APP_DIR = Path.home() / 'AppData' / 'Local' / 'ForeverMarketTracker' if __import__('os').name == 'nt' else Path.home() / '.forever_market_tracker'
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / 'market.sqlite3'
SETTINGS_PATH = APP_DIR / 'settings.json'

def load_settings():
    defaults = {'region':'eu','house_id':'','realm_id':'','namespace':'dynamic-forever-eu','auction_url':'','foreverdb_url':'','foreverdb_key':'','client_id':'2659c616a4cc4e4e85ba016f1e0d20b6','client_secret':'','interval_minutes':60,'catalogue_days':30,'ah_cut_percent':5}
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
    columns={r[1] for r in db.execute('PRAGMA table_info(prices)')}
    for column in ('cheap10_unit_copper','cheap20_unit_copper'):
        if column not in columns: db.execute(f'ALTER TABLE prices ADD COLUMN {column} INTEGER')
    item_columns={r[1] for r in db.execute('PRAGMA table_info(items)')}
    if 'quality' not in item_columns: db.execute('ALTER TABLE items ADD COLUMN quality INTEGER')
    db.commit()
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
        if not isinstance(item_id,int) or not isinstance(qty,(int,float)) or qty<=0: continue
        total=auction.get('buyout')
        unit=auction.get('unit_price')
        if unit is None and isinstance(total,int) and total>0: unit=(total+qty-1)//qty
        if not isinstance(unit,(int,float)) or unit<=0: continue
        by_item.setdefault(item_id,[]).append((int(unit),int(qty)))
    return by_item

def weighted_median(entries):
    ordered=sorted(entries)
    total=sum(q for _,q in ordered)
    running=0
    for price,q in ordered:
        running+=q
        if running*2>=total:return price
    return 0

def cheapest_fraction(entries, fraction):
    """Quantity-weighted mean of the cheapest fraction of units, rounded to copper.

    Uses a fractional final unit to avoid upward bias at tiny volumes.
    """
    if not 0 < fraction <= 1: raise ValueError('fraction must be between 0 and 1')
    total=sum(q for _,q in entries)
    if total <= 0: return 0
    remaining=total*fraction
    cost=0.0
    for price,qty in sorted(entries):
        taken=min(remaining,qty)
        cost+=price*taken
        remaining-=taken
        if remaining <= 1e-9:break
    return int(cost/(total*fraction)+0.5)

def store_snapshot(db,payload,source='Blizzard API'):
    data=parse_auctions(payload)
    if not data: raise ValueError('No usable buyout auctions found; refusing to store empty snapshot')
    columns={r[1] for r in db.execute('PRAGMA table_info(prices)')}
    for column in ('cheap10_unit_copper','cheap20_unit_copper'):
        if column not in columns: db.execute(f'ALTER TABLE prices ADD COLUMN {column} INTEGER')
    with db:
        cur=db.execute('INSERT INTO snapshots(captured_at,source,auction_count) VALUES (?,?,?)',(int(time.time()),source,len(payload['auctions'])))
        sid=cur.lastrowid
        db.executemany('INSERT INTO prices (snapshot_id,item_id,min_unit_copper,median_unit_copper,quantity,listings,cheap10_unit_copper,cheap20_unit_copper) VALUES (?,?,?,?,?,?,?,?)',[(sid,item,min(p for p,_ in entries),weighted_median(entries),sum(q for _,q in entries),len(entries),cheapest_fraction(entries,.10),cheapest_fraction(entries,.20)) for item,entries in data.items()])
        db.executemany("INSERT OR IGNORE INTO items(item_id,name,updated_at) VALUES (?, ?, ?)",[(item,f'Item #{item}',int(time.time())) for item in data])
    return len(data)

ITEM_CLASSES = {0:'Consumables',1:'Containers',2:'Weapons',3:'Gems',4:'Armor',5:'Reagents',6:'Projectiles',7:'Trade Goods',8:'Generic',9:'Recipes',10:'Currency',11:'Quivers',12:'Quest Items',13:'Keys',14:'Permanent',15:'Miscellaneous',16:'Glyphs'}
WEAPON_SUBCLASSES = {0:'Axes (1H)',1:'Axes (2H)',2:'Bows',3:'Guns',4:'Maces (1H)',5:'Maces (2H)',6:'Polearms',7:'Swords (1H)',8:'Swords (2H)',10:'Staves',13:'Fist Weapons',15:'Daggers',16:'Thrown',18:'Crossbows',19:'Wands',20:'Fishing Poles'}
ARMOR_SUBCLASSES = {0:'Miscellaneous',1:'Cloth',2:'Leather',3:'Mail',4:'Plate',6:'Shields',7:'Librams',8:'Idols',9:'Totems'}
TRADE_SUBCLASSES = {0:'Trade Goods',1:'Parts',2:'Explosives',3:'Devices',4:'Jewelcrafting',5:'Cloth',6:'Leather',7:'Metal & Stone',8:'Meat',9:'Herbs',10:'Elemental',11:'Other',12:'Enchanting',13:'Materials'}

def _number_or_none(value):
    if isinstance(value,dict): value=value.get('id',value.get('value'))
    try: return int(value)
    except (ValueError,TypeError): return None

def _category(obj):
    cls=obj.get('classId',obj.get('class_id',obj.get('itemClass',obj.get('item_class',obj.get('class')))))
    sub=obj.get('subclassId',obj.get('subclass_id',obj.get('subclass',obj.get('item_subclass'))))
    cls_id=_number_or_none(cls); sub_id=_number_or_none(sub)
    category=ITEM_CLASSES.get(cls_id)
    if category is None:
        raw=obj.get('category') or cls
        category=raw.get('name') if isinstance(raw,dict) else raw
    if not isinstance(category,str) or not category.strip():category='Uncategorised'
    subclass={2:WEAPON_SUBCLASSES,4:ARMOR_SUBCLASSES,7:TRADE_SUBCLASSES}.get(cls_id,{}).get(sub_id)
    if not subclass:
        raw=obj.get('subcategory') or sub
        subclass=raw.get('name') if isinstance(raw,dict) else raw
    if not isinstance(subclass,str):subclass=''
    return category,subclass

QUALITY_NAMES = {0:'Poor',1:'Common',2:'Uncommon',3:'Rare',4:'Epic',5:'Legendary',6:'Artifact',7:'Heirloom'}
QUALITY_COLORS = {0:'#9D9D9D',1:'#E5EDF6',2:'#1EFF00',3:'#0070DD',4:'#A335EE',5:'#FF8000',6:'#E6CC80',7:'#00CCFF'}

def item_quality(obj):
    """Parse ForeverDB quality if supplied; missing/unknown remains NULL."""
    for key in ('quality','itemQuality','item_quality','rarity'):
        if key not in obj: continue
        raw=obj[key]
        if isinstance(raw,dict): raw=raw.get('id',raw.get('value',raw.get('quality')))
        if isinstance(raw,str) and not raw.strip().isdigit():
            inverse={name.lower():num for num,name in QUALITY_NAMES.items()}
            return inverse.get(raw.strip().lower())
        number=_number_or_none(raw)
        return number if number in QUALITY_NAMES else None
    return None

def quality_for_items(db,item_ids):
    """Read qualities in one query; absent values intentionally have no rarity colour."""
    ids=list(dict.fromkeys(item_ids))
    if not ids:return {}
    result={}
    for start in range(0,len(ids),900):
        batch=ids[start:start+900]
        marks=','.join('?' for _ in batch)
        result.update(db.execute(f'SELECT item_id,quality FROM items WHERE item_id IN ({marks})',batch).fetchall())
    return result

def import_catalogue(db,items):
    if 'quality' not in {r[1] for r in db.execute('PRAGMA table_info(items)')}:
        db.execute('ALTER TABLE items ADD COLUMN quality INTEGER')
    rows=[]
    now=int(time.time())
    for obj in items:
        if not isinstance(obj,dict):continue
        item_id=_number_or_none(obj.get('id',obj.get('item_id')))
        if item_id is None:continue
        name=obj.get('name') or f'Item #{item_id}'
        if isinstance(name,dict):name=name.get('en_US') or name.get('enGB') or next(iter(name.values()),f'Item #{item_id}')
        category,subcategory=_category(obj)
        rows.append((item_id,str(name),category,subcategory,now,item_quality(obj)))
    if not rows:raise ValueError('No usable item records; catalogue refresh aborted')
    with db:
        db.executemany("INSERT INTO items (item_id,name,category,subcategory,updated_at,quality) VALUES (?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET name=excluded.name,category=excluded.category,subcategory=excluded.subcategory,updated_at=excluded.updated_at,quality=COALESCE(excluded.quality,items.quality)",rows)
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('catalogue_refreshed',?)",(str(now),))
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
