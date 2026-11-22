"""Category-aware auction asking-price timing analysis."""
import datetime as dt
import statistics
from collections import defaultdict

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
TRADE_GOODS = ('trade goods','tradegoods')

def categories(db):
    rows=db.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND TRIM(category)<>'' ORDER BY category COLLATE NOCASE").fetchall()
    return [r[0] for r in rows]

def market_items(db, category='Trade Goods', min_quantity=100):
    """Latest snapshot's items in a selected category; All includes everything."""
    return db.execute('''SELECT i.item_id,i.name,i.subcategory,p.quantity,p.min_unit_copper
        FROM prices p JOIN items i ON i.item_id=p.item_id
        WHERE p.snapshot_id=(SELECT MAX(id) FROM snapshots)
        AND (?='All categories' OR LOWER(i.category)=LOWER(?)
             OR (?='Trade Goods' AND LOWER(i.category) IN ('trade goods','tradegoods')))
        AND p.quantity>=? ORDER BY i.name COLLATE NOCASE''',
        (category,category,category,min_quantity)).fetchall()

def trade_goods(db,min_quantity=100):
    return market_items(db,'Trade Goods',min_quantity)

def observations(db,item_id,days=90):
    cutoff=int(dt.datetime.now().timestamp())-days*86400
    return db.execute('''SELECT s.captured_at,p.min_unit_copper,p.median_unit_copper,
        p.quantity,p.listings,p.cheap10_unit_copper,p.cheap20_unit_copper
        FROM prices p JOIN snapshots s ON s.id=p.snapshot_id
        WHERE p.item_id=? AND s.captured_at>=? ORDER BY s.captured_at''',(item_id,cutoff)).fetchall()

def analyse(rows,timezone=dt.timezone.utc,min_samples=3,metric='cheap10'):
    cells=defaultdict(list)
    for row in rows:
        timestamp,lowest,median,quantity,listings=row[:5]
        cheap10=row[5] if len(row)>5 else None
        cheap20=row[6] if len(row)>6 else None
        selected={'lowest':lowest,'cheap10':cheap10,'cheap20':cheap20,'median':median}.get(metric)
        if selected is None or selected<=0 or quantity<=0:continue
        local=dt.datetime.fromtimestamp(timestamp,timezone)
        cells[(local.weekday(),local.hour)].append((selected,quantity,lowest))
    result={}
    for key,vals in cells.items():
        prices=[v[0] for v in vals]
        result[key]={'count':len(vals),'median_price':int(statistics.median(prices)),
            'median_quantity':int(statistics.median(v[1] for v in vals)),
            'median_lowest':int(statistics.median(v[2] for v in vals)),
            'price_spread':max(prices)-min(prices),'eligible':len(vals)>=min_samples}
    return result

def price_ratio(price,minimum,maximum):
    """None means no observed price variation; never imply cheapness from one price."""
    if maximum<=minimum:return None
    return max(0.0,min(1.0,(price-minimum)/(maximum-minimum)))

def summarize(cells,min_samples=1):
    eligible=[(key,value) for key,value in cells.items() if value['count']>=min_samples]
    if len(eligible)<2:return None
    low_key,low=min(eligible,key=lambda kv:kv[1]['median_price'])
    high_key,high=max(eligible,key=lambda kv:kv[1]['median_price'])
    if low_key==high_key or high['median_price']<=low['median_price']:return None
    return {'buy':low_key,'sell':high_key,'buy_price':low['median_price'],
        'sell_price':high['median_price'],'buy_supply':low['median_quantity'],
        'sell_supply':high['median_quantity'],'buy_samples':low['count'],
        'sell_samples':high['count'],'spread_pct':100*(high['median_price']-low['median_price'])/low['median_price']}
