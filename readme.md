## About
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated: full flexibility in defining business schema, API structure, and external libraries
- Tech Stack:Python,FastAPI,PostgreSQL,Redis,S3,Celery,RabbitMQ,Kafka,Sentry





## Modules
- one click postgres database setup
- postgres csv uploader
- postgres query runner
- auth apis
- logged in user apis
- admin apis
- api cache using redis
- celery/kafka/rabbitmq/redis pub-sub queue setup
- sentry/mongodb/posthog integration
- otp client integration - fast2sms/resend
- aws s3,sns,ses integration
- ratelimiter setup
- html pages serve
- postgres crud apis as per rbac








## Installation
```bash
#setup
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

#env
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_jwt=YwAyJ6hIrvpRrv4clHM8asr6gATOg
config_key_root=UZit5LLGZmqqvScH8E8PAZSsYKSt
config_mongodb_url=mongodb://localhost:27017
config_celery_broker_url=redis://localhost:6379
config_celery_backend_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_redis_pubsub_url=redis://localhost:6379

#start
./venv/bin/uvicorn main:app --reload
```







## Commands
```bash
#test curl
./curl.sh

#docker
docker build -t atom .
docker run -p 8000:8000 atom

#consumer
venv/bin/celery -A consumer.celery worker --loglevel=info
venv/bin/python -m consumer.kafka
venv/bin/python -m consumer.rabbitmq
venv/bin/python -m consumer.redis
```







## zzz
```bash
#package
./venv/bin/pip install fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip freeze > requirements.txt

#cli
postgres=psql postgresql://atom@127.0.0.1/postgres
mongodb=mongosh
redis=redis-cli -u redis://localhost:6379

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

#p95
SELECT api, ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)::numeric, 2) AS p95_response_time FROM log_api WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY api ORDER BY p95_response_time DESC;

#asyncio
from function import function_postgres_export
import asyncio
x="postgresql://atom@127.0.0.1/postgres"
y="select * from users limit 10"
asyncio.run(function_postgres_export(x,y))

#postgres sample insert
INSERT INTO test (type, title, location) VALUES
(1, 'Near 100m',  'POINT(80.0009 15.0009)'),
(2, 'Near 200m',  'POINT(80.0018 15.0018)'),
(3, 'Near 300m',  'POINT(80.0027 15.0027)'),
(4, 'Near 400m',  'POINT(80.0036 15.0036)'),
(5, 'Near 500m',  'POINT(80.0045 15.0045)'),
(6, 'Near 600m',  'POINT(80.0054 15.0054)'),
(7, 'Near 700m',  'POINT(80.0063 15.0063)'),
(8, 'Near 800m',  'POINT(80.0072 15.0072)'),
(9, 'Near 900m',  'POINT(80.0081 15.0081)'),
(10,'Near 1000m', 'POINT(80.0090 15.0090)');
```
