# packages
import asyncio
import csv
import io
import json
import re
import orjson
from azure.storage.blob import PublicAccess
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from google.genai import types
from pymongo import DeleteOne, UpdateOne

# router
router = APIRouter()

# api
@router.get("/admin/sync")
async def func_api_admin_sync(*, request: Request):
    app_state = request.app.state
    if app_state.client_postgres: await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=None, func_postgres_serialize=None, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table=None, obj_list=None, buffer_limit=None, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=None, func_regex_check=None)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres=app_state.client_postgres) if app_state.client_postgres else {}
    app_state.cache_postgres_schema_ai = await app_state.func_postgres_schema_read_ai(client_postgres=app_state.client_postgres) if app_state.client_postgres else {}
    app_state.cache_postgres_schema_dict = {name: await app_state.func_postgres_schema_read(client_postgres=client) for name, client in app_state.client_postgres_dict.items()}
    app_state.cache_postgres_schema_ai_dict = {name: await app_state.func_postgres_schema_read_ai(client_postgres=client) for name, client in app_state.client_postgres_dict.items()}
    app_state.cache_openapi = app_state.func_openapi_spec_generate(app_routes=request.app.routes, app_state=app_state)
    app_state.cache_config = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("config"), is_json_value=1) if app_state.client_postgres and "config" in app_state.cache_postgres_schema else {}
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("users_role")) if app_state.client_postgres else {}
    app_state.cache_users_deactivated = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("users_deactivated")) if app_state.client_postgres else {}
    app_state.cache_users_deleted = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("users_deleted")) if app_state.client_postgres else {}
    return {"status": 1, "message": "done"}

@router.get("/admin/postgres-info")
async def func_api_admin_postgres_info(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if not client_postgres: raise Exception("postgres client not initialized")
    info = await app_state.func_postgres_info_read(client_postgres=client_postgres)
    return {"status": 1, "message": info}

@router.get("/admin/postgres-schema")
async def func_api_admin_postgres_schema(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if not client_postgres: raise Exception("postgres client not initialized")
    schema = await app_state.func_postgres_schema_read(client_postgres=client_postgres)
    return {"status": 1, "message": schema}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "table", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": 0, "allowed": ["now", "buffer"], "default": "now"}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[])
    obj_list = ob.get("obj_list", [ob])
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": 0, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": 0, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": 0, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": 0, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": 0, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": 0, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if not client_postgres: raise Exception("postgres client not initialized")
    if oq["table"] not in cache_postgres_schema: raise Exception(f"table '{oq['table']}' not found")
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "table", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": 0, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[])
    obj_list = ob.get("obj_list", [ob])
    if any("password" in item for item in obj_list) and any(len(item) != 2 or "id" not in item or "password" not in item for item in obj_list): raise Exception("password update requires exactly two fields (id, password)")
    if oq["table"] == "users" and app_state.config_is_otp_require_users_update == 1 and any(key in obj_list[0] for key in ("email", "mobile")): len(obj_list) <= 1 or (_ for _ in ()).throw(Exception("multi-object user update restricted")); len(obj_list[0]) == 2 or (_ for _ in ()).throw(Exception("sensitive fields must be updated individually (item length 2 required)")); await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=obj_list[0].get("email"), mobile=obj_list[0].get("mobile"), config_otp_expiry_sec=app_state.config_otp_expiry_sec)
    if "updated_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'updated_by_id' column for update tracking")
    if request.state.user.get("id"): obj_list = [dict(item, updated_by_id=request.state.user["id"]) for item in obj_list]
    created_by_id = None
    result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None, config_regex=app_state.config_regex)
    return {"status": 1, "message": result}

@router.post("/admin/object-delete")
async def func_api_admin_object_delete(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "table", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "ids", "type": "list:int", "required": 1, "allowed": None, "default": None}])
    if ob["table"] == "users" and app_state.config_is_user_delete != 1: raise Exception("users hard delete disabled")
    created_by_id = None
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=created_by_id)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": 1, "allowed": ["create", "update", "delete"], "default": None}, {"name": "table", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "file", "type": "file", "required": 1, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=of["db"])
    res = await app_state.func_postgres_import(app_state=app_state, mode=of["mode"], table=of["table"], file=of["file"][-1], client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema)
    return {"status": 1, "message": res}

@router.post("/admin/redis-import")
async def func_api_admin_redis_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, param_specs=[{"name": "mode", "type": "str", "required": 1, "allowed": ["create", "delete"], "default": None}, {"name": "file", "type": "file", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_redis_import(client_redis=app_state.client_redis, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, mode=of["mode"], file=of["file"][-1])
    return {"status": 1, "message": res}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, param_specs=[{"name": "mode", "type": "str", "required": 1, "allowed": ["create", "update", "delete"], "default": None}, {"name": "database", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "file", "type": "file", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_mongodb_import(client_mongodb=app_state.client_mongodb, mode=of["mode"], database=of["database"], table=of["table"], file=of["file"][-1])
    return {"status": 1, "message": res}

@router.get("/admin/blob-container-read")
async def func_api_admin_blob_container_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services, "default": None}])
    res = await app_state.func_blob_containers_read(client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, service=oq["service"])
    return {"status": 1, "message": res}

@router.post("/admin/blob-container-ops")
async def func_api_admin_blob_container_ops(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": 1, "allowed": ["create", "public", "empty", "delete"], "default": None}])
    res = await app_state.func_blob_container_ops(client_s3=app_state.client_s3, client_s3_resource=app_state.client_s3_resource, client_azure_blob=app_state.client_azure_blob, config_aws_s3_region_name=app_state.config_aws_s3_region_name, service=oq["service"], container=oq["container"], mode=oq["mode"])
    return {"status": 1, "message": res}

@router.post("/admin/blob-delete-url")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services, "default": None}, {"name": "url", "type": "list", "required": 1, "allowed": None, "default": None}])
    service, urls = ob["service"], ob["url"]
    if len(urls) > 500: raise Exception("maximum 500 URLs allowed per request")
    await app_state.func_blob_url_delete(app_state=app_state, service=service, urls=urls, user_id=None)
    return {"status": 1, "message": f"{len(urls)} {service} URLs processed"}

@router.post("/admin/postgres-query-runner-write")
async def func_api_admin_postgres_query_runner_write(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_postgres_query_runner_write(client_postgres=app_state.client_postgres, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/postgres-query-runner-read")
async def func_api_admin_postgres_query_runner_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    res = await app_state.func_postgres_query_runner_read(client_postgres=client_postgres, config_query_runner_read_limit=app_state.config_query_runner_read_limit, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/postgres-query-runner-read-export")
async def func_api_admin_postgres_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    generator = await app_state.func_postgres_query_runner_read_export(client_postgres=client_postgres, config_query_runner_export_limit=app_state.config_query_runner_export_limit, sql=ob["sql"])
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=postgres_query_result.csv"})

@router.post("/admin/postgres-query-generator-ai")
async def func_api_admin_postgres_query_ai(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "ai", "type": "str", "required": 0, "allowed": app_state.config_ai_services, "default": "gemini"}, {"name": "question", "type": "str", "required": 1, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    res = await app_state.func_postgres_query_generator_ai(client_postgres=client_postgres, client_gemini=app_state.client_gemini, client_openai=app_state.client_openai, func_postgres_schema_read_ai=app_state.func_postgres_schema_read_ai, cache_postgres_schema_ai=cache_postgres_schema_ai, config_query_runner_read_limit=app_state.config_query_runner_read_limit, ai=ob["ai"], question=ob["question"])
    return {"status": 1, "message": res}

@router.post("/admin/mssql-query-runner-write")
async def func_api_admin_mssql_query_runner_write(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_mssql_query_runner_write(client_mssql=app_state.client_mssql, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/mssql-query-runner-read")
async def func_api_admin_mssql_query_runner_read(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_mssql_query_runner_read(client_mssql=app_state.client_mssql, config_query_runner_read_limit=app_state.config_query_runner_read_limit, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/mssql-query-runner-read-export")
async def func_api_admin_mssql_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    generator = await app_state.func_mssql_query_runner_read_export(client_mssql=app_state.client_mssql, config_query_runner_export_limit=app_state.config_query_runner_export_limit, sql=ob["sql"])
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=mssql_query_runner_read_export.csv"})

@router.post("/admin/clickhouse-query-runner-write")
async def func_api_admin_clickhouse_query_runner_write(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_clickhouse_query_runner_write(client_clickhouse=app_state.client_clickhouse, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/clickhouse-query-runner-read")
async def func_api_admin_clickhouse_query_runner_read(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_clickhouse_query_runner_read(client_clickhouse=app_state.client_clickhouse, config_query_runner_read_limit=app_state.config_query_runner_read_limit, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/clickhouse-query-runner-read-export")
async def func_api_admin_clickhouse_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "sql", "type": "str", "required": 1, "allowed": None, "default": None}])
    generator = await app_state.func_clickhouse_query_runner_read_export(client_clickhouse=app_state.client_clickhouse, config_query_runner_export_limit=app_state.config_query_runner_export_limit, sql=ob["sql"])
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=clickhouse_query_runner_read_export.csv"})
