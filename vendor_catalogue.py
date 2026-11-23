"""ForeverDB vendor inventories: preserve provenance and unknown stock status."""
import time
import requests

BASE='https://foreverdb.net/api/v1/vendors'

def _payload(value,kind):
    data=value.get('data',value) if isinstance(value,dict) else value
    if isinstance(data,dict):
        for key in (kind,'results','items','vendors','inventory','sells','stock'):
            if isinstance(data.get(key),list):return data[key]
    if isinstance(data,list):return data
    raise ValueError('Unexpected ForeverDB '+kind+' response structure')

def _id(obj):
    if isinstance(obj,dict):
        for key in ('id','npcId','npc_id','vendorId','vendor_id'):
            if obj.get(key) is not None:
                try:return int(obj[key])
                except (ValueError,TypeError):pass
    return None

def _item_id(obj):
    if not isinstance(obj,dict):return None
    for key in ('itemId','item_id','id'):
        if obj.get(key) is not None:
            try:return int(obj[key])
            except (ValueError,TypeError):pass
    nested=obj.get('item')
    return _item_id(nested) if isinstance(nested,dict) else None

def stock_type(obj):
    """Only classify explicit signals. Zero maxcount convention is not assumed."""
    if not isinstance(obj,dict):return 'unknown'
    for key in ('limitedStock','limited_stock','isLimitedStock','limited'):
        if type(obj.get(key)) is bool:return 'limited' if obj[key] else 'unlimited'
    for key in ('unlimitedStock','unlimited_stock','isUnlimitedStock'):
        if type(obj.get(key)) is bool:return 'unlimited' if obj[key] else 'limited'
    for key in ('stockType','stock_type','availability'):
        val=obj.get(key)
        if isinstance(val,str):
            val=val.strip().lower().replace('_',' ').replace('-',' ')
            if val in ('unlimited','unlimited stock','infinite'):return 'unlimited'
            if val in ('limited','limited stock'):return 'limited'
    return 'unknown'

def seen_status(obj):
    if not isinstance(obj,dict):return 'unknown'
    for key in ('seenInForever','seen_in_forever'):
        if type(obj.get(key)) is bool:return 'forever' if obj[key] else 'classic'
    for key in ('source','dataSource','data_source'):
        val=obj.get(key)
        if isinstance(val,dict):val=val.get('type',val.get('name'))
        if isinstance(val,str):
            if 'forever' in val.lower():return 'forever'
            if 'classic' in val.lower() or 'cmangos' in val.lower():return 'classic'
    return 'unknown'

def parse_vendor(vendor,detail):
    vendor_id=_id(vendor) or _id(detail.get('data',detail) if isinstance(detail,dict) else {})
    if vendor_id is None:return []
    payload=detail.get('data',detail) if isinstance(detail,dict) else detail
    if not isinstance(payload,dict):return []
    inventory=None
    for key in ('items','inventory','sells','stock','vendorItems'):
        if isinstance(payload.get(key),list):inventory=payload[key];break
    if inventory is None:raise ValueError('Vendor inventory missing for NPC '+str(vendor_id))
    provenance=seen_status(payload)
    if provenance=='unknown':provenance=seen_status(vendor)
    rows=[]
    for obj in inventory:
        ident=_item_id(obj)
        if ident is None:continue
        stock=stock_type(obj)
        if stock=='unknown' and isinstance(obj.get('stock'),dict):stock=stock_type(obj['stock'])
        source=seen_status(obj)
        if source=='unknown':source=provenance
        price=None
        for key in ('buyPrice','buy_price','purchasePrice','purchase_price','vendorPrice','vendor_price'):
            value=obj.get(key)
            if isinstance(value,dict):value=value.get('copper',value.get('amount'))
            try:
                if value is not None and int(value)>0:price=int(value);break
            except (ValueError,TypeError):pass
        rows.append((ident,vendor_id,stock,source,price) if price is not None else (ident,vendor_id,stock,source))
    return rows

def fetch_vendors(settings,progress=None):
    key=settings.get('foreverdb_key','').strip()
    if not key:raise ValueError('Enter your ForeverDB API key in Settings')
    session=requests.Session();session.headers.update({'X-API-Key':key,'User-Agent':'ForeverMarketTracker/1.2.2 (desktop; data credited to ForeverDB.net)'})
    def get(url,params=None):
        for attempt in range(4):
            response=session.get(url,params=params,timeout=60)
            if response.status_code==429 and attempt<3:
                try:delay=min(90,max(1,int(response.headers.get('Retry-After','5'))))
                except ValueError:delay=5
                time.sleep(delay);continue
            response.raise_for_status();return response.json()
    vendors=[];offset=0;total=None
    while True:
        response=get(BASE,{'limit':100,'offset':offset});batch=_payload(response,'vendors')
        meta=response.get('meta',{}) if isinstance(response,dict) else {}
        if isinstance(meta,dict) and meta.get('total') is not None:total=int(meta['total'])
        if not batch:
            if total is not None and offset<total:raise ValueError('Vendor listing ended early')
            break
        vendors.extend(batch);offset+=len(batch)
        if progress:progress('Listing vendors',offset,total or 0)
        if total is not None and offset>=total:break
        if len(batch)<100:break
        if offset>100000:raise ValueError('Too many vendor records')
        time.sleep(.12)
    if not vendors:raise ValueError('ForeverDB returned no vendors')
    records=[]
    for index,vendor in enumerate(vendors,1):
        ident=_id(vendor)
        if ident is None:continue
        detail=get(BASE+'/'+str(ident));records.extend(parse_vendor(vendor,detail))
        if progress:progress('Fetching vendor inventories',index,len(vendors))
        time.sleep(.12)
    if not records:raise ValueError('No vendor inventory records found; nothing changed')
    return records,len(vendors)

def migrate(db):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS vendor_inventory (
            item_id INTEGER NOT NULL, vendor_id INTEGER NOT NULL,
            stock_type TEXT NOT NULL CHECK(stock_type IN ('limited','unlimited','unknown')),
            provenance TEXT NOT NULL, PRIMARY KEY(item_id,vendor_id))""")
        db.execute('CREATE INDEX IF NOT EXISTS idx_vendor_inventory_stock ON vendor_inventory(stock_type,item_id)')
        if 'purchase_copper' not in {r[1] for r in db.execute('PRAGMA table_info(vendor_inventory)')}:
            db.execute('ALTER TABLE vendor_inventory ADD COLUMN purchase_copper INTEGER')

def save_inventory(db,rows):
    migrate(db)
    with db:
        db.execute('DELETE FROM vendor_inventory')
        db.executemany('INSERT OR REPLACE INTO vendor_inventory(item_id,vendor_id,stock_type,provenance,purchase_copper) VALUES (?,?,?,?,?)',[tuple(r)+(None,) if len(r)==4 else tuple(r) for r in rows])
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('vendor_inventory_refreshed',?)",(str(int(time.time())),))
    return len(rows)

def vendor_classification(db):
    migrate(db)
    return db.execute("""SELECT stock_type,COUNT(DISTINCT item_id) FROM vendor_inventory
        GROUP BY stock_type""").fetchall()
