"""Historical weekday/hour timing estimates for budget-planner candidates."""
from zoneinfo import ZoneInfo
from market_timing import observations,analyse
from simplified_market import temporary_spike_indices,slot_name
UK=ZoneInfo('Europe/London')

def item_timing(db,item_id,days=30):
    rows=[r for r in observations(db,item_id,days) if len(r)>5 and r[5] and r[5]>0]
    removed=temporary_spike_indices(rows)
    rows=[r for i,r in enumerate(rows) if i not in removed]
    if len(rows)<2:return ('Insufficient history','Insufficient history')
    cells=analyse(rows,UK,min_samples=1,metric='cheap10')
    if len(cells)<2:return ('Insufficient history','Insufficient history')
    buy=min(cells,key=lambda k:cells[k]['median_price'])
    sell=max(cells,key=lambda k:cells[k]['median_price'])
    if cells[buy]['median_price']>=cells[sell]['median_price']:return ('No clear pattern','No clear pattern')
    return (slot_name(buy),slot_name(sell))

def timing_for_items(db,item_ids,days=30):
    return {item_id:item_timing(db,item_id,days) for item_id in set(item_ids)}
