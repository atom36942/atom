from pathlib import Path
def func_find_html(name,folder):
    for item in Path(folder).rglob("*.html"):
        if item.stem == name:
            return str(item)
    raise Exception("path not found")

import traceback
from fastapi import responses
async def func_handler_api_error(request,e):
   error=str(e)
   if request.app.state.config_is_traceback:print(traceback.format_exc())
   response=responses.JSONResponse(status_code=400,content={"status":0,"message":error})
   if request.app.state.config_sentry_dsn:sentry_sdk.capture_exception(e)
   return error,response

import asyncio
async def func_handler_log_api(start,request,response,type,error):
   if request.app.state.config_is_log_api and request.app.state.cache_postgres_schema.get("log_api"):
      api=request.url.path
      obj={"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"api_id":request.app.state.config_api.get(api,{}).get("id"),"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":int((time.perf_counter()-start) * 1000),"type":type,"description":error}
      asyncio.create_task(request.app.state.func_postgres_obj_create(request.app.state.client_postgres_pool,request.app.state.func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,"buffer","log_api",[obj],0,request.app.state.config_table.get("log_api",{}).get("buffer")))
      return None

import json, subprocess, sys
def func_upgrade_packages():
    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "pip"], capture_output=True)
    out = subprocess.check_output([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    packages = [p["name"] for p in json.loads(out)]
    status = {"upgraded": [], "failed": []}
    for pkg in packages:
        res = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "--upgrade-strategy", "only-if-needed", pkg], capture_output=True)
        status["upgraded" if res.returncode == 0 else "failed"].append(pkg)
    return status
    
async def func_handler_obj_create(role,request):
    obj_query=await request.app.state.func_request_param_read(request,"query",[["mode","str",0,"now"],["table","str",1,None],["is_serialize","int",0,0],["queue","str",0,None]])
    obj_body=await request.app.state.func_request_param_read(request,"body",[])
    obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
    if request.state.user.get("id") and "created_by_id" in request.app.state.cache_postgres_schema.get(obj_query["table"],{}):
        for item in obj_list:item["created_by_id"]=request.state.user.get("id")
    if role=="my":
        if obj_query["table"] not in request.app.state.config_my_table_create_list:raise Exception("table not allowed")
        if any(any(k in request.app.state.config_column_disabled_list for k in x) for x in obj_list):raise Exception(f"key not allowed")
    elif role=="public":
        if obj_query["table"] not in request.app.state.config_public_table_create_list:raise Exception("table not allowed")
        if any(any(k in request.app.state.config_column_disabled_list for k in x) for x in obj_list):raise Exception(f"key not allowed")
    if not obj_query["queue"]:output=await request.app.state.func_postgres_obj_create(request.app.state.client_postgres_pool,request.app.state.func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,obj_query["mode"],obj_query["table"],obj_list,obj_query["is_serialize"],request.app.state.config_table.get(obj_query["table"],{}).get("buffer"))
    elif obj_query["queue"]:
        payload={"func":"func_postgres_obj_create","mode":obj_query["mode"],"table":obj_query["table"],"obj_list":obj_list,"is_serialize":obj_query["is_serialize"],"buffer":request.app.state.config_table.get(obj_query["table"],{}).get("buffer")}
        output=await request.app.state.func_handler_producer(request,obj_query["queue"],payload)
    return output

async def func_handler_obj_update(role,request):
    obj_query=await request.app.state.func_request_param_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["queue","str",0,None],["otp","int",0,None]])
    obj_body=await request.app.state.func_request_param_read(request,"body",[])
    obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
    if request.state.user.get("id") and "updated_by_id" in request.app.state.cache_postgres_schema.get(obj_query["table"],{}):
        for item in obj_list:item["updated_by_id"]=request.state.user.get("id")
    if role=="my":
        created_by_id=None if obj_query["table"]=="users" else request.state.user["id"]
        if any(any(k in request.app.state.config_column_disabled_list for k in x) for x in obj_list):raise Exception("key not allowed")
        if obj_query["table"]=="users":
            if len(obj_list)!=1:raise Exception("multi object issue")
            if obj_list[0]["id"]!=request.state.user["id"]:raise Exception("ownership issue")
            if any(key in obj_list[0] and len(obj_list[0])!=3 for key in ["password","email","mobile"]):raise Exception("obj length should be 2")
            if request.app.state.config_is_otp_verify_profile_update and any(key in obj_list[0] and not obj_query["otp"] for key in ["email","mobile"]):raise Exception("otp missing")
            if obj_query["otp"]:await request.app.state.func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],obj_list[0].get("email"),obj_list[0].get("mobile"),request.app.state.config_otp_expire_sec)
    elif role=="admin":
        created_by_id=None
    if not obj_query["queue"]:output=await request.app.state.func_postgres_obj_update(request.app.state.client_postgres_pool,request.app.state.func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,obj_query["table"],obj_list,obj_query["is_serialize"],created_by_id)
    elif obj_query["queue"]:
        payload={"func":"func_postgres_obj_update","table":obj_query["table"],"obj_list":obj_list,"is_serialize":obj_query["is_serialize"],"created_by_id":created_by_id}
        output=await request.app.state.func_handler_producer(request,obj_query["queue"],payload)
    return obj_query,obj_list

async def func_handler_producer(request,queue,payload):
   if queue=="celery":output=await request.app.state.func_celery_producer(request.app.state.client_celery_producer,payload["func"],[v for k,v in payload.items() if k!="func"])
   elif queue=="kafka":output=await request.app.state.func_kafka_producer(request.app.state.client_kafka_producer,request.app.state.config_channel_name,payload)
   elif queue=="rabbitmq":output=await request.app.state.func_rabbitmq_producer(request.app.state.client_rabbitmq_producer,request.app.state.config_channel_name,payload)
   elif queue=="redis":output=await request.app.state.func_redis_producer(request.app.state.client_redis_producer,request.app.state.config_channel_name,payload)
   return output

import asyncio
from itertools import count
_counter=count(1)
async def func_handler_consumer(payload,func_postgres_obj_create,func_postgres_obj_update,func_postgres_obj_serialize,client_postgres_pool,cache_postgres_column_datatype):
    n=next(_counter)
    if payload["func"]=="func_postgres_obj_create":output=asyncio.create_task(func_postgres_obj_create(client_postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype,payload["mode"],payload["table"],payload["obj_list"],payload["is_serialize"],payload["buffer"]))
    elif payload["func"]=="func_postgres_obj_update":output=asyncio.create_task(func_postgres_obj_update(client_postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype,payload["table"],payload["obj_list"],payload["is_serialize"],payload["created_by_id"]))
    else:raise Exception("wrong consumer func")
    print(n)
    return output

import csv
def func_csv_to_obj_list(path):
    with open(path,"r",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        return [row for row in reader]
    
import csv, io
async def func_api_file_to_obj_list(file):
    text = io.TextIOWrapper(file.file, encoding="utf-8")
    reader = csv.DictReader(text)
    obj_list = [row for row in reader]
    await file.close()
    return obj_list

from pathlib import Path
import uuid, shutil
async def func_api_file_save(file,output_path=None):
    if not output_path:output_path=f"export/{uuid.uuid4().hex}{Path(file.filename or '').suffix}"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f: shutil.copyfileobj(file.file, f)
    return output_path

def func_list_to_tuple(ns):
    for k, v in ns.items():
        if isinstance(v, list):
            ns[k] = tuple(v)

async def func_postgres_runner(client_postgres_pool,mode,query):
    query_lower=query.lower()
    if mode not in ["read","write"]:raise Exception("mode=read/write")
    block_word = ["drop", "truncate"]
    for item in block_word:
        if item in query_lower:
            raise Exception(f"{item} keyword not allowed in query")
    async with client_postgres_pool.acquire() as conn:
        if mode == "read":return await conn.fetch(query)
        if mode == "write":
            if "returning" in query_lower:return await conn.fetch(query)
            else:return await conn.execute(query)
    return None

async def func_postgres_ids_update(client_postgres_pool,table,ids,column,value,created_by_id=None,updated_by_id=None):
    set_clause=f"{column}=$1" if updated_by_id is None else f"{column}=$1,updated_by_id=$2"
    query=f"update {table} set {set_clause} where id in ({ids}) and ($3::bigint is null or created_by_id=$3);"
    async with client_postgres_pool.acquire() as conn:
        params=[value]
        if updated_by_id is not None:params.append(updated_by_id)
        params.append(created_by_id)
        await conn.execute(query,*params)
        
async def func_postgres_ids_delete(client_postgres_pool,table,ids,created_by_id=None):
    query=f"delete from {table} where id in ({ids}) and ($1::bigint is null or created_by_id=$1);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query,created_by_id)

async def func_postgres_parent_read(client_postgres_pool,table,parent_column,parent_table,created_by_id=None,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    query=f"with x as (select {parent_column} from {table} where ($1::bigint is null or created_by_id=$1) order by {order} limit {limit} offset {(page-1)*limit}) select ct.* from x left join {parent_table} ct on x.{parent_column}=ct.id;"
    async with client_postgres_pool.acquire() as conn:
        obj_list=await conn.fetch(query,created_by_id)
    return obj_list

import re, json
async def func_postgres_map_column(client_postgres_pool,query):
    if not query:return {}
    def parse_cols(q):
        m=re.search(r"select\s+(.*?)\s+from\s",q,flags=re.I|re.S)
        cols=[c.strip() for c in m.group(1).split(",")]
        return cols[0],cols[1:]
    c1,c2_cols=parse_cols(query);output={}
    async with client_postgres_pool.acquire() as conn:
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
async def func_postgres_clean(client_postgres_pool, config_table):
    async with client_postgres_pool.acquire() as conn:
        for table_name, cfg in config_table.items():
            days = cfg.get("retention_day")
            if days is None:continue
            threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            query = f"DELETE FROM {table_name} WHERE created_at < $1"
            await conn.execute(query, threshold_date)
    return None
        
from datetime import datetime
import json
import re
async def func_postgres_obj_read(client_postgres_pool, func_postgres_obj_serialize, cache_postgres_column_datatype, func_creator_data_add, func_action_count_add, table, obj):
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
    order, limit, page = obj.get("order", "id desc"), int(obj.get("limit", 100)), int(obj.get("page", 1))
    columns_raw = obj.get("column", "*")
    columns = "*" if columns_raw == "*" else ",".join([validate_sql_key(c.strip()) for c in columns_raw.split(",")])
    creator_key, action_key = obj.get("creator_key"), obj.get("action_key")
    filters = {k: v for k, v in obj.items() if k not in ["table", "order", "limit", "page", "column", "creator_key", "action_key"]}
    async def _serialize_single(col, val, datatype):
        if str(val).lower() == "null": return None
        res = await func_postgres_obj_serialize({col: datatype}, [{col: val}])
        return res[0][col]
    conditions, values, idx = [], [], 1
    v_ops = {"=": "=", "==": "=", "!=": "!=", "<>": "<>", ">": ">", "<": "<", ">=": ">=", "<=": "<=", "is": "IS", "is not": "IS NOT", "in": "IN", "not in": "NOT IN", "between": "BETWEEN"}
    str_ops = {"like": "LIKE", "ilike": "ILIKE", "~": "~", "~*": "~*"}
    for col_key, expr in filters.items():
        validate_sql_key(col_key)
        if expr.lower().startswith("point,"):
            try:
                _, rest = expr.split(",", 1); lon, lat, mn, mx = [float(x) for x in rest.split("|")]
                conditions.append(f"ST_Distance({col_key}, ST_Point({lon}, {lat})::geography) BETWEEN {mn} AND {mx}"); continue
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
        if op not in avail: raise Exception(f"invalid operator '{op}' for column '{col_key}' ({dtype}). available: {', '.join(avail)}")
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
            if op not in ["is", "is not"]: raise Exception(f"null requires is/is not for {col_key}")
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
    query = f"SELECT {columns} FROM {safe_table} {where} ORDER BY {order} LIMIT {limit} OFFSET {(page - 1) * limit}"
    async with client_postgres_pool.acquire() as conn:
        try:
            records = await conn.fetch(query, *values); res_list = [dict(r) for r in records]
            if creator_key and res_list: res_list = await func_creator_data_add(client_postgres_pool, res_list, creator_key)
            if action_key and res_list: res_list = await func_action_count_add(client_postgres_pool, res_list, action_key)
            return res_list
        except Exception as e: raise Exception(f"Read Error: {e}")
        
async def func_postgres_obj_update(client_postgres_pool, func_postgres_obj_serialize, cache_postgres_column_datatype, table, obj_list, is_serialize=None, created_by_id=None, batch_size=None, return_ids=False):
    if not obj_list:return None
    if not is_serialize:is_serialize=0
    if not all("id" in obj for obj in obj_list):raise Exception("all objects must have 'id' field")
    batch_size = batch_size or 5000
    if is_serialize:obj_list = await func_postgres_obj_serialize(cache_postgres_column_datatype, obj_list)
    async def postgres_update_objects(client_pool, tbl, objs, user_id=None, batch_sz=5000, ret_ids=False):
        cols = [c for c in objs[0] if c != "id"]
        if not cols:return [] if ret_ids else None
        max_batch = 65535 // (len(cols) + 1 + (1 if user_id else 0))
        batch_sz = min(batch_sz, max_batch)
        ids = [] if ret_ids else None
        async with client_pool.acquire() as conn:
            if len(objs) == 1:
                obj = objs[0]
                params = [obj[c] for c in cols] + [obj["id"]]
                where = f"id=${len(params)}" + (f" AND created_by_id=${len(params)+1}" if user_id else "")
                if user_id:params.append(user_id)
                set_clause = ",".join(f"{c}=${i+1}" for i, c in enumerate(cols))
                if ret_ids:
                    row = await conn.fetch(f"UPDATE {tbl} SET {set_clause} WHERE {where} RETURNING id;", *params)
                    return [row[0]["id"]] if row else []
                else:
                    await conn.execute(f"UPDATE {tbl} SET {set_clause} WHERE {where};", *params)
                    return None
            async with conn.transaction():
                for i in range(0, len(objs), batch_sz):
                    batch = objs[i:i+batch_sz]
                    vals, set_clauses = [], []
                    for col in cols:
                        cases = []
                        for obj in batch:
                            vals.extend([obj[col], obj["id"]])
                            idx_val, idx_id = len(vals)-1, len(vals)
                            if user_id:
                                vals.append(user_id)
                                idx_user = len(vals)
                                cases.append(f"WHEN id=${idx_id} AND created_by_id=${idx_user} THEN ${idx_val}")
                            else:
                                cases.append(f"WHEN id=${idx_id} THEN ${idx_val}")
                        set_clauses.append(f"{col} = CASE {' '.join(cases)} ELSE {col} END")
                    ids_list = [obj["id"] for obj in batch]
                    vals_offset = len(vals)
                    where_parts = [f"id IN ({','.join(f'${vals_offset+j+1}' for j in range(len(ids_list)))})"]
                    vals.extend(ids_list)
                    if user_id:
                        where_parts.append(f"created_by_id=${len(vals)+1}")
                        vals.append(user_id)
                    where_clause = " AND ".join(where_parts)
                    if ret_ids:
                        rows = await conn.fetch(f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE {where_clause} RETURNING id;", *vals)
                        ids.extend([r["id"] for r in rows])
                    else:
                        await conn.execute(f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE {where_clause};", *vals)
        return ids if ret_ids else None
    return await postgres_update_objects(client_postgres_pool, table, obj_list, created_by_id, batch_size, return_ids)

import asyncio
inmemory_cache_object_create = {}
table_object_key = {}
buffer_lock = asyncio.Lock()
async def func_postgres_obj_create(client_postgres_pool,func_postgres_obj_serialize,cache_postgres_column_datatype, mode,table=None,obj_list=None,is_serialize=None,buffer=None, returning_ids=False,conflict_columns=None,batch_size=None):
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
        conflict = f"on conflict ({','.join(conflict_cols)}) do nothing" if conflict_cols else "on conflict do nothing"
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
            return await postgres_insert_objects(client_postgres_pool, table, obj_list, returning_ids, conflict_columns, batch_size)
        elif mode == "buffer":
            if table not in inmemory_cache_object_create:inmemory_cache_object_create[table] = []
            if table not in table_object_key:table_object_key[table] = set()
            for o in obj_list:table_object_key[table].update(o.keys())
            inmemory_cache_object_create[table].extend(obj_list)
            if len(inmemory_cache_object_create[table]) >= buffer:
                objs_to_insert = inmemory_cache_object_create[table]
                inmemory_cache_object_create[table] = []
                await postgres_insert_objects(client_postgres_pool, table, objs_to_insert, returning_ids, conflict_columns, batch_size, table_object_key[table])
                return "buffer released"
            return None
        elif mode == "flush":
            results = {}
            for tbl, rows in inmemory_cache_object_create.items():
                if not rows:continue
                try:
                    schema = table_object_key.get(tbl)
                    results[tbl] = await postgres_insert_objects(client_postgres_pool, tbl, rows, returning_ids, conflict_columns, batch_size, schema)
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
async def func_postgres_stream(client_postgres_pool, query, batch_size=None):
    if not batch_size:batch_size=1000
    if not re.match(r"^\s*(SELECT|WITH|SHOW|EXPLAIN)\b", query, re.I):
        raise ValueError("Only read-only queries allowed")
    async with client_postgres_pool.acquire() as conn:
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
         
from pathlib import Path
import csv, re, uuid
async def func_postgres_export(client_postgres_pool, query, batch_size=None, output_path=None):
    if not output_path: output_path = f"export/{uuid.uuid4().hex}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if not re.match(r"^\s*(SELECT|WITH|SHOW|EXPLAIN)\b", query, re.I): raise Exception("Only read-only queries allowed")
    f, batch_size = None, batch_size or 1000
    try:
        async with client_postgres_pool.acquire() as conn, conn.transaction():
            writer = None
            async for r in conn.cursor(query, prefetch=batch_size):
                if not writer:
                    f = open(output_path, "w", newline="", encoding="utf-8")
                    writer = csv.writer(f); writer.writerow(r.keys())
                writer.writerow(r.values())
    finally:
        if f: f.close()
    return output_path

async def func_postgres_init_schema(client_postgres_pool,config_postgres,func_postgres_schema_read):
    if not config_postgres or "table" not in config_postgres: raise Exception("config_postgres.table missing")
    async def _validate():
        seen=set()
        for t,cols in config_postgres["table"].items():
            if not isinstance(cols,(list,tuple)): raise Exception(f"table config must be list {t}")
            names={c.get("name") for c in cols}
            for c in cols:
                allowed={"name","datatype","old","default","is_mandatory","index","unique","in","is_trim","is_lowercase"}
                if not isinstance(c,dict): raise Exception(f"column config must be dict {t}")
                if not {"name","datatype"}<=c.keys(): raise Exception(f"missing required keys {t}.{c}")
                if set(c)-allowed: raise Exception(f"unknown keys {t}.{c.get('name')}:{set(c)-allowed}")
                if c.get("index"):
                    for it in c["index"].split(","):
                        if it=="gin" and not any(x in c["datatype"].lower() for x in ("text","[]","jsonb")): raise Exception(f"gin not supported {t}.{c['name']}:{c['datatype']}")
                u=c.get("unique")
                if not u: continue
                for g in (x.strip() for x in u.split("|") if x.strip()):
                    ucols=[x.strip() for x in g.split(",") if x.strip()]
                    for x in ucols:
                        if x not in names: raise Exception(f"unique column not found {t}.{x}")
                    key=(t,tuple(sorted(ucols)))
                    if key in seen: raise Exception(f"duplicate unique {t}.{','.join(ucols)}")
                    seen.add(key)
    async def func_init_extension(conn):
        for e in ("postgis","pg_trgm"): await conn.execute(f"create extension if not exists {e};")
        await conn.execute("create or replace function array_all_lowercase(text[]) returns boolean immutable as $$ select coalesce(bool_and(v=lower(v)),true) from unnest($1) v $$ language sql;")
        await conn.execute("create or replace function array_all_trimmed(text[]) returns boolean immutable as $$ select coalesce(bool_and(v=trim(v)),true) from unnest($1) v $$ language sql;")
    async def func_init_table(conn,db):
        for t in config_postgres["table"]:
            if t not in db: await conn.execute(f"create table {t} (id bigint primary key generated by default as identity not null);")
    async def func_init_column_rename(conn,db):
        for t,cols in config_postgres["table"].items():
            have=db.get(t,{})
            for c in cols:
                if c.get("old") and c["name"] not in have and c["old"] in have: await conn.execute(f"alter table {t} rename column {c['old']} to {c['name']};")
    async def func_init_column(conn,db):
        for t,cols in config_postgres["table"].items():
            have=db.get(t,{})
            for c in cols:
                if c["name"] not in have: await conn.execute(f"alter table {t} add column {c['name']} {c['datatype']};")
    async def func_init_drop_column(conn,db):
        for t,cols in config_postgres["table"].items():
            want={c["name"] for c in cols}; have=set(db.get(t,{}))
            for col in have-want:
                if col!="id": await conn.execute(f"alter table {t} drop column {col} cascade;")
    async def func_init_default(conn,db):
        for t,cols in config_postgres["table"].items():
            have=db.get(t,{})
            for col,data in have.items():
                if col=="id": continue
                conf=next((c for c in cols if c["name"]==col), None)
                if data["default"] is not None and (not conf or "default" not in conf): await conn.execute(f"alter table {t} alter column {col} drop default;")
            for c in cols:
                if "default" in c:
                    d,col=c["default"],c["name"]; sql=d if isinstance(d,str) and d.endswith("()") else repr(d) if isinstance(d,str) else str(d)
                    await conn.execute(f"alter table {t} alter column {col} set default {sql};")
    async def func_init_nullable(conn,db):
        for t,cols in config_postgres["table"].items():
            for c in cols:
                cur=db.get(t,{}).get(c["name"])
                if not cur: continue
                m=c.get("is_mandatory",0)
                if m in (0,False) and cur["is_null"]==0: await conn.execute(f"alter table {t} alter column {c['name']} drop not null;")
                if m in (1,True) and cur["is_null"]==1: await conn.execute(f"alter table {t} alter column {c['name']} set not null;")
    async def func_init_index(conn,dtypes):
        rows=await conn.fetch("select indexname,indexdef from pg_indexes where schemaname='public';"); have={}
        for r in rows:
            if " USING " not in r["indexdef"]: continue
            tbl=r["indexdef"].split(" ON ")[1].split()[0].split(".")[-1]; col=r["indexdef"].split("(",1)[1].split(")",1)[0].split()[0]; it=r["indexdef"].split(" USING ")[1].split()[0].lower()
            have.setdefault((tbl,col),{})[it]=r["indexname"]
        for t,cols in config_postgres["table"].items():
            for c in cols:
                want=set() if not c.get("index") else set(c["index"].split(",")); cur=have.get((t,c["name"]),{}); dt=dtypes.get(c["name"],"").lower()
                if any(x in dt for x in ("geography","geometry")): want.add("gist")
                if c.get("old"):
                    for it,idx in have.get((t,c["old"]),{}).items():
                        if it not in cur: cur[it]=idx
                for it,n in cur.items():
                    is_managed=n.startswith(f"index_{t}_{c['name']}") or (c.get("old") and n.startswith(f"index_{t}_{c['old']}"))
                    if is_managed and it not in want: await conn.execute(f'drop index if exists "{n}"')
                for it in want:
                    name=f"index_{t}_{c['name']}_{it}"[:55]
                    if cur.get(it)==name: continue
                    if it in cur: await conn.execute(f'drop index if exists "{cur[it]}"')
                    col_def=f"{c['name']} gin_trgm_ops" if it=="gin" and "text" in dt and "[]" not in dt and "array" not in dt else c["name"]
                    await conn.execute(f"create index concurrently if not exists {name} on {t} using {it} ({col_def});")
    async def func_init_constraints(conn,db,dtypes):
        rows=await conn.fetch("select constraint_name,table_name from information_schema.table_constraints where constraint_schema='public';")
        have={(r["table_name"],r["constraint_name"].lower()) for r in rows}
        for t,cols in config_postgres["table"].items():
            want=set()
            for c in cols:
                if c.get("is_trim"): want.add(f"constraint_{t}_{c['name']}_trim")
                if c.get("is_lowercase"): want.add(f"constraint_{t}_{c['name']}_lowercase")
                if "in" in c: want.add(f"constraint_{t}_{c['name']}_in")
                if c.get("unique"):
                    for g in c["unique"].split("|"): want.add(f"constraint_unique_{t}_{'_'.join(x.strip() for x in g.split(','))}")
            for tbl,cname in have:
                if tbl!=t or not cname.startswith("constraint_"): continue
                is_old=any(cname in (f"constraint_{t}_{c['old']}_trim",f"constraint_{t}_{c['old']}_lowercase",f"constraint_{t}_{c['old']}_in") for c in cols if c.get("old"))
                if cname not in {x.lower() for x in want} and not is_old: await conn.execute(f'alter table {t} drop constraint if exists "{cname}" cascade;')
        rows=await conn.fetch("select constraint_name,table_name from information_schema.table_constraints where constraint_schema='public';")
        have={(r["table_name"],r["constraint_name"].lower()) for r in rows}
        for t,cols in config_postgres["table"].items():
            for c in cols:
                col,dt,old=c["name"],dtypes.get(c["name"],"").lower(),c.get("old")
                checks=[
                    ("is_trim",f"constraint_{t}_{col}_trim",f"constraint_{t}_{old}_trim" if old else None,f"check ({col}=trim({col}))" if "text" in dt and "[]" not in dt else f"check (array_all_trimmed({col}))" if "[]" in dt and "text" in dt else None),
                    ("is_lowercase",f"constraint_{t}_{col}_lowercase",f"constraint_{t}_{old}_lowercase" if old else None,f"check ({col}=lower({col}))" if "text" in dt and "[]" not in dt else f"check (array_all_lowercase({col}))" if "[]" in dt and "text" in dt else None),
                    ("in",f"constraint_{t}_{col}_in",f"constraint_{t}_{old}_in" if old else None,f"check ({col} in ({','.join(str(x) if isinstance(x,(int,float)) else repr(x) for x in c.get('in',[]))}))" if "in" in c else None)
                ]
                for key,n,old_n,sql in checks:
                    if not c.get(key) or not sql: continue
                    if old_n and (t,old_n.lower()) in have:
                        await conn.execute(f'alter table {t} rename constraint "{old_n}" to "{n}";')
                        have.add((t,n.lower())); have.remove((t,old_n.lower()))
                    if (t,n.lower()) not in have: await conn.execute(f"alter table {t} add constraint {n} {sql};")
                if c.get("unique"):
                    for g in c["unique"].split("|"):
                        ucols=",".join(x.strip() for x in g.split(",")); n=f"constraint_unique_{t}_{ucols.replace(',','_')}"
                        if (t,n.lower()) not in have: await conn.execute(f"alter table {t} add constraint {n} unique ({ucols});")
    async def func_init_custom_sql(conn):
        for k,sql in config_postgres.get("sql",{}).items(): await conn.execute(sql)
    await _validate()
    db,dtypes=await func_postgres_schema_read(client_postgres_pool)
    async with client_postgres_pool.acquire() as conn:
        await func_init_extension(conn); await func_init_table(conn,db); await func_init_column_rename(conn,db)
        db,dtypes=await func_postgres_schema_read(client_postgres_pool)
        await func_init_column(conn,db); await func_init_drop_column(conn,db)
        db,dtypes=await func_postgres_schema_read(client_postgres_pool)
        await func_init_default(conn,db); await func_init_nullable(conn,db); await func_init_index(conn,dtypes); await func_init_constraints(conn,db,dtypes); await func_init_custom_sql(conn)
    return None

import hashlib,json,uuid
from dateutil import parser
async def func_postgres_obj_serialize(cache_postgres_column_datatype,obj_list):
    for obj in obj_list:
        for k,v in obj.items():
            if v in (None,"","null"):obj[k]=None;continue
            d=cache_postgres_column_datatype.get(k)
            if not d:continue
            try:
                if k=="password":obj[k]=hashlib.sha256(str(v).encode()).hexdigest()
                elif "uuid" in d:obj[k]=str(uuid.UUID(v)) if isinstance(v,str) else str(v)
                elif "bytea" in d:obj[k]=v.encode() if isinstance(v,str) else v
                elif "bool" in d:obj[k]=v if isinstance(v,bool) else (str(v).lower() in ("true","t","1","yes"))
                elif "[]" in d:
                    if isinstance(v,list):ls=v
                    else:
                        s=str(v).strip()
                        if s.startswith('{') and s.endswith('}'):s=s[1:-1]
                        elif s.startswith('[') and s.endswith(']'):s=s[1:-1]
                        ls=[i.strip().strip('"').strip("'") for i in s.split(",") if i.strip()]
                    obj[k]=[int(i) for i in ls] if any(y in d for y in ("int","serial")) else [str(i) for i in ls]
                elif any(x in d for x in ("text","char","enum","geography","geometry")):obj[k]=str(v).strip()
                elif any(x in d for x in ("int","serial")) and "point" not in d:obj[k]=int(v)
                elif any(x in d for x in ("numeric","double","precision","real")):obj[k]=round(float(v),3)
                elif d=="date":obj[k]=parser.isoparse(v).date() if isinstance(v,str) else v
                elif "timestamp" in d or "time" in d:obj[k]=parser.isoparse(v) if isinstance(v,str) else v
                elif "json" in d:
                    if isinstance(v,(dict,list)):obj[k]=json.dumps(v,separators=(",",":"))
                    else:
                        try:json.loads(v);obj[k]=v
                        except:obj[k]=json.dumps(v)
            except Exception as e:raise Exception(f"serialize_error:{k}:{d}:{str(e)}")
    return obj_list

async def func_postgres_schema_read(client_postgres_pool):
    query="SELECT t.relname AS table_name, a.attname AS column_name, format_type(a.atttypid, a.atttypmod) AS data_type, pg_get_expr(d.adbin, d.adrelid) AS column_default, CASE WHEN a.attnotnull THEN 0 ELSE 1 END AS is_nullable, CASE WHEN EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = a.attrelid AND a.attnum = ANY(i.indkey)) THEN 1 ELSE 0 END AS is_index FROM pg_class t JOIN pg_namespace n ON n.oid = t.relnamespace JOIN pg_attribute a ON a.attrelid = t.oid LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum WHERE t.relkind = 'r' AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped ORDER BY t.relname, a.attnum;"
    async with client_postgres_pool.acquire() as conn: output=await conn.fetch(query)
    postgres_schema,postgres_column_datatype={},{}
    for obj in output:
        t,c,dt=obj['table_name'],obj['column_name'],obj['data_type'].lower()
        if t not in postgres_schema: postgres_schema[t]={}
        postgres_schema[t][c]={"datatype":dt,"default":obj['column_default'],"is_null":obj['is_nullable'],"is_index":obj['is_index']}
        postgres_column_datatype[c]=dt
    return postgres_schema,postgres_column_datatype

import asyncpg
async def func_postgres_client_read(config_postgres_url,config_postgres_min_connection=None,config_postgres_max_connection=None,timeout=None,command_timeout=None):
    if not config_postgres_min_connection:config_postgres_min_connection=5
    if not config_postgres_max_connection:config_postgres_max_connection=20
    if not timeout:timeout=60
    if not command_timeout:command_timeout=60
    client_postgres_pool=await asyncpg.create_pool(dsn=config_postgres_url,min_size=config_postgres_min_connection,max_size=config_postgres_max_connection,timeout=timeout,command_timeout=command_timeout)
    return client_postgres_pool

import random
from mimesis import Person,Address,Food,Text,Code,Datetime
async def func_postgres_create_fake_data(client_postgres_pool,total_row=None,batch_size=None):
    if not total_row:total_row=1000
    if not batch_size:batch_size=1000
    person,address,food,text_gen,code,dt = Person(),Address(),Food(),Text(),Code(),Datetime()
    tables = {
    "customers": [("name", "TEXT", lambda: person.full_name()), ("email", "TEXT", lambda: person.email()), ("city", "TEXT", lambda: address.city()), ("country", "TEXT", lambda: address.country()), ("birth_date", "DATE", lambda: dt.date()), ("signup_code", "TEXT", lambda: code.imei()), ("loyalty_points", "INT", lambda: random.randint(0, 10000)), ("favorite_fruit", "TEXT", lambda: food.fruit())],
    "orders": [("order_number", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("order_date", "DATE", lambda: dt.date()), ("shipping_city", "TEXT", lambda: address.city()), ("total_amount", "INT", lambda: random.randint(10, 5000)), ("status", "TEXT", lambda: random.choice(["pending", "shipped", "delivered", "cancelled"])), ("item_count", "INT", lambda: random.randint(1, 20)), ("shipping_country", "TEXT", lambda: address.country())],
    "products": [("product_name", "TEXT", lambda: food.fruit()), ("category", "TEXT", lambda: random.choice(["electronics", "clothing", "food", "books"])), ("price", "INT", lambda: random.randint(5, 1000)), ("supplier_city", "TEXT", lambda: address.city()), ("stock_quantity", "INT", lambda: random.randint(0, 500)), ("manufacture_date", "DATE", lambda: dt.date()), ("expiry_date", "DATE", lambda: dt.date()), ("sku_code", "TEXT", lambda: code.imei())],
    "employees": [("full_name", "TEXT", lambda: person.full_name()), ("email", "TEXT", lambda: person.email()), ("department", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Marketing"])), ("city", "TEXT", lambda: address.city()), ("salary", "INT", lambda: random.randint(30000, 150000)), ("hire_date", "DATE", lambda: dt.date()), ("employee_id", "TEXT", lambda: code.imei())],
    "suppliers": [("supplier_name", "TEXT", lambda: person.full_name()), ("contact_email", "TEXT", lambda: person.email()), ("city", "TEXT", lambda: address.city()), ("country", "TEXT", lambda: address.country()), ("phone_number", "TEXT", lambda: person.telephone()), ("rating", "INT", lambda: random.randint(1, 5))],
    "invoices": [("invoice_number", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("invoice_date", "DATE", lambda: dt.date()), ("amount_due", "INT", lambda: random.randint(100, 10000)), ("due_date", "DATE", lambda: dt.date()), ("status", "TEXT", lambda: random.choice(["paid", "unpaid", "overdue"]))],
    "payments": [("payment_id", "TEXT", lambda: code.imei()), ("invoice_number", "TEXT", lambda: code.imei()), ("payment_date", "DATE", lambda: dt.date()), ("amount", "INT", lambda: random.randint(50, 10000)), ("payment_method", "TEXT", lambda: random.choice(["credit_card", "paypal", "bank_transfer"])), ("status", "TEXT", lambda: random.choice(["completed", "pending", "failed"]))],
    "departments": [("department_name", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Marketing"])), ("manager", "TEXT", lambda: person.full_name()), ("location", "TEXT", lambda: address.city()), ("budget", "INT", lambda: random.randint(50000, 1000000))],
    "projects": [("project_name", "TEXT", lambda: text_gen.word()), ("start_date", "DATE", lambda: dt.date()), ("end_date", "DATE", lambda: dt.date()), ("budget", "INT", lambda: random.randint(10000, 500000)), ("department", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Marketing"]))],
    "inventory": [("item_name", "TEXT", lambda: food.spices()), ("quantity", "INT", lambda: random.randint(0, 1000)), ("warehouse_location", "TEXT", lambda: address.city()), ("last_restock_date", "DATE", lambda: dt.date())],
    "shipments": [("shipment_id", "TEXT", lambda: code.imei()), ("order_number", "TEXT", lambda: code.imei()), ("shipment_date", "DATE", lambda: dt.date()), ("delivery_date", "DATE", lambda: dt.date()), ("status", "TEXT", lambda: random.choice(["in_transit", "delivered", "delayed"]))],
    "reviews": [("review_id", "TEXT", lambda: code.imei()), ("product_name", "TEXT", lambda: food.fruit()), ("customer_name", "TEXT", lambda: person.full_name()), ("rating", "INT", lambda: random.randint(1, 5)), ("review_date", "DATE", lambda: dt.date()), ("comments", "TEXT", lambda: text_gen.sentence())],
    "tasks": [("task_name", "TEXT", lambda: text_gen.word()), ("assigned_to", "TEXT", lambda: person.full_name()), ("due_date", "DATE", lambda: dt.date()), ("priority", "TEXT", lambda: random.choice(["low", "medium", "high"])), ("status", "TEXT", lambda: random.choice(["pending", "in_progress", "completed"]))],
    "assets": [("asset_tag", "TEXT", lambda: code.imei()), ("asset_name", "TEXT", lambda: food.fruit()), ("purchase_date", "DATE", lambda: dt.date()), ("warranty_expiry", "DATE", lambda: dt.date()), ("value", "INT", lambda: random.randint(100, 10000))],
    "locations": [("location_name", "TEXT", lambda: address.city()), ("address", "TEXT", lambda: address.address()), ("country", "TEXT", lambda: address.country()), ("postal_code", "TEXT", lambda: address.postal_code())],
    "meetings": [("meeting_id", "TEXT", lambda: code.imei()), ("topic", "TEXT", lambda: text_gen.word()), ("meeting_date", "DATE", lambda: dt.date()), ("organizer", "TEXT", lambda: person.full_name()), ("location", "TEXT", lambda: address.city())],
    "tickets": [("ticket_id", "TEXT", lambda: code.imei()), ("issue", "TEXT", lambda: text_gen.sentence()), ("reported_by", "TEXT", lambda: person.full_name()), ("status", "TEXT", lambda: random.choice(["open", "closed", "in_progress"])), ("priority", "TEXT", lambda: random.choice(["low", "medium", "high"]))],
    "subscriptions": [("subscription_id", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("start_date", "DATE", lambda: dt.date()), ("end_date", "DATE", lambda: dt.date()), ("plan_type", "TEXT", lambda: random.choice(["basic", "premium", "enterprise"]))],
    }
    async def create_tables(conn,tables):
        for table_name, columns in tables.items():
            await conn.execute(f"DROP TABLE IF EXISTS {table_name};")
            columns_def = ", ".join(f"{name} {dtype}" for name, dtype, _ in columns)
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id bigint primary key generated always as identity not null, {columns_def});")
    async def insert_batch(conn, table_name, columns, batch_values):
        cols = ", ".join(name for name, _, _ in columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        await conn.executemany(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", batch_values)
    async def generate_data(conn,insert_batch,tables,total_row,batch_size):
        for table_name, columns in tables.items():
            print(f"Inserting data into {table_name}...")
            batch_values = []
            for _ in range(total_row):
                batch_values.append(tuple(gen() for _, _, gen in columns))
                if len(batch_values) == batch_size:
                    await insert_batch(conn, table_name, columns, batch_values)
                    batch_values.clear()
            if batch_values:await insert_batch(conn, table_name, columns, batch_values)
            print(f"Completed inserting {total_row} rows into {table_name}")
    async with client_postgres_pool.acquire() as conn:
        await create_tables(conn,tables)
        await generate_data(conn,insert_batch,tables,total_row,batch_size)
    return None

import redis.asyncio as redis
async def func_redis_client_read(config_redis_url):
   client_redis=redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))
   return client_redis

async def func_redis_client_read_consumer(client_redis,config_channel_name):
   client_redis_consumer=client_redis.pubsub()
   await client_redis_consumer.subscribe(config_channel_name)
   return client_redis_consumer

import json
async def func_redis_producer(client_redis,config_channel_name,payload):
   output=await client_redis.publish(config_channel_name,json.dumps(payload))
   return output

import json
async def func_redis_object_read(client_redis,key):
   output=await client_redis.get(key)
   if output:output=json.loads(output)
   return output

async def func_redis_object_create(client_redis,key_list,obj_list,expiry_sec):
   async with client_redis.pipeline(transaction=True) as pipe:
      for index,obj in enumerate(obj_list):
         key=key_list[index]
         if not expiry_sec:pipe.set(key,json.dumps(obj))
         else:pipe.setex(key,expiry_sec,json.dumps(obj))
      await pipe.execute()
   return None

async def func_redis_object_delete(client_redis,obj_list):
   async with client_redis.pipeline(transaction=True) as pipe:
      for obj in obj_list:
         pipe.delete(obj["key"])
      await pipe.execute()
   return None

import boto3
async def func_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name):
   client_ses=boto3.client("ses",region_name=config_ses_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_ses

async def func_ses_send_email(client_ses,email_from,email_to_list,title,body):
   client_ses.send_email(Source=email_from,Destination={"ToAddresses":email_to_list},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return None

async def func_sns_send_mobile_message(client_sns,mobile,message):
   client_sns.publish(PhoneNumber=mobile,Message=message)
   return None

async def func_sns_send_mobile_message_template(client_sns,mobile,message,template_id,entity_id,sender_id):
   client_sns.publish(PhoneNumber=mobile, Message=message,MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

import boto3
async def func_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name):
   client_sns=boto3.client("sns",region_name=config_sns_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_sns

import boto3
async def func_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name):
   client_s3=boto3.client("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   client_s3_resource=boto3.resource("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_s3,client_s3_resource

async def func_s3_bucket_create(client_s3,config_s3_region_name,bucket):
   output=client_s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':config_s3_region_name})
   return output

async def func_s3_url_delete(client_s3_resource,url):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=client_s3_resource.Object(bucket,key).delete()
   return output

async def func_s3_bucket_public(client_s3,bucket):
   client_s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=client_s3.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def func_s3_bucket_empty(client_s3_resource,bucket):
   output=client_s3_resource.Bucket(bucket).objects.all().delete()
   return output

async def func_s3_bucket_delete(client_s3,bucket):
   output=client_s3.delete_bucket(Bucket=bucket)
   return output

import uuid
from io import BytesIO
async def func_s3_upload(client_s3,config_s3_region_name,bucket,file,key=None,config_limit_s3_kb=None):
    if not config_limit_s3_kb:config_limit_s3_kb=100
    if not key:
        if "." not in file.filename:raise Exception("file must have extension")
        key=f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}"
    if "." not in key:raise Exception("extension must")
    file_content=await file.read()
    file.file.close()
    file_size_kb=round(len(file_content)/1024)
    if file_size_kb>config_limit_s3_kb:raise Exception("file size issue")
    client_s3.upload_fileobj(BytesIO(file_content),bucket,key)
    output={file.filename:f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"}
    return output

import uuid
async def func_s3_upload_presigned(client_s3,config_s3_region_name,bucket,key=None,config_limit_s3_kb=None,config_s3_presigned_expire_sec=None):
   if not config_limit_s3_kb:config_limit_s3_kb=100
   if not config_s3_presigned_expire_sec:config_s3_presigned_expire_sec=100
   if not key:key=f"{uuid.uuid4().hex}.bin"
   if "." not in key:raise Exception("extension must")
   output=client_s3.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=config_s3_presigned_expire_sec,Conditions=[['content-length-range',1,config_limit_s3_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"
   return output

from celery import Celery
async def func_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url):
   client_celery_producer=Celery("producer",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_producer

from celery import Celery
def func_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url):
   client_celery_consumer=Celery("worker",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_consumer

async def func_celery_producer(client_celery_producer,func,param_list):
   output=client_celery_producer.send_task(func,args=param_list)
   return output.id

import aio_pika
async def func_rabbitmq_client_read_producer(config_rabbitmq_url):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_producer=await client_rabbitmq.channel()
   return client_rabbitmq,client_rabbitmq_producer

import aio_pika
async def func_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_channel=await client_rabbitmq.channel()
   client_rabbitmq_consumer=await client_rabbitmq_channel.declare_queue(config_channel_name,auto_delete=False)
   return client_rabbitmq,client_rabbitmq_consumer

import json,aio_pika
async def func_rabbitmq_producer(client_rabbitmq_producer,config_channel_name,payload):
    payload=json.dumps(payload).encode()
    message=aio_pika.Message(body=payload)
    output=await client_rabbitmq_producer.default_exchange.publish(message,routing_key=config_channel_name)
    return output

from aiokafka import AIOKafkaProducer
async def func_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password):
    client_kafka_producer=AIOKafkaProducer(bootstrap_servers=config_kafka_url,security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,)
    await client_kafka_producer.start()
    return client_kafka_producer
 
from aiokafka import AIOKafkaConsumer
async def func_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_kafka_group_id,config_kafka_enable_auto_commit):
    client_kafka_consumer=AIOKafkaConsumer(config_channel_name,bootstrap_servers=config_kafka_url,group_id=config_kafka_group_id, security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,auto_offset_reset="earliest",enable_auto_commit=config_kafka_enable_auto_commit)
    await client_kafka_consumer.start()
    return client_kafka_consumer
 
import json
async def func_kafka_producer(client_kafka_producer,config_channel_name,payload):
   output=await client_kafka_producer.send_and_wait(config_channel_name,json.dumps(payload,indent=2).encode('utf-8'),partition=0)
   return output

async def func_handler_ratelimiter(request):
    if not request.app.state.config_api.get(request.url.path,{}).get("ratelimiter_times_sec"):return None
    client_redis_ratelimiter=request.app.state.client_redis_ratelimiter
    if not client_redis_ratelimiter:raise Exception("config_redis_url_ratelimiter missing")
    limit,window=request.app.state.config_api.get(request.url.path).get("ratelimiter_times_sec")
    identifier=request.state.user.get("id") if request.state.user else request.client.host
    ratelimiter_key=f"ratelimiter:{request.url.path}:{identifier}"
    current_count=await client_redis_ratelimiter.get(ratelimiter_key)
    if current_count and int(current_count)+1>limit:raise Exception("ratelimiter exceeded")
    pipe=client_redis_ratelimiter.pipeline()
    pipe.incr(ratelimiter_key)
    if not current_count:pipe.expire(ratelimiter_key,window)
    await pipe.execute()
    return None

async def func_handler_is_active(request):
    if not request.app.state.config_api.get(request.url.path,{}).get("is_active_check")==1 or not request.state.user:return None
    if request.app.state.config_mode_check_is_active=="token":user_is_active=request.state.user.get("is_active","absent")
    elif request.app.state.config_mode_check_is_active=="cache":user_is_active=request.app.state.cache_users_is_active.get(request.state.user["id"],"absent")
    else:raise Exception("config_mode_check_is_active=token/cache")
    if user_is_active=="absent":
        async with request.app.state.client_postgres_pool.acquire() as conn:
            rows=await conn.fetch("select id,is_active from users where id=$1",request.state.user["id"])
        user=rows[0] if rows else None
        if not user:raise Exception("user not found")
        user_is_active=user["is_active"]
    if user_is_active==0:raise Exception("user not active")
    return None

async def func_handler_admin(request):
    if not request.url.path.startswith("/admin"):return None
    def parse_access_list(access_str):return [int(item.strip()) for item in access_str.split(",")] if access_str else []
    async def fetch_user_access(user_id):
        async with request.app.state.client_postgres_pool.acquire() as conn:rows = await conn.fetch("select id,api_access from users where id=$1", user_id)
        if not rows:raise Exception("user not found")
        return rows[0]["api_access"]
    def get_cached_access():
        if request.app.state.config_mode_check_api_access == "token":return request.state.user.get("api_access", [])
        elif request.app.state.config_mode_check_api_access == "cache":return request.app.state.cache_users_api_access.get(request.state.user["id"], [])
        raise Exception("config_mode_check_api_access=token/cache")
    user_api_access = get_cached_access()
    if not user_api_access:
        user_api_access = await fetch_user_access(request.state.user["id"])
        if not user_api_access:raise Exception("api access denied")
    user_api_access_list = parse_access_list(user_api_access)
    api_id = request.app.state.config_api.get(request.url.path, {}).get("id")
    if not api_id:raise Exception("api id not mapped")
    if api_id not in user_api_access_list:raise Exception("api access denied")
    return None

from fastapi import Response
import gzip, base64, time
inmemory_cache_api = {}
async def func_handler_cache(mode,request,response):
    def should_cache(expire_sec): return expire_sec is not None and expire_sec > 0
    def build_cache_key(path, qp, uid): return f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(qp.items()))}:{uid}"
    def compress(body): return base64.b64encode(gzip.compress(body)).decode()
    def decompress(data): return gzip.decompress(base64.b64decode(data)).decode()
    if mode not in ["get","set"]: raise Exception("mode=get/set")
    uid = request.state.user.get("id") if "my/" in request.url.path else 0
    cache_key = build_cache_key(request.url.path, request.query_params, uid)
    cache_mode, expire_sec = request.app.state.config_api.get(request.url.path, {}).get("cache_sec", (None, None))
    if not should_cache(expire_sec): return None if mode == "get" else response
    if mode == "get":
        data = None
        if cache_mode == "redis": data = await request.app.state.client_redis.get(cache_key)
        elif cache_mode == "inmemory":
            item = inmemory_cache_api.get(cache_key)
            if item and item["expire_at"] > time.time(): data = item["data"]
        if data: return Response(decompress(data), status_code=200, media_type="application/json", headers={"x-cache":"hit"})
        return None
    elif mode == "set":
        body = getattr(response, "body", None)
        if body is None: body = b"".join([c async for c in response.body_iterator])
        comp = compress(body)
        if cache_mode == "redis": await request.app.state.client_redis.setex(cache_key, expire_sec, comp)
        elif cache_mode == "inmemory": inmemory_cache_api[cache_key] = {"data": comp, "expire_at": time.time() + expire_sec}
        return Response(content=body, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))
    
from fastapi import Request,responses
from starlette.background import BackgroundTask
async def func_handler_api_response_background(request,api_function):
   body=await request.body()
   async def receive():return {"type":"http.request","body":body}
   async def api_func_new():
      request_new=Request(scope=request.scope,receive=receive)
      await api_function(request_new)
   response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
   response.background=BackgroundTask(api_func_new)
   return response

async def func_handler_api_response(request,api_function):
    cache_sec=request.app.state.config_api.get(request.url.path,{}).get("cache_sec")
    response,type=None,None
    if request.query_params.get("is_background")=="1":response=await request.app.state.func_handler_api_response_background(request,api_function);type=1
    elif cache_sec:response=await request.app.state.func_handler_cache("get",request,None);type=2
    if not response:
        response=await api_function(request);type=3
        if cache_sec:response=await request.app.state.func_handler_cache("set",request,response);type=4
    return response,type

async def func_handler_token(request):
    user={}
    api=request.url.path
    token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and request.headers.get("Authorization").startswith("Bearer ") else None
    if api.startswith("/root"):
        if not token:raise Exception("token missing")
        if token!=request.app.state.config_key_root:raise Exception("token mismatch")
    elif api.startswith("/protected"):
        if not token:raise Exception("token missing")
        if token!=request.app.state.cache_config["config_api"][api]["password"]:raise Exception("token mismatch")
    else:
        if token:user=await request.app.state.func_jwt_token_decode(token,request.app.state.config_key_jwt)
        if api.startswith("/my") and not token:raise Exception("token missing")
        elif api.startswith("/private") and not token:raise Exception("token missing")
        elif api.startswith("/admin") and not token:raise Exception("token missing")
        elif request.app.state.config_api.get(api,{}).get("is_token")==1 and not token:raise Exception("token missing")
    return user

import jwt,json
async def func_jwt_token_decode(token,config_key_jwt):
   user=json.loads(jwt.decode(token,config_key_jwt,algorithms="HS256")["data"])
   return user

import jwt,json,time
async def func_jwt_token_encode(obj,config_key_jwt,config_token_expire_sec=1000,key_list=None):
   if not isinstance(obj,dict):obj=dict(obj)
   payload={k:obj.get(k) for k in key_list} if key_list else obj
   payload=json.dumps(payload,default=str)
   token=jwt.encode({"exp":time.time()+config_token_expire_sec,"data":payload},config_key_jwt)
   return token

from fastapi import FastAPI
def func_app_create(lifespan,config_is_debug_fastapi):
   app=FastAPI(debug=True if config_is_debug_fastapi else False,lifespan=lifespan)
   return app

import uvicorn
async def func_server_start(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info")
   server=uvicorn.Server(config)
   await server.serve()
   
from fastapi.middleware.cors import CORSMiddleware
def func_app_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials):
   app.add_middleware(CORSMiddleware,allow_origins=config_cors_origin_list,allow_methods=config_cors_method_list,allow_headers=config_cors_headers_list,allow_credentials=config_cors_allow_credentials)
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
def func_app_add_sentry(config_sentry_dsn):
   sentry_sdk.init(dsn=config_sentry_dsn,integrations=[FastApiIntegration()],traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)
   return None

import sys
import importlib.util
from pathlib import Path
import traceback
def func_app_add_router(app, folder_path):
    router_root = Path(folder_path).resolve()
    if not router_root.is_dir():
        raise ValueError(f"router folder not found: {router_root}")
    def load_module(file_path):
        try:
            rel = file_path.relative_to(router_root)
            module_name = "routers." + ".".join(rel.with_suffix("").parts)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            if hasattr(module, "router"):
                app.include_router(module.router)
        except Exception:
            print(f"[WARN] failed to load router: {file_path}")
            traceback.print_exc()
    for file_path in router_root.rglob("*.py"):
        if not file_path.name.startswith("__"):
            load_module(file_path)
    return None

async def func_ownership_check(client_postgres_pool,table,id,user_id):
    if table == "users":
        if id != user_id:raise Exception("obj ownership issue")
    else:
        query = f"SELECT created_by_id FROM {table} WHERE id = $1;"
        row = await client_postgres_pool.fetchrow(query, id)
        if not row:raise Exception("no obj")
        if row["created_by_id"] != user_id:raise Exception("obj ownership issue")
    return None

async def func_user_sql_read(client_postgres_pool,config_sql,user_id):
    obj = config_sql.get("user", {})
    output = {}
    async with client_postgres_pool.acquire() as conn:
        for key, query in obj.items():
            rows = await conn.fetch(query, user_id)
            output[key] = [dict(r) for r in rows]
    return output

async def func_api_usage_read(client_postgres_pool, days, created_by_id=None):
    query="select api,count(*) from log_api where created_at >= now() - ($1 * interval '1 day') and ($2::bigint is null or created_by_id=$2) group by api limit 1000;"
    async with client_postgres_pool.acquire() as conn:
        obj_list=await conn.fetch(query,days,created_by_id)
    return obj_list

async def func_creator_data_add(client_postgres_pool, obj_list, creator_key):
    if not obj_list or not creator_key:return obj_list
    creator_key_list=creator_key.split(",")
    obj_list = [dict(obj) for obj in obj_list]
    created_by_ids = {str(obj["created_by_id"]) for obj in obj_list if obj.get("created_by_id")}
    users = {}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id = ANY($1);"
        rows = await client_postgres_pool.fetch(query, list(map(int, created_by_ids)))
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

async def func_action_count_add(client_postgres_pool, obj_list, action_key):
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
        rows = await client_postgres_pool.fetch(query, list(ids))
        action_values = {str(row["id"]): row["value"] for row in rows}
    for obj in obj_list:
        obj_id = str(obj.get("id"))
        obj[f"{table}_{operator}"] = action_values.get(obj_id, 0 if operator == "count" else None)
    return obj_list

async def func_user_single_delete(mode,client_postgres_pool,user_id):
    if mode == "soft":query = "UPDATE users SET is_deleted=1 WHERE id=$1;"
    elif mode == "hard":query = "DELETE FROM users WHERE id=$1;"
    else:raise Exception("mode=soft/hard")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, user_id)
    return None

async def func_user_single_read(client_postgres_pool,user_id):
    query = "SELECT * FROM users WHERE id=$1;"
    async with client_postgres_pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id)
    user = dict(row) if row else None
    if not user:
        raise Exception("user not found")
    return user

import random
async def func_otp_generate(client_postgres_pool,email,mobile):
    if not email and not mobile:raise Exception("email/mobile any one is must")
    if email and mobile:raise Exception("only one of email or mobile is allowed")
    otp=random.randint(100000,999999)
    if email:
        query="insert into otp (otp,email) values ($1,$2);"
        values=(otp,email.strip().lower())
    else:
        query="insert into otp (otp,mobile) values ($1,$2);"
        values=(otp,mobile.strip())
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query,*values)
    return otp

async def func_otp_verify(client_postgres_pool,otp,email,mobile,config_otp_expire_sec=None):
    if not otp:raise Exception("otp missing")
    if not config_otp_expire_sec:config_otp_expire_sec=600
    if not email and not mobile: raise Exception("email/mobile any one is must")
    if email and mobile: raise Exception("only one of email or mobile is allowed")
    if email:
        query = f"select otp from otp where created_at>current_timestamp-interval '{config_otp_expire_sec} seconds' and email=$1 order by id desc limit 1;"
        value = email.strip().lower()
    else:
        query = f"select otp from otp where created_at>current_timestamp-interval '{config_otp_expire_sec} seconds' and mobile=$1 order by id desc limit 1;"
        value = mobile.strip()
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query, value)
    if not output: raise Exception("otp not found")
    if int(output[0]["otp"]) != int(otp): raise Exception("otp mismatch")
    return None

async def func_message_inbox(client_postgres_pool,user_id,is_unread=None,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    if is_unread==1:query = f"with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=$1 or user_id=$1)), y as (select max(id) as id from x group by unique_id), z as (select m.* from y left join message as m on y.id=m.id), a as (select * from z where user_id=$1 and is_read is distinct from 1) select * from a order by {order} limit {limit} offset {(page-1)*limit};"
    elif is_unread==0:query = f"with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=$1 or user_id=$1)), y as (select max(id) as id from x group by unique_id), z as (select m.* from y left join message as m on y.id=m.id), a as (select * from z where user_id=$1 and is_read=1) select * from a order by {order} limit {limit} offset {(page-1)*limit};"
    else:query = f"with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=$1 or user_id=$1)), y as (select max(id) as id from x group by unique_id), z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        return await conn.fetch(query, user_id)

async def func_message_received(client_postgres_pool,user_id,is_unread=None,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    if is_unread==1:query=f"select * from message where user_id=$1 and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
    elif is_unread==0:query=f"select * from message where user_id=$1 and is_read=1 order by {order} limit {limit} offset {(page-1)*limit};"
    else:query=f"select * from message where user_id=$1 order by {order} limit {limit} offset {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        return await conn.fetch(query,user_id)

async def func_message_thread(client_postgres_pool,user_id_1,user_id_2,order=None,limit=None,page=None):
    order,limit,page=order or "id desc",limit or 100,page or 1
    query = f"select * from message where ((created_by_id=$1 and user_id=$2) or (created_by_id=$2 and user_id=$1)) order by {order} limit {limit} offset {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        return await conn.fetch(query, user_id_1, user_id_2)

async def func_message_thread_mark_read(client_postgres_pool,user_id_1,user_id_2):
   query="update message set is_read=1 where created_by_id=$1 and user_id=$2;"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,user_id_2,user_id_1)
   return None

async def func_message_delete_single_user(client_postgres_pool,message_id,user_id):
   query="delete from message where id=$1 and (created_by_id=$2 or user_id=$2);"
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,message_id,user_id)
   return None

async def func_message_delete_bulk(mode,client_postgres_pool,user_id):
   if mode=="created":query="delete from message where created_by_id=$1;"
   elif mode=="received":query="delete from message where user_id=$1;"
   elif mode=="all":query="delete from message where (created_by_id=$1 or user_id=$1);"
   else:raise Exception("mode=created/received/all")
   async with client_postgres_pool.acquire() as conn:
      await conn.execute(query,user_id)
   return None

import hashlib
async def func_auth_signup_username_password(client_postgres_pool,type,username,password):
    query="insert into users (type,username,password) values ($1,$2,$3) returning *;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username,hashlib.sha256(str(password).encode()).hexdigest())
    return output[0]

async def func_auth_signup_username_password_bigint(client_postgres_pool,type,username_bigint,password_bigint):
    query="insert into users (type,username_bigint,password_bigint) values ($1,$2,$3) returning *;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username_bigint,password_bigint)
    return output[0]

import hashlib
async def func_auth_login_password_username(client_postgres_pool,type,password,username):
    query="select * from users where type=$1 and username=$2 and password=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username,hashlib.sha256(str(password).encode()).hexdigest())
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

async def func_auth_login_password_username_bigint(client_postgres_pool,type,password_bigint,username_bigint):
    query="select * from users where type=$1 and username_bigint=$2 and password_bigint=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,username_bigint,password_bigint)
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

import hashlib
async def func_auth_login_password_email(client_postgres_pool,type,password,email):
    query="select * from users where type=$1 and email=$2 and password=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,email,hashlib.sha256(str(password).encode()).hexdigest())
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

import hashlib
async def func_auth_login_password_mobile(client_postgres_pool,type,password,mobile):
    query="select * from users where type=$1 and mobile=$2 and password=$3 order by id desc limit 1;"
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch(query,type,mobile,hashlib.sha256(str(password).encode()).hexdigest())
    user = output[0] if output else None
    if not user: raise Exception("user not found")
    return user

async def func_auth_login_otp_email(client_postgres_pool,type,email):
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch("select * from users where type=$1 and email=$2 order by id desc limit 1;",type,email)
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("insert into users (type,email) values ($1,$2) returning *;",type,email)
            user = output[0] if output else None
    return user

async def func_auth_login_otp_mobile(client_postgres_pool,type,mobile):
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch("select * from users where type=$1 and mobile=$2 order by id desc limit 1;",type,mobile)
        user = output[0] if output else None
        if not user:
            output = await conn.fetch("insert into users (type,mobile) values ($1,$2) returning *;",type,mobile)
            user = output[0] if output else None
    return user

import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_request
async def func_auth_login_google(client_postgres_pool,config_google_login_client_id,type,google_token):
    request = google_request.Request()
    id_info = id_token.verify_oauth2_token(google_token, request, config_google_login_client_id)
    if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]: raise Exception("invalid issuer")
    if not id_info.get("email_verified", False): raise Exception("email not verified")
    if id_info.get("exp", 0) < time.time(): raise Exception("token expired")
    google_user = {
        "sub": id_info.get("sub"),
        "email": id_info.get("email"),
        "name": id_info.get("name"),
        "picture": id_info.get("picture"),
        "email_verified": id_info.get("email_verified")
    }
    async with client_postgres_pool.acquire() as conn:
        output = await conn.fetch("SELECT * FROM users WHERE type=$1 AND google_login_id=$2 ORDER BY id DESC LIMIT 1", type, google_user["sub"])
        user = output[0] if output else None
        if not user:
            metadata = json.dumps(google_user)
            output = await conn.fetch("INSERT INTO users (type, google_login_id, google_login_metadata) VALUES ($1, $2, $3::jsonb) RETURNING *", type, google_user["sub"], metadata)
            user = output[0] if output else None
    return user

from openai import OpenAI
def func_openai_client_read(config_openai_key):
   client_openai=OpenAI(api_key=config_openai_key)
   return client_openai

async def func_openai_prompt(client_openai,model,prompt,is_web_search,previous_response_id):
   if not client_openai or not model or not prompt:raise Exception("param missing")
   params={"model":model,"input":prompt}
   if is_web_search==1:params["tools"]=[{"type":"web_search"}]
   if previous_response_id:params["previous_response_id"]=previous_response_id
   output=client_openai.responses.create(**params)
   return output

import base64
async def func_openai_ocr(client_openai,model,file,prompt):
   contents=await file.read()
   b64_image=base64.b64encode(contents).decode("utf-8")
   output=client_openai.responses.create(model=model,input=[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:image/png;base64,{b64_image}"},],}],)
   return output

from pathlib import Path
import uuid, pytesseract
from PIL import Image
from pdf2image import convert_from_path
async def func_ocr_tesseract_export(input_path, output_path=None):
    if not output_path: output_path = f"export/{uuid.uuid4().hex}.txt"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if input_path.lower().endswith(".pdf"):
        text = "\n".join(
            pytesseract.image_to_string(img, lang="eng")
            for img in convert_from_path(input_path)
        )
    else:
        text = pytesseract.image_to_string(Image.open(input_path), lang="eng")
    with open(output_path, "w", encoding="utf-8") as f: f.write(text)
    return output_path

import httpx
async def func_resend_send_email(config_resend_url,config_resend_key,email_from,email_to_list,title,body):
   payload={"from":email_from,"to":email_to_list,"subject":title,"html":body}
   headers={"Authorization":f"Bearer {config_resend_key}","Content-Type": "application/json"}
   async with httpx.AsyncClient() as client:
      output=await client.post(config_resend_url,json=payload,headers=headers)
   if output.status_code!=200:raise Exception(f"{output.text}")
   return None

import requests
async def func_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,mobile,otp):
   response=requests.get(config_fast2sms_url,params={"authorization":config_fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   output=response.json()
   if output.get("return") is not True:raise Exception(f"{output.get('message')}")
   return output

from posthog import Posthog
async def func_posthog_client_read(config_posthog_project_host,config_posthog_project_key):
   client_posthog=Posthog(config_posthog_project_key,host=config_posthog_project_host)
   return client_posthog

import gspread
from google.oauth2.service_account import Credentials
def func_gsheet_client_read(config_gsheet_service_account_json_path, config_gsheet_scope_list):
    creds = Credentials.from_service_account_file(config_gsheet_service_account_json_path,scopes=config_gsheet_scope_list)
    client_gsheet = gspread.authorize(creds)
    return client_gsheet

from urllib.parse import urlparse, parse_qs
def func_gsheet_object_create(client_gsheet, sheet_url, obj_list):
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
    ss = client_gsheet.open_by_key(spreadsheet_id)
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
async def func_mongodb_client_read(config_mongodb_url):
   client_mongodb=motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
   return client_mongodb

async def func_mongodb_object_create(client_mongodb,database,table,obj_list):
   mongodb_client_database=client_mongodb[database]
   output=await mongodb_client_database[table].insert_many(obj_list)
   return str(output)

from pathlib import Path
import json, requests
def func_grafana_dashbord_all_export(host, username, password, max_limit, output_path=None):
    if not output_path: output_path = "export/grafana"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base = Path(output_path)
    s = requests.Session(); s.auth = (username, password)
    sanitize = lambda x: "".join(c if c.isalnum() or c in " _-()" else "_" for c in x)
    try: orgs = s.get(f"{host}/api/orgs").json()
    except Exception as e: print("❌ Failed to get organizations:", e); return None
    for o in orgs:
        if s.post(f"{host}/api/user/using/{o['id']}").status_code != 200: continue
        r = s.get(f"{host}/api/search?type=dash-db&limit={max_limit}", headers={"X-Grafana-Org-Id": str(o["id"])})
        if r.status_code == 422: continue
        for d in r.json():
            try:
                data = s.get(f"{host}/api/dashboards/uid/{d['uid']}").json()["dashboard"]
                p = base / sanitize(o["name"]) / sanitize(d.get("folderTitle") or "General"); p.mkdir(parents=True, exist_ok=True)
                with open(p / f"{sanitize(d['title'])}.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
            except Exception as e: print("❌ Failed to export", d.get("title"), ":", e)
    return output_path

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

from pathlib import Path
import requests, csv, uuid
from requests.auth import HTTPBasicAuth
def func_jira_filter_count_export(jira_base_url, jira_email, jira_token, output_path=None):
    if not output_path: output_path = f"export/{uuid.uuid4().hex}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    auth = HTTPBasicAuth(jira_email, jira_token)
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    r = requests.get(f"{jira_base_url}/rest/api/3/filter/search", headers=h, auth=auth, params={"maxResults": 1000})
    if r.status_code != 200: return f"error {r.status_code}: {r.text}"
    filters = sorted(r.json().get("values", []), key=lambda x: x.get("name", "").lower())
    with open(output_path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["filter_name", "issue_count"])
        for flt in filters:
            jql = flt.get("jql") or f"filter={flt.get('id')}"
            cr = requests.post(f"{jira_base_url}/rest/api/3/search/approximate-count", headers=h, auth=auth, json={"jql": jql})
            w.writerow([flt.get("name", ""), cr.json().get("count", 0) if cr.status_code == 200 else f"error {cr.status_code}"])
    return output_path

from pathlib import Path
import requests, datetime, re, uuid
from collections import defaultdict, Counter
from openai import OpenAI
def func_jira_summary_export(jira_base_url,jira_email,jira_token,jira_project_key_list,jira_max_issues_per_status,openai_key,output_path=None):
    if not output_path: output_path=f"export/{uuid.uuid4().hex}.txt"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    c=OpenAI(api_key=openai_key); h={"Accept":"application/json"}; a=(jira_email,jira_token)
    fi=lambda q: requests.get(f"{jira_base_url}/rest/api/3/search",headers=h,auth=a,params={"jql":q,"fields":"summary,project,duedate,assignee,worklog,resolutiondate,updated","maxResults":jira_max_issues_per_status}).json().get("issues",[])
    fc=lambda k:[(lambda x: x["body"]["content"][0]["content"][0]["text"])(c) for c in requests.get(f"{jira_base_url}/rest/api/3/issue/{k}/comment",headers=h,auth=a).json().get("comments",[]) if isinstance(c,dict)]
    grp=lambda xs: defaultdict(list,{i["fields"]["project"]["name"]:[*grp(xs).get(i["fields"]["project"]["name"],[]),i] for i in xs})
    def build(g,s):
        now=datetime.datetime.now(); seen=set(); o=[]
        for p,xs in g.items():
            for i in xs:
                f=i["fields"]; t=f.get("summary","")
                if t in seen: continue
                seen.add(t); cm=fc(i["key"]); last=cm[-1][:100] if cm else ""
                try:d=(now-datetime.datetime.strptime(f["updated"][:10],"%Y-%m-%d")).days
                except:d="N/A"
                h=sum(w.get("timeSpentSeconds",0) for w in f.get("worklog",{}).get("worklogs",[]))//3600
                o.append(f"{p} - {t}. Comment: {last}. Hours: {h}. Last Updated: {d}d ago. [{s}]")
        return "\n".join(o)
    ai=lambda p:[l.strip("-•* ") for l in c.chat.completions.create(model="gpt-4-0125-preview",messages=[{"role":"user","content":p}]).choices[0].message.content.splitlines() if l.strip()]
    perf=lambda ds:(Counter({(f:=i["fields"]).get("assignee",{}).get("displayName","Unassigned"):len(fc(i["key"]))+len(f.get("worklog",{}).get("worklogs",[])) for i in ds}).most_common(3),sorted(defaultdict(list,{(f:=i["fields"]).get("assignee",{}).get("displayName","Unassigned"):[i["key"]] for i in ds if f.get("duedate") and f.get("resolutiondate") and f["resolutiondate"][:10]<=f["duedate"]}).items(),key=lambda x:len(x[1]),reverse=True)[:3])
    clean=lambda xs,p=False:["- "+re.sub(r"\s+"," ",re.sub(r"[^\w\s\-.,/()]","",l)).strip() for l in xs if len(l.split())>2 and (not p or "-" in l)]
    todo=inprog=done=[]
    for k in jira_project_key_list:
        todo+=fi(f'project={k} AND statusCategory="To Do" ORDER BY updated DESC')
        inprog+=fi(f'project={k} AND statusCategory="In Progress" ORDER BY updated DESC')
        done+=fi(f'project={k} AND statusCategory="Done" ORDER BY resolutiondate DESC')
    txt=build(grp(todo),"To Do")+"\n"+build(grp(inprog),"In Progress")+"\n"+build(grp(done),"Done")
    b=ai("List blockers.\n"+txt); i=ai("Give 5 improvements.\n"+txt); ta,ot=perf(done)
    with open(output_path,"w",encoding="utf-8") as f:
        f.write("Key Blockers\n");[f.write(f"{n+1}. {x}\n") for n,x in enumerate(clean(b,True))]
        f.write("\nSuggested Improvements\n");[f.write(f"{n+1}. {x}\n") for n,x in enumerate(clean(i))]
        f.write("\nTop 3 Active Assignees\n");[f.write(f"{n}. {x[0]} ({x[1]} updates)\n") for n,x in enumerate(ta,1)]
        f.write("\nBest On-Time Assignees\n");[f.write(f"{n}. {x[0]} - {len(x[1])} issues closed on or before due date\n") for n,x in enumerate(ot,1)]
    return output_path

from pathlib import Path
import requests,time,csv,json,uuid
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
def func_jira_jql_output_export(jira_base_url,jira_email,jira_token,jql,column=None,limit=None,output_path=None):
    if not output_path: output_path=f"export/{uuid.uuid4().hex}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if not column: column="key,assignee,status"
    if not limit: limit=10000
    if "order by" not in jql.lower(): jql=f"{jql} ORDER BY key ASC"
    auth=HTTPBasicAuth(jira_email,jira_token); h={"Accept":"application/json","Content-Type":"application/json"}
    fields=[c.strip() for c in column.split(",")]; issues=[]; token=None; page=0
    while True:
        if limit and len(issues)>=limit: break
        page+=1; size=min(100,limit-len(issues))
        payload={"jql":jql,"fields":fields,"maxResults":size}
        if token: payload["nextPageToken"]=token
        try: r=requests.post(f"{jira_base_url}/rest/api/3/search/jql",headers=h,auth=auth,data=json.dumps(payload))
        except RequestException as e: return f"Connection error: {e}"
        if r.status_code!=200: return f"API error {r.status_code}: {r.text}"
        d=r.json(); cur=d.get("issues",[])
        if not cur: break
        issues+=cur
        if d.get("isLast",True) or not d.get("nextPageToken") or page>=1000: break
        token=d.get("nextPageToken"); time.sleep(0.1)
    with open(output_path,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow([c.title().replace("_"," ") for c in fields])
        for i in issues:
            row=[]
            for k in fields:
                if k=="key": v=i.get("key","")
                else:
                    d=i.get("fields",{}).get(k)
                    if isinstance(d,dict): v=d.get("displayName") or d.get("name") or str(d)
                    elif isinstance(d,list): v=", ".join(x.get("name") for x in d if isinstance(x,dict) and x.get("name"))
                    else: v=d or ""
                row.append(v)
            w.writerow(row)
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

from pathlib import Path
import uuid, os
async def func_folder_filename_export(input_path, output_path=None):
    if not output_path: output_path = f"export/{uuid.uuid4().hex}.txt"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    skip = {"venv","__pycache__", ".git",".mypy_cache",".pytest_cache","node_modules"}
    base = Path(input_path).resolve()
    with open(output_path,"w") as f:
        for r,d,fs in os.walk(base):
            d[:] = [x for x in d if x not in skip]
            for x in fs: f.write(f"{Path(r,x).relative_to(base)}\n")
    return output_path

import sys
def func_variable_size_read_kb(namespace=globals()):
   result = {}
   for name, var in namespace.items():
      if not name.startswith("__"):
         key = f"{name} ({type(var).__name__})"
         size_kb = sys.getsizeof(var) / 1024
         result[key] = size_kb
   sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
   return sorted_result

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

import os
import aiofiles
async def func_render_html(path):
    if ".." in path: raise Exception("invalid name")
    full_path = os.path.abspath(path)
    if not full_path.endswith(".html"): raise Exception("invalid file type")
    if not os.path.isfile(full_path): raise Exception("file not found")
    async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
        return await f.read()

async def func_request_param_read(request,mode,config):
    if mode == "query":param = dict(request.query_params)
    elif mode == "form":
        form = await request.form()
        param = {k:v for k,v in form.items() if isinstance(v,str)}
        for k in form.keys():
            fs = [f for f in form.getlist(k) if getattr(f,"filename",None)]
            if fs: param[k] = fs
    elif mode == "body":
        try: body = await request.json()
        except: body = None
        param = body if isinstance(body,dict) else {"body":body}
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
async def func_sftp_client_read(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_key_path,config_sftp_auth_method):
    if config_sftp_auth_method not in ("key","password"):raise Exception("auth_method must be 'key' or 'password'")
    if config_sftp_auth_method=="key":
        if not config_sftp_key_path:raise Exception("key_path required for key auth")
        conn=await asyncssh.connect(host=config_sftp_host,port=int(config_sftp_port),username=config_sftp_username,client_keys=[config_sftp_key_path],known_hosts=None)
    else:
        if not config_sftp_password:raise Exception("password required for password auth")
        conn=await asyncssh.connect(host=config_sftp_host,port=int(config_sftp_port),username=config_sftp_username,password=config_sftp_password,known_hosts=None)
    return conn

async def func_sftp_folder_filename_read(client_sftp,folder_path):
    async with client_sftp.start_sftp_client() as sftp:
        output=await sftp.listdir(folder_path)
        return output
    
async def func_sftp_file_upload(client_sftp, input_path, output_path, chunk_size=65536):
    async with client_sftp.start_sftp_client() as sftp:
        async with sftp.open(output_path, "wb") as rf:
            with open(input_path, "rb") as lf:
                while True:
                    chunk = lf.read(chunk_size)
                    if not chunk:
                        break
                    await rf.write(chunk)
    
import uuid
from pathlib import Path
async def func_sftp_file_download(client_sftp,input_path,output_path=None,chunk_size=None):
    if not output_path:output_path=f"export/{uuid.uuid4().hex}{Path(input_path).suffix}"
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    if not chunk_size:chunk_size=65536
    async with client_sftp.start_sftp_client() as sftp:
        async with sftp.open(input_path,"rb") as rf:
            with open(output_path,"wb") as lf:
                while True:
                    c=await rf.read(chunk_size)
                    if not c:break
                    lf.write(c)
    return output_path

async def func_sftp_file_delete(client_sftp, path):
    async with client_sftp.start_sftp_client() as sftp:
        await sftp.remove(path)
    return None

import csv,io,os
async def func_sftp_csv_stream(client_sftp,path,batch_size=1000,encoding="utf-8"):
    if os.path.splitext(path)[1].lower()!=".csv":raise Exception("only csv files allowed")
    async with client_sftp.start_sftp_client() as sftp:
        async with sftp.open(path,"rb") as rf:
            buffer=""
            reader=None
            batch=[]
            while True:
                chunk=await rf.read(65536)
                if not chunk:break
                buffer+=chunk.decode(encoding)
                while "\n" in buffer:
                    line,buffer=buffer.split("\n",1)
                    if reader is None:
                        reader=csv.DictReader(io.StringIO(line+"\n"))
                    else:
                        row=next(csv.DictReader(io.StringIO(reader.fieldnames and ",".join(reader.fieldnames)+"\n"+line)))
                        batch.append(row)
                        if len(batch)==batch_size:
                            yield batch
                            batch=[]
            if batch:
                yield batch
                