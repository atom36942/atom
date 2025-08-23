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

```bash
#download repo
git clone https://github.com/atom36942/atom.git
cd atom

#create venv
python3 -m venv venv

#install requirements
./venv/bin/pip install -r requirements.txt

#setup env must
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_root=2n91nIEaJpsqjFUz
config_key_jwt=2n91nIEaJpsqjFUz

#setup env optional
config_sentry_dsn=value

#setup env default
config_postgres_min_connection=5
config_postgres_max_connection=20
config_redis_url_ratelimiter=value
config_token_expire_sec=10000
config_token_user_key_list=id,mobile
config_is_signup=1
config_is_otp_verify_profile_update=1
config_is_log_api=1
config_is_prometheus==0
config_batch_log_api=10
config_batch_object_create=10
config_cors_origin_list=x,y,z                   
config_cors_method_list=x,y,z
config_cors_headers_list=x,y,z
config_cors_allow_credentials=False
config_public_table_create_list=post,comment
config_public_table_read_list=users,post
config_column_update_disabled_list=is_active,is_verified
config_mode_check_api_access=token/cache
config_mode_check_is_active=token/cache
config_limit_cache_users_api_access=0
config_limit_cache_users_is_active=0 

#server start direct
./venv/bin/uvicorn main:app --reload

#server start docker
docker build -t atom .
docker run -p 8000:8000 atom
```
</details>











<details>
<summary>Commands</summary>

<br>

```bash
#package
./venv/bin/pip install fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip freeze > requirements.txt

#test curls
./curl.sh

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
<summary>Client</summary>

<br>

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
<summary>Config API</summary>

<br>

```python
config_api={
"/test":{
"id":7,
"is_token":0,
"is_active_check":1,
"cache_sec":["inmemory/redis",60],
"ratelimiter_times_sec":[1,3]
},
}
```
</details>












<details>
<summary>SOP</summary>

<br>

- `Idea` – Founder: Define problem, scope, and core features.
- `Design` – UI/UX: Convert idea into clear user flows and visual layouts.
- `Frontend` – Frontend Developer: Build responsive UI from approved designs.
- `Backend` – Backend Developer: Develop APIs, database, and business logic (Atom can be used).
- `Deployment` – Backend Developer: Deploy code to server.
- `Testing` – QA: Verify functionality, log defects, approve prototype.
- `Live` – Founder: Make the prototype publicly accessible and announce launch.
</details>











<details>
<summary>Queue</summary>

<br>

Consumer env
```bash
#celery
config_celery_broker_url=redis://localhost:6379
config_postgres_url=postgresql://atom@127.0.0.1/postgres

#kafka
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
config_postgres_url=postgresql://atom@127.0.0.1/postgres

#rabbitmq
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_postgres_url=postgresql://atom@127.0.0.1/postgres

#redis
config_redis_pubsub_url=redis://localhost:6379
config_postgres_url=postgresql://atom@127.0.0.1/postgres
```
Consumer run
```bash
#celery
cd consumer
./venv/bin/celery -A consumer_celery worker --loglevel=info

#kafka
cd consumer
./venv/bin/python consumer_kafka.py

#rabbitmq
cd consumer
./venv/bin/python consumer_rabbitmq.py

#redis
cd consumer
./venv/bin/python consumer_redis.py
```
Producer env
```bash
#celery
config_celery_broker_url=redis://localhost:6379

#kafka
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value

#rabbitmq
config_rabbitmq_url=amqp://guest:guest@localhost:5672

#redis
config_redis_pubsub_url=redis://localhost:6379
```
Producer client
```bash
request.app.state.client_celery_producer
request.app.state.client_kafka_producer
request.app.state.client_rabbitmq_producer
request.app.state.client_redis_producer
```
</details>



























## zzz













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



