"""Outlier-resistant historical asking-price references (not executed trades)."""
import statistics

def isolated_spikes(rows, price_index=1, ratio=1.65, neighbour_tolerance=.30):
    """Detect one-observation reversals; keep sustained changes and ordinary volatility.

    Rows are ordered (timestamp, price, ...). A spike is only excluded when its
    two immediate neighbours agree closely and both bracket a pronounced excursion.
    """
    ordered=sorted(enumerate(rows),key=lambda p:p[1][0]); excluded=set()
    for i in range(1,len(ordered)-1):
        idx,row=ordered[i]
        # Reversals must be close in time; weekly seasonality is not a spike.
        if row[0]-ordered[i-1][1][0]>8*3600 or ordered[i+1][1][0]-row[0]>8*3600:continue
        before=ordered[i-1][1][price_index];after=ordered[i+1][1][price_index]
        value=row[price_index]
        if not all(isinstance(x,(int,float)) and x>0 for x in (before,after,value)):continue
        if max(before,after)/min(before,after)>1+neighbour_tolerance:continue
        reference=statistics.median((before,after))
        if value>=reference*ratio or value<=reference/ratio:excluded.add(idx)
    return excluded

def conservative_resale(prices):
    """Lower quartile of historical market-median asking prices, not a peak."""
    values=sorted(int(p) for p in prices if p and p>0)
    if not values:return None
    return values[max(0,(len(values)-1)//4)]
