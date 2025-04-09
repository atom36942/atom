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
valkey_client=None
redis_pubsub=None
import redis.asyncio as redis
async def set_redis_client(redis_url,valkey_url,channel_name):
   global redis_client
   global valkey_client
   global redis_pubsub
   if redis_url:
      redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))
      redis_pubsub=redis_client.pubsub()
      await redis_pubsub.subscribe(channel_name)
   if valkey_url:valkey_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(valkey_url))
   return None

mongodb_client=None
import motor.motor_asyncio
async def set_mongodb_client(mongodb_url):
   global mongodb_client
   if mongodb_url:mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
   return None

s3_client=None
s3_resource=None
import boto3
async def set_s3_client(s3_region_name,aws_access_key_id,aws_secret_access_key):
   global s3_client
   global s3_resource
   if s3_region_name:
      s3_client=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
      s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

sns_client=None
import boto3
async def set_sns_client(sns_region_name,aws_access_key_id,aws_secret_access_key):
   global sns_client
   if sns_region_name:
      sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

ses_client=None
import boto3
async def set_ses_client(ses_region_name,aws_access_key_id,aws_secret_access_key):
   global ses_client
   if ses_region_name:
      ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

rabbitmq_client=None
rabbitmq_channel=None
import pika
async def set_rabbitmq_client(rabbitmq_url,channel_name):
   global rabbitmq_client
   global rabbitmq_channel
   if rabbitmq_url:
      rabbitmq_client=pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
      rabbitmq_channel=rabbitmq_client.channel()
      rabbitmq_channel.queue_declare(queue=channel_name)
   return None

lavinmq_client=None
lavinmq_channel=None
import pika
async def set_lavinmq_client(lavinmq_url,channel_name):
   global lavinmq_client
   global lavinmq_channel
   if lavinmq_url:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(lavinmq_url))
      lavinmq_channel=lavinmq_client.channel()
      lavinmq_channel.queue_declare(queue=channel_name)
   return None

kafka_producer_client=None
kafka_consumer_client=None
from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def set_kafka_client(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name):
   global kafka_producer_client
   global kafka_consumer_client
   if kafka_url:
      context=create_ssl_context(cafile=kafka_path_cafile,certfile=kafka_path_certfile,keyfile=kafka_path_keyfile)
      kafka_producer_client=AIOKafkaProducer(bootstrap_servers=kafka_url,security_protocol="SSL",ssl_context=context)
      kafka_consumer_client=AIOKafkaConsumer(channel_name,bootstrap_servers=kafka_url,security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
      await kafka_producer_client.start()
      await kafka_consumer_client.start()
   return None

#sentry
import sentry_sdk
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

#redis key builder
from fastapi import Request,Response
import jwt,json,hashlib
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param_sorted=str(dict(sorted(request.query_params.items())))
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   user_id=0
   if "my/" in api:user_id=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])["id"]
   key=f"{api}---{query_param_sorted}---{str(user_id)}".lower()
   if False:key=hashlib.sha256(str(key).encode()).hexdigest()
   return key

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #postgres client
      global postgres_client
      postgres_client=await client_postgres(postgres_url)
      #postgres client asyncpg
      global postgres_client_asyncpg
      postgres_client_asyncpg=await client_postgres_asyncpg(postgres_url)
      #postgres client read
      global postgres_client_read
      postgres_client_read=await client_postgres(postgres_url)
      #postgres schema
      global postgres_schema
      postgres_schema=await postgres_schema_read(postgres_client)
      #postgres column datatype
      global postgres_column_datatype
      postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
      #users api access
      global users_api_access
      if postgres_schema.get("users"):users_api_access=await get_users_api_access(postgres_client_asyncpg,100000)
      #users is_active
      global users_is_active
      if postgres_schema.get("users"):users_is_active=await get_users_is_active(postgres_client_asyncpg,100000)

      
      
      
      
      await set_redis_client(redis_url,valkey_url,channel_name)
      await set_s3_client(s3_region_name,aws_access_key_id,aws_secret_access_key)
      await set_sns_client(sns_region_name,aws_access_key_id,aws_secret_access_key)
      await set_ses_client(ses_region_name,aws_access_key_id,aws_secret_access_key)
      await set_mongodb_client(mongodb_url)
      await set_rabbitmq_client(rabbitmq_url,channel_name)
      await set_lavinmq_client(lavinmq_url,channel_name)
      await set_kafka_client(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name)
      #ratelimiter
      if redis_client:await FastAPILimiter.init(redis_client)
      #cache
      if valkey_client:FastAPICache.init(RedisBackend(valkey_client),key_builder=redis_key_builder)
      else:FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
      #disconnect
      yield
      await postgres_client.disconnect()
      await postgres_client_asyncpg.close()
      if redis_client:await redis_client.aclose()
      if valkey_client:await valkey_client.aclose()
      if rabbitmq_client and rabbitmq_channel.is_open:rabbitmq_channel.close()
      if rabbitmq_client and rabbitmq_client.is_open:rabbitmq_client.close()
      if lavinmq_client and lavinmq_channel.is_open:lavinmq_channel.close()
      if lavinmq_client and lavinmq_client.is_open:lavinmq_client.close()
      if kafka_producer_client:await kafka_producer_client.stop()
   except Exception as e:print(e.args)

#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#middleware
from fastapi import Request,responses
import time,traceback
from starlette.background import BackgroundTask
object_list_log_api=[]
@app.middleware("http")
async def middleware(request:Request,api_function):
   global object_list_log_api
   start=time.time()
   api=request.url.path
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   request.state.user={}
   error_text=None
   try:
      #auth check
      if any(item in api for item in ["root/","my/", "private/", "admin/"]) and not token:return error("Bearer token must")
      if token:
         if "root/" in api:
            if token!=key_root:return error("token root mismatch")
         else:
            request.state.user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
            response=await admin_check(request,api,api_id,users_api_access,postgres_client)
            if response["status"]==0:return error(response["message"])
            response=await is_active_check(request,api,users_is_active,postgres_client)
            if response["status"]==0:return error(response["message"])   
      #api response
      if request.query_params.get("is_background")=="1":
         body=await request.body()
         async def receive():return {"type":"http.request","body":body}
         async def api_function_new():
            request_new=Request(scope=request.scope,receive=receive)
            await api_function(request_new)
         response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
         response.background=BackgroundTask(api_function_new)
      else:response=await api_function(request)
   except Exception as e:
      print(traceback.format_exc())
      error_text=str(e.args)
      response=error(error_text)
   #log
   response_time_ms=(time.time()-start)*1000
   object={"created_by_id":request.state.user.get("id",None),"api":api,"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":response_time_ms,"description":error_text}
   object_list_log_api.append(object)
   if postgres_schema.get("log_api") and len(object_list_log_api)>=10 and request.query_params.get("is_background")!="1":
      response.background=BackgroundTask(postgres_create,"log_api",object_list_log_api,0,postgres_client,postgres_column_datatype,object_serialize)
      object_list_log_api=[]
   #final
   return response

#router
import os
for filename in []:
   router=__import__(filename).router
   app.include_router(router)
      
#api import
from fastapi import Request,UploadFile,Depends,BackgroundTasks,responses
import hashlib,datetime,json,time,os,random,httpx
from typing import Literal
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter

#index
@app.get("/")
async def index():
   return {"status":1,"message":"welcome to atom"}

#root
@app.post("/root/db-init")
async def root_db_init(request:Request):
   #param
   mode=request.query_params.get("mode")
   if not mode:return error("mode missing")
   #logic
   if mode=="default":await postgres_schema_init(postgres_client,postgres_schema_read,postgres_schema_default)
   if mode=="custom":await postgres_schema_init(postgres_client,postgres_schema_read,await request.json())
   #postgres schema
   global postgres_schema
   postgres_schema=await postgres_schema_read(postgres_client)
   #postgres column datatype
   global postgres_column_datatype
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   #final
   return {"status":1,"message":"done"}

@app.put("/root/reset-global")
async def root_reset_global():
   #postgres schema
   global postgres_schema
   postgres_schema=await postgres_schema_read(postgres_client)
   #postgres column datatype
   global postgres_column_datatype
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   #users api access
   global users_api_access
   if postgres_schema.get("users"):users_api_access=await get_users_api_access(postgres_client_asyncpg,100000)
   #users is_active
   global users_is_active
   if postgres_schema.get("users"):users_is_active=await get_users_is_active(postgres_client_asyncpg,100000)
   #final
   return {"status":1,"message":"done"}

@app.put("/root/db-checklist")
async def root_db_checklist():
   #logix
   await postgres_client.execute(query="update users set is_active=1,is_deleted=null where id=1;",values={})
   #final
   return {"status":1,"message":"done"}

@app.post("/root/db-uploader")
async def root_db_uploader(request:Request):
   #param
   form_data_key,form_data_file=await form_data_read(request)
   mode=form_data_key.get("mode")
   table=form_data_key.get("table")
   is_serialize=int(form_data_key.get("is_serialize",1))
   if not mode or not table or not form_data_file:return error("mode/table/file missing")
   object_list=await file_to_object_list(form_data_file[-1])
   #logic
   if mode=="create":response=await postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="update":response=await postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="delete":response=await postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/root/redis-set-csv")
async def root_redis_set_csv(request:Request):
   #param
   form_data_key,form_data_file=await form_data_read(request)
   table=form_data_key.get("table")
   expiry=form_data_key.get("expiry")
   if not table or not form_data_file:return error("table/file missing")
   object_list=await file_to_object_list(form_data_file[-1])   
   #logic
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if not expiry:pipe.set(key,json.dumps(object))
         else:pipe.setex(key,expiry,json.dumps(object))
      await pipe.execute()
   #final
   return {"status":1,"message":"done"}

@app.delete("/root/redis-reset")
async def root_reset_redis():
   #logic
   if redis_client:await redis_client.flushall()
   if valkey_client:await valkey_client.flushall()
   #final
   return {"status":1,"message":"done"}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   #param
   url=request.query_params.get("url")
   if not url:return error("url missing")
   #logic
   for item in url.split("---"):
      bucket,key=item.split("//",1)[1].split(".",1)[0],item.rsplit("/",1)[1]
      output=s3_resource.Object(bucket,key).delete()
   #final
   return {"status":1,"message":output}

@app.get("/root/s3-bucket-list")
async def root_s3_bucket_list():
   #logic
   output=s3_client.list_buckets()
   #final
   return {"status":1,"message":output}

@app.post("/root/s3-bucket-ops")
async def root_s3_bucket_ops(request:Request):
   #param
   mode=request.query_params.get("mode")
   bucket=request.query_params.get("bucket")
   if not mode or not bucket:return error("mode/bucket missing")
   #logic
   if mode=="create":output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   if mode=="public":
      s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
      policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
      output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   if mode=="empty":output=s3_resource.Bucket(bucket).objects.all().delete()
   if mode=="delete":output=s3_client.delete_bucket(Bucket=bucket)
   #final
   return {"status":1,"message":output}

#auth
@app.post("/auth/signup-username-password",dependencies=[Depends(RateLimiter(times=100,seconds=1))])
async def auth_signup_username_password(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return error("type/username/password missing")
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #check
   if is_signup==0:return error("signup disabled")
   if type not in user_type_allowed:return error("wrong type")
   #logic
   query="insert into users (type,username,password) values (:type,:username,:password) returning *;"
   values={"type":type,"username":username,"password":password}
   output=await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":output}

@app.post("/auth/login-password-username")
async def auth_login_password_username(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   if not type or not username or not password:return error("type/username/password missing")
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #logic
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":password}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return error("user not found")
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   password=object.get("password")
   if not type or not email or not password:return error("type/email/password missing")
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #logic
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":password}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return error("user not found")
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   password=object.get("password")
   if not type or not mobile or not password:return error("type/mobile/password missing")
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #logic
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":password}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:return error("user not found")
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   email=object.get("email")
   otp=object.get("otp")
   if not type or not email or not otp:return error("type/email/otp missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #otp verify
   response=await verify_otp(postgres_client,otp,email,None)
   if response["status"]==0:return error(response["message"])
   #logic
   query=f"select * from users where type=:type and email=:email order by id desc limit 1;"
   values={"type":type,"email":email}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,email) values (:type,:email) returning *;"
      values={"type":type,"email":email}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   mobile=object.get("mobile")
   otp=object.get("otp")
   if not type or not mobile or not otp:return error("type/mobile/otp missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #otp verify
   response=await verify_otp(postgres_client,otp,None,mobile)
   if response["status"]==0:return error(response["message"])
   #logic
   query=f"select * from users where type=:type and mobile=:mobile order by id desc limit 1;"
   values={"type":type,"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,mobile) values (:type,:mobile) returning *;"
      values={"type":type,"mobile":mobile}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.post("/auth/login-oauth-google")
async def auth_login_oauth_google(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   google_token=object.get("google_token")
   if not type or not google_token:return error("type/google_token missing")
   #check
   if type not in user_type_allowed:return error("wrong type")
   #verify
   response=verify_google_token(google_client_id,google_token)
   if response["status"]==0:return error(response["message"])
   google_user=response["message"]
   #logic
   query=f"select * from users where type=:type and google_id=:google_id order by id desc limit 1;"
   values={"type":type,"google_id":google_user["sub"]}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,google_id,google_data) values (:type,:google_id,:google_data) returning *;"
      values={"type":type,"google_id":google_user["sub"],"google_data":json.dumps(google_user)}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

#my
@app.get("/my/profile")
async def my_profile(request:Request,background:BackgroundTasks):
   #logic
   response=await request_user_read(request,postgres_client)
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   #background
   query="update users set last_active_at=:last_active_at where id=:id;"
   values={"id":request.state.user["id"],"last_active_at":datetime.datetime.now()}
   background.add_task(postgres_client.execute,query,values)
   #final
   return {"status":1,"message":user}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   #logic
   response=await request_user_read(request,postgres_client)
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   token=await token_create(key_jwt,user)
   #final
   return {"status":1,"message":token}

@app.delete("/my/account-delete-soft")
async def my_account_delete_soft(request:Request):
   #check
   response=await request_user_read(request,postgres_client)
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   print(user)
   if user["api_access"]:return error("user not allowed as you have api_access")
   #logic
   async with postgres_client.transaction():
      await postgres_client.execute(query="update message set is_deleted=1 where created_by_id=:user_id or user_id=:user_id;",values={"user_id":request.state.user["id"]})
      await postgres_client.execute(query="update users set is_deleted=1 where id=:id;",values={"id":request.state.user["id"]})
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/account-delete-hard")
async def my_account_delete_hard(request:Request):
   #check
   response=await request_user_read(request,postgres_client)
   if response["status"]==0:return error(response["message"])
   user=response["message"]
   if user["api_access"]:return error("user not allowed as you have api_access")
   #logic
   async with postgres_client.transaction():
      await postgres_client.execute(query="delete from report_user where created_by_id=:user_id or user_id=:user_id;",values={"user_id":request.state.user["id"]})
      await postgres_client.execute(query="delete from bookmark_workseeker where created_by_id=:user_id",values={"user_id":request.state.user["id"]})
      await postgres_client.execute(query="delete from message where created_by_id=:user_id or user_id=:user_id;",values={"user_id":request.state.user["id"]})
      await postgres_client.execute(query="delete from users where id=:id;",values={"id":request.state.user["id"]})
   #final
   return {"status":1,"message":"done"}

@app.post("/my/object-create")
async def my_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   queue=request.query_params.get("queue")
   if not table:return error("table missing")
   object=await request.json()
   object["created_by_id"]=request.state.user["id"]
   data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
   #check
   if table not in ["test","message","report_user","bookmark_workseeker","workseeker"]:return error("table not allowed")
   if len(object)<=1:return error ("object issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   #logic
   if not queue:
      response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
      if response["status"]==0:return error(response["message"])
      output=response["message"]
   elif queue=="redis":output=await redis_client.publish(channel_name,json.dumps(data))
   elif queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
   elif queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
   elif queue=="kafka":output=await kafka_producer_client.send_and_wait(channel_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   elif "mongodb" in queue:
      mongodb_database_name=queue.split('_')[1]
      mongodb_database_client=mongodb_client[mongodb_database_name]
      output=await mongodb_database_client[table].insert_many([object])
      output=str(output)
   #final
   return {"status":1,"message":output}

@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=dict(request.query_params)
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #check
   if table in ["users"]:return error("table not allowed")
   #logic
   response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   object_list=response["message"]
   #final
   return {"status":1,"message":object_list}

@app.put("/my/user-update")
async def my_user_update(request:Request):
   #param
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   otp=int(request.query_params.get("otp",0))
   #check
   if "id" not in object:return error ("id missing")
   if object["id"]!=request.state.user["id"]:return error ("wrong id")
   if len(object)<=2:return error ("object length issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   if any(key in object and len(object)!=3 for key in ["password","email","mobile"]):return error("object length should be 2")
   if any(key in object and not otp for key in ["email","mobile"]):return error("otp missing")
   #otp verify
   if otp:
      email,mobile=object.get("email"),object.get("mobile")
      response=await verify_otp(postgres_client,otp,email,mobile)
      if response["status"]==0:return error(response["message"])
   #logic
   response=await postgres_update("users",[object],1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/my/object-update")
async def my_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   if not table:return error("table missing")
   #check
   if table in ["users"]:return error("table not allowed")
   if "id" not in object:return error ("id missing")
   if len(object)<=2:return error ("object null issue")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   #logic
   response=await postgres_update_self(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize,request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/my/ids-update")
async def my_ids_update(request:Request):
   #param
   table=request.query_params.get("table")
   ids=request.query_params.get("ids")
   if not table or not ids:return error("table/ids must")
   object=await request.json()
   key,value=next(reversed(object.items()),(None, None))
   #check
   if table in ["users"]:return error("table not allowed")
   if any(key in column_disabled_non_admin for key in object):return error(" object key not allowed")
   if len(object)!=1:return error(" object length should be 1")
   #logic
   query=f"update {table} set {key}=:value,updated_by_id=:updated_by_id where id in ({ids}) and created_by_id=:created_by_id;"
   values={"created_by_id":request.state.user["id"],"updated_by_id":request.state.user["id"],"value":object.get(key)}
   await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/object-delete-any")
async def my_object_delete_any(request:Request):
   #param
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=dict(request.query_params)
   object["created_by_id"]=f"=,{request.state.user['id']}"
   #check
   if table not in ["test","report_user","bookmark_workseeker"]:return error("table not allowed")
   #create where
   response=await create_where_string(object,object_serialize,postgres_column_datatype)
   if response["status"]==0:return error(response["message"])
   where_string,where_value=response["message"][0],response["message"][1]
   #logic
   query=f"delete from {table} {where_string};"
   await postgres_client.fetch_all(query=query,values=where_value)
   #final
   return {"status":1,"message":"done"}

@app.delete("/my/ids-delete")
async def my_ids_delete(request:Request):
   #param
   table=request.query_params.get("table")
   ids=request.query_params.get("ids")
   if not table or not ids:return error("table/ids must")
   #check
   if table not in ["test","report_user","bookmark_workseeker"]:return error("table not allowed")
   #logic
   query=f"delete from {table} where id in ({ids}) and created_by_id=:created_by_id;"
   values={"created_by_id":request.state.user["id"]}
   await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   table=request.query_params.get("table")
   table_parent=table.split('_',1)[-1]
   column=f"{table_parent}_id"
   if table_parent=="user":table_parent="users"
   if not table:return error("table missing")
   #logic
   query=f'''
   with 
   x as (select {column} from {table} where created_by_id=:created_by_id order by {order} limit {limit} offset {(page-1)*limit}) 
   select ct.* from x left join {table_parent}  as ct on x.{column}=ct.id;
   '''
   values={"created_by_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   #param
   mode=request.query_params.get("mode")
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   #logic
   if not mode:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {(page-1)*limit};'''
   elif mode=="unread":query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {(page-1)*limit};'''
   values={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-received")
async def my_message_received(request:Request,background:BackgroundTasks):
   #param
   mode=request.query_params.get("mode")
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   #logic
   if not mode:query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {(page-1)*limit};"
   elif mode=="unread":query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
   values={"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   #background
   query=f"update message set is_read=1,updated_by_id=:updated_by_id where id in ({','.join([str(item['id']) for item in object_list])});"
   values={"updated_by_id":request.state.user["id"]}
   background.add_task(postgres_client.execute,query,values)
   #final
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request,background:BackgroundTasks):
   #param
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   user_id=int(request.query_params.get("user_id",0))
   if not user_id:return error("user_id missing")
   #logic
   query=f"select * from message where ((created_by_id=:user_1 and user_id=:user_2) or (created_by_id=:user_2 and user_id=:user_1)) order by {order} limit {limit} offset {(page-1)*limit};"
   values={"user_1":request.state.user["id"],"user_2":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   #background
   query="update message set is_read=1,updated_by_id=:updated_by_id where created_by_id=:created_by_id and user_id=:user_id;"
   values={"created_by_id":user_id,"user_id":request.state.user["id"],"updated_by_id":request.state.user["id"]}
   background.add_task(postgres_client.execute,query,values)
   #final
   return {"status":1,"message":object_list}

@app.delete("/my/message-delete")
async def my_message_delete(request:Request):
   #param
   mode=request.query_params.get("mode")
   id=int(request.query_params.get("id",0))
   if not mode:return error("mode missing")
   if mode=="single" and not id:return error("id missing")
   #logic
   if mode=="single":output=await postgres_client.execute(query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);",values={"id":int(id),"user_id":request.state.user["id"]})
   if mode=="created":output=await postgres_client.execute(query="delete from message where created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   if mode=="received":output=await postgres_client.execute(query="delete from message where user_id=:user_id;",values={"user_id":request.state.user["id"]})
   if mode=="all":output=await postgres_client.execute(query="delete from message where (created_by_id=:user_id or user_id=:user_id);",values={"user_id":request.state.user["id"]})
   #final
   return {"status":1,"message":output}

#public
output_cache_public_info={}
@app.get("/public/info")
async def public_info(request:Request):
   #param
   global output_cache_public_info
   #logic
   if output_cache_public_info and (time.time()-output_cache_public_info.get("set_at")<=100):output=output_cache_public_info.get("output")
   else:
      output={
      "set_at":time.time(),
      "postgres_schema":postgres_schema,
      "postgres_column_datatype":postgres_column_datatype,
      "api_list":[route.path for route in request.app.routes],
      "users_api_access_count":len(users_api_access),
      "users_is_active_count":len(users_is_active),
      "redis":await redis_client.info(),
      "api_id":api_id,
      "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals().items() if not name.startswith("__")}.items(), key=lambda item:item[1], reverse=True)),
      "users_count":await postgres_client.fetch_all(query="select count(*) from users where is_active is distinct from 0;",values={}),
      }
      output_cache_public_info["set_at"]=time.time()
      output_cache_public_info["output"]=output
   #final
   return {"status":1,"message":output}

@app.post("/public/otp-send-mobile-sns")
async def public_otp_send_mobile_sns(request:Request):
   #param
   object=await request.json()
   mobile=object.get("mobile")
   entity_id=object.get("entity_id")
   sender_id=object.get("sender_id")
   template_id=object.get("template_id")
   message=object.get("message")
   if not mobile:return error("mobile missing")
   #otp save
   otp=random.randint(100000,999999)
   query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;"
   values={"otp":otp,"mobile":mobile.strip().lower()}
   await postgres_client.execute(query=query,values=values)
   #logic
   if not entity_id:output=sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   else:output=sns_client.publish(PhoneNumber=mobile,Message=message.replace("{otp}",str(otp)),MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   #final
   return {"status":1,"message":output}

@app.post("/public/otp-send-email-ses")
async def public_otp_send_email_ses(request:Request):
   #param
   object=await request.json()
   email=object.get("email")
   if not email:return error("email missing")
   #otp save
   otp=random.randint(100000,999999)
   query="insert into otp (otp,email) values (:otp,:email) returning *;"
   values={"otp":otp,"email":email.strip().lower()}
   await postgres_client.fetch_all(query=query,values=values)
   #logic
   to,title,body=[email],"otp from atom",str(otp)
   ses_client.send_email(Source=ses_sender_email,Destination={"ToAddresses":to},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   #final
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   if not table:return error("table missing")
   object=await request.json()
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/public/object-read")
@cache(expire=100)
async def public_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   creator_data=request.query_params.get("creator_data")
   if not table:return error("table missing")
   object=request.query_params
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   if postgres_client_read:response=await postgres_read(table,object,postgres_client_read,postgres_column_datatype,object_serialize,create_where_string)
   else:response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   object_list=response["message"]
   #add creator data
   if creator_data:
      response=await add_creator_data(postgres_client,object_list,creator_data)
      if response["status"]==0:return response
      object_list=response["message"]
   #final
   return {"status":1,"message":object_list}

#private
@app.post("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(request:Request):
   #param
   bucket=request.query_params.get("bucket")
   key=request.query_params.get("key")
   if not bucket or not key:return error("bucket/key missing")
   expiry_sec,size_kb=1000,100
   #check
   if "." not in key:return error("extension must")
   #logic
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   #final
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-direct")
async def private_file_upload_s3_direct(request:Request):
   #param
   form_data_key,form_data_file=await form_data_read(request)
   bucket=form_data_key.get("bucket")
   key=form_data_key.get("key")
   if not bucket or not key or not form_data_file:return error("bucket/key/file missing")
   key_list=None if key=="uuid" else key.split("---")
   #logic
   response=await s3_file_upload(s3_client,s3_region_name,bucket,key_list,form_data_file)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/private/object-read")
@cache(expire=100)
async def private_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=request.query_params
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.get("/private/workseeker-read")
@cache(expire=100)
async def private_workseeker_read(request:Request):
   #pagination
   order,limit,page=request.query_params.get("order","id desc"),int(request.query_params.get("limit",100)),int(request.query_params.get("page",1))
   #filter
   work_profile_id=int(request.query_params.get("work_profile_id")) if request.query_params.get("work_profile_id") else None
   experience_min=int(request.query_params.get("experience_min")) if request.query_params.get("experience_min") else None
   experience_max=int(request.query_params.get("experience_max")) if request.query_params.get("experience_max") else None
   skill=f"%{request.query_params.get('skill')}%" if request.query_params.get('skill') else None
   #logic
   query=f'''
   select * from workseeker where
   (work_profile_id=:work_profile_id or :work_profile_id is null) and
   (experience >= :experience_min or :experience_min is null) and
   (experience <= :experience_max or :experience_max is null) and
   (skill ilike :skill or :skill is null)
   order by {order} limit {limit} offset {(page-1)*limit};
   '''
   values={
   "work_profile_id":work_profile_id,
   "experience_min":experience_min,"experience_max":experience_max,
   "skill":skill
   }
   output=await postgres_client.fetch_all(query=query,values=values)
   #final
   return {"status":1,"message":output}

#admin
@app.post("/admin/db-runner")
async def admin_db_runner(request:Request):
   #param
   query=(await request.json()).get("query")
   if not query:return error("query must")
   #check
   danger_word=["drop","truncate"]
   stop_word=["drop","delete","update","insert","alter","truncate","create", "rename","replace","merge","grant","revoke","execute","call","comment","set","disable","enable","lock","unlock"]
   must_word=["select"]
   for item in danger_word:
       if item in query.lower():return error(f"{item} keyword not allowed in query")
   if request.state.user["id"]!=1:
      for item in stop_word:
         if item in query.lower():return error(f"{item} keyword not allowed in query")
      for item in must_word:
         if item not in query.lower():return error(f"{item} keyword must be present in query")
   #logic
   output=await postgres_client.fetch_all(query=query,values={})
   #final
   return {"status":1,"message":output}

@app.post("/admin/user-create")
async def admin_user_create(request:Request):
   #param
   object=await request.json()
   type=object.get("type")
   username=object.get("username")
   password=object.get("password")
   api_access=object.get("api_access")
   if not type or not username or not password:return error("type/username/password missing")
   password=hashlib.sha256(str(password).encode()).hexdigest()
   #check
   if type not in user_type_allowed:return error("wrong type")
   #logic
   query="insert into users (type,username,password,api_access) values (:type,:username,:password,:api_access) returning *;"
   values={"type":type,"username":username,"password":password,"api_access":api_access}
   output=await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":output}

@app.put("/admin/user-update")
async def admin_user_update(request:Request):
   #param
   object=await request.json()
   object["updated_by_id"]=request.state.user["id"]
   #check
   if "id" not in object:return error ("id missing")
   if len(object)<=2:return error ("object length issue")
   if any(key in object and len(object)!=3 for key in ["password"]):return error("object length should be 2")
   #logic
   response=await postgres_update("users",[object],1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.post("/admin/object-create")
async def admin_object_create(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   if not table:return error("table missing")
   object=await request.json()
   object["created_by_id"]=request.state.user["id"]
   #check
   if table not in ["test"]:return error("table not allowed")
   #logic
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/admin/object-update")
async def admin_object_update(request:Request):
   #param
   table=request.query_params.get("table")
   is_serialize=int(request.query_params.get("is_serialize",1))
   object=await request.json()
   if postgres_schema.get(table).get("updated_by_id"):object["updated_by_id"]=request.state.user["id"]
   if not table:return error("table missing")
   #check
   if table in ["users"]:return error("table not allowed")
   if len(object)<=2:return error ("object issue")
   if "id" not in object:return error ("id missing")
   #logic
   response=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/admin/ids-update")
async def admin_ids_update(request:Request):
   #param
   table=request.query_params.get("table")
   ids=request.query_params.get("ids")
   if not table or not ids:return error("table/ids must")
   object=await request.json()
   key,value=next(reversed(object.items()),(None, None))
   #check
   if table in ["users"]:return error("table not allowed")
   if len(object)!=1:return error(" object length should be 1")
   #logic
   query=f"update {table} set {key}=:value,updated_by_id=:updated_by_id where id in ({ids});"
   values={"updated_by_id":request.state.user["id"],"value":object.get(key)}
   await postgres_client.execute(query=query,values=values)
   #final
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def admin_ids_delete(request:Request):
   #param
   table=request.query_params.get("table")
   ids=request.query_params.get("ids")
   if not table or not ids:return error("table/ids must")
   #check
   if table in ["users"]:return error("table not allowed")
   #logic
   query=f"delete from {table} where id in ({ids});"
   await postgres_client.execute(query=query,values={})
   #final
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
@cache(expire=60)
async def admin_object_read(request:Request):
   #param
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=request.query_params
   #logic
   response=await postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string)
   if response["status"]==0:return error(response["message"])
   #final
   return response

#mode
import sys
mode=sys.argv

#fastapi
import asyncio,uvicorn
async def main_fastapi():
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info",reload=True)
   server=uvicorn.Server(config)
   await server.serve()
if __name__=="__main__" and len(mode)==1:
   try:asyncio.run(main_fastapi())
   except KeyboardInterrupt:print("exit")
   
#nest
import nest_asyncio
nest_asyncio.apply()

#redis
import asyncio,json
async def main_redis():
   postgres_client=await client_postgres(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   await set_redis_client(redis_url,valkey_url,channel_name)
   try:
      async for message in redis_pubsub.listen():
         if message["type"]=="message" and message["channel"]==b'ch1':
            data=json.loads(message['data'])
            try:
               if data["mode"]=="create":response=await postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               if data["mode"]=="update":response=await postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               print(response)
            except Exception as e:
               print(e.args)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await redis_pubsub.unsubscribe("postgres_crud")
      await redis_client.aclose()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="redis":
    try:asyncio.run(main_redis())
    except KeyboardInterrupt:print("exit")

#kafka
import asyncio,json
async def main_kafka():
   postgres_client=await client_postgres(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   await set_kafka_client(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name)
   try:
      async for message in kafka_consumer_client:
         if message.topic==channel_name:
            data=json.loads(message.value.decode('utf-8'))
            try:
               if data["mode"]=="create":response=await postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)   
               if data["mode"]=="update":response=await postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize)
               print(response)
            except Exception as e:
               print(e.args)
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await postgres_client.disconnect()
      await kafka_consumer_client.stop()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="kafka":
    try:asyncio.run(main_kafka())
    except KeyboardInterrupt:print("exit")

#aqmp callback
def aqmp_callback(ch,method,properties,body):
   data=json.loads(body)
   loop=asyncio.get_event_loop()
   try:
      if data["mode"]=="create":response=loop.run_until_complete(postgres_create(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize))
      if data["mode"]=="update":response=loop.run_until_complete(postgres_update(data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_column_datatype,object_serialize))
      print(response)
   except Exception as e:
      print(e.args)
   return None

#rabbitmq
import asyncio,json
async def main_rabbitmq():
   postgres_client=await client_postgres(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   await set_rabbitmq_client(rabbitmq_url,channel_name)
   try:
      rabbitmq_channel.basic_consume(channel_name,aqmp_callback,auto_ack=True)
      rabbitmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      rabbitmq_channel.close()
      rabbitmq_client.close()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="rabbitmq":
    try:asyncio.run(main_rabbitmq())
    except KeyboardInterrupt:print("exit")

#lavinmq
import asyncio,json
async def main_lavinmq():
   postgres_client=await client_postgres(postgres_url)
   postgres_column_datatype=await postgres_column_datatype_read(postgres_client,postgres_schema_read)
   await set_lavinmq_client(lavinmq_url,channel_name)
   try:
      lavinmq_channel.basic_consume(channel_name,aqmp_callback,auto_ack=True)
      lavinmq_channel.start_consuming()
   except KeyboardInterrupt:
      await postgres_client.disconnect()
      lavinmq_channel.close()
      lavinmq_client.close()
if __name__ == "__main__" and len(mode)>1 and mode[1]=="lavinmq":
    try:asyncio.run(main_lavinmq())
    except KeyboardInterrupt:print("exit")