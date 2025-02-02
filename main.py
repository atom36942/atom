#function
from function import *

#env
import os
from dotenv import load_dotenv
load_dotenv()
postgres_database_url=os.getenv("postgres_database_url")
redis_server_url=os.getenv("redis_server_url")
key_root=os.getenv("key_root")
key_jwt=os.getenv("key_jwt")
sentry_dsn=os.getenv("sentry_dsn")
rabbitmq_server_url=os.getenv("rabbitmq_server_url")
lavinmq_server_url=os.getenv("lavinmq_server_url")
kafka_path_cafile=os.getenv("kafka_path_cafile")
kafka_path_certfile=os.getenv("kafka_path_certfile")
kafka_path_keyfile=os.getenv("kafka_path_keyfile")
kafka_server_url=os.getenv("kafka_server_url")
aws_access_key_id=os.getenv("aws_access_key_id")
aws_secret_access_key=os.getenv("aws_secret_access_key")
s3_region_name=os.getenv("s3_region_name")
sns_region_name=os.getenv("sns_region_name")
sns_region_name=os.getenv("sns_region_name")
ses_region_name=os.getenv("ses_region_name")
mongodb_cluster_url=os.getenv("mongodb_cluster_url")

#globals
object_list_log=[]
channel_name="ch1"
postgres_config_default={
"table":{
"atom":["type-text-1-btree","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0","parent_table-text-0-btree","parent_id-bigint-0-btree"],
"project":["type-text-1-btree","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0"],
"users":["created_at-timestamptz-1-brin","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","is_active-smallint-0-btree","is_protected-smallint-0-btree","type-text-0-btree","username-text-0-0","password-text-0-btree","location-geography(POINT)-0-gist","metadata-jsonb-0-0","google_id-text-0-btree","last_active_at-timestamptz-0-0","date_of_birth-date-0-0","email-text-0-btree","mobile-text-0-btree","name-text-0-0","city-text-0-0"],
"post":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","updated_at-timestamptz-0-0","updated_by_id-bigint-0-0","type-text-0-0","title-text-0-0","description-text-0-0","file_url-text-0-0","link_url-text-0-0","tag-text-0-0","location-geography(POINT)-0-0","metadata-jsonb-0-0","is_protected-smallint-0-btree"],
"message":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","user_id-bigint-1-btree","description-text-1-0","is_read-smallint-0-btree"],
"helpdesk":["created_at-timestamptz-1-0","created_by_id-bigint-0-0","status-text-0-0","remark-text-0-0","type-text-0-0","description-text-1-0","email-text-0-btree"],
"otp":["created_at-timestamptz-1-brin","otp-integer-1-0","email-text-0-btree","mobile-text-0-btree"],
"log_api":["created_at-timestamptz-1-0","created_by_id-bigint-0-0","api-text-0-0","status_code-smallint-0-0","response_time_ms-numeric(1000,3)-0-0"],
"log_password":["created_at-timestamptz-1-0","user_id-bigint-0-0","password-text-0-0"],
"action_like":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_bookmark":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_report":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_block":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_follow":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree"],
"action_rating":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","rating-numeric(10,3)-1-0"],
"action_comment":["created_at-timestamptz-1-0","created_by_id-bigint-1-btree","parent_table-text-1-btree","parent_id-bigint-1-btree","description-text-1-0"],
"human":["created_at-timestamptz-1-0","type-text-0-btree","name-text-0-0","email-text-0-0","mobile-text-0-0","city-text-0-0","experience-numeric(10,1)-0-0","link_url-text-0-0","work_profile-text-0-0","skill-text-0-0","description-text-0-0","file_url-text-0-0"],
},
"query":{
"unique_users_username":"alter table users add constraint constraint_unique_users_username unique (username);",
"unique_acton_like":"alter table action_like add constraint constraint_unique_action_like_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_bookmark":"alter table action_bookmark add constraint constraint_unique_action_bookmark_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_report":"alter table action_report add constraint constraint_unique_action_report_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_block":"alter table action_block add constraint constraint_unique_action_block_cpp unique (created_by_id,parent_table,parent_id);",
"unique_acton_follow":"alter table action_follow add constraint constraint_unique_action_follow_cpp unique (created_by_id,parent_table,parent_id);",
}
}

#setters
postgres_client=None
from databases import Database
async def set_postgres_client():
   global postgres_client
   postgres_client=Database(os.getenv("postgres_database_url"),min_size=1,max_size=100)
   await postgres_client.connect()
   return None

postgres_schema={}
postgres_column_datatype={}
async def set_postgres_schema():
   global postgres_schema
   global postgres_column_datatype
   postgres_schema=await postgres_schema_read(postgres_client)
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return None

users_type_ids={}
async def set_users_type_ids():
   global users_type_ids
   users_type_ids={}
   if postgres_schema.get("users",{}).get("type",None):
      for type in ["admin"]:
         users_type_ids[type]=[]
         output=await postgres_client.fetch_all(query="select id from users where type=:type limit 10000",values={"type":type})
         for object in output:users_type_ids[type]+=[object["id"]]
   return None

project_data={}
async def set_project_data():
   global project_data
   project_data={}
   if postgres_schema.get("project",None):
      output=await postgres_client.fetch_all(query="select * from project limit 10000;",values={})
      for object in output:
         if object["type"] not in project_data:project_data[object["type"]]=[object]
         else:project_data[object["type"]]+=[object]
   return None

redis_client=None
redis_pubsub=None
import redis.asyncio as redis
async def set_redis_client():
   global redis_client
   global redis_pubsub
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.subscribe(channel_name)
   return None

mongodb_client=None
import motor.motor_asyncio
async def set_mongodb_client():
   global mongodb_client
   if mongodb_cluster_url:mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(mongodb_cluster_url)
   return None

s3_client=None
s3_resource=None
import boto3
async def set_s3_client():
   global s3_client,s3_resource
   if s3_region_name:
      s3_client=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
      s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

sns_client=None
import boto3
async def set_sns_client():
   global sns_client
   if sns_region_name:
      sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

ses_client=None
import boto3
async def set_ses_client():
   global ses_client
   if ses_region_name:
      ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return None

rabbitmq_client=None
rabbitmq_channel=None
import pika
async def set_rabbitmq_client():
   global rabbitmq_client
   global rabbitmq_channel
   if rabbitmq_server_url:
      rabbitmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("rabbitmq_server_url")))
      rabbitmq_channel=rabbitmq_client.channel()
      rabbitmq_channel.queue_declare(queue=channel_name)
   return None

lavinmq_client=None
lavinmq_channel=None
import pika
async def set_lavinmq_client():
   global lavinmq_client
   global lavinmq_channel
   if lavinmq_server_url:
      lavinmq_client=pika.BlockingConnection(pika.URLParameters(os.getenv("lavinmq_server_url")))
      lavinmq_channel=lavinmq_client.channel()
      lavinmq_channel.queue_declare(queue=channel_name)
   return None

kafka_producer_client=None
kafka_consumer_client=None
from aiokafka import AIOKafkaProducer
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def set_kafka_client():
   global kafka_producer_client
   global kafka_consumer_client
   if kafka_server_url:
      context=create_ssl_context(cafile=os.getenv("kafka_path_cafile"),certfile=os.getenv("kafka_path_certfile"),keyfile=os.getenv("kafka_path_keyfile"))
      kafka_producer_client=AIOKafkaProducer(bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context)
      kafka_consumer_client=AIOKafkaConsumer(channel_name,bootstrap_servers=os.getenv("kafka_server_url"),security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
      await kafka_producer_client.start()
      await kafka_consumer_client.start()
   return None

#sentry
import sentry_sdk
if sentry_dsn:
   sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

#redis key builder
from fastapi import Request,Response
import jwt,json
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   user_id=0
   if token and "root/" not in api:user_id=json.loads(jwt.decode(token,os.getenv("key_jwt"),algorithms="HS256")["data"])["id"]
   key=f"{api}---{query_param}---{str(user_id)}"
   return key

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
@asynccontextmanager
async def lifespan(app:FastAPI):
   await set_postgres_client()
   await set_postgres_schema()
   await set_users_type_ids()
   await set_project_data()
   await set_redis_client()
   await set_s3_client()
   await set_sns_client()
   await set_ses_client()
   await set_mongodb_client()
   await set_rabbitmq_client()
   await set_lavinmq_client()
   await set_kafka_client()
   await FastAPILimiter.init(redis_client)
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   yield
   try:
      await postgres_client.disconnect()
      await redis_client.aclose()
      if rabbitmq_server_url and rabbitmq_channel.is_open:rabbitmq_channel.close()
      if rabbitmq_client.is_open:rabbitmq_client.close()
      if lavinmq_server_url and lavinmq_channel.is_open:lavinmq_channel.close()
      if lavinmq_client.is_open:lavinmq_client.close()
      if kafka_server_url:await kafka_producer_client.stop()
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
@app.middleware("http")
async def middleware(request:Request,api_function):
   start=time.time()
   api=request.url.path
   method=request.method
   query_param=dict(request.query_params)
   body=await request.body()
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   print(method,api,request.headers,query_param,body)
   try:
      #auth
      user={}
      if any(item in api for item in ["root/","my/", "private/", "admin/"]) and not token:return error("token must")
      if token:
         if "root/" in api:
            if token!=key_root:return error("root key mismatch")
         else:
            user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
            if not user.get("id",None):return error("user_id not in token")
            if "admin/" in api and user["id"] not in users_type_ids.get("admin",[]):return error("only admin allowed")
      request.state.user=user
      #api response background
      if query_param.get("is_background",None)=="1":
         async def receive():return {"type":"http.request","body":body}
         async def api_function_new():
            request_new=Request(scope=request.scope,receive=receive)
            await api_function(request_new)
         response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
         response.background=BackgroundTask(api_function_new)
      #api response direct
      else:
         response=await api_function(request)
         #api log
         if postgres_schema.get("log_api",None):
            global object_list_log
            object={"created_by_id":user.get("id",None),"api":api,"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000}
            object_list_log.append(object)
            if len(object_list_log)>=3:
               response.background=BackgroundTask(postgres_create,"log_api",object_list_log,0,postgres_client,postgres_column_datatype,object_serialize)
               object_list_log=[]
   #exception
   except Exception as e:
      print(traceback.format_exc())
      return error(str(e.args))
   #final
   return response

#router
import os,glob
current_directory_path=os.path.dirname(os.path.realpath(__file__))
current_directory_file_path_list=glob.glob(f"{current_directory_path}/*")
current_directory_file_name_list=[item.rsplit("/",1)[-1] for item in current_directory_file_path_list]
current_directory_file_name_list_without_extension=[item.split(".")[0] for item in current_directory_file_name_list]
for item in current_directory_file_name_list_without_extension:
   if "api_" in item:
      router=__import__(item).router
      app.include_router(router)
      
#api import
from fastapi import Request,UploadFile,Depends,BackgroundTasks
import hashlib,datetime,json,time,jwt,os,random
from typing import Literal
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter
import fitz

#api
@app.get("/")
async def root():
   return {"status":1,"message":"welcome to atom"}
   
@app.post("/root/schema-init-default")
async def root_schema_init_default():
   await postgres_schema_init(postgres_client,postgres_schema_read,postgres_config_default)
   await postgres_schema_init_auto(postgres_client,postgres_schema_read)
   return {"status":1,"message":"done"}

@app.post("/root/schema-init-custom")
async def root_schema_init_custom(request:Request):
   body_json=await request.json()
   if not body_json:return error("body missing")
   await postgres_schema_init(postgres_client,postgres_schema_read,body_json)
   await postgres_schema_init_auto(postgres_client,postgres_schema_read)
   return {"status":1,"message":"done"}

@app.get("/root/info")
async def root_info(request:Request):
   globals_dict=globals()
   output={
   "users_type_ids":users_type_ids,
   "project_data":project_data,
   "postgres_schema":postgres_schema,
   "api_list":[route.path for route in request.app.routes],
   "api_count":len([route.path for route in request.app.routes]),
   "redis":await redis_client.info(),
   "variable_size_kb":dict(sorted({f"{name} ({type(var).__name__})":sys.getsizeof(var) / 1024 for name, var in globals_dict.items() if not name.startswith("__")}.items(), key=lambda item: item[1], reverse=True))
   }
   return {"status":1,"message":output}

@app.put("/root/reset-global")
async def root_reset_global():
   await set_postgres_schema()
   await set_project_data()
   await set_users_type_ids()
   return {"status":1,"message":"done"}

@app.put("/root/reset-redis")
async def root_reset_redis():
   await redis_client.flushall()
   return {"status":1,"message":"done"}

@app.delete("/root/db-clean")
async def root_db_clean():
   response=await postgres_clean_creator(postgres_client,postgres_schema_read)
   if response["status"]==0:return error(response["message"])
   response=await postgres_clean_parent(postgres_client,postgres_schema_read)
   if response["status"]==0:return error(response["message"])
   await postgres_client.execute(query="truncate table log_api;",values={})
   return {"status":1,"message":"done"}

@app.put("/root/db-checklist")
async def root_db_checklist():
   await postgres_client.execute(query="update users set is_protected=1 where type='admin';",values={})
   return {"status":1,"message":"done"}

@app.post("/root/query-runner")
async def root_query_runner(request:Request):
   body_json=await request.json()
   query=body_json.get("query",None)
   if not query:return error("body json query missing")
   query_value_list=[]
   for query in query.split("---"):query_value_list.append([query,{}])
   response=await postgres_transaction(postgres_client,query_value_list)
   if response["status"]==0:return error(response["message"])
   return response

@app.post("/root/csv-uploader")
async def root_csv_uploader(request:Request):
   body_form=await request.form()
   mode,table=body_form.get("mode"),body_form.get("table")
   file_list=[file for file in body_form.getlist("file") if file.filename]
   if not file_list:return error("body form file missing")
   if not mode or not table:return error("body form mode/table missing")
   object_list=await file_to_object_list(file_list[-1])
   if mode=="create":response=await postgres_create(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="update":response=await postgres_update(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if mode=="delete":response=await postgres_delete(table,object_list,1,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/root/s3-bucket-list")
async def root_s3_bucket_list():
   output=s3_client.list_buckets()
   return {"status":1,"message":output}

@app.post("/root/s3-bucket-create")
async def root_s3_bucket_create(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   return {"status":1,"message":output}

@app.put("/root/s3-bucket-public")
async def root_s3_bucket_public(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal": "*","Action": "s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return {"status":1,"message":output}

@app.delete("/root/s3-bucket-empty")
async def root_s3_bucket_empty(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   output=s3_resource.Bucket(bucket).objects.all().delete()
   return {"status":1,"message":output}

@app.delete("/root/s3-bucket-delete")
async def root_s3_bucket_empty(request:Request):
   body_json=await request.json()
   bucket=body_json.get("bucket",None)
   if not bucket:return error("body json bucket missing")
   output=s3_client.delete_bucket(Bucket=bucket)
   return {"status":1,"message":output}

@app.delete("/root/s3-url-delete")
async def root_s3_url_empty(request:Request):
   body_json=await request.json()
   url=body_json.get("url",None)
   if not url:return error("body json url missing")
   for item in url.split("---"):
      bucket,key=item.split("//",1)[1].split(".",1)[0],item.rsplit("/",1)[1]
      output=s3_resource.Object(bucket,key).delete()
   return {"status":1,"message":output}

@app.post("/root/redis-set-object")
async def root_redis_set_object(request:Request):
   body_json=await request.json()
   expiry,key,object=body_json.get("expiry",None),body_json.get("key",None),body_json.get("object",None)
   if not key or not object:return error("body json key/object missing")
   object=json.dumps(object)
   if expiry:output=await redis_client.setex(key,expiry,object)
   else:output=await redis_client.set(key,object)
   return {"status":1,"message":output}

@app.post("/root/redis-set-csv")
async def root_redis_set_csv(request:Request):
   body_form=await request.form()
   table,expiry=body_form.get("table"),body_form.get("expiry")
   file_list=[file for file in body_form.getlist("file") if file.filename]
   if not file_list:return error("body form file missing")
   if not table:return error("body form table missing")
   object_list=await file_to_object_list(file_list[-1])
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if expiry:pipe.setex(key,expiry,json.dumps(object))
         else:pipe.set(key,json.dumps(object))
      await pipe.execute()
   return {"status":1,"message":"done"}

@app.post("/auth/signup",dependencies=[Depends(RateLimiter(times=1,seconds=3))])
async def auth_signup(request:Request):
   body_json=await request.json()
   username,password=body_json.get("username",None),body_json.get("password",None)
   if not username or not password:return error("body json username/password missing")
   query="insert into users (username,password) values (:username,:password) returning *;"
   query_param={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()}
   output=await postgres_client.execute(query=query,values=query_param)
   return {"status":1,"message":output}

@app.post("/auth/login")
async def auth_login(request:Request):
   body_json=await request.json()
   username,password=body_json.get("username",None),body_json.get("password",None)
   if not username or not password:return error("body json username/password missing")
   output=await postgres_client.fetch_all(query="select id from users where username=:username and password=:password order by id desc limit 1;",values={"username":username,"password":hashlib.sha256(password.encode()).hexdigest()})
   if not output:return error("no user")
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-google")
async def auth_login_google(request:Request):
   body_json=await request.json()
   google_id=body_json.get("google_id",None)
   if not google_id:return error("body json google_id missing")
   output=await postgres_client.fetch_all(query="select id from users where google_id=:google_id order by id desc limit 1;",values={"google_id":hashlib.sha256(google_id.encode()).hexdigest()})
   if not output:output=await postgres_client.fetch_all(query="insert into users (google_id) values (:google_id) returning *;",values={"google_id":hashlib.sha256(google_id.encode()).hexdigest()})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-email")
async def auth_login_otp_email(request:Request):
   body_json=await request.json()
   email,otp=body_json.get("email",None),body_json.get("otp",None)
   if not email or not otp:return error("body json email/otp missing")
   response=await verify_otp(postgres_client,otp,email,None)
   if response["status"]==0:return error(response["message"])
   output=await postgres_client.fetch_all(query="select id from users where email=:email order by id desc limit 1;",values={"email":email})
   if not output:output=await postgres_client.fetch_all(query="insert into users (email) values (:email) returning *;",values={"email":email})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-otp-mobile")
async def auth_login_otp_mobile(request:Request):
   body_json=await request.json()
   mobile,otp=body_json.get("mobile",None),body_json.get("otp",None)
   if not mobile or not otp:return error("body json mobile/otp missing")
   response=await verify_otp(postgres_client,otp,None,mobile)
   if response["status"]==0:return error(response["message"])
   output=await postgres_client.fetch_all(query="select id from users where mobile=:mobile order by id desc limit 1;",values={"mobile":mobile})
   if not output:output=await postgres_client.fetch_all(query="insert into users (mobile) values (:mobile) returning *;",values={"mobile":mobile})
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-password-email")
async def auth_login_password_email(request:Request):
   body_json=await request.json()
   email,password=body_json.get("email",None),body_json.get("password",None)
   if not email or not password:return error("body json email/password missing")
   output=await postgres_client.fetch_all(query="select * from users where email=:email and password=:password order by id desc limit 1;",values={"email":email,"password":hashlib.sha256(password.encode()).hexdigest()})
   if not output:return error("no user")
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.post("/auth/login-password-mobile")
async def auth_login_password_mobile(request:Request):
   body_json=await request.json()
   mobile,password=body_json.get("mobile",None),body_json.get("password",None)
   if not mobile or not password:return error("body json mobile/password missing")
   output=await postgres_client.fetch_all(query="select * from users where mobile=:mobile and password=:password order by id desc limit 1;",values={"mobile":mobile,"password":hashlib.sha256(password.encode()).hexdigest()})
   if not output:return error("no user")
   user=output[0] if output else None
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/my/profile")
async def my_profile(request:Request,background:BackgroundTasks):
   user=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   background.add_task(postgres_client.execute,query="update users set last_active_at=:last_active_at where id=:id",values={"id":request.state.user["id"],"last_active_at":datetime.datetime.now()})
   return {"status":1,"message":user[0]}

@app.get("/my/token-refresh")
async def my_token_refresh(request:Request):
   token=jwt.encode({"exp":time.time()+1000000000000,"data":json.dumps({"id":request.state.user["id"]},default=str)},key_jwt)
   return {"status":1,"message":token}

@app.get("/my/message-inbox")
async def my_message_inbox(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   mode=query_param.get("mode",None)
   query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {(page-1)*limit};'''
   if mode=="unread":query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {(page-1)*limit};'''
   query_param={"created_by_id":request.state.user["id"],"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/message-received")
async def my_message_received(request:Request,background:BackgroundTasks):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   mode=query_param.get("mode",None)
   query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {(page-1)*limit};"
   if mode=="unread":query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   background.add_task(postgres_client.execute,query=f"update message set is_read=1 where id in ({','.join([str(item['id']) for item in object_list])});",values={})
   return {"status":1,"message":object_list}

@app.get("/my/message-thread")
async def my_message_thread(request:Request,background:BackgroundTasks):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   user_id=query_param.get("user_id",None)
   if not user_id:return error("query param user_id missing")
   user_id=int(user_id)
   query=f"select * from message where ((created_by_id=:user_1 and user_id=:user_2) or (created_by_id=:user_2 and user_id=:user_1)) order by {order} limit {limit} offset {(page-1)*limit};"
   query_param={"user_1":request.state.user["id"],"user_2":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   background.add_task(postgres_client.execute,query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;",values={"created_by_id":user_id,"user_id":request.state.user["id"]})
   return {"status":1,"message":object_list}

@app.get("/my/parent-read")
async def my_parent_read(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   table,parent_table=query_param.get("table",None),query_param.get("parent_table",None)
   if not table or not parent_table:return error("query param table/parent_table missing")
   query=f'''with x as (select parent_id from {table} where created_by_id=:created_by_id and parent_table=:parent_table order by {order} limit {limit} offset {(page-1)*limit}) select pt.* from x left join {parent_table} as pt on x.parent_id=pt.id;'''
   query_param={"created_by_id":request.state.user["id"],"parent_table":parent_table}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/parent-check")
async def my_parent_check(request:Request):
   query_param=dict(request.query_params)
   table,parent_table,parent_ids=query_param.get("table",None),query_param.get("parent_table",None),query_param.get("parent_ids",None)
   if not table or not parent_table or not parent_ids:return error("query param table/parent_table/parent_ids missing")
   query=f"select parent_id from {table} where parent_id in ({parent_ids}) and parent_table=:parent_table and created_by_id=:created_by_id;"
   query_param={"parent_table":parent_table,"created_by_id":request.state.user["id"]}
   output=await postgres_client.fetch_all(query=query,values=query_param)
   parent_ids_output=[item["parent_id"] for item in output if item["parent_id"]]
   parent_ids_input=parent_ids.split(",")
   parent_ids_input=[int(item) for item in parent_ids_input]
   output={item:1 if item in parent_ids_output else 0 for item in parent_ids_input}
   return {"status":1,"message":output}

@app.delete("/my/parent-delete")
async def my_parent_delete(request:Request):
   query_param=dict(request.query_params)
   table,parent_table,parent_id=query_param.get("table",None),query_param.get("parent_table",None),query_param.get("parent_id",None)
   if not table or not parent_table or not parent_id:return error("query param table/parent_table/parent_id missing")
   parent_id=int(parent_id)
   await postgres_client.fetch_all(query=f"delete from {table} where created_by_id=:created_by_id and parent_table=:parent_table and parent_id=:parent_id;",values={"created_by_id":request.state.user["id"],"parent_table":parent_table,"parent_id":parent_id})
   return {"status":1,"message":"done"}

@app.get("/my/action-on-me-creator-read")
async def my_action_on_me_creator_read(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   query=f'''with x as (select * from {table} where parent_table=:parent_table),y as (select created_by_id from x where parent_id=:parent_id group by created_by_id order by max(id) desc limit {limit} offset {(page-1)*limit}) select u.id,u.username from y left join users as u on y.created_by_id=u.id;'''
   query_param={"parent_table":"users","parent_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}

@app.get("/my/action-on-me-creator-read-mutual")
async def my_action_on_me_creator_read_mutual(request:Request):
   query_param=dict(request.query_params)
   order,limit,page=query_param.get("order","id desc"),int(query_param.get("limit",100)),int(query_param.get("page",1))
   table=query_param.get("table",None)
   if not table:return error("query param table missing")
   query=f'''with x as (select * from {table} where parent_table=:parent_table),y as (select created_by_id from {table} where created_by_id in (select parent_id from x where created_by_id=:created_by_id) and parent_id=:parent_id group by created_by_id order by max(id) desc limit {limit} offset {(page-1)*limit}) select u.id,u.username from y left join users as u on y.created_by_id=u.id;'''
   query_param={"parent_table":"users","parent_id":request.state.user["id"],"created_by_id":request.state.user["id"]}
   object_list=await postgres_client.fetch_all(query=query,values=query_param)
   return {"status":1,"message":object_list}






















@app.post("/my/object-create")
async def my_object_create(request:Request,table:str,is_serialize:int=0,queue:str=None):
   object=await request.json()
   object={k:v for k,v in object.items() if v}
   if any(k in ["id","created_at","updated_at","updated_by_id","is_active","is_verified","is_deleted","password","google_id","otp"] for k in object):return responses.JSONResponse(status_code=400,content={"status":0,"message":"key denied"})
   object["created_by_id"]=request.state.user["id"]
   if not queue:
      response=await postgres_crud("create",table,[object],is_serialize,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
      if response["status"]==0:return error(response["message"])
      output=response["message"]
   if queue:
      data={"mode":"create","table":table,"object":object,"is_serialize":is_serialize}
      if queue=="redis":output=await redis_client.publish(channel_name,json.dumps(data))
      if queue=="rabbitmq":output=rabbitmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
      if queue=="lavinmq":output=lavinmq_channel.basic_publish(exchange='',routing_key=channel_name,body=json.dumps(data))
      if queue=="kafka":output=await kafka_producer_client.send_and_wait(channel_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
      if "mongodb" in queue:
         mongodb_database_name=queue.split("_")[1]
         mongodb_database_client=mongodb_client[mongodb_database_name]
         output=await mongodb_database_client[table].insert_many([object])
         output=str(output)
   return {"status":1,"message":output}

@app.put("/my/object-update")
async def my_object_update(request:Request,table:str,otp:int=None):
   object=await request.json()
   if any(k in ["created_at","created_by_id","is_active","is_verified","type","google_id","otp"] for k in object):return responses.JSONResponse(status_code=400,content={"status":0,"message":f"key denied"})      
   if postgres_schema.get(table,{}).get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   response=await ownership_check(postgres_client,table,int(object["id"]),request.state.user["id"])
   if response["status"]==0:return error(response["message"])
   email,mobile=object.get("email",None),object.get("mobile",None)
   if table=="users" and (email or mobile):
      response=await verify_otp(postgres_client,otp,email,mobile)
      if response["status"]==0:return error(response["message"])
   response=await postgres_crud("update",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   output=response["message"]
   return {"status":1,"message":output}

@app.get("/my/object-read")
@cache(expire=60)
async def my_object_read(request:Request,table:str):
   object=dict(request.query_params)
   object["created_by_id"]=f"=,{request.state.user['id']}"
   response=await postgres_crud("read",table,[object],0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/my/message-delete-single")
async def my_message_delete_single(request:Request,id:int):
   await postgres_client.execute(query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);",values={"id":id,"user_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/message-delete-created")
async def my_message_delete_created(request:Request):
   await postgres_client.execute(query="delete from message where created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/message-delete-received")
async def my_message_delete_received(request:Request):
   await postgres_client.execute(query="delete from message where user_id=:user_id;",values={"user_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/message-delete-all")
async def my_message_delete_all(request:Request):
   await postgres_client.execute(query="delete from message where (created_by_id=:user_id or user_id=:user_id);",values={"user_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/delete-ids")
async def my_delete_ids(request:Request,table:str,ids:str):
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if len(ids.split(","))>100:return responses.JSONResponse(status_code=400,content={"status":0,"message":"max 100 ids allowed"})
   await postgres_client.execute(query=f"delete from {table} where id in ({ids}) and created_by_id=:created_by_id;",values={"created_by_id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/delete-account")
async def my_delete_account(request:Request):
   user=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   if user[0]["type"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"user type not allowed"})
   await postgres_client.execute(query="delete from users where id=:id and type is null;",values={"id":request.state.user["id"]})
   return {"status":1,"message":"done"}

@app.get("/my/object-delete")
async def my_object_delete(request:Request,table:str):
   user=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":request.state.user["id"]})
   if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
   if user[0]["type"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"user type not allowed"})
   object=dict(request.query_params)
   object["created_by_id"]=f"=,{request.state.user['id']}"
   response=await create_where_string(postgres_column_datatype,object_serialize,object)
   if response["status"]==0:return error(response["message"])
   where_string,where_value=response["message"][0],response["message"][1]
   query=f"delete from {table} {where_string};"
   await postgres_client.fetch_all(query=query,values=where_value)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def public_object_create(request:Request,table:Literal["helpdesk","human"]):
   object=await request.json()
   object={k:v for k,v in object.items() if v}
   response=await postgres_crud("create",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   return response

@app.post("/public/object-create-form")
async def public_object_create_form(request:Request,table:Literal["helpdesk","human"],bucket:str=None,file_column:str="file_url"):
   form_data=await request.form()
   object={k:v for k,v in form_data.items() if k!="file"}
   file_list=form_data.getlist("file")
   file_list=[file for file in file_list if file.filename]
   if file_list:
      if not bucket:return responses.JSONResponse(status_code=400,content={"status":0,"message":"bucket missing"})
      response=await s3_file_upload(s3_client,s3_region_name,bucket,None,file_list)
      if response["status"]==0:return error(response["message"])
      object[file_column]=",".join([v for k,v in response["message"].items()])
   response=await postgres_crud("create",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   return response

@app.post("/public/object-create-pdf-extract")
async def public_object_create_pdf_extract(request:Request,table:Literal["helpdesk","human"],pdf_column:str="description"):
   form_data=await request.form()
   object={k:v for k,v in form_data.items() if k!="file"}
   file_list=form_data.getlist("file")
   file_list=[file for file in file_list if file.filename]
   text=""
   for file in  file_list:
      if file.content_type!="application/pdf":return responses.JSONResponse(status_code=400,content={"status":0,"message":"wrong file type"})
      pdf_file=await file.read()
      doc=fitz.open(stream=pdf_file,filetype="pdf")
      for page in doc:text+=page.get_text("text")
      object[pdf_column]=text
   response=await postgres_crud("create",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   return response
   
@app.get("/public/object-read")
@cache(expire=60)
async def public_object_read(request:Request,table:str):
   if table not in ["users","post","project","atom"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   object=dict(request.query_params)
   response=await postgres_crud("read",table,[object],0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/public/otp-send-sns")
async def public_otp_send_sns(mobile:str,entity_id:str=None,sender_id:str=None,template_id:str=None,message:str=None):
   otp=random.randint(100000,999999)
   await postgres_client.execute(query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;",values={"otp":otp,"mobile":mobile})
   if not entity_id:output=sns_client.publish(PhoneNumber=mobile,Message=str(otp))
   else:output=sns_client.publish(PhoneNumber=mobile,Message=message.replace("{otp}",str(otp)),MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return {"status":1,"message":output}

@app.get("/public/otp-send-ses")
async def public_otp_send_ses(sender:str,email:str):
   otp=random.randint(100000,999999)
   await postgres_client.fetch_all(query="insert into otp (otp,email) values (:otp,:email) returning *;",values={"otp":otp,"email":email})
   to,title,body=[email],"otp from atom",str(otp)
   ses_client.send_email(Source=sender,Destination={"ToAddresses":to},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return {"status":1,"message":"done"}

@app.get("/public/redis-get-object")
async def public_redis_get_object(key:str):
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return {"status":1,"message":output}

#private
@app.post("/private/file-upload-s3")
async def private_file_upload_s3(bucket:str,key:str,file:list[UploadFile]):
   key_list=None if key=="uuid" else key.split("---")
   response=await s3_file_upload(s3_client,s3_region_name,bucket,key_list,file)
   if response["status"]==0:return error(response["message"])
   return response

@app.get("/private/file-upload-s3-presigned")
async def private_file_upload_s3_presigned(bucket:str,key:str):
   if "." not in key:return responses.JSONResponse(status_code=400,content={"status":0,"message":"extension must"})
   expiry_sec,size_kb=1000,100
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec,Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   return {"status":1,"message":output}

@app.get("/admin/object-read")
async def admin_object_read(request:Request,table:str):
   object=dict(request.query_params)
   response=await postgres_crud("read",table,[object],0,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   return response

@app.put("/admin/object-update")
async def admin_object_update(request:Request,table:str):
   object=await request.json()
   if postgres_schema.get(table,{}).get("updated_by_id",None):object["updated_by_id"]=request.state.user["id"]
   response=await postgres_crud("update",table,[object],1,postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
   if response["status"]==0:return error(response["message"])
   output=response["message"]
   #final
   return {"status":1,"message":output}

@app.get("/admin/delete-ids")
async def admin_delete_ids(table:str,ids:str):
   if table in ["users"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"table not allowed"})
   if len(ids.split(","))>100:return responses.JSONResponse(status_code=400,content={"status":0,"message":"max 100 ids allowed"})
   await postgres_client.execute(query=f"delete from {table} where id in ({ids});",values={})
   return {"status":1,"message":"done"}

@app.get("/admin/query-runner")
async def admin_query_runner(query:str):
  for item in ["insert","update","delete","alter","drop"]:
    if item in query:return responses.JSONResponse(status_code=400,content={"status":0,"message":f"{item} not allowed in query"})
  output=await postgres_client.fetch_all(query=query,values={})
  return {"status":1,"message":output}

#mode
import sys
mode=sys.argv

#fastapi
import asyncio,uvicorn
async def main_fastapi():
   config=uvicorn.Config(app,host="127.0.0.1",port=8000,log_level="info",reload=True)
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_redis_client()
   try:
      async for message in redis_pubsub.listen():
         if message["type"]=="message" and message["channel"]==b'ch1':
            data=json.loads(message['data'])
            try:
               response=await postgres_crud(data["mode"],data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_kafka_client()
   try:
      async for message in kafka_consumer_client:
         if message.topic==channel_name:
            data=json.loads(message.value.decode('utf-8'))
            try:
               response=await postgres_crud(data["mode"],data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count)
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
      response=loop.run_until_complete(postgres_crud(data["mode"],data["table"],[data["object"]],data["is_serialize"],postgres_client,postgres_schema,postgres_column_datatype,object_serialize,create_where_string,add_creator_data,add_action_count))
      print(response)
   except Exception as e:
      print(e.args)
   return None

#rabbitmq
import asyncio,json
async def main_rabbitmq():
   await set_postgres_client()
   await set_postgres_schema()
   await set_rabbitmq_client()
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
   await set_postgres_client()
   await set_postgres_schema()
   await set_lavinmq_client()
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