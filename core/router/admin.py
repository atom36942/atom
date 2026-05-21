#router
from fastapi import APIRouter
router = APIRouter()

#import
from fastapi import Request
import shutil
import os
import re
import orjson
import asyncio
import uuid

#api
@router.get("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table="", obj_list=[], config_buffer_limit=0, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check, config_obj_list_limit=app_state.config_obj_list_limit, config_table=app_state.config_table)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres_pool=app_state.client_postgres_pool) if app_state.client_postgres_pool else {}
    app_state.cache_postgres_table_list = list(app_state.cache_postgres_schema.keys())
    app_state.cache_postgres_column_list = sorted(list(set(col for table in app_state.cache_postgres_schema.values() for col in table.keys())))
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("users_role")) if app_state.client_postgres_pool else {}
    app_state.cache_users_is_active = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("users_is_active")) if app_state.client_postgres_pool else {}
    app_state.cache_users_is_deleted = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("users_is_deleted")) if app_state.client_postgres_pool else {}
    if app_state.config_is_enable_reset_tmp == 1 and os.path.exists("tmp"): shutil.rmtree("tmp"); os.makedirs("tmp")
    return {"status": 1, "message": "done"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now")])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, config_buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer", app_state.config_buffer_limit), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("limit", "int", 0, None, app_state.config_query_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    return {"status": 1, "message": await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_relation_fetch_limit_max=app_state.config_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("otp", "int", 0, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if oq["table"] == "users" and app_state.config_is_enable_otp_users_update_admin == 1 and any(key in obj_list[0] for key in ("email", "mobile")): len(obj_list) <= 1 or (_ for _ in ()).throw(Exception("multi-object user update restricted")); len(obj_list[0]) == 2 or (_ for _ in ()).throw(Exception("sensitive fields must be updated individually (item length 2 required)")); await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=oq["otp"], email=obj_list[0].get("email"), mobile=obj_list[0].get("mobile"), config_expiry_sec_otp=app_state.config_expiry_sec_otp)
    if request.state.user.get("id"): obj_list = [dict(item, updated_by_id=request.state.user["id"]) for item in obj_list]
    created_by_id = None
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None, config_obj_list_limit=app_state.config_obj_list_limit, config_regex=app_state.config_regex, config_table=app_state.config_table)}

@router.post("/admin/object-delete")
async def func_api_admin_object_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("ids", "list:int", 1, None, None)])
    return {"status": 1, "message": await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, table=ob["table"], ids=ob["ids"], created_by_id=None, client_postgres_conn=None)}

@router.post("/admin/postgres-clean")
async def func_api_admin_postgres_clean(*, request: Request):
    app_state = request.app.state
    if app_state.config_table:
        for tbl, cfg in app_state.config_table.items():
            if (retention_days := cfg.get("retention_day")) is not None:
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(tbl)): raise Exception(f"invalid identifier {tbl}")
                async with app_state.client_postgres_pool.acquire() as conn:
                    await conn.execute(f'DELETE FROM "{tbl}" WHERE "created_at" < NOW() - INTERVAL \'{retention_days} days\';')
    return {"status": 1, "message": "done"}
    
@router.post("/admin/postgres-sql-runner")
async def func_api_admin_postgres_sql_runner(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mode", "str", 0, ["read", "write"], "read"), ("sql", "str", 1, None, None)])
    if ob["mode"] not in ("read", "write"): raise Exception(f"invalid mode: {ob['mode']}")
    ql = ob["sql"].lower().strip()
    if any(re.search(rf"\b{k}\b", ql) for k in ("drop", "truncate", "delete")): raise Exception("forbidden keyword in sql")
    if ob["mode"] == "read" and not ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("read mode restricted")
    if ob["mode"] == "write" and app_state.config_is_enable_postgres_sql_runner_write != 1: raise Exception("postgres sql runner write mode disabled")
    if ob["mode"] == "read":
        if not app_state.client_postgres_pool_read: raise Exception("postgres read client not initialized")
        async with app_state.client_postgres_pool_read.acquire() as conn:
            return {"status": 1, "message": [dict(r) for r in await conn.fetch(ob["sql"], timeout=15)]}
    async with app_state.client_postgres_pool.acquire() as conn:
        if ql.startswith(("select", "with", "explain", "show", "describe")) or "returning" in ql:
            return {"status": 1, "message": [dict(r) for r in await conn.fetch(ob["sql"], timeout=15)]}
        return {"status": 1, "message": await conn.execute(ob["sql"], timeout=15)}

@router.post("/admin/mssql-sql-runner")
async def func_api_admin_mssql_sql_runner(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql: raise Exception("MSSQL client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mode", "str", 0, ["read", "write"], "read"), ("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip()
    if any(re.search(rf"\b{k}\b", ql) for k in ("drop", "truncate", "delete")): raise Exception("forbidden keyword in sql")
    if ob["mode"] == "read" and not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    async with app_state.client_mssql.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(ob["sql"])
        if ob["mode"] == "read" or ql.startswith(("select", "with")):
            columns = [column[0] for column in cursor.description]
            return {"status": 1, "message": [dict(zip(columns, row)) for row in await cursor.fetchall()]}
        await conn.commit()
        return {"status": 1, "message": "done"}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    from fastapi.responses import StreamingResponse
    sql = ob["sql"]
    ql = sql.lower().strip()
    if re.search(r"\bdrop\b", ql): raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql): raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql): raise Exception("keyword delete forbidden")
    if not ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("export restricted to select/with/explain/show/describe")
    async def _iter():
        async with app_state.client_postgres_pool.acquire() as conn:
            async with conn.transaction():
                is_first = 1
                async for record in conn.cursor(sql):
                    if is_first == 1:
                        yield ",".join(record.keys()) + "\n"
                        is_first = 0
                    yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in record.values()]) + "\n"
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=postgres_export.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("table", "str", 1, app_state.cache_postgres_table_list, None), ("file", "file", 1, None, None)])
    count = 0
    async with app_state.client_postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=5000):
                if not ol: continue
                if of["mode"] in ("update", "delete") and any("id" not in obj for obj in ol): raise Exception(f"CSV format error: Postgres {of['mode']} requires 'id' column")
                if of["mode"] == "create":
                    await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, config_buffer_limit=app_state.config_buffer_limit, mode="now", table=of["table"], obj_list=ol)
                elif of["mode"] == "update":
                    await app_state.func_postgres_update(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, table=of["table"], obj_list=ol, created_by_id=None)
                elif of["mode"] == "delete":
                    await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, table=of["table"], ids=[obj["id"] for obj in ol], created_by_id=None, client_postgres_conn=conn)
                count += len(ol)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/redis-import")
async def func_api_admin_redis_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "delete"], None), ("file", "file", 1, None, None)])
    count = 0; limit_batch = 5000
    async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=limit_batch):
        if of["mode"] == "create":
            if sorted(list(ol[0].keys())) != sorted(["key", "value"]): raise Exception("CSV format error: requires 'key' and 'value'")
            async with app_state.client_redis.pipeline(transaction=True) as pipe:
                for item in ol:
                    val = orjson.dumps(item["value"]).decode("utf-8")
                    if app_state.config_redis_cache_ttl_sec: pipe.setex(item["key"], app_state.config_redis_cache_ttl_sec, val)
                    else: pipe.set(item["key"], val)
                await pipe.execute()
        elif of["mode"] == "delete":
            if list(ol[0].keys()) != ["key"]: raise Exception("CSV format error: requires 'key' column")
            async with app_state.client_redis.pipeline(transaction=True) as pipe:
                for item in ol: pipe.delete(item["key"])
                await pipe.execute()
        count += len(ol)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("database", "str", 1, None, None), ("table", "str", 1, None, None), ("file", "file", 1, None, None)])
    count = 0; limit_batch = 5000
    def _get_mongodb_import_ids(ol, mode):
        if not ol: return []
        headers = ol[0].keys()
        if "id" not in headers and "_id" not in headers: raise Exception(f"CSV format error: MongoDB {mode} requires 'id' or '_id' column")
        ids = [item.get("id") or item.get("_id") for item in ol]
        if any(not oid for oid in ids): raise Exception(f"CSV format error: MongoDB {mode} requires non-empty 'id' or '_id'")
        return ids
    if of["mode"] == "create":
        async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=limit_batch):
            await app_state.client_mongodb[of["database"]][of["table"]].insert_many(ol)
            count += len(ol)
    elif of["mode"] == "update":
        async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=limit_batch):
            ids = _get_mongodb_import_ids(ol, of["mode"])
            for oid, item in zip(ids, ol):
                item.pop("id", None); item.pop("_id", None)
                await app_state.client_mongodb[of["database"]][of["table"]].update_one({"_id": oid}, {"$set": item})
            count += len(ol)
    elif of["mode"] == "delete":
        async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=limit_batch):
            ids = _get_mongodb_import_ids(ol, of["mode"])
            await app_state.client_mongodb[of["database"]][of["table"]].delete_many({"_id": {"$in": ids}})
            count += len(ol)
    return {"status": 1, "message": f"{count} rows processed"}

@router.get("/admin/blob-container-read")
async def func_api_admin_blob_container_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, ["s3", "azure"], None)])
    if oq["service"] == "s3":
        res = await app_state.client_s3.list_buckets()
        output = [b["Name"] for b in res.get("Buckets", [])]
    elif oq["service"] == "azure":
        output = []
        async for c in app_state.client_azure_blob.list_containers(): output.append(c.name)
    return {"status": 1, "message": output}

@router.post("/admin/blob-container-ops")
async def func_api_admin_blob_container_ops(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, ["s3", "azure"], None), ("mode", "str", 1, ["create", "public", "empty", "delete"], None), ("container", "str", 0, None, app_state.config_blob_container_default)])
    service, mode, container = oq["service"], oq["mode"], oq["container"]
    if service == "s3":
        if mode == "create": res = await app_state.client_s3.create_bucket(Bucket=container, CreateBucketConfiguration={"LocationConstraint": app_state.config_s3_region_name})
        elif mode == "public":
            await app_state.client_s3.put_public_access_block(Bucket=container, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
            res = await app_state.client_s3.put_bucket_policy(Bucket=container, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", container))
        elif mode == "empty": res = app_state.client_s3_resource.Bucket(container).objects.all().delete()
        elif mode == "delete": res = await app_state.client_s3.delete_bucket(Bucket=container)
    elif service == "azure":
        if mode == "create": res = await app_state.client_azure_blob.create_container(container)
        elif mode == "delete": res = await app_state.client_azure_blob.delete_container(container)
        else: raise Exception(f"mode {mode} not supported for azure")
    return {"status": 1, "message": res}

@router.post("/admin/blob-url-delete")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("service", "str", 1, ["s3", "azure"], None), ("url", "list", 1, None, None)])
    service, urls = ob["service"], ob["url"]
    tasks = []
    if service == "s3":
        batches = {}
        for u in urls:
            bucket = u.split("//", 1)[1].split(".", 1)[0]; key = u.split(".com/", 1)[1]
            if bucket not in batches: batches[bucket] = []
            batches[bucket].append({"Key": key})
        for b, keys in batches.items():
            for i in range(0, len(keys), 1000): tasks.append(app_state.client_s3.delete_objects(Bucket=b, Delete={"Objects": keys[i:i+1000]}))
    elif service == "azure":
        for u in urls:
            parts = u.split(".net/", 1)[1].split("/", 1)
            tasks.append(app_state.client_azure_blob.get_blob_client(container=parts[0], blob=parts[1]).delete_blob())
    if tasks: await asyncio.gather(*tasks)
    return {"status": 1, "message": f"{len(urls)} {service} URLs processed"}
