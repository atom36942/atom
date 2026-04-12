#router
from fastapi import APIRouter
router=APIRouter()

#import
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#public
@router.get("/public/converter-number")
async def func_api_public_converter_number(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request,"query",[("datatype","str",1,["smallint","int","bigint"],None,None,None),("mode","str",1,["encode","decode"],None,None,None),("x","str",1,None,None,None,None)])
   output=st.func_converter_number(obj_query["datatype"],obj_query["mode"],obj_query["x"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_public_object_create(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("mode","str",0,["now","buffer"],"now",None,None),("is_serialize","int",0,[0,1],0,None,None),("queue","str",0,None,None,None,None)])
   obj_body=await st.func_request_param_read(request,"body",[])
   return {"status":1,"message":await st.func_orchestrator_obj_create(api_role="public", obj_query=obj_query, obj_body=obj_body, user_id=request.state.user.get("id") if getattr(request.state,"user",None) else None, config_table_create_my=st.config_table_create_my, config_table_create_public=st.config_table_create_public, config_column_blocked=st.config_column_blocked, client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, config_table=st.config_table, func_orchestrator_producer=st.func_orchestrator_producer, producer_obj={"config_channel_allowed":st.config_channel_allowed, "client_celery_producer":st.client_celery_producer, "client_kafka_producer":st.client_kafka_producer, "client_rabbitmq_producer":st.client_rabbitmq_producer, "client_redis_producer":st.client_redis_producer}, func_postgres_object_create=st.func_postgres_object_create, config_limit_obj_list=st.config_limit_obj_list)}

@router.get("/public/object-read")
async def func_api_public_object_read(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None),("order","str",0,None,"id desc",None,None),("column","str",0,None,"*",None,None),("creator_key","str",0,None,None,None,None),("action_key","str",0,None,None,None,None)])
   if st.config_table_read_public and obj_query["table"] not in st.config_table_read_public:
      raise Exception(f"table not allowed: {obj_query['table']}, allowed: {st.config_table_read_public}")
   obj_list=await st.func_postgres_object_read(st.client_postgres_pool, st.func_postgres_serialize, obj_query["table"], obj_query)
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify-email")
async def func_api_public_otp_verify_email(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request,"query",[("otp","int",1,None,None,None,None),("email","str",1,None,None,None,None)])
   output=await st.func_otp_verify(st.client_postgres_pool, obj_query["otp"], obj_query["email"], None, config_expiry_sec_otp=st.config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.get("/public/otp-verify-mobile")
async def func_api_public_otp_verify_mobile(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request,"query",[("otp","int",1,None,None,None,None),("mobile","str",1,None,None,None,None)])
   output=await st.func_otp_verify(st.client_postgres_pool, obj_query["otp"], None, obj_query["mobile"], config_expiry_sec_otp=st.config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-ses")
async def func_api_public_otp_send_email_ses(request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request,"query",[("sender","str",1,None,None,None,None),("email","str",1,None,None,None,None)])
   otp=await st.func_otp_generate(st.client_postgres_pool, obj_data["email"], None)
   output=st.func_ses_send_email(st.client_ses, obj_data["sender"], [obj_data["email"]], "your otp code", str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_public_otp_send_email_resend(request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request,"query",[("sender","str",1,None,None,None,None),("email","str",1,None,None,None,None)])
   otp=await st.func_otp_generate(st.client_postgres_pool, obj_data["email"], None)
   output=await st.func_resend_send_email(st.config_resend_url, st.config_resend_key, obj_data["sender"], obj_data["email"], "your otp code", f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns")
async def func_api_public_otp_send_mobile_sns(request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request,"query",[("mobile","str",1,None,None,None,None)])
   otp=await st.func_otp_generate(st.client_postgres_pool, None, obj_data["mobile"])
   output=st.func_sns_send_mobile_message(st.client_sns, obj_data["mobile"], str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request,"body",[("mobile","str",1,None,None,None,None),("message","str",1,None,None,None,None),("template_id","str",1,None,None,None,None),("entity_id","str",1,None,None,None,None),("sender_id","str",1,None,None,None,None)])
   otp=await st.func_otp_generate(st.client_postgres_pool, None, obj_data["mobile"])
   msg=obj_data["message"].replace("{otp}",str(otp))
   output=st.func_sns_send_mobile_message_template(st.client_sns, obj_data["mobile"], msg, obj_data["template_id"], obj_data["entity_id"], obj_data["sender_id"])
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-fast2sms")
async def func_api_public_otp_send_mobile_fast2sms(request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request,"query",[("mobile","str",1,None,None,None,None)])
   otp=await st.func_otp_generate(st.client_postgres_pool, None, obj_data["mobile"])
   output=st.func_fast2sms_send_otp_mobile(st.config_fast2sms_url, st.config_fast2sms_key, obj_data["mobile"], otp)
   return {"status":1,"message":output}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("url","str",1,None,None,None,None),("email","str",1,None,None,None,None),("api_token","str",1,None,None,None,None),("start_date","str",1,None,None,None,None),("end_date","str",1,None,None,None,None)])
   import asyncio
   output_path=await asyncio.to_thread(st.func_jira_worklog_export, url=obj_body["url"], email_address=obj_body["email"], api_token=obj_body["api_token"], start_date=obj_body["start_date"], end_date=obj_body["end_date"], output_path=None)
   return await st.func_client_download_file(output_path, 1, None)

@router.get("/public/table-tag-read")
async def func_api_public_table_tag_read(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("column","str",1,st.cache_postgres_schema_columns,None,None,None),("filter_col","str",0,st.cache_postgres_schema_columns,None,None,None),("filter_val","str",0,None,None,None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)])
   val=None
   if obj_query["filter_col"] and obj_query["filter_val"]:
      val=(await st.func_postgres_serialize(st.client_postgres_pool, obj_query["table"], [{obj_query["filter_col"]:obj_query["filter_val"]}]))[0][obj_query["filter_col"]]
   output=await st.func_table_tag_read(st.client_postgres_pool, obj_query["table"], obj_query["column"], obj_query["filter_col"], val, obj_query["limit"], obj_query["page"])
   return {"status":1,"message":output}
