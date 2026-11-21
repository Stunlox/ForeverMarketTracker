"""Conservative ranked trade-goods timing opportunities; no fabricated recommendations."""
import datetime as dt
import statistics
from zoneinfo import ZoneInfo
from market_timing import DAYS, trade_goods, observations, analyse

UK = ZoneInfo('Europe/London')

def slot_name(slot):
    return f'{DAYS[slot[0]]} {slot[1]:02d}:00'

def top_deals(db, days=90, min_supply=100, cut_pct=5, limit=40,
              min_dates=14, min_slot_samples=3, min_weeks=3):
    """Rank repeatable observed opportunities, never infer trades from sparse data.

    Price is the median across snapshots of each snapshot's cheapest 10% unit-weighted
    average. Volume is current available quantity. Margin is an illustrative
    difference between asking-price proxies, not a realized trading profit.
    """
    candidates=[]
    checked=0
    for item_id,name,subcategory,current_supply,current_low in trade_goods(db,min_supply):
        checked+=1
        rows=[r for r in observations(db,item_id,days) if len(r)>5 and r[5] is not None and r[5]>0]
        dates={dt.datetime.fromtimestamp(r[0],UK).date() for r in rows}
        if len(dates)<min_dates:continue
        cells=analyse(rows,UK,min_samples=min_slot_samples,metric='cheap10')
        # Require samples across different calendar weeks; several scans in one day
        # are not sufficient to infer a recurring weekday pattern.
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
        if buy_slot==sell_slot or buy_price<=0:continue
        margin=(sell_price*(1-cut_pct/100)-buy_price)/buy_price*100
        if margin<=0:continue
        spread=(sell_price-buy_price)/buy_price*100
        # Favor supply and repeat observations, but never let volume alone outrank margin.
        score=margin*min(1,current_supply/1000)**0.5 * min(1,min(buy['count'],sell['count'])/6)**0.5
        confidence='Moderate' if min(buy['count'],sell['count'])>=6 and min(len(weeks[buy_slot]),len(weeks[sell_slot]))>=5 else 'Early'
        candidates.append({'item_id':item_id,'name':name,'subcategory':subcategory,
            'buy_time':slot_name(buy_slot),'sell_time':slot_name(sell_slot),
            'buy_price':buy_price,'sell_price':sell_price,'margin_pct':margin,
            'spread_pct':spread,'current_supply':current_supply,
            'buy_samples':buy['count'],'sell_samples':sell['count'],
            'buy_weeks':len(weeks[buy_slot]),'sell_weeks':len(weeks[sell_slot]),
            'confidence':confidence,'score':score,'dates':len(dates)})
    candidates.sort(key=lambda x:(-x['score'],-x['margin_pct'],x['name'].casefold()))
    return candidates[:limit],checked
