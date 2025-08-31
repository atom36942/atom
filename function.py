#custom
async def function_extend_client():
   output={}
   return output

#utility
async def function_param_read(request, mode, config):
    if mode == "query":
        param = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        param = {k: v for k, v in form_data.items() if isinstance(v, str)}
        param.update({
            k: [f for f in form_data.getlist(k) if getattr(f, "filename", None)]
            for k in form_data.keys()
            if any(getattr(f, "filename", None) for f in form_data.getlist(k))
        })
    elif mode == "body":
        param = await request.json()
    else:
        raise Exception(f"Invalid mode: {mode}")
    def cast(value, dtype):
        if dtype == "int":
            return int(value)
        if dtype == "float":
            return float(value)
        if dtype == "bool":
            return str(value).lower() in ("1", "true", "yes", "on")
        if dtype == "list":
            if isinstance(value, str):
                return [v.strip() for v in value.split(",")]
            if isinstance(value, list):
                return value
            return [value]
        if dtype == "file":
            return value if isinstance(value, list) else [value]
        return value
    for key, dtype, mandatory, default in config:
        if mandatory and key not in param:
            raise Exception(f"{key} missing from {mode} param")
        value = param.get(key, default)
        if dtype and value is not None:
            try:
                value = cast(value, dtype)
            except Exception:
                raise Exception(f"{key} must be of type {dtype}")
        param[key] = value
    return param
 
import os
def function_render_html(name: str):
    if ".." in name: 
        raise Exception("invalid name")
    match = None
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "venv"]
        if f"{name}.html" in files:
            match = os.path.join(root, f"{name}.html")
            break
    if not match: 
        raise Exception("file not found")
    with open(match, "r", encoding="utf-8") as file:
        return file.read()

#mongodb
import motor.motor_asyncio
async def function_mongodb_client_read(config_mongodb_url):
   client_mongodb=motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
   return client_mongodb

#aws
import boto3
async def function_aws_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name):
   client_ses=boto3.client("ses",region_name=config_ses_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_ses

import boto3
async def function_aws_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name):
   client_sns=boto3.client("sns",region_name=config_sns_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_sns

import boto3
async def function_aws_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name):
   client_s3=boto3.client("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   client_s3_resource=boto3.resource("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_s3,client_s3_resource

#gsheet
import gspread
from google.oauth2.service_account import Credentials
async def function_gsheet_client_read(config_gsheet_service_account_json_path,config_gsheet_scope_list):
   client_gsheet=gspread.authorize(Credentials.from_service_account_file(config_gsheet_service_account_json_path,scopes=config_gsheet_scope_list))
   return client_gsheet

async def function_gsheet_object_read(client_gsheet,spreadsheet_id,sheet_name,cell_boundary):
   worksheet=client_gsheet.open_by_key(spreadsheet_id).worksheet(sheet_name)
   if cell_boundary:output=worksheet.get(cell_boundary)
   else:output=worksheet.get_all_records()
   return output

#openai
from openai import OpenAI
def function_openai_client_read(config_openai_key):
   client_openai=OpenAI(api_key=config_openai_key)
   return client_openai

#posthog
from posthog import Posthog
async def function_posthog_client_read(config_posthog_project_host,config_posthog_project_key):
   client_posthog=Posthog(config_posthog_project_key,host=config_posthog_project_host)
   return client_posthog

#redis
import redis.asyncio as redis
async def function_redis_client_read(config_redis_url):
   client_redis=redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))
   return client_redis

async def function_redis_client_read_consumer(client_redis,channel_name):
   client_redis_consumer=client_redis.pubsub()
   await client_redis_consumer.subscribe(channel_name)
   return client_redis_consumer

import json
async def function_redis_producer(client_redis,channel_name,payload):
   output=await client_redis.publish(channel_name,json.dumps(payload))
   return output

import json
async def function_redis_object_read(client_redis,key):
   output=await client_redis.get(key)
   if output:output=json.loads(output)
   return output

#celery
from celery import Celery
async def function_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url):
   client_celery_producer=Celery("producer",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_producer

from celery import Celery
def function_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url):
   client_celery_consumer=Celery("worker",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_consumer

async def function_celery_producer(client_celery_producer,function,param_list):
   output=client_celery_producer.send_task(function,args=param_list)
   return output.id

#kafka
from aiokafka import AIOKafkaProducer
async def function_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password):
    client_kafka_producer=AIOKafkaProducer(bootstrap_servers=config_kafka_url,security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,)
    await client_kafka_producer.start()
    return client_kafka_producer
 
from aiokafka import AIOKafkaConsumer
async def function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,topic_name,group_id,enable_auto_commit):
    client_kafka_consumer=AIOKafkaConsumer(topic_name,bootstrap_servers=config_kafka_url,group_id=group_id, security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,auto_offset_reset="earliest",enable_auto_commit=enable_auto_commit)
    await client_kafka_consumer.start()
    return client_kafka_consumer
 
import json
async def function_kafka_producer(client_kafka_producer,channel_name,payload):
   output=await client_kafka_producer.send_and_wait(channel_name,json.dumps(payload,indent=2).encode('utf-8'),partition=0)
   return output

#rabbitmq
import aio_pika
async def function_rabbitmq_client_read_producer(config_rabbitmq_url):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_producer=await client_rabbitmq.channel()
   return client_rabbitmq,client_rabbitmq_producer

import aio_pika
async def function_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_channel=await client_rabbitmq.channel()
   client_rabbitmq_consumer=await client_rabbitmq_channel.declare_queue(config_channel_name,auto_delete=False)
   return client_rabbitmq,client_rabbitmq_consumer

import json,aio_pika
async def function_rabbitmq_producer(client_rabbitmq_producer,channel_name,payload):
    body=json.dumps(payload).encode()
    message=aio_pika.Message(body=body)
    output=await client_rabbitmq_producer.default_exchange.publish(message,routing_key=channel_name)
    return output

