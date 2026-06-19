# packages
import asyncio
import re
import uuid
import orjson
from azure.storage.blob import PublicAccess
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pymongo import DeleteOne, UpdateOne

# router
router = APIRouter()

# api
@router.get("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    if app_state.client_postgres: await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table="", obj_list=[], buffer_limit=0, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres=app_state.client_postgres_read_fallback) if app_state.client_postgres_read_fallback else {}
    app_state.cache_postgres_table_list = list(app_state.cache_postgres_schema.keys())
    app_state.cache_postgres_column_list = sorted(list(set(col for table in app_state.cache_postgres_schema.values() for col in table.keys())))
    app_state.cache_openapi = app_state.func_openapi_spec_generate(app_routes=request.app.routes, app_state=app_state)
    app_state.cache_config = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("config"), is_json_value=1) if app_state.client_postgres_read_fallback and "config" in app_state.cache_postgres_schema else {}
    app_state.cache_users_type = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_type")) if app_state.client_postgres_read_fallback else {}
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_role")) if app_state.client_postgres_read_fallback else {}
    app_state.cache_users_deactivated = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_deactivated")) if app_state.client_postgres_read_fallback else {}
    app_state.cache_users_deleted = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_deleted")) if app_state.client_postgres_read_fallback else {}
    return {"status": 1, "message": "done"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now")])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("otp", "int", 0, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if any("password" in item for item in obj_list) and any(len(item) != 2 or "id" not in item or "password" not in item for item in obj_list): raise Exception("password update requires exactly two fields (id, password)")
    if oq["table"] == "users" and app_state.config_is_enable_otp_require_users_update == 1 and any(key in obj_list[0] for key in ("email", "mobile")): len(obj_list) <= 1 or (_ for _ in ()).throw(Exception("multi-object user update restricted")); len(obj_list[0]) == 2 or (_ for _ in ()).throw(Exception("sensitive fields must be updated individually (item length 2 required)")); await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=obj_list[0].get("email"), mobile=obj_list[0].get("mobile"), config_otp_expiry_sec=app_state.config_otp_expiry_sec)
    if "updated_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'updated_by_id' column for update tracking")
    if request.state.user.get("id"): obj_list = [dict(item, updated_by_id=request.state.user["id"]) for item in obj_list]
    created_by_id = None
    result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None, config_regex=app_state.config_regex)
    return {"status": 1, "message": result}

@router.post("/admin/object-delete")
async def func_api_admin_object_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("ids", "list:int", 1, None, None)])
    if ob["table"] == "users" and app_state.config_is_enable_user_delete != 1: raise Exception("users hard delete disabled")
    created_by_id = None
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=created_by_id)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("table", "str", 1, app_state.cache_postgres_table_list, None), ("file", "file", 1, None, None)])
    if of["mode"] == "delete" and of["table"] == "users" and app_state.config_is_enable_user_delete != 1: raise Exception("users hard delete disabled")
    count = 0
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=5000):
                if not ol: continue
                if of["mode"] in ("update", "delete") and any("id" not in obj for obj in ol): raise Exception(f"CSV format error: Postgres {of['mode']} requires 'id' column")
                if of["mode"] == "create":
                    await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=of["table"], obj_list=ol)
                elif of["mode"] == "update":
                    await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=of["table"], obj_list=ol, created_by_id=None)
                elif of["mode"] == "delete":
                    await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=conn, cache_postgres_schema=app_state.cache_postgres_schema, table=of["table"], ids=[obj["id"] for obj in ol], created_by_id=None)
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
            async with app_state.client_redis.pipeline(transaction=False) as pipe:
                for item in ol:
                    val = orjson.dumps(item["value"]).decode("utf-8")
                    if app_state.config_redis_cache_ttl_sec: pipe.setex(item["key"], app_state.config_redis_cache_ttl_sec, val)
                    else: pipe.set(item["key"], val)
                await pipe.execute()
        elif of["mode"] == "delete":
            if list(ol[0].keys()) != ["key"]: raise Exception("CSV format error: requires 'key' column")
            async with app_state.client_redis.pipeline(transaction=False) as pipe:
                pipe.delete(*[item["key"] for item in ol])
                await pipe.execute()
        count += len(ol)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("database", "str", 1, None, None), ("table", "str", 1, None, None), ("file", "file", 1, None, None)])
    count = 0; limit_batch = 5000
    collection = app_state.client_mongodb[of["database"]][of["table"]]
    def _mongodb_import_id(item, mode):
        if "id" not in item and "_id" not in item: raise Exception(f"CSV format error: MongoDB {mode} requires 'id' or '_id' column")
        oid = item.get("id") or item.get("_id")
        if not oid: raise Exception(f"CSV format error: MongoDB {mode} requires non-empty 'id' or '_id'")
        return oid
    async for ol in app_state.func_api_file_to_chunks(upload_file=of["file"][-1], chunk_size=limit_batch):
        if not ol: continue
        if of["mode"] == "create":
            await collection.insert_many(ol)
        elif of["mode"] == "update":
            operations = []
            for item in ol:
                oid = _mongodb_import_id(item, of["mode"])
                item = dict(item)
                item.pop("id", None); item.pop("_id", None)
                operations.append(UpdateOne({"_id": oid}, {"$set": item}))
            await collection.bulk_write(operations, ordered=True)
        elif of["mode"] == "delete":
            operations = [DeleteOne({"_id": _mongodb_import_id(item, of["mode"])}) for item in ol]
            await collection.bulk_write(operations, ordered=True)
        count += len(ol)
    return {"status": 1, "message": f"{count} rows processed"}

@router.get("/admin/blob-container-read")
async def func_api_admin_blob_container_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_blob_services, None)])
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
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_blob_services, None), ("container", "str", 1, None, None), ("mode", "str", 1, ["create", "public", "empty", "delete"], None)])
    service, mode, container = oq["service"], oq["mode"], oq["container"]
    if service == "s3":
        if mode == "create": res = await app_state.client_s3.create_bucket(Bucket=container, CreateBucketConfiguration={"LocationConstraint": app_state.config_aws_s3_region_name})
        elif mode == "public":
            await app_state.client_s3.put_public_access_block(Bucket=container, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
            res = await app_state.client_s3.put_bucket_policy(Bucket=container, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", container))
        elif mode == "empty": res = app_state.client_s3_resource.Bucket(container).objects.all().delete()
        elif mode == "delete": res = await app_state.client_s3.delete_bucket(Bucket=container)
    elif service == "azure":
        if mode == "create":
            await app_state.client_azure_blob.create_container(container)
            res = {"service": service, "mode": mode, "container": container}
        elif mode == "public":
            container_client = app_state.client_azure_blob.get_container_client(container)
            await container_client.set_container_access_policy(signed_identifiers={}, public_access=PublicAccess.Blob)
            res = {"service": service, "mode": mode, "container": container}
        elif mode == "empty":
            container_client = app_state.client_azure_blob.get_container_client(container)
            blobs = [blob.name async for blob in container_client.list_blobs()]
            for i in range(0, len(blobs), 256):
                delete_responses = await container_client.delete_blobs(*blobs[i:i + 256], delete_snapshots="include")
                if hasattr(delete_responses, "__aiter__"):
                    async for _ in delete_responses: pass
            res = {"service": service, "mode": mode, "container": container, "deleted": len(blobs)}
        elif mode == "delete":
            await app_state.client_azure_blob.delete_container(container)
            res = {"service": service, "mode": mode, "container": container}
        else: raise Exception(f"mode {mode} not supported for azure")
    return {"status": 1, "message": res}

@router.post("/admin/blob-url-delete")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("service", "str", 1, app_state.config_blob_services, None), ("url", "list", 1, None, None)])
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

@router.post("/admin/postgres-query-runner-execute")
async def func_api_admin_postgres_query_runner_execute(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("read SQL must use /admin/postgres-query-runner-read")
    if "returning" in ql: raise Exception("RETURNING is not allowed in execute mode")
    async with app_state.client_postgres.acquire() as conn:
        result = await conn.execute(ob["sql"], timeout=15)
    return {"status": 1, "message": result}

@router.post("/admin/postgres-query-runner-read")
async def func_api_admin_postgres_query_runner_read(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("only read mode allowed")
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    limit = app_state.config_query_runner_read_limit
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        async with conn.transaction(readonly=True):
            result = []
            async for record in conn.cursor(ob["sql"], prefetch=250, timeout=15):
                result.append(dict(record))
                if len(result) >= limit: break
            return {"status": 1, "message": result}

@router.post("/admin/postgres-query-runner-read-export")
async def func_api_admin_postgres_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = ob["sql"]
    ql = sql.lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("export restricted to select/with/explain/show/describe")
    client_postgres = app_state.client_postgres_read_fallback
    if not client_postgres: raise Exception("postgres read client not initialized")
    limit = app_state.config_query_runner_export_limit
    async def _iter():
        async with client_postgres.acquire() as conn:
            async with conn.transaction(readonly=True):
                is_first = 1
                count = 0
                async for record in conn.cursor(sql):
                    if is_first == 1:
                        yield ",".join(record.keys()) + "\n"
                        is_first = 0
                    yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in record.values()]) + "\n"
                    count += 1
                    if count >= limit: break
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=postgres_query_runner_read_export.csv"})

@router.post("/admin/mssql-query-runner-execute")
async def func_api_cargowise_mssql_query_runner_execute(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql: raise Exception("MSSQL client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with")): raise Exception("read SQL must use /admin/mssql-query-runner-read")
    for attempt in range(3):
        try:
            async with app_state.client_mssql.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(ob["sql"])
                await conn.commit()
                result = "done"
                return {"status": 1, "message": result}
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(0.5)
                continue
            raise e

@router.post("/admin/mssql-query-runner-read")
async def func_api_cargowise_mssql_query_runner_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    if re.search(r"\b(insert|update|delete|merge|drop|alter|create|truncate|exec|execute|into)\b", ql): raise Exception("read mode restricted")
    limit = app_state.config_query_runner_read_limit
    for attempt in range(3):
        try:
            async with app_state.client_mssql_read.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(ob["sql"])
                columns = [column[0] for column in cursor.description]
                result = []
                while len(result) < limit:
                    rows = await cursor.fetchmany(min(500, limit - len(result)))
                    if not rows: break
                    result.extend(dict(zip(columns, row)) for row in rows)
                return {"status": 1, "message": result}
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(0.5)
                continue
            raise e

@router.post("/admin/mssql-query-runner-read-export")
async def func_api_cargowise_mssql_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    if re.search(r"\b(insert|update|delete|merge|drop|alter|create|truncate|exec|execute|into)\b", ql): raise Exception("read mode restricted")
    limit = app_state.config_query_runner_export_limit
    async def _iter():
        for attempt in range(3):
            try:
                async with app_state.client_mssql_read.acquire() as conn:
                    cursor = await conn.cursor()
                    await cursor.execute(ob["sql"])
                    columns = [column[0] for column in cursor.description]
                    yield ",".join(columns) + "\n"
                    count = 0
                    while True:
                        rows = await cursor.fetchmany(min(500, limit - count))
                        if not rows: break
                        for row in rows:
                            yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in row]) + "\n"
                        count += len(rows)
                        if count >= limit: break
                    return
            except Exception as e:
                if "08S01" in str(e) and attempt < 2:
                    import asyncio
                    await asyncio.sleep(0.5)
                    continue
                raise e
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=mssql_query_runner_read_export.csv"})
