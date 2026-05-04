#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#admin
@router.post("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    return await app_state.func_postgres_sync(client_postgres=app_state.client_postgres, config_postgres=app_state.config_postgres)

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("obj", "list", 1, [], None)])
    return await app_state.func_postgres_object_create(client_postgres=app_state.client_postgres, table=oq["table"], obj_list=ob["obj"])

@router.post("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("obj", "list", 1, [], None)])
    return await app_state.func_postgres_object_update(client_postgres=app_state.client_postgres, table=oq["table"], obj_list=ob["obj"])

@router.post("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, None, None), ("limit", "int", 0, None, 10), ("offset", "int", 0, None, 0)])
    return await app_state.func_postgres_object_read(client_postgres=app_state.client_postgres, table=oq["table"], limit=oq["limit"], offset=oq["offset"])

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("id", "list", 1, [], None)])
    return await app_state.func_postgres_ids_delete(client_postgres=app_state.client_postgres, table=oq["table"], id_list=ob["id"])

@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("query", "str", 1, None, None)])
    return await app_state.func_orchestrator_postgres_runner(query=ob["query"], client_postgres=app_state.client_postgres, func_postgres_runner=app_state.func_postgres_runner)

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, None, None)])
    return await app_state.func_orchestrator_postgres_export(table=oq["table"], client_postgres=app_state.client_postgres, func_postgres_export=app_state.func_postgres_export)

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("table", "str", 1, None, None), ("file", "file", 1, [], None)])
    return await app_state.func_orchestrator_postgres_import(table=of["table"], upload_file=of["file"][-1], client_postgres=app_state.client_postgres, func_postgres_import=app_state.func_postgres_import, func_api_file_to_chunks=app_state.func_api_file_to_chunks)

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
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, ["s3", "azure"], None, None, None), ("mode", "str", 1, ["create", "public", "empty", "delete"], None, None, None), ("container", "str", 1, None, None, None, None)])
    return {"status": 1, "message": await app_state.func_orchestrator_blob_container_ops(service=oq["service"], mode=oq["mode"], container=oq["container"], client_s3=app_state.client_s3, config_s3_region_name=app_state.config_s3_region_name, client_s3_resource=app_state.client_s3_resource, client_azure_blob=app_state.client_azure_blob, func_s3_container_create=app_state.func_s3_container_create, func_s3_container_public=app_state.func_s3_container_public, func_s3_container_empty=app_state.func_s3_container_empty, func_s3_container_delete=app_state.func_s3_container_delete, func_azure_container_create=app_state.func_azure_container_create, func_azure_container_delete=app_state.func_azure_container_delete)}

@router.post("/admin/blob-url-delete")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("url", "list", 1, [], None, None, None)])
    return {"status": 1, "message": await app_state.func_orchestrator_blob_url_delete(url=ob["url"], client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, func_s3_url_delete=app_state.func_s3_url_delete, func_azure_url_delete=app_state.func_azure_url_delete)}
