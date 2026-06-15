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
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("mode", "str", 0, ["now", "buffer"], "now")])
    enabled_create_tables = app_state.config_table_create_enable_public or []
    if "*" not in enabled_create_tables and oq["table"] not in enabled_create_tables: raise Exception(f"creation disabled for table: {oq['table']}")
    ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if restricted_key := next((key for item in obj_list for key in item if key == "deleted_at" or key in app_state.config_column_admin), None): raise Exception("deleted_at cannot be set on create; use deactivated_at for reversible inactive state" if restricted_key == "deleted_at" else f"unauthorized creation of restricted field: {restricted_key}")
    if "created_by_id" not in app_state.cache_postgres_schema.get(oq["table"], {}): raise Exception(f"table '{oq['table']}' lacks required 'created_by_id' column for ownership tracking")
    if request.state.user.get("id"): obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get(oq["table"], {}).get("buffer_limit", app_state.config_buffer_limit_default), mode=oq["mode"], table=oq["table"], obj_list=obj_list)}

@router.get("/public/object-read")
async def func_api_public_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("column", "str", 0, None, "*"), ("relation", "list", 0, None, []), ("filter", "list", 0, None, [])])
    enabled_tables = app_state.config_table_enable_read_public or []
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
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("type", "str", 1, ["email", "mobile"], None), ("value", "str", 1, None, None), ("otp", "int", 1, None, None)])
    return {"status": 1, "message": await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=oq["otp"], email=oq["value"] if oq["type"] == "email" else None, mobile=oq["value"] if oq["type"] == "mobile" else None, config_otp_expiry_sec=app_state.config_otp_expiry_sec)}

@router.post("/public/otp-send-email")
async def func_api_public_otp_send_email(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_email_services, None), ("sender", "str", 1, None, None), ("email", "str", 1, None, None)])
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, email=oq["email"], mobile=None, config_otp_length=app_state.config_otp_length)
    if oq["service"] == "ses":
        app_state.client_ses.send_email(Source=oq["sender"], Destination={"ToAddresses": [oq["email"]]}, Message={"Subject": {"Data": "your otp code"}, "Body": {"Html": {"Data": str(otp)}}})
    if oq["service"] == "resend":
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": oq["sender"], "to": [oq["email"]], "subject": "your otp code", "html": f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>"}
        async with httpx.AsyncClient() as client:
            response = await client.post(app_state.config_resend_url, headers=headers, data=orjson.dumps(payload).decode("utf-8"))
            if response.status_code != 200: raise Exception(f"failed to send email: {response.text}")
    if oq["service"] == "azure":
        if not app_state.client_azure_email: raise Exception("azure email client not configured")
        message = {"senderAddress": oq["sender"], "recipients": {"to": [{"address": oq["email"]}]}, "content": {"subject": "your otp code", "plainText": str(otp)}}
        await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(message).result())
    return {"status": 1, "message": "done"}

@router.post("/public/otp-send-mobile")
async def func_api_public_otp_send_mobile(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_mobile_services, None), ("mobile", "str", 1, None, None)])
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=oq["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    message = "done"
    if oq["service"] == "sns":
        app_state.client_sns.publish(PhoneNumber=oq["mobile"], Message=str(otp))
    if oq["service"] == "fast2sms":
        params={"authorization": app_state.config_fast2sms_key, "route": "otp", "variables_values": str(otp), "numbers": oq["mobile"]}
        async with httpx.AsyncClient() as client:
            response = await client.get(app_state.config_fast2sms_url, params=params)
            message = response.json()
    return {"status": 1, "message": message}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(*, request: Request):
    app_state = request.app.state
    ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mobile", "str", 1, None, None), ("message", "str", 1, None, None), ("template_id", "str", 1, None, None), ("entity_id", "str", 1, None, None), ("sender_id", "str", 1, None, None)])
    otp = await app_state.func_otp_generate(client_postgres=app_state.client_postgres, mobile=ob["mobile"], email=None, config_otp_length=app_state.config_otp_length)
    app_state.client_sns.publish(PhoneNumber=ob["mobile"], Message=ob["message"].replace("{otp}", str(otp)), MessageAttributes={"AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": ob["sender_id"]}, "AWS.MM.SMS.TemplateId": {"DataType": "String", "StringValue": ob["template_id"]}, "AWS.MM.SMS.EntityId": {"DataType": "String", "StringValue": ob["entity_id"]}, "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}})
    return {"status": 1, "message": "done"}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("url", "str", 1, None, None), ("email", "str", 1, None, None), ("api_token", "str", 1, None, None), ("start_date", "str", 1, None, None), ("end_date", "str", 1, None, None)])
    os.makedirs("tmp", exist_ok=True)
    output_path = f"tmp/{uuid.uuid4().hex}.csv"
    def _export():
        jira = JIRA(server=ob["url"], basic_auth=(ob["email"], ob["api_token"]))
        log_rows, people = [], set()
        for issue in jira.enhanced_search_issues(f"worklogDate >= '{ob['start_date']}' AND worklogDate <= '{ob['end_date']}'", maxResults=0):
            if getattr(issue.fields, "assignee", None): people.add(issue.fields.assignee.displayName)
            for w in jira.worklogs(issue.id):
                if ob["start_date"] <= w.started[:10] <= ob["end_date"]:
                    people.add(w.author.displayName)
                    log_rows.append((w.author.displayName, w.started[:10], w.timeSpentSeconds / 3600))  
        cols = pd.date_range(ob["start_date"], ob["end_date"]).strftime("%Y-%m-%d").tolist()
        df = pd.DataFrame(log_rows, columns=["author", "date", "hours"])
        if not df.empty: df = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0)
        df.reindex(index=sorted(people), columns=cols, fill_value=0).round(0).astype(int).to_csv(output_path)
        return output_path
    await asyncio.to_thread(_export)
    def iterfile():
        with open(output_path, mode="rb") as f:
            while chunk := f.read(1048576): yield chunk
        os.remove(output_path)
    return responses.StreamingResponse(iterfile(), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{os.path.basename(output_path)}"' })

@router.get("/public/table-groupby")
async def func_api_public_table_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_table_list, None), ("col", "str", 1, app_state.cache_postgres_column_list, None), ("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("agg_func", "str", 0, ["count", "sum", "avg", "min", "max"], "count"), ("agg_col", "str", 0, ["*"] + list(app_state.cache_postgres_column_list), "*"), ("order", "str", 0, ["count desc", "count asc", "item asc", "item desc"], "count desc"), ("filter", "list", 0, None, [])])
    enabled_tables = app_state.config_table_enable_read_public or []
    if "*" not in enabled_tables and oq["table"] not in enabled_tables: raise Exception(f"read disabled for table: {oq['table']}")
    table, col, limit, page, agg, a_col, order = oq["table"], oq["col"], oq["limit"], oq["page"], oq["agg_func"], oq["agg_col"], oq["order"]
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)) or not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(col)) or (a_col != "*" and not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(a_col))): raise Exception("invalid identifier")
    where_clause, values = await app_state.func_postgres_where_build(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=table, filter=oq["filter"], prefix="x.")
    bind_idx = len(values) + 1
    is_array = "[]" in (dt := app_state.cache_postgres_schema.get(table, {}).get(col, {}).get("datatype", "text").lower()) or "array" in dt
    agg_sql = f'{agg}(*)' if agg == "count" and a_col == "*" else f'{agg}("{a_col}")'
    order_sql = (("agg_val" if agg != "count" else "count(*)") if "count" in order else "item_col") + (" DESC" if "desc" in order else " ASC")
    q_col = f'"{col}"'; sql = f'SELECT {"item_col" if is_array else "x."+q_col+" AS item_col"}, {agg_sql} AS agg_val FROM "{table}" x {f"CROSS JOIN LATERAL unnest(x."+q_col+") item_col" if is_array else ""} {where_clause} GROUP BY item_col ORDER BY {order_sql} LIMIT ${bind_idx} OFFSET ${bind_idx+1}'
    values.extend([limit + 1, (page - 1) * limit])
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        rows = await conn.fetch(sql, *values)
        ol = [{"item": row["item_col"], "value": row["agg_val"]} for row in rows]
        return {"status": 1, "message": {"obj_list": ol[:limit], "has_next_page": len(ol) > limit}}
