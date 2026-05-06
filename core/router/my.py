#router
from fastapi import APIRouter
router = APIRouter()

#import
from fastapi import Request

#my
@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    app_state = request.app.state
    user_id = request.state.user["id"]
    async with app_state.client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
        if not record: raise Exception("user not found")
        user = dict(record)
        metadata = {}
        queries_metadata = app_state.config_sql.get("sql_profile_metadata")
        if queries_metadata:
            for key, sql_query in queries_metadata.items():
                records = await conn.fetch(sql_query, user_id)
                metadata[key] = [dict(record) for record in records]
        await conn.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", user_id)
    profile = {**user, **metadata}
    token = await app_state.func_token_encode(user=profile, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status": 1, "message": profile | {"token": token}}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request: Request):
    app_state = request.app.state
    async with app_state.client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", request.state.user["id"])
        if not record: raise Exception("user not found")
        user = dict(record)
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status": 1, "message": token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("days", "int", 1, None, None)])
    query = "SELECT api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY api LIMIT 1000;"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, oq["days"], request.state.user["id"])
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["soft", "hard"], None)])
    user_id = request.state.user["id"]
    async with app_state.client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT role FROM users WHERE id=$1", user_id)
        if not user: raise Exception("user not found")
        if user["role"] is not None: raise Exception("account with role cannot be deleted")
        if oq["mode"] == "soft": query = "UPDATE users SET is_deleted=1 WHERE id=$1"
        elif oq["mode"] == "hard": query = "DELETE FROM users WHERE id=$1"
        else: raise Exception(f"invalid delete mode: {oq['mode']}, allowed: soft, hard")
        await conn.execute(query, user_id)
    return {"status": 1, "message": "account deleted"}

@router.get("/my/message-received")
async def func_api_my_message_received(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, 100), ("page", "int", 0, None, 1)])
    user_id = request.state.user["id"]
    unread_filter = "AND is_read=1" if oq["mode"] == "read" else "AND is_read IS DISTINCT FROM 1" if oq["mode"] == "unread" else ""
    query = f"SELECT * FROM message WHERE user_id=$1 {unread_filter} ORDER BY {oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_id)
        obj_list = [dict(r) for r in records]
        if obj_list:
            mark_read_ids = [r["id"] for r in obj_list if r.get("is_read") != 1]
            if mark_read_ids: await conn.execute(f"UPDATE message SET is_read=1 WHERE id IN ({','.join(map(str, mark_read_ids))})")
    return {"status": 1, "message": obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, 100), ("page", "int", 0, None, 1)])
    user_id = request.state.user["id"]
    where_clause = "user_id=$1 AND is_read=1" if oq["mode"] == "read" else "user_id=$1 AND is_read IS DISTINCT FROM 1" if oq["mode"] == "unread" else "1=1"
    query = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - user_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR user_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_id)
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("user_id", "int", 1, None, None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, 100), ("page", "int", 0, None, 1)])
    user_one_id = request.state.user["id"]
    query = f"SELECT * FROM message WHERE ((created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1)) ORDER BY {oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_one_id, oq["user_id"])
        obj_list = [dict(r) for r in records]
        await conn.execute("UPDATE message SET is_read=1 WHERE created_by_id=$1 AND user_id=$2;", oq["user_id"], user_one_id)
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
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["sent", "received", "all"], None)])
    user_id = request.state.user["id"]
    if oq["mode"] == "sent":
        query = "DELETE FROM message WHERE created_by_id=$1"
        args = (user_id,)
    elif oq["mode"] == "received":
        query = "DELETE FROM message WHERE user_id=$1"
        args = (user_id,)
    elif oq["mode"] == "all":
        query = "DELETE FROM message WHERE (created_by_id=$1 OR user_id=$1)"
        args = (user_id,)
    else:
        raise Exception(f"invalid delete mode: {oq['mode']}, allowed: sent, received, all")
    async with app_state.client_postgres_pool.acquire() as conn:
        await conn.execute(query, *args)
    return {"status": 1, "message": "messages deleted"}

@router.get("/my/parent-read")
async def func_api_my_parent_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("parent_table", "str", 1, app_state.cache_postgres_table_list, None), ("parent_column", "str", 1, app_state.cache_postgres_column_list, None), ("order", "str", 0, None, "id desc"), ("limit", "int", 0, None, 100), ("page", "int", 0, None, 1)])
    query = f"SELECT x.* FROM {oq['table']} x JOIN {oq['parent_table']} p ON x.{oq['parent_column']} = p.id WHERE p.created_by_id = $1 ORDER BY x.{oq['order']} LIMIT {oq['limit']} OFFSET {(oq['page']-1)*oq['limit']};"
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, request.state.user["id"])
        output = [dict(r) for r in records]
    return {"status": 1, "message": output}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("ids", "str", 1, None, None)])
    output = await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, table=ob["table"], ids=ob["ids"], created_by_id=request.state.user.get("id", 0), client_postgres_conn=None)
    return {"status": 1, "message": output}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now"), ("is_serialize", "int", 0, [0, 1], 0), ("queue", "str", 0, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_create(user_id=request.state.user["id"], api_role="my", table=oq["table"], mode=oq["mode"], is_serialize=oq["is_serialize"], queue=oq["queue"], obj_list=obj_list, config_table_create_disable_my=app_state.config_table_create_disable_my, config_table_create_enable_public=app_state.config_table_create_enable_public, config_column_disable=app_state.config_column_disable, config_table=app_state.config_table, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_create=app_state.func_postgres_create, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, client_postgres_conn=None)}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now"), ("is_serialize", "int", 0, [0, 1], 0), ("otp", "int", 0, None, None), ("queue", "str", 0, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_update(user_id=request.state.user["id"], api_role="my", table=oq["table"], mode=oq["mode"], is_serialize=oq["is_serialize"], queue=oq["queue"], otp=oq["otp"], obj_list=obj_list, config_table=app_state.config_table, config_is_enable_otp_users_update_admin=app_state.config_is_enable_otp_users_update_admin, config_column_disable=app_state.config_column_disable, config_column_enable_single_update=app_state.config_column_enable_single_update, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check, func_otp_verify=app_state.func_otp_verify, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, config_expiry_sec_otp=app_state.config_expiry_sec_otp, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_update=app_state.func_postgres_update, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, client_postgres_conn=None)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("limit", "int", 0, None, 100), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("creator_key", "str", 0, None, None), ("action_key", "str", 0, None, None)])
    oq["created_by_id"] = f"""=,{request.state.user["id"]}"""
    ol = await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], filter_obj=oq, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], creator_key=oq["creator_key"], action_key=oq["action_key"])
    return {"status": 1, "message": ol}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("database", "str", 1, None, None), ("table", "str", 1, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    res = await app_state.client_mongodb[oq["database"]][oq["table"]].insert_many(obj_list)
    output = [str(id) for id in res.inserted_ids]
    return {"status": 1, "message": output}
