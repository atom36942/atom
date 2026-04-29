#router
from fastapi import APIRouter
router = APIRouter()

#import
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#my
@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    app_state = request.app.state
    profile = await app_state.func_user_profile_read(client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"], config_sql=app_state.config_sql, func_user_single_read=app_state.func_user_single_read)
    token = await app_state.func_token_encode(user=profile, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status": 1, "message": profile | token}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request: Request):
    app_state = request.app.state
    user = await app_state.func_user_single_read(client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status": 1, "message": token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("days", "int", 1, None, None, None, None)])
    obj_list = await app_state.func_user_api_usage_read(client_postgres_pool=app_state.client_postgres_pool, days=obj_query["days"], user_id=request.state.user["id"])
    return {"status": 1, "message": obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["soft", "hard"], None, None, None)])
    output = await app_state.func_user_account_delete(mode=obj_query["mode"], client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"])
    return {"status": 1, "message": output}

@router.get("/my/message-received")
async def func_api_my_message_received(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None, None, None), ("order", "str", 0, None, "id desc", None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None)])
    obj_list = await app_state.func_message_received(client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"], mode=obj_query["mode"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
    return {"status": 1, "message": obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["all", "unread", "read"], None, None, None), ("order", "str", 0, None, "id desc", None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None)])
    obj_list = await app_state.func_message_inbox(client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"], mode=obj_query["mode"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
    return {"status": 1, "message": obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("user_id", "int", 1, None, None, None, None), ("order", "str", 0, None, "id desc", None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None)])
    obj_list = await app_state.func_message_thread(client_postgres_pool=app_state.client_postgres_pool, user_one_id=request.state.user["id"], user_id=obj_query["user_id"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
    asyncio.create_task(app_state.func_message_thread_mark_read(client_postgres_pool=app_state.client_postgres_pool, current_user_id=request.state.user["id"], partner_id=obj_query["user_id"]))
    return {"status": 1, "message": obj_list}

@router.delete("/my/message-delete-single")
async def func_api_my_message_delete_single(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("id", "int", 1, None, None, None, None)])
    output = await app_state.func_message_delete_single(client_postgres_pool=app_state.client_postgres_pool, id=obj_query["id"], user_id=request.state.user["id"])
    return {"status": 1, "message": output}

@router.delete("/my/message-delete-bulk")
async def func_api_my_message_delete_bulk(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["sent", "received", "all"], None, None, None)])
    output = await app_state.func_message_delete_bulk(client_postgres_pool=app_state.client_postgres_pool, user_id=request.state.user["id"], mode=obj_query["mode"])
    return {"status": 1, "message": output}

@router.get("/my/parent-read")
async def func_api_my_parent_read(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("parent_table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("parent_column", "str", 1, app_state.cache_postgres_schema_columns, None, None, None), ("order", "str", 0, None, "id desc", None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None)])
    output = await app_state.func_parent_read(client_postgres_pool=app_state.client_postgres_pool, table=obj_query["table"], parent_column=obj_query["parent_column"], parent_table=obj_query["parent_table"], created_by_id=request.state.user["id"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
    return {"status": 1, "message": output}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(*, request: Request):
    app_state = request.app.state
    obj_body = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("ids", "str", 1, None, None, None, None)])
    output = await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, table=obj_body["table"], ids=obj_body["ids"], created_by_id=request.state.user.get("id", 0))
    return {"status": 1, "message": output}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("mode", "str", 0, ["now", "buffer"], "now", None, None), ("is_serialize", "int", 0, [0, 1], 0, None, None), ("queue", "str", 0, None, None, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_create(user_id=request.state.user["id"], api_role="my", obj_query=oq, obj_body=ob, config_table_create_my=app_state.config_table_create_my, config_table_create_public=app_state.config_table_create_public, config_column_blocked=app_state.config_column_blocked, config_table=app_state.config_table, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_create=app_state.func_postgres_create, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer)}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("is_serialize", "int", 0, [0, 1], 0, None, None), ("otp", "int", 0, None, None, None, None), ("queue", "str", 0, None, None, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_update(user_id=request.state.user["id"], api_role="my", obj_query=oq, obj_body=ob, config_is_otp_users_update_admin=app_state.config_is_otp_users_update_admin, config_column_blocked=app_state.config_column_blocked, config_column_single_update=app_state.config_column_single_update, func_otp_verify=app_state.func_otp_verify, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, config_expiry_sec_otp=app_state.config_expiry_sec_otp, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_update=app_state.func_postgres_update, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None), ("order", "str", 0, None, "id desc", None, None), ("column", "str", 0, None, "*", None, None), ("creator_key", "str", 0, None, None, None, None), ("action_key", "str", 0, None, None, None, None)])
    oq["created_by_id"] = f"""=,{request.state.user["id"]}"""
    ol = await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], filter_obj=oq, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], creator_key=oq["creator_key"], action_key=oq["action_key"])
    return {"status": 1, "message": ol}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request: Request):
    app_state = request.app.state
    obj_query = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("database", "str", 1, None, None, None, None), ("table", "str", 1, None, None, None, None)])
    obj_body = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = obj_body.get("obj_list", [obj_body])
    output = await app_state.func_mongodb_object_create(client_mongodb=app_state.client_mongodb, database=obj_query["database"], table=obj_query["table"], obj_list=obj_list)
    return {"status": 1, "message": output}
