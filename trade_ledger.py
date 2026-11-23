"""Manual purchase/sale journal and conservative history-based sell guidance."""
import datetime as dt
import math
import statistics
import time
from zoneinfo import ZoneInfo
from market_timing import observations, analyse
from simplified_market import temporary_spike_indices, slot_name

UK=ZoneInfo('Europe/London')

def migrate(db):
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS trade_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity>0),
            buy_unit_copper INTEGER NOT NULL CHECK(buy_unit_copper>=0),
            bought_at INTEGER NOT NULL,
            sold INTEGER NOT NULL DEFAULT 0 CHECK(sold IN (0,1)),
            sell_unit_copper INTEGER,
            sold_at INTEGER,
            note TEXT NOT NULL DEFAULT '',
            CHECK (sold=0 OR (sell_unit_copper IS NOT NULL AND sell_unit_copper>=0))
        )""")
        db.execute('CREATE INDEX IF NOT EXISTS idx_trade_lots_item ON trade_lots(item_id)')

def save_lot(db,item_id,quantity,buy_unit_copper,sold=False,sell_unit_copper=None,note='',lot_id=None):
    migrate(db)
    item_id=int(item_id);quantity=int(quantity);buy_unit_copper=int(buy_unit_copper)
    if quantity<=0 or buy_unit_copper<0:raise ValueError('Enter a positive quantity and nonnegative purchase price')
    if not db.execute('SELECT 1 FROM items WHERE item_id=?',(item_id,)).fetchone():raise ValueError('Select an item from the catalogue')
    if sold:
        if sell_unit_copper is None or int(sell_unit_copper)<0:raise ValueError('Enter the selling price when marking an item sold')
        sell_unit_copper=int(sell_unit_copper)
    else:sell_unit_copper=None
    with db:
        if lot_id is None:
            cursor=db.execute('INSERT INTO trade_lots(item_id,quantity,buy_unit_copper,bought_at,sold,sell_unit_copper,sold_at,note) VALUES(?,?,?,?,?,?,?,?)',
                (item_id,quantity,buy_unit_copper,int(time.time()),int(sold),sell_unit_copper,int(time.time()) if sold else None,note.strip()))
            return cursor.lastrowid
        old=db.execute('SELECT sold,sold_at FROM trade_lots WHERE id=?',(lot_id,)).fetchone()
        if old is None:raise ValueError('Trade not found')
        sold_at=(old[1] or int(time.time())) if sold else None
        db.execute('UPDATE trade_lots SET item_id=?,quantity=?,buy_unit_copper=?,sold=?,sell_unit_copper=?,sold_at=?,note=? WHERE id=?',
            (item_id,quantity,buy_unit_copper,int(sold),sell_unit_copper,sold_at,note.strip(),lot_id))
        return lot_id

def delete_lot(db,lot_id):
    with db:db.execute('DELETE FROM trade_lots WHERE id=?',(lot_id,))

def lots(db):
    migrate(db)
    return db.execute("""SELECT t.id,t.item_id,i.name,i.quality,t.quantity,t.buy_unit_copper,t.bought_at,t.sold,t.sell_unit_copper,t.sold_at,t.note
        FROM trade_lots t LEFT JOIN items i ON i.item_id=t.item_id ORDER BY t.sold ASC,t.bought_at DESC,t.id DESC""").fetchall()

def realised_profit(quantity,buy_unit,sell_unit,cut_pct=5):
    return int(math.floor(quantity*sell_unit*(1-cut_pct/100)+0.5))-quantity*buy_unit

def sell_advice(db,item_id,paid_copper,cut_pct=5,days=30):
    """Suggest only repeated hours with prices above after-fee break-even.

    AH snapshots are asking prices, not sales. Never recommend an isolated peak.
    """
    if cut_pct>=100:raise ValueError('AH cut must be less than 100%')
    break_even=math.floor(paid_copper/(1-cut_pct/100))+1
    rows=[r for r in observations(db,item_id,days) if len(r)>5 and r[5] and r[5]>0]
    excluded=temporary_spike_indices(rows)
    clean=[r for i,r in enumerate(rows) if i not in excluded]
    if len(clean)<3:return {'status':'Insufficient history','message':'Not enough clean AH snapshots to estimate a selling window.', 'break_even':break_even,'reference':None,'window':None,'samples':len(clean)}
    prices=[int(r[2]) for r in clean if r[2] and r[2]>0]
    if not prices:return {'status':'Insufficient history','message':'No valid historical market asking prices.','break_even':break_even,'reference':None,'window':None,'samples':len(clean)}
    reference=int(statistics.median(prices))
    # Median metric for sale estimates, cheapest 10% for buy estimates.
    cells=analyse(clean,UK,min_samples=2,metric='median')
    candidates=[(slot,v) for slot,v in cells.items() if v['count']>=2 and v['median_price']>=break_even]
    candidates.sort(key=lambda pair:(-pair[1]['median_price'],-pair[1]['count']))
    if candidates:
        slot,entry=candidates[0]
        weeks={dt.datetime.fromtimestamp(r[0],UK).isocalendar()[:2] for r in clean if (dt.datetime.fromtimestamp(r[0],UK).weekday(),dt.datetime.fromtimestamp(r[0],UK).hour)==slot}
        status='Repeated window' if len(weeks)>=2 else 'Provisional window'
        return {'status':status,'message':f'{slot_name(slot)} (UK); {entry["count"]} observations across {len(weeks)} week(s). Historical asking prices only.',
            'break_even':break_even,'reference':reference,'window':slot_name(slot),'expected':entry['median_price'],'samples':len(clean)}
    if reference>=break_even:
        return {'status':'No reliable hour','message':'Typical asking prices clear break-even, but no specific hour has enough repeated profitable observations.',
            'break_even':break_even,'reference':reference,'window':None,'samples':len(clean)}
    return {'status':'Wait / reassess','message':'Historical median is below break-even and no repeated profitable selling hour was found.',
        'break_even':break_even,'reference':reference,'window':None,'samples':len(clean)}
