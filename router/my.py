# packages
import urllib.parse
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    user_id = request.state.user["id"]
    user = await app_state.func_user_read_single(client_postgres=client_postgres, user_id=user_id)
    metadata = {k: [dict(r) for r in await client_postgres.fetch(v, user_id)] for k, v in app_state.config_sql.get("profile_metadata", {}).items()}
    user["metadata"] = metadata
    return {"status": 1, "message": user}

@router.post("/my/ping")
async def func_api_my_ping(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    await app_state.client_postgres.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", request.state.user["id"])
    return {"status": 1, "message": "pong"}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    user = await app_state.func_user_read_single(client_postgres=app_state.client_postgres, user_id=request.state.user["id"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "days", "type": "int", "required": True, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    sql = "SELECT path AS api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY path LIMIT 1000;"
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql, oq["days"], request.state.user["id"])
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": False, "allowed": ["now", "buffer"], "default": "now"}, {"name": "queue", "type": "str", "required": False, "allowed": app_state.config_queue_services, "default": None}])
    if "*" in app_state.config_table_my_create_blocked or oq["table"] in app_state.config_table_my_create_blocked: raise Exception(f"creation disabled for table: {oq['table']}")
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="created_by_id")
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_create", payload={"mode": oq["mode"], "table": oq["table"], "obj_list": obj_list})}
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    filters = oq["filter"] + [f"""created_by_id = {request.state.user["id"]}"""]
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=filters, limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/my/object-read-owned")
async def func_api_my_owned_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "ownership_column", "type": "str", "required": True, "allowed": app_state.config_column_ownership, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    filters = oq["filter"] + [f"""{oq["ownership_column"]} = {request.state.user["id"]}"""]
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=filters, limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    schema_cols = cache_postgres_schema.get(oq["table"], {})
    if oq["ownership_column"] == "received_by_id" and "id" in schema_cols and "read_at" in schema_cols:
        app_state.func_postgres_mark_read(client_postgres=app_state.client_postgres, table=oq["table"], ownership_column=oq["ownership_column"], user_id=request.state.user["id"], ids=[r.get("id") for r in ol if isinstance(r, dict)])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": False, "allowed": None, "default": None}, {"name": "queue", "type": "str", "required": False, "allowed": app_state.config_queue_services, "default": None}])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    await app_state.func_check_user_update_permission(app_state=app_state, table=oq["table"], obj_list=obj_list, scope="my", otp=oq["otp"], user_id=request.state.user.get("id"))
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="updated_by_id", purpose="update tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="updated_by_id")
    created_by_id = request.state.user["id"] if oq["table"] != "users" else None
    if oq["queue"]: return {"status": 1, "message": await app_state.func_producer(queue=oq["queue"], client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, channel="func_postgres_update", payload={"table": oq["table"], "obj_list": obj_list, "created_by_id": created_by_id})}
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None)}

@router.post("/my/object-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "ids", "type": "list:int", "required": True, "allowed": None, "default": None}])
    app_state.func_check_batch_limit(app_state=app_state, items=ob["ids"])
    app_state.func_check_user_delete_permission(app_state=app_state, table=ob["table"], scope="my", ids=ob["ids"], user_id=request.state.user.get("id"))
    app_state.func_check_table_column_exists(app_state=app_state, table=ob["table"], column="created_by_id", purpose="ownership tracking")
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=request.state.user["id"])
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/my/user-delete")
async def func_api_my_user_delete(*, request: Request):
    app_state, current_user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "id", "type": "int", "required": True, "allowed": None, "default": None}])
    if not app_state.config_is_user_delete: raise Exception("users hard delete disabled")
    if int(oq["id"]) != int(current_user_id): raise Exception("users table delete allowed only for own account")
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table="users", ids=[oq["id"]], created_by_id=None)
    return {"status": 1, "message": f"{deleted_count} user deleted"}

@router.delete("/my/object-delete-all")
async def func_api_my_object_delete_all(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}])
    app_state.func_check_user_delete_permission(app_state=app_state, table=oq["table"], scope="my_all")
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="my", action="delete_all")
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    deleted_count = await app_state.func_postgres_delete_all(client_postgres=app_state.client_postgres, table=oq["table"], ownership_column="created_by_id", user_id=user_id)
    return {"status": 1, "message": f"{deleted_count} objects deleted"}

@router.post("/my/object-delete-owned")
async def func_api_my_owned_ids_delete(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "ownership_column", "type": "str", "required": True, "allowed": app_state.config_column_ownership, "default": None}, {"name": "ids", "type": "list:int", "required": True, "allowed": None, "default": None}])
    app_state.func_check_batch_limit(app_state=app_state, items=ob["ids"])
    app_state.func_check_user_delete_permission(app_state=app_state, table=ob["table"], scope="my_owned")
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=user_id, ownership_column=ob["ownership_column"])
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/my/object-delete-owned-all")
async def func_api_my_owned_object_delete_all(*, request: Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "ownership_column", "type": "str", "required": True, "allowed": app_state.config_column_ownership, "default": None}])
    app_state.func_check_user_delete_permission(app_state=app_state, table=oq["table"], scope="my_owned_all")
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="my", action="delete_owned_all")
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column=oq["ownership_column"], purpose="ownership tracking")
    deleted_count = await app_state.func_postgres_delete_all(client_postgres=app_state.client_postgres, table=oq["table"], ownership_column=oq["ownership_column"], user_id=user_id)
    return {"status": 1, "message": f"{deleted_count} objects deleted"}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": True, "allowed": ["all", "unread", "read"], "default": None}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    where_clause = {"read": "received_by_id=$1 AND read_at IS NOT NULL", "unread": "received_by_id=$1 AND read_at IS NULL"}.get(oq["mode"], "1=1")
    sql = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - received_by_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR received_by_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {oq['order']} LIMIT {oq['limit'] + 1} OFFSET {(oq['page']-1)*oq['limit']};"
    async with client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, request.state.user["id"])]
        return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "user_id", "type": "int", "required": True, "allowed": None, "default": None}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    user_one_id = request.state.user["id"]
    sql = f"SELECT * FROM message WHERE ((created_by_id=$1 AND received_by_id=$2) OR (created_by_id=$2 AND received_by_id=$1)) ORDER BY {oq['order']} LIMIT {oq['limit'] + 1} OFFSET {(oq['page']-1)*oq['limit']};"
    async with client_postgres.acquire() as conn:
        ol = [dict(r) for r in await conn.fetch(sql, user_one_id, oq["user_id"])]
    async with app_state.client_postgres.acquire() as conn:
        await conn.execute("UPDATE message SET read_at=now() WHERE created_by_id=$1 AND received_by_id=$2;", oq["user_id"], user_one_id)
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mongodb: raise Exception("mongodb client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "database", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[])
    obj_list = ob.get("obj_list", [ob])
    res = await app_state.client_mongodb[oq["database"]][oq["table"]].insert_many(obj_list)
    output=[str(id) for id in res.inserted_ids]
    return {"status": 1, "message": output}
    
@router.post("/my/blob-delete-url")
async def func_api_my_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "url", "type": "list:str", "required": True, "allowed": None, "default": None}])
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
