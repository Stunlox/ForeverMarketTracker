"""Rank observed category-wide timing differences with explicit confidence labels."""
import datetime as dt
import statistics
from zoneinfo import ZoneInfo
from market_timing import DAYS,market_items,trade_goods,observations,analyse
UK=ZoneInfo('Europe/London')

def slot_name(slot):return f'{DAYS[slot[0]]} {slot[1]:02d}:00'

def confidence_label(dates,samples,weeks):
    if dates>=14 and samples>=6 and weeks>=3:return 'High'
    if dates>=7 and samples>=3 and weeks>=2:return 'Good'
    if dates>=3 and samples>=2:return 'Moderate'
    return 'Low data'

def temporary_spike_indices(rows, ratio=2.5):
    """Remove isolated >2.5x upward/downward excursions that immediately revert.

    Uses adjacent snapshots only; a sustained change is never labelled a reversal.
    """
    ordered=sorted(enumerate(rows), key=lambda pair:pair[1][0])
    bad=set()
    for pos in range(1,len(ordered)-1):
        original,row=ordered[pos]
        before=ordered[pos-1][1][5] if len(ordered[pos-1][1])>5 else None
        after=ordered[pos+1][1][5] if len(ordered[pos+1][1])>5 else None
        price=row[5] if len(row)>5 else None
        if not before or not after or not price:continue
        baseline=statistics.median((before,after))
        if max(before,after)/min(before,after)>1.35:continue
        if price>=baseline*ratio or price<=baseline/ratio:bad.add(original)
    return bad

def top_deals(db,days=90,min_supply=100,cut_pct=5,limit=40,
              min_dates=2,min_slot_samples=1,min_weeks=1,category='Trade Goods',
              min_profit_gold=0,exclude_spikes=True):
    """Early *provisional* price signals; snapshots are listings, not completed sales."""
    candidates=[];checked=0
    for item_id,name,subcategory,current_supply,current_low in (trade_goods(db,min_supply) if category=='Trade Goods' else market_items(db,category,min_supply)):
        checked+=1
        rows=[r for r in observations(db,item_id,days) if len(r)>5 and r[5] is not None and r[5]>0]
        if exclude_spikes:
            excluded=temporary_spike_indices(rows)
            rows=[r for index,r in enumerate(rows) if index not in excluded]
        dates={dt.datetime.fromtimestamp(r[0],UK).date() for r in rows}
        if len(dates)<min_dates:continue
        cells=analyse(rows,UK,min_samples=min_slot_samples,metric='cheap10')
        weeks={}
        for r in rows:
            when=dt.datetime.fromtimestamp(r[0],UK)
            weeks.setdefault((when.weekday(),when.hour),set()).add((when.isocalendar().year,when.isocalendar().week))
        eligible=[(slot,stats) for slot,stats in cells.items()
                  if stats['count']>=min_slot_samples and len(weeks.get(slot,set()))>=min_weeks]
        if len(eligible)<2:continue
        buy_slot,buy=min(eligible,key=lambda x:x[1]['median_price'])
        sell_slot,sell=max(eligible,key=lambda x:x[1]['median_price'])
        buy_price=buy['median_price'];sell_price=sell['median_price']
        if buy_slot==sell_slot or buy_price<=0 or sell_price<=buy_price:continue
        margin=(sell_price*(1-cut_pct/100)-buy_price)/buy_price*100
        if margin<=0 or (sell_price*(1-cut_pct/100)-buy_price)<min_profit_gold*10000:continue
        samples=min(buy['count'],sell['count'])
        span_weeks=min(len(weeks[buy_slot]),len(weeks[sell_slot]))
        confidence=confidence_label(len(dates),samples,span_weeks)
        # Low-evidence opportunities remain visible but rank below stronger signals
        evidence_factor={'Low data':.25,'Moderate':.5,'Good':.8,'High':1.0}[confidence]
        score=margin*min(1,current_supply/1000)**.5*evidence_factor
        candidates.append({'item_id':item_id,'name':name,'subcategory':subcategory,
            'buy_time':slot_name(buy_slot),'sell_time':slot_name(sell_slot),
            'buy_price':buy_price,'sell_price':sell_price,'margin_pct':margin,
            'spread_pct':(sell_price-buy_price)/buy_price*100,
            'current_supply':current_supply,'buy_samples':buy['count'],
            'sell_samples':sell['count'],'buy_weeks':len(weeks[buy_slot]),
            'sell_weeks':len(weeks[sell_slot]),'confidence':confidence,
            'score':score,'dates':len(dates),'snapshots':len(rows)})
    candidates.sort(key=lambda x:(-x['score'],-x['margin_pct'],x['name'].casefold()))
    return candidates[:max(1,min(300,int(limit)))],checked
