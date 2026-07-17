# packages
import asyncio
import csv
import io
import json
import re
import orjson
from azure.storage.blob import PublicAccess
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from google.genai import types
from pymongo import DeleteOne, UpdateOne

# router
router = APIRouter()

# api
@router.get("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    if app_state.client_postgres: await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table="", obj_list=[], buffer_limit=0, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres=app_state.client_postgres_read_fallback) if app_state.client_postgres_read_fallback else {}
    app_state.cache_postgres_schema_ai = await app_state.func_postgres_schema_read_ai(client_postgres=app_state.client_postgres_read_fallback) if app_state.client_postgres_read_fallback else {}
    app_state.cache_postgres_schema_external = await app_state.func_postgres_schema_read(client_postgres=app_state.client_postgres_external) if app_state.client_postgres_external else {}
    app_state.cache_postgres_schema_external_ai = await app_state.func_postgres_schema_read_ai(client_postgres=app_state.client_postgres_external) if app_state.client_postgres_external else {}
    app_state.cache_postgres_schema_table_list = list(app_state.cache_postgres_schema.keys())
    app_state.cache_postgres_schema_column_list = sorted(list(set(col for table in app_state.cache_postgres_schema.values() for col in table.keys())))
    app_state.cache_openapi = app_state.func_openapi_spec_generate(app_routes=request.app.routes, app_state=app_state)
    app_state.cache_config = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("config"), is_json_value=1) if app_state.client_postgres_read_fallback and "config" in app_state.cache_postgres_schema else {}
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_role")) if app_state.client_postgres_read_fallback else {}
    app_state.cache_users_deactivated = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_deactivated")) if app_state.client_postgres_read_fallback else {}
    app_state.cache_users_deleted = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres_read_fallback, config_sql=app_state.config_sql.get("users_deleted")) if app_state.client_postgres_read_fallback else {}
    return {"status": 1, "message": "done"}

@router.get("/admin/postgres-info")
async def func_api_admin_postgres_info(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("db", "str", 0, ["main", "external"], "main")])
    client_postgres = app_state.client_postgres_read_fallback if oq["db"] == "main" else app_state.client_postgres_external
    if not client_postgres: raise Exception(f"{oq['db']} postgres client not initialized")
    info = await app_state.func_postgres_info_read(client_postgres=client_postgres)
    return {"status": 1, "message": info}

@router.get("/admin/postgres-schema")
async def func_api_admin_postgres_schema(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("db", "str", 0, ["main", "external"], "main")])
    client_postgres = app_state.client_postgres_read_fallback if oq["db"] == "main" else app_state.client_postgres_external
    cache_key = "cache_postgres_schema" if oq["db"] == "main" else "cache_postgres_schema_external"
    schema = getattr(app_state, cache_key, {}) or {}
    if not schema:
        if not client_postgres: raise Exception(f"{oq['db']} postgres client not initialized")
        schema = await app_state.func_postgres_schema_read(client_postgres=client_postgres)
        setattr(app_state, cache_key, schema)
    return {"status": 1, "message": schema}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now")])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("otp", "int", 0, None, None)])
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
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("ids", "list:int", 1, None, None)])
    if ob["table"] == "users" and app_state.config_is_enable_user_delete != 1: raise Exception("users hard delete disabled")
    created_by_id = None
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=created_by_id)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("file", "file", 1, None, None)])
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
    if not app_state.client_redis: raise Exception("redis client not initialized")
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
    if not app_state.client_mongodb: raise Exception("mongodb client not initialized")
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
    if (oq["service"] == "s3" and not app_state.client_s3) or (oq["service"] == "azure" and not app_state.client_azure_blob): raise Exception("blob client not initialized")
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
    if (service == "s3" and ((mode == "empty" and not app_state.client_s3_resource) or (mode != "empty" and not app_state.client_s3))) or (service == "azure" and not app_state.client_azure_blob): raise Exception("blob client not initialized")
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

@router.post("/admin/blob-delete-url")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("service", "str", 1, app_state.config_blob_services, None), ("url", "list", 1, None, None)])
    service, urls = ob["service"], ob["url"]
    if len(urls) > 500: raise Exception("maximum 500 URLs allowed per request")
    await app_state.func_blob_url_delete(app_state=app_state, service=service, urls=urls, user_id=None)
    return {"status": 1, "message": f"{len(urls)} {service} URLs processed"}

@router.post("/admin/postgres-query-runner-write")
async def func_api_admin_postgres_query_runner_write(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("read SQL must use /admin/postgres-query-runner-read")
    if "returning" in ql: raise Exception("RETURNING is not allowed in write mode")
    async with app_state.client_postgres.acquire() as conn:
        result = await conn.execute(ob["sql"], timeout=15)
    return {"status": 1, "message": result}

@router.post("/admin/postgres-query-runner-read")
async def func_api_admin_postgres_query_runner_read(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("db", "str", 0, ["main", "external"], "main"), ("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    client_postgres = app_state.client_postgres_read_fallback if ob["db"] == "main" else app_state.client_postgres_external
    if not client_postgres: raise Exception(f"{ob['db']} postgres read client not initialized")
    timeout_sec = 30
    async with client_postgres.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
            records = await stmt.fetch(app_state.config_query_runner_read_limit, timeout=timeout_sec)
    return {"status": 1, "message": [dict(row) for row in records]}

@router.post("/admin/postgres-query-runner-read-export")
async def func_api_admin_postgres_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("db", "str", 0, ["main", "external"], "main"), ("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    client_postgres = app_state.client_postgres_read_fallback if ob["db"] == "main" else app_state.client_postgres_external
    if not client_postgres: raise Exception(f"{ob['db']} postgres read client not initialized")
    timeout_sec = 30
    async def _iter():
        async with client_postgres.acquire() as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
                stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
                columns = [attr.name for attr in stmt.get_attributes()]
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(columns)
                yield buffer.getvalue()
                buffer.seek(0); buffer.truncate(0)
                async for record in stmt.cursor(app_state.config_query_runner_export_limit, prefetch=250, timeout=timeout_sec):
                    writer.writerow([record[column] for column in columns])
                    yield buffer.getvalue()
                    buffer.seek(0); buffer.truncate(0)
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=postgres_query_result.csv"})

@router.post("/admin/postgres-query-generator-ai")
async def func_api_admin_postgres_query_ai(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("db", "str", 0, ["main", "external"], "main"), ("ai", "str", 0, app_state.config_ai_services, "gemini"), ("question", "str", 1, None, None)])
    if ob["ai"] == "gemini" and not app_state.client_gemini: raise Exception("Gemini client not initialized")
    if ob["ai"] == "openai" and not app_state.client_openai: raise Exception("OpenAI client not initialized")
    client_postgres = app_state.client_postgres_read_fallback if ob["db"] == "main" else app_state.client_postgres_external
    cache_key = "cache_postgres_schema_ai" if ob["db"] == "main" else "cache_postgres_schema_external_ai"
    if not client_postgres: raise Exception(f"{ob['db']} postgres client not initialized")
    question = str(ob["question"] or "").strip()
    default_limit = 10
    max_limit = app_state.config_query_runner_read_limit
    def func_postgres_query_ai_schema_prompt(cache_postgres_schema_ai: dict) -> list:
        output = []
        for table_key, table in sorted((cache_postgres_schema_ai or {}).items()):
            columns = []
            for column_name, column in sorted(table.get("columns", {}).items()):
                columns.append({
                    "name": column_name,
                    "data_type": column.get("data_type"),
                    "is_indexed": bool(column.get("is_indexed")),
                    "index_methods": column.get("index_methods") or [],
                    "is_primary": bool(column.get("is_primary")),
                    "is_unique": bool(column.get("is_unique")),
                })
            output.append({"table": table_key, "relation_type": table.get("relation_type"), "columns": columns})
        return output
    def func_postgres_query_ai_blocked_message(message: str) -> str:
        message = str(message or "").strip()
        if not message or re.search(r"\b(success|successfully|generated|done|created)\b", message, flags=re.IGNORECASE):
            return "Could not generate a safe SQL query. Please mention a valid object. Filters must use indexed columns."
        return message
    def func_postgres_query_ai_clean_identifier(identifier: str) -> str:
        return str(identifier or "").strip().strip('"')
    def func_postgres_query_ai_resolve_table_key(*, value: str, cache_postgres_schema_ai: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not value: return ""
        value = re.sub(r"\s*\.\s*", ".", value)
        lookup = {key.lower(): key for key in (cache_postgres_schema_ai or {}).keys()}
        lookup.update({str(table.get("table_name") or key.split(".")[-1]).lower(): key for key, table in (cache_postgres_schema_ai or {}).items()})
        return lookup.get(value.lower(), "")
    def func_postgres_query_ai_resolve_column_name(*, table_key: str, value: str, cache_postgres_schema_ai: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not table_key or not value: return ""
        columns = (cache_postgres_schema_ai.get(table_key, {}).get("columns") or {})
        lookup = {column.lower(): column for column in columns.keys()}
        return lookup.get(value.lower(), "")
    def func_postgres_query_ai_validate_sql(*, sql: str, default_limit: int, max_limit: int, cache_postgres_schema_ai: dict) -> str:
        sql = str(sql or "").strip().rstrip(";").strip()
        if not sql: raise Exception("AI did not generate SQL.")
        if ";" in sql: raise Exception("AI generated multiple SQL statements.")
        if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("AI generated non-read SQL.")
        known_tables = set((cache_postgres_schema_ai or {}).keys())
        table_matches = re.findall(r'\b(?:from|join)\s+((?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+))?)(?:\s+(?:as\s+)?("[^"]+"|\w+))?', sql, flags=re.IGNORECASE)
        alias_to_table = {}
        for raw_table, raw_alias in table_matches:
            parts = [part.strip().strip('"') for part in raw_table.split(".")]
            table_key = ".".join(parts) if len(parts) > 1 else f"public.{parts[0]}"
            table_key = func_postgres_query_ai_resolve_table_key(value=table_key, cache_postgres_schema_ai=cache_postgres_schema_ai) or table_key
            if table_key not in known_tables: raise Exception(f"AI generated SQL for unknown object: {table_key}")
            alias = raw_alias.strip().strip('"') if raw_alias else parts[-1]
            if alias.lower() in {"where", "join", "on", "group", "order", "limit"}: alias = parts[-1]
            alias_to_table[alias] = table_key
        where_match = re.search(r'\bwhere\b(.+?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)', sql, flags=re.IGNORECASE | re.DOTALL)
        if where_match:
            filters = re.findall(r'(?:(?:"([^"]+)"|(\w+))\s*\.\s*)?(?:"([^"]+)"|(\w+))\s*(=|<>|!=|>=|<=|>|<|\bILIKE\b|\bLIKE\b|\bIN\b|\bBETWEEN\b)', where_match.group(1), flags=re.IGNORECASE)
            for quoted_alias, plain_alias, quoted_col, plain_col, _operator in filters:
                alias = quoted_alias or plain_alias
                column = quoted_col or plain_col
                candidate_tables = [alias_to_table[alias]] if alias and alias in alias_to_table else list(alias_to_table.values())
                column_names = [(table_key, func_postgres_query_ai_resolve_column_name(table_key=table_key, value=column, cache_postgres_schema_ai=cache_postgres_schema_ai)) for table_key in candidate_tables]
                column_matches = [cache_postgres_schema_ai[table_key]["columns"][column_name] for table_key, column_name in column_names if column_name]
                if not column_matches: raise Exception(f"AI generated filter on unknown column: {column}")
                if column_matches and not any(col.get("is_indexed") for col in column_matches): raise Exception(f"AI generated filter on non-indexed column: {column}")
        limit_match = re.search(r'\blimit\s+(\d+)\s*$', sql, flags=re.IGNORECASE)
        if limit_match:
            limit = max(1, min(int(limit_match.group(1)), max_limit))
            sql = re.sub(r'\blimit\s+\d+\s*$', f"LIMIT {limit}", sql, flags=re.IGNORECASE)
        else:
            sql = f"{sql}\nLIMIT {default_limit}"
        return f"{sql.rstrip(';')};"
    cache_postgres_schema_ai = getattr(app_state, cache_key, {}) or {}
    if not cache_postgres_schema_ai:
        cache_postgres_schema_ai = await app_state.func_postgres_schema_read_ai(client_postgres=client_postgres)
        setattr(app_state, cache_key, cache_postgres_schema_ai)
    prompt_schema = func_postgres_query_ai_schema_prompt(cache_postgres_schema_ai)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "sql": {"type": "STRING", "nullable": True},
            "message": {"type": "STRING"},
            "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
    }
    response_json_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sql": {"type": ["string", "null"]},
            "message": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["sql", "message", "warnings"],
    }
    prompt = "\n".join([
        "You generate safe PostgreSQL SELECT SQL for an internal read-only query runner.",
        "",
        "Rules:",
        "1. Return JSON only in the requested schema.",
        "2. If the request cannot be answered safely, return sql null and a short message.",
        "3. Generate only SELECT or WITH SQL.",
        "4. Use only objects and columns from the schema below.",
        f"5. If the user asks for a limit, use that LIMIT up to {max_limit}. If the user does not ask for a limit, use LIMIT {default_limit}.",
        "6. Prefer public schema objects without schema qualification when schema_name is public.",
        "7. Do not drop user intent. If the user asks for a specific value, place, customer, port, country, status, date, or other filter, include that filter.",
        "8. WHERE filters must use indexed columns. If the request requires filtering on a non-indexed column or no matching indexed column is clear, return sql null and ask admin to create an index or mention the indexed column.",
        "9. For text prefix search, use ILIKE 'value%'. Avoid broad contains search unless the column has a gin index.",
        "10. Limit-only SELECT from an explicitly named object is allowed and does not need an indexed filter.",
        "11. Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, or multiple statements.",
        "",
        "User question:",
        question,
        "",
        "Schema:",
        json.dumps(prompt_schema, separators=(",", ":")),
    ])
    if ob["ai"] == "gemini":
        response = await asyncio.to_thread(
            app_state.client_gemini.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=response_schema, temperature=0.1),
        )
        data = json.loads(response.text or "{}")
    else:
        response = await asyncio.to_thread(
            app_state.client_openai.responses.create,
            model="gpt-4.1-mini",
            input=prompt,
            text={"format": {"type": "json_schema", "name": "postgres_query_generator", "schema": response_json_schema, "strict": True}},
            temperature=0.1,
        )
        data = json.loads(response.output_text or "{}")
    if not data.get("sql"):
        return {"status": 1, "message": {"sql": None, "message": func_postgres_query_ai_blocked_message(data.get("message")), "warnings": data.get("warnings") or []}}
    sql = func_postgres_query_ai_validate_sql(sql=data.get("sql"), default_limit=default_limit, max_limit=max_limit, cache_postgres_schema_ai=cache_postgres_schema_ai)
    return {"status": 1, "message": {"sql": sql, "message": "SQL generated in the editor. Review before Run or Export.", "warnings": data.get("warnings") or []}}

@router.post("/admin/mssql-query-runner-write")
async def func_api_cargowise_mssql_query_runner_write(*, request: Request):
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
                    await asyncio.sleep(0.5)
                    continue
                raise e
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=mssql_query_runner_read_export.csv"})
