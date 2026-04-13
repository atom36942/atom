#router
from fastapi import APIRouter
router=APIRouter()

#import
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#public
@router.get("/public/converter-number")
async def func_api_public_converter_number(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("datatype","str",1,["smallint","int","bigint"],None,None,None,None),("mode","str",1,["encode","decode"],None,None,None,None),("x","str",1,None,None,None,None,None)], strict=0)
   output=st.func_converter_number(type=obj_query["datatype"], mode=obj_query["mode"], x=obj_query["x"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_public_object_create(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("mode","str",0,["now","buffer"],"now",None,None,None),("is_serialize","int",0,[0,1],0,None,None,None),("queue","str",0,None,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_create(api_role="public", obj_query=obj_query, obj_body=obj_body, user_id=request.state.user.get("id") if getattr(request.state,"user",None) else None, config_table_create_my=st.config_table_create_my, config_table_create_public=st.config_table_create_public, config_column_blocked=st.config_column_blocked, client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, config_table=st.config_table, func_orchestrator_producer=st.func_orchestrator_producer, producer_obj={"config_channel_allowed":st.config_channel_allowed, "client_celery_producer":st.client_celery_producer, "client_kafka_producer":st.client_kafka_producer, "client_rabbitmq_producer":st.client_rabbitmq_producer, "client_redis_producer":st.client_redis_producer}, func_postgres_create=st.func_postgres_create, config_limit_obj_list=st.config_limit_obj_list, cache_postgres_buffer=st.cache_postgres_buffer)}

@router.get("/public/object-read")
async def func_api_public_object_read(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("limit","int",0,None,100,None,None,None),("page","int",0,None,1,None,None,None),("order","str",0,None,"id desc",None,None,None),("column","str",0,None,"*",None,None,None),("creator_key","str",0,None,None,None,None,None),("action_key","str",0,None,None,None,None,None)], strict=0)
   if st.config_table_read_public and obj_query["table"] not in st.config_table_read_public:
      raise Exception(f"table not allowed: {obj_query['table']}, allowed: {st.config_table_read_public}")
   obj_list=await st.func_postgres_read(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, table=obj_query["table"], filter_obj=obj_query, limit=obj_query["limit"], page=obj_query["page"], order=obj_query["order"], column=obj_query["column"], creator_key=obj_query["creator_key"], action_key=obj_query["action_key"])
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify-email")
async def func_api_public_otp_verify_email(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("otp","int",1,None,None,None,None,None),("email","str",1,None,None,None,None,None)], strict=0)
   output=await st.func_otp_verify(client_postgres_pool=st.client_postgres_pool, otp=obj_query["otp"], email=obj_query["email"], mobile=None, config_expiry_sec_otp=st.config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.get("/public/otp-verify-mobile")
async def func_api_public_otp_verify_mobile(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("otp","int",1,None,None,None,None,None),("mobile","str",1,None,None,None,None,None)], strict=0)
   output=await st.func_otp_verify(client_postgres_pool=st.client_postgres_pool, otp=obj_query["otp"], mobile=obj_query["mobile"], email=None, config_expiry_sec_otp=st.config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-ses")
async def func_api_public_otp_send_email_ses(*, request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request=request, mode="query", config=[("sender","str",1,None,None,None,None,None),("email","str",1,None,None,None,None,None)], strict=0)
   otp=await st.func_otp_generate(client_postgres_pool=st.client_postgres_pool, email=obj_data["email"], mobile=None)
   output=st.func_ses_send_email(client_ses=st.client_ses, from_email=obj_data["sender"], to_emails=[obj_data["email"]], subject="your otp code", body=str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_public_otp_send_email_resend(*, request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request=request, mode="query", config=[("sender","str",1,None,None,None,None,None),("email","str",1,None,None,None,None,None)], strict=0)
   otp=await st.func_otp_generate(client_postgres_pool=st.client_postgres_pool, email=obj_data["email"], mobile=None)
   output=await st.func_resend_send_email(config_resend_url=st.config_resend_url, config_resend_key=st.config_resend_key, from_email=obj_data["sender"], to_email=obj_data["email"], email_subject="your otp code", email_content=f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns")
async def func_api_public_otp_send_mobile_sns(*, request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request=request, mode="query", config=[("mobile","str",1,None,None,None,None,None)], strict=0)
   otp=await st.func_otp_generate(client_postgres_pool=st.client_postgres_pool, mobile=obj_data["mobile"], email=None)
   output=st.func_sns_send_mobile_message(client_sns=st.client_sns, mobile=obj_data["mobile"], message=str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(*, request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request=request, mode="body", config=[("mobile","str",1,None,None,None,None,None),("message","str",1,None,None,None,None,None),("template_id","str",1,None,None,None,None,None),("entity_id","str",1,None,None,None,None,None),("sender_id","str",1,None,None,None,None,None)], strict=0)
   otp=await st.func_otp_generate(client_postgres_pool=st.client_postgres_pool, mobile=obj_data["mobile"], email=None)
   msg=obj_data["message"].replace("{otp}",str(otp))
   output=st.func_sns_send_mobile_message_template(client_sns=st.client_sns, mobile=obj_data["mobile"], message=msg, template_id=obj_data["template_id"], entity_id=obj_data["entity_id"], sender_id=obj_data["sender_id"])
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-fast2sms")
async def func_api_public_otp_send_mobile_fast2sms(*, request:Request):
   st=request.app.state
   obj_data=await st.func_request_param_read(request=request, mode="query", config=[("mobile","str",1,None,None,None,None,None)], strict=0)
   otp=await st.func_otp_generate(client_postgres_pool=st.client_postgres_pool, mobile=obj_data["mobile"], email=None)
   output=st.func_fast2sms_send_otp_mobile(config_fast2sms_url=st.config_fast2sms_url, config_fast2sms_key=st.config_fast2sms_key, mobile=obj_data["mobile"], otp_code=str(otp))
   return {"status":1,"message":output}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("url","str",1,None,None,None,None,None),("email","str",1,None,None,None,None,None),("api_token","str",1,None,None,None,None,None),("start_date","str",1,None,None,None,None,None),("end_date","str",1,None,None,None,None,None)], strict=0)
   import asyncio, uuid
   output_path=f"tmp/{uuid.uuid4().hex}.csv"
   await asyncio.to_thread(st.func_jira_worklog_export, url=obj_body["url"], email=obj_body["email"], api_token=obj_body["api_token"], start_date=obj_body["start_date"], end_date=obj_body["end_date"], output_path=output_path)
   return await st.func_client_download_file(file_path=output_path, is_delete_after=1, chunk_size=1048576)

@router.get("/public/table-tag-read")
async def func_api_public_table_tag_read(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("column","str",1,st.cache_postgres_schema_columns,None,None,None,None),("limit","int",0,None,100,None,None,None),("page","int",0,None,1,None,None,None),("filter_column","str",0,st.cache_postgres_schema_columns,None,None,None,None),("filter_value","str",0,None,None,None,None,None)], strict=0)
   val=None
   if obj_query["filter_column"] and obj_query["filter_value"]:
      val=(await st.func_postgres_serialize(client_postgres_pool=st.client_postgres_pool, cache_postgres_schema=st.cache_postgres_schema, table=obj_query["table"], obj_list=[{obj_query["filter_column"]:obj_query["filter_value"]}], is_base=0))[0][obj_query["filter_column"]]
   output=await st.func_table_tag_read(client_postgres_pool=st.client_postgres_pool, table=obj_query["table"], column=obj_query["column"], limit=obj_query["limit"], page=obj_query["page"], filter_column=obj_query["filter_column"], filter_value=val)
   return {"status":1,"message":output}
