#router
from fastapi import APIRouter
router = APIRouter()

#import
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#public
@router.get("/public/converter-number")
async def func_api_public_converter_number(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("datatype", "str", 1, ["smallint", "int", "bigint"], None, None, None), ("mode", "str", 1, ["encode", "decode"], None, None, None), ("x", "str", 1, None, None, None, None)])
    return {"status": 1, "message": app_state.func_converter_number(type=oq["datatype"], mode=oq["mode"], x=oq["x"])}

@router.post("/public/object-create")
async def func_api_public_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("mode", "str", 0, ["now", "buffer"], "now", None, None), ("is_serialize", "int", 0, [0, 1], 0, None, None), ("queue", "str", 0, None, None, None, None)])
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    return {"status": 1, "message": await app_state.func_orchestrator_obj_create(user_id=None, api_role="public", obj_query=oq, obj_body=ob, config_table_create_my=app_state.config_table_create_my, config_table_create_public=app_state.config_table_create_public, config_column_blocked=app_state.config_column_blocked, config_table=app_state.config_table, client_celery_producer=app_state.client_celery_producer, client_kafka_producer=app_state.client_kafka_producer, client_rabbitmq_producer=app_state.client_rabbitmq_producer, client_redis_producer=app_state.client_redis_producer, func_orchestrator_producer=app_state.func_orchestrator_producer, func_postgres_create=app_state.func_postgres_create, client_postgres_pool=app_state.client_postgres_pool, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer)}

@router.get("/public/object-read")
async def func_api_public_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None), ("order", "str", 0, None, "id desc", None, None), ("column", "str", 0, None, "*", None, None), ("creator_key", "str", 0, None, None, None, None), ("action_key", "str", 0, None, None, None, None)])
    if app_state.config_table_read_public and oq["table"] not in app_state.config_table_read_public: raise Exception(f"table not allowed: {oq['table']}, allowed: {app_state.config_table_read_public}")
    ol = await app_state.func_postgres_read(client_postgres_pool=app_state.client_postgres_pool, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], filter_obj=oq, limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], creator_key=oq["creator_key"], action_key=oq["action_key"])
    return {"status": 1, "message": ol}

@router.get("/public/otp-verify-email")
async def func_api_public_otp_verify_email(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("otp", "int", 1, None, None, None, None), ("email", "str", 1, None, None, None, None)])
    return {"status": 1, "message": await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=oq["otp"], email=oq["email"], mobile=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)}

@router.get("/public/otp-verify-mobile")
async def func_api_public_otp_verify_mobile(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("otp", "int", 1, None, None, None, None), ("mobile", "str", 1, None, None, None, None)])
    return {"status": 1, "message": await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=oq["otp"], mobile=oq["mobile"], email=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)}

@router.post("/public/otp-send-email-ses")
async def func_api_public_otp_send_email_ses(*, request: Request):
    app_state = request.app.state
    od = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("sender", "str", 1, None, None, None, None), ("email", "str", 1, None, None, None, None)])
    otp = await app_state.func_otp_generate(client_postgres_pool=app_state.client_postgres_pool, email=od["email"], mobile=None)
    return {"status": 1, "message": app_state.func_ses_send_email(client_ses=app_state.client_ses, from_email=od["sender"], to_emails=[od["email"]], subject="your otp code", body=str(otp))}

@router.post("/public/otp-send-email-resend")
async def func_api_public_otp_send_email_resend(*, request: Request):
    app_state = request.app.state
    od = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("sender", "str", 1, None, None, None, None), ("email", "str", 1, None, None, None, None)])
    otp = await app_state.func_otp_generate(client_postgres_pool=app_state.client_postgres_pool, email=od["email"], mobile=None)
    return {"status": 1, "message": await app_state.func_resend_send_email(config_resend_url=app_state.config_resend_url, config_resend_key=app_state.config_resend_key, from_email=od["sender"], to_email=od["email"], email_subject="your otp code", email_content=f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")}

@router.post("/public/otp-send-mobile-sns")
async def func_api_public_otp_send_mobile_sns(*, request: Request):
    app_state = request.app.state
    od = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mobile", "str", 1, None, None, None, None)])
    otp = await app_state.func_otp_generate(client_postgres_pool=app_state.client_postgres_pool, mobile=od["mobile"], email=None)
    return {"status": 1, "message": app_state.func_sns_send_mobile_message(client_sns=app_state.client_sns, mobile=od["mobile"], message=str(otp))}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(*, request: Request):
    app_state = request.app.state
    od = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mobile", "str", 1, None, None, None, None), ("message", "str", 1, None, None, None, None), ("template_id", "str", 1, None, None, None, None), ("entity_id", "str", 1, None, None, None, None), ("sender_id", "str", 1, None, None, None, None)])
    otp = await app_state.func_otp_generate(client_postgres_pool=app_state.client_postgres_pool, mobile=od["mobile"], email=None)
    return {"status": 1, "message": app_state.func_sns_send_mobile_message_template(client_sns=app_state.client_sns, mobile=od["mobile"], message=od["message"].replace("{otp}", str(otp)), template_id=od["template_id"], entity_id=od["entity_id"], sender_id=od["sender_id"])}

@router.post("/public/otp-send-mobile-fast2sms")
async def func_api_public_otp_send_mobile_fast2sms(*, request: Request):
    app_state = request.app.state
    od = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mobile", "str", 1, None, None, None, None)])
    otp = await app_state.func_otp_generate(client_postgres_pool=app_state.client_postgres_pool, mobile=od["mobile"], email=None)
    return {"status": 1, "message": app_state.func_fast2sms_send_otp_mobile(config_fast2sms_url=app_state.config_fast2sms_url, config_fast2sms_key=app_state.config_fast2sms_key, mobile=od["mobile"], otp_code=str(otp))}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("url", "str", 1, None, None, None, None), ("email", "str", 1, None, None, None, None), ("api_token", "str", 1, None, None, None, None), ("start_date", "str", 1, None, None, None, None), ("end_date", "str", 1, None, None, None, None)])
    import uuid; output_path = f"tmp/{uuid.uuid4().hex}.csv"
    await asyncio.to_thread(app_state.func_jira_worklog_export, url=ob["url"], email=ob["email"], api_token=ob["api_token"], start_date=ob["start_date"], end_date=ob["end_date"], output_path=output_path)
    return await app_state.func_client_download_file(file_path=output_path, is_delete_after=1, chunk_size=1048576)

@router.get("/public/table-tag-read")
async def func_api_public_table_tag_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("table", "str", 1, app_state.cache_postgres_schema_tables, None, None, None), ("column", "str", 1, app_state.cache_postgres_schema_columns, None, None, None), ("limit", "int", 0, None, 100, None, None), ("page", "int", 0, None, 1, None, None), ("filter_column", "str", 0, app_state.cache_postgres_schema_columns, None, None, None), ("filter_value", "str", 0, None, None, None, None)])
    val = (await app_state.func_postgres_serialize(client_postgres_pool=app_state.client_postgres_pool, cache_postgres_schema=app_state.cache_postgres_schema, table=oq["table"], obj_list=[{oq["filter_column"]: oq["filter_value"]}], is_base=0))[0][oq["filter_column"]] if oq["filter_column"] and oq["filter_value"] else None
    return {"status": 1, "message": await app_state.func_table_tag_read(client_postgres_pool=app_state.client_postgres_pool, table=oq["table"], column=oq["column"], limit=oq["limit"], page=oq["page"], filter_column=oq["filter_column"], filter_value=val)}
