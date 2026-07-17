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
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now")])
    enabled_create_tables = app_state.config_table_public_create_enable or []
    if "*" not in enabled_create_tables and oq["table"] not in enabled_create_tables: raise Exception(f"creation disabled for table: {oq['table']}")
    ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if restricted_key := next((key for item in obj_list for key in item if key in app_state.config_column_admin), None): raise Exception(f"unauthorized update to restricted field: {restricted_key}")
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/public/object-read")
async def func_api_public_object_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    enabled_tables = app_state.config_table_public_read_enable or []
    if "*" not in enabled_tables and oq["table"] not in enabled_tables: raise Exception(f"read disabled for table: {oq['table']}")
    if (disabled_relation_table := next((parts[1] for rel in oq["relation"] for parts in ([p.strip() for p in rel.split(",", 4)],) if len(parts) >= 2 and "*" not in enabled_tables and parts[1] not in enabled_tables), None)) is not None: raise Exception(f"relation read disabled for table: {disabled_relation_table}")
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}
    
@router.get("/public/converter-number")
async def func_api_public_converter_number(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("datatype", "str", 1, ["smallint", "int", "bigint"], None), ("mode", "str", 1, ["encode", "decode"], None), ("x", "str", 1, None, None)])
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}; charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if oq["datatype"] not in type_limits: raise ValueError(f"invalid type: {oq['datatype']}, allowed: {list(type_limits.keys())}")
    base = len(charset); max_len = type_limits[oq["datatype"]]
    if oq["mode"] == "encode":
        val_str = str(oq["x"]); val_len = len(val_str)
        if val_len > max_len: raise ValueError(f"input too long {val_len} > {max_len}")
        result_num = val_len
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1: raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return {"status": 1, "message": result_num}
    if oq["mode"] == "decode":
        try: num_val = int(oq["x"])
        except Exception: raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return {"status": 1, "message": "".join(decoded_chars[::-1][1:]) if decoded_chars else ""}

@router.get("/public/otp-verify")
async def func_api_public_otp_verify(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("type", "str", 1, ["email", "mobile"], None), ("value", "str", 1, None, None), ("otp", "int", 1, None, None)])
    return {"status": 1, "message": await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=oq["value"] if oq["type"] == "email" else None, mobile=oq["value"] if oq["type"] == "mobile" else None, config_otp_expiry_sec=app_state.config_otp_expiry_sec)}

@router.post("/public/otp-send-email")
async def func_api_public_otp_send_email(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_email_services, None), ("sender", "str", 1, None, None), ("email", "str", 1, None, None)])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, email=oq["email"], mobile=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_email(app_state=app_state, service=oq["service"], sender=oq["sender"], email=oq["email"], otp=otp)
    return {"status": 1, "message": res}

@router.post("/public/otp-send-mobile")
async def func_api_public_otp_send_mobile(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_mobile_services, None), ("mobile", "str", 1, None, None)])
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=oq["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_mobile(app_state=app_state, service=oq["service"], mobile=oq["mobile"], otp=otp)
    return {"status": 1, "message": res}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mobile", "str", 1, None, None), ("message", "str", 1, None, None), ("template_id", "str", 1, None, None), ("entity_id", "str", 1, None, None), ("sender_id", "str", 1, None, None)])
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=ob["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    res = await app_state.func_otp_send_mobile(app_state=app_state, service="sns", mobile=ob["mobile"], otp=otp, sns_template=ob)
    return {"status": 1, "message": res}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("url", "str", 1, None, None), ("email", "str", 1, None, None), ("api_token", "str", 1, None, None), ("start_date", "str", 1, None, None), ("end_date", "str", 1, None, None)])
    output_path = await app_state.func_jira_worklog_export(url=ob["url"], email=ob["email"], api_token=ob["api_token"], start_date=ob["start_date"], end_date=ob["end_date"])
    def iterfile():
        with open(output_path, mode="rb") as f:
            while chunk := f.read(1048576): yield chunk
        os.remove(output_path)
    return responses.StreamingResponse(iterfile(), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{os.path.basename(output_path)}"' })

@router.get("/public/table-groupby")
async def func_api_public_table_groupby(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_table_list, None), ("col", "str", 1, app_state.cache_postgres_schema_column_list, None), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("agg_func", "str", 0, ["count", "sum", "avg", "min", "max"], "count"), ("agg_col", "str", 0, ["*"] + list(app_state.cache_postgres_schema_column_list), "*"), ("order", "str", 0, ["count desc", "count asc", "item asc", "item desc"], "count desc"), ("filter", "list", 0, None, [])])
    enabled_tables = app_state.config_table_public_read_enable or []
    if "*" not in enabled_tables and oq["table"] not in enabled_tables: raise Exception(f"read disabled for table: {oq['table']}")
    res = await app_state.func_postgres_groupby_read(app_state=app_state, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], agg=oq["agg_func"], a_col=oq["agg_col"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}
