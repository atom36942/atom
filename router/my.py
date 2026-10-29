# import
from fastapi import APIRouter
from fastapi import Request
from fastapi import WebSocket
from fastapi.responses import StreamingResponse

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
    if app_state.config_is_profile_update_last_active_at and not app_state.config_is_read_only: app_state.func_background_run(app_state=app_state, coroutine=app_state.func_user_last_active_update(client_postgres=app_state.client_postgres_dict.get("master"), user_id=user_id))
    return {"status": 1, "message": user}

@router.websocket("/my/message-socket")
async def func_api_my_message_socket(*, websocket: WebSocket):
    await websocket.app.state.func_message_socket(app_state=websocket.app.state, websocket=websocket)

@router.post("/my/ping")
async def func_api_my_ping(*, request: Request):
    app_state = request.app.state
    await app_state.func_user_last_active_update(client_postgres=app_state.client_postgres_dict.get("master"), user_id=request.state.user["id"])
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
    if not app_state.client_postgres_log_api: raise app_state.func_api_error(message="API logging is off (config_postgres_db_log_api)", status_code=503)
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
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_dict.get("queue"), channel="func_postgres_create", payload={"mode": oq["mode"], "table": oq["table"], "obj_list": obj_list})}
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=request.state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, buffer_postgres=app_state.buffer_postgres_create, buffer_rows_max=app_state.config_buffer_rows_max, buffer_full_mode="reject", config_column_regex=app_state.config_column_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_read, "default": "created_by_id"}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1, "minimum": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "relation", "type": "list", "default": []}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], relation=oq["relation"], scope="my", action="read")
    app_state.func_check_table_column_exists(app_state=app_state, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    filters = oq["filter"] + [f"""{oq["ownership_column"]} = {request.state.user["id"]}"""]
    ol = await app_state.func_postgres_read(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=filters, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"], config_column_read_blocked=app_state.config_column_read_blocked, blocked_tables=app_state.config_table_my_read_blocked)
    schema_cols = request.state.cache_postgres_schema.get(oq["table"], {})
    if oq["ownership_column"] == "received_by_id" and "id" in schema_cols and "read_at" in schema_cols:
        app_state.func_postgres_mark_read(client_postgres=app_state.client_postgres_dict.get("master"), table=oq["table"], ownership_column=oq["ownership_column"], user_id=request.state.user["id"], ids=[r.get("id") for r in ol if isinstance(r, dict)])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_more": len(ol) > oq["limit"], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/my/object-read-export")
async def func_api_my_object_read_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_read, "default": "created_by_id"}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "filter", "type": "list", "default": []}, {"name": "connection", "type": "str"}], strict=True, strict_types=True, reject_unknown=True)
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], relation=[], scope="my", action="read")
    app_state.func_check_table_column_exists(app_state=app_state, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    filters = oq["filter"] + [f"""{oq["ownership_column"]} = {request.state.user["id"]}"""]
    generator = await app_state.func_postgres_read_export(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, table=oq["table"], filter=filters, order=oq["order"], column=oq["column"], export_limit=app_state.config_export_limit, config_column_read_blocked=app_state.config_column_read_blocked, blocked_tables=app_state.config_table_my_read_blocked)
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{oq["table"]}.csv"'})

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_update, "default": "created_by_id"}, {"name": "queue", "type": "str", "allowed": app_state.config_queue_services}])
    app_state.func_check_table_not_users(table=oq["table"], api="/my/user-update")
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="updated_by_id", purpose="update tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="updated_by_id")
    created_by_id = request.state.user["id"]
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_dict.get("queue"), channel="func_postgres_update", payload={"table": oq["table"], "obj_list": obj_list, "created_by_id": created_by_id, "ownership_column": oq["ownership_column"]})}
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, ownership_column=oq["ownership_column"], client_postgres_conn=None)}

@router.put("/my/user-update")
async def func_api_my_user_update(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    # only otp is typed; every other field passes through (strict off) and is checked against the users table
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "otp", "type": "int"}])
    if "id" in ob and str(ob["id"]) != str(user_id): raise Exception("ownership issue: cannot update other users")
    values = await app_state.func_user_update_check(client_postgres=request.state.client_postgres, obj=ob, is_admin=False, is_otp_required=True, config_column_single_update=app_state.config_column_single_update, config_column_users_blocked=app_state.config_column_users_blocked, config_column_users_my_blocked=app_state.config_column_users_my_blocked, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static, config_otp_max_attempt=app_state.config_otp_max_attempt)
    await app_state.func_postgres_update(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, table="users", obj_list=[{**values, "id": user_id, "updated_by_id": user_id}], created_by_id=None, client_postgres_conn=None)
    return {"status": 1, "message": "user updated"}

@router.delete("/my/user-delete")
async def func_api_my_user_delete(*, request: Request):
    app_state = request.app.state
    return {"status": 1, "message": await app_state.func_user_delete(client_postgres=request.state.client_postgres, user_id=request.state.user["id"], config_is_user_delete=app_state.config_is_user_delete)}

@router.post("/my/object-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_delete, "default": "created_by_id"}])
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ids", "type": "list:int", "required": True}])
    table, ids = ob["table"], ob["ids"]
    app_state.func_check_table_not_users(table=table, api="/my/user-delete")
    app_state.func_check_batch_limit(app_state=app_state, items=ids)
    ownership_column = oq["ownership_column"]
    app_state.func_check_table_column_exists(app_state=app_state, table=table, column=ownership_column, purpose="ownership tracking")
    created_by_id = request.state.user["id"]
    deleted_count = await app_state.func_postgres_delete(client_postgres=request.state.client_postgres, client_postgres_conn=None, cache_postgres_schema=request.state.cache_postgres_schema, table=table, ids=ids, created_by_id=created_by_id, ownership_column=ownership_column)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/my/object-delete-all")
async def func_api_my_object_delete_all(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ownership_column", "type": "str", "allowed": app_state.config_column_ownership_delete, "default": "created_by_id"}])
    app_state.func_check_table_not_users(table=oq["table"], api="/my/user-delete")
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="my", action="delete_all")
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    res = await app_state.func_postgres_delete_all(client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], ownership_column=oq["ownership_column"], user_id=user_id, limit=getattr(app_state, "config_batch_item_limit", 5000) or 5000)
    return {"status": 1, "message": {"deleted_count": res["deleted_count"], "has_more": res["has_more"], "has_next_page": res["has_next_page"]}}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "mode", "type": "str", "required": True, "allowed": ["all", "unread", "read"]}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1, "minimum": 1}])
    fetch_limit, offset = app_state.func_message_pagination(limit=oq["limit"], page=oq["page"], max_limit=app_state.config_sql_read_limit_max)
    order_sql = app_state.func_message_order(order=oq["order"], cache_postgres_schema=request.state.cache_postgres_schema)
    where_clause = {"read": "received_by_id=$1 AND read_at IS NOT NULL", "unread": "received_by_id=$1 AND read_at IS NULL"}.get(oq["mode"], "1=1")
    sql = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - received_by_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR received_by_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {order_sql} LIMIT $2 OFFSET $3;"  # noqa: S608 - ORDER BY built by func_message_order from known columns
    async with request.state.client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, request.state.user["id"], fetch_limit, offset)]
        return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_more": len(ol) > oq["limit"], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "user_id", "type": "int", "required": True}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1, "minimum": 1}])
    if not app_state.client_postgres_dict.get("master"): raise app_state.func_api_error(message="postgres client not initialized", status_code=500)
    user_one_id = request.state.user["id"]
    fetch_limit, offset = app_state.func_message_pagination(limit=oq["limit"], page=oq["page"], max_limit=app_state.config_sql_read_limit_max)
    order_sql = app_state.func_message_order(order=oq["order"], cache_postgres_schema=request.state.cache_postgres_schema)
    sql = f"SELECT * FROM message WHERE ((created_by_id=$1 AND received_by_id=$2) OR (created_by_id=$2 AND received_by_id=$1)) ORDER BY {order_sql} LIMIT $3 OFFSET $4;"  # noqa: S608 - ORDER BY built by func_message_order from known columns
    async with request.state.client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, user_one_id, oq["user_id"], fetch_limit, offset)]
    async with app_state.client_postgres_dict.get("master").acquire() as conn:
        await conn.execute("UPDATE message SET read_at=now() WHERE created_by_id=$1 AND received_by_id=$2 AND read_at IS NULL;", oq["user_id"], user_one_id)
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_more": len(ol) > oq["limit"], "has_next_page": len(ol) > oq["limit"]}}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mongodb: raise app_state.func_api_error(message="mongodb client not initialized", status_code=500)
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "database", "type": "str", "required": True}, {"name": "table", "type": "str", "required": True}], strict=True, reject_unknown=True)
    if oq["table"] not in app_state.config_mongodb_my_create_allowed.get(oq["database"], []): raise app_state.func_api_error(message=f"creation disabled for mongodb collection: {oq['database']}.{oq['table']}", status_code=403)
    obj_list = await app_state.func_extract_request_object_list(request=request)
    if not isinstance(obj_list, list) or not obj_list or not all(isinstance(x, dict) for x in obj_list): raise Exception("obj_list must be a non-empty list of objects")
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    for obj in obj_list:
        if any(k in ("_id", "created_by_id") or k.startswith("$") or "." in k for k in obj): raise Exception("fields _id, created_by_id, $-prefixed and dotted keys are not allowed")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="created_by_id")
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
