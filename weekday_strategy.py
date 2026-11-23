"""Weekday-only evening-to-next-afternoon asking-price signals (UK local time)."""
from collections import defaultdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from statistics import median
import time

UK=ZoneInfo('Europe/London')

def slot(ts):
    d=datetime.fromtimestamp(ts,UK)
    if d.weekday()>=5:return None
    if 18<=d.hour<24 and d.weekday()<=3:return (d.date(),'buy')
    if 12<=d.hour<18 and d.weekday()>=1:return (d.date(),'sell')
    return None

def paired_signals(observations,cut_pct=5,min_pairs=3):
    """Observations: (item_id, unix_ts, cheap10_copper, quantity).

    Each pair must be a Mon-Thu evening followed by the NEXT calendar day's
    Tue-Fri afternoon. Weekends never participate, including Fri->Mon.
    """
    slots=defaultdict(list)
    for item_id,ts,price,quantity in observations:
        key=slot(ts)
        if key and price and price>0:
            day,kind=key
            slots[(item_id,day,kind)].append((int(price),int(quantity)))
    by_item=defaultdict(list)
    for item_id,day,kind in list(slots):
        if kind!='buy':continue
        following=day+timedelta(days=1)
        sells=slots.get((item_id,following,'sell'))
        if not sells:continue
        buys=slots[(item_id,day,'buy')]
        buy=median(p for p,q in buys)
        sell=median(p for p,q in sells)
        by_item[item_id].append((day,buy,sell,median(q for p,q in buys)))
    result={}
    for item_id,pairs in by_item.items():
        if len(pairs)<min_pairs:continue
        margins=[round(sell*(1-cut_pct/100))-buy for _,buy,sell,_ in pairs]
        positives=sum(m>0 for m in margins)
        buy=round(median(p[1] for p in pairs));sell=round(median(p[2] for p in pairs))
        net=round(sell*(1-cut_pct/100))-buy
        if net<=0 or positives/len(pairs)<.6:continue
        result[item_id]={'pairs':len(pairs),'wins':positives,'win_rate':positives/len(pairs),
                         'buy_reference':buy,'sell_reference':sell,'net_per_unit':net,
                         'median_buy_supply':median(p[3] for p in pairs),
                         'confidence':'Low data' if len(pairs)<5 else 'Moderate' if len(pairs)<10 else 'Good'}
    return result

def weekday_candidates(db,days=30,category='Trade Goods',min_quantity=100,quantity_mode='Latest snapshot',cut_pct=5,include_unlimited=False,include_limited=False,min_pairs=3):
    cutoff=int(time.time())-days*86400
    # Collect only the columns required for this strategy; chunking is unnecessary here.
    observations=db.execute('''SELECT p.item_id,s.captured_at,COALESCE(NULLIF(p.cheap10_unit_copper,0),p.min_unit_copper),p.quantity
        FROM prices p JOIN snapshots s ON s.id=p.snapshot_id WHERE s.captured_at>=?''',(cutoff,)).fetchall()
    signals=paired_signals(observations,cut_pct,min_pairs)
    if not signals:return []
    from exclusions import excluded_ids
    blocked=excluded_ids(db,include_unlimited=include_unlimited,include_limited=include_limited)
    # All quantities and current-price proxies are sourced from weekday snapshots.
    # Never use a Saturday/Sunday snapshot, even for the "latest" supply filter.
    weekday_obs=[(ident,ts,price,qty) for ident,ts,price,qty in observations
                 if datetime.fromtimestamp(ts,UK).weekday()<5]
    last_by_item={}
    qty_history=defaultdict(list)
    for ident,ts,price,qty in weekday_obs:
        qty_history[ident].append(qty)
        if ident not in last_by_item or ts>last_by_item[ident][0]:
            last_by_item[ident]=(ts,price,qty)
    item_info={r[0]:r[1:] for r in db.execute('SELECT item_id,name,category,quality FROM items')}
    latest=[(ident,*item_info[ident],qty,price) for ident,(ts,price,qty) in last_by_item.items()
            if ident in item_info and ident in signals]
    averages={ident:sum(values)/len(values) for ident,values in qty_history.items()} if quantity_mode=='Historical average' else {}
    output=[]
    for item_id,name,cat,quality,qty,price in latest:
        if item_id not in signals or item_id in blocked:continue
        if category!='All categories' and cat.casefold()!=category.casefold():continue
        supply=averages.get(item_id,0) if quantity_mode=='Historical average' else qty
        if supply<min_quantity:continue
        signal=signals[item_id]
        # Today's executable price is unknown; use observed cheapest 10% asking-price proxy.
        if not price or price<=0:continue
        net=round(signal['sell_reference']*(1-cut_pct/100))-price
        if net<=0:continue
        output.append({'item_id':item_id,'name':name,'quality':quality,'quantity':qty,'filter_quantity':supply,
                       'current_buy':price,'estimated_net_unit':net,**signal})
    output.sort(key=lambda r:(-r['win_rate'],-r['pairs'],-r['estimated_net_unit']))
    return output
