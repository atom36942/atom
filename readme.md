## About

<details>
<summary>About</summary>

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










## Installation

<details>
<summary>Installation</summary>

### 1. Setup repo
Mac
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Windows
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
### 2. Setup env
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
### 3. Server Start
```bash
python main.py                  # Run directly
uvicorn main:app --reload       # Run with auto-reload (dev)
```
</details>

<details>
<summary>Installation With Docker</summary>

<br>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
docker build -t atom .
docker run -p 8000:8000 atom
```
</details>

<details>
<summary>Installation Without Activating Virtualenv</summary>

<br>

```bash
git clone https://github.com/atom36942/atom.git       # Clone the repository
cd atom                                               # Navigate into project directory
python3 -m venv venv                                  # Create a virtual environment
./venv/bin/pip install -r requirements.txt            # Install requirements
touch .env                                            # Create .env file
./venv/bin/python main.py                             # Run directly
./venv/bin/uvicorn main:app --reload                  # Start the server with reload
./venv/bin/pip install fastapi                        # Install package (ex FastAPI)
./venv/bin/pip freeze > requirements.txt              # Freeze updated dependencies
./venv/bin/pip install --upgrade fastapi              # Upgrade package (ex FastAPI)
./venv/bin/pip uninstall fastapi                      # Uninstall package (ex FastAPI)
```
</details>













## Extend Atom

<details>
<summary>Extend Router</summary>

<br>

- Easily extend Atom by adding your API router files
- How to add new router 1st way - create any `.py` file starting with `router` in the root folder
- How to add new router 2nd way - place it inside a `router/` folder with any `.py` filename
- All custom router files are auto-loaded at startup
- All routes automatically use atom middleware
- All routes includes atom middleware by defualt having prebuilt auth,admin check,user active check,ratelimter,background apis,caching,api log
- See `router.py` for sample usage
</details>

<details>
<summary>Extend Files</summary>

<br>

- Add extra file logic in `extend_{logic}.py` like function,import,pydantic,etc
- Add all extend files in `extend_master.py`
- import `extend_master.py` in your routes
```python
from extend import *
from extend_master import *
```
</details>

<details>
<summary>Extend Config</summary>

<br>

- Easily extend Atom by adding your config
- How to add new config 1st way - add it in `.env` file
- How to add new config 2nd way - create any `.py` file starting with `config` in the root folder
- How to add new config 3rd way - place it inside a `config/` folder with any `.py` filename
- How to access - Use `config` var dict in your routes
- For ex:
```python
some_value=config.get("xyz")
```
</details>













## APIs

<details>
<summary>API Collection</summary>

<br>

- All atom APIs are defined in main.py
- All atom APIs are listed in `curl.txt` as ready-to-run `curl` commands  
- You can copy-paste any of these directly into Postman (use "Raw Text" option)  
- `test.sh` executes all active curl commands automatically  
- Any line starting with `0 curl` is skipped during automated testing with `test.sh`
</details>

<details>
<summary>API Testing</summary>

<br>

- You can use the `test.sh` script to run a batch of API tests.
- It reads all curl commands from `curl.txt`
- Executes them one by one as a quick integration test
- To disable a specific curl command, prefix the curl command with `0` in `curl.txt`
- Testing Summary (URL, status code, execution time) will be saved to `curl.csv`
```bash
./test.sh
```
</details>












## Core Concept

<details>
<summary>FastAPI App</summary>

<br>

- FastAPI App is setup in the `main.py` app section.
- Lifespan events are added
- Adds CORS as per the config
- Routers auto-loaded
- Sentry is enabled if `config_sentry_dsn` is set.
- Prometheus is added if `config_is_prometheus` is 1.
</details>

<details>
<summary>Lifespan</summary>

<br>

- FastAPI backend startup and shutdown logic is handled via the lifespan function in `main.py`
- Initializes service clients at startup: Postgres, Redis, MongoDB, Kafka, RabbitMQ, Celery, AWS (S3/SNS/SES), OpenAI, PostHog etc
- Reads and caches Postgres schema, `users.api_access`, and `users.is_active` if columns exist.
- Injects all `config_`, `client_`, and `cache_` variables into `app.state`.
- Cleans up all clients on shutdown (disconnect/close/flush).
- No client is required — each is conditionally initialized if config is present.
- All startup exceptions are logged via `traceback`.
</details>

<details>
<summary>Middleware</summary>

<br>

- Handles token validation and injects user into `request.state.user` using `function_token_check`.
- Applies admin access control for apis containing `admin/` via `function_check_api_access`.
- Checks if user is active when `is_active_check` is set in `config_api`.
- Enforces rate limiting if `ratelimiter_times_sec` is set for the API.
- Runs API in background if `is_background=1` is present in query params.
- Serves cached response if `cache_sec` is set.
- Captures and logs exceptions; sends to Sentry if configured.
- Logs API calls to `log_api` table if schema has logging enabled.
</details>

<details>
<summary>Config API</summary>

<br>

- Prebuilt `config_api` dict in config.py to control api logics
- You can also add your api in the same dict
- For ex. `/test` api:
```python
"/test":{
"id":7,
"is_token":0,
"is_active_check":1,
"cache_sec":["inmemory",60],
"ratelimiter_times_sec":[1,1]
}
```
- id - unique api id
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
- Understanding `table` columns:-
```python
"type-bigint-0-btree"
"title-text-1-btree,gin"
```
- each row represent one column in the table
- `type` or `title` = column name
- `bigint` or `text` = column datatype
- `0` or `1` = column can be be null or not. if 0, it can be null else 1 which will force not null constraint
- `btree` or `btree,gin`  = index on that column. if 0, no index. it can be multiple also with comma separated values
</details>















## Modules

<details>
<summary>Client</summary>

<br>

- All clients are initialized once during app startup using the FastAPI lifespan event in `main.py`
- You can access these clients in your custom routes via `request.app.state.{client_name}`
- Available client list (check `main.py` lifespan section)
- Example:-
```python
request.app.state.client_postgres
request.app.state.client_postgres_asyncpg
request.app.state.client_postgres_asyncpg_pool
request.app.state.client_postgres_read
request.app.state.client_redis
request.app.state.client_redis_producer
request.app.state.client_mongodb
request.app.state.client_s3
request.app.state.client_s3_resource
request.app.state.client_sns
request.app.state.client_ses
request.app.state.client_openai
request.app.state.client_posthog
request.app.state.client_celery_producer
request.app.state.client_kafka_producer
request.app.state.client_rabbitmq
request.app.state.client_rabbitmq_channel
```
</details>

<details>
<summary>Token</summary>

<br>

- Extracts token from headers, validates it using `function_token_check`.
- Decoded user info is injected into `request.state.user` for downstream access.
```bash
request.state.user.get("id")
request.state.user.get("is_active")
request.state.user.get("mobile")
```
- How to enable auth for your apis: update below key in `config_api` dict in config.py for the api
```bash
is_token=1
```
To set extra user keys in token, set `config_token_key_list` in `config.py` or `.env` with first 3 keys as id,is_active,api_access
```python
config_token_key_list=id,is_active,api_access,mobile,username
``` 
</details>

<details>
<summary>User Active Check</summary>

<br>

- You can enable user is_active check for any api in your router
- This is check by atom middleware using token
- Add key `is_active_check=1` for that api In `config_api` variable in `config.py`
- To mark user inactive, set `is_active=0` column in users table
- To mark user active, set `is_active=1` or `is_active=null` column in users table
```sql
update users set is_active=0 where id=1;
```
</details>

<details>
<summary>Ratelimiter</summary>

<br>

- If `ratelimiter_times_sec` is set in `config_api`, enforces per-user rate limiting using Redis.
- Prevents abuse by limiting request frequency to defined time intervals.
- Identifier is token else host
- Add the following key to your `.env` file to enable ratelimiter
```bash
config_redis_url_ratelimiter=redis://localhost:6379
```
</details>

<details>
<summary>API Caching</summary>

<br>

- If `cache_sec` is set in `config_api`, serves cached response from Inmemory or Redis before executing the API.
- After API execution, response is cached if not already fetched from cache.
```bash
"cache_sec":["inmemory",60]
"cache_sec":["redis",60]
```
</details>

<details>
<summary>Admin APIs</summary>

<br>

- Add `/admin` in the route path to mark it as an admin API  
- Check the `curl.txt` file for examples under the admin section  
- `/admin` APIs are meant for routes that should be restricted to limited users.  
- Access control is check by middleware using token
- Assign a unique ID in the `config_api` variable in `config.py` (check existing samples there)  
- Only users whose `api_access` column in the database contains that API ID will be allowed to access it  
- Example to give user_id=1 access to admin APIs with IDs 1,2,3
```sql
update users set api_access='1,2,3' where id=1;
```
- To revoke access, update `api_access` column and refresh token 
</details>

<details>
<summary>Background Execution</summary>

<br>

- If `is_background=1` is in query params, runs the API function as a background task using `function_api_response_background`.
- Immediately returns a success response while processing continues in the background.
</details>

<details>
<summary>API Log</summary>

<br>

- Prebuilt api logs in log_api table in database using atom middleware
- If `log_api` table exists in schema, logs each API call with metadata like type, user ID, path, status, response time, and error (if any)
- Logging is done asynchronously using `function_log_create_postgres`.
- Add the following key to your `.env` file to control batch insert of log(optional,default is 10)
```bash
config_batch_log_api=value
```
</details>

<details>
<summary>CORS</summary>

<br>

- Configure cors setting by addding below config keys:
```bash
config_cors_origin_list
config_cors_method_list
config_cors_headers_list
config_cors_allow_credentials
```
</details>

<details>
<summary>Sentry</summary>

<br>

- Prebuilt Sentry connection
- Docs - https://docs.sentry.io/platforms/python/
- Logs errors and performance data to Sentry
- Add the following key to your `.env` file
```bash
config_sentry_dsn=value
```
</details>

<details>
<summary>Prometheus</summary>

<br>

- Enable Prometheus metrics by addding below config key:
```bash
config_is_prometheus=1
```
</details>

<details>
<summary>Default Settings</summary>

<br>

- With below config keys,you can control default settings
- Default values are in main.py config section
- You can add them in `.env` or `config.py` file
```bash
config_token_expire_sec=10000                               # token expiry time 
config_is_signup=0/1                                        # enable/disable signup
config_is_otp_verify=0/1                                    # enable/disable otp verify in user profile update
config_batch_object_create=10                               # control batch for object create
config_column_disabled_list=value                           # control which keys non admin users can't update
config_table_allowed_public_create_list=post,comment        # control which table insert is allowed in public
config_table_allowed_public_read_list=users,post            # control which table read is allowed in public
```
</details>














## Client

<details>
<summary>Postgres</summary>

<br>

- Atom has prebuilt postgres connection using two package Databases/Asyncpg
- Databases - https://github.com/encode/databases
- Asyncpg - https://github.com/MagicStack/asyncpg
- Use client in your routes to execute any raw sql in your router
- Add the following key to your `.env` file
```bash
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
```python
request.app.state.client_postgres 
request.app.state.client_postgres_asyncpg
request.app.state.client_postgres_asyncpg_pool
 ```
</details>

<details>
<summary>Postgres Read Replica</summary>

<br>

- Prebuilt Postgres read replica config is available.
- docs - https://github.com/encode/databases
- Add the following key to your `.env` file
```bash
config_postgres_url_read=postgresql://atom@127.0.0.1/postgres
```
- Use client in your routes
```bash
request.app.state.client_postgres_read 
 ```
</details>

<details>
<summary>Redis</summary>

<br>

- Prebuilt Redis connection
- Docs - https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- Add the following key to your `.env` file
```bash
config_redis_url=redis://localhost:6379
```
- Use client in your routes
```bash
request.app.state.clienclient_redist_mongodb 
 ```
</details>

<details>
<summary>Posthog</summary>

<br>

- Prebuilt Posthog connection
- Docs - https://posthog.com/docs/libraries/python
- Add the following key to your `.env` file
```bash
config_posthog_project_host=value
config_posthog_project_key=value
```
- Use client in your routes
- Check `/posthog` in `router.py` file for sample useage
```bash
request.app.state.client_posthog 
 ```
</details>

<details>
<summary>Mongodb</summary>

<br>

- Prebuilt Mongodb connection
- Docs - https://motor.readthedocs.io/en/stable
- Add the following key to your `.env` file
```bash
config_mongodb_url=mongodb://localhost:27017
```
- Use client in your routes
```bash
request.app.state.client_mongodb 
 ```
</details>

<details>
<summary>AWS S3</summary>

<br>

- Prebuilt AWS S3 connection
- Docs - https://boto3.amazonaws.com
- Add the following key to your `.env` file
```bash
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_s3_region_name=value
```
- Use client in your routes
```bash
request.app.state.client_s3 
request.app.state.client_s3_resource 
 ```
</details>

<details>
<summary>AWS SNS</summary>

<br>

- Prebuilt AWS SNS connection
- Docs - https://boto3.amazonaws.com
- Add the following key to your `.env` file
```bash
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_sns_region_name=value
```
- Use client in your routes
```bash
request.app.state.client_sns 
 ```
</details>

<details>
<summary>AWS SES</summary>

<br>

- Prebuilt AWS SES connection
- Docs - https://boto3.amazonaws.com
- Add the following key to your `.env` file
```bash
config_aws_access_key_id=value
config_aws_secret_access_key=value
config_ses_region_name=value
```
- Use client in your routes
```bash
request.app.state.client_ses 
 ```
</details>

<details>
<summary>OpenAI</summary>

<br>

- Prebuilt OpenAI connection
- Docs - https://github.com/openai/openai-python
- Add the following key to your `.env` file
```bash
config_openai_key=value
```
- Use client in your routes
```bash
request.app.state.client_openai 
 ```
</details>













## Consumer

<details>
<summary>Celery</summary>

<br>

- Start broker server (redis/rabbitmq)
- Add the following key to your `.env` file
```bash
config_celery_broker_url=redis://localhost:6379
```
- Check `/celery-producer` in `router.py` file for sample useage
- Check `consumer_celery.py` file for consumer logic
- You can extend both producer and consumer
- How to run `consumer_celery.py` file:
```bash
celery -A consumer_celery worker --loglevel=info                # Run with activated virtualenv
./venv/bin/celery -A consumer_celery worker --loglevel=info     # Run without activating virtualenv
```
</details>

<details>
<summary>Kafka</summary>

<br>

- Start Kafka server locally or remotely with SASL/PLAIN 
- Add the following key to your `.env` file
```bash
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
```
- Check `/kafka-producer` in `router.py` file for sample useage
- Check `consumer_kafka.py` file for consumer logic
- You can extend both producer and consumer
- How to run `consumer_kafka.py` file:
```bash
python consumer_kafka.py                # Run with activated virtualenv
./venv/bin/python consumer_kafka.py     # Run without activating virtualenv
```
</details>

<details>
<summary>RabbitMQ</summary>

<br>

- Start RabbitMQ server locally or remotely
- Add the following key to your `.env` file
```bash
config_rabbitmq_url=amqp://guest:guest@localhost:5672
```
- Check `/rabbitmq-producer` in `router.py` file for sample useage
- Check `consumer_rabbitmq.py` file for consumer logic
- You can extend both producer and consumer
- How to run `consumer_rabbitmq.py` file:
```bash
python consumer_rabbitmq.py                # Run with activated virtualenv
./venv/bin/python consumer_rabbitmq.py     # Run without activating virtualenv
```
</details>

<details>
<summary>Redis Pub/Sub</summary>

<br>

- Start Redis server locally or remotely
- Add the following key to your `.env` file
```bash
config_redis_pubsub_url=redis://localhost:6379
```
- Check `/redis-producer` in `router.py` file for sample useage
- Check `consumer_redis.py` file for consumer logic
- You can extend both producer and consumer
- How to run `consumer_redis.py` file:
```bash
python consumer_redis.py                # Run with activated virtualenv
./venv/bin/python consumer_redis.py     # Run without activating virtualenv
```
</details>









## Miscellaneous

<details>
<summary>Google Login</summary>

<br>

- Prebuilt Google Login
- Add the following key to your `.env` file
```bash
config_google_login_client_id=value
```
- check api in the auth section of file `curl.txt`
</details>

<details>
<summary>Send Otp Fast2SMS</summary>

<br>

- Prebuilt Fast2SMS connection
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

- Prebuilt Resend connection
- Docs - https://resend.com/docs/api-reference
- Add the following key to your `.env` file
```bash
config_resend_url=value
config_resend_key=value
```
- check api in the public section of file `curl.txt`
</details>








