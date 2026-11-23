"""Persistent, user-controlled trading exclusions. Vendor flags require explicit metadata."""
def migrate(db):
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS item_exclusions (item_id INTEGER PRIMARY KEY, reason TEXT NOT NULL DEFAULT 'Manual', added_at INTEGER NOT NULL DEFAULT (strftime('%s','now')))")
        db.execute("CREATE TABLE IF NOT EXISTS vendor_items (item_id INTEGER PRIMARY KEY, source TEXT NOT NULL)")

def exclude(db,item_id,reason='Manual'):
    migrate(db)
    with db: db.execute('INSERT INTO item_exclusions(item_id,reason) VALUES (?,?) ON CONFLICT(item_id) DO UPDATE SET reason=excluded.reason',(int(item_id),reason))

def restore(db,item_id):
    with db: db.execute('DELETE FROM item_exclusions WHERE item_id=?',(int(item_id),))

def excluded_ids(db,include_vendor=True,include_unlimited=False,include_limited=False):
    if db is None:return set()
    migrate(db)
    result={r[0] for r in db.execute('SELECT item_id FROM item_exclusions')}
    if include_vendor:result.update(r[0] for r in db.execute('SELECT item_id FROM vendor_items'))
    from vendor_catalogue import migrate as migrate_vendor
    migrate_vendor(db)
    # Default: omit confirmed vendor items, but do not silently omit unknown stock.
    if not include_unlimited:
        result.update(r[0] for r in db.execute("SELECT item_id FROM vendor_inventory WHERE stock_type='unlimited'"))
    if not include_limited:
        result.update(r[0] for r in db.execute("SELECT item_id FROM vendor_inventory WHERE stock_type='limited'"))
    return result

def vendor_source(obj):
    """Only accept explicit vendor-only flags, not guesses from names or price."""
    if obj.get('vendorOnly') is True or obj.get('vendor_only') is True:return 'ForeverDB vendor-only flag'
    return None

def import_vendor_metadata(db,items):
    """Add verified vendor-only flags; do not erase prior evidence on incomplete imports."""
    from core import _number_or_none
    migrate(db)
    rows=[]
    for obj in items:
        if not isinstance(obj,dict):continue
        ident=_number_or_none(obj.get('id',obj.get('item_id')))
        source=vendor_source(obj)
        if ident is not None and source:rows.append((ident,source))
    with db:db.executemany('INSERT INTO vendor_items(item_id,source) VALUES (?,?) ON CONFLICT(item_id) DO UPDATE SET source=excluded.source',rows)
    return len(rows)
