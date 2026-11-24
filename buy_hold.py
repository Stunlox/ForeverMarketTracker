"""Current acquisition vs repeated future UK selling windows; local data only."""
import datetime as dt
import time, math
from collections import defaultdict
from zoneinfo import ZoneInfo
from pricing_reference import isolated_spikes, conservative_resale
from exclusions import excluded_ids
from supply_filter import eligible
from investment import allocate
UK=ZoneInfo('Europe/London')

def windows(points, now, hours, buy, cut, roi):
    bad=isolated_spikes(points,1)|isolated_spikes(points,2)
    groups=defaultdict(dict)
    for i,(ts,cheap,median,qty) in enumerate(points):
        if i in bad or not cheap or not median or qty<=0:continue
        local=dt.datetime.fromtimestamp(ts,UK)
        # Conservative sale reference uses competitive asking prices, not market maxima.
        groups[(local.weekday(),local.hour//6)][local.date()]=groups[(local.weekday(),local.hour//6)].get(local.date(),[])+[cheap]
    import statistics
    choices=[];seen=set()
    for offset in range(1,hours+1):
        future=dt.datetime.fromtimestamp(now+offset*3600,UK)
        key=(future.weekday(),future.hour//6)
        if key in seen:continue
        seen.add(key)
        days=groups.get(key,{})
        if len(days)<2:continue
        price=conservative_resale([statistics.median(v) for v in days.values()])
        net=math.floor(price*(1-cut/100))-buy
        if net<=0 or net/buy*100<roi:continue
        choices.append((price,offset,future,len(days),key))
    return max(choices,key=lambda x:(x[0],-x[1])) if choices else None

def opportunities(db,budget,days=30,category='Trade Goods',cut_pct=5,include_unlimited=False,include_limited=False,min_quantity=100,quantity_mode='Latest snapshot',quality=None,hours=72,min_roi=5,now=None):
    now=time.time() if now is None else now
    latest=db.execute('SELECT id,captured_at FROM snapshots ORDER BY id DESC LIMIT 1').fetchone()
    if not latest:return [],None
    sid,stamp=latest
    if now-stamp>7200:return [],stamp
    blocked=excluded_ids(db,include_unlimited=include_unlimited,include_limited=include_limited)
    records=[]
    for ident,name,cat,q,qty,buy in db.execute('''SELECT i.item_id,i.name,i.category,i.quality,p.quantity,p.cheap10_unit_copper FROM prices p JOIN items i ON i.item_id=p.item_id WHERE p.snapshot_id=?''',(sid,)):
        if ident in blocked or not buy or qty<10 or (quality is not None and q!=quality):continue
        if category!='All categories' and cat.lower()!=category.lower() and not(category=='Trade Goods' and cat.lower()=='tradegoods'):continue
        records.append(dict(item_id=ident,name=name,category=cat,quality=q,supply=qty,buy=buy,affordable_supply=qty//10))
    records=eligible(db,records,min_quantity,quantity_mode,days)
    result=[]
    for r in records:
        points=db.execute('''SELECT s.captured_at,p.cheap10_unit_copper,p.median_unit_copper,p.quantity FROM prices p JOIN snapshots s ON s.id=p.snapshot_id WHERE p.item_id=? AND s.captured_at>=? AND s.captured_at<=? ORDER BY s.captured_at''',(r['item_id'],now-days*86400,now)).fetchall()
        w=windows(points,now,hours,r['buy'],cut_pct,min_roi)
        if not w:continue
        price,offset,future,count,key=w
        net=math.floor(price*(1-cut_pct/100))-r['buy']
        start=key[1]*6
        result.append(dict(r,resale=price,net_per_unit=net,margin=100*net/r['buy'],window=f'{future:%a %d %b} {start:02d}:00–{start+6:02d}:00',dates=count,snapshots=len(points),confidence='Good' if count>=4 else 'Moderate',hold=offset))
    result.sort(key=lambda r:(-r['margin'],-r['dates'],r['hold']))
    return allocate(budget,result,cut_pct),stamp
