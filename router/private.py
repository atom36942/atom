# packages
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import orjson
from azure.storage.blob import BlobSasPermissions, ContainerSasPermissions, generate_blob_sas, generate_container_sas
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/private/send-email")
async def func_api_private_send_email(request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_email_services, "default": None}, {"name": "sender", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "to", "type": "list", "required": True, "allowed": None, "default": None}, {"name": "subject", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "text", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "cc", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "bcc", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "reply_to", "type": "list", "required": False, "allowed": None, "default": []}])
    res = await app_state.func_email_send(app_state=app_state, service=ob["service"], sender=ob["sender"], to=ob["to"], subject=ob["subject"], text=ob["text"], cc=ob["cc"], bcc=ob["bcc"], reply_to=ob["reply_to"])
    return {"status":1,"message":res}

@router.post("/private/blob-upload-file")
async def func_api_private_blob_upload_file(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "file", "type": "file", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_blob_upload_file(app_state=app_state, service=of["service"], container=of["container"], files=of["file"], user_id=request.state.user["id"])
    return {"status":1,"message":res}

@router.post("/private/blob-upload-url")
async def func_api_private_blob_upload_url(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "count", "type": "int", "required": False, "allowed": None, "default": 1}])
    res = await app_state.func_blob_upload_url(app_state=app_state, service=oq["service"], container=oq["container"], count=oq["count"], user_id=request.state.user["id"])
    return {"status":1,"message":res}

@router.post("/private/blob-container-sas")
async def func_api_private_blob_container_sas(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": True, "allowed": None, "default": None}])
    if oq["service"] == "s3":
        raise Exception("s3 is not allowed for this api")
    container = oq["container"]
    if oq["service"] == "azure":
        sas_token = generate_container_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, permission=ContainerSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_blob_expire_sec_preview))
        return {"status":1,"message":{"sas_token": sas_token, "expiry_sec": app_state.config_blob_expire_sec_preview}}

@router.post("/private/blob-preview-urls")
async def func_api_private_blob_preview_urls(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "urls", "type": "list", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_blob_preview_urls_get(client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, config_azure_account_name=app_state.config_azure_account_name, config_azure_account_key=app_state.config_azure_account_key, config_blob_expire_sec_preview=app_state.config_blob_expire_sec_preview, service=of["service"], urls=of["urls"])
    return {"status":1,"message":res}

@router.get("/private/object-read")
async def func_api_private_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if oq["table"] not in cache_postgres_schema: raise Exception(f"table '{oq['table']}' not found")
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    enabled_tables = app_state.config_table_private_read_enabled or []
    if (disabled_relation_table := next((parts[1] for rel in oq["relation"] for parts in ([p.strip() for p in rel.split(",", 4)],) if len(parts) >= 2 and "*" not in enabled_tables and parts[1] not in enabled_tables), None)) is not None: raise Exception(f"relation read disabled for table: {disabled_relation_table}")
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/private/table-column-groupby")
async def func_api_private_table_column_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "col", "type": "list", "required": True, "allowed": None, "default": None}, {"name": "agg", "type": "str", "required": False, "allowed": ["count", "sum", "avg", "min", "max"], "default": "count"}, {"name": "agg_col", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": 1000}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "count desc"}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    res = await app_state.func_postgres_table_column_groupby_read(app_state=app_state, client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], agg=oq["agg"], agg_col=oq["agg_col"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

@router.get("/private/table-column-distinct")
async def func_api_private_table_column_distinct(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "col", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": 1000}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": ["item asc", "item desc", "asc", "desc"], "default": "item asc"}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    res = await app_state.func_postgres_table_column_distinct_read(app_state=app_state, client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

