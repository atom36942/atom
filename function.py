#client
from databases import Database
async def function_client_read_postgres(config_postgres_url,config_postgres_min_connection=5,config_postgres_max_connection=20):
   client_postgres=Database(config_postgres_url,min_size=config_postgres_min_connection,max_size=config_postgres_max_connection)
   await client_postgres.connect()
   return client_postgres

import asyncpg
async def function_client_read_postgres_asyncpg(config_postgres_url):
   client_postgres_asyncpg=await asyncpg.connect(config_postgres_url)
   return client_postgres_asyncpg

import asyncpg
async def function_client_read_postgres_asyncpg_pool(config_postgres_url,config_postgres_min_connection=5,config_postgres_max_connection=20):
   client_postgres_asyncpg_pool=await asyncpg.create_pool(dsn=config_postgres_url,min_size=config_postgres_min_connection,max_size=config_postgres_max_connection)
   return client_postgres_asyncpg_pool

import redis.asyncio as redis
async def function_client_read_redis(config_redis_url):
   client_redis=redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))
   return client_redis

import motor.motor_asyncio
async def function_client_read_mongodb(config_mongodb_url):
   client_mongodb=motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
   return client_mongodb

from posthog import Posthog
async def function_client_read_posthog(config_posthog_project_key,config_posthog_project_host):
   client_posthog=Posthog(config_posthog_project_key,host=config_posthog_project_host)
   return client_posthog

import boto3
async def function_client_read_s3(config_s3_region_name,config_aws_access_key_id,config_aws_secret_access_key):
   client_s3=boto3.client("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   client_s3_resource=boto3.resource("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_s3,client_s3_resource

import boto3
async def function_client_read_sns(config_sns_region_name,config_aws_access_key_id,config_aws_secret_access_key):
   client_sns=boto3.client("sns",region_name=config_sns_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_sns

import boto3
async def function_client_read_ses(config_ses_region_name,config_aws_access_key_id,config_aws_secret_access_key):
   client_ses=boto3.client("ses",region_name=config_ses_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_ses

import gspread
from google.oauth2.service_account import Credentials
async def function_client_read_gsheet(config_gsheet_service_account_json_path,config_gsheet_scope_list):
   client_gsheet=gspread.authorize(Credentials.from_service_account_file(config_gsheet_service_account_json_path,scopes=config_gsheet_scope_list))
   return client_gsheet

from openai import OpenAI
def function_client_read_openai(config_openai_key):
   client_openai=OpenAI(api_key=config_openai_key)
   return client_openai

#celery
from celery import Celery
async def function_client_read_celery_producer(config_celery_broker_url):
   client_celery_producer=Celery("producer",broker=config_celery_broker_url,backend=config_celery_broker_url)
   return client_celery_producer

from celery import Celery
def function_client_read_celery_consumer(config_celery_broker_url):
   client_celery_consumer=Celery("worker",broker=config_celery_broker_url,backend=config_celery_broker_url)
   return client_celery_consumer

async def function_producer_celery(client_celery_producer,function,param_list):
   output=client_celery_producer.send_task(function,args=param_list)
   return output.id

#kafka
from aiokafka import AIOKafkaProducer
async def function_client_read_kafka_producer(config_kafka_url,config_kafka_username,config_kafka_password):
    client_kafka_producer=AIOKafkaProducer(bootstrap_servers=config_kafka_url,security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,)
    await client_kafka_producer.start()
    return client_kafka_producer
 
from aiokafka import AIOKafkaConsumer
async def function_client_read_kafka_consumer(config_kafka_url,config_kafka_username,config_kafka_password,topic_name,group_id,enable_auto_commit):
    client_kafka_consumer=AIOKafkaConsumer(topic_name,bootstrap_servers=config_kafka_url,group_id=group_id, security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,auto_offset_reset="earliest",enable_auto_commit=enable_auto_commit)
    await client_kafka_consumer.start()
    return client_kafka_consumer
 
import json
async def function_producer_kafka(client_kafka_producer,channel_name,payload):
   output=await client_kafka_producer.send_and_wait(channel_name,json.dumps(payload,indent=2).encode('utf-8'),partition=0)
   return output

#rabbitmq
import aio_pika
async def function_client_read_rabbitmq(config_rabbitmq_url):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_channel=await client_rabbitmq.channel()
   return client_rabbitmq,client_rabbitmq_channel

import json,aio_pika
async def function_producer_rabbitmq(client_rabbitmq_channel,channel_name,payload):
   output=await client_rabbitmq_channel.default_exchange.publish(aio_pika.Message(body=json.dumps(payload).encode()),routing_key=channel_name)
   return output

#redis
async def function_client_read_redis_consumer(client_redis,channel_name):
   client_redis_consumer=client_redis.pubsub()
   await client_redis_consumer.subscribe(channel_name)
   return client_redis_consumer

import json
async def function_producer_redis(client_redis,channel_name,payload):
   output=await client_redis.publish(channel_name,json.dumps(payload))
   return output

#fastapi
from fastapi import FastAPI
def function_fastapi_app_read(is_debug,lifespan):
   app=FastAPI(debug=is_debug,lifespan=lifespan)
   return app

import uvicorn
async def function_server_start(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info")
   server=uvicorn.Server(config)
   await server.serve()
   
from fastapi import responses
def function_return_error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})

async def function_param_read(mode,request,must,optional):
   param=[]
   if mode=="query":
      object=dict(request.query_params)
   if mode=="form":
      form_data=await request.form()
      object={key:value for key,value in form_data.items() if isinstance(value,str)}
      file_list=[file for key,value in form_data.items() for file in form_data.getlist(key)  if key not in object and file.filename]
      object["file_list"]=file_list
   if mode=="body":
      object=await request.json()
   for item in must:
      if item not in object:raise Exception(f"{item} missing from {mode} param")
      param.append(object[item])
   for item in optional:
      param.append(object.get(item))
   return object,param

from fastapi.middleware.cors import CORSMiddleware
def function_add_cors(app,cors_origin,cors_method,cors_headers,cors_allow_credentials):
   app.add_middleware(CORSMiddleware,allow_origins=cors_origin,allow_methods=cors_method,allow_headers=cors_headers,allow_credentials=cors_allow_credentials)
   return None

from prometheus_fastapi_instrumentator import Instrumentator
def function_add_prometheus(app):
   Instrumentator().instrument(app).expose(app)
   return None

def function_add_app_state(var_dict,app,prefix_tuple):
    for k, v in var_dict.items():
        if k.startswith(prefix_tuple):
            setattr(app.state, k, v)

import sentry_sdk
def function_add_sentry(config_sentry_dsn):
   sentry_sdk.init(dsn=config_sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)
   return None

import os
import importlib.util
from pathlib import Path
def function_add_router(app,pattern):
   base_dir = Path(__file__).parent
   skip_dirs = {"venv", "__pycache__", ".git", ".mypy_cache"}
   for root, dirs, files in os.walk(base_dir):
      dirs[:] = [d for d in dirs if d not in skip_dirs]
      is_router_folder = os.path.basename(root).startswith(pattern)
      for file in files:
         if file.endswith(".py") and (file.startswith(pattern) or is_router_folder):
            module_path = os.path.join(root, file)
            module_name = os.path.splitext(os.path.relpath(module_path, base_dir))[0].replace(os.sep, ".")
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, pattern):
               app.include_router(module.router)
   return None

#object
async def function_object_create_postgres(client_postgres,table,object_list,is_serialize,function_object_serialize,postgres_column_datatype):
   if is_serialize==1:object_list=await function_object_serialize(object_list,postgres_column_datatype)
   column_insert_list=list(object_list[0].keys())
   query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if len(object_list)==1:
      output=await client_postgres.execute(query=query,values=object_list[0])
   else:
      async with client_postgres.transaction():output=await client_postgres.execute_many(query=query,values=object_list)
   return output

buffer_object_create={}
table_object_key={}
async def function_object_create_postgres_batch(function_object_create_postgres,client_postgres,table,object,config_batch_object_create,is_serialize,function_object_serialize,postgres_column_datatype):
   global buffer_object_create, table_object_key
   if table not in buffer_object_create:
      buffer_object_create[table]=[]
   if table not in table_object_key or table_object_key[table]==[]:
      table_object_key[table]=list(object.keys())
   if list(object.keys())!=table_object_key[table]:raise Exception(f"keys should be {table_object_key[table]}")
   buffer_object_create[table].append(object)
   if len(buffer_object_create[table])>=config_batch_object_create:
      await function_object_create_postgres(client_postgres,table,buffer_object_create[table],is_serialize,function_object_serialize,postgres_column_datatype)
      buffer_object_create[table]=[]
      table_object_key[table]=[]
   return None

async def function_object_create_postgres_asyncpg(client_postgres_asyncpg,table,object_list):
   column_insert_list=list(object_list[0].keys())
   query=f"""INSERT INTO {table} ({','.join(column_insert_list)}) VALUES ({','.join(['$'+str(i+1) for i in range(len(column_insert_list))])}) ON CONFLICT DO NOTHING;"""
   values=[tuple(obj[col] for col in column_insert_list) for obj in object_list]
   await client_postgres_asyncpg.executemany(query,values)
   return None

async def function_object_create_redis(client_redis,key_list,object_list,expiry_sec):
   async with client_redis.pipeline(transaction=True) as pipe:
      for index,object in enumerate(object_list):
         key=key_list[index]
         if not expiry_sec:pipe.set(key,json.dumps(object))
         else:pipe.setex(key,expiry_sec,json.dumps(object))
      await pipe.execute()
   return None

async def function_object_create_gsheet(client_gsheet,spreadsheet_id,sheet_name,object_list):
   for object in object_list:
      row=[object[key] for key in sorted(object.keys())]
      output=client_gsheet.open_by_key(spreadsheet_id).worksheet(sheet_name).append_row(row)
   return output

async def function_object_create_mongodb(client_mongodb,database,table,object_list):
   mongodb_client_database=client_mongodb[database]
   output=await mongodb_client_database[table].insert_many(object_list)
   return str(output)

async def function_object_read_postgres(client_postgres,table,object,function_create_where_string,function_object_serialize,postgres_column_datatype):
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   column=object.get("column","*")
   location_filter=object.get("location_filter")
   if location_filter:
      location_filter_split=location_filter.split(",")
      long,lat,min_meter,max_meter=float(location_filter_split[0]),float(location_filter_split[1]),int(location_filter_split[2]),int(location_filter_split[3])
   where_string,where_value=await function_create_where_string(object,function_object_serialize,postgres_column_datatype)
   if location_filter:query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   else:query=f"select {column} from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   object_list=await client_postgres.fetch_all(query=query,values=where_value)
   return object_list

import json
async def function_object_read_redis(client_redis,key):
   output=await client_redis.get(key)
   if output:output=json.loads(output)
   return output

async def function_object_read_gsheet(client_gsheet,spreadsheet_id,sheet_name,cell_boundary):
   worksheet=client_gsheet.open_by_key(spreadsheet_id).worksheet(sheet_name)
   if cell_boundary:output=worksheet.get(cell_boundary)
   else:output=worksheet.get_all_records()
   return output

import pandas
async def function_object_read_gsheet_pandas(spreadsheet_id,gid):
   url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
   df=pandas.read_csv(url)
   output=df.to_dict(orient="records")
   return output

async def function_object_update_postgres(client_postgres,table,object_list,is_serialize,function_object_serialize,postgres_column_datatype):
   if is_serialize:object_list=await function_object_serialize(object_list,postgres_column_datatype)
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id returning *;"
   if len(object_list)==1:
      output=await client_postgres.execute(query=query,values=object_list[0])
   else:
      async with client_postgres.transaction():output=await client_postgres.execute_many(query=query,values=object_list)
   return output

async def function_object_update_postgres_user(client_postgres,table,object_list,user_id,is_serialize,function_object_serialize,postgres_column_datatype):
   if is_serialize:object_list=await function_object_serialize(object_list,postgres_column_datatype)
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id and created_by_id={user_id} returning *;"
   if len(object_list)==1:
      output=await client_postgres.execute(query=query,values=object_list[0])
   else:
      async with client_postgres.transaction():output=await client_postgres.execute_many(query=query,values=object_list)
   return output

async def function_object_delete_postgres(client_postgres,table,object_list,is_serialize,function_object_serialize,postgres_column_datatype):
   if is_serialize:object_list=await function_object_serialize(object_list,postgres_column_datatype)
   query=f"delete from {table} where id=:id;"
   if len(object_list)==1:
      output=await client_postgres.execute(query=query,values=object_list[0])
   else:
      async with client_postgres.transaction():output=await client_postgres.execute_many(query=query,values=object_list)
   return output

async def function_object_delete_postgres_any(client_postgres,table,object,function_create_where_string,function_object_serialize,postgres_column_datatype):
   where_string,where_value=await function_create_where_string(object,function_object_serialize,postgres_column_datatype)
   query=f"delete from {table} {where_string};"
   await client_postgres.execute(query=query,values=where_value)
   return None

#token
import jwt,json,time
async def function_token_encode(config_key_jwt,config_token_expire_sec,key_list,object):
   data=dict(object)
   payload={k:data.get(k) for k in key_list}
   payload=json.dumps(payload,default=str)
   token=jwt.encode({"exp":time.time()+config_token_expire_sec,"data":payload},config_key_jwt)
   return token

import jwt,json
async def function_token_decode(token,config_key_jwt):
   user=json.loads(jwt.decode(token,config_key_jwt,algorithms="HS256")["data"])
   return user

async def function_token_check(request,config_key_root,config_key_jwt,config_api,function_token_decode):
   user={}
   api=request.url.path
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and request.headers.get("Authorization").startswith("Bearer ") else None
   if api.startswith("/root"):
      if token!=config_key_root:raise Exception("token root mismatch")
   else:
      if token:user=await function_token_decode(token,config_key_jwt)
      if api.startswith("/my") and not token:raise Exception("token missing")
      elif api.startswith("/private") and not token:raise Exception("token missing")
      elif api.startswith("/admin") and not token:raise Exception("token missing")
      elif config_api.get(api,{}).get("is_token")==1 and not token:raise Exception("token missing")
   return user

#middleware
import json
buffer_log_api=[]
async def function_log_create_postgres(function_object_create_postgres,client_postgres,config_batch_log_api,object):
   try:
      global buffer_log_api
      buffer_log_api.append(object)
      if len(buffer_log_api)>=config_batch_log_api:
         await function_object_create_postgres(client_postgres,"log_api",buffer_log_api,0,None,None)
         buffer_log_api=[]
   except Exception as e:print(str(e))
   return None

from fastapi import Request,responses
from starlette.background import BackgroundTask
async def function_api_response_background(request,api_function):
   body=await request.body()
   async def receive():return {"type":"http.request","body":body}
   async def api_function_new():
      request_new=Request(scope=request.scope,receive=receive)
      await api_function(request_new)
   response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
   response.background=BackgroundTask(api_function_new)
   return response

async def function_check_api_access(mode,request,cache_users_api_access,client_postgres,config_api):
   if mode=="token":user_api_access_list=[int(item.strip()) for item in request.state.user["api_access"].split(",")] if request.state.user["api_access"] else []
   elif mode=="cache":user_api_access_list=cache_users_api_access.get(request.state.user["id"],"absent")
   if user_api_access_list=="absent":
      query="select id,api_access from users where id=:id;"
      values={"id":request.state.user["id"]}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
      if not user:raise Exception("user not found")
      api_access_str=user["api_access"]
      if not api_access_str:raise Exception("api access denied")
      user_api_access_list=[int(item.strip()) for item in api_access_str.split(",")]
   api_id=config_api.get(request.url.path,{}).get("id")
   if not api_id:raise Exception("api id not mapped")
   if api_id not in user_api_access_list:raise Exception("api access denied")
   return None

async def function_check_is_active(mode,request,cache_users_is_active,client_postgres):
   if mode=="token":user_is_active=request.state.user["is_active"]
   elif mode=="cache":user_is_active=cache_users_is_active.get(request.state.user["id"],"absent")
   if user_is_active=="absent":
      query="select id,is_active from users where id=:id;"
      values={"id":request.state.user["id"]}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
      if not user:raise Exception("user not found")
      user_is_active=user["is_active"]
   if user_is_active==0:raise Exception("user not active")
   return None

async def function_check_ratelimiter(request,client_redis,config_api):
   limit,window=config_api.get(request.url.path).get("ratelimiter_times_sec")
   identifier=request.state.user.get("id") if request.state.user else request.client.host
   ratelimiter_key=f"ratelimiter:{request.url.path}:{identifier}"
   current_count=await client_redis.get(ratelimiter_key)
   if current_count and int(current_count)+1>limit:raise Exception("ratelimiter exceeded")
   pipe=client_redis.pipeline()
   pipe.incr(ratelimiter_key)
   if not current_count:pipe.expire(ratelimiter_key,window)
   await pipe.execute()
   return None

from fastapi import Response
import gzip,base64,time
inmemory_cache={}
async def function_cache_api_response(mode,request,response,client_redis,config_api):
   query_param_sorted="&".join(f"{k}={v}" for k, v in sorted(request.query_params.items()))
   identifier=request.state.user.get("id") if "my/" in request.url.path else 0
   cache_key=f"cache:{request.url.path}?{query_param_sorted}:{identifier}"
   cache_mode,expire_sec=config_api.get(request.url.path,{}).get("cache_sec",(None,None))
   if mode=="get":
      response=None
      cached_response=None
      if cache_mode=="redis":
         cached_response=await client_redis.get(cache_key)
         if cached_response:response=Response(content=gzip.decompress(base64.b64decode(cached_response)).decode(),status_code=200,media_type="application/json")
      if cache_mode=="inmemory":
         cache_item=inmemory_cache.get(cache_key)
         if cache_item and cache_item["expire_at"]>time.time():response=Response(content=gzip.decompress(base64.b64decode(cache_item["data"])).decode(),status_code=200,media_type="application/json")
   if mode=="set":
      body=b"".join([chunk async for chunk in response.body_iterator])
      if cache_mode=="redis":
         await client_redis.setex(cache_key,expire_sec,base64.b64encode(gzip.compress(body)).decode())
      if cache_mode=="inmemory":
         inmemory_cache[cache_key]={"data":base64.b64encode(gzip.compress(body)).decode(),"expire_at":time.time()+expire_sec}
      response=Response(content=body, status_code=response.status_code, media_type=response.media_type)
   return response

#send
async def function_send_email_ses(client_ses,email_from,email_to_list,title,body):
   client_ses.send_email(Source=email_from,Destination={"ToAddresses":email_to_list},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return None

import httpx
async def function_send_email_resend(config_resend_url,config_resend_key,email_from,email_to_list,title,body):
   payload={"from":email_from,"to":email_to_list,"subject":title,"html":body}
   headers={"Authorization":f"Bearer {config_resend_key}","Content-Type": "application/json"}
   async with httpx.AsyncClient() as client:
      output=await client.post(config_resend_url,json=payload,headers=headers)
   if output.status_code!=200:raise Exception(f"{output.text}")
   return None

import requests
async def function_send_mobile_otp_fast2sms(config_fast2sms_url,config_fast2sms_key,mobile,otp):
   response=requests.get(config_fast2sms_url,params={"authorization":config_fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   output=response.json()
   if output.get("return") is not True:raise Exception(f"{output.get('message')}")
   return output

async def function_send_mobile_message_sns(client_sns,mobile,message):
   client_sns.publish(PhoneNumber=mobile,Message=message)
   return None

async def function_send_mobile_message_sns_template(client_sns,mobile,message,template_id,entity_id,sender_id):
   client_sns.publish(PhoneNumber=mobile, Message=message,MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

#otp
import random
async def function_otp_generate(mode,data,client_postgres):
   otp=random.randint(100000,999999)
   if mode=="email":
      query="insert into otp (otp,email) values (:otp,:email) returning *;"
      values={"otp":otp,"email":data.strip().lower()}
   if mode=="mobile":
      query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;"
      values={"otp":otp,"mobile":data.strip().lower()}
   await client_postgres.execute(query=query,values=values)
   return otp

async def function_otp_verify(mode,otp,data,client_postgres):
   if mode=="email":
      query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
      values={"email":data}
   if mode=="mobile":
      query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
      values={"mobile":data}
   output=await client_postgres.fetch_all(query=query,values=values)
   if not output:raise Exception("otp not found")
   if int(output[0]["otp"])!=int(otp):raise Exception("otp mismatch")
   return None

#s3
async def function_s3_bucket_create(config_s3_region_name,client_s3,bucket):
   output=client_s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':config_s3_region_name})
   return output

async def function_s3_bucket_public(client_s3,bucket):
   client_s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=client_s3.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def function_s3_bucket_empty(client_s3_resource,bucket):
   output=client_s3_resource.Bucket(bucket).objects.all().delete()
   return output

async def function_s3_bucket_delete(client_s3,bucket):
   output=client_s3.delete_bucket(Bucket=bucket)
   return output

async def function_s3_url_delete(client_s3_resource,url):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=client_s3_resource.Object(bucket,key).delete()
   return output

async def function_s3_file_upload_presigned(config_s3_region_name,client_s3,bucket,key,expiry_sec,limit_size_kb):
   if "." not in key:raise Exception("extension must")
   output=client_s3.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec, Conditions=[['content-length-range',1,limit_size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"
   return output

import uuid
from io import BytesIO
async def function_s3_file_upload_direct(config_s3_region_name,client_s3,bucket,key_list,file_list):
   if not key_list:key_list=[f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}" for file in file_list]
   output={}
   for index,file in enumerate(file_list):
      key=key_list[index]
      if "." not in key:raise Exception("extension must")
      file_content=await file.read()
      file_size_kb=round(len(file_content)/1024)
      if file_size_kb>100:raise Exception("file size issue")
      client_s3.upload_fileobj(BytesIO(file_content),bucket,key)
      output[file.filename]=f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"
      file.file.close()
   return output

#postgres
async def function_postgres_drop_all_index(client_postgres):
   query="0 DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'index_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;"
   await client_postgres.execute(query=query,values={})
   return None

async def function_postgres_query_runner(client_postgres,query,user_id=1):
   block_word=["drop","truncate"]
   stop_word=["drop","delete","update","insert","alter","truncate","create", "rename","replace","merge","grant","revoke","execute","call","comment","set","disable","enable","lock","unlock"]
   must_word=["select"]
   for item in block_word:
      if item in query.lower():raise Exception(f"{item} keyword not allowed in query")
   if user_id!=1:
      for item in stop_word:
         if item in query.lower():raise Exception(f"{item} keyword not allowed in query")
      for item in must_word:
         if item not in query.lower():raise Exception(f"{item} keyword not allowed in query")
   output=await client_postgres.fetch_all(query=query,values={})
   return output

import csv,re
from io import StringIO
async def function_postgres_stream(client_postgres_asyncpg_pool,query):
   if not re.match(r"^\s*SELECT\s", query,flags=re.IGNORECASE):raise Exception(status_code=400, detail="Only SELECT queries are allowed.")
   async with client_postgres_asyncpg_pool.acquire() as client_postgres_asyncpg:
      async with client_postgres_asyncpg.transaction():
         stmt = await client_postgres_asyncpg.prepare(query)
         column_names = [attr.name for attr in stmt.get_attributes()]
         stream = StringIO()
         writer = csv.writer(stream)
         writer.writerow(column_names)
         yield stream.getvalue()
         stream.seek(0)
         stream.truncate(0)
         async for row in client_postgres_asyncpg.cursor(query):
               writer.writerow(row)
               yield stream.getvalue()
               stream.seek(0)
               stream.truncate(0)

async def function_postgres_schema_read(client_postgres):
   query='''
   WITH t AS (SELECT * FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'),
   c AS (
   SELECT table_name, column_name, data_type, 
   CASE WHEN is_nullable='YES' THEN 1 ELSE 0 END AS is_nullable, 
   column_default 
   FROM information_schema.columns 
   WHERE table_schema='public'
   ), 
   i AS (
   SELECT t.relname::text AS table_name, a.attname AS column_name,
   CASE WHEN idx.indisprimary OR idx.indisunique OR idx.indisvalid THEN 1 ELSE 0 END AS is_index
   FROM pg_attribute a
   JOIN pg_class t ON a.attrelid=t.oid
   JOIN pg_namespace ns ON t.relnamespace=ns.oid
   LEFT JOIN pg_index idx ON a.attrelid=idx.indrelid AND a.attnum=ANY(idx.indkey)
   WHERE ns.nspname='public' AND a.attnum > 0 AND t.relkind='r'
   )
   SELECT t.table_name as table, c.column_name as column, c.data_type as datatype,c.column_default as default, c.is_nullable as is_null, COALESCE(i.is_index, 0) AS is_index 
   FROM t 
   LEFT JOIN c ON t.table_name=c.table_name 
   LEFT JOIN i ON t.table_name=i.table_name AND c.column_name=i.column_name;
   '''
   output=await client_postgres.fetch_all(query=query,values={})
   postgres_schema={}
   for object in output:
      table,column=object["table"],object["column"]
      column_data={"datatype":object["datatype"],"default":object["default"],"is_null":object["is_null"],"is_index":object["is_index"]}
      if table not in postgres_schema:postgres_schema[table]={}
      postgres_schema[table][column]=column_data
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return postgres_schema,postgres_column_datatype

async def function_postgres_schema_init(client_postgres,config_postgres_schema,function_postgres_schema_read):
   if not config_postgres_schema:raise Exception("config_postgres_schema null")
   async def function_init_extension(client_postgres):
      await client_postgres.execute(query="create extension if not exists postgis;",values={})
      await client_postgres.execute(query="create extension if not exists pg_trgm;",values={})
      return None
   async def function_init_table(client_postgres,config_postgres_schema,function_postgres_schema_read):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      for table,column_list in config_postgres_schema["table"].items():
         is_table=postgres_schema.get(table,{})
         if not is_table:
            query=f"create table if not exists {table} (id bigint primary key generated by default as identity not null);"
            await client_postgres.execute(query=query,values={})
      return None
   async def function_init_column(client_postgres,config_postgres_schema,function_postgres_schema_read):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      for table,column_list in config_postgres_schema["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            is_column=postgres_schema.get(table,{}).get(column_name,{})
            if not is_column:
               query=f"alter table {table} add column if not exists {column_name} {column_datatype};"
               await client_postgres.execute(query=query,values={})
      return None
   async def function_init_nullable(client_postgres,config_postgres_schema,function_postgres_schema_read):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      for table,column_list in config_postgres_schema["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            is_null=postgres_schema.get(table,{}).get(column_name,{}).get("is_null",None)
            if column_is_mandatory=="0" and is_null==0:
               query=f"alter table {table} alter column {column_name} drop not null;"
               await client_postgres.execute(query=query,values={})
            if column_is_mandatory=="1" and is_null==1:
               query=f"alter table {table} alter column {column_name} set not null;"
               await client_postgres.execute(query=query,values={})
      return None
   async def function_init_index(client_postgres,config_postgres_schema):
      index_name_list=[object["indexname"] for object in (await client_postgres.fetch_all(query="SELECT indexname FROM pg_indexes WHERE schemaname='public';",values={}))]
      for table,column_list in config_postgres_schema["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            if column_index_type=="0":
               query=f"DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname ILIKE 'index_{table}_{column_name}_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;"
               await client_postgres.execute(query=query,values={})
            else:
               index_type_list=column_index_type.split(",")
               for index_type in index_type_list:
                  index_name=f"index_{table}_{column_name}_{index_type}"
                  if index_name not in index_name_list:
                     if index_type=="gin" and column_datatype=="text":
                        query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name} gin_trgm_ops);"
                        await client_postgres.execute(query=query,values={})
                     else:
                        query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name});"
                        await client_postgres.execute(query=query,values={})
      return None
   async def function_init_query_default(client_postgres,function_postgres_schema_read):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      query_default_created_at="DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema='public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;"
      query_default_updated_at_1="create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';"
      query_default_updated_at_2="DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;"
      query_protect_is_protected="DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected=1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;"
      query_function_delete_disable_bulk="create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;"
      query_check_is_active="DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_active' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_active', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_active IN (0,1) OR is_active IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;"
      query_check_is_verified="DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_verified' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_verified', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_verified IN (0,1) OR is_verified IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;"
      query_check_is_deleted="DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_deleted' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_deleted', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_deleted IN (0,1) OR is_deleted IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;"
      query_check_is_protected="DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_protected' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_protected', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_protected IN (0,1) OR is_protected IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;"
      query_root_user_1="insert into users (type,username,password,api_access) values (1,'atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','1,2,3,4,5,6,7,8,9,10') on conflict do nothing;"
      query_root_user_2="create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;"
      query_log_password_change_1="CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;"
      query_log_password_change_2="CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();"
      for query in [query_default_created_at,query_default_updated_at_1,query_default_updated_at_2,query_protect_is_protected,query_function_delete_disable_bulk,query_check_is_active,query_check_is_verified,query_check_is_deleted,query_check_is_protected]:await client_postgres.execute(query=query,values={})
      if postgres_schema.get("users"):
         for query in [query_root_user_1,query_root_user_2]:await client_postgres.execute(query=query,values={})
      if postgres_schema.get("users") and postgres_schema.get("log_password"):
         for query in [query_log_password_change_1,query_log_password_change_2]:await client_postgres.execute(query=query,values={})
      return None
   async def function_init_query_client(client_postgres,config_postgres_schema):
      constraint_name_list={object["constraint_name"].lower() for object in (await client_postgres.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))}
      for query in config_postgres_schema["query"].values():
         if query.split()[0]=="0":continue
         if "add constraint" in query.lower() and query.split()[5].lower() in constraint_name_list:continue
         await client_postgres.execute(query=query,values={})
      return None
   await function_init_extension(client_postgres)
   await function_init_table(client_postgres,config_postgres_schema,function_postgres_schema_read)
   await function_init_column(client_postgres,config_postgres_schema,function_postgres_schema_read)
   await function_init_nullable(client_postgres,config_postgres_schema,function_postgres_schema_read)
   await function_init_index(client_postgres,config_postgres_schema)
   await function_init_query_default(client_postgres,function_postgres_schema_read)
   await function_init_query_client(client_postgres,config_postgres_schema)
   return None

#auth
import hashlib
async def function_auth_signup_username_password(client_postgres,type,username,password):
   query="insert into users (type,username,password) values (:type,:username,:password) returning *;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   return output[0]

async def function_auth_signup_username_password_bigint(client_postgres,type,username_bigint,password_bigint):
   query="insert into users (type,username_bigint,password_bigint) values (:type,:username_bigint,:password_bigint) returning *;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await client_postgres.fetch_all(query=query,values=values)
   return output[0]

import hashlib
async def function_auth_login_password_username(client_postgres,type,password,username,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

import hashlib
async def function_auth_login_password_username_bigint(client_postgres,type,password_bigint,username_bigint,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   query=f"select * from users where type=:type and username_bigint=:username_bigint and password_bigint=:password_bigint order by id desc limit 1;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

import hashlib
async def function_auth_login_password_email(client_postgres,type,password,email,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

import hashlib
async def function_auth_login_password_mobile(client_postgres,type,password,mobile,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

async def function_auth_login_otp_email(client_postgres,type,email,function_otp_verify,otp,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   await function_otp_verify("email",otp,email,client_postgres)
   query=f"select * from users where type=:type and email=:email order by id desc limit 1;"
   values={"type":type,"email":email}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,email) values (:type,:email) returning *;"
      values={"type":type,"email":email}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

async def function_auth_login_otp_mobile(client_postgres,type,mobile,function_otp_verify,otp,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   await function_otp_verify("mobile",otp,mobile,client_postgres)
   query=f"select * from users where type=:type and mobile=:mobile order by id desc limit 1;"
   values={"type":type,"mobile":mobile}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,mobile) values (:type,:mobile) returning *;"
      values={"type":type,"mobile":mobile}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_request
async def function_auth_login_google(client_postgres,type,google_token,config_google_login_client_id,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_key_list):
   request=google_request.Request()
   id_info=id_token.verify_oauth2_token(google_token,request,config_google_login_client_id)
   google_user={"sub": id_info.get("sub"),"email": id_info.get("email"),"name": id_info.get("name"),"picture": id_info.get("picture"),"email_verified": id_info.get("email_verified")}
   query=f"select * from users where type=:type and google_id=:google_id order by id desc limit 1;"
   values={"type":type,"google_id":google_user["sub"]}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,google_id,google_data) values (:type,:google_id,:google_data) returning *;"
      values={"type":type,"google_id":google_user["sub"],"google_data":json.dumps(google_user)}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_key_list,user)
   return token

#crud
import datetime
async def function_update_last_active_at(client_postgres,user_id):
   try:
      query="update users set last_active_at=:last_active_at where id=:id;"
      values={"id":user_id,"last_active_at":datetime.datetime.now()}
      await client_postgres.execute(query=query,values=values)
   except Exception as e:print(str(e))
   return None

async def function_read_user_single(client_postgres,user_id):
   query="select * from users where id=:id;"
   values={"id":user_id}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=dict(output[0]) if output else None
   if not user:raise Exception("user not found")
   return user

async def function_delete_user_single(client_postgres,mode,user_id):
   if mode=="soft":query="update users set is_deleted=1 where id=:id;"
   if mode=="hard":query="delete from users where id=:id;"
   values={"id":user_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_update_ids(client_postgres,table,ids,column,value,updated_by_id,created_by_id):
   query=f"update {table} set {column}=:value,updated_by_id=:updated_by_id where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"value":value,"created_by_id":created_by_id,"updated_by_id":updated_by_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_delete_ids(client_postgres,table,ids,created_by_id):
   query=f"delete from {table} where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"created_by_id":created_by_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_parent_object_read(client_postgres,table,parent_column,parent_table,order,limit,offset,user_id):
   query=f'''
   with
   x as (select {parent_column} from {table} where (created_by_id=:created_by_id or :created_by_id is null) order by {order} limit {limit} offset {offset}) 
   select ct.* from x left join {parent_table}  as ct on x.{parent_column}=ct.id;
   '''
   values={"created_by_id":user_id}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

#message
async def function_message_inbox(client_postgres,user_id,order,limit,offset,is_unread):
   if not is_unread:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {offset};'''
   elif int(is_unread)==1:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {offset};'''
   values={"created_by_id":user_id,"user_id":user_id}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

async def function_message_received(client_postgres,user_id,order,limit,offset,is_unread):
   if not is_unread:query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {offset};"
   elif int(is_unread)==1:query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {offset};"
   values={"user_id":user_id}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

async def function_message_thread(client_postgres,user_id_1,user_id_2,order,limit,offset):
   query=f"select * from message where ((created_by_id=:user_id_1 and user_id=:user_id_2) or (created_by_id=:user_id_2 and user_id=:user_id_1)) order by {order} limit {limit} offset {offset};"
   values={"user_id_1":user_id_1,"user_id_2":user_id_2}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

async def function_message_thread_mark_read(client_postgres,user_id_1,user_id_2):
   query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;"
   values={"created_by_id":user_id_2,"user_id":user_id_1}
   await client_postgres.execute(query=query,values={})
   return None

async def function_message_object_mark_read(client_postgres,object_list):
   try:
      ids=','.join([str(item['id']) for item in object_list])
      query=f"update message set is_read=1 where id in ({ids});"
      await client_postgres.execute(query=query,values={})
   except Exception as e:print(str(e))
   return None

async def function_message_delete_user_single(client_postgres,user_id,message_id):
   query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id,"id":message_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_message_delete_user_created(client_postgres,user_id):
   query="delete from message where created_by_id=:user_id;"
   values={"user_id":user_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_message_delete_user_received(client_postgres,user_id):
   query="delete from message where user_id=:user_id;"
   values={"user_id":user_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_message_delete_user_all(client_postgres,user_id):
   query="delete from message where (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id}
   await client_postgres.execute(query=query,values=values)
   return None

#openai
async def function_openai_prompt(client_openai,model,prompt,is_web_search,previous_response_id):
   if not client_openai or not model or not prompt:raise Exception("param missing")
   params={"model":model,"input":prompt}
   if is_web_search==1:params["tools"]=[{"type":"web_search"}]
   if previous_response_id:params["previous_response_id"]=previous_response_id
   output=client_openai.responses.create(**params)
   return output

import base64
async def function_openai_ocr(client_openai,model,file,prompt):
   contents=await file.read()
   b64_image=base64.b64encode(contents).decode("utf-8")
   output=client_openai.responses.create(model=model,input=[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:image/png;base64,{b64_image}"},],}],)
   return output

#utilities
import os
def function_export_path_file(path="."):
    skip_dirs = {"venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache", "node_modules"}
    path = os.path.abspath(path)
    out_path = os.path.join(path, "files.txt")
    with open(out_path, "w") as out_file:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, path)
                out_file.write(rel_path + "\n")
    print(f"Saved to: {out_path}")
    return None
 
import sys
def function_variable_size_kb_read(namespace):
   result = {}
   for name, var in namespace.items():
      if not name.startswith("__"):
         key = f"{name} ({type(var).__name__})"
         size_kb = sys.getsizeof(var) / 1024
         result[key] = size_kb
   sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
   return sorted_result

import csv,io
async def function_file_to_object_list(file):
   content=await file.read()
   content=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(content))
   object_list=[row for row in reader]
   await file.close()
   return object_list

async def function_column_mapping_read(client_postgres_asyncpg,table,column_1,column_2,limit,is_null,transformer):
   output = {}
   where_clause = "" if is_null else f"WHERE {column_2} IS NOT NULL"
   async with client_postgres_asyncpg.transaction():
      cursor = await client_postgres_asyncpg.cursor(f'SELECT {column_1},{column_2} FROM {table} {where_clause} ORDER BY {column_1} DESC')
      count = 0
      while count < limit:
         batch = await cursor.fetch(10000)
         if not batch: break
         if transformer == "split_int":output.update({record[column_1]: [int(item.strip()) for item in record[column_2].split(",")] if record[column_2] else [] for record in batch})
         else:output.update({record[column_1]: record[column_2] for record in batch})
         count += len(batch)
   return output

async def function_create_where_string(object,function_object_serialize,postgres_column_datatype):
   object={k:v for k,v in object.items() if (k in postgres_column_datatype and k not in ["metadata","location","table","order","limit","page"] and v is not None)}
   where_operator={k:v.split(',',1)[0] for k,v in object.items()}
   where_value={k:v.split(',',1)[1] for k,v in object.items()}
   object_list=await function_object_serialize([where_value],postgres_column_datatype)
   where_value=object_list[0]
   where_string_list=[f"({key} {where_operator[key]} :{key} or :{key} is null)" for key in [*object]]
   where_string_joined=' and '.join(where_string_list)
   where_string=f"where {where_string_joined}" if where_string_joined else ""
   return where_string,where_value
   
async def function_add_creator_data(client_postgres,user_key,object_list):
    object_list=[dict(object) for object in object_list]
    created_by_ids={str(object["created_by_id"]) for object in object_list if object.get("created_by_id")}
    users={}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id IN ({','.join(created_by_ids)});"
        users = {str(user["id"]): dict(user) for user in await client_postgres.fetch_all(query=query,values={})}
    for object in object_list:
        created_by_id = str(object.get("created_by_id"))
        if created_by_id in users:
            for key in user_key.split(","):
                object[f"creator_{key}"] = users[created_by_id].get(key)
        else:
            for key in user_key.split(","):
                object[f"creator_{key}"] = None
    return object_list
 
async def function_ownership_check(client_postgres,table,id,user_id):
   if table=="users":
      if id!=user_id:raise Exception("object ownership issue")
   if table!="users":
      query=f"select created_by_id from {table} where id=:id;"
      values={"id":id}
      output=await client_postgres.fetch_all(query=query,values=values)
      if not output:raise Exception("no object")
      if output[0]["created_by_id"]!=user_id:raise Exception("object ownership issue")
   return None

import hashlib,datetime,json
async def function_object_serialize(object_list,postgres_column_datatype):
   for index,object in enumerate(object_list):
      for key,value in object.items():
         datatype=postgres_column_datatype.get(key)
         if not datatype:continue
         if not value:continue
         elif key in ["password"]:object_list[index][key]=hashlib.sha256(str(value).encode()).hexdigest()
         elif datatype=="text" and value in ["","null"]:object_list[index][key]=None
         elif datatype=="text":object_list[index][key]=value.strip()
         elif "int" in datatype:object_list[index][key]=int(value)
         elif datatype=="numeric":object_list[index][key]=round(float(value),3)
         elif datatype=="date":object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%d')
         elif "time" in datatype:object_list[index][key]=datetime.datetime.strptime(value,'%Y-%m-%dT%H:%M:%S')
         elif datatype=="ARRAY":object_list[index][key]=value.split(",")
         elif datatype=="jsonb":object_list[index][key]=json.dumps(value)
   return object_list

import os
from dotenv import load_dotenv, dotenv_values
import importlib.util
from pathlib import Path
import traceback
def function_config_read():
   base_dir = Path(__file__).parent
   def read_env_file():
      load_dotenv(base_dir / ".env")
      return {k.lower(): v for k, v in dotenv_values(base_dir / ".env").items()}
   def read_root_config_py_files():
      output = {}
      for file in os.listdir(base_dir):
         if file.startswith("config") and file.endswith(".py"):
            module_path = base_dir / file
            try:
               module_name = os.path.splitext(file)[0]
               spec = importlib.util.spec_from_file_location(module_name, module_path)
               if spec and spec.loader:
                  module = importlib.util.module_from_spec(spec)
                  spec.loader.exec_module(module)
                  output.update({
                     k.lower(): getattr(module, k)
                     for k in dir(module) if not k.startswith("__")
                  })
            except Exception as e:
               print(f"[WARN] Failed to load root config file: {module_path}")
               traceback.print_exc()
      return output
   def read_config_folder_files():
      output = {}
      config_dir = base_dir / "config"
      if not config_dir.exists() or not config_dir.is_dir():
         return output
      for file in os.listdir(config_dir):
         if file.endswith(".py"):
            module_path = config_dir / file
            try:
               rel_path = os.path.relpath(module_path, base_dir)
               module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
               if not module_name.strip():
                  continue
               spec = importlib.util.spec_from_file_location(module_name, module_path)
               if spec and spec.loader:
                  module = importlib.util.module_from_spec(spec)
                  spec.loader.exec_module(module)
                  output.update({
                     k.lower(): getattr(module, k)
                     for k in dir(module) if not k.startswith("__")
                  })
            except Exception as e:
               print(f"[WARN] Failed to load config folder file: {module_path}")
               traceback.print_exc()
      return output
   output = {}
   output.update(read_env_file())
   output.update(read_root_config_py_files())
   output.update(read_config_folder_files())
   return output



def function_converter_numeric(mode,x):
   MAX_LEN = 30
   CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-_.@#"
   BASE = len(CHARS)
   CHAR_TO_NUM = {ch: i for i, ch in enumerate(CHARS)}
   NUM_TO_CHAR = {i: ch for i, ch in enumerate(CHARS)}
   if mode=="encode":
      if len(x) > MAX_LEN:raise Exception(f"String too long (max {MAX_LEN} characters)")
      num = 0
      for ch in x:
         if ch not in CHAR_TO_NUM:raise Exception(f"Unsupported character: '{ch}'")
         num = num * BASE + CHAR_TO_NUM[ch]
      output=len(x) * (BASE ** MAX_LEN) + num
   if mode=="decode":
      length = x // (BASE ** MAX_LEN)
      num = x % (BASE ** MAX_LEN)
      chars = []
      for _ in range(length):
         num, rem = divmod(num, BASE)
         chars.append(NUM_TO_CHAR[rem])
      output=''.join(reversed(chars))
   return output

def function_converter_bigint(mode,x):
   MAX_LENGTH = 11
   CHARSET = 'abcdefghijklmnopqrstuvwxyz0123456789_'
   BASE = len(CHARSET)
   LENGTH_BITS = 6
   VALUE_BITS = 64 - LENGTH_BITS
   CHAR_TO_INDEX = {c: i for i, c in enumerate(CHARSET)}
   INDEX_TO_CHAR = {i: c for i, c in enumerate(CHARSET)}
   if mode=="encode":
      if len(x) > MAX_LENGTH:raise Exception(f"text length exceeds {MAX_LENGTH} characters.")
      value = 0
      for char in x:
         if char not in CHAR_TO_INDEX:raise Exception(f"Invalid character: {char}")
         value = value * BASE + CHAR_TO_INDEX[char]
      output=(len(x) << VALUE_BITS) | value
   if mode=="decode":
      length = x >> VALUE_BITS
      value = x & ((1 << VALUE_BITS) - 1)
      chars = []
      for _ in range(length):
         value, index = divmod(value, BASE)
         chars.append(INDEX_TO_CHAR[index])
      output=''.join(reversed(chars))
   return output
  
import os,json,requests
def function_grafana_dashboards_export(host,username,password,max_limit,export_dir):
   session = requests.Session()
   session.auth = (username, password)
   def sanitize(name):return "".join(c if c.isalnum() or c in " _-()" else "_" for c in name)
   def ensure_dir(path):os.makedirs(path, exist_ok=True)
   def get_organizations():
      r = session.get(f"{host}/api/orgs")
      r.raise_for_status()
      return r.json()
   def switch_org(org_id):return session.post(f"{host}/api/user/using/{org_id}").status_code == 200
   def get_dashboards(org_id):
      headers = {"X-Grafana-Org-Id": str(org_id)}
      r = session.get(f"{host}/api/search?type=dash-db&limit={max_limit}", headers=headers)
      if r.status_code == 422:return []
      r.raise_for_status()
      return r.json()
   def get_dashboard_json(uid):
      r = session.get(f"{host}/api/dashboards/uid/{uid}")
      r.raise_for_status()
      return r.json()
   def export_dashboard(org_name, folder_name, dashboard_meta):
      uid = dashboard_meta["uid"]
      data = get_dashboard_json(uid)
      dashboard_only = data["dashboard"]
      path = os.path.join(export_dir, sanitize(org_name), sanitize(folder_name or "General"))
      ensure_dir(path)
      file_path = os.path.join(path, f"{sanitize(dashboard_meta['title'])}.json")
      with open(file_path, "w", encoding="utf-8") as f:json.dump(dashboard_only, f, indent=2)
      print(f"✅ {org_name}/{folder_name}/{dashboard_meta['title']}")
   try:
      orgs = get_organizations()
   except Exception as e:
      print("❌ Failed to fetch organizations:", e)
      return
   for org in orgs:
      if not switch_org(org["id"]):continue
      try:
         dashboards = get_dashboards(org["id"])
      except Exception as e:
         print("❌ Failed to fetch dashboards:",e)
         continue
      for dash in dashboards:
         try:export_dashboard(org["name"], dash.get("folderTitle", "General"), dash)
         except Exception as e:print("❌ Failed to export", dash.get("title"), ":", e)
         
import asyncpg,random
from mimesis import Person,Address,Food,Text,Code,Datetime
async def function_create_fake_data(config_postgres_url,TOTAL_ROWS,BATCH_SIZE):
   client_postgres_asyncpg = await asyncpg.connect(config_postgres_url)
   person = Person()
   address = Address()
   food = Food()
   text_gen = Text()
   code = Code()
   dt = Datetime()
   TABLES = {
   "customers": [("name", "TEXT", lambda: person.full_name()), ("email", "TEXT", lambda: person.email()), ("city", "TEXT", lambda: address.city()), ("country", "TEXT", lambda: address.country()), ("birth_date", "DATE", lambda: dt.date()), ("signup_code", "TEXT", lambda: code.imei()), ("loyalty_points", "INT", lambda: random.randint(0, 10000)), ("favorite_fruit", "TEXT", lambda: food.fruit())],
   "orders": [("order_number", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("order_date", "DATE", lambda: dt.date()), ("shipping_city", "TEXT", lambda: address.city()), ("total_amount", "INT", lambda: random.randint(10, 5000)), ("status", "TEXT", lambda: random.choice(["pending", "shipped", "delivered", "cancelled"])), ("item_count", "INT", lambda: random.randint(1, 20)), ("shipping_country", "TEXT", lambda: address.country())],
   "products": [("product_name", "TEXT", lambda: food.fruit()), ("category", "TEXT", lambda: random.choice(["electronics", "clothing", "food", "books"])), ("price", "INT", lambda: random.randint(5, 1000)), ("supplier_city", "TEXT", lambda: address.city()), ("stock_quantity", "INT", lambda: random.randint(0, 500)), ("manufacture_date", "DATE", lambda: dt.date()), ("expiry_date", "DATE", lambda: dt.date()), ("sku_code", "TEXT", lambda: code.imei())],
   "employees": [("full_name", "TEXT", lambda: person.full_name()), ("email", "TEXT", lambda: person.email()), ("department", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Support"])), ("city", "TEXT", lambda: address.city()), ("salary", "INT", lambda: random.randint(30000, 150000)), ("hire_date", "DATE", lambda: dt.date()), ("employee_id", "TEXT", lambda: code.imei())],
   "suppliers": [("supplier_name", "TEXT", lambda: person.full_name()), ("contact_email", "TEXT", lambda: person.email()), ("city", "TEXT", lambda: address.city()), ("country", "TEXT", lambda: address.country()), ("phone_number", "TEXT", lambda: person.telephone()), ("rating", "INT", lambda: random.randint(1, 5))],
   "invoices": [("invoice_number", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("invoice_date", "DATE", lambda: dt.date()), ("amount_due", "INT", lambda: random.randint(100, 10000)), ("due_date", "DATE", lambda: dt.date()), ("status", "TEXT", lambda: random.choice(["paid", "unpaid", "overdue"]))],
   "payments": [("payment_id", "TEXT", lambda: code.imei()), ("invoice_number", "TEXT", lambda: code.imei()), ("payment_date", "DATE", lambda: dt.date()), ("amount", "INT", lambda: random.randint(50, 10000)), ("payment_method", "TEXT", lambda: random.choice(["credit_card", "paypal", "bank_transfer"])), ("status", "TEXT", lambda: random.choice(["completed", "pending", "failed"]))],
   "departments": [("department_name", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Support"])), ("manager", "TEXT", lambda: person.full_name()), ("location", "TEXT", lambda: address.city()), ("budget", "INT", lambda: random.randint(50000, 1000000))],
   "projects": [("project_name", "TEXT", lambda: text_gen.word()), ("start_date", "DATE", lambda: dt.date()), ("end_date", "DATE", lambda: dt.date()), ("budget", "INT", lambda: random.randint(10000, 500000)), ("department", "TEXT", lambda: random.choice(["HR", "Engineering", "Sales", "Support"]))],
   "inventory": [("item_name", "TEXT", lambda: food.spices()), ("quantity", "INT", lambda: random.randint(0, 1000)), ("warehouse_location", "TEXT", lambda: address.city()), ("last_restock_date", "DATE", lambda: dt.date())],
   "shipments": [("shipment_id", "TEXT", lambda: code.imei()), ("order_number", "TEXT", lambda: code.imei()), ("shipment_date", "DATE", lambda: dt.date()), ("delivery_date", "DATE", lambda: dt.date()), ("status", "TEXT", lambda: random.choice(["in_transit", "delivered", "delayed"]))],
   "reviews": [("review_id", "TEXT", lambda: code.imei()), ("product_name", "TEXT", lambda: food.fruit()), ("customer_name", "TEXT", lambda: person.full_name()), ("rating", "INT", lambda: random.randint(1, 5)), ("review_date", "DATE", lambda: dt.date()), ("comments", "TEXT", lambda: text_gen.sentence())],
   "tasks": [("task_name", "TEXT", lambda: text_gen.word()), ("assigned_to", "TEXT", lambda: person.full_name()), ("due_date", "DATE", lambda: dt.date()), ("priority", "TEXT", lambda: random.choice(["low", "medium", "high"])), ("status", "TEXT", lambda: random.choice(["pending", "in_progress", "completed"]))],
   "assets": [("asset_tag", "TEXT", lambda: code.imei()), ("asset_name", "TEXT", lambda: food.fruit()), ("purchase_date", "DATE", lambda: dt.date()), ("warranty_expiry", "DATE", lambda: dt.date()), ("value", "INT", lambda: random.randint(100, 10000))],
   "locations": [("location_name", "TEXT", lambda: address.city()), ("address", "TEXT", lambda: address.address()), ("country", "TEXT", lambda: address.country()), ("postal_code", "TEXT", lambda: address.postal_code())],
   "meetings": [("meeting_id", "TEXT", lambda: code.imei()), ("topic", "TEXT", lambda: text_gen.word()), ("meeting_date", "DATE", lambda: dt.date()), ("organizer", "TEXT", lambda: person.full_name()), ("location", "TEXT", lambda: address.city())],
   "tickets": [("ticket_id", "TEXT", lambda: code.imei()), ("issue", "TEXT", lambda: text_gen.sentence()), ("reported_by", "TEXT", lambda: person.full_name()), ("status", "TEXT", lambda: random.choice(["open", "closed", "in_progress"])), ("priority", "TEXT", lambda: random.choice(["low", "medium", "high"]))],
   "subscriptions": [("subscription_id", "TEXT", lambda: code.imei()), ("customer_name", "TEXT", lambda: person.full_name()), ("start_date", "DATE", lambda: dt.date()), ("end_date", "DATE", lambda: dt.date()), ("plan_type", "TEXT", lambda: random.choice(["basic", "premium", "enterprise"]))],
   }
   async def create_tables(client_postgres_asyncpg,TABLES):
      for table_name, columns in TABLES.items():
         await client_postgres_asyncpg.execute(f"DROP TABLE IF EXISTS {table_name};")
         columns_def = ", ".join(f"{name} {dtype}" for name, dtype, _ in columns)
         query = f"CREATE TABLE IF NOT EXISTS {table_name} (id bigint primary key generated always as identity not null, {columns_def});"
         await client_postgres_asyncpg.execute(query)
   async def insert_batch(client_postgres_asyncpg, table_name, columns, batch_values):
      cols = ", ".join(name for name, _, _ in columns)
      placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
      query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
      await client_postgres_asyncpg.executemany(query, batch_values)
   async def generate_data(client_postgres_asyncpg,insert_batch,TABLES,TOTAL_ROWS,BATCH_SIZE):
      for table_name, columns in TABLES.items():
         print(f"Inserting data into {table_name}...")
         batch_values = []
         for _ in range(TOTAL_ROWS):
               row = tuple(gen() for _, _, gen in columns)
               batch_values.append(row)
               if len(batch_values) == BATCH_SIZE:
                  await insert_batch(client_postgres_asyncpg, table_name, columns, batch_values)
                  batch_values.clear()
         if batch_values:await insert_batch(client_postgres_asyncpg, table_name, columns, batch_values)
         print(f"Completed inserting {TOTAL_ROWS} rows into {table_name}")
   await create_tables(client_postgres_asyncpg,TABLES)
   await generate_data(client_postgres_asyncpg,insert_batch,TABLES,TOTAL_ROWS,BATCH_SIZE)
   await client_postgres_asyncpg.close()
   return None

import pytesseract
from PIL import Image
from pdf2image import convert_from_path
def function_ocr_tesseract(file_path):
    try:
        if file_path.lower().endswith('.pdf'):
            images = convert_from_path(file_path)
            text = ''
            for img in images:
                text += pytesseract.image_to_string(img, lang='eng') + '\n'
            return text
        else:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image, lang='eng')
    except Exception as e:
        raise RuntimeError(f"OCR failed: {e}")
     
import requests, datetime, re
from collections import defaultdict, Counter
from openai import OpenAI
def function_jira_summary_export(jira_base_url,jira_email,jira_token,jira_project_key_list,jira_max_issues_per_status,openai_key):
    client = OpenAI(api_key=openai_key)
    headers = {"Accept": "application/json"}
    auth = (jira_email, jira_token)
    def fetch_issues(jql):
        url = f"{jira_base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "fields": "summary,project,duedate,assignee,worklog,issuetype,parent,resolutiondate,updated",
            "maxResults": jira_max_issues_per_status
        }
        r = requests.get(url, headers=headers, params=params, auth=auth)
        r.raise_for_status()
        return r.json().get("issues", [])
    def fetch_comments(issue_key):
      url = f"{jira_base_url}/rest/api/3/issue/{issue_key}/comment"
      r = requests.get(url, headers=headers, auth=auth)
      r.raise_for_status()
      comments_data = r.json().get("comments", [])
      comment_texts = []
      for c in comments_data:
         try:
               content = c["body"].get("content", [])
               if content and "content" in content[0]:
                  text = content[0]["content"][0].get("text", "")
                  comment_texts.append(text)
         except (KeyError, IndexError, TypeError):
               continue
      return comment_texts
    def group_by_project(issues):
        grouped = defaultdict(list)
        for i in issues:
            name = i["fields"]["project"]["name"]
            grouped[name].append(i)
        return grouped
    def summarize_with_ai(prompt):
        try:
            res = client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{"role": "user", "content": prompt}]
            )
            lines = res.choices[0].message.content.strip().split("\n")
            return [l.strip("-•* \n") for l in lines if l.strip()]
        except Exception as e:
            return [f"AI summary failed: {e}"]
    def build_prompt(issues_by_project, status_label):
        report, seen = [], set()
        now = datetime.datetime.now()
        for project, issues in issues_by_project.items():
            for i in issues:
                f = i["fields"]
                title = f.get("summary", "").strip()
                if title in seen:
                    continue
                seen.add(title)
                comments = fetch_comments(i["key"])
                last_comment = comments[-1][:100] if comments else ""
                updated_days_ago = "N/A"
                try:
                    updated_field = f.get("updated")
                    if updated_field:
                        updated_dt = datetime.datetime.strptime(updated_field[:10], "%Y-%m-%d")
                        updated_days_ago = (now - updated_dt).days
                except:
                    pass
                time_spent = sum(w.get("timeSpentSeconds", 0) for w in f.get("worklog", {}).get("worklogs", [])) // 3600
                line = f"{project} - {title}. Comment: {last_comment}. Hours: {time_spent}. Last Updated: {updated_days_ago}d ago. [{status_label}]"
                report.append(line.strip())
        return "\n".join(report)
    def calculate_activity_and_performance(issues_done):
        activity_counter = Counter()
        on_time_closures = defaultdict(list)
        for issue in issues_done:
            f = issue["fields"]
            assignee = f["assignee"]["displayName"] if f.get("assignee") else "Unassigned"
            comments = fetch_comments(issue["key"])
            worklogs = f.get("worklog", {}).get("worklogs", [])
            activity_counter[assignee] += len(comments) + len(worklogs)
            if f.get("duedate") and f.get("resolutiondate"):
                try:
                    due = datetime.datetime.strptime(f["duedate"], "%Y-%m-%d")
                    resolved = datetime.datetime.strptime(f["resolutiondate"][:10], "%Y-%m-%d")
                    if resolved <= due:
                        on_time_closures[assignee].append(issue["key"])
                except:
                    continue
        top_active = activity_counter.most_common(3)
        best_ontime = sorted(on_time_closures.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        return top_active, best_ontime
    def clean_lines(lines, include_project=False):
        cleaned = []
        for line in lines:
            if len(line.split()) < 3:
                continue
            if include_project and "-" not in line:
                continue
            line = re.sub(r"[^\w\s\-.,/()]", "", line).strip()
            line = re.sub(r'\s+', ' ', line)
            cleaned.append(f"- {line}")
        return cleaned
    def save_summary_to_file(blockers, improvements, top_active, on_time, filename="jira.txt"):
        def numbered(lines):
            return [f"{i+1}. {line}" for i, line in enumerate(lines)]
        with open(filename, "w", encoding="utf-8") as f:
            f.write("Key Blockers\n")
            for line in numbered(clean_lines(blockers, include_project=True)):
                f.write(f"{line}\n")
            f.write("\nSuggested Improvements\n")
            for line in numbered(clean_lines(improvements)):
                f.write(f"{line}\n")
            f.write("\nTop 3 Active Assignees\n")
            for i, (name, count) in enumerate(top_active, 1):
                f.write(f"{i}. {name} ({count} updates)\n")
            f.write("\nBest On-Time Assignees\n")
            for i, (name, items) in enumerate(on_time, 1):
                f.write(f"{i}. {name} - {len(items)} issues closed on or before due date\n")
    issues_todo, issues_inprog, issues_done = [], [], []
    for key in jira_project_key_list:
        issues_todo += fetch_issues(f'project = {key} AND statusCategory = "To Do" ORDER BY updated DESC')
        issues_inprog += fetch_issues(f'project = {key} AND statusCategory = "In Progress" ORDER BY updated DESC')
        issues_done += fetch_issues(f'project = {key} AND statusCategory = "Done" ORDER BY resolutiondate DESC')
    todo_grouped = group_by_project(issues_todo)
    inprog_grouped = group_by_project(issues_inprog)
    done_grouped = group_by_project(issues_done)
    all_prompt_text = (
        build_prompt(todo_grouped, "To Do") + "\n" +
        build_prompt(inprog_grouped, "In Progress") + "\n" +
        build_prompt(done_grouped, "Done")
    )
    prompt_blockers = (
        "From the Jira issues below, list actual blockers that can delay progress. "
        "Each line must begin with the project name. Be specific and short. Max 100 characters per bullet."
    )
    prompt_improvement = (
        "You are a Jira productivity assistant. Based on the following Jira issue summaries, "
        "give exactly 5 specific, actionable process improvements to improve execution quality and velocity. "
        "Each point should be a short bullet (one line, max 100 characters). "
        "Return only the 5 bullet points. Do not include any introduction, summary, explanation, or heading."
    )
    blockers = summarize_with_ai(prompt_blockers + "\n" + all_prompt_text)
    improvements = summarize_with_ai(prompt_improvement + "\n" + all_prompt_text)
    top_active, on_time = calculate_activity_and_performance(issues_done)
    save_summary_to_file(blockers, improvements, top_active, on_time)
    return "✅ Executive JIRA summary saved to 'jira.txt'"

