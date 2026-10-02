# import
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/my/blob-preview-urls")
async def func_api_my_blob_preview_urls(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services}, {"name": "urls", "type": "list", "required": True}])
    res = await app_state.func_blob_preview_urls_get(client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, config_azure_account_name=app_state.config_azure_account_name, config_azure_account_key=app_state.config_azure_account_key, config_blob_expire_sec_preview=app_state.config_blob_expire_sec_preview, service=of["service"], urls=of["urls"], user_id=request.state.user["id"])
    return {"status": 1, "message": res}

@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    app_state = request.app.state
    user_id = request.state.user["id"]
    user = await app_state.func_user_read_single(client_postgres=request.state.client_postgres, user_id=user_id)
    for column in app_state.config_column_read_blocked or ["password"]: user.pop(column, None)
    metadata = {k: [dict(r) for r in await request.state.client_postgres.fetch(v, user_id)] for k, v in app_state.config_sql.get("profile_metadata", {}).items()}
    user["metadata"] = metadata
    return {"status": 1, "message": user}

@router.post("/my/ping")
async def func_api_my_ping(*, request: Request):
    app_state = request.app.state
    if not request.state.client_postgres: raise app_state.func_api_error(message="postgres client not initialized", status_code=500)
    await request.state.client_postgres.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", request.state.user["id"])
    return {"status": 1, "message": "pong"}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request: Request):
    app_state = request.app.state
    if not request.state.client_postgres: raise app_state.func_api_error(message="postgres client not initialized", status_code=500)
    user = await app_state.func_user_read_single(client_postgres=request.state.client_postgres, user_id=request.state.user["id"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "days", "type": "int", "required": True}])
    if not app_state.client_postgres_log_api: raise app_state.func_api_error(message="postgres client not initialized", status_code=500)
    sql = "SELECT path AS api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY path LIMIT 1000;"
    async with app_state.client_postgres_log_api.acquire() as conn:
        records = await conn.fetch(sql, oq["days"], request.state.user["id"])
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "mode", "type": "str", "allowed": ["now", "buffer"], "default": "now"}, {"name": "queue", "type": "str", "allowed": app_state.config_queue_services}])
    if "*" in app_state.config_table_my_create_blocked or oq["table"] in app_state.config_table_my_create_blocked: raise Exception(f"creation disabled for table: {oq['table']}")
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="created_by_id")
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_create", payload={"mode": oq["mode"], "table": oq["table"], "obj_list": obj_list})}
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=request.state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_column_regex=app_state.config_column_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_read, "default": "created_by_id"}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "relation", "type": "list", "default": []}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], relation=oq["relation"], scope="my", action="read")
    app_state.func_check_table_column_exists(app_state=app_state, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    filters = oq["filter"] + [f"""{oq["ownership_column"]} = {request.state.user["id"]}"""]
    ol = await app_state.func_postgres_read(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=filters, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"], config_column_read_blocked=app_state.config_column_read_blocked, blocked_tables=app_state.config_table_my_read_blocked)
    schema_cols = request.state.cache_postgres_schema.get(oq["table"], {})
    if oq["ownership_column"] == "received_by_id" and "id" in schema_cols and "read_at" in schema_cols:
        app_state.func_postgres_mark_read(client_postgres=app_state.client_postgres_dict.get("master"), table=oq["table"], ownership_column=oq["ownership_column"], user_id=request.state.user["id"], ids=[r.get("id") for r in ol if isinstance(r, dict)])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_more": len(ol) > oq["limit"], "has_next_page": len(ol) > oq["limit"]}}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_update, "default": "created_by_id"}, {"name": "otp", "type": "int"}, {"name": "queue", "type": "str", "allowed": app_state.config_queue_services}])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    await app_state.func_check_user_update_permission(app_state=app_state, table=oq["table"], obj_list=obj_list, scope="my", otp=oq["otp"], user_id=request.state.user.get("id"))
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="updated_by_id", purpose="update tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="updated_by_id")
    if oq["table"] == "users" and "ownership_column" in request.query_params: raise Exception("ownership_column is not supported for users update")
    created_by_id = request.state.user["id"] if oq["table"] != "users" else None
    if oq["table"] != "users": app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_update", payload={"table": oq["table"], "obj_list": obj_list, "created_by_id": created_by_id, "ownership_column": oq["ownership_column"]})}
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, ownership_column=oq["ownership_column"], client_postgres_conn=None)}

@router.post("/my/object-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_delete, "default": "created_by_id"}])
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ids", "type": "list:int", "required": True}])
    table, ids = ob["table"], ob["ids"]
    app_state.func_check_batch_limit(app_state=app_state, items=ids)
    app_state.func_check_user_delete_permission(app_state=app_state, table=table, scope="my", ids=ids, user_id=request.state.user.get("id"))
    if table == "users" and "ownership_column" in request.query_params: raise Exception("ownership_column is not supported for users deletion")
    ownership_column = oq["ownership_column"]
    created_by_id = None
    if table != "users":
        app_state.func_check_table_column_exists(app_state=app_state, table=table, column=ownership_column, purpose="ownership tracking")
        created_by_id = request.state.user["id"]
    deleted_count = await app_state.func_postgres_delete(client_postgres=request.state.client_postgres, client_postgres_conn=None, cache_postgres_schema=request.state.cache_postgres_schema, table=table, ids=ids, created_by_id=created_by_id, ownership_column=ownership_column)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/my/object-delete-all")
async def func_api_my_object_delete_all(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_delete, "default": "created_by_id"}])
    app_state.func_check_user_delete_permission(app_state=app_state, table=oq["table"], scope="my_all")
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="my", action="delete_all")
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    res = await app_state.func_postgres_delete_all(client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], ownership_column=oq["ownership_column"], user_id=user_id, limit=getattr(app_state, "config_batch_item_limit", 5000) or 5000)
    return {"status": 1, "message": {"deleted_count": res["deleted_count"], "has_more": res["has_more"], "has_next_page": res["has_next_page"]}}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "mode", "type": "str", "required": True, "allowed": ["all", "unread", "read"]}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1}])
    fetch_limit, offset = app_state.func_message_pagination(limit=oq["limit"], page=oq["page"], max_limit=app_state.config_sql_read_limit_max)
    order_sql = app_state.func_message_order(order=oq["order"], cache_postgres_schema=request.state.cache_postgres_schema)
    where_clause = {"read": "received_by_id=$1 AND read_at IS NOT NULL", "unread": "received_by_id=$1 AND read_at IS NULL"}.get(oq["mode"], "1=1")
    sql = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - received_by_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR received_by_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {order_sql} LIMIT $2 OFFSET $3;"
    async with request.state.client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, request.state.user["id"], fetch_limit, offset)]
        return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_more": len(ol) > oq["limit"], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "user_id", "type": "int", "required": True}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1}])
    if not app_state.client_postgres_dict.get("master"): raise app_state.func_api_error(message="postgres client not initialized", status_code=500)
    user_one_id = request.state.user["id"]
    fetch_limit, offset = app_state.func_message_pagination(limit=oq["limit"], page=oq["page"], max_limit=app_state.config_sql_read_limit_max)
    order_sql = app_state.func_message_order(order=oq["order"], cache_postgres_schema=request.state.cache_postgres_schema)
    sql = f"SELECT * FROM message WHERE ((created_by_id=$1 AND received_by_id=$2) OR (created_by_id=$2 AND received_by_id=$1)) ORDER BY {order_sql} LIMIT $3 OFFSET $4;"
    async with request.state.client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, user_one_id, oq["user_id"], fetch_limit, offset)]
    async with app_state.client_postgres_dict.get("master").acquire() as conn:
        await conn.execute("UPDATE message SET read_at=now() WHERE created_by_id=$1 AND received_by_id=$2 AND read_at IS NULL;", oq["user_id"], user_one_id)
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_more": len(ol) > oq["limit"], "has_next_page": len(ol) > oq["limit"]}}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mongodb: raise app_state.func_api_error(message="mongodb client not initialized", status_code=500)
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "database", "type": "str", "required": True}, {"name": "table", "type": "str", "required": True}])
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[])
    obj_list = ob.get("obj_list", [ob])
    res = await app_state.client_mongodb[oq["database"]][oq["table"]].insert_many(obj_list)
    output=[str(id) for id in res.inserted_ids]
    return {"status": 1, "message": output}
    
@router.post("/my/blob-delete-url")
async def func_api_my_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services}, {"name": "url", "type": "list:str", "required": True}])
    service, urls, user_id = ob["service"], ob["url"], request.state.user["id"]
    if len(urls) > 500: raise Exception("maximum 500 URLs allowed per request")
    await app_state.func_blob_url_delete(app_state=app_state, service=service, urls=urls, user_id=user_id)
    return {"status": 1, "message": f"{len(urls)} {service} URLs processed"}

@router.post("/my/blob-delete-all")
async def func_api_my_blob_delete_all(*, request: Request):
    app_state = request.app.state
    user_id = request.state.user["id"]
    res = await app_state.func_blob_delete_all(app_state=app_state, user_id=user_id, limit=500)
    return {"status": 1, "message": res}
