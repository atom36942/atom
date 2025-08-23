<details>
<summary>About</summary>

<br>

About
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated: full flexibility in defining business schema, API structure, and external libraries

Tech Stack
Atom uses a proven tech stack so you can build fast without worrying about stack choices.
- Language: Python  
- Framework: FastAPI (for building async APIs)  
- Database: PostgreSQL (primary relational database)  
- Caching: Redis or Valkey (used for cache, rate limiting, task queues, etc.)  
- Object Storage: S3 (for storing files and media objects)  
- Queue: RabbitMQ or Kafka (for background jobs and async processing)  
- Task Worker: Celery (for background processing)  
- Monitoring: Sentry/Prometheus (for error tracking and performance monitoring)  
</details>



































<details>
<summary>Installation</summary>

<br>

Setup Repo
```bash
#download repo
git clone https://github.com/atom36942/atom.git
cd atom

#create venv
python3 -m venv venv

#install requirements
./venv/bin/pip install -r requirements.txt
```
Setup env
- Create a `.env` file in the root directory with min 4 keys 
- `config_postgres_url`: primary database (PostgreSQL) connection URL  
- `config_redis_url`: used for caching,rate limiting etc 
- `config_key_root`: secret key to authenticate root-user APIs - /root/{api}  
- `config_key_jwt`: secret key used for signing and verifying JWT tokens
```env
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_root=any random secret key (2n91nIEaJpsqjFUz)
config_key_jwt=any random secret key (2n91nIEaJpsqjFUz)
```
Server Start
```bash
#direct
./venv/bin/python main.py

#reload
./venv/bin/uvicorn main:app --reload

#docker
docker build -t atom .
docker run -p 8000:8000 atom
```
</details>






































## Feature

<details>
<summary>API Collection</summary>

<br>

- All atom APIs are defined in main.py
- All atom APIs are listed in `curl.txt` as ready-to-run `curl` commands  
- You can copy-paste any of these directly into Postman (use "Raw Text" option)  
- Any curl starting with `0` is skipped during automated testing with `test.sh`
- Major section - index,root,auth,my,public,private,admin,router
</details>

<details>
<summary>API Testing</summary>

<br>

- You can use the `test.sh` script to run a batch of API tests.
- It reads all curl commands from `curl.txt`
- Executes them one by one as a quick integration test
- To disable a specific curl command, prefix the curl command with `0` in `curl.txt`
- Testing Summary (API,Status Code,Response Time (ms)) will be saved to `curl.csv` in the root folder
- How to run script:
```bash
./test.sh
```
</details>

<details>
<summary>API Log</summary>

<br>

- Prebuilt api logs in `log_api` table in database
- Logging is done asynchronously
</details>

<details>
<summary>Default Settings</summary>

<br>

- With below config keys,you can control default settings
- Default values are in main.py config section
- You can add them in `.env` or `config.py` to update default value
- Each key is independent of each other
```bash
#postgres
config_postgres_min_connection=5
config_postgres_max_connection=20

#ratelimiter
config_redis_url_ratelimiter=value

#token
config_token_expire_sec=10000
config_token_user_key_list=id,mobile

#enable/disable
config_is_signup=1
config_is_otp_verify_profile_update=1
config_is_log_api=1
config_is_prometheus==0

#batch
config_batch_log_api=10
config_batch_object_create=10

#cors                             
config_cors_origin_list=x,y,z                   
config_cors_method_list=x,y,z
config_cors_headers_list=x,y,z
config_cors_allow_credentials=False

#crud
config_public_table_create_list=post,comment
config_public_table_read_list=users,post
config_column_update_disabled_list=is_active,is_verified

#mode
config_mode_check_api_access=token/cache
config_mode_check_is_active=token/cache

#cache
config_limit_cache_users_api_access=0
config_limit_cache_users_is_active=0     
```
</details>

<details>
<summary>Enable Monitoring</summary>

<br>

Add the following key to your `.env` file
```bash
#sentry
config_sentry_dsn=value

#prometheus
config_is_prometheus=1
```
</details>

<details>
<summary>Client</summary>

<br>

- Search client name in `main.py` or `function.py` for understaning usage. Docs link below:-
- Databases - https://github.com/encode/databases
- Asyncpg - https://github.com/MagicStack/asyncpg
- Redis - https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- Mongodb - https://motor.readthedocs.io/en/stable
- AWS S3/SNS/SES - https://boto3.amazonaws.com
- Posthog - https://posthog.com/docs/libraries/python
- OpenAI - https://github.com/openai/openai-python
- How to enable: add below key in .env
```bash
#postgres
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_postgres_url_read=postgresql://atom@127.0.0.1/postgres

#redis
config_redis_url=redis://localhost:6379

#mongodb
config_mongodb_url=mongodb://localhost:27017

#aws s3
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_s3_region_name=value

#aws sns
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_sns_region_name=value

#aws ses
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_ses_region_name=value

#posthog
config_posthog_project_host=value
config_posthog_project_key=value

#openai
config_openai_key=value
```

How to access client in your routes.
```python
request.app.state.client_postgres
request.app.state.client_postgres_asyncpg
request.app.state.client_postgres_asyncpg_pool
request.app.state.client_postgres_read
request.app.state.client_redis
request.app.state.client_mongodb
request.app.state.client_s3
request.app.state.client_s3_resource
request.app.state.client_sns
request.app.state.client_ses
request.app.state.client_posthog
request.app.state.client_openai 
 ```
</details>

<details>
<summary>Database Init</summary>

<br>

- Extend below config_postgres_schema as per your schema.
- Replace it in config.py
```python
config_postgres_schema={
"table":{
"test":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-bigint-0-btree",
"title-text-0-btree,gin",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0",
"rating-numeric(10,3)-0-0",
"remark-text-0-btree,gin",
"location-geography(POINT)-0-gist",
"metadata-jsonb-0-gin"
],
"users":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-bigint-1-btree",
"username-text-0-btree",
"password-text-0-btree",
"google_id-text-0-btree",
"google_data-jsonb-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"api_access-text-0-0",
"last_active_at-timestamptz-0-0",
"username_bigint-bigint-0-btree",
"password_bigint-bigint-0-btree"
],
"otp":[
"created_at-timestamptz-0-brin",
"otp-integer-1-0",
"email-text-0-btree",
"mobile-text-0-btree"
],
"log_password":[
"created_at-timestamptz-0-0",
"user_id-bigint-0-0",
"password-text-0-0"
],
"message":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"user_id-bigint-1-btree",
"description-text-1-0",
"is_read-smallint-0-btree"
],
"report_user":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"user_id-bigint-1-btree"
],
"log_api":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"type-bigint-0-btree",
"ip_address-text-0-0",
"api-text-0-btree,gin",
"method-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-0",
"response_time_ms-numeric(1000,3)-0-0",
"description-text-0-0"
],
},
"query":{
"users_disable_bulk_delete":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"users_check_username":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"users_unique_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"users_unique_2":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"users_unique_3":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"users_unique_4":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_id);",
"users_unique_5":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"users_unique_6":"alter table users add constraint constraint_unique_users_type_username_bigint unique (type,username_bigint);",
}
}
```
- It has two keys: table and query.
- Table contains table definitions.
- Query contains extra SQL queries to run.
- Understanding schema:-
```python
"type-bigint-0-btree"
"title-text-1-btree,gin"
```
- each row represent one column in the table
- `type` or `title` = column name
- `bigint` or `text` = column datatype
- `0` or `1` = column can be be null or not. if 0, it can be null else 1 which will force not null constraint
- `btree` or `btree,gin`  = index on that column. if 0, no index. it can be multiple also with comma separated values
- Hit below curl to init the database
- Token root is from .env (`config_key_root`)
```curl
curl -X GET "$baseurl/root/postgres-init" -H "Authorization: Bearer $token_root"
```
</details>

<details>
<summary>Config API</summary>

<br>

- Update below `config_api` dict in `config.py` for your api settings:
```bash
config_api={
"/admin/object-create":{"id":1},
"/admin/object-update":{"id":2},
"/admin/ids-update":{"id":3},
"/admin/ids-delete":{"id":4}, 
"/admin/object-read":{"id":5,"cache_sec":["redis",100]},
"/admin/postgres-query-runner":{"id":6},
"/test":{"id":7,"is_token":0,"is_active_check":1,"cache_sec":["inmemory",60],"ratelimiter_times_sec":[1,3]},
}
```
- enable admin check - id:100
- enable auth - is_token:1
- enable user active check - is_active_check:1
- enable caching - cache_sec:["inmemory/redis",60]
- enable ratelimiter - ratelimiter_times_sec:[1,3]
</details>

<details>
<summary>Admin APIs</summary>

<br>

- Add `/admin` in the route path to mark it as an admin API  
- Check the `curl.txt` file for examples
- `/admin` APIs are meant for routes that should be restricted to limited users.  
- Access control is check by middleware using token
- Assign a unique ID in the `config_api` in `config.py`:
```bash
"id":3
```
- Only users whose `api_access` column in the database contains that API ID will be allowed to access it  
- Example to give user_id=1 access to admin APIs with IDs 1,2,3
```sql
update users set api_access='1,2,3' where id=1;
```
- To revoke access, update `api_access` column and refresh token 
</details>

<details>
<summary>Token Decode</summary>

<br>

- Decoded user info is injected into `request.state.user` for downstream access.
```bash
request.state.user.get("id")
request.state.user.get("is_active")
request.state.user.get("mobile")
```
</details>

<details>
<summary>Execute API in Background</summary>

<br>

- Check the `curl.txt` file for examples
- Immediately returns a success response while processing continues in the background.
- Send below key in query params:
```python
is_background=1
```
</details>

<details>
<summary>Send Otp</summary>

<br>

- Fast2SMS - https://www.fast2sms.com/docs
- Resend - https://resend.com/docs/api-reference
- Check api in the public section of file `curl.txt`
- Add the following key to your `.env` file
```bash
#fast2sms
config_fast2sms_url=value
config_fast2sms_key=value

#resend
config_resend_url=value
config_resend_key=value
```
</details>

<details>
<summary>Google Login</summary>

<br>

- Check api in the auth section of file `curl.txt`
- Add the following key to your `.env` file
```bash
#google
config_google_login_client_id=value
```
</details>

<details>
<summary>Celery</summary>

<br>

- Prebuilt Consumer/Producer client
- Docs - https://github.com/celery/celery
- You can add more functions in consumer/producer
- Search producer client in `main.py` or `function.py` for understaning usage
- Commands:
```bash
#consumer .env
config_celery_broker_url=redis://localhost:6379
config_postgres_url=postgresql://atom@127.0.0.1/postgres

##consumer run
./venv/bin/celery -A consumer_celery worker --loglevel=info

#producer .env
config_celery_broker_url=redis://localhost:6379

#producer client
request.app.state.client_celery_producer 
```
</details>


<details>
<summary>Kafka</summary>

<br>

- Prebuilt Consumer/Producer client
- Docs - https://github.com/aio-libs/aiokafka
- You can add more functions in consumer/producer
- Search producer client in `main.py` or `function.py` for understaning usage
- Commands:
```bash
#consumer .env
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
config_postgres_url=postgresql://atom@127.0.0.1/postgres

##consumer run
./venv/bin/python consumer_kafka.py

#producer .env
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value

#producer client
request.app.state.client_kafka_producer
```
</details>

<details>
<summary>Rabbitmq</summary>

<br>

- Prebuilt Consumer/Producer client
- Docs - https://github.com/mosquito/aio-pika
- You can add more functions in consumer/producer
- Search producer client in `main.py` or `function.py` for understaning usage
- Commands:
```bash
#consumer .env
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_postgres_url=postgresql://atom@127.0.0.1/postgres

##consumer run
./venv/bin/python consumer_rabbitmq.py

#producer .env
config_rabbitmq_url=amqp://guest:guest@localhost:5672

#producer client
request.app.state.client_rabbitmq_producer
```
</details>

<details>
<summary>Redis Pub-Sub</summary>

<br>

- Prebuilt Consumer/Producer client
- Docs - https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- You can add more functions in consumer/producer
- Search producer client in `main.py` or `function.py` for understaning usage
- Commands:
```bash
#consumer .env
config_redis_pubsub_url=redis://localhost:6379
config_postgres_url=postgresql://atom@127.0.0.1/postgres

##consumer run
./venv/bin/python consumer_redis.py

#producer .env
config_redis_pubsub_url=redis://localhost:6379

#producer client
request.app.state.client_redis_producer
```
</details>























## Misc

<details>
<summary>Useful Commands</summary>

<br>

```bash
#package
./venv/bin/pip install fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip freeze > requirements.txt

#stop python
lsof -ti :8000 | xargs kill -9

#reset postgres                    
drop schema if exists public cascade;
create schema if not exists public;

#export postgres
\copy table to 'path'  delimiter ',' csv header;
\copy (query) to 'path'  delimiter ',' csv header;

#import postgres       
\copy table from 'path' delimiter ',' csv header;
\copy table(column) from 'path' delimiter ',' csv header;   
```
</details>

<details>
<summary>SOP for developing an Idea</summary>

<br>

- `Idea` – Founder: Define problem, scope, and core features.
- `Design` – UI/UX: Convert idea into clear user flows and visual layouts.
- `Frontend` – Frontend Developer: Build responsive UI from approved designs.
- `Backend` – Backend Developer: Develop APIs, database, and business logic (Atom can be used).
- `Deployment` – Backend Developer: Deploy code to server.
- `Testing` – QA: Verify functionality, log defects, approve prototype.
- `Live` – Founder: Make the prototype publicly accessible and announce launch.
</details>

