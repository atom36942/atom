#custom
async def function_extend_client():
   output={}
   return output

#utility
import sys
def function_check_required_env(config, required_keys):
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return None

import os
def function_delete_files(folder_path=".", extension_list=None, file_prefix_list=None):
    if extension_list is None:
        extension_list = []
    if file_prefix_list is None:
        file_prefix_list = []
    skip_dirs = ('venv', 'env', '__pycache__', 'node_modules')
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not (d.startswith('.') or d.lower() in skip_dirs)]
        for filename in files:
            if any(filename.endswith(ext) for ext in extension_list) or any(filename.startswith(prefix) for prefix in file_prefix_list):
                file_path = os.path.join(root, filename)
                os.remove(file_path)
    return None

import os
def function_export_directory_filename(dir_path=".",output_path="export_filename.txt"):
    skip_dirs = {"venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache", "node_modules"}
    dir_path = os.path.abspath(dir_path)
    with open(output_path, "w") as out_file:
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, dir_path)
                out_file.write(rel_path + "\n")
    print(f"Saved to: {output_path}")
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

import os
from dotenv import load_dotenv, dotenv_values
import importlib.util
from pathlib import Path
import traceback
def function_config_read():
    base_dir = Path(__file__).resolve().parent
    def read_env_file():
        env_path = base_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return {k.lower(): v for k, v in dotenv_values(env_path).items()}
        return {}
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
                except Exception:
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
                except Exception:
                    print(f"[WARN] Failed to load config folder file: {module_path}")
                    traceback.print_exc()
        return output
    output = {}
    output.update(read_env_file())
    output.update(read_root_config_py_files())
    output.update(read_config_folder_files())
    return output

#api
import csv,io
async def function_file_to_object_list(file):
   content=await file.read()
   content=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(content))
   object_list=[row for row in reader]
   await file.close()
   return object_list

import os
async def function_stream_file(path,chunk_size=1024*1024):
   with open(path, "rb") as f:
      while chunk := f.read(chunk_size):
         yield chunk

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

#converter
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
from sentry_sdk.integrations.fastapi import FastApiIntegration
def function_add_sentry(config_sentry_dsn):
   sentry_sdk.init(dsn=config_sentry_dsn,integrations=[FastApiIntegration()],traces_sample_rate=1.0,profiles_sample_rate=1.0,send_default_pii=True)
   return None

import os
import importlib.util
from pathlib import Path
import traceback
def function_add_router(app,pattern):
   base_dir = Path(__file__).parent
   def load_module(module_path):
      try:
         rel_path = os.path.relpath(module_path, base_dir)
         module_name = os.path.splitext(rel_path)[0].replace(os.sep, ".")
         if not module_name.strip():
            return
         spec = importlib.util.spec_from_file_location(module_name, module_path)
         if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, pattern):
               app.include_router(module.router)
      except Exception as e:
         print(f"[WARN] Failed to load router module: {module_path}")
         traceback.print_exc()
   def add_root_pattern_files():
      for file in os.listdir(base_dir):
         if file.startswith(pattern) and file.endswith(".py"):
            module_path = base_dir / file
            load_module(module_path)
   def add_pattern_folder_files():
      router_dir = base_dir / pattern
      if router_dir.exists() and router_dir.is_dir():
         for file in os.listdir(router_dir):
            if file.endswith(".py"):
               module_path = router_dir / file
               load_module(module_path)
   add_root_pattern_files()
   add_pattern_folder_files()
   return None

#posthog
from posthog import Posthog
async def function_posthog_client_read(config_posthog_project_host,config_posthog_project_key):
   client_posthog=Posthog(config_posthog_project_key,host=config_posthog_project_host)
   return client_posthog

#mongodb
import motor.motor_asyncio
async def function_mongodb_client_read(config_mongodb_url):
   client_mongodb=motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
   return client_mongodb

#ocr
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
def function_export_ocr_tesseract(file_path, output_path="export_ocr.txt"):
    if file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path)
        text = ''
        for img in images:
            text += pytesseract.image_to_string(img, lang='eng') + '\n'
    else:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='eng')
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved to: {output_path}")
    return None
 
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

#aws
import boto3
async def function_ses_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name):
   client_ses=boto3.client("ses",region_name=config_ses_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_ses

import boto3
async def function_sns_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name):
   client_sns=boto3.client("sns",region_name=config_sns_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_sns

import boto3
async def function_s3_client_read(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name):
   client_s3=boto3.client("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   client_s3_resource=boto3.resource("s3",region_name=config_s3_region_name,config_aws_access_key_id=config_aws_access_key_id,config_aws_secret_access_key=config_aws_secret_access_key)
   return client_s3,client_s3_resource

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

import uuid
from io import BytesIO
async def function_s3_upload_file(bucket,key,file,client_s3,config_s3_region_name,config_limit_s3_kb=100):
    if not key:
        if "." not in file.filename:raise Exception("file must have extension")
        key=f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}"
    if "." not in key:raise Exception("extension must")
    file_content=await file.read()
    file.file.close()
    file_size_kb=round(len(file_content)/1024)
    if file_size_kb>config_limit_s3_kb:raise Exception("file size issue")
    client_s3.upload_fileobj(BytesIO(file_content),bucket,key)
    output={file.filename:f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"}
    return output

import uuid
async def function_s3_upload_presigned(bucket,key,client_s3,config_s3_region_name,config_limit_s3_kb=100,config_s3_presigned_expire_sec=60):
   if not key:key=f"{uuid.uuid4().hex}.bin"
   if "." not in key:raise Exception("extension must")
   output=client_s3.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=config_s3_presigned_expire_sec,Conditions=[['content-length-range',1,config_limit_s3_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{key}"
   return output

#openai
from openai import OpenAI
def function_openai_client_read(config_openai_key):
   client_openai=OpenAI(api_key=config_openai_key)
   return client_openai

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

#grafana
import os, json, requests
def function_export_grafana_dashboard(host, username, password, max_limit, output_path="export_grafana"):
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
        if r.status_code == 422:
            return []
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
        path = os.path.join(output_path, sanitize(org_name), sanitize(folder_name or "General"))
        ensure_dir(path)
        file_path = os.path.join(path, f"{sanitize(dashboard_meta['title'])}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_only, f, indent=2)
        print(f"✅ {org_name}/{folder_name}/{dashboard_meta['title']}")
    try:
        orgs = get_organizations()
    except Exception as e:
        print("❌ Failed to fetch organizations:", e)
        return
    for org in orgs:
        if not switch_org(org["id"]):
            continue
        try:
            dashboards = get_dashboards(org["id"])
        except Exception as e:
            print("❌ Failed to fetch dashboards:", e)
            continue
        for dash in dashboards:
            try:
                export_dashboard(org["name"], dash.get("folderTitle", "General"), dash)
            except Exception as e:
                print("❌ Failed to export", dash.get("title"), ":", e)
    print(f"Saved to: {output_path}")
    return None

#jira
from jira import JIRA
import pandas as pd
from datetime import date
import calendar
def function_export_jira_worklog(jira_base_url, jira_email, jira_token, start_date=None, end_date=None, output_path="export_jira_worklog.csv"):
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day).strftime("%Y-%m-%d")
    jira = JIRA(server=jira_base_url, basic_auth=(jira_email, jira_token))
    issues = jira.search_issues(f"worklogDate >= {start_date} AND worklogDate <= {end_date}", maxResults=False, expand="worklog")
    data, assignees = [], set()
    for i in issues:
        if i.fields.assignee:
            assignees.add(i.fields.assignee.displayName)
        for wl in i.fields.worklog.worklogs:
            wl_date = wl.started[:10]
            if start_date <= wl_date <= end_date:
                data.append((wl.author.displayName, wl_date, wl.timeSpentSeconds / 3600))
    df = pd.DataFrame(data, columns=["author","date","hours"])
    df_pivot = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0)
    df_pivot = df_pivot.reindex(assignees, fill_value=0).round(0).astype(int)
    df_pivot.to_csv(output_path)
    return f"saved to {output_path}"

import requests, csv
from requests.auth import HTTPBasicAuth
def function_export_jira_filter_count(jira_base_url, jira_email, jira_token, output_path="export_jira_filter_count.csv"):
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {"Accept": "application/json"}
    resp = requests.get(f"{jira_base_url}/rest/api/3/filter/my", headers=headers, auth=auth, params={"maxResults": 1000})
    if resp.status_code != 200:
        return f"error {resp.status_code}: {resp.text}"
    data = resp.json()
    filters = sorted(data, key=lambda x: x.get("name", "").lower())
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filter_name", "issue_count"])
        for flt in filters:
            jql_url = f"{jira_base_url}/rest/api/3/search"
            jql_params = {"jql": flt.get("jql", ""), "maxResults": 0}
            jql_resp = requests.get(jql_url, headers=headers, auth=auth, params=jql_params)
            count = jql_resp.json().get("total", 0) if jql_resp.status_code == 200 else f"error {jql_resp.status_code}"
            writer.writerow([flt.get("name", ""), count])
    return f"saved to {output_path}"

import requests, datetime, re
from collections import defaultdict, Counter
from openai import OpenAI
def function_export_jira_summary(jira_base_url,jira_email,jira_token,jira_project_key_list,jira_max_issues_per_status,openai_key,output_path="export_jira_summary.txt"):
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
    def save_summary_to_file(blockers, improvements, top_active, on_time, filename=output_path):
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
    return f"saved to {output_path}"