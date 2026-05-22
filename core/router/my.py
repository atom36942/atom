#router
from fastapi import APIRouter
router = APIRouter()

#import
from fastapi import Request

#api
@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    app_state = request.app.state
    user_id = request.state.user["id"]
    user = await app_state.func_user_read_single(client_postgres_pool=app_state.client_postgres_pool, user_id=user_id)
    async with app_state.client_postgres_pool.acquire() as conn:
        metadata = {}
        queries_metadata = app_state.config_sql.get("profile_metadata")
        if queries_metadata:
            for key, sql in queries_metadata.items():
                records = await conn.fetch(sql, user_id)
                metadata[key] = [dict(record) for record in records]
        await conn.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", user_id)
    profile = {**user, **metadata}
    token = await app_state.func_token_encode(user=profile, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status": 1, "message": profile | {"token": token}}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request: Request):
    app_state = request.app.state
    user = await app_state.func_user_read_single(client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status": 1, "message": token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("days", "int", 1, None, None)])
    sql = "SELECT path AS api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY path LIMIT 1000;"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql, oq["days"], request.state.user["id"])
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, app_state.config_query_limit_default), ("page", "int", 0, None, 1)])
    user_id = request.state.user["id"]
    where_clause = "user_id=$1 AND read_at IS NOT NULL" if oq["mode"] == "read" else "user_id=$1 AND read_at IS NULL" if oq["mode"] == "unread" else "1=1"
    sql = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - user_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR user_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql, user_id)
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.get("/my/message-received")
async def func_api_my_message_received(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, app_state.config_query_limit_default), ("page", "int", 0, None, 1)])
    user_id = request.state.user["id"]
    unread_filter = "AND read_at IS NOT NULL" if oq["mode"] == "read" else "AND read_at IS NULL" if oq["mode"] == "unread" else ""
    sql = f"SELECT * FROM message WHERE user_id=$1 {unread_filter} ORDER BY {oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql, user_id)
        obj_list = [dict(r) for r in records]
        if obj_list:
            mark_read_ids = [r["id"] for r in obj_list if r.get("read_at") is None]
            if mark_read_ids: await conn.execute(f"UPDATE message SET read_at=now() WHERE id IN ({','.join(map(str, mark_read_ids))})")
    return {"status": 1, "message": obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("user_id", "int", 1, None, None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, app_state.config_query_limit_default), ("page", "int", 0, None, 1)])
    user_one_id = request.state.user["id"]
    sql = f"SELECT * FROM message WHERE ((created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1)) ORDER BY {oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql, user_one_id, oq["user_id"])
        obj_list = [dict(r) for r in records]
        await conn.execute("UPDATE message SET read_at=now() WHERE created_by_id=$1 AND user_id=$2;", oq["user_id"], user_one_id)
    return {"status": 1, "message": obj_list}

@router.delete("/my/message-delete-single")
async def func_api_my_message_delete_single(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("id", "int", 1, None, None)])
    async with app_state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM message WHERE id=$1 AND (created_by_id=$2 OR user_id=$2)", oq["id"], request.state.user["id"])
    return {"status": 1, "message": "message deleted"}

@router.delete("/my/message-delete-bulk")
async def func_api_my_message_delete_bulk(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["sent", "received", "all"], None)])
    async with app_state.client_postgres_pool.acquire() as conn:
        if oq["mode"] == "sent": await conn.execute("DELETE FROM message WHERE created_by_id=$1", user_id)
        elif oq["mode"] == "received": await conn.execute("DELETE FROM message WHERE user_id=$1", user_id)
        elif oq["mode"] == "all": await conn.execute("DELETE FROM message WHERE (created_by_id=$1 OR user_id=$1)", user_id)
    return {"status": 1, "message": "messages deleted"}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("database", "str", 1, None, None), ("table", "str", 1, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    res = await app_state.client_mongodb[oq["database"]][oq["table"]].insert_many(obj_list)
    output=[str(id) for id in res.inserted_ids]
    return {"status": 1, "message": output}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now"), ("queue", "str", 0, app_state.config_queue, None)])
    if "*" in app_state.config_table_create_disable_my or oq["table"] in app_state.config_table_create_disable_my: raise Exception(f"creation disabled for table: {oq['table']}")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if any("deleted_at" in item for item in obj_list): raise Exception("deleted_at cannot be set on create; use deactivated_at for reversible inactive state")
    if restricted_key := next((key for item in obj_list for key in item if key in app_state.config_admin_columns), None): raise Exception(f"unauthorized creation of restricted field: {restricted_key}")
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_create", payload={"mode": oq["mode"], "table": oq["table"], "obj_list": obj_list})}
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, config_buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer", app_state.config_buffer_limit), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("limit", "int", 0, None, app_state.config_query_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    for rel in oq["relation"]:
        parts = [p.strip() for p in rel.split(",", 4)]
        if len(parts) >= 2 and "*" not in app_state.config_table_read_enable_public and parts[1] not in app_state.config_table_read_enable_public: raise Exception(f"relation read disabled for table: {parts[1]}")
    filters = oq["filter"] + [f"""created_by_id = {request.state.user["id"]}"""]
    ol = await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_relation_fetch_limit_max=app_state.config_relation_fetch_limit_max, table=oq["table"], filter=filters, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": ol}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("otp", "int", 0, None, None), ("queue", "str", 0, app_state.config_queue, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if any("deleted_at" in item for item in obj_list) and oq["table"] != "users": raise Exception("deleted_at update allowed only for users table; use deactivated_at etc for reversible inactive state")
    if restricted_key := next((key for item in obj_list for key in item if key in app_state.config_admin_columns), None): raise Exception(f"unauthorized update to restricted field: {restricted_key}")
    if oq["table"] == "users" and len(obj_list) > 1: raise Exception("multi-object user update restricted")
    if oq["table"] == "users" and str(obj_list[0].get("id")) != str(request.state.user["id"]): raise Exception("ownership issue: cannot update other users")
    if oq["table"] == "users" and any(key in app_state.config_column_enable_single_update for key in obj_list[0]) and len(obj_list[0]) != 2: raise Exception("sensitive fields must be updated individually (item length 2 required)")
    if oq["table"] == "users" and any(key in obj_list[0] for key in ("email", "mobile")): await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=oq["otp"], email=obj_list[0].get("email"), mobile=obj_list[0].get("mobile"), config_expiry_sec_otp=app_state.config_expiry_sec_otp)
    if "updated_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'updated_by_id' column for update tracking")
    if request.state.user.get("id"): obj_list = [dict(item, updated_by_id=request.state.user["id"]) for item in obj_list]
    created_by_id = request.state.user["id"] if oq["table"] != "users" else None
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_update", payload={"table": oq["table"], "obj_list": obj_list, "created_by_id": created_by_id})}
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None)}

@router.post("/my/object-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("ids", "list:int", 1, None, None)])
    user_id = request.state.user.get("id", 0)
    created_by_id = user_id
    if ob["table"] == "users":
        if len(ob["ids"]) != 1: raise Exception("multiple users table delete not allowed")
        if int(ob["ids"][0]) != int(user_id): raise Exception("users table delete allowed only for own account")
        created_by_id = None
    deleted_count = await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, config_obj_list_limit=app_state.config_obj_list_limit, table=ob["table"], ids=ob["ids"], created_by_id=created_by_id, config_is_enable_user_delete=app_state.config_is_enable_user_delete)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}
