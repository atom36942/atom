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
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "table", "type": "str", "required": 1, "allowed": app_state.cache_postgres_schema_table_list, "default": None}, {"name": "mode", "type": "str", "required": 0, "allowed": ["now", "buffer"], "default": "now"}])
    enabled_create_tables = app_state.config_table_public_create_enable or []
    if "*" not in enabled_create_tables and oq["table"] not in enabled_create_tables: raise Exception(f"creation disabled for table: {oq['table']}")
    ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[])
    obj_list = ob.get("obj_list", [ob])
    if restricted_key := next((key for item in obj_list for key in item if key in app_state.config_column_admin), None): raise Exception(f"unauthorized update to restricted field: {restricted_key}")
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/public/object-read")
async def func_api_public_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": app_state.cache_postgres_db_name_list, "default": None}, {"name": "table", "type": "str", "required": 1, "allowed": app_state.cache_postgres_schema_table_list, "default": None}, {"name": "limit", "type": "int", "required": 0, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": 0, "allowed": None, "default": 1}, {"name": "order", "type": "str", "required": 0, "allowed": None, "default": "id desc"}, {"name": "column", "type": "str", "required": 0, "allowed": None, "default": "*"}, {"name": "relation", "type": "list", "required": 0, "allowed": None, "default": []}, {"name": "filter", "type": "list", "required": 0, "allowed": None, "default": []}])
    client_postgres = app_state.client_postgres if oq["db"] is None else app_state.client_postgres_dict[oq["db"]]
    if not client_postgres: raise Exception("postgres client not initialized")
    enabled_tables = app_state.config_table_public_read_enable or []
    if "*" not in enabled_tables and oq["table"] not in enabled_tables: raise Exception(f"read disabled for table: {oq['table']}")
    if (disabled_relation_table := next((parts[1] for rel in oq["relation"] for parts in ([p.strip() for p in rel.split(",", 4)],) if len(parts) >= 2 and "*" not in enabled_tables and parts[1] not in enabled_tables), None)) is not None: raise Exception(f"relation read disabled for table: {disabled_relation_table}")
    ol = await app_state.func_postgres_read(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}
    
@router.get("/public/converter-number")
async def func_api_public_converter_number(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "datatype", "type": "str", "required": 1, "allowed": ["smallint", "int", "bigint"], "default": None}, {"name": "mode", "type": "str", "required": 1, "allowed": ["encode", "decode"], "default": None}, {"name": "x", "type": "str", "required": 1, "allowed": None, "default": None}])
    res = await app_state.func_converter_number(datatype=oq["datatype"], mode=oq["mode"], x=oq["x"])
    return {"status": 1, "message": res}

@router.get("/public/otp-verify")
async def func_api_public_otp_verify(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "type", "type": "str", "required": 1, "allowed": ["email", "mobile"], "default": None}, {"name": "value", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": 1, "allowed": None, "default": None}])
    return {"status": 1, "message": await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=oq["value"] if oq["type"] == "email" else None, mobile=oq["value"] if oq["type"] == "mobile" else None, config_otp_expiry_sec=app_state.config_otp_expiry_sec)}

@router.post("/public/otp-send-email")
async def func_api_public_otp_send_email(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_email_services, "default": None}, {"name": "sender", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "email", "type": "str", "required": 1, "allowed": None, "default": None}])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, email=oq["email"], mobile=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_email(app_state=app_state, service=oq["service"], sender=oq["sender"], email=oq["email"], otp=otp)
    return {"status": 1, "message": res}

@router.post("/public/otp-send-mobile")
async def func_api_public_otp_send_mobile(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_mobile_services, "default": None}, {"name": "mobile", "type": "str", "required": 1, "allowed": None, "default": None}])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=oq["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_mobile(app_state=app_state, service=oq["service"], mobile=oq["mobile"], otp=otp)
    return {"status": 1, "message": res}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "mobile", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "message", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "template_id", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "entity_id", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "sender_id", "type": "str", "required": 1, "allowed": None, "default": None}])
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=ob["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_mobile(app_state=app_state, service="sns", mobile=ob["mobile"], otp=otp, sns_template=ob)
    return {"status": 1, "message": res}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "url", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "email", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "api_token", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "start_date", "type": "str", "required": 1, "allowed": None, "default": None}, {"name": "end_date", "type": "str", "required": 1, "allowed": None, "default": None}])
    output_path = await app_state.func_jira_worklog_export(url=ob["url"], email=ob["email"], api_token=ob["api_token"], start_date=ob["start_date"], end_date=ob["end_date"])
    def iterfile():
        with open(output_path, mode="rb") as f:
            while chunk := f.read(1048576): yield chunk
        os.remove(output_path)
    return responses.StreamingResponse(iterfile(), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{os.path.basename(output_path)}"' })

@router.get("/public/table-groupby")
async def func_api_public_table_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "db", "type": "str", "required": 0, "allowed": app_state.cache_postgres_db_name_list, "default": None}, {"name": "table", "type": "str", "required": 1, "allowed": app_state.cache_postgres_schema_table_list, "default": None}, {"name": "col", "type": "str", "required": 1, "allowed": app_state.cache_postgres_schema_column_list, "default": None}, {"name": "limit", "type": "int", "required": 0, "allowed": None, "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "required": 0, "allowed": None, "default": 1}, {"name": "agg_func", "type": "str", "required": 0, "allowed": ["count", "sum", "avg", "min", "max"], "default": "count"}, {"name": "agg_col", "type": "str", "required": 0, "allowed": ["*"] + list(app_state.cache_postgres_schema_column_list), "default": "*"}, {"name": "order", "type": "str", "required": 0, "allowed": ["count desc", "count asc", "item asc", "item desc"], "default": "count desc"}, {"name": "filter", "type": "list", "required": 0, "allowed": None, "default": []}])
    client_postgres = app_state.client_postgres if oq["db"] is None else app_state.client_postgres_dict[oq["db"]]
    if not client_postgres: raise Exception("postgres client not initialized")
    enabled_tables = app_state.config_table_public_read_enable or []
    if "*" not in enabled_tables and oq["table"] not in enabled_tables: raise Exception(f"read disabled for table: {oq['table']}")
    res = await app_state.func_postgres_groupby_read(app_state=app_state, client_postgres=client_postgres, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], agg=oq["agg_func"], a_col=oq["agg_col"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}
