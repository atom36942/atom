#router
from fastapi import APIRouter
router = APIRouter()

#import
import asyncio
import orjson
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#admin
@router.get("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, buffer_limit=0, cache_postgres_buffer=app_state.cache_postgres_buffer)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres_pool=app_state.client_postgres_pool) if app_state.client_postgres_pool else {}
    app_state.cache_postgres_schema_tables = list(app_state.cache_postgres_schema.keys())
    app_state.cache_postgres_schema_columns = sorted(list(set(col for table in app_state.cache_postgres_schema.values() for col in table.keys())))
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("cache_users_role")) if app_state.client_postgres_pool else {}
    app_state.cache_users_is_active = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("cache_users_is_active")) if app_state.client_postgres_pool else {}
    await app_state.func_postgres_clean(client_postgres_pool=app_state.client_postgres_pool, config_table=app_state.config_table)
    if app_state.config_is_reset_tmp == 1:app_state.func_folder_reset(folder_path="tmp")
    return {"status": 1, "message": "done"}

@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(*, request: Request):
    app_state = request.app.state
    obj_body = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mode", "str", 1, ["read", "write"], None, None, None), ("query", "str", 1, None, None, None, None)])
    output = await app_state.func_postgres_runner(client_postgres_pool=app_state.client_postgres_pool, mode=obj_body["mode"], query=obj_body["query"])
    return {"status": 1, "message": output}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(*, request: Request):
    app_state = request.app.state
    obj_body = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("query", "str", 1, None, None, None, None)])
    stream = app_state.func_postgres_export(client_postgres_pool=app_state.client_postgres_pool, query=obj_body["query"])
    return responses.StreamingResponse(stream, media_type="text/csv", headers={"Content-Disposition": "attachment;filename=file.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    obj_f = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None, None, None), ("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("file", "file", 1, [], None, None, None), ("is_serialize", "int", 0, [0, 1], 1, None, None)])
    count = await app_state.func_orchestrator_semaphore_postgres_import(upload_file=obj_f["file"][-1], mode=obj_f["mode"], table=obj_f["table"], is_serialize=obj_f["is_serialize"], client_postgres_pool=app_state.client_postgres_pool, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_create=app_state.func_postgres_create, func_postgres_update=app_state.func_postgres_update, func_postgres_delete=app_state.func_postgres_delete, func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("mode", "str", 0, ["now", "buffer"], "now", None, None), ("is_serialize", "int", 0, [0, 1], 0, None, None), ("queue", "str", 0, None, None, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_create(user_id=None, api_role="admin", obj_query=oq, obj_body=ob, config_table_create_my=app_state.config_table_create_my, config_table_create_public=app_state.config_table_create_public, config_column_blocked=app_state.config_column_blocked, config_table=app_state.config_table, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_create=app_state.func_postgres_create, client_postgres_pool=app_state.client_postgres_pool, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer)}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("is_serialize", "int", 0, [0, 1], 0, None, None), ("otp", "int", 0, None, None, None, None), ("queue", "str", 0, None, None, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_update(user_id=None, api_role="admin", obj_query=oq, obj_body=ob, config_is_otp_users_update_admin=app_state.config_is_otp_users_update_admin, config_column_blocked=app_state.config_column_blocked, config_column_single_update=app_state.config_column_single_update, func_otp_verify=app_state.func_otp_verify, client_postgres_pool=app_state.client_postgres_pool, config_expiry_sec_otp=app_state.config_expiry_sec_otp, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_update=app_state.func_postgres_update, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None), ("order", "str", 0, None, "id desc", None, None), ("column", "str", 0, None, "*", None, None), ("creator_key", "str", 0, None, None, None, None), ("action_key", "str", 0, None, None, None, None)])
    ol = await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], filter_obj=oq, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], creator_key=oq["creator_key"], action_key=oq["action_key"])
    return {"status": 1, "message": ol}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("ids", "str", 1, None, None, None, None)])
    return {"status": 1, "message": await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, table=ob["table"], ids=ob["ids"], created_by_id=None)}

@router.post("/admin/redis-import")
async def func_api_admin_redis_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "delete"], None, None, None), ("file", "file", 1, [], None, None, None)])
    if of["mode"] == "create":
        count = await app_state.func_redis_create(upload_file=of["file"][-1], client_redis=app_state.client_redis, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    elif of["mode"] == "delete":
        count = await app_state.func_redis_delete(upload_file=of["file"][-1], client_redis=app_state.client_redis, func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None, None, None), ("database", "str", 1, None, None, None, None), ("table", "str", 1, None, None, None, None), ("file", "file", 1, [], None, None, None)])
    if of["mode"] == "create":
        count = await app_state.func_mongodb_create(upload_file=of["file"][-1], client_mongodb=app_state.client_mongodb, database=of["database"], table=of["table"], func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    elif of["mode"] == "update":
        count = await app_state.func_mongodb_update(upload_file=of["file"][-1], client_mongodb=app_state.client_mongodb, database=of["database"], table=of["table"], func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    elif of["mode"] == "delete":
        count = await app_state.func_mongodb_delete(upload_file=of["file"][-1], client_mongodb=app_state.client_mongodb, database=of["database"], table=of["table"], func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/s3-bucket-ops")
async def func_api_admin_s3_bucket_ops(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode", "str", 1, ["create", "public", "empty", "delete"], None, None, None), ("bucket", "str", 1, None, None, None, None)])
    if oq["mode"] == "create":
       output = await app_state.func_s3_bucket_create(client_s3=app_state.client_s3, config_s3_region_name=app_state.config_s3_region_name, bucket=oq["bucket"])
    elif oq["mode"] == "public":
       output = await app_state.func_s3_bucket_public(client_s3=app_state.client_s3, bucket=oq["bucket"])
    elif oq["mode"] == "empty":
       output = app_state.func_s3_bucket_empty(client_s3_resource=app_state.client_s3_resource, bucket=oq["bucket"])
    elif oq["mode"] == "delete":
       output = await app_state.func_s3_bucket_delete(client_s3=app_state.client_s3, bucket=oq["bucket"])
    return {"status": 1, "message": output}

@router.post("/admin/s3-url-delete")
async def func_api_admin_s3_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("url", "list", 1, [], None, None, None)])
    return {"status": 1, "message": app_state.func_s3_url_delete(client_s3_resource=app_state.client_s3_resource, url=ob["url"])}
