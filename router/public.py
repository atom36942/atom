# packages
import asyncio
import os
import re
import uuid
import httpx
import orjson
import pandas as pd
from fastapi import APIRouter, Request, responses
from jira import JIRA

# router
router = APIRouter()

# api
@router.post("/public/object-create")
async def func_api_public_object_create(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "mode", "type": "str", "required": False, "allowed": ["now", "buffer"], "default": "now"}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="public", action="create")
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="created_by_id")
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/public/object-read")
async def func_api_public_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": False, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": False, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    if oq["table"] not in cache_postgres_schema: raise Exception(f"table '{oq['table']}' not found")
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="public", action="read")
    enabled_tables = app_state.config_table_public_read_enabled or []
    if (disabled_relation_table := next((parts[1] for rel in oq["relation"] for parts in ([p.strip() for p in rel.split(",", 4)],) if len(parts) >= 2 and "*" not in enabled_tables and parts[1] not in enabled_tables), None)) is not None: raise Exception(f"relation read disabled for table: {disabled_relation_table}")
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}
    
@router.get("/public/converter-number")
async def func_api_public_converter_number(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "datatype", "type": "str", "required": True, "allowed": ["smallint", "int", "bigint"], "default": None}, {"name": "mode", "type": "str", "required": True, "allowed": ["encode", "decode"], "default": None}, {"name": "x", "type": "str", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_converter_number(datatype=oq["datatype"], mode=oq["mode"], x=oq["x"])
    return {"status": 1, "message": res}

@router.get("/public/otp-verify")
async def func_api_public_otp_verify(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "type", "type": "str", "required": True, "allowed": ["email", "mobile"], "default": None}, {"name": "value", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": True, "allowed": None, "default": None}])
    return {"status": 1, "message": await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=oq["value"] if oq["type"] == "email" else None, mobile=oq["value"] if oq["type"] == "mobile" else None, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static)}

@router.post("/public/otp-send-email")
async def func_api_public_otp_send_email(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_email_services, "default": None}, {"name": "sender", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "email", "type": "str", "required": True, "allowed": None, "default": None}])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, email=oq["email"], mobile=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_email(app_state=app_state, service=oq["service"], sender=oq["sender"], email=oq["email"], otp=otp)
    return {"status": 1, "message": res}

@router.post("/public/otp-send-mobile")
async def func_api_public_otp_send_mobile(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_mobile_services, "default": None}, {"name": "mobile", "type": "str", "required": True, "allowed": None, "default": None}])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=oq["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_mobile(app_state=app_state, service=oq["service"], mobile=oq["mobile"], otp=otp)
    return {"status": 1, "message": res}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "mobile", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "message", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "template_id", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "entity_id", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "sender_id", "type": "str", "required": True, "allowed": None, "default": None}])
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=ob["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_mobile(app_state=app_state, service="sns", mobile=ob["mobile"], otp=otp, sns_template=ob)
    return {"status": 1, "message": res}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "url", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "email", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "api_token", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "start_date", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "end_date", "type": "str", "required": True, "allowed": None, "default": None}])
    output_path = await app_state.func_jira_worklog_export(url=ob["url"], email=ob["email"], api_token=ob["api_token"], start_date=ob["start_date"], end_date=ob["end_date"])
    def iterfile():
        with open(output_path, mode="rb") as f:
            while chunk := f.read(1048576): yield chunk
        os.remove(output_path)
    return responses.StreamingResponse(iterfile(), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{os.path.basename(output_path)}"' })

@router.get("/public/table-column-values")
async def func_api_public_table_column_values(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "db", "type": "str", "required": False, "allowed": None, "default": None}, {"name": "table", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "col", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "include_count", "type": "bool", "required": False, "allowed": None, "default": True}, {"name": "limit", "type": "int", "required": False, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": False, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": False, "allowed": ["count desc", "count asc", "item asc", "item desc"], "default": "count desc"}, {"name": "filter", "type": "list", "required": False, "allowed": None, "default": []}])
    client_postgres, cache_postgres_schema, cache_postgres_schema_ai = app_state.func_postgres_db_select(app_state=app_state, db=oq["db"])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="public", action="read")
    res = await app_state.func_postgres_column_values_read(app_state=app_state, client_postgres=client_postgres, cache_postgres_schema=cache_postgres_schema, table=oq["table"], col=oq["col"], include_count=oq["include_count"], limit=oq["limit"], page=oq["page"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

@router.post("/public/blob-upload-file")
async def func_api_public_blob_upload_file(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "file", "type": "file", "required": True, "allowed": None, "default": None}])
    res = await app_state.func_blob_upload_file(app_state=app_state, service=of["service"], container=of["container"], files=of["file"], user_id=request.state.user.get("id"))
    return {"status": 1, "message": res}

@router.post("/public/blob-upload-url")
async def func_api_public_blob_upload_url(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services, "default": None}, {"name": "container", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "count", "type": "int", "required": False, "allowed": None, "default": 1}])
    res = await app_state.func_blob_upload_url(app_state=app_state, service=oq["service"], container=oq["container"], count=oq["count"], user_id=request.state.user.get("id"))
    return {"status": 1, "message": res}

@router.post("/public/password-hash")
async def func_api_public_password_hash(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "password", "type": "str", "required": True, "allowed": None, "default": None}])
    return {"status": 1, "message": app_state.client_password_hasher.hash(str(ob["password"]))}
