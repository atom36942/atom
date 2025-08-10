## About

<details>
<summary>What is atom</summary>

<br>

- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated: full flexibility in defining business schema, API structure, and external libraries  
</details>

<details>
<summary>Tech Stack</summary>

<br>

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
<summary>File Structure</summary>

<br>

Explanation of key files in the repo:
- `function.py` – Core business logic or utility functions
- `.env` – Config variables used across the app  
- `config.py` – Config variables used across the app  
- `main.py` – FastAPI Server + core APIs 
- `extend.py` – Logic for extneding router
- `router.py` – Samples for extending the APIs  
- `curl.txt` – List of curl requests used for testing  
- `test.sh` – Shell script to execute curl.txt tests  
- `consumer_redis.py` – Redis consumer for pub/sub or queue  
- `consumer_rabbitmq.py` – RabbitMQ consumer  
- `consumer_kafka.py` – Kafka consumer  
- `consumer_celery.py` – Celery worker 
- `requirements.txt` – Python dependencies
- `readme.md` – Project documentation   
- `Dockerfile` – Build and run the project inside Docker  
- `.gitignore` – Files/directories to ignore in git
</details>

<details>
<summary>FastAPI App</summary>

<br>

- FastAPI App is setup in file `main.py` app section with Lifespan events
- Cors is enabled as per config
- Routers auto-loaded
- Sentry is enabled as per config
- Prometheus is enabled as per config
</details>

<details>
<summary>Lifespan</summary>

<br>

- Backend startup and shutdown logic is handled via the lifespan function in `main.py`
- Initializes service clients.
- Reads and caches Postgres schema and other data.
- Set app state with config,client and cache.
- Cleans up all clients on shutdown (disconnect/close/flush).
- All startup exceptions are logged via traceback.
</details>

<details>
<summary>Middleware</summary>

<br>

- Handles token validation and injects user into request state.
- Applies admin access control for admin apis.
- Checks if user is active for api if enabled.
- Enforces rate limiting for api if enabled.
- Runs API in background if enabled.
- Serves cached response for api if enabled.
- Captures and logs exceptions to Sentry if enabled.
- Logs API calls if enabled.
</details>














## Core Concept

<details>
<summary>config.py</summary>

<br>

- File `config.py` contains all extra configs
- You can define any config with any datatypes
- You can use with `config` var in your routes
```bash
xyz=123
xyz="atom"
xyz=[1,2,3]
xyz={"name":"atom"}
```
- You can use in your routes using:-
```python
config.get(xyz)
```
</details>

<details>
<summary>Config API</summary>

<br>

- Prebuilt `config_api` dict in `config.py` to control api various logic as shown in ex.
- You can also add your api in the same dict
- For ex:
```python
"/test":{
"id":7,
"is_token":0,
"is_active_check":1,
"cache_sec":["inmemory",60],
"ratelimiter_times_sec":[1,1]
}
```
- id - unique api id used in admin apis check
- is_token - 0/1 - to enable auth
- is_active_check - 0/1 - to enable user active check
- cache_sec - to cache api with inmemory/redis option
- ratelimiter_times_sec - to ratelimit api
</details>

<details>
<summary>Config Database</summary>

<br>

- Prebuilt `config_postgres_schema` dict is defined in `config.py` to initialize PostgreSQL schema.
- It has two keys: `table` and `query`.
- `table` contains table definitions.
- `query` contains extra SQL queries to run.
- You can add your own table and query to it.
- Understanding columns with different possibility for `title` column as an ex:
```python
"title-text-0-0"
"title-text-0-btree"
"title-text-1-btree,gin"
```
- `title` = column name
- `text` = column datatype
- `0` or `1` = column can be be null or not. if 0, it can be null else 1 which will force not null constraint
- `0` or `btree` or `btree,gin`  = index on that column. if 0, no index. it can be multiple also with comma separated values
</details>





















## How to use atom

<details>
<summary>Download repo</summary>

<br>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
```
</details>

<details>
<summary>Create venv</summary>

<br>

```bash
python3 -m venv venv
```
</details>

<details>
<summary>Activate venv (optional)</summary>

<br>

Mac
```bash
source venv/bin/activate
```
Windows
```bash
venv\Scripts\activate
```
</details>

<details>
<summary>Install Requirements</summary>

<br>

Install requirements
```bash
pip install -r requirements.txt                     # if venv is activated
./venv/bin/pip install -r requirements.txt          # if venv is not activated
```
Extra Commands
```bash
./venv/bin/pip install fastapi                      # Install package (ex FastAPI)
./venv/bin/pip freeze > requirements.txt            # Freeze requirements
./venv/bin/pip install --upgrade fastapi            # Upgrade package (ex FastAPI)
./venv/bin/pip uninstall fastapi                    # Uninstall package (ex FastAPI)
```
</details>

<details>
<summary>Setup env</summary>

<br>

- Create a `.env` file in the root directory with min 4 keys 
- You can use local or remote URLs for Postgres and Redis
- `config_postgres_url`: primary database (PostgreSQL) connection URL  
- `config_redis_url`: used for caching, rate limiting, background tasks, etc.  
- `config_key_root`: secret key to authenticate root-user APIs - /root/{api}  
- `config_key_jwt`: secret key used for signing and verifying JWT tokens
```env
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_root=any random secret key (2n91nIEaJpsqjFUz)
config_key_jwt=any random secret key (2n91nIEaJpsqjFUz)
```
</details>

<details>
<summary>Default Settings (optional)</summary>

<br>

- With below config keys,you can control default settings
- Default values are in main.py config section
- You can add them in `.env` or `config.py` to update default value
- Each key is independent of each other
```bash
config_token_expire_sec=10000                               # token expiry time 
config_token_user_key_list=id,mobile                        # token user keys 
config_is_signup=0/1                                        # enable/disable signup
config_is_otp_verify=0/1                                    # enable/disable otp verify in user profile update
config_batch_object_create=10                               # control batch for object create
config_column_disabled_list=value                           # control which keys non admin users can't update
config_table_allowed_public_create_list=post,comment        # control which table insert is allowed in public
config_table_allowed_public_read_list=users,post            # control which table read is allowed in public
config_batch_log_api=10                                     # control batch insert for api logs
config_cors_origin_list=x,y,z                               # control cors
config_cors_method_list=x,y,z                               # control cors
config_cors_headers_list=x,y,z                              # control cors
config_cors_allow_credentials=False                         # control cors
```
</details>

<details>
<summary>Server Start</summary>

<br>

```bash
python main.py                              # if venv is activated
./venv/bin/python main.py                   # if venv is not activated
```

With reload
```bash
uvicorn main:app --reload                   # if venv is activated
./venv/bin/uvicorn main:app --reload        # if venv is not activated
```

With Docker
```bash
docker build -t atom .
docker run -p 8000:8000 atom
```
</details>

















## Extend Atom

<details>
<summary>Extend Router</summary>

<br>

- Easily extend Atom by adding your API router files in 2 ways
- 1st way - create any `.py` file starting with `router` in the root folder
- 2nd way - place it inside a `router` folder with any `.py` filename
- All custom router files are auto-loaded at startup
- All routes automatically use middleware
- All routes includes middleware by defualt having prebuilt auth,admin check,user active check,ratelimter,background apis,caching,api log
- See `router.py` for sample usage
</details>

<details>
<summary>Extend Config</summary>

<br>

- Easily extend Atom by adding your config in 4 ways
- 1st way - add it in `.env` file
- 2nd way - add it in `config.py` file
- 3rd way - create any `.py` file starting with `config` in the root folder
- 4th way - place it inside a `config/` folder with any `.py` filename
- How to access - Use `config` var dict in your routes
- For ex:
```python
some_value=config.get("xyz")
```
</details>

<details>
<summary>Extend Files</summary>

<br>

- Add extra file logic in `extend_{logic}.py` like function,import,pydantic,etc
- Add all extend files in `extend_master.py`
- This is an opinionated approach to structure code
- import `extend_master.py` in your routes
```python
from extend import *
from extend_master import *
```
</details>


















## APIs

<details>
<summary>How to find atom APIs Collection</summary>

<br>

- All atom APIs are defined in main.py
- All atom APIs are listed in `curl.txt` as ready-to-run `curl` commands  
- You can copy-paste any of these directly into Postman (use "Raw Text" option)  
- Any curl starting with `0` is skipped during automated testing with `test.sh`
- Major section - index,root,auth,my,public,private,admin,router
</details>

<details>
<summary>How to test all atom APIs</summary>

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
<summary>How to check API Log</summary>

<br>

- Prebuilt api logs in `log_api` table in database
- Logging is done asynchronously
</details>

<details>
<summary>How to enable auth</summary>

<br>

- Add below key in `config_api` dict in `config.py` for your api:
```bash
"is_token":0
```
- Decoded user info is injected into `request.state.user` for downstream access.
```bash
request.state.user.get("id")
request.state.user.get("is_active")
request.state.user.get("mobile")
```
</details>

<details>
<summary>How to enable Caching</summary>

<br>

- Add below key in `config_api` dict in `config.py` for your api using two options:
```bash
"cache_sec":["inmemory",60]
"cache_sec":["redis",60]
```
</details>

<details>
<summary>How to enable Ratelimiter</summary>

<br>

- Add the following key to your `.env` file
- Default is `config_redis_url`
```bash
config_redis_url_ratelimiter=redis://localhost:6379
```
- Add below key in `config_api` dict in `config.py` for your api:
```bash
"ratelimiter_times_sec":[1,3]
```
</details>

<details>
<summary>How to enable user Active Check</summary>

<br>

- Add below key in `config_api` dict in `config.py` for your api:
```bash
"is_active_check":1
```
</details>

<details>
<summary>How to Execute API in Background</summary>

<br>

- Send below key in query params:
```python
is_background=1
```
- Check the `curl.txt` file for examples
- Immediately returns a success response while processing continues in the background.
</details>

<details>
<summary>How to create Admin APIs</summary>

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






















## Client

<details>
<summary>Postgres</summary>

<br>

- Atom has prebuilt postgres connection using two package Databases/Asyncpg
- Databases - https://github.com/encode/databases
- Asyncpg - https://github.com/MagicStack/asyncpg
- How to access client in your routes: to execute any raw sql in your router
- It is used for primary database
- Add the following key to your `.env` file
```bash
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
- How to access client in your routes:
```python
request.app.state.client_postgres 
request.app.state.client_postgres_asyncpg
request.app.state.client_postgres_asyncpg_pool
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Postgres Read Replica</summary>

<br>

- Prebuilt Postgres read replica config is available.
- docs - https://github.com/encode/databases
- It is used for reducing load in primary database for read queries
- Add the following key to your `.env` file
```bash
config_postgres_url_read=postgresql://atom@127.0.0.1/postgres
```
- How to access client in your routes:
```bash
request.app.state.client_postgres_read 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Redis</summary>

<br>

- Prebuilt Redis connection
- Docs - https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- It is used for cache data
- Add the following key to your `.env` file
```bash
config_redis_url=redis://localhost:6379
```
- How to access client in your routes:
```bash
request.app.state.client_redis 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Mongodb</summary>

<br>

- Prebuilt Mongodb connection
- Docs - https://motor.readthedocs.io/en/stable
- It is used for secondary database
- Add the following key to your `.env` file
```bash
config_mongodb_url=mongodb://localhost:27017
```
- How to access client in your routes:
```bash
request.app.state.client_mongodb 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>AWS S3</summary>

<br>

- Prebuilt AWS S3 connection
- Docs - https://boto3.amazonaws.com
- It is used for object storage
- Add the following key to your `.env` file
```bash
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_s3_region_name=value
```
- How to access client in your routes:
```bash
request.app.state.client_s3 
request.app.state.client_s3_resource 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>AWS SNS</summary>

<br>

- Prebuilt AWS SNS connection
- Docs - https://boto3.amazonaws.com
- It is used for sending otps
- Add the following key to your `.env` file
```bash
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_sns_region_name=value
```
- How to access client in your routes:
```bash
request.app.state.client_sns 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>AWS SES</summary>

<br>

- Prebuilt AWS SES connection
- Docs - https://boto3.amazonaws.com
- It is used for sending emails
- Add the following key to your `.env` file
```bash
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_ses_region_name=value
```
- How to access client in your routes:
```bash
request.app.state.client_ses 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Posthog</summary>

<br>

- Prebuilt Posthog connection
- Docs - https://posthog.com/docs/libraries/python
- It is used for sending events
- Add the following key to your `.env` file
```bash
config_posthog_project_host=value
config_posthog_project_key=value
```
- How to access client in your routes:
```bash
request.app.state.client_posthog 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>OpenAI</summary>

<br>

- Prebuilt OpenAI connection
- Docs - https://github.com/openai/openai-python
- It is used for llm oeprations
- Add the following key to your `.env` file
```bash
config_openai_key=value
```
- How to access client in your routes:
```bash
request.app.state.client_openai 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>


















## Queue

<details>
<summary>Celery Consumer</summary>

<br>

- Prebuilt Consumer in `consumer_celery.py`
- Docs - https://github.com/celery/celery
- You can add more functions in consumer to processs
- Add the following key to your `.env` file
```bash
config_celery_broker_url=redis://localhost:6379
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
- How to run file:
```bash
celery -A consumer_celery worker --loglevel=info                # Run with activated virtualenv
./venv/bin/celery -A consumer_celery worker --loglevel=info     # Run without activating virtualenv
```
</details>

<details>
<summary>Celery Producer</summary>

<br>

- Prebuilt Producer connection
- - You can use any function which is handled in Consumer to add it in queue
- Add the following key to your `.env` file
```bash
config_celery_broker_url=redis://localhost:6379
```
- How to access client in your routes:
```bash
request.app.state.client_celery_producer 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Kafka Consumer</summary>

<br>

- Prebuilt Consumer in `consumer_kafka.py`
- Docs - https://github.com/aio-libs/aiokafka
- You can add more functions in consumer to processs
- You can add more groups and channels
- Start Kafka server locally or remotely with SASL/PLAIN
- Add the following key to your `.env` file
```bash
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
- How to run file:
```bash
python consumer_kafka.py                # Run with activated virtualenv
./venv/bin/python consumer_kafka.py     # Run without activating virtualenv
```
</details>

<details>
<summary>Kafka Producer</summary>

<br>

- Prebuilt Producer connection
- - You can use any function which is handled in Consumer to add it in queue
- Add the following key to your `.env` file
```bash
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
```
- How to access client in your routes:
```bash
request.app.state.client_kafka_producer 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Rabbitmq Consumer</summary>

<br>

- Prebuilt Consumer in `consumer_rabbitmq.py`
- Docs - https://github.com/mosquito/aio-pika
- You can add more functions in consumer to processs
- You can add more channels
- Add the following key to your `.env` file
```bash
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
- How to run file:
```bash
python consumer_rabbitmq.py                # Run with activated virtualenv
./venv/bin/python consumer_rabbitmq.py     # Run without activating virtualenv
```
</details>

<details>
<summary>Rabbitmq Producer</summary>

<br>

- Prebuilt Producer connection
- You can use any function which is handled in Consumer to add it in queue
- Add the following key to your `.env` file
```bash
config_rabbitmq_url=amqp://guest:guest@localhost:5672
```
- How to access client in your routes:
```bash
request.app.state.client_rabbitmq_producer 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>

<details>
<summary>Redis Consumer</summary>

<br>

- Prebuilt Consumer in `consumer_redis.py`
- Docs - https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- You can add more functions in consumer to processs
- You can add more channels
- Add the following key to your `.env` file
```bash
config_redis_pubsub_url=redis://localhost:6379
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
- How to run file:
```bash
python consumer_redis.py                # Run with activated virtualenv
./venv/bin/python consumer_redis.py     # Run without activating virtualenv
```
</details>

<details>
<summary>Redis Producer</summary>

<br>

- Prebuilt Producer connection
- You can use any function which is handled in Consumer to add it in queue
- Add the following key to your `.env` file
```bash
config_redis_pubsub_url=redis://localhost:6379
```
- How to access client in your routes:
```bash
request.app.state.client_redis_producer 
 ```
- Search client name in `main.py` or `function.py` for understaning usage
</details>
















## FAQ

<details>
<summary>How to enable Sentry</summary>

<br>

- Add the following key to your `.env` file
```bash
config_sentry_dsn=value
```
</details>

<details>
<summary>How to enable Prometheus</summary>

<br>

- Add the following key to your `.env` file 
```bash
config_is_prometheus=1
```
</details>

<details>
<summary>Send Otp Fast2SMS</summary>

<br>

- Docs - https://www.fast2sms.com/docs
- Add the following key to your `.env` file
```bash
config_fast2sms_url=value
config_fast2sms_key=value
```
- check api in the public section of file `curl.txt`
</details>

<details>
<summary>Send Otp Resend</summary>

<br>

- Docs - https://resend.com/docs/api-reference
- Add the following key to your `.env` file
```bash
config_resend_url=value
config_resend_key=value
```
- check api in the public section of file `curl.txt`
</details>

<details>
<summary>Google Login</summary>

<br>

- Add the following key to your `.env` file
```bash
config_google_login_client_id=value
```
- check api in the auth section of file `curl.txt`
</details>

<details>
<summary>How to init database</summary>

<br>

- Extend config_postgres_schema as per your needs.
- Keep base table/queries as it is
- check api in the auth section of file `curl.txt`
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
</details>


