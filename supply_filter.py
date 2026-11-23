"""Latest and historical-average AH listed-unit filtering (not sales)."""
import time

def average_quantities(db, item_ids, days):
    ids=list(dict.fromkeys(int(x) for x in item_ids))
    result={}
    for start in range(0,len(ids),700):
        batch=ids[start:start+700]
        if not batch:continue
        marks=','.join('?' for _ in batch)
        sql=f"""SELECT p.item_id, AVG(p.quantity) FROM prices p JOIN snapshots s ON s.id=p.snapshot_id WHERE s.captured_at>=? AND p.item_id IN ({marks}) GROUP BY p.item_id"""
        result.update(db.execute(sql,[int(time.time())-int(days)*86400,*batch]).fetchall())
    return result

def eligible(db, records, minimum=100, mode='Latest snapshot', days=30, id_key='item_id', qty_key='supply'):
    minimum=max(0,int(minimum))
    if mode=='Historical average':
        avgs=average_quantities(db,[r[id_key] for r in records],days)
        return [{**r,'filter_quantity':avgs.get(r[id_key],0)} for r in records if avgs.get(r[id_key],0)>=minimum]
    return [{**r,'filter_quantity':r[qty_key]} for r in records if r[qty_key]>=minimum]
