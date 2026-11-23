"""ForeverDB crafting recipe import and conservative AH/vendor profitability estimates."""
import json,time,requests

BASE='https://foreverdb.net/api/v1/professions'
CRAFTING=('alchemy','blacksmithing','enchanting','engineering','leatherworking','tailoring','cooking','first-aid')

def migrate(db):
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS craft_recipes (profession TEXT NOT NULL, recipe_id INTEGER NOT NULL, name TEXT NOT NULL, output_item_id INTEGER, output_quantity INTEGER NOT NULL, skill INTEGER, reagents_json TEXT NOT NULL, PRIMARY KEY(profession,recipe_id))')
        db.execute('CREATE INDEX IF NOT EXISTS idx_craft_output ON craft_recipes(output_item_id)')

def _data(payload):
    return payload.get('data',payload) if isinstance(payload,dict) else payload

def _list(payload,keys):
    obj=_data(payload)
    if isinstance(obj,list):return obj
    if isinstance(obj,dict):
        for key in keys:
            if isinstance(obj.get(key),list):return obj[key]
    raise ValueError('Unexpected ForeverDB profession response: missing list '+str(keys))

def _id(value):
    if isinstance(value,dict):value=value.get('id',value.get('itemId',value.get('item_id')))
    try:return int(value)
    except (ValueError,TypeError):return None

def _positive(value,default=1):
    try:return max(1,int(value))
    except (TypeError,ValueError):return default

def normalize_recipe(profession,obj):
    if not isinstance(obj,dict):return None
    rid=_id(obj.get('id',obj.get('recipeId',obj.get('spellId'))))
    if rid is None:return None
    output=obj.get('output',obj.get('craftedItem',obj.get('result',obj.get('creates'))))
    output_id=_id(obj.get('outputItemId',obj.get('createdItemId',output)))
    if output_id is None and isinstance(output,dict):output_id=_id(output.get('item',output))
    if output_id is None:return None  # Non-AH-enchant spells cannot be sold as an item.
    output_qty=_positive(obj.get('outputQuantity',obj.get('createdCount',output.get('quantity',1) if isinstance(output,dict) else 1)))
    ingredients=obj.get('reagents',obj.get('ingredients',obj.get('materials')))
    if not isinstance(ingredients,list):return None
    reagents=[]
    for part in ingredients:
        if not isinstance(part,dict):return None
        item=_id(part.get('itemId',part.get('item_id',part.get('item'))))
        if item is None:return None
        reagents.append([item,_positive(part.get('quantity',part.get('count',part.get('amount',1))))])
    if not reagents:return None
    skill=obj.get('requiredSkill',obj.get('skillLevel',obj.get('skill')))
    if isinstance(skill,dict):skill=skill.get('required',skill.get('level'))
    try:skill=int(skill)
    except (TypeError,ValueError):skill=None
    return (profession,rid,str(obj.get('name',f'Recipe #{rid}')),output_id,output_qty,skill,json.dumps(reagents))

def fetch_professions(settings,progress=None):
    key=settings.get('foreverdb_key','').strip()
    if not key:raise ValueError('Enter your ForeverDB API key in Settings')
    session=requests.Session();session.headers.update({'X-API-Key':key,'User-Agent':'ForeverMarketTracker/1.2.4 (ForeverDB.net credited)'})
    def get(url,params=None):
        for attempt in range(4):
            response=session.get(url,params=params,timeout=60)
            if response.status_code==429 and attempt<3:
                try:delay=min(90,max(1,int(response.headers.get('Retry-After','5'))))
                except (ValueError,TypeError):delay=5
                time.sleep(delay);continue
            response.raise_for_status();return response.json()
    listing=_list(get(BASE),('professions','results','items'))
    available={str(x.get('slug',x.get('name',''))).lower().replace(' ','-'):x for x in listing if isinstance(x,dict)}
    slugs=[s for s in CRAFTING if s in available]
    if not slugs:raise ValueError('No matching crafting professions in ForeverDB response')
    all_rows=[];counts={}
    for index,slug in enumerate(slugs):
        offset=0;total=None;seen=set();count=0
        while True:
            payload=get(BASE+'/'+slug,{'limit':100,'offset':offset})
            rows=_list(payload,('recipes','results','items'))
            meta=payload.get('meta',{}) if isinstance(payload,dict) else {}
            if isinstance(meta,dict) and meta.get('total') is not None:total=int(meta['total'])
            if not rows:
                if total is not None and offset<total:raise ValueError(slug+' recipe listing ended early')
                break
            for item in rows:
                parsed=normalize_recipe(slug,item)
                if parsed and parsed[1] not in seen:all_rows.append(parsed);seen.add(parsed[1]);count+=1
            offset+=len(rows)
            if progress:progress(f'{slug}: {offset:,} recipes checked',index*100+min(99,int(100*offset/max(total or offset,1))),len(slugs)*100)
            if total is not None and offset>=total:break
            if len(rows)<100:break
            if offset>100000:raise ValueError('Too many recipes in '+slug)
            time.sleep(.12)
        counts[slug]=count
        if progress:progress(f'{slug} complete ({count:,} usable recipes)',(index+1)*100,len(slugs)*100)
    if not all_rows:raise ValueError('No usable craft recipes found; original data retained. Inspect ForeverDB schema.')
    return all_rows,counts

def save_recipes(db,rows):
    if not rows:raise ValueError('Refusing empty recipe import')
    migrate(db)
    with db:
        db.execute('DELETE FROM craft_recipes')
        db.executemany('INSERT OR REPLACE INTO craft_recipes VALUES (?,?,?,?,?,?,?)',rows)
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('professions_refreshed',?)",(str(int(time.time())),))
    return len(rows)

def latest_prices(db):
    return {r[0]:(r[1],r[2],r[3]) for r in db.execute('''SELECT p.item_id,p.min_unit_copper,p.median_unit_copper,p.quantity FROM prices p JOIN (SELECT item_id,MAX(snapshot_id) AS sid FROM prices GROUP BY item_id) q ON p.item_id=q.item_id AND p.snapshot_id=q.sid''')}

def profitability(db,profession,cut=5):
    migrate(db);prices=latest_prices(db)
    names=dict(db.execute('SELECT item_id,name FROM items'))
    # Explicit NPC purchase prices only; unknown vendor cost is not assumed free.
    from vendor_catalogue import migrate as vendor_migrate
    vendor_migrate(db)
    vendor={r[0]:r[1] for r in db.execute('SELECT item_id,MIN(purchase_copper) FROM vendor_inventory WHERE purchase_copper>0 GROUP BY item_id')}
    results=[]
    for prof,rid,name,output,qty,skill,raw in db.execute('SELECT * FROM craft_recipes WHERE profession=?',(profession,)):
        detail=[];total=0;missing=[]
        for item,count in json.loads(raw):
            quote=prices.get(item)
            ah_unit=(quote[1] if quote and quote[1]>0 else quote[0] if quote and quote[0]>0 else None)
            vendor_unit=vendor.get(item)
            if ah_unit is None and vendor_unit is None:missing.append(names.get(item,f'Item #{item}'));continue
            unit=min(x for x in (ah_unit,vendor_unit) if x is not None)
            source='NPC vendor' if vendor_unit is not None and unit==vendor_unit else 'AH'
            total+=unit*count
            detail.append((names.get(item,f'Item #{item}'),count,unit,source))
        sell=prices.get(output)
        if missing or not sell or sell[1]<=0:
            results.append(dict(name=name,recipe_id=rid,skill=skill,output=output,quantity=qty,materials=detail,missing=missing or (['Output AH price'] if not sell else []),cost=None,price=None,profit=None,roi=None,supply=sell[2] if sell else 0));continue
        gross=sell[1]*qty
        net=int(gross*(100-cut)/100)-total
        results.append(dict(name=name,recipe_id=rid,skill=skill,output=output,quantity=qty,materials=detail,missing=[],cost=total,price=sell[1],profit=net,roi=100*net/total if total else None,supply=sell[2]))
    return results
