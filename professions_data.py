"""ForeverDB crafting recipe import and conservative AH/vendor profitability estimates."""
import json,time,requests
from collections import namedtuple
ReagentQuote=namedtuple('ReagentQuote','name count unit source item_id quality ah vendor stock')

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
    if isinstance(value,dict):
        for k in ('itemId','item_id','id','entry','itemID','spellId'):
            if value.get(k) is not None:return _id(value[k])
        return None
    try:return int(value)
    except (ValueError,TypeError):return None

def _positive(value,default=1):
    try:return max(1,int(value))
    except (TypeError,ValueError):return default

def _field(obj,*keys):
    if not isinstance(obj,dict):return None
    for k in keys:
        if obj.get(k) is not None:return obj[k]
    return None

def _item_id(value):
    if isinstance(value,dict):
        for key in ('item','itemId','item_id','createdItem','output','result','product'):
            if key in value and value[key] is not None:
                found=_item_id(value[key])
                if found is not None:return found
    return _id(value)

def _recipes(payload):
    obj=_data(payload)
    if isinstance(obj,list):return obj
    if isinstance(obj,dict):
        for key in ('recipes','results','items'):
            candidate=obj.get(key)
            if isinstance(candidate,list):return candidate
            if isinstance(candidate,dict):
                for sub in ('data','items','results','recipes'):
                    if isinstance(candidate.get(sub),list):return candidate[sub]
    raise ValueError('ForeverDB profession page missing recipe list; response keys: '+str(list(obj)[:20] if isinstance(obj,dict) else type(obj).__name__))

def recipe_rejection(obj):
    if not isinstance(obj,dict):return 'not a recipe object'
    if _id(_field(obj,'id','recipeId','recipe_id','spellId','spell_id')) is None and _id(_field(obj,'spell','recipe')) is None:return 'missing recipe/spell ID'
    output=_field(obj,'output','craftedItem','result','creates','makes','createdItem','produces','created','product')
    if _item_id(_field(obj,'outputItemId','output_item_id','createdItemId','created_item_id')) is None and _item_id(output) is None:return 'missing auctionable output item ID'
    ingredients=_field(obj,'reagents','ingredients','materials','requiredReagents')
    if isinstance(ingredients,dict):ingredients=_field(ingredients,'items','reagents','data','materials')
    if not isinstance(ingredients,list) or not ingredients:return 'missing reagent list'
    for part in ingredients:
        if not isinstance(part,dict) or _item_id(_field(part,'item','itemId','item_id','reagent','material')) is None:return 'unrecognised reagent item ID'
    return 'other invalid recipe'

def normalize_recipe(profession,obj):
    if not isinstance(obj,dict):return None
    rid=_id(_field(obj,'id','recipeId','recipe_id','spellId','spell_id')) or _id(_field(obj,'spell','recipe'))
    if rid is None:return None
    output=_field(obj,'output','craftedItem','result','creates','makes','createdItem','produces','created','product')
    output_id=_item_id(_field(obj,'outputItemId','output_item_id','createdItemId','created_item_id')) or _item_id(output)
    if output_id is None:return None
    output_qty=_positive(_field(obj,'outputQuantity','createdCount','outputCount','count') or _field(output,'count','quantity','min','minCount') or 1)
    ingredients=_field(obj,'reagents','ingredients','materials','requiredReagents')
    if isinstance(ingredients,dict):ingredients=_field(ingredients,'items','reagents','data','materials')
    if not isinstance(ingredients,list):return None
    reagents=[]
    for part in ingredients:
        if not isinstance(part,dict):return None
        item=_item_id(_field(part,'itemId','item_id','item','reagent','material'))
        if item is None:return None
        reagents.append([item,_positive(_field(part,'quantity','count','amount','requiredCount','qty') or 1)])
    if not reagents:return None
    skill=_field(obj,'requiredSkill','skillLevel','skill','required_skill')
    if isinstance(skill,dict):skill=_field(skill,'required','level','orange','min')
    try:skill=int(skill)
    except (TypeError,ValueError):skill=None
    return (profession,rid,str(obj.get('name',f'Recipe #{rid}')),output_id,output_qty,skill,json.dumps(reagents))

def _total(payload):
    if not isinstance(payload,dict):return None
    for obj in (payload.get('meta'),payload.get('pagination'),_data(payload)):
        if isinstance(obj,dict):
            for key in ('total','totalCount','total_count'):
                if obj.get(key) is not None:
                    try:return int(obj[key])
                    except (ValueError,TypeError):pass
    return None

def fetch_professions(settings,progress=None):
    from collections import Counter
    key=settings.get('foreverdb_key','').strip()
    if not key:raise ValueError('Enter your ForeverDB API key in Settings')
    session=requests.Session();session.headers.update({'X-API-Key':key,'User-Agent':'ForeverMarketTracker/1.2.4a (ForeverDB.net credited)'})
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
    all_rows=[];counts={};reasons=Counter();sample_keys=set();checked=0
    for index,slug in enumerate(slugs):
        offset=0;total=None;seen=set();count=0
        while True:
            payload=get(BASE+'/'+slug,{'limit':100,'offset':offset})
            rows=_recipes(payload)
            if total is None:total=_total(payload)
            if not rows:
                if total is not None and offset<total:raise ValueError(slug+' recipe listing ended early')
                break
            for item in rows:
                checked+=1
                if isinstance(item,dict):sample_keys.update(item.keys())
                parsed=normalize_recipe(slug,item)
                if parsed and parsed[1] not in seen:all_rows.append(parsed);seen.add(parsed[1]);count+=1
                elif not parsed:reasons[recipe_rejection(item)]+=1
            offset+=len(rows)
            if progress:progress(f'{slug}: {offset:,} checked / {count:,} usable / {sum(reasons.values()):,} rejected',index*100+min(99,int(100*offset/max(total or offset,1))),len(slugs)*100)
            if total is not None and offset>=total:break
            if len(rows)<100:break
            if offset>100000:raise ValueError('Too many recipes in '+slug)
            time.sleep(.12)
        counts[slug]=count
        if progress:progress(f'{slug} complete ({count:,} usable, {checked:,} total checked)',(index+1)*100,len(slugs)*100)
    if not all_rows:
        summary=', '.join(f'{k}: {v}' for k,v in reasons.most_common(4))
        raise ValueError(f'No usable recipes from {checked:,} checked. Rejections: {summary or "none"}. Recipe keys: {", ".join(sorted(sample_keys))[:350] or "none"}. Existing data retained.')
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
    item_cols={r[1] for r in db.execute('PRAGMA table_info(items)')}
    qualities=dict(db.execute('SELECT item_id,quality FROM items')) if 'quality' in item_cols else {}
    # Explicit NPC purchase prices only; unknown vendor cost is not assumed free.
    from vendor_catalogue import migrate as vendor_migrate
    vendor_migrate(db)
    vendor={r[0]:(r[1],r[2]) for r in db.execute('''SELECT item_id,MIN(purchase_copper),stock_type
        FROM vendor_inventory v WHERE purchase_copper>0 AND purchase_copper=(
        SELECT MIN(purchase_copper) FROM vendor_inventory w WHERE w.item_id=v.item_id AND w.purchase_copper>0)
        GROUP BY item_id''')}
    results=[]
    for prof,rid,name,output,qty,skill,raw in db.execute('SELECT * FROM craft_recipes WHERE profession=?',(profession,)):
        detail=[];total=0;missing=[]
        for item,count in json.loads(raw):
            quote=prices.get(item)
            ah_unit=(quote[1] if quote and quote[1]>0 else quote[0] if quote and quote[0]>0 else None)
            vendor_quote=vendor.get(item)
            vendor_unit=vendor_quote[0] if vendor_quote else None
            if ah_unit is None and vendor_unit is None:missing.append(names.get(item,f'Item #{item}'));continue
            unit=min(x for x in (ah_unit,vendor_unit) if x is not None)
            source='NPC vendor' if vendor_unit is not None and unit==vendor_unit else 'AH'
            total+=unit*count
            detail.append(ReagentQuote(names.get(item,f'Item #{item}'),count,unit,source,item,qualities.get(item),
                ah_unit,vendor_unit,vendor_quote[1] if vendor_quote else 'unknown'))
        sell=prices.get(output)
        if missing or not sell or sell[1]<=0:
            results.append(dict(name=names.get(output,name) if name.startswith('Recipe #') else name,quality=qualities.get(output),recipe_id=rid,skill=skill,output=output,quantity=qty,materials=detail,missing=missing or (['Output AH price'] if not sell else []),cost=None,price=None,profit=None,roi=None,supply=sell[2] if sell else 0));continue
        gross=sell[1]*qty
        net=int(gross*(100-cut)/100)-total
        results.append(dict(name=names.get(output,name) if name.startswith('Recipe #') else name,quality=qualities.get(output),recipe_id=rid,skill=skill,output=output,quantity=qty,materials=detail,missing=[],cost=total,price=sell[1],profit=net,roi=100*net/total if total else None,supply=sell[2]))
    return results
