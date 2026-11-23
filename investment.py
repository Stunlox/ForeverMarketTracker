"""Budget-aware, conservative *estimates* from aggregated AH snapshots.

Exact purchase tiers are not in the historical schema; estimates must not imply
that every unit can actually be bought at the observed cheapest price.
"""
import statistics,time,math
from simplified_market import temporary_spike_indices

def budget_quantity(budget_copper, unit_price_copper, supply):
    if budget_copper<=0 or unit_price_copper<=0 or supply<=0:return 0
    return max(0,min(int(supply),int(budget_copper)//int(unit_price_copper)))

def estimate(budget_copper,buy_price,sell_price,supply,cut_pct=5):
    qty=budget_quantity(budget_copper,buy_price,supply)
    cost=qty*buy_price
    proceeds=round(qty*sell_price*(1-cut_pct/100))
    return {'quantity':qty,'cost':cost,'net_proceeds':proceeds,'profit':proceeds-cost,
            'remaining':int(budget_copper)-cost}

def candidates(db,days=30,category='Trade Goods',min_supply=1,cut_pct=5,limit=300,include_all=False,search='',include_unlimited=False,include_limited=False):
    """Find latest snapshot items, using robust historical resale reference.

    Exclude one-off spikes and use the median of cleaned observations, not
    historical maxima. Returns opportunities; not evidence of actual sales.
    """
    cutoff=int(time.time())-days*86400
    sql='''SELECT i.item_id,i.name,i.category,i.quality,p.quantity,p.min_unit_copper,
        p.cheap10_unit_copper,p.cheap20_unit_copper,p.median_unit_copper
        FROM prices p JOIN items i ON i.item_id=p.item_id
        WHERE p.snapshot_id=(SELECT MAX(id) FROM snapshots)
        AND p.quantity>=? AND LOWER(i.name) LIKE ? AND (?='All categories' OR LOWER(i.category)=LOWER(?)
        OR (?='Trade Goods' AND LOWER(i.category) IN ('trade goods','tradegoods')))
        ORDER BY i.name COLLATE NOCASE'''
    items=db.execute(sql,(min_supply,"%"+search.casefold()+"%",category,category,category)).fetchall()
    result=[]
    # Query historical observations in one pass rather than one SQL call per item.
    ids=[r[0] for r in items];history={i:[] for i in ids}
    for offset in range(0,len(ids),800):
        batch=ids[offset:offset+800]
        if not batch:continue
        marks=','.join('?' for _ in batch)
        query=f'''SELECT p.item_id,s.captured_at,p.cheap10_unit_copper,p.median_unit_copper
            FROM prices p JOIN snapshots s ON s.id=p.snapshot_id
            WHERE s.captured_at>=? AND p.item_id IN ({marks}) ORDER BY s.captured_at'''
        for item_id,ts,cheap,median in db.execute(query,[cutoff,*batch]):
            if cheap and cheap>0:history[item_id].append((ts,cheap,median))
    for item_id,name,cat,quality,supply,low,cheap10,cheap20,median in items:
        points=history[item_id]
        if len(points)<3 and not include_all:continue
        # Spike detector accepts the observation tuple used by timing analysis.
        synthetic=[(ts,price,price,supply,1,price,price) for ts,price,_ in points]
        excluded=temporary_spike_indices(synthetic)
        cleaned=[point for i,point in enumerate(points) if i not in excluded]
        if len(cleaned)<3 and not include_all:continue
        distinct_dates=len({time.localtime(ts).tm_yday+(time.localtime(ts).tm_year*366) for ts,_,_ in cleaned})
        # Conservative reference from cleaned historical cheap-10% asking prices.
        resale=int(statistics.median([price for _,price,_ in cleaned])) if cleaned else int(median or low or 0)
        # Cheapest-10% metric is a proxy, not an executable order-book quote.
        buy=int(cheap10 or low or 0)
        if buy<=0 or (resale<=buy and not include_all):continue
        net_per_unit=round(resale*(1-cut_pct/100))-buy
        if net_per_unit<=0 and not include_all:continue
        result.append({'item_id':item_id,'name':name,'category':cat,'quality':quality,
            'supply':supply,'affordable_supply':max(1,math.floor(supply*.10)),'buy':buy,'resale':resale,'net_per_unit':net_per_unit,
            'margin':net_per_unit/buy*100,'snapshots':len(cleaned),'dates':distinct_dates,
            'confidence':'Insufficient data' if len(cleaned)<3 else 'Low data' if distinct_dates<3 else 'Moderate' if distinct_dates<7 else 'Good' if distinct_dates<14 else 'High'})
    from exclusions import excluded_ids
    blocked=excluded_ids(db,include_unlimited=include_unlimited,include_limited=include_limited)
    result=[r for r in result if r['item_id'] not in blocked]
    result.sort(key=lambda d:(-d['net_per_unit'],-d['margin']))
    return result[:max(1,int(limit)) if include_all else max(1,min(300,int(limit))) ]

def allocate(budget_copper,items,cut_pct=5,max_item_share=.35):
    """Greedy diversified proposal: never spend over budget or supply.

    A per-item allocation cap limits concentrated hypothetical investments.
    """
    remaining=int(budget_copper);result=[]
    for item in items:
        allocation=min(remaining,int(budget_copper*max_item_share))
        qty=budget_quantity(allocation,item['buy'],item['affordable_supply'])
        if not qty:continue
        purchase=estimate(allocation,item['buy'],item['resale'],qty,cut_pct)
        result.append({**item,**purchase})
        remaining-=purchase['cost']
        if remaining<=0:break
    return result
