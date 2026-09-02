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
    res = await app_state.func_admin_sync(app_state=app_state, app_routes=request.app.routes)
    return {"status": 1, "message": res}

@router.get("/admin/postgres-info")
async def func_api_admin_postgres_info(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    info = await app_state.func_postgres_info_read(client_postgres=client_postgres)
    return {"status": 1, "message": info}

@router.get("/admin/postgres-schema")
async def func_api_admin_postgres_schema(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    schema = await app_state.func_postgres_schema_read(client_postgres=client_postgres)
    return {"status": 1, "message": schema}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": False, "allowed": ["now", "buffer"], "default": "now"}])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="created_by_id")
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if oq["table"] not in cache_postgres_schema: raise Exception(f"table '{oq['table']}' not found")
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/admin/table-column-groupby")
async def func_api_admin_table_column_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "col", "type": "list", "required": True, "allowed": None, "default": None}, {"name": "agg", "type": "str", "required": False, "allowed": ["count", "sum", "avg", "min", "max"], "default": "count"}, {"name": "agg_col", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": 1000}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "count desc"}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    res = await app_state.func_postgres_table_column_groupby_read(app_state=app_state, client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], agg=oq["agg"], agg_col=oq["agg_col"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

@router.get("/admin/table-column-distinct")
async def func_api_admin_table_column_distinct(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "col", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": 1000}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": ["item asc", "item desc", "asc", "desc"], "default": "item asc"}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    res = await app_state.func_postgres_table_column_distinct_read(app_state=app_state, client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": False, "allowed": None, "default": None}])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    await app_state.func_check_user_update_permission(app_state=app_state, table=oq["table"], obj_list=obj_list, scope="admin", otp=oq["otp"])
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="updated_by_id", purpose="update tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="updated_by_id")
    created_by_id = None
    result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], obj_list=obj_list, created_by_id=created_by_id, client_postgres_conn=None, config_regex=app_state.config_regex)
    return {"status": 1, "message": result}

@router.post("/admin/object-delete")
async def func_api_admin_object_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "ids", "type": "list:int", "required": True, "allowed": None, "default": None}])
    app_state.func_check_batch_limit(app_state=app_state, items=ob["ids"])
    app_state.func_check_user_delete_permission(app_state=app_state, table=ob["table"], scope="admin")
    created_by_id = None
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=ob["table"], ids=ob["ids"], created_by_id=created_by_id)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.delete("/admin/user-delete")
async def func_api_admin_user_delete(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "id", "type": "int", "required": True, "allowed": None, "default": None}])
    if not app_state.config_is_user_delete: raise Exception("users hard delete disabled")
    deleted_count = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table="users", ids=[oq["id"]], created_by_id=None)
    return {"status": 1, "message": f"{deleted_count} user deleted"}

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": True, "allowed": ["create", "update", "delete"], "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "file", "type": "file", "required": True, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=of["db"])
    res = await app_state.func_postgres_import(app_state=app_state, mode=of["mode"], table=of["table"], file=of["file"][-1], client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema)
    return {"status": 1, "message": res}

@router.post("/admin/redis-import")
async def func_api_admin_redis_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=False, param_specs=[{"name": "mode", "type": "str", "required": True, "allowed": ["create", "delete"], "default": None}, {"name": "file", "type": "file", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_redis_import(client_redis=app_state.client_redis, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, mode=of["mode"], file=of["file"][-1])
    return {"status": 1, "message": res}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=False, param_specs=[{"name": "mode", "type": "str", "required": True, "allowed": ["create", "update", "delete"], "default": None}, {"name": "database", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "file", "type": "file", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_mongodb_import(client_mongodb=app_state.client_mongodb, mode=of["mode"], database=of["database"], table=of["table"], file=of["file"][-1])
    return {"status": 1, "message": res}

@router.get("/admin/blob-container-read")
async def func_api_admin_blob_container_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}])
    res = await app_state.func_blob_containers_read(client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, service=oq["service"])
    return {"status": 1, "message": res}

@router.post("/admin/blob-container-ops")
async def func_api_admin_blob_container_ops(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": True, "allowed": ["create", "public", "empty", "delete"], "default": None}])
    res = await app_state.func_blob_container_ops(client_s3=app_state.client_s3, client_s3_resource=app_state.client_s3_resource, client_azure_blob=app_state.client_azure_blob, config_aws_s3_region_name=app_state.config_aws_s3_region_name, service=oq["service"], container=oq["container"], mode=oq["mode"])
    return {"status": 1, "message": res}

@router.post("/admin/blob-delete-url")
async def func_api_admin_blob_url_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "url", "type": "list", "required": True, "allowed": None, "default": None}])
    service, urls = ob["service"], ob["url"]
    if len(urls) > 500: raise Exception("maximum 500 URLs allowed per request")
    await app_state.func_blob_url_delete(app_state=app_state, service=service, urls=urls, user_id=None)
    return {"status": 1, "message": f"{len(urls)} {service} URLs processed"}

@router.post("/admin/postgres-query-runner-write")
async def func_api_admin_postgres_query_runner_write(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_postgres_query_runner_write(client_postgres=app_state.client_postgres, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/postgres-query-runner-read")
async def func_api_admin_postgres_query_runner_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    res = await app_state.func_postgres_query_runner_read(client_postgres=client_postgres, config_query_runner_read_limit=app_state.config_query_runner_read_limit, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/postgres-query-runner-read-export")
async def func_api_admin_postgres_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    generator = await app_state.func_postgres_query_runner_read_export(client_postgres=client_postgres, config_query_runner_export_limit=app_state.config_query_runner_export_limit, sql=ob["sql"])
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=postgres_query_result.csv"})

@router.post("/admin/postgres-query-generator-ai")
async def func_api_admin_postgres_query_ai(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "ai", "type": "str", "required": False, "allowed": app_state.config_ai_services, "default": "gemini"}, {"name": "question", "type": "str", "required": True, "allowed": None, "default": None}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    res = await app_state.func_postgres_query_generator_ai(client_postgres=client_postgres, client_gemini=app_state.client_gemini, client_openai=app_state.client_openai, func_postgres_schema_read_ai=app_state.func_postgres_schema_read_ai, cache_postgres_schema_ai=cache_postgres_schema_ai, config_query_runner_read_limit=app_state.config_query_runner_read_limit, ai=ob["ai"], question=ob["question"])
    return {"status": 1, "message": res}

@router.post("/admin/mssql-query-runner-write")
async def func_api_admin_mssql_query_runner_write(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_mssql_query_runner_write(client_mssql=app_state.client_mssql, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/mssql-query-runner-read")
async def func_api_admin_mssql_query_runner_read(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_mssql_query_runner_read(client_mssql=app_state.client_mssql, config_query_runner_read_limit=app_state.config_query_runner_read_limit, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/mssql-query-runner-read-export")
async def func_api_admin_mssql_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    generator = await app_state.func_mssql_query_runner_read_export(client_mssql=app_state.client_mssql, config_query_runner_export_limit=app_state.config_query_runner_export_limit, sql=ob["sql"])
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=mssql_query_runner_read_export.csv"})

@router.post("/admin/clickhouse-query-runner-write")
async def func_api_admin_clickhouse_query_runner_write(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_clickhouse_query_runner_write(client_clickhouse=app_state.client_clickhouse, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/clickhouse-query-runner-read")
async def func_api_admin_clickhouse_query_runner_read(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_clickhouse_query_runner_read(client_clickhouse=app_state.client_clickhouse, config_query_runner_read_limit=app_state.config_query_runner_read_limit, sql=ob["sql"])
    return {"status": 1, "message": res}

@router.post("/admin/clickhouse-query-runner-read-export")
async def func_api_admin_clickhouse_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "sql", "type": "str", "required": True, "allowed": None, "default": None}])
    generator = await app_state.func_clickhouse_query_runner_read_export(client_clickhouse=app_state.client_clickhouse, config_query_runner_export_limit=app_state.config_query_runner_export_limit, sql=ob["sql"])
    return StreamingResponse(generator, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=clickhouse_query_runner_read_export.csv"})

@router.post("/admin/clickhouse-query-generator-ai")
async def func_api_admin_clickhouse_query_generator_ai(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "ai", "type": "str", "required": False, "allowed": app_state.config_ai_services, "default": "gemini"}, {"name": "question", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_clickhouse_query_generator_ai(client_clickhouse=app_state.client_clickhouse, client_gemini=app_state.client_gemini, client_openai=app_state.client_openai, func_clickhouse_schema_read_ai=app_state.func_clickhouse_schema_read_ai, cache_clickhouse_schema_ai=app_state.cache_clickhouse_schema_ai, config_query_runner_read_limit=app_state.config_query_runner_read_limit, ai=ob["ai"], question=ob["question"])
    return {"status": 1, "message": res}
