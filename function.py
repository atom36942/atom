import os
from dotenv import load_dotenv
def function_load_env(env_path):
   load_dotenv(env_path)
   output={k: os.getenv(k) for k in os.environ}
   return output

import uvicorn
async def function_server_start_uvicorn(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info",reload=True)
   server=uvicorn.Server(config)
   await server.serve()

import sentry_sdk
def function_app_add_sentry(config_sentry_dsn):
   sentry_sdk.init(dsn=config_sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)
   return None

def function_app_add_router(app,router_list):
   for item in router_list:
       router=__import__(item).router
       app.include_router(router)

from fastapi.middleware.cors import CORSMiddleware
def function_app_add_cors(app):
   app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
   return None

from prometheus_fastapi_instrumentator import Instrumentator
def function_app_add_prometheus(app):
   Instrumentator().instrument(app).expose(app)
   return None

import json
async def function_publish_kafka(data,client_kafka_producer,config_channel_name):
   output=await client_kafka_producer.send_and_wait(config_channel_name,json.dumps(data,indent=2).encode('utf-8'),partition=0)
   return output

import json
async def function_publish_redis(data,client_redis,config_channel_name):
   output=await client_redis.publish(config_channel_name,json.dumps(data))
   return output

import json,aio_pika
async def function_publish_rabbitmq(data,client_rabbitmq_channel,config_channel_name):
   output=await client_rabbitmq_channel.default_exchange.publish(aio_pika.Message(body=json.dumps(data).encode()),routing_key=config_channel_name)
   return output

import json,aio_pika
async def function_publish_lavinmq(data,client_lavinmq_channel,config_channel_name):
   output=await client_lavinmq_channel.default_exchange.publish(aio_pika.Message(body=json.dumps(data).encode()),routing_key=config_channel_name)
   return output

from fastapi import responses
def function_return_error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})

import requests
async def function_fast2sms_send_otp(mobile,otp,config_fast2sms_key,config_fast2sms_url):
   response=requests.get(config_fast2sms_url,params={"authorization":config_fast2sms_key,"numbers":mobile,"variables_values":otp,"route":"otp"})
   return response

async def function_ses_send_email(email_list,title,body,sender_email,client_ses):
   client_ses.send_email(Source=sender_email,Destination={"ToAddresses":email_list},Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}})
   return None

async def function_sns_send_message(mobile,message,client_sns):
   client_sns.publish(PhoneNumber=mobile,Message=message)
   return None

async def function_sns_send_message_template(mobile,message,template_id,entity_id,sender_id,client_sns):
   client_sns.publish(PhoneNumber=mobile, Message=message,MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

async def function_s3_bucket_create(bucket,client_s3,config_s3_region_name):
   output=client_s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':config_s3_region_name})
   return output

async def function_s3_bucket_public(bucket,client_s3):
   client_s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=client_s3.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def function_s3_bucket_empty(bucket,client_s3_resource):
   output=client_s3_resource.Bucket(bucket).objects.all().delete()
   return output

async def function_s3_bucket_delete(bucket,client_s3):
   output=client_s3.delete_bucket(Bucket=bucket)
   return output

async def function_s3_url_delete(url,client_s3_resource):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=client_s3_resource.Object(bucket,key).delete()
   return output

import uuid
from io import BytesIO
async def function_s3_file_upload_direct(bucket,key_list,file_list,client_s3,config_s3_region_name):
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

async def function_s3_file_upload_presigned(bucket,key,expiry_sec,size_kb,client_s3,config_s3_region_name):
   if "." not in key:raise Exception("extension must")
   output=client_s3.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec, Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"
   return output

async def function_mongodb_object_create(table,object_list,database,client_mongodb):
   mongodb_client_database=client_mongodb[database]
   output=await mongodb_client_database[table].insert_many(object_list)
   return str(output)

async def function_redis_object_create(table,object_list,expiry,client_redis):
   async with client_redis.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if not expiry:pipe.set(key,json.dumps(object))
         else:pipe.setex(key,expiry,json.dumps(object))
      await pipe.execute()
   return None

import csv,io
async def function_file_to_object_list(file):
   content=await file.read()
   content=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(content))
   object_list=[row for row in reader]
   await file.close()
   return object_list

import json
async def function_redis_set_object(object,key,expiry,client_redis):
   object=json.dumps(object)
   if not expiry:output=await client_redis.set(key,object)
   else:output=await client_redis.setex(key,expiry,object)
   return output

import json
async def function_redis_get_object(key,client_redis):
   output=await client_redis.get(key)
   if output:output=json.loads(output)
   return output

import json
object_list_log_api=[]
async def function_postgres_log_create(object,batch,cache_postgres_column_datatype,client_postgres,function_postgres_create,function_object_serialize):
   try:
      global object_list_log_api
      object_list_log_api.append(object)
      if len(object_list_log_api)>=batch:
         await function_postgres_create("log_api",object_list_log_api,0,client_postgres,cache_postgres_column_datatype,function_object_serialize)
         object_list_log_api=[]
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

async def function_cache_users_is_active_read(limit,client_postgres_asyncpg):
   output={}
   async with client_postgres_asyncpg.transaction():
      cursor=await client_postgres_asyncpg.cursor('SELECT id,is_active FROM users ORDER BY id DESC')
      count=0
      while count < limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         output.update({record['id']: record['is_active'] for record in batch})
         if False:await client_redis.mset({f"users_is_active_{record['id']}":0 if record['is_active']==0 else 1 for record in batch})
         count+=len(batch)
   return output

async def function_cache_users_api_access_read(limit,client_postgres_asyncpg):
   output={}
   async with client_postgres_asyncpg.transaction():
      cursor=await client_postgres_asyncpg.cursor('select id,api_access from users where api_access is not null order by id desc')
      count=0
      while count < limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         output.update({record['id']:[int(item.strip()) for item in record["api_access"].split(",")] for record in batch})
         count+=len(batch)
   return output

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

async def function_check_rate_limiter(request,client_redis,config_api):
   limit,window=config_api.get(request.url.path).get("rate_limiter")
   identifier=request.state.user.get("id") if request.state.user else request.client.host
   rate_key=f"ratelimit:{request.url.path}:{identifier}"
   current_count=await client_redis.get(rate_key)
   if current_count and int(current_count)+1>limit:raise Exception("rate limit exceeded")
   pipe=client_redis.pipeline()
   pipe.incr(rate_key)
   if not current_count:pipe.expire(rate_key,window)
   await pipe.execute()
   return None

from fastapi import Response
import gzip,base64
async def function_cache_api_response(mode,request,response,expire_sec,client_redis):
   query_sorted="&".join(f"{k}={v}" for k,v in sorted(request.query_params.items()))
   cache_key=f"{request.url.path}?{query_sorted}:{request.state.user.get('id')}" if "my/" in request.url.path else f"{request.url.path}?{query_sorted}"
   if mode=="get":
      response=None
      cached_response=await client_redis.get(cache_key)
      if cached_response:response=Response(content=gzip.decompress(base64.b64decode(cached_response)).decode(),status_code=200,media_type="application/json")
   if mode=="set":
      body=b"".join([chunk async for chunk in response.body_iterator])
      await client_redis.setex(cache_key,expire_sec,base64.b64encode(gzip.compress(body)).decode())
      response=Response(content=body, status_code=response.status_code, media_type=response.media_type)
   return response

import jwt,json,time
async def function_token_encode(user,config_key_jwt,config_token_expire_sec):
   data={"id":user["id"],"is_active":user.get("is_active"),"api_access":user.get("api_access")}
   data=json.dumps(data,default=str)
   token=jwt.encode({"exp":time.time()+config_token_expire_sec,"data":data},config_key_jwt)
   return token

import jwt,json
async def function_token_decode(token,config_key_jwt):
   user=json.loads(jwt.decode(token,config_key_jwt,algorithms="HS256")["data"])
   return user

async def function_token_check(request,config_key_root,config_key_jwt,function_token_decode):
   user={}
   api=request.url.path
   token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and "Bearer " in request.headers.get("Authorization") else None
   if "root/" in api:
      if token!=config_key_root:raise Exception("token root mismatch")
   else:
      if any(path in api for path in ["my/", "private/", "admin/"]) and not token:raise Exception("token missing")
      if token:user=await function_token_decode(token,config_key_jwt)
   return user

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

import hashlib
async def function_signup_username_password(type,username,password,client_postgres):
   query="insert into users (type,username,password) values (:type,:username,:password) returning *;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   return output[0]

async def function_signup_username_password_bigint(type,username_bigint,password_bigint,client_postgres):
   query="insert into users (type,username_bigint,password_bigint) values (:type,:username_bigint,:password_bigint) returning *;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await client_postgres.fetch_all(query=query,values=values)
   return output[0]

import hashlib
async def function_login_password_username(type,password,username,client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode):
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

import hashlib
async def function_login_password_username_bigint(type,password_bigint,username_bigint,client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode):
   query=f"select * from users where type=:type and username_bigint=:username_bigint and password_bigint=:password_bigint order by id desc limit 1;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

import hashlib
async def function_login_password_email(type,password,email,client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode):
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

import hashlib
async def function_login_password_mobile(type,password,mobile,client_postgres,config_key_jwt,config_token_expire_sec,function_token_encode):
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

async def function_login_otp_email(type,email,otp,client_postgres,config_key_jwt,config_token_expire_sec,function_verify_otp,function_token_encode):
   await function_verify_otp(client_postgres,otp,email,None)
   query=f"select * from users where type=:type and email=:email order by id desc limit 1;"
   values={"type":type,"email":email}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,email) values (:type,:email) returning *;"
      values={"type":type,"email":email}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

async def function_login_otp_mobile(type,mobile,otp,client_postgres,config_key_jwt,config_token_expire_sec,function_verify_otp,function_token_encode):
   await function_verify_otp(client_postgres,otp,None,mobile)
   query=f"select * from users where type=:type and mobile=:mobile order by id desc limit 1;"
   values={"type":type,"mobile":mobile}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,mobile) values (:type,:mobile) returning *;"
      values={"type":type,"mobile":mobile}
      output=await client_postgres.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_request
async def function_login_google(type,google_token,client_postgres,config_key_jwt,config_token_expire_sec,config_google_login_client_id,function_token_encode):
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
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec)
   return token

async def function_message_inbox_user(user_id,order,limit,offset,is_unread,client_postgres):
   if not is_unread:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {offset};'''
   elif int(is_unread)==1:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {offset};'''
   values={"created_by_id":user_id,"user_id":user_id}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

async def function_message_received_user(user_id,order,limit,offset,is_unread,client_postgres):
   if not is_unread:query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {offset};"
   elif int(is_unread)==1:query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {offset};"
   values={"user_id":user_id}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

async def function_message_thread_user(user_id_1,user_id_2,order,limit,offset,client_postgres):
   query=f"select * from message where ((created_by_id=:user_id_1 and user_id=:user_id_2) or (created_by_id=:user_id_2 and user_id=:user_id_1)) order by {order} limit {limit} offset {offset};"
   values={"user_id_1":user_id_1,"user_id_2":user_id_2}
   object_list=await client_postgres.fetch_all(query=query,values=values)
   return object_list

async def function_message_thread_mark_read(user_id_1,user_id_2,client_postgres):
   query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;"
   values={"created_by_id":user_id_2,"user_id":user_id_1}
   await client_postgres.execute(query=query,values={})
   return None

async def function_message_object_mark_read(object_list,client_postgres):
   try:
      ids=','.join([str(item['id']) for item in object_list])
      query=f"update message set is_read=1 where id in ({ids});"
      await client_postgres.execute(query=query,values={})
   except Exception as e:print(str(e))
   return None

async def function_message_delete_single_user(user_id,message_id,client_postgres):
   query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id,"id":message_id}
   await client_postgres.execute(query=query,values={})
   return None

async def function_message_delete_created_user(user_id,client_postgres):
   query="delete from message where created_by_id=:user_id;"
   values={"user_id":user_id}
   await client_postgres.execute(query=query,values={})
   return None

async def function_message_delete_received_user(user_id,client_postgres):
   query="delete from message where user_id=:user_id;"
   values={"user_id":user_id}
   await client_postgres.execute(query=query,values={})
   return None

async def function_message_delete_all_user(user_id,client_postgres):
   query="delete from message where (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id}
   await client_postgres.execute(query=query,values={})
   return None

import datetime
async def function_update_last_active_at_user(user_id,client_postgres):
   try:
      query="update users set last_active_at=:last_active_at where id=:id;"
      values={"id":user_id,"last_active_at":datetime.datetime.now()}
      await client_postgres.execute(query=query,values=values)
   except Exception as e:print(str(e))
   return None

async def function_read_user_single(user_id,client_postgres):
   query="select * from users where id=:id;"
   values={"id":user_id}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=dict(output[0]) if output else None
   if not user:raise Exception("user not found")
   return user

async def function_delete_user_single(mode,user_id,client_postgres):
   if mode=="soft":query="update users set is_deleted=1 where id=:id;"
   if mode=="hard":query="delete from users where id=:id;"
   values={"id":user_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_update_ids(table,ids,column,value,updated_by_id,created_by_id,client_postgres):
   query=f"update {table} set {column}=:value,updated_by_id=:updated_by_id where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"value":value,"created_by_id":created_by_id,"updated_by_id":updated_by_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_delete_ids(table,ids,created_by_id,client_postgres):
   query=f"delete from {table} where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"created_by_id":created_by_id}
   await client_postgres.execute(query=query,values=values)
   return None

async def function_query_runner(query,user_id,client_postgres):
   danger_word=["drop","truncate"]
   stop_word=["drop","delete","update","insert","alter","truncate","create", "rename","replace","merge","grant","revoke","execute","call","comment","set","disable","enable","lock","unlock"]
   must_word=["select"]
   for item in danger_word:
      if item in query.lower():raise Exception(f"{item} keyword not allowed in query")
   if user_id!=1:
      for item in stop_word:
         if item in query.lower():raise Exception(f"{item} keyword not allowed in query")
      for item in must_word:
         if item not in query.lower():raise Exception(f"{item} keyword not allowed in query")
   output=await client_postgres.fetch_all(query=query,values={})
   return output

async def function_add_creator_data(object_list,user_key,client_postgres):
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
 
async def function_ownership_check(table,id,user_id,client_postgres):
   if table=="users":
      if id!=user_id:raise Exception("object ownership issue")
   if table!="users":
      query=f"select created_by_id from {table} where id=:id;"
      values={"id":id}
      output=await client_postgres.fetch_all(query=query,values=values)
      if not output:raise Exception("no object")
      if output[0]["created_by_id"]!=user_id:raise Exception("object ownership issue")
   return None

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

async def function_postgres_schema_init(client_postgres,config_postgres,function_postgres_schema_read):
   async def init_extension(client_postgres):
      await client_postgres.execute(query="create extension if not exists postgis;",values={})
      await client_postgres.execute(query="create extension if not exists pg_trgm;",values={})
   async def init_table(client_postgres,function_postgres_schema_read,config_postgres):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      for table,column_list in config_postgres["table"].items():
         is_table=postgres_schema.get(table,{})
         if not is_table:
            query=f"create table if not exists {table} (id bigint primary key generated always as identity not null);"
            await client_postgres.execute(query=query,values={})
   async def init_column(client_postgres,function_postgres_schema_read,config_postgres):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      for table,column_list in config_postgres["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            is_column=postgres_schema.get(table,{}).get(column_name,{})
            if not is_column:
               query=f"alter table {table} add column if not exists {column_name} {column_datatype};"
               await client_postgres.execute(query=query,values={})
   async def init_nullable(client_postgres,function_postgres_schema_read,config_postgres):
      postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
      for table,column_list in config_postgres["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            is_null=postgres_schema.get(table,{}).get(column_name,{}).get("is_null",None)
            if column_is_mandatory=="0" and is_null==0:
               query=f"alter table {table} alter column {column_name} drop not null;"
               await client_postgres.execute(query=query,values={})
            if column_is_mandatory=="1" and is_null==1:
               query=f"alter table {table} alter column {column_name} set not null;"
               await client_postgres.execute(query=query,values={})
   async def init_index(client_postgres,config_postgres):
      index_name_list=[object["indexname"] for object in (await client_postgres.fetch_all(query="SELECT indexname FROM pg_indexes WHERE schemaname='public';",values={}))]
      for table,column_list in config_postgres["table"].items():
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
   async def init_query(client_postgres,config_postgres):
      constraint_name_list={object["constraint_name"].lower() for object in (await client_postgres.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))}
      for query in config_postgres["query"].values():
         if query.split()[0]=="0":continue
         if "add constraint" in query.lower() and query.split()[5].lower() in constraint_name_list:continue
         await client_postgres.fetch_all(query=query,values={})
   await init_extension(client_postgres)
   await init_table(client_postgres,function_postgres_schema_read,config_postgres)
   await init_column(client_postgres,function_postgres_schema_read,config_postgres)
   await init_nullable(client_postgres,function_postgres_schema_read,config_postgres)
   await init_index(client_postgres,config_postgres)
   await init_query(client_postgres,config_postgres)
   return None

import asyncio,json
async def function_consumer_kafka(config_kafka_url,config_kafka_path_cafile,config_kafka_path_certfile,config_kafka_path_keyfile,config_channel_name,config_postgres_url,function_kafka_consumer_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize):
   kafka_consumer_client=await function_kafka_consumer_client_read(config_kafka_url,config_kafka_path_cafile,config_kafka_path_certfile,config_kafka_path_keyfile,config_channel_name)
   client_postgres=await function_postgres_client_read(config_postgres_url)
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
   try:
      async for message in kafka_consumer_client:
         if message.topic==config_channel_name:
            data=json.loads(message.value.decode('utf-8'))
            try:
               if data["mode"]=="create":output=await function_postgres_create(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)   
               if data["mode"]=="update":output=await function_postgres_update(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
               print(output)
            except Exception as e:print(str(e))
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await client_postgres.disconnect()
      await kafka_consumer_client.stop()

import asyncio,json
async def function_consumer_redis(config_redis_url,config_channel_name,config_postgres_url,function_redis_client_read,function_redis_consumer_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize):
   client_redis=await function_redis_client_read(config_redis_url)
   redis_consumer_client=await function_redis_consumer_client_read(client_redis,config_channel_name)
   client_postgres=await function_postgres_client_read(config_postgres_url)
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
   try:
      async for message in redis_consumer_client.listen():
         if message["type"]=="message" and message["channel"]==config_channel_name.encode():
            data=json.loads(message['data'])
            try:
               if data["mode"]=="create":output=await function_postgres_create(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
               if data["mode"]=="update":output=await function_postgres_update(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
               print(output)
            except Exception as e:print(str(e))
   except asyncio.CancelledError:print("subscription cancelled")
   finally:
      await client_postgres.disconnect()
      await redis_consumer_client.unsubscribe(config_channel_name)
      await client_redis.aclose()
      
import aio_pika,asyncio,json
async def function_consumer_rabbitmq(config_rabbitmq_url,config_channel_name,config_postgres_url,function_rabbitmq_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize):
   client_rabbitmq,client_rabbitmq_channel=await function_rabbitmq_client_read(config_rabbitmq_url)
   client_postgres=await function_postgres_client_read(config_postgres_url)
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
   async def aqmp_callback(message: aio_pika.IncomingMessage):
      async with message.process():
         try:
            data=json.loads(message.body)
            mode=data.get("mode")
            if mode=="create":output=await function_postgres_create(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
            elif mode=="update":output=await function_postgres_update(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
            else:output=f"Unsupported mode: {mode}"
            print(output)
         except Exception as e:print("Callback function_error:",e.args)
   try:
      queue=await client_rabbitmq_channel.declare_queue(config_channel_name,auto_delete=False)
      await queue.consume(aqmp_callback)
      await asyncio.Future()
   except KeyboardInterrupt:
      await client_postgres.disconnect()
      await client_rabbitmq_channel.close()
      await client_rabbitmq.close()

import aio_pika,asyncio,json
async def function_consumer_lavinmq(config_lavinmq_url,config_channel_name,config_postgres_url,function_lavinmq_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize):
   client_lavinmq,client_lavinmq_channel=await function_lavinmq_client_read(config_lavinmq_url)
   client_postgres=await function_postgres_client_read(config_postgres_url)
   postgres_schema,postgres_column_datatype=await function_postgres_schema_read(client_postgres)
   async def aqmp_callback(message: aio_pika.IncomingMessage):
      async with message.process():
         try:
            data=json.loads(message.body)
            mode=data.get("mode")
            if mode=="create":output=await function_postgres_create(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
            elif mode=="update":output=await function_postgres_update(data["table"],[data["object"]],data["is_serialize"],client_postgres,postgres_column_datatype,function_object_serialize)
            else:output=f"Unsupported mode: {mode}"
            print(output)
         except Exception as e:print("Callback function_error:",e.args)
   try:
      queue=await client_lavinmq_channel.declare_queue(config_channel_name,auto_delete=False)
      await queue.consume(aqmp_callback)
      await asyncio.Future()
   except KeyboardInterrupt:
      await client_postgres.disconnect()
      await client_lavinmq_channel.close()
      await client_lavinmq.close()
      
def function_numeric_converter(mode,x):
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

def function_bigint_converter(mode,x):
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
def function_export_grafana_dashboards(host,username,password,max_limit,export_dir):
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
      path = os.path.join(export_dir, sanitize(org_name), sanitize(folder_name or "General"))
      ensure_dir(path)
      file_path = os.path.join(path, f"{sanitize(dashboard_meta['title'])}.json")
      with open(file_path, "w", encoding="utf-8") as f:json.dump(data, f, indent=2)
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