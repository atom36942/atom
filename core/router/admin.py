#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#admin
@router.post("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, buffer_limit=0, cache_postgres_buffer=app_state.cache_postgres_buffer, client_postgres_conn=None)
    await app_state.func_postgres_update(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, created_by_id=None, is_return_ids=0, buffer_limit=0, cache_postgres_buffer=app_state.cache_postgres_buffer, client_postgres_conn=None)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres_pool=app_state.client_postgres_pool) if app_state.client_postgres_pool else {}
    app_state.cache_postgres_schema_tables = list(app_state.cache_postgres_schema.keys())
    app_state.cache_postgres_schema_columns = sorted(list(set(col for table in app_state.cache_postgres_schema.values() for col in table.keys())))
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("cache_users_role")) if app_state.client_postgres_pool else {}
    app_state.cache_users_is_active = await app_state.func_postgres_map_column(client_postgres_pool=app_state.client_postgres_pool, config_sql=app_state.config_sql.get("cache_users_is_active")) if app_state.client_postgres_pool else {}
    await app_state.func_postgres_clean(client_postgres_pool=app_state.client_postgres_pool, config_table=app_state.config_table)
    if app_state.config_is_enable_reset_tmp == 1: app_state.func_folder_reset(folder_path="tmp")
    return {"status": 1, "message": "done"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None), ("mode", "str", 0, ["now", "buffer"], "now"), ("is_serialize", "int", 0, [0, 1], 0), ("queue", "str", 0, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = app_state.func_request_obj_list_read(obj_body=ob)
    return {"status": 1, "message": await app_state.func_orchestrator_obj_create(user_id=None, api_role="admin", table=oq["table"], mode=oq["mode"], is_serialize=oq["is_serialize"], queue=oq["queue"], obj_list=obj_list, config_table_create_disable_my=app_state.config_table_create_disable_my, config_table_create_enable_public=app_state.config_table_create_enable_public, config_column_disable=app_state.config_column_disable, config_table=app_state.config_table, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_create=app_state.func_postgres_create, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, client_postgres_conn=None)}

@router.post("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None), ("mode", "str", 0, ["now", "buffer"], "now"), ("is_serialize", "int", 0, [0, 1], 0), ("otp", "int", 0, None, None), ("queue", "str", 0, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = app_state.func_request_obj_list_read(obj_body=ob)
    return {"status": 1, "message": await app_state.func_orchestrator_obj_update(user_id=None, api_role="admin", table=oq["table"], mode=oq["mode"], is_serialize=oq["is_serialize"], queue=oq["queue"], otp=oq["otp"], obj_list=obj_list, config_table=app_state.config_table, config_is_enable_otp_users_update_admin=app_state.config_is_enable_otp_users_update_admin, config_column_disable=app_state.config_column_disable, config_column_enable_single_update=app_state.config_column_enable_single_update, config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check, func_otp_verify=app_state.func_otp_verify, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, config_expiry_sec_otp=app_state.config_expiry_sec_otp, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_update=app_state.func_postgres_update, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, client_postgres_conn=None)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None), ("limit", "int", 0, None, 100), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("creator_key", "str", 0, None, None), ("action_key", "str", 0, None, None)])
    return {"status": 1, "message": await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], filter_obj=oq, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], creator_key=oq["creator_key"], action_key=oq["action_key"])}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None), ("ids", "str", 1, None, None)])
    return {"status": 1, "message": await app_state.func_postgres_delete(client_postgres_pool=app_state.client_postgres_pool, table=ob["table"], ids=ob["ids"], created_by_id=None, client_postgres_conn=None)}

@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("query", "str", 1, None, None), ("mode", "str", 0, ["read", "write"], "read")])
    return {"status": 1, "message": await app_state.func_postgres_runner(client_postgres_pool=app_state.client_postgres_pool, mode=ob["mode"], query=ob["query"])}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, None, None)])
    return await app_state.func_postgres_export(client_postgres_pool=app_state.client_postgres_pool, query=f"SELECT * FROM {oq['table']}")

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("table", "str", 1, app_state.cache_postgres_schema_tables, None), ("file", "file", 1, [], None), ("is_serialize", "int", 0, [0, 1], 1)])
    count = await app_state.func_orchestrator_postgres_import(table=of["table"], upload_file=of["file"][-1], mode=of["mode"], is_serialize=of["is_serialize"], config_regex=app_state.config_regex, func_regex_check=app_state.func_regex_check, client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_create=app_state.func_postgres_create, func_postgres_update=app_state.func_postgres_update, func_postgres_delete=app_state.func_postgres_delete, func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/redis-import")
async def func_api_admin_redis_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "delete"], None), ("file", "file", 1, [], None)])
    if of["mode"] == "create":
        count = await app_state.func_redis_create(upload_file=of["file"][-1], client_redis=app_state.client_redis, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    elif of["mode"] == "delete":
        count = await app_state.func_redis_delete(upload_file=of["file"][-1], client_redis=app_state.client_redis, func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    return {"status": 1, "message": f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("mode", "str", 1, ["create", "update", "delete"], None), ("database", "str", 1, None, None), ("table", "str", 1, None, None), ("file", "file", 1, [], None)])
    if of["mode"] == "create":
        count = await app_state.func_mongodb_create(upload_file=of["file"][-1], client_mongodb=app_state.client_mongodb, database=of["database"], table=of["table"], func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    elif of["mode"] == "update":
        count = await app_state.func_mongodb_update(upload_file=of["file"][-1], client_mongodb=app_state.client_mongodb, database=of["database"], table=of["table"], func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    elif of["mode"] == "delete":
        count = await app_state.func_mongodb_delete(upload_file=of["file"][-1], client_mongodb=app_state.client_mongodb, database=of["database"], table=of["table"], func_api_file_to_chunks=app_state.func_api_file_to_chunks)
    return {"status": 1, "message": f"{count} rows processed"}

@router.get("/admin/blob-container-read")
async def func_api_admin_blob_container_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, ["s3", "azure"], None, None, None)])
    if oq["service"] == "s3":
        output = await app_state.func_s3_container_read(client_s3=app_state.client_s3)
    elif oq["service"] == "azure":
        output = await app_state.func_azure_container_read(client_azure_blob=app_state.client_azure_blob)
    return {"status": 1, "message": output}

@router.post("/admin/blob-container-ops")
async def func_api_admin_blob_container_ops(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, ["s3", "azure"], None), ("mode", "str", 1, ["create", "public", "empty", "delete"], None), ("container", "str", 1, None, None)])
    return {"status": 1, "message": await app_state.func_orchestrator_blob_container_ops(service=oq["service"], mode=oq["mode"], container=oq["container"], client_s3=app_state.client_s3, config_s3_region_name=app_state.config_s3_region_name, client_s3_resource=app_state.client_s3_resource, client_azure_blob=app_state.client_azure_blob, func_s3_container_create=app_state.func_s3_container_create, func_s3_container_public=app_state.func_s3_container_public, func_s3_container_empty=app_state.func_s3_container_empty, func_s3_container_delete=app_state.func_s3_container_delete, func_azure_container_create=app_state.func_azure_container_create, func_azure_container_delete=app_state.func_azure_container_delete)}

@router.post("/admin/blob-url-delete")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("url", "list", 1, [], None)])
    return {"status": 1, "message": await app_state.func_orchestrator_blob_url_delete(url=ob["url"], client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, func_s3_url_delete=app_state.func_s3_url_delete, func_azure_url_delete=app_state.func_azure_url_delete)}
