# packages
import asyncio
import urllib.parse
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    app_state = request.app.state
    user_id = request.state.user["id"]
    user = await app_state.func_user_read_single(client_postgres=app_state.client_postgres_read_fallback, user_id=user_id)
    metadata = {k: [dict(r) for r in await app_state.client_postgres_read_fallback.fetch(v, user_id)] for k, v in app_state.config_sql.get("profile_metadata", {}).items()}
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    asyncio.create_task(app_state.client_postgres.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", user_id))
    return {"status": 1, "message": {"user": user, "token": token, "metadata": metadata}}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request: Request):
    app_state = request.app.state
    user = await app_state.func_user_read_single(client_postgres=app_state.client_postgres_read_fallback, user_id=request.state.user["id"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": {"user": user, "token": token}}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("days", "int", 1, None, None)])
    sql = "SELECT path AS api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY path LIMIT 1000;"
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        records = await conn.fetch(sql, oq["days"], request.state.user["id"])
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now"), ("queue", "str", 0, app_state.config_queue_services, None)])
    if "*" in app_state.config_table_my_create_disable or oq["table"] in app_state.config_table_my_create_disable: raise Exception(f"creation disabled for table: {oq['table']}")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if app_state.config_batch_item_limit and len(obj_list) > app_state.config_batch_item_limit: raise Exception(f"maximum {app_state.config_batch_item_limit} objects allowed")
    if restricted_key := next((key for item in obj_list for key in item if key in app_state.config_column_admin), None): raise Exception(f"unauthorized update to restricted field: {restricted_key}")
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_create", payload={"mode": oq["mode"], "table": oq["table"], "obj_list": obj_list})}
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("ownership_column", "str", 0, app_state.config_column_ownership, "created_by_id"), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    schema_cols = app_state.cache_postgres_schema.get(oq["table"], {})
    if oq["ownership_column"] not in schema_cols: raise Exception(f"table '{oq['table']}' lacks ownership column '{oq['ownership_column']}'")
    filters = oq["filter"] + [f"""{oq["ownership_column"]} = {request.state.user["id"]}"""]
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=filters, limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    if oq["ownership_column"] == "user_id" and "id" in schema_cols and "read_at" in schema_cols: app_state.func_postgres_mark_read(client_postgres=app_state.client_postgres, table=oq["table"], ownership_column=oq["ownership_column"], user_id=request.state.user["id"], ids=[r.get("id") for r in ol if isinstance(r, dict)])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("otp", "int", 0, None, None), ("queue", "str", 0, app_state.config_queue_services, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if app_state.config_batch_item_limit and len(obj_list) > app_state.config_batch_item_limit: raise Exception(f"maximum {app_state.config_batch_item_limit} objects allowed")
    if restricted_key := next((key for item in obj_list for key in item if key in app_state.config_column_admin), None): raise Exception(f"unauthorized update to restricted field: {restricted_key}")
    if oq["table"] == "users" and (restricted_user_key := next((key for item in obj_list for key in item if key in getattr(app_state, 'config_column_admin_users', [])), None)): raise Exception(f"unauthorized update to restricted user field: {restricted_user_key}")
    if oq["table"] == "users" and len(obj_list) > 1: raise Exception("multi-object user update restricted")
    if oq["table"] == "users" and str(obj_list[0].get("id")) != str(request.state.user["id"]): raise Exception("ownership issue: cannot update other users")
    if oq["table"] == "users" and any(key in app_state.config_column_single_update for key in obj_list[0]) and len(obj_list[0]) != 2: raise Exception("sensitive fields must be updated individually (item length 2 required)")
    if oq["table"] == "users" and any(key in obj_list[0] for key in ("email", "mobile")): await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=obj_list[0].get("email"), mobile=obj_list[0].get("mobile"), config_otp_expiry_sec=app_state.config_otp_expiry_sec)
    if "updated_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'updated_by_id' column for update tracking")
    if request.state.user.get("id"): obj_list = [dict(item, updated_by_id=request.state.user["id"]) for item in obj_list]
    created_by_id = request.state.user["id"] if oq["table"] != "users" else None
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_update", payload={"table": oq["table"], "obj_list": obj_list, "created_by_id": created_by_id})}
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None)}

@router.post("/my/object-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("ids", "list:int", 1, None, None)])
    if app_state.config_batch_item_limit and len(ob["ids"]) > app_state.config_batch_item_limit: raise Exception(f"maximum {app_state.config_batch_item_limit} objects allowed")
    if ob["table"] == "users" and app_state.config_is_enable_user_delete != 1: raise Exception("users hard delete disabled")
    if ob["table"] == "users" and len(ob["ids"]) != 1: raise Exception("multiple users table delete not allowed")
    if ob["table"] == "users" and int(ob["ids"][0]) != int(request.state.user["id"]): raise Exception("users table delete allowed only for own account")
    created_by_id = request.state.user["id"] if ob["table"] != "users" else None
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=created_by_id)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/my/object-delete-all")
async def func_api_my_object_delete_all(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None)])
    if oq["table"] == "users": raise Exception("users bulk delete disabled; use /my/object-delete for own account")
    enabled_delete_all = app_state.config_table_my_delete_all_enable or []
    if "*" not in enabled_delete_all and oq["table"] not in enabled_delete_all: raise Exception(f"delete all disabled for table: {oq['table']}")
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    async with app_state.client_postgres.acquire() as conn:
        result = await conn.execute(f"""DELETE FROM "{oq["table"]}" WHERE "created_by_id"=$1""", user_id)
    return {"status": 1, "message": f"{int(result.rsplit(' ', 1)[-1])} objects deleted"}

@router.post("/my/object-delete-received")
async def func_api_my_received_ids_delete(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("col", "str", 0, ["user_id"], "user_id"), ("ids", "list:int", 1, None, None)])
    if app_state.config_batch_item_limit and len(ob["ids"]) > app_state.config_batch_item_limit: raise Exception(f"maximum {app_state.config_batch_item_limit} objects allowed")
    schema = app_state.cache_postgres_schema.get(ob["table"], {})
    col = ob["col"]
    if ob["table"] == "users" or "id" not in schema or col not in schema: raise Exception(f"users delete disabled or missing 'id'/'{col}' column")
    id_list, deleted_count = [int(x) for x in ob["ids"]], 0
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            for i in range(0, len(id_list), 5000):
                result = await conn.fetchval(f"""WITH deleted AS (DELETE FROM "{ob["table"]}" WHERE id=ANY($1::bigint[]) AND "{col}"=$2 RETURNING 1) SELECT COUNT(*) FROM deleted""", id_list[i:i+5000], user_id)
                deleted_count += result
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/my/object-delete-received-all")
async def func_api_my_received_object_delete_all(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("col", "str", 0, ["user_id"], "user_id")])
    if oq["table"] == "users": raise Exception("users received bulk delete disabled")
    enabled_delete_all_user_id = app_state.config_table_my_delete_all_received_enable or []
    if "*" not in enabled_delete_all_user_id and oq["table"] not in enabled_delete_all_user_id: raise Exception(f"received delete all disabled for table: {oq['table']}")
    col = oq["col"]
    if col not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required '{col}' column for ownership tracking")
    async with app_state.client_postgres.acquire() as conn:
        result = await conn.execute(f"""DELETE FROM "{oq["table"]}" WHERE "{col}"=$1""", user_id)
    return {"status": 1, "message": f"{int(result.rsplit(' ', 1)[-1])} objects deleted"}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1)])
    where_clause = {"read": "user_id=$1 AND read_at IS NOT NULL", "unread": "user_id=$1 AND read_at IS NULL"}.get(oq["mode"], "1=1")
    sql = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - user_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR user_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {oq['order']} LIMIT {oq['limit'] + 1} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, request.state.user["id"])]
        return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("user_id", "int", 1, None, None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1)])
    user_one_id = request.state.user["id"]
    sql = f"SELECT * FROM message WHERE ((created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1)) ORDER BY {oq['order']} LIMIT {oq['limit'] + 1} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, user_one_id, oq["user_id"])]
        await conn.execute("UPDATE message SET read_at=now() WHERE created_by_id=$1 AND user_id=$2;", oq["user_id"], user_one_id)
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("database", "str", 1, None, None), ("table", "str", 1, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    res = await app_state.client_mongodb[oq["database"]][oq["table"]].insert_many(obj_list)
    output=[str(id) for id in res.inserted_ids]
    return {"status": 1, "message": output}
    
@router.post("/my/object-blob-delete")
async def func_api_my_object_blob_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("cols", "list:str", 1, None, None), ("ids", "list:int", 1, None, None)])
    if app_state.config_batch_item_limit and len(ob["ids"]) > app_state.config_batch_item_limit: raise Exception(f"maximum {app_state.config_batch_item_limit} objects allowed")
    schema = app_state.cache_postgres_schema.get(ob["table"], {})
    if "created_by_id" not in schema: raise Exception(f"table '{ob['table']}' lacks required 'created_by_id' column for ownership tracking")
    for col in ob["cols"]:
        if col not in schema: raise Exception(f"column '{col}' not found in table '{ob['table']}'")
    id_list, user_id = [int(x) for x in ob["ids"]], request.state.user["id"]
    cols_query = ", ".join(f'"{c}"' for c in ob["cols"])
    async with app_state.client_postgres.acquire() as conn:
        rows = await conn.fetch(f"""SELECT "id", {cols_query} FROM "{ob['table']}" WHERE "id"=ANY($1::bigint[]) AND "created_by_id"=$2""", id_list, user_id)
    if not rows: return {"status": 1, "message": "0 ids deleted"}
    s3_batches, azure_tasks = {}, []
    for row in rows:
        for col in ob["cols"]:
            if not (url := row[col]): continue
            parsed = urllib.parse.urlparse(url)
            if "blob.core.windows.net" in url:
                parts = parsed.path.lstrip("/").split("/", 1)
                if len(parts) == 2:
                    if not app_state.client_azure_blob: raise Exception("azure blob client not configured")
                    azure_tasks.append(app_state.client_azure_blob.get_blob_client(container=parts[0], blob=urllib.parse.unquote(parts[1])).delete_blob())
            elif "amazonaws.com" in url:
                host_parts = parsed.netloc.split(".")
                if host_parts[0] != "s3": bucket, key = host_parts[0], parsed.path.lstrip("/")
                else:
                    parts = parsed.path.lstrip("/").split("/", 1)
                    if len(parts) != 2: continue
                    bucket, key = parts[0], parts[1]
                if not app_state.client_s3: raise Exception("s3 client not configured")
                s3_batches.setdefault(bucket, []).append({"Key": urllib.parse.unquote(key)})
    for bucket, keys in s3_batches.items():
        for i in range(0, len(keys), 1000):
            response = await app_state.client_s3.delete_objects(Bucket=bucket, Delete={"Objects": keys[i:i+1000], "Quiet": True})
            if response.get("Errors"): raise Exception(f"S3 blob delete failed: {response['Errors'][:3]}")
    if azure_tasks:
        for result in await asyncio.gather(*azure_tasks, return_exceptions=True):
            if isinstance(result, Exception) and type(result).__name__ != "ResourceNotFoundError": raise result
    set_clause = ", ".join(f'"{c}"=NULL' for c in ob["cols"])
    async with app_state.client_postgres.acquire() as conn:
        await conn.execute(f"""UPDATE "{ob['table']}" SET {set_clause} WHERE "id"=ANY($1::bigint[]) AND "created_by_id"=$2""", [r["id"] for r in rows], user_id)
    return {"status": 1, "message": f"{len(rows)} ids deleted"}

@router.post("/my/blob-url-delete")
async def func_api_my_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("service", "str", 1, app_state.config_blob_services, None), ("url", "list:str", 1, None, None)])
    service, urls, user_id = ob["service"], ob["url"], request.state.user["id"]
    tasks = []
    if service == "s3":
        batches = {}
        for u in urls:
            bucket = u.split("//", 1)[1].split(".", 1)[0]
            key = u.split(".com/", 1)[1]
            if not urllib.parse.unquote(key).startswith(f"user_{user_id}/"): continue
            if bucket not in batches: batches[bucket] = []
            batches[bucket].append({"Key": urllib.parse.unquote(key)})
        for b, keys in batches.items():
            for i in range(0, len(keys), 1000): tasks.append(app_state.client_s3.delete_objects(Bucket=b, Delete={"Objects": keys[i:i+1000]}))
    elif service == "azure":
        for u in urls:
            parts = u.split(".net/", 1)[1].split("/", 1)
            blob_key = urllib.parse.unquote(parts[1])
            if not blob_key.startswith(f"user_{user_id}/"): continue
            tasks.append(app_state.client_azure_blob.get_blob_client(container=parts[0], blob=blob_key).delete_blob())
    if tasks: await asyncio.gather(*tasks, return_exceptions=True)
    return {"status": 1, "message": f"{len(urls)} {service} URLs processed"}
