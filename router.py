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
   st=request.app.state
   output=st.func_info_read(request.app.routes,st.cache_postgres_schema,st.config_postgres,st.config_table,st.config_api)
   return {"status":1,"message":output}

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("username","str",1,None,None),("password","str",1,None,None)])
   user=await func_auth_signup_username_password(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username"],obj_body["password"],config_is_signup,config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("username_bigint","int",1,None,None),("password_bigint","int",1,None,None)])
   user=await func_auth_signup_username_password_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username_bigint"],obj_body["password_bigint"],config_is_signup,config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_auth_login_password_username(request:Request):
   obj_body=await func_request_param_read("body",request,[["type","int",1,None,None],["password","str",1,None,None],["username","str",1,None,None]])
   user=await func_auth_login_password_username(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["username"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username-bigint")
async def func_api_auth_login_password_username_bigint(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("password_bigint","int",1,None,None),("username_bigint","int",1,None,None)])
   user=await func_auth_login_password_username_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password_bigint"],obj_body["username_bigint"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-email")
async def func_api_auth_login_password_email(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("password","str",1,None,None),("email","str",1,None,None)])
   user=await func_auth_login_password_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["email"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-mobile")
async def func_api_auth_login_password_mobile(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("password","str",1,None,None),("mobile","str",1,None,None)])
   user=await func_auth_login_password_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["mobile"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-email")
async def func_api_auth_login_otp_email(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("email","str",1,None,None),("otp","int",1,None,None)])
   await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],obj_body["email"],None,config_expiry_sec_otp)
   user=await func_auth_login_otp_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["email"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-mobile")
async def func_api_auth_login_otp_mobile(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("mobile","str",1,None,None),("otp","int",1,None,None)])
   await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],None,obj_body["mobile"],config_expiry_sec_otp)
   user=await func_auth_login_otp_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["mobile"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(request:Request):
   obj_body=await func_request_param_read("body",request,[("type","int",1,None,None),("google_token","str",1,None,None)])
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
   obj_query=await func_request_param_read("query",request,[("days","int",0,7,None)])
   obj_list=await func_api_usage_read(request.app.state.client_postgres_pool,obj_query["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(request:Request):
   obj_query=await func_request_param_read("query",request,[("mode","str",1,None,["soft","hard"])])
   output=await func_account_delete(obj_query["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":output}

@router.get("/my/message-received")
async def func_api_my_message_received(request:Request):
   obj_query=await func_request_param_read("query",request,[("is_unread","int",0,None,None),("order","str",0,None,None),("limit","int",0,None,None),("page","int",0,None,None)])
   obj_list=await func_message_received(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["is_unread"],obj_query["order"],obj_query["limit"],obj_query["page"],request.app.state.func_postgres_ids_update)
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(request:Request):
   obj_query=await func_request_param_read("query",request,[("is_unread","int",0,None,None),("order","str",0,None,None),("limit","int",0,None,None),("page","int",0,None,None)])
   obj_list=await func_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["is_unread"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(request:Request):
   obj_query=await func_request_param_read("query",request,[("user_id","int",1,None,None),("order","str",0,None,None),("limit","int",0,None,None),("page","int",0,None,None)])
   obj_list=await func_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   asyncio.create_task(func_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete")
async def func_api_my_message_delete(request:Request):
   obj_query=await func_request_param_read("query",request,[("mode","str",1,None,["single","sent","received","all"]),("id","int",0,None,None)])
   output=await func_message_delete(obj_query["mode"],request.app.state.client_postgres_pool,request.state.user["id"],obj_query["id"])
   return {"status":1,"message":output}

@router.get("/my/parent-read")
async def func_api_my_parent_read(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("parent_table","str",1,None,None),("parent_column","str",1,None,None),("order","str",0,None,None),("limit","int",0,None,None),("page","int",0,None,None)])
   output=await func_postgres_parent_read(request.app.state.client_postgres_pool,obj_query["table"],obj_query["parent_column"],obj_query["parent_table"],request.state.user["id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":output}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(request:Request):
   obj_body=await func_request_param_read("body",request,[("table","str",1,None,None),("ids","str",1,None,None)])
   output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],request.state.user["id"],config_table_system,config_limit_ids_delete)
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def func_api_my_object_create(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("is_serialize","int",0,0,None),("mode","str",0,"now",None),("queue","str",0,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   st=request.app.state
   return {"status":1,"message":await func_obj_create_logic(obj_query,obj_body,"my",request.state.user.get("id"),st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_obj_create)}

@router.put("/my/object-update")
async def func_api_my_object_update(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("is_serialize","int",0,0,None),("otp","int",0,None,None),("queue","str",0,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   st=request.app.state
   return {"status":1,"message":await func_obj_update_logic(obj_query,obj_body,"my",request.state.user.get("id"),st.config_column_blocked,st.config_column_single_update,st.client_postgres_pool,st.func_postgres_obj_serialize,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_obj_update,st.func_otp_verify,st.config_expiry_sec_otp)}

@router.get("/my/object-read")
async def func_api_my_object_read(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None)])
   obj_query["created_by_id"]=f"=,{request.state.user['id']}"
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(request:Request):
   obj_query=await func_request_param_read("query",request,[("database","str",1,None,None),("table","str",1,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
   output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_query["database"],obj_query["table"],obj_list)
   return {"status":1,"message":output}

#public
@router.get("/public/converter-number")
async def func_api_public_converter_number(request:Request):
   obj_query=await func_request_param_read("query",request,[("datatype","str",1,None,None),("mode","str",1,None,None),("x","str",1,None,None)])
   output=func_converter_number(obj_query["datatype"],obj_query["mode"],obj_query["x"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_public_object_create(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("is_serialize","int",0,0,None),("mode","str",0,"now",None),("queue","str",0,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   st=request.app.state
   return {"status":1,"message":await func_obj_create_logic(obj_query,obj_body,"public",request.state.user.get("id") if getattr(request.state,"user",None) else None,st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_obj_create)}

@router.get("/public/object-read")
async def func_api_public_object_read(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None)])
   obj_list=await func_postgres_obj_read_public(request.app.state.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query,config_table_read_public)
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify")
async def func_api_public_otp_verify(request:Request):
   obj_query=await func_request_param_read("query",request,[("otp","int",1,None,None),("email","str",0,None,None),("mobile","str",0,None,None)])
   output=await func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],obj_query["email"],obj_query["mobile"],config_expiry_sec_otp)
   return {"status":1,"message":output}

@router.get("/public/otp-send-email-ses")
async def func_api_public_otp_send_email_ses(request:Request):
   obj_query=await func_request_param_read("query",request,[("sender","str",1,None,None),("email","str",1,None,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=func_ses_send_email(request.app.state.client_ses,obj_query["sender"],[obj_query["email"]],"your otp code",str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_public_otp_send_email_resend(request:Request):
   obj_query=await func_request_param_read("query",request,[("sender","str",1,None,None),("email","str",1,None,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_resend_send_email(config_resend_url,config_resend_key,obj_query["sender"],[obj_query["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-sns")
async def func_api_public_otp_send_mobile_sns(request:Request):
   obj_query=await func_request_param_read("query",request,[("mobile","str",1,None,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=func_sns_send_mobile_message(request.app.state.client_sns,obj_query["mobile"],str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_public_otp_send_mobile_sns_template(request:Request):
   obj_body=await func_request_param_read("body",request,[("mobile","str",1,None,None),("message","str",1,None,None),("template_id","str",1,None,None),("entity_id","str",1,None,None),("sender_id","str",1,None,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_body["mobile"])
   output=func_sns_send_mobile_message_template(request.app.state.client_sns,obj_body["mobile"],message,obj_body["template_id"],obj_body["entity_id"],obj_body["sender_id"])
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-fast2sms")
async def func_api_public_otp_send_mobile_fast2sms(request:Request):
   obj_query=await func_request_param_read("query",request,[("mobile","str",1,None,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=func_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,obj_query["mobile"],otp)
   return {"status":1,"message":output}

@router.post("/public/object-create-gsheet")
async def func_api_public_object_create_gsheet(request:Request):
   obj_query=await func_request_param_read("query",request,[("url","str",1,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
   output=func_gsheet_object_create(request.app.state.client_gsheet,obj_query["url"],obj_list)
   return {"status":1,"message":output}

@router.get("/public/object-read-gsheet")
async def func_api_public_object_read_gsheet(request:Request):
   obj_query=await func_request_param_read("query",request,[("url","str",1,None,None)])
   obj_list=await func_gsheet_object_read(obj_query["url"])
   return {"status":1,"message":obj_list}

@router.post("/public/jira-worklog-export")
async def func_api_public_jira_worklog_export(request:Request):
   obj_body=await func_request_param_read("body",request,[("jira_base_url","str",1,None,None),("jira_email","str",1,None,None),("jira_token","str",1,None,None),("start_date","str",0,None,None),("end_date","str",0,None,None)])
   output_path=func_jira_worklog_export(obj_body["jira_base_url"],obj_body["jira_email"],obj_body["jira_token"],obj_body["start_date"],obj_body["end_date"],None)
   return await func_client_download_file(output_path)

@router.get("/public/table-tag-read")
async def func_api_public_table_tag_read(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("column","str",1,None,None),("filter_col","str",0,None,None),("filter_val","str",0,None,None),("limit","int",0,None,None),("page","int",0,None,None)])
   val=None
   if obj_query["filter_col"] and obj_query["filter_val"]:val=(await func_postgres_obj_serialize(request.app.state.client_postgres_pool,obj_query["table"],[{obj_query["filter_col"]:obj_query["filter_val"]}]))[0][obj_query["filter_col"]]
   output=await func_table_tag_read(request.app.state.client_postgres_pool,obj_query["table"],obj_query["column"],obj_query["filter_col"],val,obj_query["limit"],obj_query["page"])
   return {"status":1,"message":output}

#private
@router.post("/private/s3-upload-file")
async def func_api_private_s3_upload_file(request:Request):
   obj_form=await func_request_param_read("form",request,[("bucket","str",1,None,None),("file","file",1,[],None),("key","list",0,[],None)])
   output={}
   for index,item in enumerate(obj_form["file"]):
      k=obj_form["key"][index] if index<len(obj_form["key"]) else None
      output[item.filename]=await func_s3_upload(request.app.state.client_s3,config_s3_region_name,obj_form["bucket"],item,k,config_s3_limit_kb)
   return {"status":1,"message":output}

@router.get("/private/s3-upload-presigned")
async def func_api_private_s3_upload_presigned(request:Request):
   obj_query=await func_request_param_read("query",request,[("bucket","str",1,None,None),("key","str",0,None,None)])
   output=func_s3_upload_presigned(request.app.state.client_s3,config_s3_region_name,obj_query["bucket"],obj_query["key"],config_s3_limit_kb,config_s3_presigned_expire_sec)
   return {"status":1,"message":output}

#admin
@router.get("/admin/postgres-init")
async def func_api_admin_postgres_init(request:Request):
   output=await func_postgres_init(request.app.state.client_postgres_pool,config_postgres)
   return {"status":1,"message":output}

@router.get("/admin/sync")
async def func_api_admin_sync(request:Request):
   await func_postgres_obj_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,"flush")
   request.app.state.cache_postgres_schema=await func_postgres_schema_read(request.app.state.client_postgres_pool) if request.app.state.client_postgres_pool else {}
   request.app.state.cache_users_role=await func_sql_map_column(request.app.state.client_postgres_pool,config_sql.get("cache_users_role")) if request.app.state.client_postgres_pool else {}
   request.app.state.cache_users_is_active=await func_sql_map_column(request.app.state.client_postgres_pool,config_sql.get("cache_users_is_active")) if request.app.state.client_postgres_pool else {}
   func_sync_routes_check(request.app.routes,request.app.state.config_api)
   await func_postgres_clean(request.app.state.client_postgres_pool,config_table)
   return {"status":1,"message":"done"}

@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(request:Request):
   obj_body=await func_request_param_read("body",request,[("mode","str",1,None,None),("query","str",1,None,None)])
   output=await func_postgres_runner(request.app.state.client_postgres_pool,obj_body["mode"],obj_body["query"])
   return {"status":1,"message":output}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(request:Request):
   obj_body=await func_request_param_read("body",request,[("query","str",1,None,None)])
   stream=func_postgres_stream(request.app.state.client_postgres_pool,obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(request:Request):
   obj_form=await func_request_param_read("form",request,[("mode","str",1,None,None),("table","str",1,None,None),("file","file",1,[],None)])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":output=await func_postgres_obj_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,"now",obj_form["table"],obj_list,1,None)
   elif obj_form["mode"]=="update":output=await func_postgres_obj_update(request.app.state.client_postgres_pool,func_postgres_obj_serialize,obj_form["table"],obj_list,1,None)
   elif obj_form["mode"]=="delete":output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_form["table"],",".join(str(obj["id"]) for obj in obj_list),None)
   return {"status":1,"message":output}

@router.post("/admin/redis-import")
async def func_api_admin_redis_import(request:Request):
   obj_form=await func_request_param_read("form",request,[("mode","str",1,None,None),("table","str",1,None,None),("file","file",1,[],None),("expiry_sec","int",0,None,None)])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":
      key_list=[f"{obj_form['table']}_{item['id']}" for item in obj_list]
      output=await func_redis_object_create(request.app.state.client_redis,key_list,obj_list,obj_form["expiry_sec"])
   return {"status":1,"message":output}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(request:Request):
   obj_form=await func_request_param_read("form",request,[("mode","str",1,None,None),("database","str",1,None,None),("table","str",1,None,None),("file","file",1,[],None)])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
   return {"status":1,"message":output}

@router.get("/admin/s3-bucket-ops")
async def func_api_admin_s3_bucket_ops(request:Request):
   obj_query=await func_request_param_read("query",request,[("mode","str",1,None,None),("bucket","str",1,None,None)])
   if obj_query["mode"]=="create":output=await func_s3_bucket_create(request.app.state.client_s3,config_s3_region_name,obj_query["bucket"])
   elif obj_query["mode"]=="public":output=await func_s3_bucket_public(request.app.state.client_s3,obj_query["bucket"])
   elif obj_query["mode"]=="empty":output=func_s3_bucket_empty(request.app.state.client_s3_resource,obj_query["bucket"])
   elif obj_query["mode"]=="delete":output=await func_s3_bucket_delete(request.app.state.client_s3,obj_query["bucket"])
   return {"status":1,"message":output}

@router.post("/admin/s3-url-delete")
async def func_api_admin_s3_url_delete(request:Request):
   obj_body=await func_request_param_read("body",request,[("url","list",1,[],None)])
   for item in obj_body["url"]:output=func_s3_url_delete(request.app.state.client_s3_resource,item)
   return {"status":1,"message":output}

@router.post("/admin/object-create")
async def func_api_admin_object_create(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("is_serialize","int",0,0,None),("mode","str",0,"now",None),("queue","str",0,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   st=request.app.state
   return {"status":1,"message":await func_obj_create_logic(obj_query,obj_body,"admin",request.state.user.get("id"),st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_obj_create)}

@router.put("/admin/object-update")
async def func_api_admin_object_update(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None),("is_serialize","int",0,0,None),("otp","int",0,None,None),("queue","str",0,None,None)])
   obj_body=await func_request_param_read("body",request,[])
   st=request.app.state
   return {"status":1,"message":await func_obj_update_logic(obj_query,obj_body,"admin",request.state.user.get("id"),st.config_column_blocked,st.config_column_single_update,st.client_postgres_pool,st.func_postgres_obj_serialize,st.func_producer_logic,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_name,st.func_celery_producer,st.func_kafka_producer,st.func_rabbitmq_producer,st.func_redis_producer,st.func_postgres_obj_update,st.func_otp_verify,st.config_expiry_sec_otp)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(request:Request):
   obj_query=await func_request_param_read("query",request,[("table","str",1,None,None)])
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(request:Request):
   obj_body=await func_request_param_read("body",request,[("table","str",1,None,None),("ids","str",1,None,None)])
   output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],None,config_table_system,config_limit_ids_delete)
   return {"status":1,"message":output}

#zzz
@router.get("/test")
async def func_api_test(request:Request):
   return {"status":1,"message":"welcome to test"}

@router.get("/page/{name}")
async def func_api_page_serve(name):
   return await func_html_serve(name)

@router.websocket("/websocket")
async def func_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await func_postgres_obj_create(websocket.app.state.client_postgres_pool,func_postgres_obj_serialize,"buffer","test",[{"title":message}],0,3)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")
