#import
from function import *
from config import *

#globals
postgres_client=None
postgres_client_asyncpg=None
postgres_client_read=None
postgres_schema={}
postgres_column_datatype={}
users_api_access={}
users_is_active={}
redis_client=None
mongodb_client=None
s3_client=None
s3_resource=None
sns_client=None
ses_client=None
rabbitmq_client=None
rabbitmq_channel=None
lavinmq_client=None
lavinmq_channel=None
kafka_producer_client=None
gsheet_client=None
openai_client=None

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #postgres client
      global postgres_client
      postgres_client=await function_postgres_client_read(postgres_url)
      #postgres client asyncpg
      global postgres_client_asyncpg
      postgres_client_asyncpg=await postgres_client_asyncpg_read(postgres_url)
      #postgres client read replica
      global postgres_client_read
      if postgres_url_read:postgres_client_read=await function_postgres_client_read(postgres_url_read)
      #postgres schema
      global postgres_schema,postgres_column_datatype
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(postgres_client)
      #users api access
      global users_api_access
      if postgres_schema.get("users",{}).get("api_access"):users_api_access=await users_api_access_read(postgres_client_asyncpg,users_api_access_max_count)
      #users is_active
      global users_is_active
      if postgres_schema.get("users",{}).get("is_active"):users_is_active=await users_is_active_read(postgres_client_asyncpg,users_is_active_max_count)
      #redis client
      global redis_client
      if redis_url:redis_client=await function_redis_client_read(redis_url)
      #mongodb client
      global mongodb_client
      if mongodb_url:mongodb_client=await mongodb_client_read(mongodb_url)
      #s3 client
      global s3_client,s3_resource
      if s3_region_name:s3_client,s3_resource=await s3_client_read(s3_region_name,aws_access_key_id,aws_secret_access_key)
      #sns client
      global sns_client
      if sns_region_name:sns_client=await sns_client_read(sns_region_name,aws_access_key_id,aws_secret_access_key)
      #ses client
      global ses_client
      if ses_region_name:ses_client=await ses_client_read(ses_region_name,aws_access_key_id,aws_secret_access_key)
      #rabbitmq channel
      global rabbitmq_client,rabbitmq_channel
      if rabbitmq_url:rabbitmq_client,rabbitmq_channel=await function_rabbitmq_channel_read(rabbitmq_url)
      #lavinmq channel
      global lavinmq_client,lavinmq_channel
      if lavinmq_url:lavinmq_client,lavinmq_channel=await function_lavinmq_channel_read(lavinmq_url)
      #kafka producer client
      global kafka_producer_client
      if kafka_url:kafka_producer_client=await kafka_producer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name)
      #gsheet client
      global gsheet_client
      if gsheet_service_account_json_path:gsheet_client=await gsheet_client_read(gsheet_service_account_json_path,gsheet_scope_list)
      #openai client
      global openai_client
      if openai_key:openai_client=openai_client_read(openai_key)
      #app state
      app.state.global_state={
      "postgres_client": postgres_client,
      "postgres_column_datatype": postgres_column_datatype
      }
      #app shutdown
      yield
      #postgres
      await postgres_client.disconnect()
      await postgres_client_asyncpg.close()
      if postgres_client_read:await postgres_client_read.close()
      #redis
      if redis_client:await redis_client.aclose()
      #kafka
      if kafka_producer_client:await kafka_producer_client.stop()
      #rabbitmq
      if rabbitmq_client:
         if not rabbitmq_channel.is_closed:await rabbitmq_channel.close()
         if not rabbitmq_client.is_closed:await rabbitmq_client.close()
      #lavinmq
      if lavinmq_client:
         if not lavinmq_channel.is_closed:await lavinmq_channel.close()
         if not lavinmq_client.is_closed:await lavinmq_client.close()
   except Exception as e:print(str(e))
   
#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#sentry
import sentry_sdk
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)

#prometheus
from prometheus_fastapi_instrumentator import Instrumentator
if False:Instrumentator().instrument(app).expose(app)

#middleware
from fastapi import Request
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      start=time.time()
      response=None
      error=None
      request.state.user=await function_token_check(request,key_root,key_jwt,function_token_decode)
      if "admin/" in request.url.path:await function_api_access_check(request,api_config,users_api_access,postgres_client)
      if api_config.get(request.url.path,{}).get("is_active_check")==1:await function_is_active_check(request,users_is_active,postgres_client)
      if api_config.get(request.url.path,{}).get("rate_limiter"):await function_rate_limiter_check(request,api_config,redis_client)
      if request.query_params.get("is_background")=="1":response=await function_api_response_background(request,api_function)
      elif api_config.get(request.url.path,{}).get("is_cache")==1:response=await function_api_response_cache("get",request,None,redis_client)
      if not response:
         response=await api_function(request)
         if api_config.get(request.url.path,{}).get("is_cache")==1:response=await function_api_response_cache("set",request,response,redis_client)
   except Exception as e:
      error=str(e)
      print(traceback.format_exc())
      response=function_error(error)
      if sentry_dsn:sentry_sdk.capture_exception(e)
   object={"ip_address":request.client.host,"created_by_id":request.state.user.get("id",None),"api":request.url.path,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
   asyncio.create_task(log_api_create(object,log_api_batch_count,function_postgres_create,postgres_client,postgres_column_datatype,function_object_serialize))
   return response

#router
router_add(router_list,app)

#api
from fastapi import Request,responses
import json,time,os,asyncio,requests,sys,aio_pika

@app.get("/")
async def index():
   return {"status":1,"message":"welcome to atom"}

@app.get("/root/postgres-init")
async def root_postgres_init(request:Request):
   await function_postgres_schema_init(postgres_client,function_postgres_schema_read,postgres_config)
   return {"status":1,"message":"done"}

@app.post("/root/postgres-uploader")
async def root_postgres_uploader(request:Request):
   object,[mode,table,file_list]=await function_param_read("form",request,["mode","table","file_list"],[])
   object_list=await function_file_to_object_list(file_list[-1])
   if mode=="create":output=await function_postgres_create(table,object_list,1,postgres_client,postgres_column_datatype,function_object_serialize)
   if mode=="update":output=await function_postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,function_object_serialize)
   if mode=="delete":output=await function_postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.post("/root/redis-uploader")
async def root_redis_uploader(request:Request):
   object,[table,file_list,expiry]=await function_param_read("form",request,["table","file_list"],["expiry"])
   object_list=await function_file_to_object_list(file_list[-1])
   await function_redis_object_create(redis_client,table,object_list,expiry)
   return {"status":1,"message":"done"}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   object,[mode,bucket]=await function_param_read("body",request,["mode","bucket"],[])
   if mode=="create":output=await function_s3_bucket_create(s3_client,bucket,s3_region_name)
   if mode=="public":output=await function_s3_bucket_public(s3_client,bucket)
   if mode=="empty":output=await function_s3_bucket_empty(s3_resource,bucket)
   if mode=="delete":output=await function_s3_bucket_delete(s3_client,bucket)
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   object,[url]=await function_param_read("body",request,["url"],[])
   for item in url.split("---"):output=await function_s3_url_delete(item,s3_resource)
   return {"status":1,"message":output}

@app.post("/auth/signup")
async def auth_signup(request:Request):
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_signup_username_password(postgres_client,type,username,password)
   token=await function_token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

@app.post("/auth/signup-bigint")
async def auth_signup_bigint(request:Request):
   object,[type,username,password]=await function_param_read("body",request,["type","username","password"],[])
   user=await function_signup_username_password_bigint(postgres_client,type,username,password)
   token=await function_token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

@app.post("/auth/login-password-username")
async def auth_login_password_username(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_login_password_username(postgres_client,function_token_create,key_jwt,token_expire_sec,type,password,username)
   return {"status":1,"message":token}

@app.post("/auth/login-password-bigint")
async def auth_login_password_bigint(request:Request):
   object,[type,password,username]=await function_param_read("body",request,["type","password","username"],[])
   token=await function_login_password_username_bigint(postgres_client,function_token_create,key_jwt,token_expire_sec,type,password,username)
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   object,[type,password,email]=await function_param_read("body",request,["type","password","email"],[])
   token=await function_login_password_email(postgres_client,function_token_create,key_jwt,token_expire_sec,type,password,email)
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   object,[type,password,mobile]=await function_param_read("body",request,["type","password","mobile"],[])
   token=await function_login_password_mobile(postgres_client,function_token_create,key_jwt,token_expire_sec,type,password,mobile)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   object,[type,otp,email]=await function_param_read("body",request,["type","otp","email"],[])
   token=await function_login_otp_email(postgres_client,function_token_create,key_jwt,token_expire_sec,function_verify_otp,type,otp,email)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   object,[type,otp,mobile]=await function_param_read("body",request,["type","otp","mobile"],[])
   token=await function_login_otp_mobile(postgres_client,function_token_create,key_jwt,token_expire_sec,function_verify_otp,type,otp,mobile)
   return {"status":1,"message":token}

@app.post("/auth/login-google")
async def auth_login_google(request:Request):
   object,[type,google_token]=await function_param_read("body",request,["type","google_token"],[])
   token=await function_login_google(postgres_client,function_token_create,key_jwt,token_expire_sec,google_user_read,google_client_id,type,google_token)
   return {"status":1,"message":token}

@app.get("/my/profile")
async def my_profile(request:Request):
   user=await read_user_single(postgres_client,request.state.user["id"])
   asyncio.create_task(function_update_user_last_active_at(postgres_client,request.state.user["id"]))
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   user=await read_user_single(postgres_client,request.state.user["id"])
   token=await function_token_create(key_jwt,token_expire_sec,user)
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   user=await read_user_single(postgres_client,request.state.user["id"])
   if user["api_access"]:return function_error("not allowed as you have api_access")
   await function_delete_user(mode,postgres_client,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request):
   object_1,[table,is_serialize,queue]=await function_param_read("query",request,["table"],["is_serialize","queue"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   object["created_by_id"]=request.state.user["id"]
   if table in ["users"]:return function_error("table not allowed")
   if len(object)<=1:return function_error ("object issue")
   if any(key in column_disabled_non_admin for key in object):return function_error(" object key not allowed")
   if not queue:output=await function_postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   elif queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      if queue=="redis":output=await function_redis_publish(redis_client,channel_name,data)
      elif queue=="rabbitmq":output=await function_rabbitmq_publish(rabbitmq_channel,channel_name,data)
      elif queue=="lavinmq":output=await function_lavinmq_publish(lavinmq_channel,channel_name,data)
      elif queue=="kafka":output=await function_kafka_publish(kafka_producer_client,channel_name,data)
      elif "mongodb" in queue:output=await mongodb_create_object(mongodb_client,queue.split('_')[1],table,[object])
   return {"status":1,"message":output}

@app.get("/my/object-read")
async def my_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   output=await function_postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   return {"status":1,"message":output}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   object,[table,parent_table,parent_column,order,limit,page]=await function_param_read("query",request,["table","parent_table","parent_column"],["order","limit","page"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   output=await function_postgres_parent_read(table,parent_column,parent_table,postgres_client,order,limit,(page-1)*limit,request.state.user["id"])
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request):
   object_1,[table,otp]=await function_param_read("query",request,["table"],["otp"])
   object,[]=await function_param_read("body",request,[],[])
   object["updated_by_id"]=request.state.user["id"]
   if "id" not in object:return function_error ("id missing")
   if len(object)<=2:return function_error ("object length issue")
   if any(key in column_disabled_non_admin for key in object):return function_error(" object key not allowed")
   if table=="users":
      if object["id"]!=request.state.user["id"]:return function_error ("wrong id")
      if any(key in object and len(object)!=3 for key in ["password","email","mobile"]):return function_error("object length should be 2")
      if any(key in object and not otp for key in ["email","mobile"]):return function_error("otp missing")
      if otp:
         email,mobile=object.get("email"),object.get("mobile")
         await function_verify_otp(postgres_client,otp,email,mobile)
   if table=="users":output=await function_postgres_update("users",[object],1,postgres_client,postgres_column_datatype,function_object_serialize)
   else:output=await function_postgres_update_user(table,[object],1,postgres_client,postgres_column_datatype,function_object_serialize,request.state.user["id"])
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   if table in ["users"]:return function_error("table not allowed")
   if column in column_disabled_non_admin:return function_error("column not allowed")
   await function_postgres_update_ids(postgres_client,table,ids,column,value,request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   if table in ["users"]:return function_error("table not allowed")
   await function_postgres_delete_ids(postgres_client,table,ids,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   object["created_by_id"]=f"=,{request.state.user['id']}"
   if table in ["users"]:return function_error("table not allowed")
   await function_postgres_delete_any(table,object,postgres_client,create_where_string,function_object_serialize,postgres_column_datatype)
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def my_message_received(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_received_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   if object_list:asyncio.create_task(function_mark_message_object_read(postgres_client,object_list))
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   object,[order,limit,page,is_unread]=await function_param_read("query",request,[],["order","limit","page","is_unread"])
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_inbox_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request):
   object,[user_id,order,limit,page]=await function_param_read("query",request,["user_id"],["order","limit","page"])
   user_id=int(user_id)
   order,limit,page=order if order else "id desc",int(limit) if limit else 100,int(page) if page else 1
   object_list=await function_message_thread_user(postgres_client,request.state.user["id"],user_id,order,limit,(page-1)*limit)
   asyncio.create_task(function_mark_message_read_thread(postgres_client,request.state.user["id"],user_id))
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete-bulk")
async def my_message_delete_bulk(request:Request):
   object,[mode]=await function_param_read("query",request,["mode"],[])
   if mode=="all":await function_message_delete_user_all(postgres_client,request.state.user["id"])
   if mode=="created":await function_message_delete_user_created(postgres_client,request.state.user["id"])
   if mode=="received":await function_message_delete_user_received(postgres_client,request.state.user["id"])
   return {"status":1,"message":"done"}

@app.delete("/my/message-delete-single")
async def my_message_delete_single(request:Request):
   object,[id]=await function_param_read("query",request,["id"],[])
   await function_message_delete_user_single(postgres_client,request.state.user["id"],int(id))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_generate_save_otp(postgres_client,None,mobile)
   await function_sns_send_message(sns_client,mobile,str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns-template")
async def public_otp_send_mobile_sns_template(request:Request):
   object,[mobile,template_id,entity_id,sender_id,message]=await function_param_read("body",request,["mobile","template_id","entity_id","sender_id","message"],[])
   otp=await function_generate_save_otp(postgres_client,None,mobile)
   await function_sns_send_message_template(sns_client,mobile,template_id,entity_id,sender_id,message)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def public_otp_send_mobile_fast2sms(request:Request):
   object,[mobile]=await function_param_read("body",request,["mobile"],[])
   otp=await function_generate_save_otp(postgres_client,None,mobile)
   await function_otp_send_mobile_fast2sms(fast2sms_url,fast2sms_key,mobile,otp)
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_generate_save_otp(postgres_client,email,None)
   await function_send_email_ses(ses_client,sender_email,[email],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def public_otp_send_email_resend(request:Request):
   object,[email,sender_email]=await function_param_read("body",request,["email","sender_email"],[])
   otp=await function_generate_save_otp(postgres_client,email,None)
   await function_send_email_resend(resend_key,resend_url,sender_email,[email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def public_otp_verify_email(request:Request):
   object,[otp,email]=await function_param_read("body",request,["otp","email"],[])
   await function_verify_otp(postgres_client,otp,email,None)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def public_otp_verify_mobile(request:Request):
   object,[otp,mobile]=await function_param_read("body",request,["otp","mobile"],[])
   await function_verify_otp(postgres_client,otp,None,mobile)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 0
   if table not in table_allowed_public_create.split(","):return function_error("table not allowed")
   output=await function_postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def public_object_read(request:Request):
   object,[table,creator_data]=await function_param_read("query",request,["table"],["creator_data"])
   if table not in table_allowed_public_read.split(","):return function_error("table not allowed")
   if postgres_client_read:object_list=await function_postgres_read(table,object,postgres_client_read,postgres_column_datatype,function_object_serialize,create_where_string)
   else:object_list=await function_postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   if object_list and creator_data:object_list=await function_add_creator_data(postgres_client,object_list,creator_data)
   return {"status":1,"message":object_list}

public_info_cache={}
@app.get("/public/info")
async def public_info(request:Request):
   global public_info_cache
   if not public_info_cache or (time.time()-public_info_cache.get("set_at")>=1000):
      public_info_cache={
      "set_at":time.time(),
      "api_list":[route.path for route in request.app.routes],
      "redis":await redis_client.info() if redis_client else None,
      "postgres_schema":postgres_schema,
      "postgres_column_datatype":postgres_column_datatype,
      "bucket":s3_client.list_buckets() if s3_client else None,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True))
      }
   return {"status":1,"message":public_info_cache}

@app.get("/public/page/{filename}")
async def public_page(filename:str):
   file_path=os.path.join(".",f"{filename}.html")
   if ".." in filename or "/" in filename:return function_error("invalid filename")
   if not os.path.isfile(file_path):return function_error ("file not found")
   with open(file_path, "r", encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   object,[bucket,file_list,key]=await function_param_read("form",request,["bucket","file_list"],["key"])
   key_list=key.split("---") if key else None
   output=await function_s3_file_upload_direct(s3_client,s3_region_name,bucket,key_list,file_list)
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   object,[bucket,key]=await function_param_read("body",request,["bucket","key"],[])
   output=await s3_file_upload_presigned(s3_client,s3_region_name,bucket,key,1000,100)
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   object_1,[table,is_serialize]=await function_param_read("query",request,["table"],["is_serialize"])
   object,[]=await function_param_read("body",request,[],[])
   is_serialize=int(is_serialize) if is_serialize else 1
   if postgres_schema.get(table).get("created_by_id"):object["created_by_id"]=request.state.user["id"]
   output=await function_postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   object_1,[table]=await function_param_read("query",request,["table"],[])
   object,[]=await function_param_read("body",request,[],[])
   if "id" not in object:return function_error ("id missing")
   if len(object)<=1:return function_error ("object length issue")
   if postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   output=await function_postgres_update(table,[object],1,postgres_client,postgres_column_datatype,function_object_serialize)
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   object,[table,ids,column,value]=await function_param_read("body",request,["table","ids","column","value"],[])
   await function_postgres_update_ids(postgres_client,table,ids,column,value,request.state.user["id"],None)
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   object,[table,ids]=await function_param_read("body",request,["table","ids"],[])
   await function_postgres_delete_ids(postgres_client,table,ids,None)
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def admin_object_read(request:Request):
   object,[table]=await function_param_read("query",request,["table"],[])
   output=await function_postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   return {"status":1,"message":output}

@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   object,[query]=await function_param_read("body",request,["query"],[])
   output=await postgres_query_runner(postgres_client,query,request.state.user["id"])
   return {"status":1,"message":output}

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_uvicorn_server_start(app))
   except KeyboardInterrupt:print("exit")