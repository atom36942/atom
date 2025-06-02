import asyncpg,random
from mimesis import Person,Address,Food,Text,Code,Datetime
async def generate_fake_data(postgres_url,TOTAL_ROWS,BATCH_SIZE):
   conn = await asyncpg.connect(postgres_url)
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
   async def create_tables(conn,TABLES):
      for table_name, columns in TABLES.items():
         await conn.execute(f"DROP TABLE IF EXISTS {table_name};")
         columns_def = ", ".join(f"{name} {dtype}" for name, dtype, _ in columns)
         query = f"CREATE TABLE IF NOT EXISTS {table_name} (id bigint primary key generated always as identity not null, {columns_def});"
         await conn.execute(query)
   async def insert_batch(conn, table_name, columns, batch_values):
      cols = ", ".join(name for name, _, _ in columns)
      placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
      query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
      await conn.executemany(query, batch_values)
   async def generate_data(conn,insert_batch,TABLES,TOTAL_ROWS,BATCH_SIZE):
      for table_name, columns in TABLES.items():
         print(f"Inserting data into {table_name}...")
         batch_values = []
         for _ in range(TOTAL_ROWS):
               row = tuple(gen() for _, _, gen in columns)
               batch_values.append(row)
               if len(batch_values) == BATCH_SIZE:
                  await insert_batch(conn, table_name, columns, batch_values)
                  batch_values.clear()
         if batch_values:await insert_batch(conn, table_name, columns, batch_values)
         print(f"Completed inserting {TOTAL_ROWS} rows into {table_name}")
   await create_tables(conn,TABLES)
   await generate_data(conn,insert_batch,TABLES,TOTAL_ROWS,BATCH_SIZE)
   await conn.close()
   return None

async def bigint_converter(mode,x):
   CHARSET = 'abcdefghijklmnopqrstuvwxyz0123456789_'
   BASE = len(CHARSET)
   MAX_LENGTH = 11
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

import httpx
async def send_email_resend(resend_key,resend_url,sender_email,email_list,title,body):
   payload={"from":sender_email,"to":email_list,"subject":title,"html":body}
   headers={"Authorization":f"Bearer {resend_key}","Content-Type": "application/json"}
   async with httpx.AsyncClient() as client:
      output=await client.post(resend_url,json=payload,headers=headers)
   if output.status_code!=200:raise Exception(f"{output.text}")
   return None

import gspread
from google.oauth2.service_account import Credentials
async def gsheet_client_read(gsheet_service_account_json_path,gsheet_scope_list):
   gsheet_client=gspread.authorize(Credentials.from_service_account_file(gsheet_service_account_json_path,scopes=gsheet_scope_list))
   return gsheet_client

async def gsheet_create(gsheet_client,spreadsheet_id,sheet_name,object):
   row=[object[key] for key in sorted(object.keys())]
   output=gsheet_client.open_by_key(spreadsheet_id).worksheet(sheet_name).append_row(row)
   return output

async def gsheet_read_service_account(gsheet_client,spreadsheet_id,sheet_name,cell_boundary):
   worksheet=gsheet_client.open_by_key(spreadsheet_id).worksheet(sheet_name)
   if cell_boundary:output=worksheet.get(cell_boundary)
   else:output=worksheet.get_all_records()
   return output

import pandas
async def gsheet_read_pandas(spreadsheet_id,gid):
   url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
   df=pandas.read_csv(url)
   output=df.to_dict(orient="records")
   return output

async def openai_prompt(openai_client,model,prompt,is_web_search,previous_response_id):
   if not openai_client or not model or not prompt:raise Exception("param missing")
   params={"model":model,"input":prompt}
   if is_web_search==1:params["tools"]=[{"type":"web_search"}]
   if previous_response_id:params["previous_response_id"]=previous_response_id
   output=openai_client.responses.create(**params)
   return output

import base64
async def openai_ocr(openai_client,model,prompt,file):
   contents=await file.read()
   b64_image=base64.b64encode(contents).decode("utf-8")
   output=openai_client.responses.create(model=model,input=[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:image/png;base64,{b64_image}"},],}],)
   return output

from databases import Database
async def postgres_client_read(postgres_url):
   postgres_client=Database(postgres_url,min_size=1,max_size=100)
   await postgres_client.connect()
   return postgres_client

import asyncpg
async def postgres_client_asyncpg_read(postgres_url):
   postgres_client_asyncpg=await asyncpg.connect(postgres_url)
   return postgres_client_asyncpg

import redis.asyncio as redis
async def redis_client_read(redis_url):
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))
   return redis_client

import redis.asyncio as redis
async def redis_pubsub_read(redis_url,channel_name):
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.subscribe(channel_name)
   return redis_client,redis_pubsub

import motor.motor_asyncio
async def mongodb_client_read(mongodb_url):
   mongodb_client=motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
   return mongodb_client

import boto3
async def s3_client_read(s3_region_name,aws_access_key_id,aws_secret_access_key):
   s3_client=boto3.client("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   s3_resource=boto3.resource("s3",region_name=s3_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return s3_client,s3_resource

import boto3
async def sns_client_read(sns_region_name,aws_access_key_id,aws_secret_access_key):
   sns_client=boto3.client("sns",region_name=sns_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return sns_client

import boto3
async def ses_client_read(ses_region_name,aws_access_key_id,aws_secret_access_key):
   ses_client=boto3.client("ses",region_name=ses_region_name,aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
   return ses_client

import pika
async def rabbitmq_client_read(rabbitmq_url,channel_name):
   rabbitmq_client=pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
   rabbitmq_channel=rabbitmq_client.channel()
   rabbitmq_channel.queue_declare(queue=channel_name)
   return rabbitmq_client,rabbitmq_channel

import pika
async def lavinmq_client_read(lavinmq_url,channel_name):
   lavinmq_client=pika.BlockingConnection(pika.URLParameters(lavinmq_url))
   lavinmq_channel=lavinmq_client.channel()
   lavinmq_channel.queue_declare(queue=channel_name)
   return lavinmq_client,lavinmq_channel

from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_ssl_context
async def kafka_producer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name):
   context=create_ssl_context(cafile=kafka_path_cafile,certfile=kafka_path_certfile,keyfile=kafka_path_keyfile)
   kafka_producer_client=AIOKafkaProducer(bootstrap_servers=kafka_url,security_protocol="SSL",ssl_context=context)
   await kafka_producer_client.start()
   return kafka_producer_client

from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def kafka_consumer_client_read(kafka_url,kafka_path_cafile,kafka_path_certfile,kafka_path_keyfile,channel_name):
   context=create_ssl_context(cafile=kafka_path_cafile,certfile=kafka_path_certfile,keyfile=kafka_path_keyfile)
   kafka_consumer_client=AIOKafkaConsumer(channel_name,bootstrap_servers=kafka_url,security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
   await kafka_consumer_client.start()
   return kafka_consumer_client

async def postgres_create(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   column_insert_list=list(object_list[0].keys())
   query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_update(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_update_user(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize,user_id):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   column_update_list=[*object_list[0]]
   column_update_list.remove("id")
   query=f"update {table} set {','.join([f'{item}=:{item}' for item in column_update_list])} where id=:id and created_by_id={user_id} returning *;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_delete(table,object_list,is_serialize,postgres_client,postgres_column_datatype,object_serialize):
   if is_serialize:object_list=await object_serialize(object_list,postgres_column_datatype)
   query=f"delete from {table} where id=:id;"
   if len(object_list)==1:
      output=await postgres_client.execute(query=query,values=object_list[0])
   else:
      async with postgres_client.transaction():output=await postgres_client.execute_many(query=query,values=object_list)
   return output

async def postgres_delete_any(table,object,postgres_client,create_where_string,object_serialize,postgres_column_datatype):
   where_string,where_value=await create_where_string(object,object_serialize,postgres_column_datatype)
   query=f"delete from {table} {where_string};"
   await postgres_client.execute(query=query,values=where_value)
   return None

async def postgres_read(table,object,postgres_client,postgres_column_datatype,object_serialize,create_where_string):
   order,limit,page=object.get("order","id desc"),int(object.get("limit",100)),int(object.get("page",1))
   column=object.get("column","*")
   location_filter=object.get("location_filter")
   if location_filter:
      location_filter_split=location_filter.split(",")
      long,lat,min_meter,max_meter=float(location_filter_split[0]),float(location_filter_split[1]),int(location_filter_split[2]),int(location_filter_split[3])
   where_string,where_value=await create_where_string(object,object_serialize,postgres_column_datatype)
   if location_filter:query=f'''with x as (select * from {table} {where_string}),y as (select *,st_distance(location,st_point({long},{lat})::geography) as distance_meter from x) select * from y where distance_meter between {min_meter} and {max_meter} order by {order} limit {limit} offset {(page-1)*limit};'''
   else:query=f"select {column} from {table} {where_string} order by {order} limit {limit} offset {(page-1)*limit};"
   object_list=await postgres_client.fetch_all(query=query,values=where_value)
   return object_list

async def postgres_parent_read(table,parent_column,parent_table,postgres_client,order,limit,offset,user_id):
   query=f'''
   with
   x as (select {parent_column} from {table} where (created_by_id=:created_by_id or :created_by_id is null) order by {order} limit {limit} offset {offset}) 
   select ct.* from x left join {parent_table}  as ct on x.{parent_column}=ct.id;
   '''
   values={"created_by_id":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

import hashlib,datetime,json
async def object_serialize(object_list,postgres_column_datatype):
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

async def create_where_string(object,object_serialize,postgres_column_datatype):
   object={k:v for k,v in object.items() if (k in postgres_column_datatype and k not in ["metadata","location","table","order","limit","page"] and v is not None)}
   where_operator={k:v.split(',',1)[0] for k,v in object.items()}
   where_value={k:v.split(',',1)[1] for k,v in object.items()}
   object_list=await object_serialize([where_value],postgres_column_datatype)
   where_value=object_list[0]
   where_string_list=[f"({key} {where_operator[key]} :{key} or :{key} is null)" for key in [*object]]
   where_string_joined=' and '.join(where_string_list)
   where_string=f"where {where_string_joined}" if where_string_joined else ""
   return where_string,where_value
   
import random
async def generate_save_otp(postgres_client,email,mobile):
   if email and mobile:raise Exception("send either email/mobile")
   if not email and not mobile:raise Exception("send either email/mobile")
   otp=random.randint(100000,999999)
   if email:
      query="insert into otp (otp,email) values (:otp,:email) returning *;"
      values={"otp":otp,"email":email.strip().lower()}
      await postgres_client.execute(query=query,values=values)
   if mobile:
      query="insert into otp (otp,mobile) values (:otp,:mobile) returning *;"
      values={"otp":otp,"mobile":mobile.strip().lower()}
      await postgres_client.execute(query=query,values=values)
   return otp
   
async def verify_otp(postgres_client,otp,email,mobile):
   if email and mobile:raise Exception("send either email/mobile")
   if not email and not mobile:raise Exception("send either email/mobile")
   if email:
      query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and email=:email order by id desc limit 1;"
      values={"email":email}
      output=await postgres_client.fetch_all(query=query,values=values)
   if mobile:
      query="select otp from otp where created_at>current_timestamp-interval '10 minutes' and mobile=:mobile order by id desc limit 1;"
      values={"mobile":mobile}
      output=await postgres_client.fetch_all(query=query,values=values)
   if not output:raise Exception("otp not found")
   if int(output[0]["otp"])!=int(otp):raise Exception("otp mismatch")
   return None

async def postgres_schema_read(postgres_client):
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
   output=await postgres_client.fetch_all(query=query,values={})
   postgres_schema={}
   for object in output:
      table,column=object["table"],object["column"]
      column_data={"datatype":object["datatype"],"default":object["default"],"is_null":object["is_null"],"is_index":object["is_index"]}
      if table not in postgres_schema:postgres_schema[table]={}
      postgres_schema[table][column]=column_data
   return postgres_schema

async def postgres_column_datatype_read(postgres_client,postgres_schema_read):
   postgres_schema=await postgres_schema_read(postgres_client)
   postgres_column_datatype={k:v["datatype"] for table,column in postgres_schema.items() for k,v in column.items()}
   return postgres_column_datatype

async def postgres_schema_init(postgres_client,postgres_schema_read,postgres_config):
   async def init_extension(postgres_client):
      await postgres_client.execute(query="create extension if not exists postgis;",values={})
      await postgres_client.execute(query="create extension if not exists pg_trgm;",values={})
   async def init_table(postgres_client,postgres_schema_read,postgres_config):
      postgres_schema=await postgres_schema_read(postgres_client)
      for table,column_list in postgres_config["table"].items():
         is_table=postgres_schema.get(table,{})
         if not is_table:
            query=f"create table if not exists {table} (id bigint primary key generated always as identity not null);"
            await postgres_client.execute(query=query,values={})
   async def init_column(postgres_client,postgres_schema_read,postgres_config):
      postgres_schema=await postgres_schema_read(postgres_client)
      for table,column_list in postgres_config["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            is_column=postgres_schema.get(table,{}).get(column_name,{})
            if not is_column:
               query=f"alter table {table} add column if not exists {column_name} {column_datatype};"
               await postgres_client.execute(query=query,values={})
   async def init_nullable(postgres_client,postgres_schema_read,postgres_config):
      postgres_schema=await postgres_schema_read(postgres_client)
      for table,column_list in postgres_config["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            is_null=postgres_schema.get(table,{}).get(column_name,{}).get("is_null",None)
            if column_is_mandatory=="0" and is_null==0:
               query=f"alter table {table} alter column {column_name} drop not null;"
               await postgres_client.execute(query=query,values={})
            if column_is_mandatory=="1" and is_null==1:
               query=f"alter table {table} alter column {column_name} set not null;"
               await postgres_client.execute(query=query,values={})
   async def init_index(postgres_client,postgres_config):
      index_name_list=[object["indexname"] for object in (await postgres_client.fetch_all(query="SELECT indexname FROM pg_indexes WHERE schemaname='public';",values={}))]
      for table,column_list in postgres_config["table"].items():
         for column in column_list:
            column_name,column_datatype,column_is_mandatory,column_index_type=column.split("-")
            if column_index_type=="0":
               query=f"DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname ILIKE 'index_{table}_{column_name}_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;"
               await postgres_client.execute(query=query,values={})
            else:
               index_type_list=column_index_type.split(",")
               for index_type in index_type_list:
                  index_name=f"index_{table}_{column_name}_{index_type}"
                  if index_name not in index_name_list:
                     if index_type=="gin":
                        query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name} gin_trgm_ops);"
                        await postgres_client.execute(query=query,values={})
                     else:
                        query=f"create index concurrently if not exists {index_name} on {table} using {index_type} ({column_name});"
                        await postgres_client.execute(query=query,values={})
   async def init_query(postgres_client,postgres_config):
      constraint_name_list={object["constraint_name"].lower() for object in (await postgres_client.fetch_all(query="select constraint_name from information_schema.constraint_column_usage;",values={}))}
      for query in postgres_config["query"].values():
         if query.split()[0]=="0":continue
         if "add constraint" in query.lower() and query.split()[5].lower() in constraint_name_list:continue
         await postgres_client.fetch_all(query=query,values={})
   await init_extension(postgres_client)
   await init_table(postgres_client,postgres_schema_read,postgres_config)
   await init_column(postgres_client,postgres_schema_read,postgres_config)
   await init_nullable(postgres_client,postgres_schema_read,postgres_config)
   await init_index(postgres_client,postgres_config)
   await init_query(postgres_client,postgres_config)
   return None

async def ownership_check(postgres_client,table,id,user_id):
   if table=="users":
      if id!=user_id:raise Exception("object ownership issue")
   if table!="users":
      query=f"select created_by_id from {table} where id=:id;"
      values={"id":id}
      output=await postgres_client.fetch_all(query=query,values=values)
      if not output:raise Exception("no object")
      if output[0]["created_by_id"]!=user_id:raise Exception("object ownership issue")
   return None

async def add_creator_data(postgres_client,object_list,user_key):
    object_list=[dict(object) for object in object_list]
    created_by_ids={str(object["created_by_id"]) for object in object_list if object.get("created_by_id")}
    users={}
    if created_by_ids:
        query = f"SELECT * FROM users WHERE id IN ({','.join(created_by_ids)});"
        users = {str(user["id"]): dict(user) for user in await postgres_client.fetch_all(query=query,values={})}
    for object in object_list:
        created_by_id = str(object.get("created_by_id"))
        if created_by_id in users:
            for key in user_key.split(","):
                object[f"creator_{key}"] = users[created_by_id].get(key)
        else:
            for key in user_key.split(","):
                object[f"creator_{key}"] = None
    return object_list
 
async def postgres_query_runner(postgres_client,query,user_id):
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
   output=await postgres_client.fetch_all(query=query,values={})
   return output

async def postgres_update_ids(postgres_client,table,ids,column,value,updated_by_id,created_by_id):
   query=f"update {table} set {column}=:value,updated_by_id=:updated_by_id where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"value":value,"created_by_id":created_by_id,"updated_by_id":updated_by_id}
   await postgres_client.execute(query=query,values=values)
   return None

async def postgres_delete_ids(postgres_client,table,ids,created_by_id):
   query=f"delete from {table} where id in ({ids}) and (created_by_id=:created_by_id or :created_by_id is null);"
   values={"created_by_id":created_by_id}
   await postgres_client.execute(query=query,values=values)
   return None

import uuid
from io import BytesIO
async def s3_file_upload_direct(s3_client,s3_region_name,bucket,key_list,file_list):
   if not key_list:key_list=[f"{uuid.uuid4().hex}.{file.filename.rsplit('.',1)[1]}" for file in file_list]
   output={}
   for index,file in enumerate(file_list):
      key=key_list[index]
      if "." not in key:raise Exception("extension must")
      file_content=await file.read()
      file_size_kb=round(len(file_content)/1024)
      if file_size_kb>100:raise Exception("file size issue")
      s3_client.upload_fileobj(BytesIO(file_content),bucket,key)
      output[file.filename]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
      file.file.close()
   return output

async def s3_file_upload_presigned(s3_client,s3_region_name,bucket,key,expiry_sec,size_kb):
   if "." not in key:raise Exception("extension must")
   output=s3_client.generate_presigned_post(Bucket=bucket,Key=key,ExpiresIn=expiry_sec, Conditions=[['content-length-range',1,size_kb*1024]])
   for k,v in output["fields"].items():output[k]=v
   del output["fields"]
   output["url_final"]=f"https://{bucket}.s3.{s3_region_name}.amazonaws.com/{key}"
   return output
     
import csv,io
async def file_to_object_list(file):
   content=await file.read()
   content=content.decode("utf-8")
   reader=csv.DictReader(io.StringIO(content))
   object_list=[row for row in reader]
   await file.close()
   return object_list

async def form_data_read(request):
   form_data=await request.form()
   object={key:value for key,value in form_data.items() if isinstance(value,str)}
   file_list=[file for key,value in form_data.items() for file in form_data.getlist(key)  if key not in object and file.filename]
   return object,file_list

import json
async def redis_set_object(redis_client,key,expiry,object):
   object=json.dumps(object)
   if not expiry:output=await redis_client.set(key,object)
   else:output=await redis_client.setex(key,expiry,object)
   return output

import json
async def redis_get_object(redis_client,key):
   output=await redis_client.get(key)
   if output:output=json.loads(output)
   return output

import jwt,json
async def token_decode(token,key_jwt):
   user=json.loads(jwt.decode(token,key_jwt,algorithms="HS256")["data"])
   return user

import jwt,json,time
async def token_create(key_jwt,token_expire_sec,user):
   user={"id":user["id"]}
   user=json.dumps(user,default=str)
   token=jwt.encode({"exp":time.time()+token_expire_sec,"data":user},key_jwt)
   return token

async def read_user_single(postgres_client,user_id):
   query="select * from users where id=:id;"
   values={"id":user_id}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=dict(output[0]) if output else None
   if not user:raise Exception("user not found")
   return user

async def users_api_access_check(user_id,api_id_value,users_api_access,postgres_client):
   user_api_access=users_api_access.get(user_id,"absent")
   if user_api_access=="absent":
      query="select id,api_access from users where id=:id;"
      values={"id":user_id}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
      if not user:raise Exception("user not found")
      api_access_str=user["api_access"]
      if not api_access_str:raise Exception("api access denied")
      user_api_access=[int(item.strip()) for item in api_access_str.split(",")]
   if api_id_value not in user_api_access:raise Exception("api access denied")
   return None

async def users_is_active_check(user_id,users_is_active,postgres_client):
   user_is_active=users_is_active.get(user_id,"absent")
   if user_is_active=="absent":
      query="select id,is_active from users where id=:id;"
      values={"id":user_id}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
      if not user:raise Exception("user not found")
      user_is_active=user["is_active"]
   if user_is_active==0:raise Exception("user not active")
   return None

async def users_is_active_read(postgres_client_asyncpg,limit):
   users_is_active={}
   async with postgres_client_asyncpg.transaction():
      cursor=await postgres_client_asyncpg.cursor('SELECT id,is_active FROM users ORDER BY id DESC')
      count=0
      while count < limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         users_is_active.update({record['id']: record['is_active'] for record in batch})
         if False:await redis_client.mset({f"users_is_active_{record['id']}":0 if record['is_active']==0 else 1 for record in batch})
         count+=len(batch)
   return users_is_active

async def users_api_access_read(postgres_client_asyncpg,limit):
   users_api_access={}
   async with postgres_client_asyncpg.transaction():
      cursor=await postgres_client_asyncpg.cursor('SELECT id,api_access FROM users where api_access is not null ORDER BY id DESC')
      count=0
      while count < limit:
         batch=await cursor.fetch(10000)
         if not batch:break
         users_api_access.update({record['id']:[int(item.strip()) for item in record["api_access"].split(",")] for record in batch})
         if False:await redis_client.mset({f"users_api_access_{record['id']}":record['api_access'] for record in batch})
         count+=len(batch)
   return users_api_access

from fastapi import Request,responses
from starlette.background import BackgroundTask
async def api_response_background(request,api_function):
   body=await request.body()
   async def receive():return {"type":"http.request","body":body}
   async def api_function_new():
      request_new=Request(scope=request.scope,receive=receive)
      await api_function(request_new)
   response=responses.JSONResponse(status_code=200,content={"status":1,"message":"added in background"})
   response.background=BackgroundTask(api_function_new)
   return response

import json
object_list_log_api=[]
async def log_api_create(object,batch,postgres_create,postgres_client,postgres_column_datatype,object_serialize):
   global object_list_log_api
   object_list_log_api.append(object)
   if len(object_list_log_api)>=batch:
      await postgres_create("log_api",object_list_log_api,0,postgres_client,postgres_column_datatype,object_serialize)
      object_list_log_api=[]
   return None

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
async def cache_init(redis_client,redis_key_builder):
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   
import os
def router_add(router_list,app):
   for item in router_list:
       router=__import__(item).router
       app.include_router(router)

async def redis_object_create(redis_client,table,object_list,expiry):
   async with redis_client.pipeline(transaction=True) as pipe:
      for object in object_list:
         key=f"{table}_{object['id']}"
         if not expiry:pipe.set(key,json.dumps(object))
         else:pipe.setex(key,expiry,json.dumps(object))
      await pipe.execute()
   return None

async def s3_url_delete(url,s3_resource):
   bucket=url.split("//",1)[1].split(".",1)[0]
   key=url.rsplit("/",1)[1]
   output=s3_resource.Object(bucket,key).delete()
   return output

import datetime
async def update_user_last_active_at(postgres_client,user_id):
   query="update users set last_active_at=:last_active_at where id=:id;"
   values={"id":user_id,"last_active_at":datetime.datetime.now()}
   await postgres_client.execute(query=query,values=values)
   return None

async def mongodb_create_object(mongodb_client,database,table,object_list):
   mongodb_client_database=mongodb_client[database]
   output=await mongodb_client_database[table].insert_many(object_list)
   return str(output)

async def message_inbox_user(postgres_client,user_id,order,limit,offset,is_unread):
   if not is_unread:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id) select * from z order by {order} limit {limit} offset {offset};'''
   elif int(is_unread)==1:query=f'''with x as (select id,abs(created_by_id-user_id) as unique_id from message where (created_by_id=:created_by_id or user_id=:user_id)),y as (select max(id) as id from x group by unique_id),z as (select m.* from y left join message as m on y.id=m.id),a as (select * from z where user_id=:user_id and is_read!=1 is null) select * from a order by {order} limit {limit} offset {offset};'''
   values={"created_by_id":user_id,"user_id":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

async def message_received_user(postgres_client,user_id,order,limit,offset,is_unread):
   if not is_unread:query=f"select * from message where user_id=:user_id order by {order} limit {limit} offset {offset};"
   elif int(is_unread)==1:query=f"select * from message where user_id=:user_id and is_read is distinct from 1 order by {order} limit {limit} offset {offset};"
   values={"user_id":user_id}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

async def message_thread_user(postgres_client,user_id_1,user_id_2,order,limit,offset):
   query=f"select * from message where ((created_by_id=:user_id_1 and user_id=:user_id_2) or (created_by_id=:user_id_2 and user_id=:user_id_1)) order by {order} limit {limit} offset {offset};"
   values={"user_id_1":user_id_1,"user_id_2":user_id_2}
   object_list=await postgres_client.fetch_all(query=query,values=values)
   return object_list

async def mark_message_read_thread(postgres_client,user_id_1,user_id_2):
   query="update message set is_read=1 where created_by_id=:created_by_id and user_id=:user_id;"
   values={"created_by_id":user_id_2,"user_id":user_id_1}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_single(postgres_client,user_id,message_id):
   query="delete from message where id=:id and (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id,"id":message_id}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_created(postgres_client,user_id):
   query="delete from message where created_by_id=:user_id;"
   values={"user_id":user_id}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_received(postgres_client,user_id):
   query="delete from message where user_id=:user_id;"
   values={"user_id":user_id}
   await postgres_client.execute(query=query,values={})
   return None

async def message_delete_user_all(postgres_client,user_id):
   query="delete from message where (created_by_id=:user_id or user_id=:user_id);"
   values={"user_id":user_id}
   await postgres_client.execute(query=query,values={})
   return None

async def send_email_ses(ses_client,sender_email,email_list,title,body):
   ses_client.send_email(
   Source=sender_email,
   Destination={"ToAddresses":email_list},
   Message={"Subject":{"Charset":"UTF-8","Data":title},"Body":{"Text":{"Charset":"UTF-8","Data":body}}}
   )
   return None

async def send_message_template_sns(sns_client,mobile,message,entity_id,template_id,sender_id):
   sns_client.publish(
      PhoneNumber=mobile,
      Message=message,
      MessageAttributes={"AWS.MM.SMS.EntityId":{"DataType":"String","StringValue":entity_id},"AWS.MM.SMS.TemplateId":{"DataType":"String","StringValue":template_id},"AWS.SNS.SMS.SenderID":{"DataType":"String","StringValue":sender_id},"AWS.SNS.SMS.SMSType":{"DataType":"String","StringValue":"Transactional"}})
   return None

async def s3_bucket_create(s3_client,bucket,s3_region_name):
   output=s3_client.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':s3_region_name})
   return output

async def s3_bucket_public(s3_client,bucket):
   s3_client.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':False,'IgnorePublicAcls':False,'BlockPublicPolicy':False,'RestrictPublicBuckets':False})
   policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''
   output=s3_client.put_bucket_policy(Bucket=bucket,Policy=policy.replace("bucket_name",bucket))
   return output

async def s3_bucket_empty(s3_resource,bucket):
   output=s3_resource.Bucket(bucket).objects.all().delete()
   return output

async def s3_bucket_delete(s3_client,bucket):
   output=s3_client.delete_bucket(Bucket=bucket)
   return output

from google.oauth2 import id_token
from google.auth.transport import requests
def google_user_read(google_token,google_client_id):
   request=requests.Request()
   id_info=id_token.verify_oauth2_token(google_token,request,google_client_id)
   google_user={"sub": id_info.get("sub"),"email": id_info.get("email"),"name": id_info.get("name"),"picture": id_info.get("picture"),"email_verified": id_info.get("email_verified")}
   return google_user

import hashlib
async def signup_username_password(postgres_client,type,username,password):
   query="insert into users (type,username,password) values (:type,:username,:password) returning *;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   return output[0]

async def signup_username_password_bigint(postgres_client,type,username_bigint,password_bigint):
   query="insert into users (type,username_bigint,password_bigint) values (:type,:username_bigint,:password_bigint) returning *;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await postgres_client.fetch_all(query=query,values=values)
   return output[0]

import hashlib
async def login_password_username(postgres_client,token_create,key_jwt,token_expire_sec,type,username,password):
   query=f"select * from users where type=:type and username=:username and password=:password order by id desc limit 1;"
   values={"type":type,"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

import hashlib
async def login_password_username_bigint(postgres_client,token_create,key_jwt,token_expire_sec,type,username_bigint,password_bigint):
   query=f"select * from users where type=:type and username_bigint=:username_bigint and password_bigint=:password_bigint order by id desc limit 1;"
   values={"type":type,"username_bigint":username_bigint,"password_bigint":password_bigint}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

import hashlib
async def login_password_email(postgres_client,token_create,key_jwt,token_expire_sec,type,email,password):
   query=f"select * from users where type=:type and email=:email and password=:password order by id desc limit 1;"
   values={"type":type,"email":email,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

import hashlib
async def login_password_mobile(postgres_client,token_create,key_jwt,token_expire_sec,type,mobile,password):
   query=f"select * from users where type=:type and mobile=:mobile and password=:password order by id desc limit 1;"
   values={"type":type,"mobile":mobile,"password":hashlib.sha256(str(password).encode()).hexdigest()}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:raise Exception("user not found")
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

async def login_otp_email(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,email,otp):
   await verify_otp(postgres_client,otp,email,None)
   query=f"select * from users where type=:type and email=:email order by id desc limit 1;"
   values={"type":type,"email":email}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,email) values (:type,:email) returning *;"
      values={"type":type,"email":email}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

async def login_otp_mobile(postgres_client,token_create,key_jwt,token_expire_sec,verify_otp,type,mobile,otp):
   await verify_otp(postgres_client,otp,None,mobile)
   query=f"select * from users where type=:type and mobile=:mobile order by id desc limit 1;"
   values={"type":type,"mobile":mobile}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,mobile) values (:type,:mobile) returning *;"
      values={"type":type,"mobile":mobile}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

async def login_google(postgres_client,token_create,key_jwt,token_expire_sec,google_user_read,google_client_id,type,google_token):
   google_user=google_user_read(google_token,google_client_id)
   query=f"select * from users where type=:type and google_id=:google_id order by id desc limit 1;"
   values={"type":type,"google_id":google_user["sub"]}
   output=await postgres_client.fetch_all(query=query,values=values)
   user=output[0] if output else None
   if not user:
      query=f"insert into users (type,google_id,google_data) values (:type,:google_id,:google_data) returning *;"
      values={"type":type,"google_id":google_user["sub"],"google_data":json.dumps(google_user)}
      output=await postgres_client.fetch_all(query=query,values=values)
      user=output[0] if output else None
   token=await token_create(key_jwt,token_expire_sec,user)
   return token

from fastapi import responses
def error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})