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
async def function_login_password_username(type,password,username,client_postgres,config_key_jwt,config_token_expire_sec,function_token_create):
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return token

import hashlib
async def function_login_password_username_bigint(type,password_bigint,username_bigint,client_postgres,config_key_jwt,config_token_expire_sec,function_token_create):
   query=f"select * from users where type=:type and username_bigint=:username_bigint and password_bigint=:password_bigint order by id desc limit 1;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return token

import hashlib
async def function_login_password_email(type,password,email,client_postgres,config_key_jwt,config_token_expire_sec,function_token_create):
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return token

import hashlib
async def function_login_password_mobile(type,password,mobile,client_postgres,config_key_jwt,config_token_expire_sec,function_token_create):
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await client_postgres.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return token

async def function_login_otp_email(type,email,otp,client_postgres,config_key_jwt,config_token_expire_sec,function_verify_otp,function_token_create):
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
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return token

async def function_login_otp_mobile(type,mobile,otp,client_postgres,config_key_jwt,config_token_expire_sec,function_verify_otp,function_token_create):
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
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
   return token

import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_request
async def function_login_google(type,google_token,client_postgres,config_key_jwt,config_token_expire_sec,config_google_login_client_id,function_token_create):
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
   token=await function_token_create(config_key_jwt,config_token_expire_sec,user)
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

async def function_message_thread_mark_read_user(user_id_1,user_id_2,client_postgres):
   query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;"
   values={"created_by_id":user_id_2,"user_id":user_id_1}
   await client_postgres.execute(query=query,values={})
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
