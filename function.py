import os
def func_structure_create(dirs, files):
    for d in dirs: os.makedirs(d, exist_ok=True)
    for f in files: open(f, "a").close()
    
from pathlib import Path
def func_structure_check(root, dirs=(), files=()):
    r = Path(root)
    if not r.exists():
        raise RuntimeError(f"[ROOT_MISSING] {r}")
    md = [d for d in dirs if not (r/d).is_dir()]
    mf = [f for f in files if not (r/f).is_file()]
    if md or mf:
        raise RuntimeError(
            "STRUCTURE_INVALID\n"
            f"DIRS_MISSING: {','.join(md) if md else '-'}\n"
            f"FILES_MISSING: {','.join(mf) if mf else '-'}"
        )
    return None

async def func_check_config_api(api,app_routes):
    allowed={"id","is_token","is_active_check","cache_sec","ratelimiter_times_sec"}
    route_set=set()
    for r in app_routes:
        p=getattr(r,"path",None)
        if p:route_set.add(p)
    for path,cfg in api.items():
        if type(path) is not str or not path.startswith("/"):raise Exception("invalid api path:"+str(path))
        if path not in route_set:raise Exception("path not in fastapi routes:"+path)
        if type(cfg) is not dict:raise Exception("invalid config for:"+path)
        for k in cfg:
            if k not in allowed:raise Exception("invalid key "+k+" in "+path)
        if "id" not in cfg or type(cfg["id"]) is not int:raise Exception("invalid id in "+path)
        if "is_token" in cfg and cfg["is_token"] not in (0,1):raise Exception("invalid is_token in "+path)
        if "is_active_check" in cfg and cfg["is_active_check"] not in (0,1):raise Exception("invalid is_active_check in "+path)
        if "cache_sec" in cfg:
            v=cfg["cache_sec"]
            if type(v) not in (list,tuple) or len(v)!=2:raise Exception("invalid cache_sec in "+path)
            if v[0] not in ("redis","inmemory"):raise Exception("invalid cache backend in "+path)
            if type(v[1]) is not int or v[1]<0:raise Exception("invalid cache ttl in "+path)
        if "ratelimiter_times_sec" in cfg:
            v=cfg["ratelimiter_times_sec"]
            if type(v) not in (list,tuple) or len(v)!=2:raise Exception("invalid ratelimiter_times_sec in "+path)
            if type(v[0]) is not int or type(v[1]) is not int:raise Exception("invalid ratelimiter_times_sec value in "+path)
            if v[0]<=0 or v[1]<=0:raise Exception("invalid ratelimiter_times_sec range in "+path)
    return None

import re
async def func_table_tag_read(postgres_pool,table,column,filter_col=None,filter_val=None,limit=None,page=None):
    if not limit:limit=100
    if not page:page=1
    rx=re.compile(r"^[a-z_][a-z0-9_]*$")
    if not rx.match(table):raise Exception("bad table")
    if not rx.match(column):raise Exception("bad column")
    if filter_col and not rx.match(filter_col):raise Exception("bad filter")
    limit=min(max(int(limit),1),500);page=max(int(page),1)
    where="";args=[]
    if filter_col and filter_val is not None:
        where=f"WHERE x.{filter_col}=$1";args=[filter_val]
    q=f"SELECT t,count(*) FROM {table} x CROSS JOIN LATERAL unnest(x.{column}) t {where} GROUP BY t ORDER BY count(*) DESC LIMIT {limit} OFFSET {(page-1)*limit}"
    async with postgres_pool.acquire() as conn:
        rows=await conn.fetch(q,*args)
    return [{"tag":r['t'],"count":r['count']} for r in rows]

import aiohttp
from bs4 import BeautifulSoup
async def func_person_intel_read(q,searchapi_key,gemini):
    P1="Extract explicit facts only, grouped under identity, role, skills, intent, signals. Text: {ctx}"
    P2="Summarize the following facts into a coherent person profile. Facts:\n{ctx}"
    async def _r1(ctx):
        r=gemini.models.generate_content(model="gemini-2.0-flash",contents=P1.format(ctx=ctx))
        return r.text.strip()
    async def _r2(ctx):
        r=gemini.models.generate_content(model="gemini-2.0-flash",contents=P2.format(ctx=ctx))
        return r.text.strip()
    U="https://www.searchapi.io/api/v1/search";E="google";N=5;L=6000
    async with aiohttp.ClientSession() as s:
        async with s.get(U,params={"engine":E,"q":q,"api_key":searchapi_key}) as r:j=await r.json();urls=[x["link"] for x in j.get("organic_results",[])[:N]]
        fr=[];used=[]
        for u in urls:
            async with s.get(u,headers={"User-Agent":"Mozilla/5.0"}) as r:raw=await r.read();html=raw.decode("utf-8","ignore")
            soup=BeautifulSoup(html,"html.parser")
            for t in soup(["script","style","noscript"]):t.decompose()
            clean=" ".join(soup.stripped_strings)[:L]
            i=await _r1(clean)
            if i:fr.append(i);used.append(u)
    m="\n".join(fr);f=await _r2(m)
    return {"summary":f,"sources":len(fr),"urls":used}

from google import genai
async def func_gemini_client_read(gemini_key):
    client = genai.Client(api_key=gemini_key)
    return client

async def func_postgres_flush(app):
    await app.state.func_postgres_obj_create(app.state.client_postgres_pool,app.state.func_postgres_obj_serialize,app.state.cache_postgres_column_datatype,"flush")
    return None
    
from pathlib import Path
import os
import aiofiles
from fastapi import responses, HTTPException
async def func_html_serve(name: str):
    file = name if name.endswith(".html") else f"{name}.html"
    root = Path("static")
    p = root / file
    if not p.is_file():
        for p in root.rglob(file):
            if p.is_file(): break
        else:
            raise HTTPException(404, "page not found")
    path = str(p)
    if ".." in path: raise HTTPException(400, "invalid name")
    full_path = os.path.abspath(path)
    if not full_path.endswith(".html"): raise HTTPException(400, "invalid file type")
    if not os.path.isfile(full_path): raise HTTPException(404, "file not found")
    try:
        async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
            html = await f.read()
    except Exception:
        raise HTTPException(500, "failed to read file")
    return responses.HTMLResponse(content=html)

async def func_postgres_cache_reset(postgres_pool, func_postgres_schema_read):
    return await func_postgres_schema_read(postgres_pool) if postgres_pool else ({},{})

async def func_users_cache_reset(postgres_pool, func_postgres_map_column, sql_config, postgres_schema):
    c1=await func_postgres_map_column(postgres_pool,sql_config.get("cache_users_api_id_access")) if postgres_pool and postgres_schema.get("users",{}).get("api_id_access") else {}
    c2=await func_postgres_map_column(postgres_pool,sql_config.get("cache_users_is_active")) if postgres_pool and postgres_schema.get("users",{}).get("is_active") else {}
    return c1, c2

import traceback,asyncpg,re
from fastapi import responses
async def func_api_response_error(e,is_traceback,sentry_dsn):
    if isinstance(e,asyncpg.exceptions.UniqueViolationError):col=re.findall(r'\((.*?)\)=',e.detail or "");error=(col[0].replace("_"," ")+" already exists") if col else "duplicate value"
    elif isinstance(e,asyncpg.exceptions.CheckViolationError):c=e.constraint_name or "";error=re.sub(r"^constraint_|_regex$","",c).replace("_"," ")+" invalid"
    elif isinstance(e,asyncpg.exceptions.ForeignKeyViolationError):col=re.findall(r'\((.*?)\)=',e.detail or "");error=(col[0].replace("_"," ")+" invalid reference") if col else "invalid reference"
    elif isinstance(e,asyncpg.exceptions.NotNullViolationError):col=re.findall(r'"(.*?)"',e.message or "");error=(col[-1].replace("_"," ")+" required") if col else "missing required field"
    elif isinstance(e,asyncpg.exceptions.InvalidTextRepresentationError):error="invalid datatype"
    elif isinstance(e,asyncpg.exceptions.NumericValueOutOfRangeError):error="value out of range"
    elif isinstance(e,asyncpg.exceptions.StringDataRightTruncationError):error="value too long"
    elif isinstance(e,asyncpg.exceptions.DeadlockDetectedError):error="database deadlock retry"
    elif isinstance(e,asyncpg.exceptions.SerializationError):error="transaction conflict retry"
    else:error=str(e)
    if is_traceback:print(traceback.format_exc())
    response=responses.JSONResponse(status_code=400,content={"status":0,"message":error})
    if sentry_dsn:import sentry_sdk;sentry_sdk.capture_exception(e)
    return error,response

import asyncio,time
async def func_api_log_create(start, ip_address, user_id, api, method, query_param_str, status_code, type, error, is_log_api, log_api_schema, api_id, func_postgres_obj_create, postgres_pool, func_postgres_obj_serialize, postgres_column_datatype, table_buffer):
   if is_log_api and log_api_schema:
      obj={"ip_address":ip_address,"created_by_id":user_id,"api":api,"api_id":api_id,"method":method,"query_param":query_param_str,"status_code":status_code,"response_time_ms":int((time.perf_counter()-start) * 1000),"type":type,"description":error}
      asyncio.create_task(func_postgres_obj_create(postgres_pool,func_postgres_obj_serialize,postgres_column_datatype,"buffer","log_api",[obj],0,table_buffer))
      return None

async def func_obj_create_logic(obj_query, obj_body, role, user_id, table_create_my_list, table_create_public_list, column_blocked_list, postgres_schema, postgres_pool, func_postgres_obj_serialize, postgres_column_datatype, table_config, func_producer_logic, celery_producer, kafka_producer, rabbitmq_producer, redis_producer, channel_name, func_celery_producer, func_kafka_producer, func_rabbitmq_producer, func_redis_producer, func_postgres_obj_create):
    obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
    if obj_query.get("table")=="users":obj_query["is_serialize"]=1
    if role=="my":
        if obj_query.get("table") not in table_create_my_list:raise Exception("table not allowed")
        if any(any(k in column_blocked_list for k in x) for x in obj_list):raise Exception(f"key not allowed")
    elif role=="public":
        if obj_query.get("table") not in table_create_public_list:raise Exception("table not allowed")
        if any(any(k in column_blocked_list for k in x) for x in obj_list):raise Exception(f"key not allowed")
    elif role=="admin":
        pass
    if user_id and "created_by_id" in postgres_schema.get(obj_query.get("table"),{}):[item.__setitem__("created_by_id",user_id) for item in obj_list]
    if not obj_query.get("queue"):
        output=await func_postgres_obj_create(postgres_pool,func_postgres_obj_serialize,postgres_column_datatype,obj_query.get("mode"),obj_query.get("table"),obj_list,obj_query.get("is_serialize"),table_config.get(obj_query.get("table"),{}).get("buffer"))
    elif obj_query.get("queue"):
        payload={"func":"func_postgres_obj_create","mode":obj_query.get("mode"),"table":obj_query.get("table"),"obj_list":obj_list,"is_serialize":obj_query.get("is_serialize"),"buffer":table_config.get(obj_query.get("table"),{}).get("buffer")}
        output=await func_producer_logic(payload,obj_query.get("queue"),celery_producer,kafka_producer,rabbitmq_producer,redis_producer,channel_name,func_celery_producer,func_kafka_producer,func_rabbitmq_producer,func_redis_producer)
    return output

async def func_obj_update_logic(obj_query, obj_body, role, user_id, column_blocked_list, column_single_update_list, postgres_schema, postgres_pool, func_postgres_obj_serialize, postgres_column_datatype, func_producer_logic, celery_producer, kafka_producer, rabbitmq_producer, redis_producer, channel_name, func_celery_producer, func_kafka_producer, func_rabbitmq_producer, func_redis_producer, func_postgres_obj_update, func_otp_verify, expiry_sec_otp):
    obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
    if obj_query.get("table")=="users":obj_query["is_serialize"]=1
    if role=="my":
        created_by_id=None if obj_query.get("table")=="users" else user_id
        if any(any(k in column_blocked_list for k in x) for x in obj_list):raise Exception("key not allowed")
        if obj_query.get("table")=="users":
            if len(obj_list)!=1:raise Exception("multi object issue")
            if obj_list[0].get("id")!=user_id:raise Exception("ownership issue")
            if "is_deleted" in obj_list[0]:raise Exception("use account delete api")
            if any(key in obj_list[0] and len(obj_list[0])!=2 for key in column_single_update_list):raise Exception("obj length should be 2")
            if any(k in obj_list[0] for k in ("email","mobile")):await func_otp_verify(postgres_pool,obj_query.get("otp"),obj_list[0].get("email"),obj_list[0].get("mobile"),expiry_sec_otp)
    elif role=="public":
        raise Exception("not allowed")
    elif role=="admin":
        created_by_id=None
    if user_id and "updated_by_id" in postgres_schema.get(obj_query.get("table"),{}):[item.__setitem__("updated_by_id",user_id) for item in obj_list]
    if not obj_query.get("queue"):
        output=await func_postgres_obj_update(postgres_pool,func_postgres_obj_serialize,postgres_column_datatype,obj_query.get("table"),obj_list,obj_query.get("is_serialize"),created_by_id)
    elif obj_query.get("queue"):
        payload={"func":"func_postgres_obj_update","table":obj_query.get("table"),"obj_list":obj_list,"is_serialize":obj_query.get("is_serialize"),"created_by_id":created_by_id}
        output=await func_producer_logic(payload,obj_query.get("queue"),celery_producer,kafka_producer,rabbitmq_producer,redis_producer,channel_name,func_celery_producer,func_kafka_producer,func_rabbitmq_producer,func_redis_producer)
    return output

async def func_producer_logic(payload, queue, celery_producer, kafka_producer, rabbitmq_producer, redis_producer, channel_name, func_celery_producer, func_kafka_producer, func_rabbitmq_producer, func_redis_producer):
   if queue=="celery":output=await func_celery_producer(celery_producer,payload["func"],[v for k,v in payload.items() if k!="func"])
   elif queue=="kafka":output=await func_kafka_producer(kafka_producer,channel_name,payload)
   elif queue=="rabbitmq":output=await func_rabbitmq_producer(rabbitmq_producer,channel_name,payload)
   elif queue=="redis":output=await func_redis_producer(redis_producer,channel_name,payload)
   return output

import asyncio
from itertools import count
_counter=count(1)
async def func_consumer_logic(payload,func_postgres_obj_create,func_postgres_obj_update,func_postgres_obj_serialize,postgres_pool,cache_postgres_column_datatype):
    n=next(_counter)
    if payload["func"]=="func_postgres_obj_create":output=asyncio.create_task(func_postgres_obj_create(postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype,payload["mode"],payload["table"],payload["obj_list"],payload["is_serialize"],payload["buffer"]))
    elif payload["func"]=="func_postgres_obj_update":output=asyncio.create_task(func_postgres_obj_update(postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype,payload["table"],payload["obj_list"],payload["is_serialize"],payload["created_by_id"]))
    else:raise Exception("wrong consumer func")
    print(n)
    return output

import csv, io
async def func_api_file_to_obj_list(file):
    text = io.TextIOWrapper(file.file, encoding="utf-8")
    reader = csv.DictReader(text)
    obj_list = [row for row in reader]
    await file.close()
    return obj_list

def func_config_override_from_env(g):
    import json, os, ast
    from dotenv import load_dotenv
    load_dotenv()
    for k,v in list(g.items()):
        if k.startswith("config_"):
            if (e:=os.getenv(k)) is not None:
                if isinstance(g[k], list) or k.endswith("_list"):g[k]=json.loads(e)
                elif isinstance(v,bool):g[k]=e.lower()=="true"
                elif isinstance(v,int):g[k]=int(e)
                elif isinstance(v,dict):
                    try:g[k]=json.loads(e)
                    except:pass
                else:
                    try:g[k]=int(e)
                    except:g[k]=e
            if isinstance(g[k], list):g[k]=tuple(g[k])
    try:
        with open("config.py","r") as f:
            for n in ast.parse(f.read()).body:
                if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Name):
                    t,v = n.targets[0].id, n.value.id
                    if t.startswith("config_") and v.startswith("config_") and os.getenv(t) is None:g[t]=g[v]
    except Exception:pass

async def func_postgres_runner(postgres_pool,mode,query):
    query_lower=query.lower()
    if mode not in ["read","write"]:raise Exception("mode=read/write")
    block_word = ["drop", "truncate"]
    for item in block_word:
        if item in query_lower:
            raise Exception(f"{item} keyword not allowed in query")
    async with postgres_pool.acquire() as conn:
        if mode == "read":return await conn.fetch(query)
        if mode == "write":
            if "returning" in query_lower:return await conn.fetch(query)
            else:return await conn.execute(query)
    return None

async def func_postgres_ids_update(postgres_pool,table,ids,column,value,created_by_id=None,updated_by_id=None):
    set_clause=f"{column}=$1" if updated_by_id is None else f"{column}=$1,updated_by_id=$2"
    query=f"update {table} set {set_clause} where id in ({ids}) and ($3::bigint is null or created_by_id=$3);"
    async with postgres_pool.acquire() as conn:
        params=[value]
        if updated_by_id is not None:params.append(updated_by_id)
        params.append(created_by_id)
        await conn.execute(query,*params)

async def func_postgres_ids_delete(postgres_pool,table,ids,created_by_id=None):
    query=f"delete from {table} where id in ({ids}) and ($1::bigint is null or created_by_id=$1);"
    async with postgres_pool.acquire() as conn:
        await conn.execute(query,created_by_id)
    return "ids deleted"

async def func_postgres_parent_read(postgres_pool,table,parent_column,parent_table,created_by_id=None,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    query=f"with x as (select {parent_column} from {table} where ($1::bigint is null or created_by_id=$1) order by {order} limit {limit} offset {(page-1)*limit}) select ct.* from x left join {parent_table} ct on x.{parent_column}=ct.id;"
    async with postgres_pool.acquire() as conn:
        obj_list=await conn.fetch(query,created_by_id)
    return obj_list

import re, json
async def func_postgres_map_column(postgres_pool,query):
    if not query:return {}
    def parse_cols(q):
        m=re.search(r"select\s+(.*?)\s+from\s",q,flags=re.I|re.S)
        cols=[c.strip() for c in m.group(1).split(",")]
        return cols[0],cols[1:]
    c1,c2_cols=parse_cols(query);output={}
    async with postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for row in conn.cursor(query,prefetch=5000):
                k=row.get(c1)
                if len(c2_cols)==1:
                    c2=c2_cols[0]
                    v=dict(row) if c2=="*" else row.get(c2)
                else:
                    v={col:row.get(col) for col in c2_cols}
                if isinstance(v,str) and v.lstrip().startswith(("{","[")):
                    v=json.loads(v)
                if k not in output:output[k]=v
                else:
                    if not isinstance(output[k],list):output[k]=[output[k]]
                    output[k].append(v)
    return output

import datetime
async def func_postgres_clean(postgres_pool, table):
    async with postgres_pool.acquire() as conn:
        for table_name, cfg in table.items():
            days = cfg.get("retention_day")
            if days is None:continue
            threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            query = f"DELETE FROM {table_name} WHERE created_at < $1"
            await conn.execute(query, threshold_date)
    return None

from datetime import datetime
import json
import re
async def func_postgres_obj_read(postgres_pool, func_postgres_obj_serialize, cache_postgres_column_datatype, func_creator_data_add, func_action_count_add, table, obj):
    """
    obj={"order":"created_at desc"}
    obj={"limit":20}
    obj={"page":1}
    obj={"column":"id,title,tag"}
    obj={"creator_key":"username,email"}
    obj={"action_key":"report_test,test_id,count,id"}
    obj={"id":"=,1"}
    obj={"id":"in,1|2|3|4"}
    obj={"title":"ilike,%search%"}
    obj={"status":"is,null"}
    obj={"id":"is distinct from,1"}
    obj={"id":"is not distinct from,null"}
    obj={"age":"between,18|35"}
    obj={"tag":"contains,python"}
    obj={"tag":"overlap,python|sql"}
    obj={"tag":"any,python"}
    obj={"tag_int":"contains,1|2|3"}
    obj={"tag_int":"overlap,10|20"}
    obj={"tag_int":"any,5"}
    obj={"metadata":"contains,role|admin"}
    obj={"metadata":"contains,id|123|int"}
    obj={"metadata":"exists,is_verified"}
    obj={"location":"point,80.0|15.0|0|1000"}
    """
    def validate_sql_key(name):
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(name)): raise Exception(f"security error: invalid identifier {name}")
        return name
    safe_table = validate_sql_key(table)
    order_raw = obj.get("order", "id desc")
    order_parts = []
    for part in order_raw.split(","):
        sub = part.strip().split()
        if sub:
            col = validate_sql_key(sub[0])
            dir_val = sub[1].upper() if len(sub) > 1 and sub[1].lower() in ["asc", "desc"] else "ASC"
            order_parts.append(f"{col} {dir_val}")
    order = ", ".join(order_parts)
    limit, page = int(obj.get("limit", 100)), int(obj.get("page", 1))
    columns_raw = obj.get("column", "*")
    columns = "*" if columns_raw == "*" else ",".join([validate_sql_key(c.strip()) for c in columns_raw.split(",")])
    creator_key, action_key = obj.get("creator_key"), obj.get("action_key")
    filters = {k: v for k, v in obj.items() if k not in ["table", "order", "limit", "page", "column", "creator_key", "action_key"]}
    async def _serialize_single(col, val, datatype):
        if str(val).lower() == "null": return None
        res = await func_postgres_obj_serialize({col: datatype}, [{col: val}])
        return res[0][col]
    conditions, values, idx = [], [], 1
    v_ops = {"=": "=", "==": "=", "!=": "!=", "<>": "<>", ">": ">", "<": "<", ">=": ">=", "<=": "<=", "is": "IS", "is not": "IS NOT", "in": "IN", "not in": "NOT IN", "between": "BETWEEN", "is distinct from": "IS DISTINCT FROM", "is not distinct from": "IS NOT DISTINCT FROM"}
    str_ops = {"like": "LIKE", "ilike": "ILIKE", "~": "~", "~*": "~*"}
    for col_key, expr in filters.items():
        validate_sql_key(col_key)
        if expr.lower().startswith("point,"):
            try:
                _, rest = expr.split(",", 1); lon, lat, mn, mx = [float(x) for x in rest.split("|")]
                conditions.append(f"ST_Distance({col_key}, ST_Point(${idx}, ${idx+1})::geography) BETWEEN ${idx+2} AND ${idx+3}")
                values.extend([lon, lat, mn, mx]); idx += 4; continue
            except: raise Exception(f"invalid point filter for {col_key}")
        dtype = cache_postgres_column_datatype.get(col_key, "text")
        dt_low = dtype.lower(); is_json, is_arr = "json" in dt_low, ("[]" in dt_low or "array" in dt_low)
        base_type = dt_low.replace("[]", "").replace("array", "").strip() if is_arr else dtype
        if "," not in expr: raise Exception(f"invalid format for {col_key}: {expr}")
        op, raw_val = expr.split(",", 1); op = op.strip().lower()
        avail = list(v_ops.keys())
        if any(x in dt_low for x in ["text", "char", "varchar"]): avail += list(str_ops.keys())
        if is_arr: avail += ["contains", "overlap", "any"]
        if is_json: avail += ["contains", "exists"]
        if op not in avail: raise Exception(f"invalid operator '{op}'")
        s_val = None
        if op == "contains":
            if is_json:
                if "|" in raw_val and not (raw_val.startswith("{") or raw_val.startswith("[")):
                    parts = raw_val.split("|"); k, v_raw, t = parts[0], parts[1], (parts[2].lower() if len(parts) > 2 else "str")
                    v = int(v_raw) if t == "int" else (v_raw.lower() == "true" if t == "bool" else float(v_raw) if t == "float" else v_raw)
                    s_val = json.dumps({k: v})
                else:
                    try: s_val = json.dumps(json.loads(raw_val))
                    except: s_val = raw_val
            elif is_arr: s_val = [await _serialize_single(col_key, x.strip(), base_type) for x in raw_val.split("|")]
            else: s_val = await _serialize_single(col_key, raw_val, dtype)
        elif op == "overlap": s_val = [await _serialize_single(col_key, x.strip(), base_type) for x in raw_val.split("|")]
        elif op in ["in", "not in", "between"]: s_val = [await _serialize_single(col_key, x.strip(), dtype if op == "between" else base_type) for x in raw_val.split("|")]
        elif op == "any": s_val = await _serialize_single(col_key, raw_val, base_type)
        else: s_val = await _serialize_single(col_key, raw_val, dtype)
        if s_val is None:
            if op not in ["is", "is not", "is distinct from", "is not distinct from"]: raise Exception(f"null requires is/distinct for {col_key}")
            conditions.append(f"{col_key} {v_ops[op]} NULL")
        elif op == "contains": values.append(s_val); conditions.append(f"{col_key} @> ${idx}{'::jsonb' if is_json else ''}"); idx += 1
        elif op == "exists": values.append(s_val); conditions.append(f"{col_key} ? ${idx}"); idx += 1
        elif op == "overlap": values.append(s_val); conditions.append(f"{col_key} && ${idx}"); idx += 1
        elif op == "any": values.append(s_val); conditions.append(f"${idx} = ANY({col_key})"); idx += 1
        elif op in ["in", "not in"]:
            ph = [f"${idx + i}" for i in range(len(s_val))]; values.extend(s_val); conditions.append(f"{col_key} {v_ops[op]} ({','.join(ph)})"); idx += len(s_val)
        elif op == "between": values.extend(s_val); conditions.append(f"{col_key} BETWEEN ${idx} AND ${idx+1}"); idx += 2
        else:
            final_op = v_ops.get(op) or str_ops.get(op)
            conditions.append(f"{col_key} {final_op} ${idx}"); values.append(s_val); idx += 1
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT {columns} FROM {safe_table} {where} ORDER BY {order} LIMIT ${idx} OFFSET ${idx+1}"
    values.extend([limit, (page - 1) * limit])
    async with postgres_pool.acquire() as conn:
        try:
            records = await conn.fetch(query, *values); res_list = [dict(r) for r in records]
            if creator_key and res_list: res_list = await func_creator_data_add(postgres_pool, res_list, creator_key)
            if action_key and res_list: res_list = await func_action_count_add(postgres_pool, res_list, action_key)
            return res_list
        except Exception as e: raise Exception(f"Read Error: {e}")

async def func_postgres_obj_update(postgres_pool, func_postgres_obj_serialize, cache_postgres_column_datatype, table, obj_list, is_serialize=None, created_by_id=None, batch_size=None, return_ids=False):
    if not obj_list:return "0 rows updated"
    if not is_serialize:is_serialize=0
    if not all("id" in obj for obj in obj_list):raise Exception("all objects must have 'id' field")
    batch_size=batch_size or 5000
    if is_serialize:obj_list=await func_postgres_obj_serialize(cache_postgres_column_datatype,obj_list)
    async def postgres_update_objects(client_pool,tbl,objs,user_id=None,batch_sz=5000,ret_ids=False):
        cols=[c for c in objs[0] if c!="id"]
        if not cols:return "0 rows updated"
        max_batch=65535//(len(cols)+1+(1 if user_id else 0))
        batch_sz=min(batch_sz,max_batch)
        ids=[] if ret_ids else None
        total=0
        async with client_pool.acquire() as conn:
            if len(objs)==1:
                obj=objs[0]
                params=[obj[c] for c in cols]+[obj["id"]]
                where=f"id=${len(params)}"+(f" AND created_by_id=${len(params)+1}" if user_id else "")
                if user_id:params.append(user_id)
                set_clause=",".join(f"{c}=${i+1}" for i,c in enumerate(cols))
                if ret_ids:
                    row=await conn.fetch(f"UPDATE {tbl} SET {set_clause} WHERE {where} RETURNING id;",*params)
                    total=len(row)
                else:
                    res=await conn.execute(f"UPDATE {tbl} SET {set_clause} WHERE {where};",*params)
                    total=int(res.split()[-1])
                return f"{total} rows updated"
            async with conn.transaction():
                for i in range(0,len(objs),batch_sz):
                    batch=objs[i:i+batch_sz]
                    vals,set_clauses=[],[]
                    for col in cols:
                        cases=[]
                        for obj in batch:
                            vals.extend([obj[col],obj["id"]])
                            idx_val,idx_id=len(vals)-1,len(vals)
                            if user_id:
                                vals.append(user_id)
                                idx_user=len(vals)
                                cases.append(f"WHEN id=${idx_id} AND created_by_id=${idx_user} THEN ${idx_val}")
                            else:
                                cases.append(f"WHEN id=${idx_id} THEN ${idx_val}")
                        set_clauses.append(f"{col} = CASE {' '.join(cases)} ELSE {col} END")
                    ids_list=[obj["id"] for obj in batch]
                    vals_offset=len(vals)
                    where_parts=[f"id IN ({','.join(f'${vals_offset+j+1}' for j in range(len(ids_list)))})"]
                    vals.extend(ids_list)
                    if user_id:
                        where_parts.append(f"created_by_id=${len(vals)+1}")
                        vals.append(user_id)
                    where_clause=" AND ".join(where_parts)
                    if ret_ids:
                        rows=await conn.fetch(f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE {where_clause} RETURNING id;",*vals)
                        ids.extend([r["id"] for r in rows])
                    else:
                        res=await conn.execute(f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE {where_clause};",*vals)
                        total+=int(res.split()[-1])
        if ret_ids:total=len(ids)
        return f"{total} rows updated"
    return await postgres_update_objects(postgres_pool,table,obj_list,created_by_id,batch_size,return_ids)

import asyncio
inmemory_cache_object_create = {}
table_object_key = {}
buffer_lock = asyncio.Lock()
async def func_postgres_obj_create(postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype,mode,table=None,obj_list=None,is_serialize=None,buffer=None,returning_ids=False,conflict_columns=None,batch_size=None):
    if mode != "flush" and (not table or not obj_list):raise Exception("table/obj_list cant be null")
    if not is_serialize:is_serialize=0
    buffer = buffer or 10
    batch_size = batch_size or 5000
    if is_serialize and obj_list:obj_list = await func_postgres_obj_serialize(cache_postgres_column_datatype, obj_list)
    if obj_list and len(obj_list) == 1:returning_ids = True
    async def postgres_insert_objects(client_pool, tbl, objs, ret_ids=False, conflict_cols=None, batch_sz=5000, use_schema=None):
        if not objs:return None
        if use_schema:
            cols = sorted(list(use_schema))
            for o in objs:
                for k in cols:
                    if k not in o:o[k] = None
        else:
            cols = list(objs[0].keys())
        col_count = len(cols)
        max_batch = 65535 // col_count
        batch_sz = min(batch_sz, max_batch)
        conflict = f"on conflict ({','.join(conflict_cols)})" if conflict_cols else ""
        ids = [] if ret_ids else None
        async with client_pool.acquire() as conn:
            async with conn.transaction():
                for i in range(0, len(objs), batch_sz):
                    batch = objs[i:i + batch_sz]
                    vals, rows_sql = [], []
                    for j, o in enumerate(batch):
                        start = j * col_count + 1
                        rows_sql.append(f"({', '.join([f'${k}' for k in range(start, start + col_count)])})")
                        vals.extend([o.get(k) for k in cols])
                    q = f"insert into {tbl} ({','.join(cols)}) values {','.join(rows_sql)} {conflict}"
                    if ret_ids:
                        q += " returning id;"
                        fetched = await conn.fetch(q, *vals)
                        ids.extend([r["id"] for r in fetched])
                    else:
                        await conn.execute(q, *vals)
        return ids if ret_ids else None
    global inmemory_cache_object_create, table_object_key
    async with buffer_lock:
        if mode == "now":
            return await postgres_insert_objects(postgres_pool, table, obj_list, returning_ids, conflict_columns, batch_size)
        elif mode == "buffer":
            if table not in inmemory_cache_object_create:inmemory_cache_object_create[table] = []
            if table not in table_object_key:table_object_key[table] = set()
            for o in obj_list:table_object_key[table].update(o.keys())
            inmemory_cache_object_create[table].extend(obj_list)
            if len(inmemory_cache_object_create[table]) >= buffer:
                objs_to_insert = inmemory_cache_object_create[table]
                inmemory_cache_object_create[table] = []
                await postgres_insert_objects(postgres_pool, table, objs_to_insert, returning_ids, conflict_columns, batch_size, table_object_key[table])
                return "buffer released"
            return None
        elif mode == "flush":
            results = {}
            for tbl, rows in inmemory_cache_object_create.items():
                if not rows:continue
                try:
                    schema = table_object_key.get(tbl)
                    results[tbl] = await postgres_insert_objects(postgres_pool, tbl, rows, returning_ids, conflict_columns, batch_size, schema)
                except Exception as e:
                    results[tbl] = e
                finally:
                    inmemory_cache_object_create[tbl] = []
            return results
        else:
            raise Exception("mode must be 'now', 'buffer', or 'flush'")

import csv
from io import StringIO
import time, re
async def func_postgres_stream(postgres_pool, query, batch_size=None):
    if not batch_size:batch_size=1000
    if not re.match(r"^\s*(SELECT|WITH|SHOW|EXPLAIN)\b", query, re.I):
        raise ValueError("Only read-only queries allowed")
    async with postgres_pool.acquire() as conn:
        async with conn.transaction():
            stmt = await conn.prepare(query)
            col_names = [a.name for a in stmt.get_attributes()]
            stream = StringIO()
            writer_stream = csv.writer(stream)
            writer_stream.writerow(col_names)
            yield stream.getvalue()
            stream.seek(0); stream.truncate(0)
            async for row in stmt.cursor(prefetch=batch_size):
                writer_stream.writerow(list(row))
                yield stream.getvalue()
                stream.seek(0); stream.truncate(0)

async def func_postgres_init(postgres_pool, postgres, postgres_is_extension, is_match_column):
    if not postgres or "table" not in postgres: raise Exception("postgres.table missing")
    async def _validate():
        seen=set()
        for t,cols in postgres["table"].items():
            if not isinstance(cols,(list,tuple)): raise Exception(f"table config must be list {t}")
            names={c.get("name") for c in cols}
            for c in cols:
                allowed={"name","datatype","old","default","is_mandatory","index","unique","in","regex"}
                if not isinstance(c,dict) or not {"name","datatype"}<=c.keys(): raise Exception(f"invalid column config {t}")
                if set(c)-allowed: raise Exception(f"unknown keys {t}.{c.get('name')}")
                if c.get("index")=="gin" and "text" not in c["datatype"].lower() and "[]" not in c["datatype"] and "jsonb" not in c["datatype"]: raise Exception(f"gin error {t}.{c['name']}")
                u=c.get("unique")
                if u:
                    for g in (x.strip() for x in u.split("|") if x.strip()):
                        ucols=[x.strip() for x in g.split(",") if x.strip()]
                        if any(x not in names for x in ucols): raise Exception(f"unique column not found {t}")
                        key=(t,tuple(sorted(ucols)))
                        if key in seen: raise Exception(f"duplicate unique {t}")
                        seen.add(key)
    async def read_db(conn):
        cols=await conn.fetch("select table_name,column_name,data_type,is_nullable,column_default,udt_name from information_schema.columns where table_schema='public'")
        cons=await conn.fetch("select conname,relname from pg_constraint join pg_class on pg_class.oid=conrelid join pg_namespace n on n.oid=pg_class.relnamespace where n.nspname='public'")
        idx=await conn.fetch("select indexname,indexdef from pg_indexes where schemaname='public'")
        db={}
        for r in cols:
            t=r["table_name"]; db.setdefault(t,{})[r["column_name"]]={"type":(r["udt_name"] or r["data_type"]).lower(),"null":r["is_nullable"]=="YES","default":r["column_default"]}
        idx_map={}
        for r in idx:
            if " USING " not in r["indexdef"]: continue
            tbl=r["indexdef"].split(" ON ")[1].split()[0].split(".")[-1]; col=r["indexdef"].split("(",1)[1].split(")",1)[0].split()[0]; it=r["indexdef"].split(" USING ")[1].split()[0].lower()
            idx_map.setdefault((tbl,col),{})[it]=r["indexname"]
        return db,{(r["relname"],r["conname"].lower()) for r in cons},idx_map
    def trim(x): return x[:63]
    await _validate()
    async with postgres_pool.acquire() as conn:
        if postgres_is_extension:
            for e in ("postgis","pg_trgm"): await conn.execute(f"create extension if not exists {e}")
        await conn.execute("create or replace function array_regex_match(text[],text) returns boolean immutable as $$ select coalesce(bool_and(v ~ $2),true) from unnest($1) v $$ language sql")
        for t in postgres["table"]: await conn.execute(f"create table if not exists {t} (id bigint primary key generated by default as identity not null)")
        for t in postgres["table"]:
            await conn.execute(f"""DO $$ DECLARE r RECORD; BEGIN FOR r IN SELECT tgname FROM pg_trigger WHERE tgrelid = '{t}'::regclass AND tgname LIKE 'trigger_%' AND tgisinternal = false LOOP EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', r.tgname, '{t}'); END LOOP; END $$;""")
        db,cons,idx=await read_db(conn)
        for t,cols in postgres["table"].items():
            have=db.get(t,{})
            for c in cols:
                if c.get("old") and c["name"] not in have and c["old"] in have: await conn.execute(f"alter table {t} rename column {c['old']} to {c['name']}")
        db,cons,idx=await read_db(conn)
        for t,cols in postgres["table"].items():
            have=db.get(t,{})
            for c in cols:
                col,dt=c["name"],c["datatype"]
                if col not in have: await conn.execute(f"alter table {t} add column {col} {dt}")
                elif have[col]["type"]!=dt.lower(): await conn.execute(f"alter table {t} alter column {col} type {dt} using {col}::{dt}")
        if is_match_column:
            db,_,_=await read_db(conn)
            for t,cols in postgres["table"].items():
                want={c["name"] for c in cols}; have=set(db.get(t,{}))
                for col in have-want-{"id"}: await conn.execute(f"alter table {t} drop column {col} cascade")
        db,cons,idx=await read_db(conn)
        for t,cols in postgres["table"].items():
            have=db.get(t,{})
            for c in cols:
                col,cur=c["name"],have.get(c["name"])
                if not cur: continue
                if "default" in c:
                    d=c["default"]; sql=d if isinstance(d,str) and d.endswith("()") else repr(d) if isinstance(d,str) else str(d)
                    await conn.execute(f"alter table {t} alter column {col} set default {sql}")
                elif cur["default"] is not None: await conn.execute(f"alter table {t} alter column {col} drop default")
                m=c.get("is_mandatory")
                if m in (1,True) and cur["null"]: await conn.execute(f"alter table {t} alter column {col} set not null")
                elif m in (0,False) and not cur["null"]: await conn.execute(f"alter table {t} alter column {col} drop not null")
        for t,cols in postgres["table"].items():
            for c in cols:
                col,dt,want=c["name"],c["datatype"].lower(),set(c.get("index","").split(",")) if c.get("index") else set()
                cur=idx.get((t,col),{})
                for it,n in cur.items():
                    if n.startswith(f"index_{t}_{col}") and it not in want: await conn.execute(f'drop index if exists "{n}"')
                for it in want:
                    name=trim(f"index_{t}_{col}_{it}")
                    if cur.get(it)!=name:
                        if it in cur: await conn.execute(f'drop index if exists "{cur[it]}"')
                        await conn.execute(f"create index if not exists {name} on {t} using {it} ({col+' gin_trgm_ops' if it=='gin' and dt=='text' else col})")
        db,cons,idx=await read_db(conn)
        for t,cols in postgres["table"].items():
            w_cons=set()
            for c in cols:
                col,dt=c["name"],c["datatype"].lower()
                if c.get("regex"): w_cons.add(trim(f"constraint_{t}_{col}_regex"))
                if "in" in c: w_cons.add(trim(f"constraint_{t}_{col}_in"))
                if c.get("unique"):
                    for g in c["unique"].split("|"): w_cons.add(trim(f"constraint_unique_{t}_{'_'.join(x.strip() for x in g.split(','))}"))
            for tbl,n in list(cons):
                if tbl==t and n.startswith("constraint_") and n not in {x.lower() for x in w_cons}:
                    await conn.execute(f'alter table {t} drop constraint if exists "{n}" cascade'); cons.remove((tbl,n))
            for c in cols:
                col,dt=c["name"],c["datatype"].lower()
                if c.get("regex"):
                    n=trim(f"constraint_{t}_{col}_regex"); sql=f"check ({col} ~ '{c['regex']}')" if dt=="text" else f"check (array_regex_match({col},'{c['regex']}'))" if dt=="text[]" else None
                    if sql:
                        if (t,n.lower()) in cons: await conn.execute(f'alter table {t} drop constraint "{n}"')
                        await conn.execute(f"alter table {t} add constraint {n} {sql}")
                if "in" in c:
                    n=trim(f"constraint_{t}_{col}_in"); vals=",".join(str(x) if isinstance(x,(int,float)) else repr(x) for x in c["in"])
                    if (t,n.lower()) in cons: await conn.execute(f'alter table {t} drop constraint "{n}"')
                    await conn.execute(f"alter table {t} add constraint {n} check ({col} in ({vals}))")
                if c.get("unique"):
                    for g in c["unique"].split("|"):
                        ucols=",".join(x.strip() for x in g.split(",")); n=trim(f"constraint_unique_{t}_{ucols.replace(',','_')}")
                        if (t,n.lower()) in cons: await conn.execute(f'alter table {t} drop constraint "{n}"')
                        await conn.execute(f"alter table {t} add constraint {n} unique ({ucols})")
        for k,sql in postgres.get("sql",{}).items():
            if not sql.startswith("0"): await conn.execute(sql)
    return "database init done"

import hashlib, orjson, uuid
from dateutil import parser
async def func_postgres_obj_serialize(cache_postgres_column_datatype, obj_list):
    for obj in obj_list:
        for k, v in obj.items():
            if v in (None, "", "null"):
                obj[k] = None
                continue
            d = cache_postgres_column_datatype.get(k)
            if not d:
                continue
            try:
                if k == "password":
                    obj[k] = hashlib.sha256(str(v).encode()).hexdigest()
                elif "uuid" in d:
                    obj[k] = str(uuid.UUID(v)) if isinstance(v, str) else str(v)
                elif "bytea" in d:
                    obj[k] = v.encode() if isinstance(v, str) else v
                elif "bool" in d:
                    obj[k] = v if isinstance(v, bool) else (str(v).lower() in ("true", "t", "1", "yes"))
                elif "[]" in d:
                    if isinstance(v, list):
                        ls = v
                    else:
                        s = str(v).strip()
                        if s.startswith('{') and s.endswith('}'): s = s[1:-1]
                        elif s.startswith('[') and s.endswith(']'): s = s[1:-1]
                        ls = [i.strip().strip('"').strip("'") for i in s.split(",") if i.strip()]
                    obj[k] = [int(i) for i in ls] if any(y in d for y in ("int", "serial")) else [str(i) for i in ls]
                elif any(x in d for x in ("text", "char", "enum", "geography", "geometry")):
                    obj[k] = str(v).strip()
                elif any(x in d for x in ("int", "serial")) and "point" not in d:
                    obj[k] = int(v)
                elif any(x in d for x in ("numeric", "double", "precision", "real")):
                    obj[k] = round(float(v), 3)
                elif d == "date":
                    obj[k] = parser.isoparse(v).date() if isinstance(v, str) else v
                elif "timestamp" in d or "time" in d:
                    obj[k] = parser.isoparse(v) if isinstance(v, str) else v
                elif "json" in d:
                    if isinstance(v, (dict, list)):
                        obj[k] = orjson.dumps(v).decode()
                    else:
                        try:
                            orjson.loads(v)
                            obj[k] = v
                        except:
                            obj[k] = orjson.dumps(v).decode()
            except Exception as e:
                raise Exception(f"serialize_error:{k}:{d}:{str(e)}")
    return obj_list

async def func_postgres_schema_read(postgres_pool):
    query="SELECT t.relname AS table_name, a.attname AS column_name, format_type(a.atttypid, a.atttypmod) AS data_type, pg_get_expr(d.adbin, d.adrelid) AS column_default, CASE WHEN a.attnotnull THEN 0 ELSE 1 END AS is_nullable, CASE WHEN EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = a.attrelid AND a.attnum = ANY(i.indkey)) THEN 1 ELSE 0 END AS is_index FROM pg_class t JOIN pg_namespace n ON n.oid = t.relnamespace JOIN pg_attribute a ON a.attrelid = t.oid LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum WHERE t.relkind = 'r' AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped ORDER BY t.relname, a.attnum;"
    async with postgres_pool.acquire() as conn: output=await conn.fetch(query)
    postgres_schema,postgres_column_datatype={},{}
    for obj in output:
        t,c,dt=obj['table_name'],obj['column_name'],obj['data_type'].lower()
        if t not in postgres_schema: postgres_schema[t]={}
        postgres_schema[t][c]={"datatype":dt,"default":obj['column_default'],"is_null":obj['is_nullable'],"is_index":obj['is_index']}
        postgres_column_datatype[c]=dt
    return postgres_schema,postgres_column_datatype

import asyncpg
async def func_postgres_client_read(postgres_url,postgres_min_connection=None,postgres_max_connection=None,timeout=None,command_timeout=None):
    if not postgres_min_connection:postgres_min_connection=5
    if not postgres_max_connection:postgres_max_connection=20
    if not timeout:timeout=60
    if not command_timeout:command_timeout=60
    postgres_pool=await asyncpg.create_pool(dsn=postgres_url,min_size=postgres_min_connection,max_size=postgres_max_connection,timeout=timeout,command_timeout=command_timeout)
    return postgres_pool

import redis.asyncio as redis
async def func_redis_client_read(redis_url):
   r=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))
   return r

async def func_redis_client_read_consumer(redis,channel_name):
   client_redis_consumer=redis.pubsub()
   await client_redis_consumer.subscribe(channel_name)
   return client_redis_consumer

import json
async def func_redis_producer(redis,channel_name,payload):
   output=await redis.publish(channel_name,json.dumps(payload))
   return output

async def func_redis_object_create(redis,key_list,obj_list,expiry_sec):
   async with redis.pipeline(transaction=True) as pipe:
      for index,obj in enumerate(obj_list):
         key=key_list[index]
         if not expiry_sec:pipe.set(key,json.dumps(obj))
         else:pipe.setex(key,expiry_sec,json.dumps(obj))
      await pipe.execute()
   return None

import boto3
async def func_ses_client_read(aws_access_key_id,aws_secret_access_key,ses_region_name):
   ses=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return ses

async def func_ses_send_email(ses,email_from,email_to_list,title,body):
   ses.send_email(Source=email_from,Destination={"ToAddresses":email_to_list},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return None

async def func_sns_send_mobile_message(sns,mobile,message):
   sns.publish(PhoneNumber=mobile,Message=message)
   return None

async def func_sns_send_mobile_message_template(sns,mobile,message,template_id,entity_id,sender_id):
   sns.publish(PhoneNumber=mobile, Message=message,MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

import boto3
async def func_sns_client_read(aws_access_key_id,aws_secret_access_key,sns_region_name):
   sns=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return sns

import boto3
async def func_s3_client_read(aws_access_key_id,aws_secret_access_key,s3_region_name):
   s3=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return s3,s3_resource

async def func_s3_bucket_create(s3,s3_region_name,bucket):
   return s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})

async def func_s3_bucket_public(s3,bucket):
   s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def func_s3_bucket_empty(s3_resource,bucket):
   return s3_resource.Bucket(bucket).objects.all().delete()

async def func_s3_bucket_delete(s3,bucket):
   return s3.delete_bucket(Bucket=bucket)

async def func_s3_url_delete(s3_resource,url):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=s3_resource.Object(bucket,key).delete()
   return output

import uuid
from io import BytesIO
async def func_s3_upload(s3,s3_region_name,bucket,file,key=None,limit_s3_kb=None):
    if not limit_s3_kb:limit_s3_kb=100
    if not key:
        if "." not in file.filename:raise Exception("file must have extension")
        key=f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}"
    if "." not in key:raise Exception("extension must")
    file_content=await file.read()
    file.file.close()
    file_size_kb=round(len(file_content)/1024)
    if file_size_kb>limit_s3_kb:raise Exception("file size issue")
    s3.upload_fileobj(BytesIO(file_content),bucket,key)
    output={file.filename:f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"}
    return output

import uuid
async def func_s3_upload_presigned(s3,s3_region_name,bucket,key=None,limit_s3_kb=None,s3_presigned_expire_sec=None):
   if not limit_s3_kb:limit_s3_kb=100
   if not s3_presigned_expire_sec:s3_presigned_expire_sec=100
   if not key:key=f"{uuid.uuid4().hex}.bin"
   if "." not in key:raise Exception("extension must")
   output=s3.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=s3_presigned_expire_sec,Conditions=[['content-length-range',1,limit_s3_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   return output

from celery import Celery
async def func_celery_client_read_producer(celery_broker_url,celery_backend_url):
   celery_producer=Celery("producer",broker=celery_broker_url,backend=celery_backend_url)
   return celery_producer

from celery import Celery
def func_celery_client_read_consumer(celery_broker_url,celery_backend_url):
   client_celery_consumer=Celery("worker",broker=celery_broker_url,backend=celery_backend_url)
   return client_celery_consumer

async def func_celery_producer(celery_producer,func,param_list):
   output=celery_producer.send_task(func,args=param_list)
   return output.id

import aio_pika
async def func_rabbitmq_client_read_producer(rabbitmq_url):
   client_rabbitmq=await aio_pika.connect_robust(rabbitmq_url)
   rabbitmq_producer=await client_rabbitmq.channel()
   return client_rabbitmq,rabbitmq_producer

import aio_pika
async def func_rabbitmq_client_read_consumer(rabbitmq_url,channel_name):
   client_rabbitmq=await aio_pika.connect_robust(rabbitmq_url)
   client_rabbitmq_channel=await client_rabbitmq.channel()
   client_rabbitmq_consumer=await client_rabbitmq_channel.declare_queue(channel_name,auto_delete=False)
   return client_rabbitmq,client_rabbitmq_consumer

import json,aio_pika
async def func_rabbitmq_producer(rabbitmq_producer,channel_name,payload):
    payload=json.dumps(payload).encode()
    message=aio_pika.Message(body=payload)
    output=await rabbitmq_producer.default_exchange.publish(message,routing_key=channel_name)
    return output

from aiokafka import AIOKafkaProducer
async def func_kafka_client_read_producer(kafka_url,kafka_username,kafka_password):
    kafka_producer=AIOKafkaProducer(bootstrap_servers=kafka_url,security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=kafka_username,sasl_plain_password=kafka_password,)
    await kafka_producer.start()
    return kafka_producer
 
from aiokafka import AIOKafkaConsumer
async def func_kafka_client_read_consumer(kafka_url,kafka_username,kafka_password,channel_name,kafka_group_id,kafka_enable_auto_commit):
    client_kafka_consumer=AIOKafkaConsumer(channel_name,bootstrap_servers=kafka_url,group_id=kafka_group_id, security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=kafka_username,sasl_plain_password=kafka_password,auto_offset_reset="earliest",enable_auto_commit=kafka_enable_auto_commit)
    await client_kafka_consumer.start()
    return client_kafka_consumer
 
import json
async def func_kafka_producer(kafka_producer,channel_name,payload):
   output=await kafka_producer.send_and_wait(channel_name,json.dumps(payload,indent=2).encode('utf-8'),partition=0)
   return output

async def func_check_ratelimiter(redis_client, api_config, path, identifier):
    if not api_config.get(path,{}).get("ratelimiter_times_sec"):return None
    if not redis_client:raise Exception("redis_url_ratelimiter missing")
    limit,window=api_config.get(path).get("ratelimiter_times_sec")
    ratelimiter_key=f"ratelimiter:{path}:{identifier}"
    current_count=await redis_client.get(ratelimiter_key)
    if current_count and int(current_count)+1>limit:raise Exception("ratelimiter exceeded")
    pipe=redis_client.pipeline()
    pipe.incr(ratelimiter_key)
    if not current_count:pipe.expire(ratelimiter_key,window)
    await pipe.execute()
    return None

async def func_check_is_active(user, path, api_config, active_check_mode, postgres_pool, users_active_cache):
    if not api_config.get(path,{}).get("is_active_check")==1 or not user: return None
    async def fetch_user_is_active(user_id):
        async with postgres_pool.acquire() as conn: rows=await conn.fetch("select id,is_active from users where id=$1",user_id)
        if not rows: raise Exception("user not found")
        return rows[0]["is_active"]
    user_is_active=None
    if active_check_mode=="realtime":user_is_active=await fetch_user_is_active(user["id"])
    elif active_check_mode=="cache":
        user_is_active=users_active_cache.get(user["id"],"absent")
        if user_is_active=="absent": user_is_active=await fetch_user_is_active(user["id"])
    elif active_check_mode=="token":
        user_is_active=user.get("is_active","absent")
        if user_is_active=="absent": raise Exception("token has no is_active key")
    else: raise Exception("config_mode_check_is_active=token/cache/realtime")
    if user_is_active==0: raise Exception("user not active")
    return None

async def func_check_admin(user, path, api_config, admin_check_mode, postgres_pool, users_access_cache):
    if not path.startswith("/admin"): return None
    def parse_access_list(access_str): return [int(item.strip()) for item in access_str.split(",")] if access_str else []
    async def fetch_user_access(user_id):
        async with postgres_pool.acquire() as conn: rows = await conn.fetch("select id,api_id_access from users where id=$1", user_id)
        if not rows: raise Exception("user not found")
        return rows[0]["api_id_access"]
    user_api_id_access = None
    if admin_check_mode == "realtime":user_api_id_access = await fetch_user_access(user["id"])
    elif admin_check_mode == "cache":
        user_api_id_access = users_access_cache.get(user["id"], "absent")
        if user_api_id_access == "absent": user_api_id_access = await fetch_user_access(user["id"])
    elif admin_check_mode == "token":
        user_api_id_access = user.get("api_id_access","absent")
        if user_api_id_access == "absent": raise Exception("token has no api_id_access key")
    else: raise Exception("config_mode_check_is_admin=token/cache/realtime")
    if not user_api_id_access: raise Exception("you are not admin")
    user_api_id_access_list = parse_access_list(user_api_id_access); api_id = api_config.get(path, {}).get("id")
    if not api_id: raise Exception("api id not mapped")
    if api_id not in user_api_id_access_list: raise Exception("api access denied")
    return None

from fastapi import Response
import gzip, base64, time
inmemory_cache_api = {}
async def func_check_cache(mode, url_path, query_params, api_config, redis_client, user_id, response):
    def should_cache(expire_sec): return expire_sec is not None and expire_sec > 0
    def build_cache_key(path, qp, uid): return f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(qp.items()))}:{uid}"
    def compress(body): return base64.b64encode(gzip.compress(body)).decode()
    def decompress(data): return gzip.decompress(base64.b64decode(data)).decode()
    if mode not in ["get","set"]: raise Exception("mode=get/set")
    uid = user_id if "my/" in url_path else 0
    cache_key = build_cache_key(url_path, query_params, uid)
    cache_mode, expire_sec = api_config.get(url_path, {}).get("cache_sec", (None, None))
    if not should_cache(expire_sec): return None if mode == "get" else response
    if mode == "get":
        data = None
        if cache_mode == "redis": data = await redis_client.get(cache_key)
        elif cache_mode == "inmemory":
            item = inmemory_cache_api.get(cache_key)
            if item and item["expire_at"] > time.time(): data = item["data"]
        if data: return Response(decompress(data), status_code=200, media_type="application/json", headers={"x-cache":"hit"})
        return None
    elif mode == "set":
        body = getattr(response, "body", None)
        if body is None: body = b"".join([c async for c in response.body_iterator])
        comp = compress(body)
        if cache_mode == "redis": await redis_client.setex(cache_key, expire_sec, comp)
        elif cache_mode == "inmemory": inmemory_cache_api[cache_key] = {"data": comp, "expire_at": time.time() + expire_sec}
        return Response(content=body, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))
    
from fastapi import Request,responses
from starlette.background import BackgroundTask
async def func_api_response_background(scope, body_bytes, api_function):
   async def receive():return {"type":"http.request","body":body_bytes}
   async def api_func_new():
      request_new=Request(scope=scope,receive=receive)
      await api_function(request_new)
   response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
   response.background=BackgroundTask(api_func_new)
   return response

async def func_api_response(request, api_function, api_config, redis_client, user_id, func_background, func_cache):
    cache_sec=api_config.get(request.url.path,{}).get("cache_sec")
    response,type,qp=None,None,dict(request.query_params)
    if qp.get("is_background")=="1":
        body=await request.body()
        response=await func_background(request.scope,body,api_function);type=1
    elif cache_sec:response=await func_cache("get",request.url.path,qp,api_config,redis_client,user_id,None);type=2
    if not response:
        response=await api_function(request);type=3
        if cache_sec:response=await func_cache("set",request.url.path,qp,api_config,redis_client,user_id,response);type=4
    return response,type

async def func_check_token(headers, path, root_key, token_secret_key, api_config, func_decode_token):
    user={}
    token=headers.get("Authorization").split("Bearer ",1)[1] if headers.get("Authorization") and headers.get("Authorization").startswith("Bearer ") else None
    if path.startswith("/root"):
        if not token:raise Exception("token missing")
        if token!=root_key:raise Exception("token mismatch")
    else:
        if token:user=await func_decode_token(token,token_secret_key)
        if path.startswith("/my") and not token:raise Exception("token missing")
        elif path.startswith("/private") and not token:raise Exception("token missing")
        elif path.startswith("/admin") and not token:raise Exception("token missing")
        elif api_config.get(path,{}).get("is_token")==1 and not token:raise Exception("token missing")
    return user

import jwt,json
async def func_token_decode(token,key_jwt):
   user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
   return user

import jwt,json,time
async def func_token_encode(obj,key_jwt,token_expiry_sec,token_refresh_expiry_sec,key_list=None):
   if not isinstance(obj,dict):obj=dict(obj)
   payload={k:obj.get(k) for k in key_list} if key_list else obj
   payload=json.dumps(payload,default=str)
   now=int(time.time())
   exp=now+token_expiry_sec
   exp_refresh=now+token_refresh_expiry_sec
   token=jwt.encode({"exp":exp,"data":payload,"type":"access"},key_jwt)
   token_refresh=jwt.encode({"exp":exp_refresh,"data":payload,"type":"refresh"},key_jwt)
   return {"token":token,"token_refresh":token_refresh,"token_expiry_sec":token_expiry_sec,"token_refresh_expiry_sec":token_refresh_expiry_sec}

from fastapi import FastAPI
def func_fastapi_app_read(lifespan,is_debug_fastapi):
   app=FastAPI(debug=True if is_debug_fastapi else False,lifespan=lifespan)
   return app

import uvicorn
async def func_server_start(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info")
   server=uvicorn.Server(config)
   await server.serve()
   
from fastapi.middleware.cors import CORSMiddleware
def func_app_add_cors(app,cors_origin_list,cors_method_list,cors_headers_list,cors_allow_credentials):
   app.add_middleware(CORSMiddleware,allow_origins=cors_origin_list,allow_methods=cors_method_list,allow_headers=cors_headers_list,allow_credentials=cors_allow_credentials)
   return None

from prometheus_fastapi_instrumentator import Instrumentator
def func_app_add_prometheus(app):
   Instrumentator().instrument(app).expose(app)
   return None

def func_app_state_add(app,obj,pattern_tuple):
    for k, v in obj.items():
        if k.startswith(pattern_tuple):
            setattr(app.state, k, v)

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
def func_app_add_sentry(sentry_dsn):
   sentry_sdk.init(dsn=sentry_dsn,integrations=[FastApiIntegration()],traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)
   return None

from fastapi.staticfiles import StaticFiles
def func_app_add_static(app,folder_static,mount_path):
    app.mount(mount_path, StaticFiles(directory=folder_static),name="static")
    return None

import sys, importlib.util, traceback
from pathlib import Path
def func_add_router(app):
    def load(router_root, file_path):
        try:
            rel = file_path.relative_to(router_root)
            mod = "routers." + ".".join(rel.with_suffix("").parts)
            spec = importlib.util.spec_from_file_location(mod, file_path)
            if not spec or not spec.loader:
                return
            m = importlib.util.module_from_spec(spec)
            sys.modules[mod] = m
            spec.loader.exec_module(m)
            if not hasattr(m, "router"):
                raise RuntimeError(f"Missing `router` in {file_path}")
            app.include_router(m.router)
        except Exception:
            print(f"[FATAL] router load failed: {file_path}")
            traceback.print_exc()
            raise
    root = Path(".").resolve()
    if not root.is_dir():return
    for f in root.rglob("*.py"):
        if f.name.startswith((".", "__")) or any(p.startswith(".") or p in ("venv", "env", "__pycache__") for p in f.parts):continue
        rel = f.relative_to(root)
        if len(rel.parts) == 1:
            if f.name.startswith("router"): load(root, f)
        elif "router" in rel.parts[:-1]:
            load(root, f)

async def func_user_sql_read(postgres_pool,sql,user_id):
    obj = sql.get("profile_metadata", {})
    output = {}
    async with postgres_pool.acquire() as conn:
        for key, query in obj.items():
            rows = await conn.fetch(query, user_id)
            output[key] = [dict(r) for r in rows]
    return output

async def func_api_usage_read(postgres_pool, days, created_by_id=None):
    query="select api,count(*) from log_api where created_at >= now() - ($1 * interval '1 day') and ($2::bigint is null or created_by_id=$2) group by api limit 1000;"
    async with postgres_pool.acquire() as conn:
        obj_list=await conn.fetch(query,days,created_by_id)
    return obj_list

async def func_creator_data_add(postgres_pool, obj_list, creator_key):
    if not obj_list or not creator_key:return obj_list
    creator_key_list=creator_key.split(",")
    obj_list = [dict(obj) for obj in obj_list]
    created_by_ids = {str(obj["created_by_id"]) for obj in obj_list if obj.get("created_by_id")}
    users = {}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id = ANY($1);"
        rows = await postgres_pool.fetch(query, list(map(int, created_by_ids)))
        users = {str(user["id"]): dict(user) for user in rows}
    for obj in obj_list:
        created_by_id = str(obj.get("created_by_id"))
        if created_by_id in users:
            for key in creator_key_list:
                obj[f"creator_{key}"] = users[created_by_id].get(key)
        else:
            for key in creator_key_list:
                obj[f"creator_{key}"] = None
    return obj_list

async def func_action_count_add(postgres_pool, obj_list, action_key):
    if not obj_list or not action_key: return obj_list
    obj_list = [dict(obj) for obj in obj_list]
    table, column, operator, operator_column = action_key.split(",")
    ids = {obj.get("id") for obj in obj_list if obj.get("id")}
    action_values = {}
    if ids:
        query = f"""
            SELECT {column} AS id, {operator}({operator_column}) AS value
            FROM {table}
            WHERE {column} = ANY($1)
            GROUP BY {column};
        """
        rows = await postgres_pool.fetch(query, list(ids))
        action_values = {str(row["id"]): row["value"] for row in rows}
    for obj in obj_list:
        obj_id = str(obj.get("id"))
        obj[f"{table}_{operator}"] = action_values.get(obj_id, 0 if operator == "count" else None)
    return obj_list

async def func_account_delete(mode,postgres_pool,user_id):
    if mode == "soft":query = "UPDATE users SET is_deleted=1 WHERE id=$1;"
    elif mode == "hard":query = "DELETE FROM users WHERE id=$1;"
    else:raise Exception("mode=soft/hard")
    async with postgres_pool.acquire() as conn:
        await conn.execute(query, user_id)
    return "account deleted"

async def func_user_single_read(postgres_pool,user_id):
    query = "SELECT * FROM users WHERE id=$1;"
    async with postgres_pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id)
    user = dict(row) if row else None
    if not user:
        raise Exception("user not found")
    return user

import random
async def func_otp_generate(postgres_pool,email,mobile):
    if not email and not mobile:raise Exception("email/mobile any one is must")
    if email and mobile:raise Exception("only one of email or mobile is allowed")
    otp=random.randint(100000,999999)
    if email:
        query="insert into otp (otp,email) values ($1,$2);"
        values=(otp,email.strip().lower())
    else:
        query="insert into otp (otp,mobile) values ($1,$2);"
        values=(otp,mobile.strip())
    async with postgres_pool.acquire() as conn:
        await conn.execute(query,*values)
    return otp

async def func_otp_verify(postgres_pool,otp,email,mobile,expiry_sec_otp=None):
    if not otp:raise Exception("otp missing")
    if not expiry_sec_otp:expiry_sec_otp=600
    if not email and not mobile: raise Exception("email/mobile any one is must")
    if email and mobile: raise Exception("only one of email or mobile is allowed")
    if email:
        query = f"select otp from otp where created_at>current_timestamp-interval '{expiry_sec_otp} seconds' and email=$1 order by id desc limit 1;"
        value = email.strip().lower()
    else:
        query = f"select otp from otp where created_at>current_timestamp-interval '{expiry_sec_otp} seconds' and mobile=$1 order by id desc limit 1;"
        value = mobile.strip()
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query, value)
    if not output: raise Exception("otp not found")
    if int(output[0]["otp"]) != int(otp): raise Exception("otp mismatch")
    return None

async def func_message_inbox(postgres_pool,user_id,is_unread=None,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    if is_unread==1:query = f"with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=$1 or user_id=$1)), y as (select max(id) as id from x group by unique_id), z as (select m.* from y left join message as m on y.id=m.id), a as (select * from z where user_id=$1 and is_read is distinct from 1) select * from a order by {order} limit {limit} offset {(page-1)*limit};"
    elif is_unread==0:query = f"with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=$1 or user_id=$1)), y as (select max(id) as id from x group by unique_id), z as (select m.* from y left join message as m on y.id=m.id), a as (select * from z where user_id=$1 and is_read=1) select * from a order by {order} limit {limit} offset {(page-1)*limit};"
    else:query = f"with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=$1 or user_id=$1)), y as (select max(id) as id from x group by unique_id), z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {(page-1)*limit};"
    async with postgres_pool.acquire() as conn:
        return await conn.fetch(query, user_id)

async def func_message_received(postgres_pool,user_id,is_unread=None,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    if is_unread==1:query=f"select * from message where user_id=$1 and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
    elif is_unread==0:query=f"select * from message where user_id=$1 and is_read=1 order by {order} limit {limit} offset {(page-1)*limit};"
    else:query=f"select * from message where user_id=$1 order by {order} limit {limit} offset {(page-1)*limit};"
    async with postgres_pool.acquire() as conn:
        return await conn.fetch(query,user_id)

async def func_message_thread(postgres_pool,user_id_1,user_id_2,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    query = f"select * from message where ((created_by_id=$1 and user_id=$2) or (created_by_id=$2 and user_id=$1)) order by {order} limit {limit} offset {(page-1)*limit};"
    async with postgres_pool.acquire() as conn:
        return await conn.fetch(query, user_id_1, user_id_2)

async def func_message_thread_mark_read(postgres_pool,user_id_1,user_id_2):
   query="update message set is_read=1 where created_by_id=$1 and user_id=$2;"
   async with postgres_pool.acquire() as conn:
      await conn.execute(query,user_id_2,user_id_1)
   return None

async def func_message_delete_single(postgres_pool,message_id,user_id):
   query="delete from message where id=$1 and (created_by_id=$2 or user_id=$2);"
   async with postgres_pool.acquire() as conn:
      await conn.execute(query,message_id,user_id)
   return None

async def func_message_delete_bulk(mode,postgres_pool,user_id):
   if mode=="created":query="delete from message where created_by_id=$1;"
   elif mode=="received":query="delete from message where user_id=$1;"
   elif mode=="all":query="delete from message where (created_by_id=$1 or user_id=$1);"
   else:raise Exception("mode=created/received/all")
   async with postgres_pool.acquire() as conn:
      await conn.execute(query,user_id)
   return None

import hashlib
async def func_auth_signup_username_password(postgres_pool,type,username,password):
    password=hashlib.sha256(str(password).encode()).hexdigest()
    query="insert into users (type,username,password) values ($1,$2,$3) returning *;"
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username,password)
    print(output)
    return output[0]
    
async def func_auth_signup_username_password_bigint(postgres_pool,type,username_bigint,password_bigint):
    query="insert into users (type,username_bigint,password_bigint) values ($1,$2,$3) returning *;"
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username_bigint,password_bigint)
    return output[0]

import hashlib
async def func_auth_login_password_username(postgres_pool,type,password,username):
    password=hashlib.sha256(str(password).encode()).hexdigest()
    query="select * from users where type=$1 and username=$2 and password=$3 order by id desc limit 1;"
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username,password)
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

async def func_auth_login_password_username_bigint(postgres_pool,type,password_bigint,username_bigint):
    query="select * from users where type=$1 and username_bigint=$2 and password_bigint=$3 order by id desc limit 1;"
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username_bigint,password_bigint)
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

import hashlib
async def func_auth_login_password_email(postgres_pool,type,password,email):
    password=hashlib.sha256(str(password).encode()).hexdigest()
    query="select * from users where type=$1 and email=$2 and password=$3 order by id desc limit 1;"
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,email,password)
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

import hashlib
async def func_auth_login_password_mobile(postgres_pool,type,password,mobile):
    password=hashlib.sha256(str(password).encode()).hexdigest()
    query="select * from users where type=$1 and mobile=$2 and password=$3 order by id desc limit 1;"
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,mobile,password)
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

async def func_auth_login_otp_email(postgres_pool,type,email):
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch("select * from users where type=$1 and email=$2 order by id desc limit 1;",type,email)
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("insert into users (type,email) values ($1,$2) returning *;",type,email)
            user = output[0] if output else None
    return user

async def func_auth_login_otp_mobile(postgres_pool,type,mobile):
    async with postgres_pool.acquire() as conn:
        output = await conn.fetch("select * from users where type=$1 and mobile=$2 order by id desc limit 1;",type,mobile)
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("insert into users (type,mobile) values ($1,$2) returning *;",type,mobile)
            user = output[0] if output else None
    return user

import json,time
from google.oauth2 import id_token
from google.auth.transport import requests as google_request
async def func_auth_login_google(postgres_pool,google_login_client_id,type,google_token):
    request=google_request.Request()
    id_info=id_token.verify_oauth2_token(google_token,request,google_login_client_id)
    if id_info.get("iss") not in ["accounts.google.com","https://accounts.google.com"]: raise Exception("invalid issuer")
    if not id_info.get("email_verified",False): raise Exception("email not verified")
    if id_info.get("exp",0)<time.time(): raise Exception("token expired")
    email=id_info.get("email").lower()
    google_user={"sub":id_info.get("sub"),"email":email,"name":id_info.get("name"),"picture":id_info.get("picture"),"email_verified":1}
    async with postgres_pool.acquire() as conn:
        output=await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1",type,email)
        user=output[0] if output else None
        if not user:
            output=await conn.fetch("INSERT INTO users (type,email,google_login_id,google_login_metadata) VALUES ($1,$2,$3,$4::jsonb) RETURNING *",type,email,google_user["sub"],json.dumps(google_user))
            user=output[0] if output else None
        elif not user.get("google_login_id"):
            await conn.execute("UPDATE users SET google_login_id=$1,google_login_metadata=$2::jsonb WHERE id=$3",google_user["sub"],json.dumps(google_user),user["id"])
    return user

from openai import OpenAI
def func_openai_client_read(openai_key):
   openai=OpenAI(api_key=openai_key)
   return openai

import httpx
async def func_resend_send_email(resend_url,resend_key,email_from,email_to_list,title,body):
   payload={"from":email_from,"to":email_to_list,"subject":title,"html":body}
   headers={"Authorization":f"Bearer {resend_key}","Content-Type": "application/json"}
   async with httpx.AsyncClient() as client:
      output=await client.post(resend_url,json=payload,headers=headers)
   if output.status_code!=200:raise Exception(f"{output.text}")
   return None

import requests
async def func_fast2sms_send_otp_mobile(fast2sms_url,fast2sms_key,mobile,otp):
   response=requests.get(fast2sms_url,params={"authorization":fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   output=response.json()
   if output.get("return") is not True:raise Exception(f"{output.get('message')}")
   return output

from posthog import Posthog
async def func_posthog_client_read(posthog_project_host,posthog_project_key):
   client_posthog=Posthog(posthog_project_key,host=posthog_project_host)
   return client_posthog

import gspread
from google.oauth2.service_account import Credentials
def func_gsheet_client_read(gsheet_service_account_json_path, gsheet_scope_list):
    creds = Credentials.from_service_account_file(gsheet_service_account_json_path,scopes=gsheet_scope_list)
    gsheet = gspread.authorize(creds)
    return gsheet

from urllib.parse import urlparse, parse_qs
def func_gsheet_object_create(gsheet, sheet_url, obj_list):
    if not obj_list:
        return None
    url_path = urlparse(sheet_url).path.split('/')
    try:
        spreadsheet_id = url_path[3]
    except:
        raise Exception("invalid sheet URL: spreadsheet_id not found")
    qs = parse_qs(urlparse(sheet_url).query)
    if "gid" not in qs:
        raise Exception("invalid sheet URL: gid not found")
    sheet_gid = int(qs["gid"][0])
    ss = gsheet.open_by_key(spreadsheet_id)
    sheet = next((s for s in ss.worksheets() if s.id == sheet_gid), None)
    if not sheet:
        raise Exception("sheet gid invalid")
    columns = list(obj_list[0].keys())
    rows = [[obj.get(col, "") for col in columns] for obj in obj_list]
    output = sheet.append_rows(
        rows,
        value_input_option="USER_ENTERED",
        insert_data_option="INSERT_ROWS"
    )
    return output

import pandas as pd
from urllib.parse import urlparse, parse_qs
import aiohttp
import io
async def func_gsheet_object_read(url):
    parsed = urlparse(url)
    if '/d/' not in parsed.path:
        raise ValueError("Invalid Google Sheet URL")
    spreadsheet_id = parsed.path.split('/d/')[1].split('/')[0]
    gid = parse_qs(parsed.query).get('gid', ['0'])[0]
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(csv_url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch CSV: {resp.status}")
            data = await resp.text()
    df = pd.read_csv(io.StringIO(data))
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")

import motor.motor_asyncio
async def func_mongodb_client_read(mongodb_url):
   mongodb=motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
   return mongodb

async def func_mongodb_object_create(mongodb,database,table,obj_list):
   mongodb_client_database=mongodb[database]
   output=await mongodb_client_database[table].insert_many(obj_list)
   return str(output)

from jira import JIRA
from pathlib import Path
import pandas as pd, uuid, calendar
from datetime import date
def func_jira_worklog_export(jira_base_url, jira_email, jira_token, start_date=None, end_date=None, output_path=None):
    if not output_path: output_path = f"export/{uuid.uuid4().hex}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    today = date.today()
    if not start_date: start_date = today.replace(day=1).strftime("%Y-%m-%d")
    if not end_date: end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1]).strftime("%Y-%m-%d")
    jira = JIRA(server=jira_base_url, basic_auth=(jira_email, jira_token))
    issues = jira.search_issues(f"worklogDate >= {start_date} AND worklogDate <= {end_date}", maxResults=False, expand="worklog")
    rows, assignees = [], set()
    for i in issues:
        if i.fields.assignee: assignees.add(i.fields.assignee.displayName)
        for wl in i.fields.worklog.worklogs:
            d = wl.started[:10]
            if start_date <= d <= end_date: rows.append((wl.author.displayName, d, wl.timeSpentSeconds / 3600))
    pd.DataFrame(rows, columns=["author","date","hours"]).pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0).reindex(assignees, fill_value=0).round(0).astype(int).to_csv(output_path)
    return output_path

import os, shutil
def func_folder_reset(folder_path):
    folder_path = folder_path if os.path.isabs(folder_path) else os.path.join(os.getcwd(), folder_path)
    if not os.path.isdir(folder_path):
        return "folder not found"
    for name in os.listdir(folder_path):
        path = os.path.join(folder_path, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    return None

import os, mimetypes, aiofiles
from fastapi import responses
from starlette.background import BackgroundTask
async def func_client_download_file(path,is_cleanup=1,chunk_size=1024*1024):
    filename = os.path.basename(path)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    async def iterator():
        async with aiofiles.open(path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    background = BackgroundTask(os.remove, path) if is_cleanup else None
    return responses.StreamingResponse(iterator(), media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'}, background=background)

async def func_request_param_read(mode,request,config):
    if mode == "query":param = dict(request.query_params)
    elif mode == "form":
        form = await request.form()
        param = {k:v for k,v in form.items() if isinstance(v,str)}
        for k in form.keys():
            fs = [f for f in form.getlist(k) if getattr(f,"filename",None)]
            if fs: param[k] = fs
    elif mode == "body":
        try: payload = await request.json()
        except: payload = None
        param = payload if isinstance(payload,dict) else {"body":payload}
    else:raise Exception("mode should be query,form,body")
    CAST_MAP = {
        "int":   lambda v: int(v),
        "float": lambda v: float(v),
        "bool":  lambda v: v if isinstance(v,bool) else str(v).strip().lower() in ("1","true","yes","on"),
        "list":  lambda v: [] if v is None else (
                    v if isinstance(v,list) else (
                        [] if (isinstance(v,str) and v.strip()=="") else
                        [x.strip() for x in v.split(",")] if isinstance(v,str) else [v]
                    )
                 ),
        "file":  lambda v: [] if v is None else (v if isinstance(v,list) else [v]),
        "str":   lambda v: str(v),
        "any":   lambda v: v,
    }
    for key,dtype,mandatory,default in config:
        if mandatory and key not in param:
            raise Exception(f"{key} missing in {mode}")
        val = param.get(key,default)
        if mandatory and (val is None or (isinstance(val,str) and val.strip()=="")):
            raise Exception(f"{key} cannot be null")
        if val is not None:
            try:
                val = CAST_MAP[dtype](val)
            except KeyError:
                raise Exception(f"Invalid dtype '{dtype}'")
            except:
                raise Exception(f"{key} invalid value for type {dtype}")
        param[key] = val
    return param

async def func_converter_number(datatype, mode, x):
    limits = {"smallint": 2, "int": 5, "bigint": 11}
    if datatype not in limits: raise ValueError(f"Invalid datatype '{datatype}'. Supported limits: {limits}")
    max_len, CH = limits[datatype], 'abcdefghijklmnopqrstuvwxyz0123456789_-.@#'
    B = len(CH)
    if mode == "encode":
        s = str(x); nl = len(s)
        if nl > max_len: raise ValueError(f"Input '{s}' length {nl} exceeds {datatype} limit {max_len}. Limits: {limits}")
        n = nl
        for c in s:
            idx = CH.find(c); 
            if idx == -1: raise ValueError(f"Char '{c}' not in charset: {CH}")
            n = n * B + idx
        return n
    if mode == "decode":
        try: n, res = int(x), []
        except: raise ValueError(f"Invalid integer: {x}")
        while n > 0: n, r = divmod(n, B); res.append(CH[r])
        return "".join(res[::-1][1:]) if res else ""
    raise ValueError(f"Invalid mode '{mode}': Use encode|decode")

import asyncssh
async def func_sftp_client_read(sftp_host,sftp_port,sftp_username,sftp_password,sftp_key_path,sftp_auth_method):
    if sftp_auth_method not in ("key","password"):raise Exception("auth_method must be 'key' or 'password'")
    if sftp_auth_method=="key":
        if not sftp_key_path:raise Exception("key_path required for key auth")
        conn=await asyncssh.connect(host=sftp_host,port=int(sftp_port),username=sftp_username,client_keys=[sftp_key_path],known_hosts=None)
    else:
        if not sftp_password:raise Exception("password required for password auth")
        conn=await asyncssh.connect(host=sftp_host,port=int(sftp_port),username=sftp_username,password=sftp_password,known_hosts=None)
    return conn

