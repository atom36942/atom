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

async def function_param_read(mode,request,must,optional):
   must_value=[]
   optional_value=[]
   if mode=="query_param":object=request.query_params
   for item in must:
      if item not in object:raise Exception(f"{item} missing")
      must_value.append(object[item])
   for item in optional:
      optional_value.append(object.get(item))
   return must_value,optional_value

@app.post("/root/db-init")
async def root_db_init(request:Request):
   #param
   mode=object.get("mode")
   if not mode:return function_error("mode missing")
   #variable
   elif mode=="1":config=postgres_config
   elif mode=="2":config=await request.json()
   #logic
   await postgres_schema_init(postgres_client,function_postgres_schema_read,config)
   #final
   return {"status":1,"message":"done"}

@app.post("/root/db-uploader")
async def root_db_uploader(request:Request):
   #param
   object,file_list=await form_data_read(request)
   mode=object.get("mode")
   table=object.get("table")
   is_serialize=int(object.get("is_serialize",1))
   if not mode or not table or not file_list:return function_error("mode/table/file missing")
   #object list
   object_list=await file_to_object_list(file_list[-1])
   #logic
   if mode=="create":output=await function_postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   if mode=="update":output=await function_postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,function_object_serialize)
   if mode=="delete":output=await postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,function_object_serialize)
   #final
   return {"status":1,"message":output}

@app.post("/root/redis-uploader")
async def root_redis_uploader(request:Request):
   #param
   object,file_list=await form_data_read(request)
   table=object.get("table")
   expiry=object.get("expiry")
   if not table or not file_list:return function_error("table/file missing")
   #object list
   object_list=await file_to_object_list(file_list[-1])
   #logic
   await redis_object_create(redis_client,table,object_list,expiry)
   #final
   return {"status":1,"message":"done"}

@app.delete("/root/redis-reset")
async def root_reset_redis():
   #logic
   if redis_client:await redis_client.flushall()
   #final
   return {"status":1,"message":"done"}

@app.put("/root/reset-global")
async def root_reset_global():
   #postgres schema reset
   global postgres_schema,postgres_column_datatype
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(postgres_client)
   #users api access reset
   global users_api_access
   if postgres_schema.get("users",{}).get("api_access"):users_api_access=await users_api_access_read(postgres_client_asyncpg,users_api_access_max_count)
   #users is_active reset
   global users_is_active
   if postgres_schema.get("users",{}).get("is_active"):users_is_active=await users_is_active_read(postgres_client_asyncpg,users_is_active_max_count)
   #final
   return {"status":1,"message":"done"}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   #param
   mode=request.query_params.get("mode")
   bucket=request.query_params.get("bucket")
   if not mode or not bucket:return function_error("mode/bucket missing")
   #logic
   if mode=="create":output=await s3_bucket_create(s3_client,bucket,s3_region_name)
   if mode=="public":output=await s3_bucket_public(s3_client,bucket)
   if mode=="empty":output=await s3_bucket_empty(s3_resource,bucket)
   if mode=="delete":output=await s3_bucket_delete(s3_client,bucket)
   #final
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   #param
   url=request.query_params.get("url")
   if not url:return function_error("url missing")
   #logic
   for item in url.split("---"):output=await s3_url_delete(item,s3_resource)
   #final
   return {"status":1,"message":output}

@app.post("/auth/signup-username-password")
async def auth_signup_username_password(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return function_error("type/username/password missing")
   #check
   if is_signup==0:return function_error("signup disabled")
   if type not in user_type_allowed:return function_error("wrong type")
   #logic
   user=await signup_username_password(postgres_client,type,username,password)
   token=await token_create(key_jwt,token_expire_sec,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/signup-username-password-bigint")
async def auth_signup_username_password_bigint(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username_bigint=object.get("username_bigint")
   password_bigint=object.get("password_bigint")
   if not type or not username_bigint or not password_bigint:return function_error("type/username_bigint/password_bigint missing")
   #check
   if is_signup==0:return function_error("signup disabled")
   if type not in user_type_allowed:return function_error("wrong type")
   #logic
   user=await signup_username_password_bigint(postgres_client,type,username_bigint,password_bigint)
   token=await token_create(key_jwt,token_expire_sec,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-username")
async def auth_login_password_username(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return function_error("type/username/password missing")
   #logic
   token=await login_password_username(postgres_client,token_create,key_jwt,token_expire_sec,type,username,password)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-username-bigint")
async def auth_login_password_username_bigint(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username_bigint=object.get("username_bigint")
   password_bigint=object.get("password_bigint")
   if not type or not username_bigint or not password_bigint:return function_error("type/username_bigint/password_bigint missing")
   #logic
   token=await login_password_username_bigint(postgres_client,token_create,key_jwt,token_expire_sec,type,username_bigint,password_bigint)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   password=object.get("password")
   if not type or not email or not password:return function_error("type/email/password missing")
   #logic
   token=await login_password_email(postgres_client,token_create,key_jwt,token_expire_sec,type,email,password)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   password=object.get("password")
   if not type or not mobile or not password:return function_error("type/mobile/password missing")
   #logic
   token=await login_password_mobile(postgres_client,token_create,key_jwt,token_expire_sec,type,mobile,password)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   otp=object.get("otp")
   if not type or not email or not otp:return function_error("type/email/otp missing")
   #check
   if type not in user_type_allowed:return function_error("wrong type")
   #logic
   token=await login_otp_email(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,email,otp)
   #final
   return {"status":1,"message":token}
   
@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   otp=object.get("otp")
   if not type or not mobile or not otp:return function_error("type/mobile/otp missing")
   #check
   if type not in user_type_allowed:return function_error("wrong type")
   #logic
   token=await login_otp_mobile(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,mobile,otp)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-oauth-google")
async def auth_login_oauth_google(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   google_token=object.get("google_token")
   if not type or not google_token:return function_error("type/google_token missing")
   #check
   if type not in user_type_allowed:return function_error("wrong type")
   #logic
   token=await login_google(postgres_client,token_create,key_jwt,token_expire_sec,google_user_read,google_client_id,type,google_token)
   #final
   return {"status":1,"message":token}

@app.get("/my/profile")
async def my_profile(request:Request):
   #logic
   user=await read_user_single(postgres_client,request.state.user["id"])
   asyncio.create_task(update_user_last_active_at(postgres_client,request.state.user["id"]))
   #final
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #read user
   user=await read_user_single(postgres_client,request.state.user["id"])
   #token create
   token=await token_create(key_jwt,token_expire_sec,user)
   #final
   return {"status":1,"message":token}

@app.delete("/my/account-delete")
async def my_account_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   if not mode:return function_error("mode missing")
   #check user
   user=await read_user_single(postgres_client,request.state.user["id"])
   if user["api_access"]:return function_error("not allowed as you have api_access")
   #logic
   if mode=="soft":
      query="update users set is_deleted=1 where id=:id;"
      values={"id":request.state.user["id"]}
      await postgres_client.execute(query=query,values=values)
   elif mode=="hard":
      query="delete from users where id=:id;"
      values={"id":request.state.user["id"]}
      await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   queue=request.query_params.get("queue")
   object=await request.json()
   if not table:return function_error("table missing")
   #modify
   object["created_by_id"]=request.state.user["id"]
   #check
   if table in ["users"]:return function_error("table not allowed")
   if len(object)<=1:return function_error ("object issue")
   if any(key in column_disabled_non_admin for key in object):return function_error(" object key not allowed")
   #logic
   data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
   if not queue:output=await function_postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   elif queue=="redis":output=await redis_client.publish(channel_name,json.dumps(data))
   elif queue=="rabbitmq":output=await rabbitmq_channel.default_exchange.publish(aio_pika.Message(body=json.dumps(data).encode()),routing_key=channel_name)
   elif queue=="lavinmq":output=await lavinmq_channel.default_exchange.publish(aio_pika.Message(body=json.dumps(data).encode()),routing_key=channel_name)
   elif queue=="kafka":output=await kafka_producer_client.send_and_wait(channel_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   elif "mongodb" in queue:output=await mongodb_create_object(mongodb_client,queue.split('_')[1],table,[object])
   #final
   return {"status":1,"message":output}

@app.get("/my/object-read")
async def my_object_read(request:Request):
   #param
   object=dict(request.query_params)
   table=object.get("table")
   if not table:return function_error("table missing")
   #modify
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #logic
   output=await postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   #final
   return {"status":1,"message":output}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   table=request.query_params.get("table")
   parent_column=request.query_params.get("parent_column")
   parent_table=request.query_params.get("parent_table")
   if not table or not parent_column:return function_error("table/parent_column/parent_table missing")
   #logic
   output=await postgres_parent_read(table,parent_column,parent_table,postgres_client,order,limit,(page-1)*limit,request.state.user["id"])
   #final
   return {"status":1,"message":output}

@app.put("/my/user-update")
async def my_user_update(request:Request):
   #param
   object=await request.json()
   otp=int(request.query_params.get("otp",0))
   #modify
   object["updated_by_id"]=request.state.user["id"]
   #check
   if "id" not in object:return function_error ("id missing")
   if object["id"]!=request.state.user["id"]:return function_error ("wrong id")
   if len(object)<=2:return function_error ("object length issue")
   if any(key in column_disabled_non_admin for key in object):return function_error(" object key not allowed")
   if any(key in object and len(object)!=3 for key in ["password","email","mobile"]):return function_error("object length should be 2")
   if any(key in object and not otp for key in ["email","mobile"]):return function_error("otp missing")
   #otp verify
   if otp>0:
      email,mobile=object.get("email"),object.get("mobile")
      await verify_otp(postgres_client,otp,email,mobile)
   #logic
   output=await function_postgres_update("users",[object],1,postgres_client,postgres_column_datatype,function_object_serialize)
   #final
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if not table:return function_error("table missing")
   #modify
   object["updated_by_id"]=request.state.user["id"]
   #check
   if table in ["users"]:return function_error("table not allowed")
   if "id" not in object:return function_error ("id missing")
   if len(object)<=2:return function_error ("object length issue")
   if any(key in column_disabled_non_admin for key in object):return function_error(" object key not allowed")
   #logic
   output=await postgres_update_user(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize,request.state.user["id"])
   #final
   return {"status":1,"message":output}

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   del object["table"]
   del object["ids"]
   key,value=next(reversed(object.items()),(None, None))
   if not table or not ids or not key:return function_error("table/ids/key must")
   #check
   if table in ["users"]:return function_error("table not allowed")
   if key in column_disabled_non_admin:return function_error("column not allowed")
   #logic
   await postgres_update_ids(postgres_client,table,ids,key,value,request.state.user["id"],request.state.user["id"])
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   if not table or not ids:return function_error("table/ids must")
   #check
   if table in ["users"]:return function_error("table not allowed")
   #logic
   await postgres_delete_ids(postgres_client,table,ids,request.state.user["id"])
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request):
   #param
   table=request.query_params.get("table")
   object=dict(request.query_params)
   if not table:return function_error("table missing")
   #modify
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #check
   if table in ["users"]:return function_error("table not allowed")
   #logic
   await postgres_delete_any(table,object,postgres_client,create_where_string,function_object_serialize,postgres_column_datatype)
   #final
   return {"status":1,"message":"done"}

@app.get("/my/message-received")
async def my_message_received(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   is_unread=request.query_params.get("is_unread")
   #logic
   object_list=await message_received_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   #mark message read
   if object_list:
      ids=','.join([str(item['id']) for item in object_list])
      query=f"update message set is_read=1 where id in ({ids});"
      asyncio.create_task(postgres_client.execute(query=query,values={}))
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   is_unread=request.query_params.get("is_unread")
   #logic
   object_list=await message_inbox_user(postgres_client,request.state.user["id"],order,limit,(page-1)*limit,is_unread)
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   user_id=int(request.query_params.get("user_id",0))
   if not user_id:return function_error("user_id missing")
   #logic
   object_list=await message_thread_user(postgres_client,request.state.user["id"],user_id,order,limit,(page-1)*limit)
   #mark message thread read
   asyncio.create_task(mark_message_read_thread(postgres_client,request.state.user["id"],user_id))
   #final
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete")
async def my_message_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   id=int(request.query_params.get("id",0))
   if not mode:return function_error("mode missing")
   #check
   if mode=="single" and not id:return function_error("id missing")
   #logic
   if mode=="single":await message_delete_user_single(postgres_client,request.state.user["id"],id)
   if mode=="created":await message_delete_user_created(postgres_client,request.state.user["id"])
   if mode=="received":await message_delete_user_received(postgres_client,request.state.user["id"])
   if mode=="all":await message_delete_user_all(postgres_client,request.state.user["id"])
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request):
   #param
   object=await request.json()
   mobile=object.get("mobile")
   template_id=object.get("template_id")
   message=object.get("message")
   entity_id=object.get("entity_id")
   sender_id=object.get("sender_id")
   if not mobile:return function_error("mobile missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,None,mobile)
   #logic
   if template_id:await send_message_template_sns(sns_client,mobile,message.replace("{otp}",str(otp)),entity_id,template_id,sender_id)
   else:sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def public_otp_send_mobile_fast2sms(request:Request):
   #param
   object=await request.json()
   mobile=object.get("mobile")
   if not mobile:return function_error("mobile missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,None,mobile)
   #logic
   response=requests.get("https://www.fast2sms.com/dev/bulkV2",params={"authorization":fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   #final
   return {"status":1,"message":response.json()}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   #param
   object=await request.json()
   email=object.get("email")
   sender_email=object.get("sender_email")
   if not email or not sender_email:return function_error("email/sender_email missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,email,None)
   #logic
   await send_email_ses(ses_client,sender_email,[email],"your otp code",str(otp))
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def public_otp_send_email_resend(request:Request):
   #param
   object=await request.json()
   email=object.get("email")
   sender_email=object.get("sender_email")
   if not email or not sender_email:return function_error("email/sender_email missing")
   #generate otp
   otp=await generate_save_otp(postgres_client,email,None)
   #logic
   await send_email_resend(resend_key,"https://api.resend.com/emails",sender_email,[email],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def public_otp_verify_email(request:Request):
   #param
   object=await request.json()
   otp=object.get("otp")
   email=object.get("email")
   if not otp or not email:return function_error("otp/email missing")
   #logic
   await verify_otp(postgres_client,otp,email,None)
   #final
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def public_otp_verify_mobile(request:Request):
   #param
   object=await request.json()
   otp=object.get("otp")
   mobile=object.get("mobile")
   if not otp or not mobile:return function_error("otp/mobile missing")
   #logic
   await verify_otp(postgres_client,otp,None,mobile)
   #final
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if not table:return function_error("table missing")
   #check
   if table not in table_allowed_public_create.split(","):return function_error("table not allowed")
   #logic
   output=await function_postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   #final
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def public_object_read(request:Request):
   #param
   object=request.query_params
   table=object.get("table")
   creator_data=object.get("creator_data")
   if not table:return function_error("table missing")
   #check
   if table not in table_allowed_public_read.split(","):return function_error("table not allowed")
   #logic
   if postgres_client_read:object_list=await postgres_read(table,object,postgres_client_read,postgres_column_datatype,function_object_serialize,create_where_string)
   else:object_list=await postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   #add creator data
   if creator_data and object_list:object_list=await add_creator_data(postgres_client,object_list,creator_data)
   #final
   return {"status":1,"message":object_list}

@app.post("/public/openai-prompt")
async def public_openai_prompt(request:Request):
   #param
   object=await request.json()
   model=object.get("model")
   prompt=object.get("prompt")
   is_web_search=int(object.get("is_web_search",0))
   previous_response_id=object.get("previous_response_id")
   if not model or not prompt:return function_error("model/prompt missing")
   #logic
   output=await openai_prompt(openai_client,model,prompt,is_web_search,previous_response_id)
   #final
   return {"status":1,"message":output}

@app.post("/public/openai-ocr")
async def public_openai_ocr(request:Request):
   #param
   object,file_list=await form_data_read(request)
   model=object.get("model")
   prompt=object.get("prompt")
   if not model or not prompt or not file_list:return function_error("model/prompt/file missing")
   #logic
   output=await openai_ocr(openai_client,model,prompt,file_list[-1])
   #final
   return {"status":1,"message":output}

@app.post("/public/gsheet-create")
async def public_gsheet_create(request:Request):
   #param
   spreadsheet_id=request.query_params.get("spreadsheet_id")
   sheet_name=request.query_params.get("sheet_name")
   object=await request.json()
   if not spreadsheet_id or not sheet_name:return function_error("spreadsheet_id/sheet_name missing")
   #logic
   output=await gsheet_create(gsheet_client,spreadsheet_id,sheet_name,object)
   #final
   return {"status":1,"message":output}

@app.get("/public/gsheet-read-service-account")
async def public_gsheet_read_service_account(request:Request):
   #param
   spreadsheet_id=request.query_params.get("spreadsheet_id")
   sheet_name=request.query_params.get("sheet_name")
   cell_boundary=request.query_params.get("cell_boundary")
   if not spreadsheet_id or not sheet_name:return function_error("spreadsheet_id/sheet_name missing")
   #logic
   output=await gsheet_read_service_account(gsheet_client,spreadsheet_id,sheet_name,cell_boundary)
   #final
   return {"status":1,"message":output}

@app.get("/public/gsheet-read-direct")
async def public_gsheet_read_direct(request:Request):
   #param
   spreadsheet_id=request.query_params.get("spreadsheet_id")
   gid=request.query_params.get("gid")
   if not spreadsheet_id or not gid:return function_error("spreadsheet_id/gid missing")
   #logic
   output=await gsheet_read_pandas(spreadsheet_id,gid)
   #final
   return {"status":1,"message":output}

cache_public_info={}
@app.get("/public/info")
async def public_info(request:Request):
   #variable
   global cache_public_info
   #logic
   if not cache_public_info or (time.time()-cache_public_info.get("set_at")>=1000):
      cache_public_info={
      "set_at":time.time(),
      "api_list":[route.path for route in request.app.routes],
      "redis":await redis_client.info() if redis_client else None,
      "postgres_schema":postgres_schema,
      "postgres_column_datatype":postgres_column_datatype,
      "bucket":s3_client.list_buckets() if s3_client else None,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True))
      }
   #final
   return {"status":1,"message":cache_public_info}

@app.get("/public/page/{filename}")
async def public_page(filename:str):
   #variable
   file_path=os.path.join(".",f"{filename}.html")
   #check
   if ".." in filename or "/" in filename:return function_error("invalid filename")
   if not os.path.isfile(file_path):return function_error ("file not found")
   #logic
   with open(file_path, "r", encoding="utf-8") as file:html_content=file.read()
   #final
   return responses.HTMLResponse(content=html_content)

@app.get("/private/object-read")
async def private_object_read(request:Request):
   #param
   object=request.query_params
   table=object.get("table")
   if not table:return function_error("table missing")
   #check
   if table not in table_allowed_private_read.split(","):return function_error("table not allowed")
   #logic
   output=await postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   #final
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   #param
   object,file_list=await form_data_read(request)
   bucket=object.get("bucket")
   key=object.get("key")
   if not bucket or not file_list:return function_error("bucket/file missing")
   #variable
   key_list=None
   if key:key_list=key.split("---")
   #logic
   output=await s3_file_upload_direct(s3_client,s3_region_name,bucket,key_list,file_list)
   #final
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   #param
   object=await request.json()
   bucket=object.get("bucket")
   key=object.get("key")
   if not bucket or not key:return function_error("bucket/key missing")
   #logic
   output=await s3_file_upload_presigned(s3_client,s3_region_name,bucket,key,1000,100)
   #final
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   #param
   object=await request.json()
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   if not table:return function_error("table missing")
   #modify
   if postgres_schema.get(table).get("created_by_id"):object["created_by_id"]=request.state.user["id"]
   #logic
   output=await function_postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   #final
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if not table:return function_error("table missing")
   #modify
   if postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   #check
   if "id" not in object:return function_error ("id missing")
   if len(object)<=2:return function_error ("object length issue")
   #logic
   output=await function_postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,function_object_serialize)
   #final
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   del object["table"]
   del object["ids"]
   key,value=next(reversed(object.items()),(None, None))
   if not table or not ids or not key:return function_error("table/ids/key must")
   #logic
   await postgres_update_ids(postgres_client,table,ids,key,value,request.state.user["id"],None)
   #final
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   #param
   object=await request.json()
   table=object.get("table")
   ids=object.get("ids")
   if not table or not ids:return function_error("table/ids must")
   #logic
   await postgres_delete_ids(postgres_client,table,ids,None)
   #final
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def admin_object_read(request:Request):
   #param
   object=request.query_params
   table=object.get("table")
   if not table:return function_error("table missing")
   #logic
   output=await postgres_read(table,object,postgres_client,postgres_column_datatype,function_object_serialize,create_where_string)
   #final
   return {"status":1,"message":output}

@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   #param
   query=(await request.json()).get("query")
   if not query:return function_error("query must")
   #logic
   output=await postgres_query_runner(postgres_client,query,request.state.user["id"])
   #final
   return {"status":1,"message":output}

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_uvicorn_server_start(app))
   except KeyboardInterrupt:print("exit")