#router
from fastapi import APIRouter
router=APIRouter()

#import
from config import *
from function import *
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#index
@router.get("/")
async def func_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"} if not config_index_html else await func_html_serve(config_index_html)

@router.get("/health")
async def func_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"}

@router.get("/openapi.json")
async def func_api_openapi_json(request:Request):
   return request.app.state.func_openapi_spec_generate(request.app.routes, request.app.state)

@router.get("/info")
async def func_api_index(request:Request):
   st=request.app.state
   output=st.func_repo_info(request.app.routes,st.cache_postgres_schema,st.config_postgres,st.config_table,st.config_api)
   return {"status":1,"message":output}

@router.get("/page-{name}")
async def func_api_page_serve(request:Request,name:str):
   return await func_html_serve(name)

@router.websocket("/websocket")
async def func_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await func_postgres_create(websocket.app.state.client_postgres_pool,func_postgres_obj_serialize,"test",[{"title":message}],"buffer",0,3)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("username","str",1,None,None),("password","str",1,None,None)])
   user=await func_auth_signup_username_password(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username"],obj_body["password"],config_is_signup,config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("username_bigint","int",1,None,None),("password_bigint","int",1,None,None)])
   user=await func_auth_signup_username_password_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username_bigint"],obj_body["password_bigint"],config_is_signup,config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_auth_login_password_username(request:Request):
   obj_body=await func_request_param_read(request,"body",[["type","int",1,None,None],["password","str",1,None,None],["username","str",1,None,None]])
   user=await func_auth_login_password_username(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["username"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username-bigint")
async def func_api_auth_login_password_username_bigint(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("password_bigint","int",1,None,None),("username_bigint","int",1,None,None)])
   user=await func_auth_login_password_username_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password_bigint"],obj_body["username_bigint"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-email")
async def func_api_auth_login_password_email(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("password","str",1,None,None),("email","str",1,None,None)])
   user=await func_auth_login_password_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["email"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-mobile")
async def func_api_auth_login_password_mobile(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("password","str",1,None,None),("mobile","str",1,None,None)])
   user=await func_auth_login_password_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["mobile"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-email")
async def func_api_auth_login_otp_email(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("email","str",1,None,None),("otp","int",1,None,None)])
   await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],obj_body["email"],None,config_expiry_sec_otp)
   user=await func_auth_login_otp_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["email"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-mobile")
async def func_api_auth_login_otp_mobile(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("mobile","str",1,None,None),("otp","int",1,None,None)])
   await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],None,obj_body["mobile"],config_expiry_sec_otp)
   user=await func_auth_login_otp_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["mobile"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None),("google_token","str",1,None,None)])
   user=await func_auth_login_google(request.app.state.client_postgres_pool,config_google_login_client_id,obj_body["type"],obj_body["google_token"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

#my
@router.get("/my/profile")
async def func_api_my_profile(request:Request):
   st=request.app.state
   profile=await func_my_profile_read(st.client_postgres_pool,request.state.user["id"],config_sql)
   token=await func_token_encode(profile,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":profile|token}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(request:Request):
   user=await func_user_single_read(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(request:Request):
   obj_query=await func_request_param_read(request,"query",[("days","int",1,None,None)])
   obj_list=await func_api_usage_read(request.app.state.client_postgres_pool,obj_query["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["soft","hard"],None)])
   output=await func_account_delete(obj_query["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":output}

@router.get("/my/message-received")
async def func_api_my_message_received(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["all","unread","read"],None),("order","str",0,None,"id desc"),("limit","int",0,None,100),("page","int",0,None,1)])
   obj_list=await func_message_received(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["mode"],obj_query["order"],obj_query["limit"],obj_query["page"],request.app.state.func_postgres_ids_update)
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["all","unread","read"],None),("order","str",0,None,"id desc"),("limit","int",0,None,100),("page","int",0,None,1)])
   obj_list=await func_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["mode"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(request:Request):
   obj_query=await func_request_param_read(request,"query",[("user_id","int",1,None,None),("order","str",0,None,"id desc"),("limit","int",0,None,100),("page","int",0,None,1)])
   obj_list=await func_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   asyncio.create_task(func_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def func_api_my_message_delete_single(request:Request):
   obj_query=await func_request_param_read(request,"query",[("id","int",1,None,None)])
   output=await func_message_delete_single(request.app.state.client_postgres_pool,obj_query["id"],request.state.user["id"])
   return {"status":1,"message":output}

@router.delete("/my/message-delete-bulk")
async def func_api_my_message_delete_bulk(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["sent","received","all"],None)])
   output=await func_message_delete_bulk(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["mode"])
   return {"status":1,"message":output}

@router.get("/my/parent-read")
async def func_api_my_parent_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("parent_table","str",1,st.cache_postgres_schema_tables,None),("parent_column","str",1,st.cache_postgres_schema_columns,None),("order","str",0,None,"id desc"),("limit","int",0,None,100),("page","int",0,None,1)])
   output=await func_postgres_parent_read(st.client_postgres_pool,obj_query["table"],obj_query["parent_column"],obj_query["parent_table"],request.state.user["id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":output}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(request:Request):
   st=request.app.state
   obj_body=await func_request_param_read(request,"body",[("table","str",1,st.cache_postgres_schema_tables,None),("ids","str",1,None,None)])
   output=await func_postgres_ids_delete(st.client_postgres_pool,obj_body["table"],obj_body["ids"],request.state.user.get("id",0),config_table_system,config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def func_api_my_object_create(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("mode","str",0,["now","buffer"],"now"),("is_serialize","int",0,[0,1],0),("queue","str",0,["redis","celery","rabbitmq","kafka"],None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_obj_create_logic("my",obj_query,obj_body,request.state.user.get("id"),st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_create,st.config_postgres_batch_limit)}

@router.put("/my/object-update")
async def func_api_my_object_update(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("is_serialize","int",0,[0,1],0),("otp","int",0,None,None),("queue","str",0,["redis","celery","rabbitmq","kafka"],None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_obj_update_logic("my",obj_query,obj_body,request.state.user.get("id"),st.config_column_blocked,st.config_column_single_update,st.client_postgres_pool,st.func_postgres_obj_serialize,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_update,st.func_otp_verify,st.config_expiry_sec_otp,0,st.config_postgres_batch_limit)}

@router.get("/my/object-read")
async def func_api_my_object_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("limit","int",0,None,100),("page","int",0,None,1),("order","str",0,None,"id desc"),("column","str",0,None,"*"),("creator_key","str",0,None,None),("action_key","str",0,None,None)])
   obj_query["created_by_id"]=f"""=,{request.state.user["id"]}"""
   obj_list=await func_postgres_read(st.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(request:Request):
   obj_query=await func_request_param_read(request,"query",[("database","str",1,None,None),("table","str",1,None,None)])
   obj_body=await func_request_param_read(request,"body",[])
   obj_list=obj_body.get("obj_list", [obj_body])
   output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_query["database"],obj_query["table"],obj_list)
   return {"status":1,"message":output}

#public
@router.get("/public/converter-number")
async def func_api_public_converter_number(request:Request):
   obj_query=await func_request_param_read(request,"query",[("datatype","str",1,["smallint","int","bigint"],None),("mode","str",1,["encode","decode"],None),("x","str",1,None,None)])
   output=func_converter_number(obj_query["datatype"],obj_query["mode"],obj_query["x"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_public_object_create(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("mode","str",0,["now","buffer"],"now"),("is_serialize","int",0,[0,1],0),("queue","str",0,["redis","celery","rabbitmq","kafka"],None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_obj_create_logic("public",obj_query,obj_body,request.state.user.get("id") if getattr(request.state,"user",None) else None,st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_create,st.config_postgres_batch_limit)}

@router.get("/public/object-read")
async def func_api_public_object_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("limit","int",0,None,100),("page","int",0,None,1),("order","str",0,None,"id desc"),("column","str",0,None,"*"),("creator_key","str",0,None,None),("action_key","str",0,None,None)])
   if config_table_read_public and obj_query["table"] not in config_table_read_public:
      raise Exception(f"table not allowed: {obj_query['table']}, allowed: {config_table_read_public}")
   obj_list=await func_postgres_read(st.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify-email")
async def func_api_public_otp_verify_email(request:Request):
   obj_query=await func_request_param_read(request,"query",[("otp","int",1,None,None),("email","str",1,None,None)])
   output=await func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],obj_query["email"],None,config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.get("/public/otp-verify-mobile")
async def func_api_public_otp_verify_mobile(request:Request):
   obj_query=await func_request_param_read(request,"query",[("otp","int",1,None,None),("mobile","str",1,None,None)])
   output=await func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],None,obj_query["mobile"],config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-ses")
async def func_api_public_otp_send_email_ses(request:Request):
   st=request.app.state
   obj_data=await func_request_param_read(request,"query",[("sender","str",1,None,None),("email","str",1,None,None)])
   otp=await func_otp_generate(st.client_postgres_pool,obj_data["email"],None)
   output=func_ses_send_email(st.client_ses,obj_data["sender"],[obj_data["email"]],"your otp code",str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_public_otp_send_email_resend(request:Request):
   st=request.app.state
   obj_data=await func_request_param_read(request,"query",[("sender","str",1,None,None),("email","str",1,None,None)])
   otp=await func_otp_generate(st.client_postgres_pool,obj_data["email"],None)
   output=await func_resend_send_email(config_resend_url,config_resend_key,obj_data["sender"],[obj_data["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns")
async def func_api_public_otp_send_mobile_sns(request:Request):
   st=request.app.state
   obj_data=await func_request_param_read(request,"query",[("mobile","str",1,None,None)])
   otp=await func_otp_generate(st.client_postgres_pool,None,obj_data["mobile"])
   output=func_sns_send_mobile_message(st.client_sns,obj_data["mobile"],str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(request:Request):
   st=request.app.state
   obj_data=await func_request_param_read(request,"body",[("mobile","str",1,None,None),("message","str",1,None,None),("template_id","str",1,None,None),("entity_id","str",1,None,None),("sender_id","str",1,None,None)])
   otp=await func_otp_generate(st.client_postgres_pool,None,obj_data["mobile"])
   msg=obj_data["message"].replace("{otp}",str(otp))
   output=func_sns_send_mobile_message_template(st.client_sns,obj_data["mobile"],msg,obj_data["template_id"],obj_data["entity_id"],obj_data["sender_id"])
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-fast2sms")
async def func_api_public_otp_send_mobile_fast2sms(request:Request):
   st=request.app.state
   obj_data=await func_request_param_read(request,"query",[("mobile","str",1,None,None)])
   otp=await func_otp_generate(st.client_postgres_pool,None,obj_data["mobile"])
   output=func_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,obj_data["mobile"],otp)
   return {"status":1,"message":output}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(request:Request):
   obj_body=await func_request_param_read(request,"body",[("jira_url","str",1,None,None),("email","str",1,None,None),("api_token","str",1,None,None),("start_date","str",0,None,None),("end_date","str",0,None,None)])
   import asyncio; output_path=await asyncio.to_thread(func_jira_worklog_export,obj_body["jira_url"],obj_body["email"],obj_body["api_token"],obj_body["start_date"],obj_body["end_date"],None)
   return await func_client_download_file(output_path,1,None)

@router.get("/public/table-tag-read")
async def func_api_public_table_tag_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("column","str",1,st.cache_postgres_schema_columns,None),("filter_col","str",0,st.cache_postgres_schema_columns,None),("filter_val","str",0,None,None),("limit","int",0,None,100),("page","int",0,None,1)])
   val=None
   if obj_query["filter_col"] and obj_query["filter_val"]:val=(await func_postgres_obj_serialize(st.client_postgres_pool,obj_query["table"],[{obj_query["filter_col"]:obj_query["filter_val"]}]))[0][obj_query["filter_col"]]
   output=await func_table_tag_read(st.client_postgres_pool,obj_query["table"],obj_query["column"],obj_query["filter_col"],val,obj_query["limit"],obj_query["page"])
   return {"status":1,"message":output}

#private
@router.post("/private/s3-upload-file")
async def func_api_private_s3_upload_file(request:Request):
   obj_form=await func_request_param_read(request,"form",[("bucket","str",1,None,None),("file","file",1,[],None)])
   st,output=request.app.state,{}
   if len(obj_form["file"])>config_s3_upload_limit_count:raise Exception(f"maximum {config_s3_upload_limit_count} files allowed")
   for item in obj_form["file"]:
      output[item.filename]=await func_s3_upload(st.client_s3,obj_form["bucket"],item,config_s3_limit_kb)
   return {"status":1,"message":output}

@router.post("/private/s3-upload-presigned")
async def func_api_private_s3_upload_presigned(request:Request):
   obj_query=await func_request_param_read(request,"query",[("bucket","str",1,None,None),("count","int",0,None,1)])
   if obj_query["count"]>config_s3_upload_limit_count:raise Exception(f"maximum {config_s3_upload_limit_count} allowed")
   st,output=request.app.state,[]
   for _ in range(obj_query["count"]):
      output.append(func_s3_upload_presigned(st.client_s3,config_s3_region_name,obj_query["bucket"],config_s3_limit_kb,config_s3_presigned_expire_sec))
   return {"status":1,"message":output}

#admin
@router.get("/admin/sync")
async def func_api_admin_sync(request:Request):
   if request.app.state.client_postgres_pool: await func_postgres_init(request.app.state.client_postgres_pool, config_postgres)
   await func_postgres_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,None,None,"flush")
   request.app.state.cache_postgres_schema=await func_postgres_schema_read(request.app.state.client_postgres_pool) if request.app.state.client_postgres_pool else {}
   request.app.state.cache_postgres_schema_tables=list(request.app.state.cache_postgres_schema.keys())
   request.app.state.cache_postgres_schema_columns=sorted(list(set(col for table in request.app.state.cache_postgres_schema.values() for col in table.keys())))
   request.app.state.cache_users_role=await func_sql_map_column(request.app.state.client_postgres_pool,config_sql.get("cache_users_role")) if request.app.state.client_postgres_pool else {}
   request.app.state.cache_users_is_active=await func_sql_map_column(request.app.state.client_postgres_pool,config_sql.get("cache_users_is_active")) if request.app.state.client_postgres_pool else {}
   await func_postgres_clean(request.app.state.client_postgres_pool,config_table)
   return {"status":1,"message":"done"}
   
@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(request:Request):
   obj_body=await func_request_param_read(request,"body",[("mode","str",1,["read","write"],None),("query","str",1,None,None)])
   output=await func_postgres_runner(request.app.state.client_postgres_pool,obj_body["mode"],obj_body["query"])
   return {"status":1,"message":output}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(request:Request):
   obj_body=await func_request_param_read(request,"body",[("query","str",1,None,None)])
   stream=func_postgres_stream(request.app.state.client_postgres_pool,obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,["create","update","delete"],None),("table","str",1,st.cache_postgres_schema_tables,None),("file","file",1,[],None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      if obj_form["mode"]=="create":await func_postgres_create(st.client_postgres_pool,func_postgres_obj_serialize,obj_form["table"],obj_list,"now",1,None)
      elif obj_form["mode"]=="update":await func_postgres_update(st.client_postgres_pool,func_postgres_obj_serialize,obj_form["table"],obj_list,1,None)
      elif obj_form["mode"]=="delete":await func_postgres_ids_delete(st.client_postgres_pool,obj_form["table"],",".join(str(obj["id"]) for obj in obj_list),None)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("mode","str",0,["now","buffer"],"now"),("is_serialize","int",0,[0,1],0),("queue","str",0,["redis","celery","rabbitmq","kafka"],None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_obj_create_logic("admin",obj_query,obj_body,request.state.user.get("id"),st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_create,st.config_postgres_batch_limit)}

@router.put("/admin/object-update")
async def func_api_admin_object_update(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("is_serialize","int",0,[0,1],0),("otp","int",0,None,None),("queue","str",0,["redis","celery","rabbitmq","kafka"],None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_obj_update_logic("admin",obj_query,obj_body,request.state.user.get("id"),st.config_column_blocked,st.config_column_single_update,st.client_postgres_pool,st.func_postgres_obj_serialize,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_update,st.func_otp_verify,st.config_expiry_sec_otp,st.config_is_otp_users_update_admin,st.config_postgres_batch_limit)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None),("limit","int",0,None,100),("page","int",0,None,1),("order","str",0,None,"id desc"),("column","str",0,None,"*"),("creator_key","str",0,None,None),("action_key","str",0,None,None)])
   obj_list=await func_postgres_read(st.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(request:Request):
   st=request.app.state
   obj_body=await func_request_param_read(request,"body",[("table","str",1,st.cache_postgres_schema_tables,None),("ids","str",1,None,None)])
   output=await func_postgres_ids_delete(st.client_postgres_pool,obj_body["table"],obj_body["ids"],None,config_table_system,config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/admin/redis-import-create")
async def func_api_admin_redis_import_create(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("table","str",1,st.cache_postgres_schema_tables,None),("file","file",1,[],None),("expiry_sec","int",0,None,None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      key_list=[f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
      await func_redis_object_create(st.client_redis,key_list,obj_list,obj_form["expiry_sec"])
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/redis-import-delete")
async def func_api_admin_redis_import_delete(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("table","str",1,st.cache_postgres_schema_tables,None),("file","file",1,[],None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      key_list=[f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
      await func_redis_object_delete(st.client_redis,key_list)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,["create","delete"],None),("database","str",1,None,None),("table","str",1,st.cache_postgres_schema_tables,None),("file","file",1,[],None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      if obj_form["mode"]=="create":await func_mongodb_object_create(st.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
      elif obj_form["mode"]=="delete":await func_mongodb_object_delete(st.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/s3-bucket-ops")
async def func_api_admin_s3_bucket_ops(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["create","public","empty","delete"],None),("bucket","str",1,None,None)])
   st=request.app.state
   if obj_query["mode"]=="create":
      output=await func_s3_bucket_create(st.client_s3,config_s3_region_name,obj_query["bucket"])
   elif obj_query["mode"]=="public":
      output=await func_s3_bucket_public(st.client_s3,obj_query["bucket"])
   elif obj_query["mode"]=="empty":
      output=func_s3_bucket_empty(st.client_s3_resource,obj_query["bucket"])
   elif obj_query["mode"]=="delete":
      output=await func_s3_bucket_delete(st.client_s3,obj_query["bucket"])
   return {"status":1,"message":output}

@router.post("/admin/s3-url-delete")
async def func_api_admin_s3_url_delete(request:Request):
   st=request.app.state
   obj_body=await func_request_param_read(request,"body",[("url","list",1,[],None)])
   output=func_s3_url_delete(st.client_s3_resource,obj_body["url"])
   return {"status":1,"message":output}

